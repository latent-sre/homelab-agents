"""The one command line for the fleet's instruments: `python -m fleet <verb>`.

Every verb shares `--root` and `--json`, and every verb's exit code comes from the kernel's
ladder (`fleet.diagnostics`), so a caller never has to learn one instrument's private codes.
Phase 1 ships `validate`; later phases add the generator, the doctor, and the probes as verbs
and reduce the scripts under `scripts/` to shims.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fleet import rules
from fleet.findings import Report
from fleet.rules.inventory import render_inventory, write_inventory
from fleet.snapshot import Fleet

DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def validate(
    root: Path,
    *,
    groups: tuple[str, ...] | None = None,
    skip: tuple[str, ...] = (),
) -> Report:
    """Run the rule groups in the legacy `validate_repo` order and return a `Report`."""
    fleet = Fleet.load(root)
    selected = rules.REPO_GROUP_ORDER if groups is None else groups
    return Report(root, rules.run(fleet, groups=selected, skip=skip))


def _validate_command(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    skip = ("adapters.generated",) if args.no_adapters else ()
    # Inventory is checked last and only on an otherwise clean tree, and `--write-inventory`
    # repairs it first: a drifted inventory on a broken tree would be regenerated from broken
    # names, so the order is load-bearing (the legacy validator's contract).
    report = validate(
        root, groups=tuple(g for g in rules.REPO_GROUP_ORDER if g != "inventory"), skip=skip
    )
    findings = list(report.findings)
    if not findings:
        fleet = Fleet.load(root)
        expected = render_inventory(fleet.agent_names, fleet.skill_names)
        if args.write_inventory:
            try:
                write_inventory(root / "README.md", expected)
            except ValueError as exc:
                from fleet.findings import Finding

                findings.append(Finding("inventory", str(exc), root / "README.md"))
        if not findings:
            findings.extend(rules.run(fleet, groups=("inventory",)))
    report = Report(root, findings)

    if args.json:
        print(report.render_json())
    elif args.github:
        print(report.render_github())
    else:
        if report.findings:
            print(report.render_human(), file=sys.stderr)
        else:
            fleet = Fleet.load(root)
            print(
                f"Validated {len(fleet.agent_names)} agents and {len(fleet.skill_names)} skills; "
                f"inventory is current."
            )
    return report.exit_status()


def _rules_command(args: argparse.Namespace) -> int:
    for entry in rules.rules():
        print(f"{entry.id:36} [{entry.group}] {entry.why}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fleet", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="verb", required=True)

    validate_parser = sub.add_parser(
        "validate", help="validate the canonical fleet and its adapters"
    )
    validate_parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository root")
    validate_parser.add_argument("--json", action="store_true", help="print the report as JSON")
    validate_parser.add_argument(
        "--github", action="store_true", help="print GitHub Actions annotations, one per finding"
    )
    validate_parser.add_argument(
        "--write-inventory",
        action="store_true",
        help="rewrite the README inventory before checking it",
    )
    validate_parser.add_argument(
        "--no-adapters",
        action="store_true",
        help="skip the generated-adapter byte comparison (the slowest rule; never skipped in CI)",
    )
    validate_parser.set_defaults(handler=_validate_command)

    rules_parser = sub.add_parser("rules", help="list every registered rule with its group and why")
    rules_parser.set_defaults(handler=_rules_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)
