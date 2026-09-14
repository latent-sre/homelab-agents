"""Content identity for a routing measurement, moved onto the kernel with `fleet/provenance.py`.

These are the runner's own provenance tests, retargeted at the module that outlived it. The
identity rules they pin are the reason a paired before/after means anything: a benchmark taken
against different plugin bytes, a different case selection, or different evaluator code is not
comparable to another, and each of these tests names the way that could go unnoticed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fleet import provenance
from tests.support import git


class ProvenanceTest(unittest.TestCase):
    """A benchmark identity changes only when an input that can affect the eval changes."""

    def _plugin(self, root: Path, files: list[tuple[str, bytes]] | None = None) -> None:
        files = files or [
            (".claude-plugin/plugin.json", b'{"name":"probe"}\n'),
            ("agents/probe.md", b"---\nname: probe\n---\nfirst\n"),
        ]
        for relative, content in files:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


    def test_source_identity_hashes_exact_file_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp).resolve() / "cluster.json"
            source.write_bytes(b'{"cases":[]}\n')
            before = provenance.source_identity([source])
            source.write_bytes(b'{"cases":[]}\r\n')
            after = provenance.source_identity([source])
        self.assertNotEqual(before[0]["sha256"], after[0]["sha256"])
        self.assertNotIn("\\", before[0]["path"])

    def test_evaluator_identity_hashes_exact_files_and_python_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evaluator = Path(tmp).resolve() / "grader.py"
            evaluator.write_bytes(b"first\n")
            before = provenance.evaluator_identity([evaluator])
            evaluator.write_bytes(b"second\n")
            after = provenance.evaluator_identity([evaluator])
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertRegex(before["files"][0]["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(before["runtime"]["implementation"])
        self.assertRegex(before["runtime"]["python_version"], r"^\d+\.\d+")

    def test_evaluator_change_makes_batch_provenance_incomparable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            source = root / "cluster.json"
            source.write_text('{"cases":[]}\n', encoding="utf-8")
            evaluator = root / "grader.py"
            evaluator.write_text("first\n", encoding="utf-8")
            before = provenance.benchmark_provenance(
                [source], [], "*", root, evaluator_paths=[evaluator]
            )
            evaluator.write_text("second\n", encoding="utf-8")
            after = provenance.benchmark_provenance(
                [source], [], "*", root, evaluator_paths=[evaluator]
            )
        self.assertFalse(provenance._content_provenance_matches(before, after))

    def test_selection_identity_hashes_definitions_expression_and_ids(self) -> None:
        cases = [{"id": "one", "prompt": "first"}]
        first = provenance.selection_identity("one*", cases)
        changed_definition = provenance.selection_identity(
            "one*", [{"id": "one", "prompt": "second"}]
        )
        changed_expression = provenance.selection_identity("*", cases)
        reordered_keys = provenance.selection_identity(
            "one*", [{"prompt": "first", "id": "one"}]
        )
        self.assertNotEqual(first["sha256"], changed_definition["sha256"])
        self.assertNotEqual(first["sha256"], changed_expression["sha256"])
        self.assertEqual(first["sha256"], reordered_keys["sha256"])
        self.assertEqual(["one"], first["case_ids"])
        self.assertEqual("one*", first["expression"])

    def test_plugin_identity_changes_with_runtime_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            before = provenance.plugin_identity(root)
            (root / "agents" / "probe.md").write_text("changed\n", encoding="utf-8")
            after = provenance.plugin_identity(root)
        self.assertNotEqual(before["sha256"], after["sha256"])

    def test_plugin_identity_is_stable_across_creation_and_traversal_order(self) -> None:
        files = [
            ("skills/z/SKILL.md", b"z\n"),
            (".claude-plugin/plugin.json", b"{}\n"),
            ("agents/a.md", b"a\n"),
        ]
        with (
            tempfile.TemporaryDirectory() as first_tmp,
            tempfile.TemporaryDirectory() as second_tmp,
        ):
            first, second = Path(first_tmp).resolve(), Path(second_tmp).resolve()
            self._plugin(first, files)
            self._plugin(second, list(reversed(files)))
            first_identity = provenance.plugin_identity(first)
            second_identity = provenance.plugin_identity(second)
        self.assertEqual(first_identity["sha256"], second_identity["sha256"])

    def test_eval_outputs_and_unrelated_docs_are_explicitly_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            output = root / "evals" / "baselines" / "run" / "benchmark.json"
            output.parent.mkdir(parents=True)
            output.write_text("first", encoding="utf-8")
            skill = root / "skills" / "probe" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "Ignore eval output `evals/baselines/run/benchmark.json`.\n", encoding="utf-8"
            )
            docs = root / "docs" / "roadmap.md"
            docs.parent.mkdir()
            docs.write_text("unrelated", encoding="utf-8")
            before = provenance.plugin_identity(root)
            output.write_text("second", encoding="utf-8")
            docs.write_text("also unrelated", encoding="utf-8")
            after = provenance.plugin_identity(root)
        self.assertEqual(before["sha256"], after["sha256"])
        self.assertIn("evals/**", after["scope"]["excluded"])
        self.assertIn("unreferenced docs/**", after["scope"]["excluded"])

    def test_external_plugin_directory_is_hashed_directly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / "external-plugin"
            root.mkdir()
            self._plugin(root)
            identity = provenance.plugin_identity(root)
        self.assertEqual(2, identity["files_hashed"])
        self.assertEqual([".claude-plugin", "agents"], identity["scope"]["included"])

    def test_explicit_plugin_root_runtime_dependency_is_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            hook = root / "hooks" / "hooks.json"
            hook.parent.mkdir()
            hook.write_text('${CLAUDE_PLUGIN_ROOT}/scripts/guard.py', encoding="utf-8")
            guard = root / "scripts" / "guard.py"
            guard.parent.mkdir()
            guard.write_text("first\n", encoding="utf-8")
            before = provenance.plugin_identity(root)
            guard.write_text("second\n", encoding="utf-8")
            after = provenance.plugin_identity(root)
        self.assertIn("scripts/guard.py", before["scope"]["included"])
        self.assertNotEqual(before["sha256"], after["sha256"])

    def test_repo_relative_referenced_script_is_hashed_but_unrelated_script_is_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root, [
                (".claude-plugin/plugin.json", b"{}\n"),
                ("skills/probe/SKILL.md", b"Run `python scripts/learning_ledger.py check`.\n"),
                ("scripts/learning_ledger.py", b"print('first')\n"),
                ("scripts/unrelated.py", b"print('unrelated first')\n"),
            ])
            before = provenance.plugin_identity(root)
            (root / "scripts" / "unrelated.py").write_text(
                "print('unrelated second')\n", encoding="utf-8"
            )
            unrelated_changed = provenance.plugin_identity(root)
            (root / "scripts" / "learning_ledger.py").write_text(
                "print('second')\n", encoding="utf-8"
            )
            referenced_changed = provenance.plugin_identity(root)
        self.assertIn("scripts/learning_ledger.py", before["scope"]["included"])
        self.assertNotIn("scripts/unrelated.py", before["scope"]["included"])
        self.assertEqual(before["sha256"], unrelated_changed["sha256"])
        self.assertNotEqual(unrelated_changed["sha256"], referenced_changed["sha256"])

    def test_repo_relative_script_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root, [
                (".claude-plugin/plugin.json", b"{}\n"),
                ("skills/probe/SKILL.md", b"Run `python scripts/../outside.py`.\n"),
            ])
            with self.assertRaises(provenance.ProvenanceError):
                provenance.plugin_identity(root)

    def test_backticked_repo_relative_read_dependency_is_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root, [
                (".claude-plugin/plugin.json", b"{}\n"),
                ("skills/probe/SKILL.md", b"Read `learning/README.md` before deciding.\n"),
                ("learning/README.md", b"first\n"),
                ("learning/unrelated.md", b"unrelated first\n"),
            ])
            before = provenance.plugin_identity(root)
            (root / "learning" / "unrelated.md").write_text(
                "unrelated second\n", encoding="utf-8"
            )
            unrelated_changed = provenance.plugin_identity(root)
            (root / "learning" / "README.md").write_text("second\n", encoding="utf-8")
            referenced_changed = provenance.plugin_identity(root)
        self.assertIn("learning/README.md", before["scope"]["included"])
        self.assertNotIn("learning/unrelated.md", before["scope"]["included"])
        self.assertEqual(before["sha256"], unrelated_changed["sha256"])
        self.assertNotEqual(unrelated_changed["sha256"], referenced_changed["sha256"])

    @unittest.skipUnless(shutil.which("git"), "git is required for Git identity coverage")
    def test_git_head_and_dirty_boolean_are_recorded_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            git(root, "init", "-q")
            git(root, "config", "core.autocrlf", "false")
            git(root, "add", ".")
            git(
                root, "-c", "user.name=Eval Test", "-c", "user.email=eval@example.invalid",
                "commit", "-qm", "baseline",
            )
            clean = provenance.plugin_identity(root)
            self.assertRegex(clean["git_head"], r"^[0-9a-f]{40,64}$")
            self.assertIs(clean["git_dirty"], False)
            unrelated = root / "docs" / "note.md"
            unrelated.parent.mkdir()
            unrelated.write_text("dirty but outside runtime scope\n", encoding="utf-8")
            dirty_unrelated = provenance.plugin_identity(root)
            self.assertIs(dirty_unrelated["git_dirty"], True)
            self.assertEqual(clean["sha256"], dirty_unrelated["sha256"])
            (root / "agents" / "probe.md").write_text("dirty\n", encoding="utf-8")
            dirty = provenance.plugin_identity(root)
            self.assertIs(dirty["git_dirty"], True)
            self.assertNotEqual(clean["sha256"], dirty["sha256"])


    def test_symlink_in_runtime_tree_is_rejected_where_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            target = root / "target.md"
            target.write_text("target", encoding="utf-8")
            link = root / "agents" / "linked.md"
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            with self.assertRaises(provenance.ProvenanceError):
                provenance.plugin_identity(root)


class FrozenPluginTest(unittest.TestCase):
    """The A -> B -> A defence, driven directly rather than through a runner.

    Endpoint hashing cannot see an edit that is made and undone while sessions are loading the
    source checkout, so a measurement executes bytes collected for one content identity out of a
    private copy. These used to be exercised through the retiring runner's `main`; the behaviour
    belongs to these two functions, so they are driven here.
    """

    def _plugin(self, root: Path) -> bytes:
        (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
        (root / ".claude-plugin" / "plugin.json").write_bytes(b'{"name":"probe"}\n')
        (root / "agents").mkdir(exist_ok=True)
        content = b"---\nname: probe\n---\nfirst\n"
        (root / "agents" / "probe.md").write_bytes(content)
        return content

    def test_the_frozen_copy_keeps_the_bytes_an_edit_and_undo_would_hide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp).resolve() / "plugin"
            plugin.mkdir()
            original = self._plugin(plugin)
            with provenance.frozen_plugin(plugin) as (frozen, identity):
                self.assertNotEqual(plugin, frozen)
                self.assertEqual(original, (frozen / "agents" / "probe.md").read_bytes())
                # The edit-and-undo the endpoint hash cannot see, made mid-measurement.
                (plugin / "agents" / "probe.md").write_bytes(b"temporary mid-run bytes\n")
                self.assertEqual(
                    original,
                    (frozen / "agents" / "probe.md").read_bytes(),
                    "the executing copy followed an edit to the source checkout",
                )
                (plugin / "agents" / "probe.md").write_bytes(original)
                self.assertEqual(identity["sha256"], provenance.plugin_identity(frozen)["sha256"])
            provenance.verify_frozen_plugin(plugin, identity)

    def test_a_mutation_left_in_place_is_refused_at_the_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp).resolve() / "plugin"
            plugin.mkdir()
            self._plugin(plugin)
            with provenance.frozen_plugin(plugin) as (_frozen, identity):
                (plugin / "agents" / "probe.md").write_bytes(b"---\nname: probe\n---\nsecond\n")
            with self.assertRaisesRegex(provenance.ProvenanceError, "changed while the batch"):
                provenance.verify_frozen_plugin(plugin, identity)

    def test_the_private_copy_is_gone_once_the_measurement_ends(self) -> None:
        """It carries a copy of the plugin under test; leaving it behind is a disclosure."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp).resolve() / "plugin"
            plugin.mkdir()
            self._plugin(plugin)
            with provenance.frozen_plugin(plugin) as (frozen, _identity):
                self.assertTrue(frozen.exists())
            self.assertFalse(frozen.exists())


