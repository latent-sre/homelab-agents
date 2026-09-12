"""The platform gate must inspect plugin contents, not only its marketplace entry."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import validate_claude_plugin


class ClaudePluginValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        self.files = {
            ".claude-plugin/plugin.json": b'{"name":"example"}\n',
            ".claude-plugin/marketplace.json": b'{"name":"market"}\n',
            "CLAUDE.md": b"@AGENTS.md\n",
            "agents/reader.md": b"---\nname: reader\n---\nRead carefully.\n",
            "skills/broken/SKILL.md": b'---\ndescription: "unclosed\n---\n',
            "skills/broken/references/example.md": b"Keep these bytes.\n",
            "commands/example.md": b"An optional command.\n",
            "hooks/hooks.json": b'{"hooks": {}}\n',
            "scripts/guard.py": b"raise SystemExit(0)\n",
            "workflows/review.js": b"export const meta = {};\n",
            ".mcp.json": b'{"mcpServers": {}}\n',
        }
        for relative, data in self.files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def test_both_targets_are_explicit_and_plugin_bytes_survive_staging(self) -> None:
        targets: list[Path] = []

        def run(argv, **kwargs):
            self.assertEqual(["claude", "plugin", "validate"], argv[:3])
            self.assertEqual("--strict", argv[-1])
            target = Path(argv[3])
            targets.append(target)
            if len(targets) == 2:
                stage = target.parent.parent
                self.assertEqual("plugin.json", target.name)
                self.assertFalse((stage / "CLAUDE.md").exists())
                self.assertFalse((stage / ".claude-plugin/marketplace.json").exists())
                for relative, data in self.files.items():
                    if relative in {"CLAUDE.md", ".claude-plugin/marketplace.json"}:
                        continue
                    self.assertEqual(data, (stage / relative).read_bytes(), relative)
            return subprocess.CompletedProcess(argv, 0)

        self.assertEqual(0, validate_claude_plugin.validate(self.root, "claude", run=run))
        self.assertEqual(self.root / ".claude-plugin/marketplace.json", targets[0])
        self.assertFalse(targets[1].parent.parent.exists(), "staging should be cleaned up")
        for relative, data in self.files.items():
            self.assertEqual(data, (self.root / relative).read_bytes())

    def test_either_target_failure_is_retained_and_both_are_checked(self) -> None:
        for statuses in ((1, 0), (0, 1), (2, 0), (0, 2)):
            with self.subTest(statuses=statuses):
                results = [subprocess.CompletedProcess([], code) for code in statuses]
                run = mock.Mock(side_effect=results)
                result = validate_claude_plugin.validate(self.root, "claude", run=run)
                self.assertNotEqual(0, result)
                self.assertEqual(2, run.call_count)

    def test_missing_cli_is_not_a_pass(self) -> None:
        with mock.patch.object(validate_claude_plugin.shutil, "which", return_value=None):
            self.assertEqual(2, validate_claude_plugin.main(["--root", str(self.root)]))

    def test_failed_invocation_or_copy_is_not_a_pass(self) -> None:
        with mock.patch.object(validate_claude_plugin.shutil, "which", return_value="claude"):
            with mock.patch.object(validate_claude_plugin, "validate", side_effect=OSError("missing")):
                self.assertEqual(2, validate_claude_plugin.main(["--root", str(self.root)]))
            with mock.patch.object(
                validate_claude_plugin, "validate",
                side_effect=subprocess.TimeoutExpired("claude", 60),
            ):
                self.assertEqual(2, validate_claude_plugin.main(["--root", str(self.root)]))


@unittest.skipUnless(shutil.which("claude"), "Claude CLI is not installed")
class NativeClaudeContentsTests(unittest.TestCase):
    def test_malformed_skill_and_hook_fail_the_actual_platform_gate(self) -> None:
        source = Path(__file__).resolve().parents[1]
        for relative, data in (
            ("skills/broken/SKILL.md", '---\nname: broken\ndescription: "unclosed\n---\n'),
            ("hooks/hooks.json", "{invalid-json"),
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / ".claude-plugin").mkdir()
                for name in ("plugin.json", "marketplace.json"):
                    shutil.copy2(source / ".claude-plugin" / name, root / ".claude-plugin" / name)
                path = root / relative
                path.parent.mkdir(parents=True)
                path.write_text(data, encoding="utf-8")

                def run(argv, **kwargs):
                    return subprocess.run(argv, capture_output=True, encoding="utf-8", **kwargs)

                self.assertEqual(1, validate_claude_plugin.validate(
                    root, shutil.which("claude"), run=run,
                ))


if __name__ == "__main__":
    unittest.main()
