"""The rule registry: every validator rule is a pure function over one `Fleet` snapshot.

A rule is registered with a stable id (`<artifact>.<subject>[.<aspect>]`), the artifact group
its legacy caller ran, and a one-sentence "why": the silent failure it exists to catch. The id
is the handle a consumer filters by and a test asserts on; the why is what a reader needs before
weakening the rule. Rules return `Finding`s whose `text` keeps the message register the fleet
already relies on.

Ordering is deliberate and stable: groups run in the caller's sequence, rules within a group in
registration order, and the findings of a run of definition-scoped rules are re-sequenced
definition-major (every finding about `agents/a.md`, in rule order, before any about
`agents/b.md`), which is how the legacy per-definition loops emitted them. A caller comparing
two reports therefore sees the same sequence the fleet has always produced. Rules self-gate on
the snapshot (no plugin manifest, no `workflows/`) rather than on the caller, so a synthetic
fixture under `tests/fixtures/` makes no claims it does not carry.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from fleet.findings import Finding
from fleet.snapshot import Fleet

RuleFunction = Callable[[Fleet], list[Finding]]

# A rule is scoped to the fleet (one verdict about the tree, such as a missing directory or a
# duplicate name) or to a definition (a verdict per agent or skill). The scope decides how the
# runner sequences findings; see `run`.
SCOPES = ("fleet", "definition")


@dataclass(frozen=True)
class Rule:
    id: str
    group: str
    why: str
    run: RuleFunction
    # Every finding id this rule may emit. A rule that keeps several legacy checks together for
    # their shared early-return semantics (the plugin pass) still declares each id it produces,
    # so a consumer can discover, select, or skip any id through the registry.
    emits: tuple[str, ...] = ()
    scope: str = "fleet"

    @property
    def emitted_ids(self) -> tuple[str, ...]:
        return self.emits or (self.id,)


REGISTRY: dict[str, Rule] = {}
_ORDER: list[str] = []

# The legacy `validate_repo` sequence, by group, so the wrappers and the CLI agree on order. It
# is also the closed vocabulary of groups: registration and selection both refuse a name outside
# it.
REPO_GROUP_ORDER: tuple[str, ...] = (
    "agents",
    "skills",
    "scalars",
    "plugin",
    "adapters",
    "guide",
    "routing",
    "conformance",
    "references",
    "workflows",
    "inventory",
)


def rule(
    id: str, *, group: str, why: str, emits: tuple[str, ...] = (), scope: str = "fleet"
) -> Callable[[RuleFunction], RuleFunction]:
    """Register a rule. Ids are unique; a duplicate is a programming error, not an override."""

    def register(function: RuleFunction) -> RuleFunction:
        if id in REGISTRY:
            raise ValueError(f"rule id registered twice: {id}")
        if emits and id not in emits:
            raise ValueError(f"rule {id} must list itself among the ids it emits")
        if scope not in SCOPES:
            raise ValueError(f"rule {id} has unknown scope {scope!r}; expected one of {SCOPES}")
        if group not in REPO_GROUP_ORDER:
            # A mistyped group would register fine and then never be visited by the default
            # traversal: a rule that exists, passes every registry test, and runs nowhere.
            raise ValueError(
                f"rule {id} names unknown group {group!r}; expected one of {REPO_GROUP_ORDER}"
            )
        REGISTRY[id] = Rule(id, group, why, function, emits, scope)
        _ORDER.append(id)
        return function

    return register


def rules(*, groups: Iterable[str] | None = None) -> list[Rule]:
    """Rules in run order: the requested groups in the requested sequence, and within a group in
    registration order. A set of groups would lose the sequence, and registration order across
    groups is an import-dependency accident (a module that imports another registers the other's
    rules first), so the group sequence is the only order a caller may rely on."""
    sequence = tuple(REPO_GROUP_ORDER if groups is None else groups)
    unknown = [group for group in sequence if group not in REPO_GROUP_ORDER]
    if unknown:
        # A caller asking for a group that does not exist would otherwise get an empty, clean
        # report that ran no check at all.
        raise ValueError(f"unknown rule group(s) {unknown}; expected from {REPO_GROUP_ORDER}")
    ordered: list[Rule] = []
    for group in sequence:
        ordered.extend(REGISTRY[i] for i in _ORDER if REGISTRY[i].group == group)
    return ordered


def emitted_ids() -> set[str]:
    return {emitted for entry in REGISTRY.values() for emitted in entry.emitted_ids}


def run(
    fleet: Fleet, *, groups: Iterable[str] | None = None, skip: Iterable[str] = ()
) -> list[Finding]:
    """Run the selected groups in sequence and concatenate their findings.

    `skip` names rule ids or emitted ids: a skipped rule id is not run at all; a skipped emitted
    id of a multi-check rule has its findings dropped after the run.

    Within a group, each maximal run of consecutive definition-scoped rules is re-sequenced
    definition-major: the legacy validators looped over definitions and applied every check to
    one before moving to the next, and a consumer diffing two reports (or a human reading one)
    relies on every finding about one file sitting together. Rule order is kept within a
    definition, and emission order within a rule. Fleet-scoped rules keep their place."""
    skipped = set(skip)
    findings: list[Finding] = []
    homes = _definition_homes(fleet)
    batch: list[tuple[int, int, Finding]] = []
    previous_group: str | None = None

    def flush() -> None:
        batch.sort(key=lambda item: (_home_rank(item[2].path, homes), item[0], item[1]))
        findings.extend(item[2] for item in batch)
        batch.clear()

    for index, entry in enumerate(rules(groups=groups)):
        if entry.group != previous_group or entry.scope != "definition":
            flush()
            previous_group = entry.group
        if entry.id in skipped:
            continue
        emitted = [f for f in entry.run(fleet) if f.rule not in skipped]
        if entry.scope == "definition":
            batch.extend((index, position, f) for position, f in enumerate(emitted))
        else:
            findings.extend(emitted)
    flush()
    return findings


def _definition_homes(fleet: Fleet) -> dict[Path, int]:
    """Each definition's home path -- the agent file, or the skill directory -- ranked in the
    order the legacy loops walked them. A skill directory with no SKILL.md is a home too: its
    "missing SKILL.md" finding sorts among its siblings, as it always did."""
    agent_homes = [agent.path for agent in fleet.agents]
    skill_homes = sorted(
        [skill.directory for skill in fleet.skills] + list(fleet.skill_dirs_without_skill_md)
    )
    return {home: rank for rank, home in enumerate(agent_homes + skill_homes)}


def _home_rank(path: Path | None, homes: dict[Path, int]) -> int:
    """The rank of the definition a finding belongs to: its path or the nearest ancestor that
    is a home (an orphaned `references/x.md` belongs to its skill). A finding outside every
    definition sorts after them all, which is where the legacy loops put post-loop verdicts."""
    if path is not None:
        for candidate in (path, *path.parents):
            if candidate in homes:
                return homes[candidate]
    return len(homes)


# Importing the rule modules registers them. Order matters: it is the legacy validate_repo order.
from fleet.rules import (  # noqa: E402,F401
    adapters,
    agents,
    conformance,
    guide,
    inventory,
    plugin,
    references,
    routing,
    scalars,
    skills,
    workflows,
)
