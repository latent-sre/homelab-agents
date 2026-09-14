"""Project a routing cluster onto `claude plugin eval` case directories.

Phase 4 keeps `evals/routing/*.json` as the single source for what a routing case asks and hands
the RUNNING of it to the native harness. This module is the projection between the two, and it is
generated per run rather than committed: a committed copy would be a second statement of every
case, free to drift from the cluster it came from, and the fleet already pays that byte-drift tax
once for the host adapters. One source, one reader.

**The generated graders are a tripwire, never the verdict.** `fleet.routing` computes the verdict
from the harness's own traces, for two reasons that were measured rather than assumed:

1. `tool_used` counts a call whose input matches its regex whether or not the spawn SUCCEEDED
   (`docs/archive/2026-09/native-grader-errored-spawn-2026-09-14.md`). On a positive case that is
   the weaker oracle -- a routing regression hides behind a dispatch that never landed.
2. A positive case names the destinations that are all CORRECT, and passes when any one of them
   fires. Every multi-target positive in this repository -- 18 of 41 on 2026-09-14 -- names both
   an agent and a skill, so the disjunction spans two tools. A `tool_used` grader names one tool
   and several of them are scored conjunctively, so no combination of them states "Agent A or
   Skill B fired".

So the graders emitted here are only the ones that cannot cry wolf on a correct run:

- A **negative** target becomes `min: 0, max: 0` on the tool that target dispatches through. That
  is faithful or stricter -- stricter only where an errored spawn is counted -- so it can raise a
  false alarm but can never hide an over-trigger.
- A **positive** case gets one deliberately vacuous grader, because nothing faithful can be said
  about it here. It is vacuous in the open rather than partly-true, so a reader cannot mistake the
  native score for a routing result; the grader's own prose says where the verdict comes from.

The harness rejects a case with no graders (`graders: Required`), which is why the vacuous one
exists at all rather than the field being omitted.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping

from fleet.frontmatter import yaml_flow_list, yaml_scalar, yaml_single_quoted
from fleet.fs import safe_path_segment

# Read-only tools plus the two a routing decision travels through. The retiring runner ran
# `claude -p` under default headless permissions, which denies the mutating tools by approval
# rather than by roster; naming the read-only set explicitly reaches the same surface through the
# native harness's own control instead of relying on a default staying put.
DEFAULT_ALLOWED_TOOLS = ("Read", "Glob", "Grep", "Skill", "Agent")

# A routing decision is made in the first turns or not at all, and every turn past it is paid for
# without being measured. The retiring runner bounded runs by wall clock only and graded whatever
# partial transcript it had; a turn cap is the native harness's equivalent lever.
DEFAULT_MAX_TURNS = 6

# The namespace the generated TRIPWIRE graders match. A default only; `case_files` takes the
# evaluated plugin's own, because a grader hardcoding this one stayed green on an
# `other-plugin:root-cause` dispatch -- reporting a clean native run on an over-trigger it
# simply could not see, while the fleet-side verdict (which does read the dynamic namespace)
# correctly failed the case.
DEFAULT_NAMESPACE = "sde-agents"

_VACUOUS_GRADER = """---
type: tool_used
tool: Agent
min: 0
arm: both
---

Deliberately vacuous: it passes on every run, and the native score for this case means nothing.

A positive case passes when ANY of its expected destinations fires, and those destinations span
the Agent and Skill tools, which no combination of `tool_used` graders can express. The verdict
for this case is computed by `fleet/routing.py` from this run's own trace, which also excludes a
dispatch that came back an error -- something `tool_used` counts as a call.

The harness requires at least one grader, so this states its own emptiness rather than pretending
to a partial truth a reader might mistake for a result.
"""


def tool_for(component: str, agents: Iterable[str]) -> str:
    """The tool a component is dispatched through: `Agent` for an agent, `Skill` for a skill.

    Taken from the fleet roster rather than guessed from the case, because the case names a
    destination and says nothing about how it is reached.
    """
    return "Agent" if component in set(agents) else "Skill"


def forbidden_pattern(component: str, tool: str, namespace: str = DEFAULT_NAMESPACE) -> str:
    """The `input_match` regex for "this component was dispatched through this tool".

    Both spellings are live: a plugin component is usually reached as `sde-agents:<name>`, but a
    transcript may carry the bare name, and a grader matching only one of them would report a
    clean run on an over-trigger it simply failed to see. The closing quote is part of the
    pattern, so `homelab-engineer` cannot match a longer name that merely starts with it.
    """
    prefix = re.escape(namespace)
    if tool == "Agent":
        return rf'"subagent_type"\s*:\s*"(?:{prefix}:)?{component}"'
    return rf'"(?:command|skill|name)"\s*:\s*"(?:{prefix}:)?{component}"'


def _forbidden_grader(component: str, tool: str, namespace: str) -> str:
    pattern = forbidden_pattern(component, tool, namespace)
    return f"""---
type: tool_used
tool: {tool}
min: 0
max: 0
arm: both
input_match: {yaml_single_quoted(pattern)}
---

The {tool} tool was never called for `{component}`, in either the plugin-namespaced spelling
(`{namespace}:{component}`) or the bare one.

