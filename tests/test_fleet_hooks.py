"""The hook file is rendered from the hook scripts' own rosters, and byte-checked like an adapter.

Risk hypothesis: `hooks/hooks.json` names each roster TWICE -- once in the `case "$IN"` fast path
that decides whether the interpreter runs, once in the `case "$SQ"` identity fallback that fails
closed when none answers. Maintained by hand, a name could reach one block and not the other, and
the hook would still exit 0 for the agent it was supposed to cover. Phase 5 of the machinery
rewrite makes the scripts' `GUARDED_AGENT_NAMES` and `GATED_AGENT_NAMES` the single source; these
tests pin that the committed file IS that rendering, that a roster edit reaches both blocks, and
that the generator refuses the shapes it cannot render honestly.

`tests/test_hook_wiring.py` remains the behavioural oracle: it runs the rendered shell string
under `sh`. Nothing here replaces that -- a renderer whose output parses is not a hook that
decides correctly.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fleet import hooks
from fleet.rules import plugin as plugin_rules
from fleet.snapshot import (
    GATE_ROSTER,
    GATE_SCRIPT,
    GUARD_ROSTER,
    GUARD_SCRIPT,
    Fleet,
    HookScript,
)
from scripts import generate_platform_adapters as generator
from scripts import validate_fleet
from tests.support import REPO, repo_copy

HOOKS = REPO / "hooks" / "hooks.json"


def repo_rosters(root: Path) -> tuple[hooks.Roster, hooks.Roster]:
    guard = HookScript.load(root / GUARD_SCRIPT, GUARD_ROSTER).rosters
    gate = HookScript.load(root / GATE_SCRIPT, GATE_ROSTER).rosters
    assert guard is not None and gate is not None
    return (
        hooks.Roster(guard[GUARD_ROSTER], guard.plugin_name),
        hooks.Roster(gate[GATE_ROSTER], gate.plugin_name),
    )


def case_blocks(command: str) -> dict[str, str]:
    """The fast-path and fallback blocks, split by the validator's own reader.

    Deliberately not a second splitter: if this module grew its own, a renderer and a rule could
    disagree about where a block ends and both tests would still pass.
    """

    return plugin_rules._select_roster_blocks(plugin_rules._roster_blocks(command))


class RenderTests(unittest.TestCase):
    def test_the_committed_hook_file_is_the_rendered_one(self) -> None:
        # The phase-5 oracle. If this fails, either the templates drifted from the committed
        # shell or someone hand-edited the hook file -- and the generator would now overwrite
        # whichever of the two is not in `fleet/hooks.py`.
        guard, gate = repo_rosters(REPO)
        self.assertEqual(HOOKS.read_bytes(), hooks.hooks_json(guard, gate))

    def test_a_roster_name_reaches_both_case_blocks(self) -> None:
        # The failure this whole phase exists to end: a name in the fast path but not the
        # fallback (or the reverse) leaves the agent uncovered while every file claims otherwise.
        guard, gate = repo_rosters(REPO)
        added = "lab-operator"
        document = hooks.hooks_document(
            hooks.Roster(guard.names | {added}, guard.plugin_name),
            hooks.Roster(gate.names | {added}, gate.plugin_name),
        )
        for index, hook in enumerate(document["hooks"]["PreToolUse"][0]["hooks"]):
            blocks = case_blocks(hook["command"])
            self.assertEqual({"IN", "SQ"}, blocks.keys(), hook["command"])
            with self.subTest(hook=index, block="fast path"):
                self.assertIn(f"*{added}*", blocks["IN"])
            with self.subTest(hook=index, block="identity fallback"):
                self.assertIn(f'"agent_type":"{added}"', blocks["SQ"])
                self.assertIn(f'"agent_type":"sde-agents:{added}"', blocks["SQ"])

    def test_each_hook_carries_its_own_scripts_namespace(self) -> None:
        # The guard and the gate each build the namespaced `agent_type` they match from their own
        # PLUGIN_NAME. Rendering both from one value would hide a disagreement between the two
        # scripts behind a hook file that looks consistent.
        document = hooks.hooks_document(
            hooks.Roster(frozenset({"guarded"}), "guard-ns"),
            hooks.Roster(frozenset({"gated"}), "gate-ns"),
        )
        guard_command, gate_command = (
            hook["command"] for hook in document["hooks"]["PreToolUse"][0]["hooks"]
        )
        self.assertIn('"agent_type":"guard-ns:guarded"', case_blocks(guard_command)["SQ"])
        self.assertNotIn("gate-ns", guard_command)
        self.assertIn('"agent_type":"gate-ns:gated"', case_blocks(gate_command)["SQ"])
        self.assertNotIn("guard-ns", gate_command)

    def test_an_empty_roster_is_refused_rather_than_rendered(self) -> None:
        # `case "$IN" in ) ;;` is a shell syntax error. The runtime swallows it, so the hook would
        # fail on every Bash call while reading as armed. Refusing is the only honest answer.
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            hooks.render(hooks.GUARD_TEMPLATE, [], "sde-agents")
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            hooks.hooks_json(
                hooks.Roster(frozenset(), "sde-agents"),
                hooks.Roster(frozenset({"gated"}), "sde-agents"),
            )

    def test_both_templates_carry_exactly_one_of_each_placeholder(self) -> None:
        # `render` substitutes once per placeholder. A template that gained a second copy would
        # leave the literal `@@FAST_PATH@@` in the shipped shell, matching nothing.
        for name, template in (
            ("guard", hooks.GUARD_TEMPLATE),
            ("gate", hooks.GATE_TEMPLATE),
        ):
            with self.subTest(hook=name):
                self.assertEqual(1, template.count(hooks.FAST_PATH))
                self.assertEqual(1, template.count(hooks.IDENTITY))


class GeneratorWiringTests(unittest.TestCase):
    def test_the_hook_file_is_one_of_the_generated_outputs(self) -> None:
        outputs = generator.expected_outputs(REPO)
        self.assertIn(generator.HOOKS_FILE, outputs)
        self.assertEqual(HOOKS.read_bytes(), outputs[generator.HOOKS_FILE])

    def test_the_hook_directory_is_not_a_generated_root(self) -> None:
        # `--write` replaces a generated root wholesale. `hooks/` is the plugin's own hook
        # directory, so declaring it as a root would delete anything a future hook adds there.
        roots = (*generator.GENERATED_ROOTS, *generator.RETIRED_GENERATED_ROOTS)
        self.assertNotIn(Path("hooks"), roots)
        self.assertTrue(
            all(generator.HOOKS_FILE.parent != root for root in roots),
            roots,
        )

    def test_write_leaves_a_sibling_of_the_hook_file_alone(self) -> None:
        # The non-vacuous half of the test above: prove `--write` does not clear the directory.
        with repo_copy() as dst:
            sibling = dst / "hooks" / "note.txt"
            sibling.write_text("not generated\n", encoding="utf-8")
            generator.write_generated_outputs(dst)
            self.assertTrue(sibling.is_file(), "write_generated_outputs cleared hooks/")
            self.assertEqual(HOOKS.read_bytes(), (dst / "hooks" / "hooks.json").read_bytes())

    def test_a_roster_edit_makes_the_committed_hook_file_stale(self) -> None:
        # Byte-drift is what makes the single source real: change a roster without regenerating
        # and the validator says so, in both directions (adding and removing a name).
        edits = (
            ("name added", '{"homelab-engineer"}', '{"homelab-engineer", "extra"}'),
            ("name replaced", '{"homelab-engineer"}', '{"researcher"}'),
        )
        for label, before, after in edits:
            with self.subTest(change=label), repo_copy() as dst:
                script = dst / GATE_SCRIPT
                original = script.read_text(encoding="utf-8")
                changed = original.replace(before, after, 1)
                self.assertNotEqual(original, changed, "the mutation did not apply")
                script.write_text(changed, encoding="utf-8")
                issues = generator.validate_generated_outputs(dst)
                self.assertTrue(
                    any("hooks.json" in issue and "drifted" in issue for issue in issues),
                    issues,
                )

    def test_an_unreadable_roster_is_refused_rather_than_read_as_empty(self) -> None:
        # "Guards nobody" and "could not be read" render differently -- the first is a hook that
        # covers no one, the second is a bug. Rendering the first for the second would ship a
        # disarmed hook that byte-drift validation then certifies as current.
        with repo_copy() as dst:
            (dst / GATE_SCRIPT).write_text("GATED_AGENT_NAMES = compute()\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                generator.expected_outputs(dst)
            issues = generator.validate_generated_outputs(dst)
            self.assertTrue(any("cannot render" in issue for issue in issues), issues)

    def test_the_rosters_are_read_as_data_never_by_running_the_script(self) -> None:
        # The generator runs against whatever tree it is pointed at. Importing that tree's hook
        # to learn who it guards is the execution the guard exists to prevent, so the reader is
        # the snapshot's AST one. A module-level side effect proves it: an importing reader would
        # raise, a parsing one returns the roster.
        with repo_copy() as dst:
            script = dst / GUARD_SCRIPT
            script.write_text(
                'raise SystemExit("the generator imported a hook script")\n'
                + script.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            guard, _ = generator._hook_rosters(dst)
            self.assertIn("code-reviewer", guard.names)

    def test_a_link_in_place_of_the_hook_file_is_refused(self) -> None:
        # `--write` writes the hook file by path. Through a link that path is somewhere else, and
        # the repository would look regenerated while the bytes landed outside it. The generated
        # ROOTS have carried this check since issue #91; a generated file outside them needs the
        # same one, or the standalone declaration is the hole.
        with tempfile.TemporaryDirectory() as outside_dir:
            victim = Path(outside_dir) / "victim.json"
            victim.write_text("outside content\n", encoding="utf-8")
            with repo_copy() as dst:
                path = dst / generator.HOOKS_FILE
                original = path.read_bytes()
                path.unlink()
                try:
                    path.symlink_to(victim)
                except OSError as exc:  # e.g. Windows without symlink privilege
                    path.write_bytes(original)
                    self.skipTest(f"cannot create symlinks here: {exc}")
                with self.assertRaisesRegex(ValueError, "(?:link|junction|reparse)"):
                    generator._actual_generated_files(dst, tracked_files=None)
                issues = generator.validate_generated_outputs(dst)
                self.assertTrue(
                    any("cannot inspect" in issue for issue in issues), issues
                )
            self.assertEqual("outside content\n", victim.read_text(encoding="utf-8"))


class ValidatorCrossCheckTests(unittest.TestCase):
    """The cross-check is a SECOND instrument, and it must not read prose as a roster."""

    def test_the_gate_fallback_roster_is_checked_not_the_nested_bypass_case(self) -> None:
        # MEASURED DEFECT (phase 5): the rule took the LAST `case` block as the fallback. The gate
        # nests a `case "$IN"` inside its fallback to separate a prompt-suppressed session from an
        # interactive one, and that nested block names homelab-engineer only inside an English
        # denial reason. So replacing the gate's real `case "$SQ"` roster with a name that gates
        # nobody left the whole validator at exit 0 -- enforcement that checked prose.
        with repo_copy() as dst:
            path = dst / "hooks" / "hooks.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            hook = document["hooks"]["PreToolUse"][0]["hooks"][1]
            hook["command"] = hook["command"].replace(
                '''*'"agent_type":"sde-agents:homelab-engineer"'*'''
                '''|*'"agent_type":"homelab-engineer"'*''',
                '''*'"agent_type":"sde-agents:NOBODY"'*''',
                1,
            )
            path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
            issues = validate_fleet.validate_plugin(
                dst, Fleet.load(dst).agent_names, Fleet.load(dst).skill_names
            )
            self.assertTrue(
                any(
                    "no-interpreter fallback" in issue and "homelab-engineer" in issue
                    for issue in issues
                ),
                issues,
            )

    def test_a_hook_missing_either_case_variable_is_refused(self) -> None:
        # A restructured hook the cross-check cannot recognize must fail, not report nothing.
        for variable in ("IN", "SQ"):
            with self.subTest(removed=variable), repo_copy() as dst:
                path = dst / "hooks" / "hooks.json"
                document = json.loads(path.read_text(encoding="utf-8"))
                hook = document["hooks"]["PreToolUse"][0]["hooks"][0]
                hook["command"] = hook["command"].replace(
                    f'case "${variable}" in', "if false; then", 1
                )
                path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
                issues = validate_fleet.validate_plugin(
                    dst, Fleet.load(dst).agent_names, Fleet.load(dst).skill_names
                )
                self.assertTrue(
                    any("found blocks on" in issue for issue in issues), issues
                )


if __name__ == "__main__":
    unittest.main()
