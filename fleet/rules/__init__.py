"""The rule registry: every validator rule is a pure function over one `Fleet` snapshot.

A rule is registered with a stable id (`<artifact>.<subject>[.<aspect>]`), the artifact group
its legacy caller ran, and a one-sentence "why": the silent failure it exists to catch. The id
is the handle a consumer filters by and a test asserts on; the why is what a reader needs before
weakening the rule. Rules return `Finding`s whose `text` keeps the message register the fleet
already relies on.

Ordering is deliberate and stable: rules run in registration order, grouped exactly as the
legacy `validate_*` functions ran them, so a caller comparing two reports sees the same
sequence. Rules self-gate on the snapshot (no plugin manifest, no `workflows/`) rather than on
the caller, so a synthetic fixture under `tests/fixtures/` makes no claims it does not carry.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from fleet.findings import Finding
from fleet.snapshot import Fleet

RuleFunction = Callable[[Fleet], list[Finding]]


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

    @property
    def emitted_ids(self) -> tuple[str, ...]:
        return self.emits or (self.id,)


REGISTRY: dict[str, Rule] = {}
_ORDER: list[str] = []


def rule(
    id: str, *, group: str, why: str, emits: tuple[str, ...] = ()
) -> Callable[[RuleFunction], RuleFunction]:
    """Register a rule. Ids are unique; a duplicate is a programming error, not an override."""

    def register(function: RuleFunction) -> RuleFunction:
        if id in REGISTRY:
            raise ValueError(f"rule id registered twice: {id}")
        if emits and id not in emits:
            raise ValueError(f"rule {id} must list itself among the ids it emits")
        REGISTRY[id] = Rule(id, group, why, function, emits)
        _ORDER.append(id)
        return function

    return register


def rules(*, groups: Iterable[str] | None = None) -> list[Rule]:
    """Rules in run order: the requested groups in the requested sequence, and within a group in
    registration order. A set of groups would lose the sequence, and registration order across
    groups is an import-dependency accident (a module that imports another registers the other's
    rules first), so the group sequence is the only order a caller may rely on."""
    sequence = tuple(REPO_GROUP_ORDER if groups is None else groups)
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
    id of a multi-check rule has its findings dropped after the run."""
    skipped = set(skip)
    findings: list[Finding] = []
    for entry in rules(groups=groups):
        if entry.id in skipped:
            continue
        findings.extend(f for f in entry.run(fleet) if f.rule not in skipped)
    return findings


# The legacy `validate_repo` sequence, by group, so the wrappers and the CLI agree on order.
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