class ExecutableModeTest(unittest.TestCase):
    """Round 9: the private copy was written with the process umask, losing the execute bit.

    A plugin that runs one of its own files -- a hook command under `${CLAUDE_PLUGIN_ROOT}` --
    met `Permission denied` inside the snapshot while the byte-only identity still matched, so
    the benchmark measured behaviour the supplied plugin does not have. Identity stays
    byte-derived on purpose; only the execute bits travel.
    """

    def test_an_executable_plugin_file_stays_executable_in_the_frozen_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp).resolve() / "plugin"
            (plugin / ".claude-plugin").mkdir(parents=True)
            (plugin / ".claude-plugin" / "plugin.json").write_bytes(b'{"name":"probe"}\n')
            (plugin / "agents").mkdir()
            (plugin / "agents" / "probe.md").write_bytes(b"---\nname: probe\n---\nx\n")
            # Referenced through ${CLAUDE_PLUGIN_ROOT}, which is what pulls a script into the
            # runtime file set -- and is exactly the shape that executes it.
            hook = plugin / "hooks" / "hooks.json"
            hook.parent.mkdir()
            hook.write_text("${CLAUDE_PLUGIN_ROOT}/scripts/check.sh", encoding="utf-8")
            runner = plugin / "scripts" / "check.sh"
            runner.parent.mkdir()
            runner.write_bytes(b"#!/bin/sh\nexit 0\n")
            runner.chmod(0o755)
            self.assertIn(
                "scripts/check.sh", provenance.plugin_identity(plugin)["scope"]["included"],
                "fixture guard: the executable must be in the runtime set to mean anything",
            )
            with provenance.frozen_plugin(plugin) as (frozen, _identity):
                copied = frozen / "scripts" / "check.sh"
                self.assertTrue(copied.exists())
                self.assertTrue(
                    os.access(copied, os.X_OK),
                    "an executable the plugin runs itself must still be executable when frozen",
                )
                # A non-executable neighbour must NOT gain the bit.
                self.assertFalse(os.access(frozen / "agents" / "probe.md", os.X_OK))


