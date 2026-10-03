from __future__ import annotations

import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import install_codex_agents


class InstallCodexAgentsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "source"
        self.target = self.root / "target"
        self.source.mkdir()
        (self.source / "reviewer.toml").write_text(
            "# generated\nname = \"reviewer\"\n",
            encoding="utf-8",
        )
        (self.source / "builder.toml").write_text(
            "# generated\nname = \"builder\"\n",
            encoding="utf-8",
        )

    def test_install_writes_managed_copies_and_then_is_idempotent(self) -> None:
        plan = install_codex_agents.build_sync_plan(self.source, self.target)
        self.assertEqual(2, len(plan.writes))
        self.assertFalse(plan.conflicts)

        install_codex_agents.apply_sync_plan(plan)
        reviewer = (self.target / "reviewer.toml").read_text(encoding="utf-8")
        self.assertTrue(reviewer.startswith(install_codex_agents.INSTALL_MARKER))

        second_plan = install_codex_agents.build_sync_plan(self.source, self.target)
        self.assertFalse(second_plan.out_of_sync)

    def test_semantically_equal_imported_copy_is_safely_adopted(self) -> None:
        self.target.mkdir()
        (self.source / "reviewer.toml").write_text(
            "# generated\n"
            'name = "reviewer"\n'
            'description = "Reviews code"\n'
            'sandbox_mode = "read-only"\n'
            "developer_instructions = '''\nReview carefully.\n'''\n",
            encoding="utf-8",
        )
        imported = self.target / "reviewer.toml"
        imported.write_text(
            'name = "reviewer"\n'
            "description = 'Reviews code'\n"
            'sandbox_mode = "read-only"\n'
            'developer_instructions = """Review carefully."""\n',
            encoding="utf-8",
        )

        plan = install_codex_agents.build_sync_plan(self.source, self.target)

        self.assertIn(imported, dict(plan.writes))
        self.assertFalse(plan.conflicts)
        install_codex_agents.apply_sync_plan(plan)
        self.assertTrue(
            imported.read_text(encoding="utf-8").startswith(
                install_codex_agents.INSTALL_MARKER
            )
        )

    def test_semantic_adoption_rejects_extra_or_changed_authority(self) -> None:
        self.target.mkdir()
        (self.source / "reviewer.toml").write_text(
            'name = "reviewer"\n'
            'description = "Reviews code"\n'
            'sandbox_mode = "read-only"\n'
            'developer_instructions = "Review carefully."\n',
            encoding="utf-8",
        )

        for suffix in (
            'skills = ["extra-authority"]\n',
            'developer_instructions = "Different instructions."\n',
        ):
            with self.subTest(suffix=suffix):
                target = self.target / "reviewer.toml"
                base = (
                    'name = "reviewer"\n'
                    'description = "Reviews code"\n'
                    'sandbox_mode = "read-only"\n'
                )
                target.write_text(
                    base
                    + (
                        'developer_instructions = "Review carefully."\n' + suffix
                        if suffix.startswith("skills")
                        else suffix
                    ),
                    encoding="utf-8",
                )

                plan = install_codex_agents.build_sync_plan(self.source, self.target)

                self.assertEqual((target,), plan.conflicts)
                self.assertNotIn(target, dict(plan.writes))

    def test_unmanaged_collision_aborts_before_any_change(self) -> None:
        self.target.mkdir()
        conflict = self.target / "reviewer.toml"
        conflict.write_text("user-owned\n", encoding="utf-8")

        plan = install_codex_agents.build_sync_plan(self.source, self.target)
        self.assertEqual((conflict,), plan.conflicts)
        with self.assertRaisesRegex(ValueError, "refusing to overwrite unmanaged"):
            install_codex_agents.apply_sync_plan(plan)

        self.assertEqual("user-owned\n", conflict.read_text(encoding="utf-8"))
        self.assertFalse((self.target / "builder.toml").exists())

    def test_prune_removes_only_stale_managed_agents(self) -> None:
        self.target.mkdir()
        stale = self.target / "stale.toml"
        stale.write_text(
            f"{install_codex_agents.INSTALL_MARKER}\nname = \"stale\"\n",
            encoding="utf-8",
        )
        unmanaged = self.target / "personal.toml"
        unmanaged.write_text("name = \"personal\"\n", encoding="utf-8")

        plan = install_codex_agents.build_sync_plan(self.source, self.target)
        self.assertEqual((stale,), plan.removals)
        install_codex_agents.apply_sync_plan(plan)

        self.assertFalse(stale.exists())
        self.assertEqual(
            "name = \"personal\"\n",
            unmanaged.read_text(encoding="utf-8"),
        )

    def test_user_target_honors_codex_home(self) -> None:
        codex_home = self.root / "custom-codex-home"
        codex_home.mkdir()
        with mock.patch.dict(
            os.environ,
            {"CODEX_HOME": str(codex_home)},
        ):
            self.assertEqual(
                (codex_home / "agents").resolve(),
                install_codex_agents._user_agents_directory(),
            )

    def test_user_sync_writes_beneath_codex_home(self) -> None:
        codex_home = self.root / "sync-codex-home"
        codex_home.mkdir()
        with (
            mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}),
            mock.patch("sys.stdout", new=io.StringIO()),
        ):
            self.assertEqual(0, install_codex_agents.main(["--user"]))

        installed = codex_home / "agents" / "code-reviewer.toml"
        self.assertTrue(installed.is_file())
        self.assertTrue(
            installed.read_text(encoding="utf-8").startswith(
                install_codex_agents.INSTALL_MARKER
            )
        )

    def test_user_target_defaults_to_dot_codex_under_home(self) -> None:
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(Path, "home", return_value=self.root),
        ):
            self.assertEqual(
                (self.root / ".codex" / "agents").resolve(),
                install_codex_agents._user_agents_directory(),
            )

    def test_user_target_rejects_missing_codex_home(self) -> None:
        missing = self.root / "missing-codex-home"
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(missing)}):
            with self.assertRaisesRegex(ValueError, "CODEX_HOME.*does not exist"):
                install_codex_agents._user_agents_directory()


if __name__ == "__main__":
    unittest.main()
