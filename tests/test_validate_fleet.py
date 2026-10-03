"""The validator: a clean baseline tree, then one targeted break per check.

Every test starts from a tree that validates clean (pinned by the first test, so no other test can
pass vacuously) and breaks exactly one thing, asserting the problem the validator names.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from scripts import validate_fleet
from tests.support import repo_copy, run_main

AGENT = """---
name: {name}
description: {name} does its job when asked.
tools: {tools}
model: sonnet
{extra}---

Body.
"""
SKILL = """---
name: {name}
description: A {name} skill.
{extra}---

Read [detail](references/detail.md) first.
"""
GUARD = 'PLUGIN_NAME = "demo"\nGUARDED_AGENT_NAMES = frozenset({"reviewer"})\n'
INVENTORY = validate_fleet.render_inventory(["builder", "reviewer"], ["craft"])


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def baseline(root: Path) -> None:
    builder = AGENT.format(name="builder", tools="Read, Bash, Edit", extra="")
    write(root, "agents/builder.md", builder)
    write(root, "agents/reviewer.md", AGENT.format(name="reviewer", tools="Read, Bash", extra=""))
    write(root, "skills/craft/SKILL.md", SKILL.format(name="craft", extra=""))
    write(root, "skills/craft/references/detail.md", "Detail.\n")
    write(root, ".claude-plugin/plugin.json", json.dumps({"name": "demo"}))
    write(root, "scripts/readonly-guard.py", GUARD)
    write(root, "README.md", f"# Demo\n\n{INVENTORY}\n")
    write(root, "CLAUDE.md", "@AGENTS.md\n")
    write(root, "AGENTS.md", "Agents live in `agents/builder.md`.\n")


def problems(mutate: Callable[[Path], None] | None = None) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        baseline(root)
        if mutate:
            mutate(root)
        issues, _, _ = validate_fleet.validate(root, adapters=False)
    return issues


def agent(name: str, tools: str = "Read", extra: str = "") -> Callable[[Path], None]:
    return lambda root: write(
        root, f"agents/{name}.md", AGENT.format(name=name, tools=tools, extra=extra)
    )


class ValidatorTests(unittest.TestCase):
    def assertReports(self, mutate: Callable[[Path], None], *fragments: str) -> None:
        issues = problems(mutate)
        for fragment in fragments:
            self.assertTrue(any(fragment in issue for issue in issues), (fragment, issues))

    def test_the_baseline_is_clean(self) -> None:
        self.assertEqual([], problems())

    def test_frontmatter_must_parse(self) -> None:
        self.assertReports(
            lambda root: write(root, "agents/broken.md", "no frontmatter\n"),
            "missing or malformed frontmatter",
        )

    def test_unknown_and_plugin_inert_agent_keys(self) -> None:
        self.assertReports(agent("extra", extra="colour: red\n"), "unknown frontmatter key")
        self.assertReports(agent("hooked", extra="hooks: x\n"), "SILENTLY IGNORED")

    def test_name_must_match_the_file_and_carry_a_description(self) -> None:
        self.assertReports(
            lambda root: write(
                root, "agents/one.md", AGENT.format(name="two", tools="Read", extra="")
            ),
            "must match 'one'",
        )
        self.assertReports(
            lambda root: write(root, "agents/quiet.md", "---\nname: quiet\ntools: Read\n---\n"),
            "missing agent description",
        )

    def test_tools_must_be_explicit_known_adopted_and_unscoped(self) -> None:
        cases = {
            "": "INHERITS EVERY TOOL",
            "Read, Wrte": "unknown tool 'Wrte'",
            "Read, PowerShell": "not adopted by this fleet",
            "Read, AskUserQuestion": "never available to a subagent",
            "Read, Bash(git diff *)": "restricts nothing",
            "Read, mcp__plugin_githits_githits__feedback": "not an exact adopted name",
            "Read, mcp__plugin_githits_githits": "not an exact adopted name",
        }
        for tools, fragment in cases.items():
            with self.subTest(tools=tools):
                self.assertReports(agent("tooled", tools=tools), fragment)

    def test_a_scoped_grant_is_one_entry_and_an_adopted_mcp_tool_is_accepted(self) -> None:
        issues = problems(agent("tooled", tools="Read, Agent(a, b)"))
        self.assertFalse(any("malformed" in issue for issue in issues), issues)
        self.assertTrue(any("'Agent(a, b)'" in issue for issue in issues), issues)
        adopted = problems(agent("tooled", tools="Read, mcp__plugin_githits_githits__pkg_info"))
        self.assertEqual([], [issue for issue in adopted if "tooled.md" in issue])

    def test_trust_separated_roles_hold_exactly_their_side(self) -> None:
        self.assertReports(
            agent("researcher", tools="ToolSearch, WebFetch, WebSearch, Read"), "forbidden tools"
        )
        self.assertReports(
            agent("repository-investigator", tools="Read, Grep, Glob"), "missing required tools"
        )

    def test_a_preload_must_resolve_to_a_model_invocable_skill(self) -> None:
        self.assertReports(agent("loader", extra="skills: ghost\n"), "does not resolve")

        def explicit_only(root: Path) -> None:
            write(root, "skills/manual/SKILL.md", SKILL.format(
                name="manual", extra="disable-model-invocation: true\n"))
            write(root, "skills/manual/references/detail.md", "Detail.\n")
            agent("loader", extra="skills: manual\n")(root)

        self.assertReports(explicit_only, "cannot be preloaded")

    def test_model_must_be_an_alias(self) -> None:
        self.assertReports(
            lambda root: write(root, "agents/pinned.md", AGENT.format(
                name="pinned", tools="Read", extra="").replace("sonnet", "claude-opus-4-1")),
            "pinned model ID",
        )

    def test_a_bare_backticked_skill_must_be_preloaded(self) -> None:
        def bare(root: Path) -> None:
            path = root / "agents" / "builder.md"
            path.write_text(path.read_text(encoding="utf-8") + "Use `craft`.\n", encoding="utf-8")

        self.assertReports(bare, "bare backticked skill name `craft`")

    def test_skills_need_a_skill_md_known_keys_and_their_own_name(self) -> None:
        self.assertReports(lambda root: (root / "skills" / "empty").mkdir(), "missing SKILL.md")
        self.assertReports(
            lambda root: write(root, "skills/craft/SKILL.md", SKILL.format(
                name="craft", extra="disable-model-invocaton: true\n")),
            "unknown frontmatter key 'disable-model-invocaton'",
        )
        self.assertReports(
            lambda root: write(root, "skills/craft/SKILL.md", SKILL.format(name="other", extra="")),
            "must match 'craft'",
        )

    def test_bundle_links_resolve_and_every_reference_file_is_linked(self) -> None:
        self.assertReports(
            lambda root: (root / "skills/craft/references/detail.md").unlink(),
            "referenced file does not exist: references/detail.md",
        )
        self.assertReports(
            lambda root: write(root, "skills/craft/references/stray.md", "Stray.\n"),
            "orphaned",
        )

        def dot_slash(root: Path) -> None:
            path = root / "skills/craft/SKILL.md"
            text = path.read_text(encoding="utf-8").replace("(references/", "(./references/")
            path.write_text(text, encoding="utf-8")

        self.assertEqual([], problems(dot_slash), "a ./ link is the same link")

        def escaping(root: Path) -> None:
            path = root / "skills/craft/SKILL.md"
            text = path.read_text(encoding="utf-8") + "See references/../../../README.md too.\n"
            path.write_text(text, encoding="utf-8")

        self.assertReports(escaping, "does not exist: references/../../../README.md")

    def test_the_guard_roster_agrees_with_the_agents(self) -> None:
        self.assertReports(
            lambda root: write(root, "scripts/readonly-guard.py", GUARD.replace(
                '"reviewer"', '"reviewer", "ghost"')),
            "lists 'ghost', not an agent",
        )
        self.assertReports(
            lambda root: write(root, "scripts/readonly-guard.py", GUARD.replace(
                'frozenset({"reviewer"})', "frozenset()")),
            "not in GUARDED_AGENT_NAMES",
        )
        self.assertReports(
            lambda root: write(root, "scripts/readonly-guard.py", GUARD.replace('"demo"', '"x"')),
            "matches nobody",
        )
        self.assertReports(
            lambda root: write(root, "scripts/readonly-guard.py", "GUARDED = 1\n"),
            "cannot read the guard roster",
        )

    def test_namespaced_references_resolve_to_the_right_kind(self) -> None:
        def body(text: str) -> Callable[[Path], None]:
            def mutate(root: Path) -> None:
                path = root / "agents" / "builder.md"
                path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")
            return mutate

        self.assertReports(body("See demo:ghost.\n"), "not an agent or skill")
        self.assertReports(body("Run /demo:reviewer.\n"), "must name a skill")
        self.assertReports(body("See demo:Bad_Name.\n"), "malformed namespaced reference")
        self.assertEqual([], problems(body("See demo:craft and /demo:craft.\n")))

    def test_the_guide_is_imported_and_names_only_real_paths(self) -> None:
        self.assertReports(lambda root: write(root, "CLAUDE.md", "# no import\n"), "never loads")
        self.assertReports(
            lambda root: write(root, "AGENTS.md", "See `scripts/gone.py`.\n"),
            "names 'scripts/gone.py'",
        )
        self.assertReports(
            lambda root: write(root, "docs/engineering-program.md", "See `fleet/gone.py`.\n"),
            "names 'fleet/gone.py'",
        )

    def test_the_inventory_is_current_and_rewritable(self) -> None:
        stale = lambda root: write(root, "README.md", f"# Demo\n\n{INVENTORY.replace('2', '9')}\n")  # noqa: E731
        self.assertReports(stale, "fleet inventory drifted")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline(root)
            stale(root)
            (root / ".claude-plugin" / "plugin.json").unlink()  # main runs the adapter check
            code, _ = run_main(validate_fleet.main, "--root", str(root), "--write-inventory")
            self.assertEqual(0, code)
            self.assertIn(INVENTORY, (root / "README.md").read_text(encoding="utf-8"))
            write(root, "agents/extra.md", "broken\n")
            code, _ = run_main(validate_fleet.main, "--root", str(root))
            self.assertEqual(1, code)


class AdapterCheckTests(unittest.TestCase):
    def test_a_hand_edited_adapter_is_reported_and_adapters_false_skips_it(self) -> None:
        with repo_copy() as dst:
            adapter = sorted((dst / ".github" / "agents").glob("*.md"))[0]
            adapter.write_text(adapter.read_text(encoding="utf-8") + "\nedit\n", encoding="utf-8")
            reported, _, _ = validate_fleet.validate(dst)
            skipped, _, _ = validate_fleet.validate(dst, adapters=False)
        self.assertTrue(any(adapter.name in issue for issue in reported), reported)
        self.assertEqual([], skipped)

    def test_the_validated_tree_supplies_its_own_generator(self) -> None:
        # With --root pointing elsewhere, a broken generator there must fail validation rather
        # than be replaced by the executing checkout's healthy copy.
        with repo_copy() as dst:
            generator = dst / "scripts" / "generate_platform_adapters.py"
            text = generator.read_text(encoding="utf-8")
            generator.write_text(text + "\nthis is not python\n", encoding="utf-8")
            issues, _, _ = validate_fleet.validate(dst)
        self.assertTrue(any("platform adapter validation crashed" in i for i in issues), issues)


if __name__ == "__main__":
    unittest.main()
