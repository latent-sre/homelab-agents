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

import contextlib
import io
import json
import os
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
from tests.support import (
    REPO,
    create_directory_link,
    remove_directory_link,
    repo_copy,
)

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

    def test_a_link_in_place_of_the_hook_directory_is_refused(self) -> None:
        # The leaf-only check this PR first shipped protected `hooks/hooks.json` and left `hooks/`
        # free to be a link — so validation AND `--write` would both follow it and overwrite a
        # file outside the checkout while the repository looked regenerated (Copilot, PR #193).
        # Every path COMPONENT is checked now, on inspect and again immediately before writing.
        with repo_copy() as dst:
            outside = dst / "outside-hooks"
            outside.mkdir()
            target = dst / "hooks"
            for path in sorted(target.iterdir()):
                path.replace(outside / path.name)
            target.rmdir()
            create_directory_link(outside, target)
            try:
                with self.assertRaisesRegex(ValueError, "(?:link|junction|reparse)"):
                    generator._actual_generated_files(dst, tracked_files=None)
                with self.assertRaisesRegex(ValueError, "(?:link|junction|reparse)"):
                    generator.write_generated_outputs(dst)
            finally:
                remove_directory_link(target)

    def test_a_hard_linked_hook_file_is_replaced_not_truncated(self) -> None:
        # A hard link is invisible to every link/reparse check: `lstat` reports a regular file.
        # `write_bytes` opens the EXISTING inode and truncates it, so a hard link at
        # `hooks/hooks.json` pointing outside the checkout means `--write` silently overwrites
        # that file. Reproduced on this PR's own head after the symlink fixes (Codex, PR #193).
        # `os.replace` swaps the directory entry instead, leaving the old inode's bytes alone.
        with repo_copy() as dst:
            # Same filesystem is required for a hard link, so the victim sits beside the copy.
            victim = dst.parent / "hard-link-victim.txt"
            victim.write_text("EXTERNAL SECRET\n", encoding="utf-8")
            target = dst / generator.HOOKS_FILE
            try:
                target.unlink()
                try:
                    os.link(victim, target)
                except OSError as exc:  # e.g. a filesystem without hard links
                    self.skipTest(f"cannot create hard links here: {exc}")
                self.assertEqual(2, victim.stat().st_nlink)

                generator.write_generated_outputs(dst)

                self.assertEqual(
                    "EXTERNAL SECRET\n",
                    victim.read_text(encoding="utf-8"),
                    "--write truncated the shared inode instead of replacing the entry",
                )
                self.assertEqual(1, victim.stat().st_nlink)
                self.assertEqual(HOOKS.read_bytes(), target.read_bytes())
                self.assertEqual(
                    ["hooks.json"],
                    sorted(path.name for path in (dst / "hooks").iterdir()),
                    "the atomic replace left a temporary file behind",
                )
            finally:
                victim.unlink(missing_ok=True)

    def test_a_linked_hook_script_is_refused_before_its_roster_is_read(self) -> None:
        # The hook scripts are canonical sources that now feed a SHIPPED artifact. A link at
        # `scripts/readonly-guard.py` would let `--write` derive the armed hook from a roster
        # outside the checkout, and byte-drift validation would then certify it as current
        # (Copilot, PR #193). They get the same check `agents/` and `skills/` have.
        for script in (GUARD_SCRIPT, GATE_SCRIPT):
            with self.subTest(script=script), tempfile.TemporaryDirectory() as outside_dir:
                planted = Path(outside_dir) / "roster.py"
                with repo_copy() as dst:
                    path = dst / script
                    original = path.read_bytes()
                    planted.write_bytes(original)
                    path.unlink()
                    try:
                        path.symlink_to(planted)
                    except OSError as exc:  # e.g. Windows without symlink privilege
                        path.write_bytes(original)
                        self.skipTest(f"cannot create symlinks here: {exc}")
                    with self.assertRaisesRegex(
                        ValueError, "(?:link|junction|reparse)"
                    ):
                        generator.expected_outputs(dst)

    def test_the_write_summary_counts_the_hook_file_separately(self) -> None:
        # `--write`'s count came from `len(expected)`, which now includes the hook file, so the
        # summary called it a platform adapter (Copilot, PR #193). The two are different artifacts
        # with different failure modes, and the line an operator reads should say so.
        with repo_copy() as dst:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(0, generator.main(["--write", "--root", str(dst)]))
            summary = buffer.getvalue()
        self.assertIn("hook file", summary)
        adapters = int(summary.split("Generated ", 1)[1].split(" ", 1)[0])
        self.assertEqual(
            adapters + len(generator.GENERATED_FILES),
            len(generator.expected_outputs(dst)),
            summary,
        )

    def test_a_missing_hook_file_reports_an_unarmed_plugin_not_roster_drift(self) -> None:
        # An absent hook file is not a hook covering the wrong roster — it is no hook at all, and
        # an operator triaging the two needs the difference (Copilot, PR #193).
        with repo_copy() as dst:
            (dst / generator.HOOKS_FILE).unlink()
            issues = generator.validate_generated_outputs(dst)
            missing = [i for i in issues if "missing generated hook file" in i]
            self.assertTrue(missing, issues)
            self.assertIn("not attached at all and nothing is armed", missing[0])
            self.assertNotIn("would still exit 0", missing[0])

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

    def test_prose_naming_a_roster_member_is_not_read_as_a_roster(self) -> None:
        # The residual hole in this PR's first fix (Copilot, PR #193): selecting the `$SQ` block
        # by variable still let `CASE_BLOCK_RE` delimit it, so removing the gate's NESTED
        # `case "$IN"` header extends the slice into the denial reason — an English sentence that
        # names homelab-engineer. A bare-name substring check then found the agent in prose while
        # the real identity roster gated nobody. Measured before the fix: zero findings.
        with repo_copy() as dst:
            path = dst / "hooks" / "hooks.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            hook = document["hooks"]["PreToolUse"][0]["hooks"][1]
            command = hook["command"].replace(
                '''*'"agent_type":"sde-agents:homelab-engineer"'*'''
                '''|*'"agent_type":"homelab-engineer"'*''',
                '''*'"agent_type":"sde-agents:NOBODY"'*''',
                1,
            )
            nested = (
                '''case "$IN" in *bypassPermissions*|*dontAsk*'''
                '''|*'"permission_mode":"auto"'*|*'"permission_mode": "auto"'*) '''
            )
            self.assertIn(nested, command, "the nested case header moved; re-anchor this test")
            hook["command"] = command.replace(nested, "", 1)
            path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
            fleet = Fleet.load(dst)
            issues = validate_fleet.validate_plugin(dst, fleet.agent_names, fleet.skill_names)
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
