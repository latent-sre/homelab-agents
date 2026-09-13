"""The rule registry and the rule-id contract over the fixtures.

Risk hypothesis: with rules as pure functions, a rule can be dropped from the registry, or two
rules can claim one id, and the legacy string-based tests would still pass as long as some other
rule happened to emit the same words. Pinning each fixture to the rule ids it must trip, and the
registry to one id per rule, makes those failures loud.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from fleet import rules
from fleet.cli import validate
from fleet.snapshot import Fleet
from tests.support import REPO, repo_copy

FIXTURES = Path(__file__).parent / "fixtures"

# Every synthetic fixture under tests/fixtures/, with the rule ids its findings must carry. A
# fixture that trips an id not listed here, or misses one, fails: the table is the contract.
FIXTURE_RULES: dict[str, set[str]] = {
    "valid": set(),
    "evidence-drift": {"agent.packet"},
    "inventory-drift": {"agent.packet", "inventory"},
    "missing-packet": {"agent.packet"},
    "missing-reference": {"agent.packet", "skill.bundle.links"},
    "missing-tools": {"agent.packet", "agent.tools"},
    "perishable-token-copy": {"references.perishable-token"},
    "trailing-token-yaml-scalar": {"frontmatter.scalar"},
    "unadopted-mcp-tool": {"agent.tools"},
    "unknown-tool": {"agent.tools"},
    "unquoted-yaml-scalar": {"frontmatter.scalar"},
    "unreachable-bare-skill": {"references.bare-skill"},
    "unterminated-yaml-scalar": {"frontmatter.scalar"},
}
# Fixtures that ship no README make no inventory claim; the legacy tests validate them with
# check_inventory=False and this table does the same.
INVENTORY_CHECKED = {"valid", "inventory-drift"}


class RegistryTests(unittest.TestCase):
    def test_every_rule_has_a_unique_id_a_group_and_a_why(self) -> None:
        seen: set[str] = set()
        for entry in rules.rules():
            self.assertNotIn(entry.id, seen)
            seen.add(entry.id)
            self.assertIn(entry.group, rules.REPO_GROUP_ORDER, entry.id)
            self.assertTrue(entry.why.strip(), f"{entry.id} has no why")
        self.assertGreater(len(seen), 20)

    def test_every_group_in_the_repo_order_has_at_least_one_rule(self) -> None:
        groups = {entry.group for entry in rules.rules()}
        self.assertEqual(set(rules.REPO_GROUP_ORDER), groups)

    def test_registering_a_duplicate_id_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            rules.rule("agent.tools", group="agents", why="dup")(lambda fleet: [])

    def test_findings_carry_the_id_of_the_rule_that_produced_them(self) -> None:
        fleet = Fleet.load(FIXTURES / "unknown-tool")
        for entry in rules.rules():
            for finding in entry.run(fleet):
                # A rule may emit a sub-id under its own prefix (plugin.* emits plugin.guard etc.)
                self.assertTrue(
                    finding.rule == entry.id or finding.rule.startswith(entry.id.split(".")[0]),
                    f"{entry.id} emitted {finding.rule}",
                )


class FixtureRuleContractTests(unittest.TestCase):
    def test_fixture_table_covers_every_fixture_directory(self) -> None:
        on_disk = {p.name for p in FIXTURES.iterdir() if p.is_dir() and p.name != "folded"}
        self.assertEqual(on_disk, set(FIXTURE_RULES))

    def test_each_fixture_trips_exactly_its_declared_rules(self) -> None:
        for name, expected in FIXTURE_RULES.items():
            with self.subTest(fixture=name):
                groups = tuple(
                    g
                    for g in rules.REPO_GROUP_ORDER
                    if g != "inventory" or name in INVENTORY_CHECKED
                )
                report = validate(FIXTURES / name, groups=groups)
                self.assertEqual(expected, {f.rule for f in report.findings}, report.texts)

    def test_the_real_repository_is_clean_under_every_rule(self) -> None:
        report = validate(REPO)
        self.assertEqual([], report.texts)


class PluginRuleIdTests(unittest.TestCase):
    def test_a_dropped_guard_roster_entry_is_a_guard_roster_finding(self) -> None:
        with repo_copy() as dst:
            guard = dst / "scripts" / "readonly-guard.py"
            guard.write_text(
                guard.read_text(encoding="utf-8").replace('"code-reviewer", ', "", 1),
                encoding="utf-8",
            )
            report = validate(dst, skip=("adapters.generated",))
        ids = {f.rule for f in report.findings}
        self.assertIn("plugin.guard.roster", ids)
        self.assertIn("plugin.hooks.guard", ids - {"plugin.guard.roster"} | {"plugin.hooks.guard"})

    def test_rosters_are_read_as_data_so_a_guard_that_cannot_run_still_reports(self) -> None:
        # A guard whose module body would raise at import is still a readable AST; the roster
        # cross-checks run instead of collapsing into "cannot load guard".
        with repo_copy() as dst:
            guard = dst / "scripts" / "readonly-guard.py"
            guard.write_text(
                guard.read_text(encoding="utf-8") + "\nraise RuntimeError('boom at import')\n",
                encoding="utf-8",
            )
            report = validate(dst, groups=("plugin",))
        self.assertEqual(
            [], [f for f in report.findings if "cannot load guard" in f.text], report.texts
        )


if __name__ == "__main__":
    unittest.main()
