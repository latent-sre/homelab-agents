"""Kernel filesystem primitives: link detection, reads that refuse to guess, atomic writes."""

from __future__ import annotations

import os
import stat
import unittest
from pathlib import Path

from fleet import fs
from tests.support import TempDirTestCase, create_directory_link, remove_directory_link


class _FakeStat:
    """A stat result shaped like Windows reports a junction: plain directory mode, reparse bit."""

    st_mode = stat.S_IFDIR
    st_file_attributes = fs.REPARSE_POINT_FLAG


class LinkDetectionTests(TempDirTestCase):
    def test_reparse_attribute_is_treated_as_a_link_on_every_platform(self) -> None:
        # is_symlink() would say False for this shape; a junction would then be walked into.
        self.assertTrue(fs.is_link_or_reparse(_FakeStat()))

    def test_a_regular_file_and_directory_are_not_links(self) -> None:
        regular = self.base / "file.txt"
        regular.write_text("x", encoding="utf-8")
        self.assertFalse(fs.is_link_or_reparse(regular))
        self.assertFalse(fs.is_link_or_reparse(self.base))

    def test_a_directory_link_is_detected_without_following_it(self) -> None:
        target = self.base / "target"
        target.mkdir()
        link = self.base / "link"
        create_directory_link(target, link)
        try:
            self.assertTrue(fs.is_link_or_reparse(link))
            self.assertFalse(fs.is_link_or_reparse(target))
        finally:
            remove_directory_link(link)

    def test_a_missing_entry_raises_rather_than_reading_as_safe(self) -> None:
        with self.assertRaises(OSError):
            fs.is_link_or_reparse(self.base / "absent")

    def test_the_reparse_flag_never_degrades_to_zero(self) -> None:
        # A zero flag would AND every attribute to False and silently disable the check.
        self.assertNotEqual(fs.REPARSE_POINT_FLAG, 0)


class ReadTests(TempDirTestCase):
    def test_invalid_utf8_reads_as_none_not_a_traceback(self) -> None:
        damaged = self.base / "bad.md"
        damaged.write_bytes(b"---\nname: x\n\xff\xfe\n---\n")
        self.assertIsNone(fs.try_read_text(damaged))
        self.assertIsNone(fs.try_read_text(self.base / "absent.md"))
        good = self.base / "good.md"
        good.write_text("héllo", encoding="utf-8")
        self.assertEqual(fs.try_read_text(good), "héllo")

    def test_runtime_byproducts_are_recognized_by_part_and_suffix(self) -> None:
        self.assertTrue(fs.is_runtime_byproduct(Path("skills/x/__pycache__/y.cpython-311.pyc")))
        self.assertTrue(fs.is_runtime_byproduct(Path("skills/x/scripts/y.PYC")))
        self.assertFalse(fs.is_runtime_byproduct(Path("skills/x/scripts/y.py")))


class AtomicWriteTests(TempDirTestCase):
    def test_write_replaces_content_and_leaves_no_temporary_file(self) -> None:
        target = self.base / "nested" / "out.toml"
        fs.atomic_write_bytes(target, b"first")
        fs.atomic_write_bytes(target, b"second")
        self.assertEqual(target.read_bytes(), b"second")
        self.assertEqual(sorted(p.name for p in target.parent.iterdir()), ["out.toml"])

    def test_a_failed_write_keeps_the_previous_content(self) -> None:
        target = self.base / "out.toml"
        target.write_bytes(b"previous")
        with self.assertRaises(TypeError):
            fs.atomic_write_bytes(target, "not bytes")  # type: ignore[arg-type]
        self.assertEqual(target.read_bytes(), b"previous")
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ["out.toml"])


class IgnoreRuleTests(TempDirTestCase):
    def test_anchored_path_is_ignored_only_at_the_repository_root(self) -> None:
        self.assertTrue(fs.is_ignored(Path(".claude/worktrees")))
        self.assertTrue(fs.is_ignored(Path(".claude/worktrees/agent-1/AGENTS.md")))
        # A basename match would wrongly drop a legitimate shipped `worktrees/` directory.
        self.assertFalse(fs.is_ignored(Path("skills/x/worktrees/README.md")))
        self.assertTrue(fs.is_ignored(Path("scripts/__pycache__/x.pyc")))
        self.assertTrue(fs.is_ignored(Path(".probe-tmp/target-repo/a")))

    def test_copytree_callback_matches_the_predicate(self) -> None:
        root = self.base
        ignore = fs.copytree_ignore(root)
        self.assertEqual(
            ignore(str(root), ["agents", ".git", "__pycache__"]), {".git", "__pycache__"}
        )
        self.assertEqual(ignore(str(root / ".claude"), ["worktrees", "workflows"]), {"worktrees"})
        # The anchored rule fires only for the repository's own `.claude`, not a nested one.
        self.assertEqual(ignore(str(root / "skills" / ".claude"), ["worktrees"]), set())
        self.assertEqual(ignore(os.fspath(root / "skills"), ["worktrees"]), set())


class PortableSegmentTest(unittest.TestCase):
    """`safe_path_segment` gates every generated eval path, on whichever OS the operator runs.

    Separator and `..` checks alone left a class of names that Linux accepts and Windows cannot
    create, so a cluster or case id like `a:b` or `CON` failed as an uncaught OSError from
    `mkdir` -- after the sessions were paid for -- instead of the documented configuration exit.
    The repository validates on three OSes, so the refusal is portable rather than per-host.
    """

    def test_windows_hostile_characters_are_refused_everywhere(self) -> None:
        for value in ("a:b", "case?", "x<y", 'quote"d', "pipe|d", "star*", "a\x01b"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "no Windows path may hold"):
                    fs.safe_path_segment(value, what="cluster")

    def test_a_trailing_dot_or_space_is_refused(self) -> None:
        """Windows strips both silently, so two distinct ids would land in one directory."""
        for value in ("name.", "name "):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "ends in a dot or space"):
                    fs.safe_path_segment(value, what="case id")

    def test_reserved_device_names_are_refused_with_or_without_a_suffix(self) -> None:
        for value in ("CON", "con", "nul.md", "COM1", "lpt9.json"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "reserved Windows device name"):
                    fs.safe_path_segment(value, what="case id")

    def test_the_names_this_repository_actually_uses_still_pass(self) -> None:
        """A portable refusal that rejected the real fleet would be worse than the defect."""
        for value in ("investigation", "prompt-tooling", "pos-diagnose-idle-lab-failure",
                      "craft-vs-fullstack", "a.b.c", "CONSOLE", "communication"):
            with self.subTest(value=value):
                self.assertEqual(value, fs.safe_path_segment(value, what="cluster"))


if __name__ == "__main__":
    unittest.main()
