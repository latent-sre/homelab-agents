#!/usr/bin/env python3
"""Validate this repository's canonical agent and skill definitions.

The rules live in `fleet/rules/` as pure functions over one `fleet.snapshot.Fleet`, judged
against the data in `fleet/policy.toml`; this script is the command-line entry the recipe and
CI run, and the compatibility surface the generator, the doctor, and the tests import. Every
`validate_*` function here runs the corresponding rule group and returns the legacy
`list[str]` of messages, byte-identical to what the rules produced before they moved. The
vocabularies are bound from the policy so a caller that reads `FLEET_TOOLS` here sees the one
table the rules use. `python -m fleet validate` is the same run with structured output.

The validator intentionally uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)  # `import fleet` when run as `python3 scripts/<name>.py`

# The generator owns the generated-root set. Its validator access is lazy, so importing it here is
# acyclic while letting both package imports and direct script execution resolve the same source.
if __package__:
    from . import generate_platform_adapters  # noqa: E402,F401
else:
    import generate_platform_adapters  # noqa: E402,F401

import fleet_records  # noqa: E402  (sibling module; scripts/ is not a package)
from fleet_records import (  # noqa: E402,F401  (re-exported: the generator and tests reach them here)
    LIST_ITEM_RE,
    NAME_RE,
    TOP_LEVEL_KEY_RE,
    definition_markdown_files,
    frontmatter_span,
    is_runtime_byproduct,
    parse_frontmatter,
    parse_frontmatter_lines,
    read_text,
    split_tools,
)

from fleet import modules, rules  # noqa: E402
from fleet.findings import texts  # noqa: E402
from fleet.policy import POLICY  # noqa: E402
from fleet.rules import agents as _agents  # noqa: E402
from fleet.rules import guide as _guide  # noqa: E402
from fleet.rules import inventory as _inventory  # noqa: E402
from fleet.rules import plugin as _plugin  # noqa: E402
from fleet.rules import references as _references  # noqa: E402
from fleet.rules import routing as _routing  # noqa: E402
from fleet.rules import skills as _skills  # noqa: E402
from fleet.rules import workflows as _workflows  # noqa: E402
from fleet.rules.adapters import load_platform_adapter_generator  # noqa: E402,F401
from fleet.snapshot import TOOL_ENTRY_RE, Fleet  # noqa: E402

# --- vocabularies, bound from fleet/policy.toml (the rationale for each lives beside it) --------
ALIAS_MODELS = set(POLICY.model_aliases)
FULL_MODEL_ID_RE = _agents.FULL_MODEL_ID_RE
KNOWN_AGENT_FIELDS = set(POLICY.known_agent_fields)
KNOWN_SKILL_FIELDS = set(POLICY.known_skill_fields)
PLUGIN_INERT_AGENT_FIELDS = set(POLICY.plugin_inert_agent_fields)
WRITE_TOOLS = set(POLICY.write_tools)
RUNTIME_TOOLS = set(POLICY.runtime_tools)
FLEET_TOOLS = set(POLICY.fleet_tools)
EVIDENCE_MCP_TOOLS = set(POLICY.evidence_mcp_tools)
FLEET_MCP_TOOLS = set(POLICY.fleet_mcp_tools)
LOCAL_REPOSITORY_TOOLS = set(POLICY.tool_groups["local_repository"])
EXTERNAL_RESEARCH_TOOLS = set(POLICY.tool_groups["external_research"])
REQUIRED_AGENT_TOOLS = {name: set(role.required) for name, role in POLICY.roles.items()}
FORBIDDEN_AGENT_TOOLS = {name: set(role.forbidden) for name, role in POLICY.roles.items()}
SUBAGENT_UNAVAILABLE_TOOLS = set(POLICY.subagent_unavailable_tools)
MCP_EXACT_TOOL_RE = _agents.MCP_EXACT_TOOL_RE
MCP_SERVER_GRANT_RE = _agents.MCP_SERVER_GRANT_RE
EVIDENCE_LABEL_STEMS = POLICY.evidence_label_stems
EVIDENCE_LABEL_RE = _agents.EVIDENCE_LABEL_RE
WORKFLOW_EVIDENCE_ENUM = POLICY.workflow_evidence_enum
WORKFLOW_EVIDENCE_ENUM_RE = _workflows.WORKFLOW_EVIDENCE_ENUM_RE
PACKET_HEADING_RE = _agents.PACKET_HEADING_RE
PERISHABLE_TOKENS = dict(POLICY.perishable_tokens)
GUIDE_IMPORT = POLICY.guide_import
PROGRAM_DOC = POLICY.program_doc
PROSE_SCALAR_FIELDS = POLICY.prose_scalar_fields
BUNDLE_REF_RE = _skills.BUNDLE_REF_RE
INVENTORY_RE = _inventory.INVENTORY_RE
INLINE_CODE_RE = _references.INLINE_CODE_RE
GUIDE_PATH_TOKEN_RE = _guide.GUIDE_PATH_TOKEN_RE
_CASE_BLOCK_RE = _plugin.CASE_BLOCK_RE
_flow_scalar_defect = fleet_records._frontmatter.flow_scalar_defect
_blank_js_strings_and_comments = _workflows._blank_js_strings_and_comments
_META_DECLARATION_RE = _workflows._META_DECLARATION_RE
load_module_by_content = modules.load_module_by_content
_execute_source = modules.execute_source
render_inventory = _inventory.render_inventory
replace_inventory = _inventory.replace_inventory
write_inventory = _inventory.write_inventory


# --- rule groups under their legacy names ---------------------------------------------------


def _run(root: Path, *groups: str, skip: tuple[str, ...] = ()) -> list[str]:
    return texts(rules.run(Fleet.load(root), groups=groups, skip=skip))


def validate_agents(root: Path) -> tuple[list[str], list[str]]:
    fleet = Fleet.load(root)
    return texts(rules.run(fleet, groups=("agents",))), fleet.agent_names


def validate_skills(root: Path) -> tuple[list[str], list[str]]:
    fleet = Fleet.load(root)
    return texts(rules.run(fleet, groups=("skills",))), fleet.skill_names


def validate_yaml_scalar_quoting(root: Path) -> list[str]:
    return _run(root, "scalars")


def validate_plugin(root: Path, agent_names: list[str], skill_names: list[str]) -> list[str]:
    return _run(root, "plugin")


def validate_platform_adapters(root: Path) -> list[str]:
    return _run(root, "adapters")


def validate_agent_guide(root: Path) -> list[str]:
    return _run(root, "guide")


def validate_routing_clusters(
    root: Path, agent_names: list[str], skill_names: list[str]
) -> list[str]:
    # Honors the caller's component names, as the legacy signature promised: a test may grade a
    # synthetic cluster against names the tree under validation does not carry.
    return [text for text, _ in _routing._routing_issues(root, agent_names, skill_names)]


def validate_host_conformance_manifest(root: Path) -> list[str]:
    return _run(root, "conformance")


def validate_bare_skill_references(root: Path, skill_names: list[str]) -> list[str]:
    return texts(_references.bare_skill_references(Fleet.load(root)))


def validate_perishable_tokens(root: Path) -> list[str]:
    return texts(_references.perishable_tokens(Fleet.load(root)))


validate_workflow_evidence_enums = _workflows.validate_workflow_evidence_enums
validate_workflow_line_endings = _workflows.validate_workflow_line_endings
validate_workflow_meta_contract = _workflows.validate_workflow_meta_contract
validate_workflow_host_boundary = _workflows.validate_workflow_host_boundary


def validate_inventory(root: Path, expected: str) -> list[str]:
    return texts(_inventory.inventory_findings(root, expected))


def bundle_references(skill_file: Path) -> set[str]:
    return _skills.bundle_references(read_text(skill_file))


def agent_tool_bases(path: Path) -> set[str]:
    fields = parse_frontmatter(path) or {}
    bases: set[str] = set()
    for entry in split_tools(fields.get("tools", "")):
        match = TOOL_ENTRY_RE.match(entry)
        if match:
            bases.add(match.group(1))
    return bases


def hook_commands(root: Path) -> list[str]:
    return list(Fleet.load(root).hook_commands)


def hook_command_for(root: Path, script: str) -> str | None:
    return Fleet.load(root).hook_command_for(script)


def hook_command(root: Path) -> str | None:
    return hook_command_for(root, "readonly-guard.py")


def load_guard(root: Path):
    """Import scripts/readonly-guard.py by path -- the hyphen makes it un-importable by name.

    This EXECUTES the guard (content-keyed, see fleet/modules.py). The validator's own rules no
    longer need this: they read the rosters as data. It remains for the tests that exercise the
    guard's behaviour and for the generator's roster lookup.
    """
    source = root / "scripts" / "readonly-guard.py"
    module = load_module_by_content(source, "readonly_guard")
    if module is None:
        raise ImportError(f"cannot load {source}")
    return module


def load_gate(root: Path):
    """Import scripts/live-effect-gate.py by path -- the hyphen makes it un-importable by name."""
    source = root / "scripts" / "live-effect-gate.py"
    module = load_module_by_content(source, "live_effect_gate")
    if module is None:
        raise ImportError(f"cannot load {source}")
    return module


def validate_repo(
    root: Path, *, check_inventory: bool = True, check_adapters: bool = True
) -> tuple[list[str], list[str], list[str]]:
    fleet = Fleet.load(root)
    groups = [g for g in rules.REPO_GROUP_ORDER if g != "inventory" or check_inventory]
    # The adapter byte-compare is 59% of a validation run (profiled 2026-08-08) and independent
    # of every other rule, so a caller validating a deliberate non-adapter mutation may skip it.
    # The command line never does: `main` always runs the full set.
    skip = () if check_adapters else ("adapters.generated",)
    issues = texts(rules.run(fleet, groups=groups, skip=skip))
    return issues, fleet.agent_names, fleet.skill_names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the validator's parent repository)",
    )
    parser.add_argument(
        "--write-inventory",
        action="store_true",
        help="rewrite the generated README inventory before validating",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    issues, agent_names, skill_names = validate_repo(root, check_inventory=False)
    if args.write_inventory and not issues:
        try:
            write_inventory(root / "README.md", render_inventory(agent_names, skill_names))
        except ValueError as exc:
            issues.append(str(exc))

    if not issues:
        issues.extend(validate_inventory(root, render_inventory(agent_names, skill_names)))

    if issues:
        print("Fleet validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(agent_names)} agents and {len(skill_names)} skills; inventory is current."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
