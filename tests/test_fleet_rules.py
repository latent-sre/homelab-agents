"""The rule registry and the rule-id contract over the fixtures.

Risk hypothesis: with rules as pure functions, a rule can be dropped from the registry, or two
rules can claim one id, and the legacy string-based tests would still pass as long as some other
rule happened to emit the same words. Pinning each fixture to the rule ids it must trip, and the
registry to one id per rule, makes those failures loud.
"""

from __future__ import annotations

import re
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

    def test_every_emitted_id_is_declared_on_its_rule(self) -> None:
        # A multi-check rule declares each id it emits, so every id a report can carry is
        # discoverable through the registry and selectable through run(skip=...).
        with repo_copy() as dst:
            guard = dst / "scripts" / "readonly-guard.py"
            guard.write_text(
                guard.read_text(encoding="utf-8").replace('"code-reviewer", ', "", 1),
                encoding="utf-8",
            )
            (dst / "skills" / "runbook" / "references" / "orphan.md").write_text(
                "x", encoding="utf-8"
            )
            # The guide rule trips three ids at once: a stale path, a dropped alias, and (with
            # the bridge line gone) a lost import.
            guide_doc = dst / "AGENTS.md"
            guide_doc.write_text(
                guide_doc.read_text(encoding="utf-8")
                .replace("scripts/validate_fleet.py", "scripts/validate_fleets.py", 1)
                .replace("`fable`", "`fable-classic`"),
                encoding="utf-8",
            )
            (dst / "CLAUDE.md").write_text("no bridge\n", encoding="utf-8")
            fleet = Fleet.load(dst)
            seen: set[str] = set()
            for entry in rules.rules():
                if entry.id == "adapters.generated":
                    continue
                for finding in entry.run(fleet):
                    seen.add(finding.rule)
                    self.assertIn(
                        finding.rule, entry.emitted_ids, f"{entry.id} emitted {finding.rule}"
                    )
        self.assertIn("plugin.guard.roster", rules.emitted_ids())
        self.assertIn("skill.bundle.orphans", rules.emitted_ids())
        self.assertLessEqual(
            {"guide.stale-path", "guide.model-aliases", "guide.bridge"}, seen, sorted(seen)
        )

    def test_definition_scoped_rules_are_the_per_definition_checks(self) -> None:
        # The scope decides the run's sequencing, so it is pinned: every per-agent and per-skill
        # check is definition-scoped, and the directory and roster verdicts are not.
        scoped = {entry.id for entry in rules.rules() if entry.scope == "definition"}
        self.assertEqual(
            {
                "agent.frontmatter",
                "agent.frontmatter.keys",
                "agent.identity",
                "agent.tools",
                "agent.tools.trust-boundary",
                "agent.skills",
                "agent.model",
                "agent.packet",
                "skill.frontmatter",
                "skill.frontmatter.keys",
                "skill.identity",
                "skill.bundle",
            },
            scoped,
        )
        with self.assertRaises(ValueError):
            rules.rule("scope.bogus", group="agents", why="w", scope="file")(lambda fleet: [])

    def test_run_sequences_definition_findings_definition_major(self) -> None:
        # The legacy loops emitted every finding about one definition before the next; a run
        # that went rule by rule would report agent b's malformed frontmatter before agent a's
        # missing name, and a consumer diffing two reports would see a reorder, not a change.
        with repo_copy() as dst:
            first, second, third = sorted((dst / "agents").glob("*.md"))[:3]
            first.write_text(
                first.read_text(encoding="utf-8").replace("name: ", "nam: ", 1),
                encoding="utf-8",
            )
            second.write_text(
                "not frontmatter\n" + second.read_text(encoding="utf-8"), encoding="utf-8"
            )
            third.write_text(
                re.sub(
                    r"^model: .*$",
                    "model: claude-opus-5",
                    third.read_text(encoding="utf-8"),
                    count=1,
                    flags=re.MULTILINE,
                ),
                encoding="utf-8",
            )
            skill_dirs = sorted(p for p in (dst / "skills").iterdir() if p.is_dir())
            (skill_dirs[0] / "SKILL.md").unlink()
            (skill_dirs[1] / "references").mkdir(exist_ok=True)
            (skill_dirs[1] / "references" / "orphan.md").write_text("x", encoding="utf-8")
            fleet = Fleet.load(dst)
            findings = rules.run(fleet, groups=("agents", "skills"))
        orphan = skill_dirs[1] / "references" / "orphan.md"
        self.assertEqual(
            [first, first, second, third, skill_dirs[0], orphan], [f.path for f in findings]
        )
        self.assertEqual(
            ["agent.frontmatter.keys", "agent.identity", "agent.frontmatter", "agent.model"],
            [f.rule for f in findings[:4]],
        )

    def test_run_follows_the_requested_group_sequence_not_import_order(self) -> None:
        # The plugin module imports the references module, so registration order interleaves
        # them; the run order must be the caller's sequence regardless.
        ids = [entry.id for entry in rules.rules(groups=("references", "plugin", "agents"))]
        self.assertEqual("references.bare-skill", ids[0])
        self.assertEqual("plugin.rules", ids[2])
        self.assertTrue(ids[3].startswith("agent"))
        default = [entry.group for entry in rules.rules()]
        self.assertEqual(list(dict.fromkeys(default)), list(rules.REPO_GROUP_ORDER))

    def test_skip_accepts_an_emitted_id_of_a_multi_check_rule(self) -> None:
        with repo_copy() as dst:
            guard = dst / "scripts" / "readonly-guard.py"
            guard.write_text(
                guard.read_text(encoding="utf-8").replace('"code-reviewer", ', "", 1),
                encoding="utf-8",
            )
            fleet = Fleet.load(dst)
            with_roster = rules.run(fleet, groups=("plugin",))
            without = rules.run(fleet, groups=("plugin",), skip=("plugin.guard.roster",))
        self.assertIn("plugin.guard.roster", {f.rule for f in with_roster})
        self.assertNotIn("plugin.guard.roster", {f.rule for f in without})


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

    def test_validate_plugin_honors_a_caller_supplied_roster(self) -> None:
        # The legacy signature validated against the supplied names; a roster that omits a
        # guarded agent must report it as "not an agent", whatever the tree holds.
        from scripts import validate_fleet

        issues = validate_fleet.validate_plugin(REPO, ["homelab-engineer"], ["runbook"])
        self.assertTrue(any("not an agent in agents/" in i for i in issues), issues)
        self.assertEqual(
            [],
            validate_fleet.validate_plugin(
                REPO,
                validate_fleet.validate_agents(REPO)[1],
                validate_fleet.validate_skills(REPO)[1],
            ),
        )

    def test_validate_bare_skill_references_honors_a_caller_supplied_roster(self) -> None:
        # The legacy signature judged bare backticks against the caller's skill names; a roster
        # that omits `runbook` must not report a reference to it, whatever the tree holds.
        from scripts import validate_fleet

        with repo_copy() as dst:
            agent = dst / "agents" / "sde-fullstack.md"
            agent.write_text(
                agent.read_text(encoding="utf-8") + "\nSee `runbook`.\n", encoding="utf-8"
            )
            reported = validate_fleet.validate_bare_skill_references(dst, ["runbook"])
            not_reported = validate_fleet.validate_bare_skill_references(dst, ["other-skill"])
        self.assertTrue(any("`runbook`" in text for text in reported), reported)
        self.assertEqual([], not_reported)

    def test_plugin_rules_judge_the_snapshot_rosters_not_the_disk(self) -> None:
        # The guard's roster is captured in Fleet.load; a guard rewritten afterwards is a
        # different tree, and this report must keep describing the one it loaded.
        with repo_copy() as dst:
            fleet = Fleet.load(dst)
            self.assertTrue(fleet.guard.exists)
            self.assertIn("code-reviewer", fleet.guard.rosters["GUARDED_AGENT_NAMES"])
            self.assertEqual({"homelab-engineer"}, set(fleet.gate.rosters["GATED_AGENT_NAMES"]))
            guard = dst / "scripts" / "readonly-guard.py"
            guard.write_text(
                guard.read_text(encoding="utf-8").replace('"code-reviewer", ', "", 1),
                encoding="utf-8",
            )
            self.assertEqual([], rules.run(fleet, groups=("plugin",)))
            self.assertIn(
                "plugin.guard.roster",
                {f.rule for f in rules.run(Fleet.load(dst), groups=("plugin",))},
            )

    def test_reference_rules_judge_the_snapshot_bytes_not_the_disk(self) -> None:
        # The definitions are read once; a file rewritten after the snapshot must not make the
        # reference rules describe a different tree than the agent rules did.
        with repo_copy() as dst:
            fleet = Fleet.load(dst)
            agent = dst / "agents" / "sde-fullstack.md"
            agent.write_text(
                agent.read_text(encoding="utf-8") + "\nSee `runbook`.\n", encoding="utf-8"
            )
            self.assertEqual([], [f for f in rules.run(fleet, groups=("references",))])
            self.assertTrue(
                [
                    f
                    for f in rules.run(Fleet.load(dst), groups=("references",))
                    if f.rule == "references.bare-skill"
                ]
            )

    def test_adapter_findings_name_the_drifted_file(self) -> None:
        with repo_copy() as dst:
            drifted = dst / ".codex" / "agents" / "researcher.toml"
            drifted.write_text(
                drifted.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8"
            )
            report = validate(dst, groups=("adapters",))
        self.assertEqual(1, len(report.findings), report.texts)
        self.assertEqual(".codex/agents/researcher.toml", report.findings[0].relative_path(dst))

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
