"""Load `fleet/policy.toml` into one frozen `Policy` the rules judge against.

The TOML is the source; this module only types it and expands the `@group` references a role
rule may use, so a vocabulary is declared exactly once. Nothing here judges a definition.

The policy that governs a run is the EXECUTING checkout's, exactly as the rules that consume it
are: rules and policy are one versioned unit, and a validator that mixed its own rules with a
target tree's tables would judge that tree by a vocabulary its rules were never written against
(a table the target lacks would be a load error, not a verdict). This is the contract the legacy
validator had, where the same tables were module constants; the tree under validation supplies
its generator and its conformance schema, never the validator's policy.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

POLICY_PATH = Path(__file__).with_name("policy.toml")


class PolicyError(ValueError):
    """The policy file is malformed: a missing table, a bad type, or an unknown `@group`."""


@dataclass(frozen=True)
class RolePolicy:
    name: str
    required: frozenset[str]
    forbidden: frozenset[str]


@dataclass(frozen=True)
class Policy:
    checked: str
    cli: str
    model_aliases: frozenset[str]
    known_agent_fields: frozenset[str]
    plugin_inert_agent_fields: frozenset[str]
    known_skill_fields: frozenset[str]
    prose_scalar_fields: tuple[str, ...]
    runtime_tools: frozenset[str]
    fleet_tools: frozenset[str]
    write_tools: frozenset[str]
    subagent_unavailable_tools: frozenset[str]
    tool_groups: Mapping[str, frozenset[str]]
    roles: Mapping[str, RolePolicy]
    evidence_label_stems: tuple[str, ...]
    perishable_tokens: Mapping[str, str]
    guide_import: str
    program_doc: str
    conformance_required_hosts: frozenset[str]
    conformance_required_baseline_model: str

    @property
    def evidence_mcp_tools(self) -> frozenset[str]:
        return self.tool_groups["evidence_mcp"]

    @property
    def fleet_mcp_tools(self) -> frozenset[str]:
        return self.evidence_mcp_tools

    @property
    def workflow_evidence_enum(self) -> tuple[str, ...]:
        # ("verified", "sourced", "unverified"), derived so the triad has one authoring point.
        return tuple(stem.split("[", 1)[1].split("]", 1)[0] for stem in self.evidence_label_stems)


def _strings(table: Mapping[str, object], key: str, where: str) -> list[str]:
    value = table.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PolicyError(f"{where}.{key} must be a list of strings")
    return list(value)


def _string(table: Mapping[str, object], key: str, where: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise PolicyError(f"{where}.{key} must be a non-empty string")
    return value


def _table(document: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise PolicyError(f"policy table [{key}] is missing")
    return value


def _expand(
    entries: Iterable[str], groups: Mapping[str, frozenset[str]], where: str
) -> frozenset[str]:
    """Replace each `@group` reference with the group's members; an unknown group is an error,
    because a typo'd reference would otherwise silently grant or forbid nothing."""
    expanded: set[str] = set()
    for entry in entries:
        if entry.startswith("@"):
            group = groups.get(entry[1:])
            if group is None:
                raise PolicyError(f"{where} references unknown tool group {entry!r}")
            expanded |= group
        else:
            expanded.add(entry)
    return frozenset(expanded)


def load(path: Path = POLICY_PATH) -> Policy:
    with Path(path).open("rb") as stream:
        document = tomllib.load(stream)

    meta = _table(document, "meta")
    models = _table(document, "models")
    agent_fm = _table(document, "agent_frontmatter")
    skill_fm = _table(document, "skill_frontmatter")
    tools = _table(document, "tools")
    raw_groups = tools.get("groups")
    if not isinstance(raw_groups, dict):
        raise PolicyError("policy table [tools.groups] is missing")
    # Groups may reference earlier groups; resolve in declaration order so a forward reference is
    # a loud error rather than a silent empty set.
    groups: dict[str, frozenset[str]] = {}
    for name in raw_groups:
        groups[name] = _expand(
            _strings(raw_groups, name, "tools.groups"), groups, f"tools.groups.{name}"
        )

    roles: dict[str, RolePolicy] = {}
    for index, entry in enumerate(document.get("roles", []), start=1):
        if not isinstance(entry, dict):
            raise PolicyError(f"roles[{index}] must be a table")
        name = _string(entry, "name", f"roles[{index}]")
        if name in roles:
            # A second table with the same name would silently replace the first role's trust
            # boundary while the loader and the validator stay green.
            raise PolicyError(f"roles[{index}] repeats the role name {name!r}")
        roles[name] = RolePolicy(
            name,
            _expand(_strings(entry, "required", f"roles.{name}"), groups, f"roles.{name}.required"),
            _expand(
                _strings(entry, "forbidden", f"roles.{name}"), groups, f"roles.{name}.forbidden"
            ),
        )

    evidence = _table(document, "evidence")
    guide = _table(document, "guide")
    conformance = _table(document, "conformance")
    perishable = document.get("perishable_tokens", {})
    if not isinstance(perishable, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in perishable.items()
    ):
        raise PolicyError("policy table [perishable_tokens] must map strings to strings")

    return Policy(
        checked=_string(meta, "checked", "meta"),
        cli=_string(meta, "cli", "meta"),
        model_aliases=frozenset(_strings(models, "aliases", "models")),
        known_agent_fields=frozenset(_strings(agent_fm, "known", "agent_frontmatter")),
        plugin_inert_agent_fields=frozenset(
            _strings(agent_fm, "plugin_inert", "agent_frontmatter")
        ),
        known_skill_fields=frozenset(_strings(skill_fm, "known", "skill_frontmatter")),
        prose_scalar_fields=tuple(_strings(skill_fm, "prose_scalar_fields", "skill_frontmatter")),
        runtime_tools=frozenset(_strings(tools, "runtime", "tools")),
        fleet_tools=frozenset(_strings(tools, "fleet", "tools")),
        write_tools=frozenset(_strings(tools, "write", "tools")),
        subagent_unavailable_tools=frozenset(_strings(tools, "subagent_unavailable", "tools")),
        # Read-only views: a consumer that mutated a mapping in place would make every later
        # validation diverge from the file the policy claims to be, with nothing to notice.
        tool_groups=MappingProxyType(dict(groups)),
        roles=MappingProxyType(dict(roles)),
        evidence_label_stems=tuple(_strings(evidence, "stems", "evidence")),
        perishable_tokens=MappingProxyType(dict(perishable)),
        guide_import=_string(guide, "import_line", "guide"),
        program_doc=_string(guide, "program_doc", "guide"),
        conformance_required_hosts=frozenset(
            _strings(conformance, "required_static_hosts", "conformance")
        ),
        conformance_required_baseline_model=_string(
            conformance, "required_baseline_model", "conformance"
        ),
    )


POLICY = load()