A tripwire, not the verdict: `tool_used` counts a call whose input matches whether or not the
spawn succeeded, so on a negative this is faithful or stricter -- it can raise a false alarm on a
dispatch that errored out, and can never hide a real over-trigger. The verdict is computed by
`fleet/routing.py` from this run's trace.
"""


def case_files(
    spec: Mapping[str, object],
    case: Mapping[str, object],
    *,
    agents: Iterable[str],
    namespace: str = DEFAULT_NAMESPACE,
    max_turns: int = DEFAULT_MAX_TURNS,
    timeout_seconds: int = 180,
    allowed_tools: Iterable[str] = DEFAULT_ALLOWED_TOOLS,
) -> dict[str, str]:
    """One case's files, keyed by path relative to the generated eval directory."""
    # The id becomes a DIRECTORY NAME below, so it is checked before it is joined to anything.
    # An absolute id silently discards the base it is joined to (`Path("/base") / "/tmp/x"` is
    # `/tmp/x`), which wrote generated case files outside the eval tree entirely.
    case_id = safe_path_segment(str(case["id"]), what="case id")
    cluster = str(spec["cluster"])
    polarity = case["polarity"]
    agent_set = set(agents)

    if polarity == "negative":
        targets = case.get("expect_not_fires")
        if targets is None:
            targets = list(spec["members"])  # the documented broad negative: the whole cluster
        graders = {}
        for target in targets:
            # The target becomes a FILENAME. Unchecked, a member like `x/../../prompt` produced
            # `<case>/graders/no-x/../../prompt.md`, which normalises onto `<case>/prompt.md` --
            # a grader silently overwriting the case's own prompt, and the containment check
            # downstream still passed because the result stays inside the tree.
            name = safe_path_segment(str(target), what="cluster member")
            graders[f"{case_id}/graders/no-{name}.md"] = _forbidden_grader(
                name, tool_for(name, agent_set), namespace
            )
    else:
        graders = {f"{case_id}/graders/verdict-is-fleet-side.md": _VACUOUS_GRADER}

    # The cluster and the case id travel into the generated case so a stray results directory can
    # still say which source case it came from. `description` is the harness's own field; the
    # cluster's `expected_output` prose is the case's reasoning and is preserved verbatim.
    expected = case.get("expected_output") or ""
    description = (
        f"Generated from evals/routing/{cluster}.json case {case_id} by fleet/nativecases.py. "
        "Do not edit: the cluster JSON is the source, and this directory is rewritten every run."
    )
    # Validated before iteration: `"tags": 1` is syntactically valid JSON, and iterating the
    # scalar raised TypeError out of `cluster_files` -- past the ValueError handler in the runner,
    # so the CLI ended in a traceback instead of the documented configuration exit before launch.
    raw_tags = case.get("tags")
    if raw_tags is None:
        raw_tags = []
    scalar = (str, int, float)
    if not isinstance(raw_tags, list) or any(not isinstance(t, scalar) for t in raw_tags):
        raise ValueError(
            f"case {case.get('id')!r} 'tags' must be a list of scalars (got {raw_tags!r})"
        )
    tags = [str(t) for t in raw_tags]
    frontmatter = "\n".join(
        [
            "---",
            f"name: {yaml_scalar(case_id)}",
            f"description: {yaml_scalar(description)}",
            f"tags: {yaml_flow_list([cluster, str(polarity), *tags])}",
            f"expected_outcome: {yaml_scalar(str(expected))}",
            f"max_turns: {max_turns}",
            f"timeout_seconds: {timeout_seconds}",
            f"allowed_tools: {yaml_flow_list(allowed_tools)}",
            "---",
            "",
            "",
        ]
    )
    return {f"{case_id}/prompt.md": frontmatter + str(case["prompt"]) + "\n", **graders}


def cluster_files(
    spec: Mapping[str, object],
    cases: Iterable[Mapping[str, object]],
    *,
    agents: Iterable[str],
    **options: object,
) -> dict[str, str]:
    """Every selected case's files, keyed by path relative to the generated eval directory.

    Refuses two cases sharing an id rather than letting the second silently overwrite the first:
    the generated directory is keyed by id, so a duplicate would drop a case from the measurement
    while every count still looked right.
    """
    files: dict[str, str] = {}
    seen: dict[str, str] = {}
    for case in cases:
        case_id = str(case["id"])
        # Case-FOLDED, because the collision is a filesystem property rather than a string one:
        # Windows and the default macOS volume resolve `Case` and `case` to one directory, so a
        # case-sensitive check accepted both and the generated tree then ran fewer cases than the
        # cluster selected -- after the sessions were paid for. The reserved-character checks in
        # `fleet.fs` do not cover aliasing; this does.
        key = case_id.casefold()
        if key in seen:
            also = seen[key]
            detail = (
                f"id {case_id!r}"
                if also == case_id
                else f"ids {also!r} and {case_id!r}, which differ only in case"
            )
            raise ValueError(
                f"cluster {spec.get('cluster')!r} has two cases with {detail}; the generated case "
                "directory is keyed by id and is case-insensitive on Windows and macOS, so one "
                "would silently replace the other"
            )
        seen[key] = case_id
        files.update(case_files(spec, case, agents=agents, **options))  # type: ignore[arg-type]
    return files


def manifest(spec: Mapping[str, object], files: Mapping[str, str]) -> str:
    """A record written beside the generated cases saying what produced them.

    The directory is disposable and git-ignored, so anyone who finds one needs it to say where it
    came from before they trust or edit it.
    """
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