class ExecuteMaskIdentityTest(unittest.TestCase):
    """Round 14: the identity bound "any execute bit", not the bits themselves.

    `frozen_plugin` carries the exact mask across, so 0450 and 0500 reproduce differently in the
    snapshot -- the evaluator's own user can run one and not the other -- while a boolean gave
    both plugins one identity and let them look reusable against each other.
    """

    def _plugin_with_mode(self, root: Path, mode: int) -> Path:
        (root / ".claude-plugin").mkdir(parents=True)
        (root / ".claude-plugin" / "plugin.json").write_bytes(b'{"name":"probe"}\n')
        (root / "agents").mkdir()
        (root / "agents" / "probe.md").write_bytes(b"---\nname: probe\n---\nx\n")
        hook = root / "hooks" / "hooks.json"
        hook.parent.mkdir()
        hook.write_text("${CLAUDE_PLUGIN_ROOT}/scripts/check.sh", encoding="utf-8")
        runner = root / "scripts" / "check.sh"
        runner.parent.mkdir()
        runner.write_bytes(b"#!/bin/sh\nexit 0\n")
        runner.chmod(mode)
        return runner

    def test_two_execute_masks_do_not_share_one_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / "plugin"
            runner = self._plugin_with_mode(root, 0o450)
            owner_cannot_run = provenance.plugin_identity(root)["sha256"]
            runner.chmod(0o500)
            owner_can_run = provenance.plugin_identity(root)["sha256"]
            self.assertNotEqual(
                owner_cannot_run, owner_can_run,
                "identical bytes the evaluator can and cannot execute are not one identity",
            )

    def test_the_group_and_other_bits_are_bound_too(self) -> None:
        """The mask is three bits: `frozen_plugin` carries all of them, so all of them count."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / "plugin"
            runner = self._plugin_with_mode(root, 0o700)
            owner_only = provenance.plugin_identity(root)["sha256"]
            runner.chmod(0o711)
            everyone = provenance.plugin_identity(root)["sha256"]
            self.assertNotEqual(owner_only, everyone)


class CanonicalTempdirTest(unittest.TestCase):
    """macOS's /var -> /private/var symlink, staged on any platform.

    The retired runner canonicalized `tempfile.tempdir` at import because the ancestor walk
    refuses a symlinked path component and every temp path on macOS has one. The move into this
    module dropped it, nothing on the Linux PR job could notice, and the three-OS matrix runs
    only after merge -- so the failure is staged here instead of waited for.
    """

    def setUp(self) -> None:
        previous = tempfile.tempdir
        self.addCleanup(setattr, tempfile, "tempdir", previous)
        self.base = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.base, True)
        real = self.base / "private_scratch"
        real.mkdir()
        self.link = self.base / "scratch"
        self.link.symlink_to(real, target_is_directory=True)
        self.plugin = self.base / "plugin"
        self.plugin.mkdir()
        (self.plugin / ".claude-plugin").mkdir()
        (self.plugin / ".claude-plugin" / "plugin.json").write_bytes(b'{"name":"probe"}\n')
        (self.plugin / "agents").mkdir()
        (self.plugin / "agents" / "probe.md").write_bytes(b"---\nname: probe\n---\nfirst\n")

    def test_a_symlinked_temp_root_makes_the_private_copy_unreadable(self) -> None:
        """The macOS failure itself: the walk refuses the frozen copy's own parent."""
        tempfile.tempdir = str(self.link)
        with self.assertRaisesRegex(provenance.ProvenanceError, "unsafe provenance path"):
            with provenance.frozen_plugin(self.plugin):
                pass

    def test_canonicalizing_the_temp_root_makes_it_usable_again(self) -> None:
        tempfile.tempdir = str(self.link)
        provenance.canonicalize_tempdir()
        with provenance.frozen_plugin(self.plugin) as (frozen, identity):
            self.assertTrue(frozen.exists())
            self.assertEqual(identity["sha256"], provenance.plugin_identity(frozen)["sha256"])

    def test_importing_the_module_canonicalizes_the_temp_root(self) -> None:
        """Pins the import-time call, not just the function: removing it must fail something."""
        env = {**os.environ, "TMPDIR": str(self.link)}
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        program = "import tempfile, fleet.provenance; print(tempfile.gettempdir())"
        result = subprocess.run(
            [sys.executable, "-c", program],
            cwd=str(Path(__file__).resolve().parents[1]), env=env,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(str(self.link.resolve()), result.stdout.strip())


class ValidatedMembersTest(unittest.TestCase):
    """A cluster's membership decides what every negative in it forbids, so a malformed one is
    refused rather than silently narrowed to whatever survived."""

    def test_a_well_formed_membership_is_returned_in_order(self) -> None:
        self.assertEqual(["a", "b"], provenance.validated_members(["a", "b"]))

    def test_a_malformed_membership_is_refused(self) -> None:
        for members in (None, [], "a", ["a", ""], ["a", 3], ["a", "   "], [["a"]]):
            with self.subTest(members=members):
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.validated_members(members)

    def test_a_repeated_member_is_tolerated_rather_than_refused(self) -> None:
        """Not an oversight to fix here: every consumer takes `set(members)`, so a repeat changes
        no verdict, and this records the contract as it is rather than as it reads."""
        self.assertEqual(["a", "a"], provenance.validated_members(["a", "a"]))
