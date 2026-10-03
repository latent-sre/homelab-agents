"""Project a routing cluster onto `claude plugin eval` case directories.

`evals/routing/*.json` is the single source for what a routing case asks. This module turns each
case into the native harness's layout -- `<case>/prompt.md` plus one grader -- and the harness both
runs and grades it. The directory is generated per run and git-ignored, so it cannot drift from the
cluster it came from.

A routing decision travels through the Agent tool (`"subagent_type"`) or the Skill tool
(`"skill"`), so each case gets ONE `regex` grader over the run's trace that matches either key
naming any of the case's targets, in the plugin-namespaced or bare spelling:

- a positive passes a run when the trace `contains` a dispatch to an expected destination;
- a negative passes a run when the trace does `not_contains` a dispatch to a forbidden one.

On a paired batch (prompt-tooling, 36 runs, 2026-10-03) this grader agreed with the retired
fleet-side grader on every run. The one known difference: it also counts a dispatch whose spawn
came back an error, which the fleet-side grader excluded.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping

from fleet.frontmatter import NAME_RE, yaml_flow_list, yaml_scalar, yaml_single_quoted
from fleet.fs import safe_path_segment

# Read-only tools plus the two a routing decision travels through, so a run can inspect and route
# but not change anything.
DEFAULT_ALLOWED_TOOLS = ("Read", "Glob", "Grep", "Skill", "Agent")

# A routing decision is made in the first turns or not at all; every turn past it is paid for
# without being measured.
DEFAULT_MAX_TURNS = 6

DEFAULT_NAMESPACE = "sde-agents"


def targets_of(spec: Mapping[str, object], case: Mapping[str, object]) -> tuple[str, list[str]]:
    """The polarity and the components a case is graded against.

    A negative without `expect_not_fires` is graded against the whole cluster -- the documented
    broad negative.
    """
    polarity = case.get("polarity")
    if polarity == "positive":
        targets = case.get("expect_fires")
    elif polarity == "negative":
        targets = case.get("expect_not_fires", spec.get("members"))
    else:
        raise ValueError(
            f"case {case.get('id')!r} polarity must be 'positive' or 'negative' (got {polarity!r})"
        )
    if not isinstance(targets, list) or not targets:
        raise ValueError(f"case {case.get('id')!r} has no components to grade against")
    return str(polarity), [str(target) for target in targets]


def routing_pattern(components: Iterable[str], namespace: str = DEFAULT_NAMESPACE) -> str:
    """A trace regex for "one of these components was dispatched", through Agent or Skill.

    Both spellings are live (`<namespace>:<name>` and the bare name). The opening and closing
    quotes are part of the pattern, so `prompt-craft` matches neither a longer name that starts
    with it nor another plugin's component of the same name. The harness compiles the pattern as
    a JavaScript RegExp, so names are inserted verbatim rather than through `re.escape`, whose
    `\\-` JavaScript rejects under the `u` flag; the component-name grammar admits no other
    character a regex treats specially.
    """
    unsafe = [name for name in (*components, namespace) if not NAME_RE.fullmatch(name)]
    if unsafe:
        raise ValueError(f"not a component name, cannot go into a grader pattern: {unsafe!r}")
    names = "|".join(sorted(set(components)))
    prefix = namespace
    return (
        rf'"subagent_type"\s*:\s*"(?:{prefix}:)?(?:{names})"'
        rf'|"skill"\s*:\s*"(?:{prefix}:)?(?:{names})"'
    )


def _grader(polarity: str, targets: list[str], namespace: str) -> str:
    match = "contains" if polarity == "positive" else "not_contains"
    named = ", ".join(f"`{target}`" for target in targets)
    claim = (
        f"At least one of {named} was dispatched"
        if polarity == "positive"
        else f"None of {named} was dispatched"
    )
    return f"""---
type: regex
target: trace
match: {match}
pattern: {yaml_single_quoted(routing_pattern(targets, namespace))}
---

{claim} through the Agent or Skill tool, in the plugin-namespaced or bare spelling.
"""


def case_files(
    spec: Mapping[str, object],
    case: Mapping[str, object],
    *,
    namespace: str = DEFAULT_NAMESPACE,
    max_turns: int = DEFAULT_MAX_TURNS,
    timeout_seconds: int = 180,
    allowed_tools: Iterable[str] = DEFAULT_ALLOWED_TOOLS,
) -> dict[str, str]:
    """One case's files, keyed by path relative to the generated eval directory."""
    # The id becomes a DIRECTORY NAME, so it is checked before it is joined to anything: an
    # absolute or `..` id would write the case outside the generated tree.
    case_id = safe_path_segment(str(case["id"]), what="case id")
    cluster = str(spec["cluster"])
    polarity, targets = targets_of(spec, case)
    raw_tags = case.get("tags") or []
    if not isinstance(raw_tags, list) or any(
        not isinstance(tag, (str, int, float)) for tag in raw_tags
    ):
        raise ValueError(f"case {case_id!r} 'tags' must be a list of scalars (got {raw_tags!r})")
    description = (
        f"Generated from evals/routing/{cluster}.json case {case_id} by fleet/nativecases.py. "
        "Do not edit: the cluster JSON is the source, and this directory is rewritten every run."
    )
    frontmatter = "\n".join(
        [
            "---",
            f"name: {yaml_scalar(case_id)}",
            f"description: {yaml_scalar(description)}",
            f"tags: {yaml_flow_list([cluster, polarity, *(str(tag) for tag in raw_tags)])}",
            f"expected_outcome: {yaml_scalar(str(case.get('expected_output') or ''))}",
            f"max_turns: {max_turns}",
            f"timeout_seconds: {timeout_seconds}",
            f"allowed_tools: {yaml_flow_list(allowed_tools)}",
            "---",
            "",
            "",
        ]
    )
    return {
        f"{case_id}/prompt.md": frontmatter + str(case["prompt"]) + "\n",
        f"{case_id}/graders/routing.md": _grader(polarity, targets, namespace),
    }


def cluster_files(
    spec: Mapping[str, object], cases: Iterable[Mapping[str, object]], **options: object
) -> dict[str, str]:
    """Every case's files, refusing two cases whose ids collide.

    Case-FOLDED, because the generated directory is keyed by id and Windows resolves `Case` and
    `case` to one directory: a collision would silently run fewer cases than the cluster holds.
    """
    files: dict[str, str] = {}
    seen: dict[str, str] = {}
    for case in cases:
        case_id = str(case["id"])
        key = case_id.casefold()
        if key in seen:
            raise ValueError(
                f"cluster {spec.get('cluster')!r} has two cases whose ids collide: "
                f"{seen[key]!r} and {case_id!r}"
            )
        seen[key] = case_id
        files.update(case_files(spec, case, **options))  # type: ignore[arg-type]
    return files


def manifest(spec: Mapping[str, object], files: Mapping[str, str]) -> str:
    """A record written beside the generated cases saying what produced them."""
    return (
        json.dumps(
            {
                "generated_by": "fleet/nativecases.py",
                "cluster": spec.get("cluster"),
                "source": f"evals/routing/{spec.get('cluster')}.json",
                "files": sorted(files),
                "warning": "generated per run; edit the cluster JSON, never this directory",
            },
            indent=2,
        )
        + "\n"
    )
