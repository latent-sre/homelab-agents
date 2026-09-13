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


REGISTRY: dict[str, Rule] = {}
_ORDER: list[str] = []


def rule(id: str, *, group: str, why: str) -> Callable[[RuleFunction], RuleFunction]:
    """Register a rule. Ids are unique; a duplicate is a programming error, not an override."""

    def register(function: RuleFunction) -> RuleFunction:
        if id in REGISTRY:
            raise ValueError(f"rule id registered twice: {id}")
        REGISTRY[id] = Rule(id, group, why, function)
        _ORDER.append(id)
        return function

    return register


def rules(*, groups: Iterable[str] | None = None) -> list[Rule]:
    wanted = None if groups is None else set(groups)
    return [REGISTRY[i] for i in _ORDER if wanted is None or REGISTRY[i].group in wanted]


def run(
    fleet: Fleet, *, groups: Iterable[str] | None = None, skip: Iterable[str] = ()
) -> list[Finding]:
    """Run the selected rule groups in registration order and concatenate their findings."""
    skipped = set(skip)
    findings: list[Finding] = []
    for entry in rules(groups=groups):
        if entry.id in skipped:
            continue
        findings.extend(entry.run(fleet))
    return findings


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
