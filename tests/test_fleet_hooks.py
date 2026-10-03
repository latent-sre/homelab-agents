"""The hook file is rendered from the hook scripts' own rosters, and byte-checked like an adapter.

Risk hypothesis: `hooks/hooks.json` names each roster TWICE -- once in the `case "$IN"` fast path
that decides whether the interpreter runs, once in the `case "$SQ"` identity fallback that fails
closed when none answers. Maintained by hand, a name could reach one block and not the other, and
the hook would still exit 0 for the agent it was supposed to cover. The guard script's
`GUARDED_AGENT_NAMES` is the single source; these tests pin that the committed file IS that
rendering, that a roster edit reaches both blocks, and that the generator refuses the shapes it
cannot render honestly.

`tests/test_hook_wiring.py` remains the behavioural oracle: it runs the rendered shell string
under `sh`. Nothing here replaces that -- a renderer whose output parses is not a hook that
decides correctly.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from fleet import hooks
from fleet.snapshot import (
    GUARD_ROSTER,
    GUARD_SCRIPT,
    HookScript,
)
from scripts import generate_platform_adapters as generator
from tests.support import (
    REPO,
    create_directory_link,
    remove_directory_link,
    repo_copy,
)

HOOKS = REPO / "hooks" / "hooks.json"


def repo_roster(root: Path) -> hooks.Roster:
    guard = HookScript.load(root / GUARD_SCRIPT, GUARD_ROSTER).rosters
    assert guard is not None
    return hooks.Roster(guard[GUARD_ROSTER], guard.plugin_name)


def case_blocks(command: str) -> dict[str, str]:
    """The fast-path (`$IN`) and identity-fallback (`$SQ`) `case` blocks, up to their `esac`."""

    blocks: dict[str, str] = {}
    for variable in ("IN", "SQ"):
        opener = f'case "${variable}" in'
        if opener in command:
            blocks[variable] = command.split(opener, 1)[1].split("esac", 1)[0]
    return blocks


class RenderTests(unittest.TestCase):
    def test_a_roster_name_reaches_both_case_blocks(self) -> None:
        # The failure this whole phase exists to end: a name in the fast path but not the
        # fallback (or the reverse) leaves the agent uncovered while every file claims otherwise.
        guard = repo_roster(REPO)
        added = "lab-operator"
        document = hooks.hooks_document(hooks.Roster(guard.names | {added}, guard.plugin_name))
        entries = document["hooks"]["PreToolUse"][0]["hooks"]
        self.assertEqual(1, len(entries), entries)
        for index, hook in enumerate(entries):
            blocks = case_blocks(hook["command"])
            self.assertEqual({"IN", "SQ"}, blocks.keys(), hook["command"])
            with self.subTest(hook=index, block="fast path"):
                self.assertIn(f"*{added}*", blocks["IN"])
            with self.subTest(hook=index, block="identity fallback"):
                self.assertIn(f'"agent_type":"{added}"', blocks["SQ"])
                self.assertIn(f'"agent_type":"sde-agents:{added}"', blocks["SQ"])

    def test_the_hook_carries_its_scripts_namespace(self) -> None:
        # The guard builds the namespaced `agent_type` it matches from its own PLUGIN_NAME, so the
        # rendered identity block must use that value, not a shared default.
        document = hooks.hooks_document(hooks.Roster(frozenset({"guarded"}), "guard-ns"))
        (command,) = (hook["command"] for hook in document["hooks"]["PreToolUse"][0]["hooks"])
        self.assertIn('"agent_type":"guard-ns:guarded"', case_blocks(command)["SQ"])

    def test_emptying_the_roster_still_generates(self) -> None:
        # End to end, in both spellings an operator would reach for. `frozenset()` in particular
        # was unreadable by the AST roster reader, which turned a valid configuration into a
        # generation failure. (The validator still flags read-only Bash agents left unguarded;
        # this pins only that generation does not break.)
        for spelling in ("frozenset()", "frozenset([])"):
            with self.subTest(spelling=spelling), repo_copy() as dst:
                script = dst / GUARD_SCRIPT
                original = script.read_text(encoding="utf-8")
                start = original.index("GUARDED_AGENT_NAMES = frozenset({")
                end = original.index("})", start) + len("})")
                script.write_text(
                    original[:start] + f"GUARDED_AGENT_NAMES = {spelling}" + original[end:],
                    encoding="utf-8",
                )
                generator.write_generated_outputs(dst)
                entries = json.loads(
                    (dst / generator.HOOKS_FILE).read_text(encoding="utf-8")
                )["hooks"]["PreToolUse"][0]["hooks"]
                self.assertEqual([], entries)
                self.assertEqual([], generator.validate_generated_outputs(dst))

    def test_a_shell_unsafe_name_is_refused_rather_than_interpolated(self) -> None:
        # Both roster spans land inside the hook's shell, and the identity span lands inside
        # SINGLE QUOTES. An apostrophe closes that quote and puts the rest in command position,
        # so a crafted PLUGIN_NAME renders a hook that RUNS a command on the next Bash call
        # rather than matching one. The generator renders whatever tree it is pointed at, so
        # these values are not trusted input (Copilot, PR #193 — reproduced before the guard).
        injection = "x') ;; *) touch /tmp/sde-agents-pwned; ;; esac; #"
        for label, names, plugin in (
            ("plugin name", ["code-reviewer"], injection),
            ("roster name", ["code-reviewer", injection], "sde-agents"),
        ):
            with self.subTest(field=label):
                with self.assertRaisesRegex(ValueError, "not a fleet component name"):
                    hooks.render(hooks.GUARD_TEMPLATE, names, plugin)
        # The grammar is the fleet's, so anything a component could legitimately be still renders.
        self.assertIn(
            "*code-reviewer*", hooks.render(hooks.GUARD_TEMPLATE, ["code-reviewer"], "sde-agents")
        )
        for rejected in ("code reviewer", "UPPER", "a;b", "*", "a/b", ""):
            with self.subTest(value=rejected):
                with self.assertRaises(ValueError):
                    hooks.render(hooks.GUARD_TEMPLATE, ["code-reviewer"], rejected)

    def test_an_empty_roster_renders_no_hook_rather_than_a_broken_one(self) -> None:
        # `case "$IN" in ) ;;` is a shell syntax error the runtime swallows, so an empty roster
        # must not render a hook. But it is a VALID configuration, not an error -- a fleet with
        # no guarded agent -- so it must not break generation (Copilot, PR #193). The honest
        # rendering of "covers nobody" is no hook at all.
        self.assertIsNone(hooks.render(hooks.GUARD_TEMPLATE, [], "sde-agents"))
        document = hooks.hooks_document(hooks.Roster(frozenset(), "sde-agents"))
        self.assertEqual([], document["hooks"]["PreToolUse"][0]["hooks"])

    def test_the_template_carries_exactly_one_of_each_placeholder(self) -> None:
        # `render` substitutes once per placeholder. A template that gained a second copy would
        # leave the literal `@@FAST_PATH@@` in the shipped shell, matching nothing.
        self.assertEqual(1, hooks.GUARD_TEMPLATE.count(hooks.FAST_PATH))
        self.assertEqual(1, hooks.GUARD_TEMPLATE.count(hooks.IDENTITY))


class GeneratorWiringTests(unittest.TestCase):
    def test_the_hook_file_is_one_of_the_generated_outputs(self) -> None:
        outputs = generator.expected_outputs(REPO)
        self.assertIn(generator.HOOKS_FILE, outputs)
        self.assertEqual(HOOKS.read_bytes(), outputs[generator.HOOKS_FILE])

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
            ("name added", '"repository-investigator",', '"repository-investigator", "extra",'),
        )
        for label, before, after in edits:
            with self.subTest(change=label), repo_copy() as dst:
                script = dst / GUARD_SCRIPT
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
            (dst / GUARD_SCRIPT).write_text("GUARDED_AGENT_NAMES = compute()\n", encoding="utf-8")
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
            guard = generator._guard_roster(dst)
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

    def test_a_refused_hook_path_leaves_the_adapter_trees_intact(self) -> None:
        # The standalone path was validated inside the write loop, after every generated root had
        # already been removed and recreated — so a link or malformed shape raised with the
        # checkout in neither the old state nor the new one. The hook file is the FIRST entry in
        # the write loop, so nothing else had been written back yet (Copilot, PR #193).
        with repo_copy() as dst:
            outside = dst / "outside-hooks"
            outside.mkdir()
            target = dst / "hooks"
            for path in sorted(target.iterdir()):
                path.replace(outside / path.name)
            target.rmdir()
            create_directory_link(outside, target)
            try:
                before = sorted(p.name for p in (dst / ".github" / "agents").iterdir())
                self.assertTrue(before, "no adapters to lose — fixture is not exercising this")
                with self.assertRaisesRegex(ValueError, "(?:link|junction|reparse)"):
                    generator.write_generated_outputs(dst)
                self.assertEqual(
                    before,
                    sorted(p.name for p in (dst / ".github" / "agents").iterdir()),
                    "a refused hook path destroyed the adapter trees it had already replaced",
                )
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

    def test_a_malformed_path_shape_is_named_rather_than_reported_as_missing(self) -> None:
        # A directory at `hooks/hooks.json`, or a regular file at `hooks/`, is neither an absent
        # hook nor a stale one. Read as "missing", validation sends the operator to `--write`, and
        # that write then fails on `mkdir` or `os.replace` with an errno the advice did not
        # predict — a repair path the diagnostic advertises and the code cannot deliver
        # (Copilot, PR #193).
        shapes = (
            ("a directory where the hook file belongs", "not a regular file"),
            ("a regular file where the hook directory belongs", "under a non-directory"),
        )
        for (label, expected), broken in zip(shapes, ("leaf", "parent"), strict=True):
            with self.subTest(shape=label), repo_copy() as dst:
                hooks_dir = dst / "hooks"
                if broken == "leaf":
                    (dst / generator.HOOKS_FILE).unlink()
                    (dst / generator.HOOKS_FILE).mkdir()
                else:
                    shutil.rmtree(hooks_dir)
                    hooks_dir.write_text("not a directory\n", encoding="utf-8")

                issues = generator.validate_generated_outputs(dst)
                self.assertTrue(any(expected in issue for issue in issues), issues)
                self.assertFalse(
                    any("missing generated hook file" in issue for issue in issues),
                    f"malformed output reported as absent: {issues}",
                )
                with self.assertRaisesRegex(ValueError, expected):
                    generator.write_generated_outputs(dst)

    def test_a_linked_hook_script_is_refused_before_its_roster_is_read(self) -> None:
        # The hook script is a canonical source that now feeds a SHIPPED artifact. A link at
        # `scripts/readonly-guard.py` would let `--write` derive the armed hook from a roster
        # outside the checkout, and byte-drift validation would then certify it as current
        # (Copilot, PR #193). It gets the same check `agents/` and `skills/` have.
        for script in (GUARD_SCRIPT,):
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


if __name__ == "__main__":
    unittest.main()
