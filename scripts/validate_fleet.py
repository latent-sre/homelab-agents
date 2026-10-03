#!/usr/bin/env python3
"""Validate this repository's canonical agent and skill definitions.

The rules live in `fleet/rules/` as pure functions over one `fleet.snapshot.Fleet`, judged
against the data in `fleet/policy.toml`; this script is the command-line entry the recipe and
CI run, and the compatibility surface the generator and the tests import. Every
`validate_*` function here runs the corresponding rule group and returns the legacy
`list[str]` of messages. `python -m fleet validate` is the same run with structured output.

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

from fleet import modules, rules  # noqa: E402
from fleet.findings import texts  # noqa: E402
from fleet.frontmatter import flow_scalar_defect as _flow_scalar_defect  # noqa: E402,F401
from fleet.frontmatter import parse_lines as parse_frontmatter_lines  # noqa: E402,F401
from fleet.frontmatter import span as frontmatter_span  # noqa: E402,F401
from fleet.frontmatter import split_tools  # noqa: E402,F401
from fleet.fs import read_text  # noqa: E402
from fleet.policy import POLICY  # noqa: E402
from fleet.references import parse_frontmatter  # noqa: E402,F401
from fleet.rules import inventory as _inventory  # noqa: E402
from fleet.rules import skills as _skills  # noqa: E402
from fleet.snapshot import Fleet  # noqa: E402

# --- vocabularies, bound from fleet/policy.toml (the rationale for each lives beside it) --------
KNOWN_AGENT_FIELDS = set(POLICY.known_agent_fields)
KNOWN_SKILL_FIELDS = set(POLICY.known_skill_fields)
WRITE_TOOLS = set(POLICY.write_tools)
INVENTORY_RE = _inventory.INVENTORY_RE
load_module_by_content = modules.load_module_by_content
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


def validate_inventory(root: Path, expected: str) -> list[str]:
    return texts(_inventory.inventory_findings(root, expected))


def bundle_references(skill_file: Path) -> set[str]:
    return _skills.bundle_references(read_text(skill_file))


def load_guard(root: Path):
    """Import scripts/readonly-guard.py by path -- the hyphen makes it un-importable by name.

    This EXECUTES the guard (content-keyed, see fleet/modules.py). TEST-ONLY: nothing in the
    validator or the generator calls it. The rules read the rosters as data, and the adapter
    generator moved onto that same reader when `hooks/hooks.json` became generated output -- it
    renders a SHIPPED artifact, so importing the tree's own hook to learn who it guards is exactly
    the execution the guard exists to prevent. What is left is the tests that exercise the guard's
    behaviour, which need the real module. Do not reintroduce a production caller (Codex, PR #193:
    this docstring still named the generator, and a script docstring is read as its contract).
    """
    source = root / "scripts" / "readonly-guard.py"
    module = load_module_by_content(source, "readonly_guard")
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
