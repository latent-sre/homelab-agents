"""The snapshot reads every definition once and the hook rosters as data, never by running."""

from __future__ import annotations

import unittest

from fleet import snapshot
from tests.support import REPO, TempDirTestCase


class SnapshotTests(TempDirTestCase):
    def test_definitions_load_with_fields_and_derived_names(self) -> None:
        fleet = snapshot.Fleet.load(REPO)
        self.assertEqual(10, len(fleet.agents))
        self.assertEqual(20, len(fleet.skills))
        self.assertEqual("sde-agents", fleet.plugin_name)
        self.assertEqual(2, len(fleet.hook_commands))
        reviewer = next(a for a in fleet.agents if a.name == "code-reviewer")
        self.assertIn("Bash", reviewer.tool_bases())
        self.assertEqual("code-reviewer", reviewer.stem)

    def test_a_malformed_definition_is_recorded_not_judged(self) -> None:
        (self.base / "agents").mkdir()
        (self.base / "agents" / "bad.md").write_text("---\ntools Read\n---\n", encoding="utf-8")
        (self.base / "agents" / "raw.md").write_bytes(b"---\nname: x\n\xff\n---\n")
        fleet = snapshot.Fleet.load(self.base)
        self.assertEqual([None, None], [a.fields for a in fleet.agents])
        self.assertFalse(fleet.agents[1].readable)
        self.assertEqual([], fleet.agent_names)
        self.assertFalse(fleet.ships_as_plugin)


class HookScriptTests(TempDirTestCase):
    def test_an_absent_or_unreadable_hook_is_recorded_with_its_reason(self) -> None:
        absent = snapshot.HookScript.load(self.base / "missing.py", "ROSTER")
        self.assertFalse(absent.exists)
        self.assertIsNone(absent.rosters)
        self.assertIn("cannot read hook rosters", absent.error or "")
        hook = self.base / "hook.py"
        hook.write_text('PLUGIN_NAME = "p"\n', encoding="utf-8")
        unreadable = snapshot.HookScript.load(hook, "ROSTER")
        self.assertTrue(unreadable.exists)
        self.assertIsNone(unreadable.rosters)
        self.assertIn("missing module constant(s) ['ROSTER']", unreadable.error or "")
        fleet = snapshot.Fleet.load(self.base)
        self.assertFalse(fleet.guard.exists)
        self.assertFalse(fleet.gate.exists)


class RosterTests(TempDirTestCase):
    def test_real_hook_rosters_read_without_execution(self) -> None:
        guard = snapshot.read_rosters(REPO / "scripts" / "readonly-guard.py", "GUARDED_AGENT_NAMES")
        self.assertEqual("sde-agents", guard.plugin_name)
        self.assertIn("code-reviewer", guard["GUARDED_AGENT_NAMES"])
        gate = snapshot.read_rosters(REPO / "scripts" / "live-effect-gate.py", "GATED_AGENT_NAMES")
        self.assertEqual({"homelab-engineer"}, set(gate["GATED_AGENT_NAMES"]))

    def test_reading_never_runs_the_script(self) -> None:
        hook = self.base / "hook.py"
        hook.write_text(
            'import sys\nsys.exit(99)\nPLUGIN_NAME = "p"\nROSTER = frozenset({"a", "b"})\n',
            encoding="utf-8",
        )
        rosters = snapshot.read_rosters(hook, "ROSTER")
        self.assertEqual({"a", "b"}, set(rosters["ROSTER"]))

    def test_non_literal_or_missing_constants_are_refused(self) -> None:
        hook = self.base / "hook.py"
        hook.write_text('PLUGIN_NAME = "p"\nROSTER = frozenset(load())\n', encoding="utf-8")
        with self.assertRaises(snapshot.RosterError):
            snapshot.read_rosters(hook, "ROSTER")
        hook.write_text('PLUGIN_NAME = "p"\n', encoding="utf-8")
        with self.assertRaises(snapshot.RosterError):
            snapshot.read_rosters(hook, "ROSTER")
        hook.write_text("def (:\n", encoding="utf-8")
        with self.assertRaises(snapshot.RosterError):
            snapshot.read_rosters(hook, "ROSTER")


if __name__ == "__main__":
    unittest.main()
