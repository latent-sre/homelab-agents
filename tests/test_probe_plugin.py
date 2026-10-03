"""The probe's offline logic: a scripted run through main(), and the correlation it grades on.

The probe drives paid sessions and runs by hand, so these tests replay transcripts through the
real main(): a clean run passes all nine checks, and each defect the probe exists to catch turns
exactly its own check red.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import probe_plugin

DENIED = "Blocked: this is a read-only agent."
REVIEWER = "sde-agents:code-reviewer"
HOMELAB = "sde-agents:homelab-engineer"
AGENT_CMD = "echo AGENTFLAG_PROBE && find . -name '*.md' -exec wc -l {} \\;"


def use(tool_id: str, name: str, tool_input: dict) -> dict:
    return {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}


def result(tool_id: str, content: str, is_error: bool = False) -> dict:
    return {"type": "tool_result", "tool_use_id": tool_id, "content": content, "is_error": is_error}


def transcript(*blocks: dict) -> str:
    return "\n".join(json.dumps({"message": {"content": [block]}}) for block in blocks)


def main_session(**overrides: object) -> list[dict]:
    """The blocks of a session where every check holds; `overrides` replace one result."""
    onboard = overrides.get("onboard_path", "C:/plugin/skills/service-onboard/SKILL.md")
    return [
        use("a1", "Agent", {"subagent_type": REVIEWER}),
        result("a1", "done", is_error=bool(overrides.get("reviewer_spawn_error"))),
        use("a2", "Agent", {"subagent_type": HOMELAB}),
        result("a2", "path read"),
        use("r1", "Read", {"file_path": onboard}),
        result("r1", "# Service onboarding"),
        use("b1", "Bash", {"command": probe_plugin.REVIEWER_CMD}),
        result("b1", str(overrides.get("reviewer_result", DENIED))),
        use("b2", "Bash", {"command": probe_plugin.MAINLOOP_CMD}),
        result(
            "b2",
            str(overrides.get("mainloop_result", "./README.md")),
            is_error=bool(overrides.get("mainloop_error")),
        ),
    ]


def run_probe(main_blocks: list[dict], agent_result: str = DENIED) -> tuple[int, str]:
    """Run main() against scripted sessions; return the exit code and the printed report."""

    def spawn(cmd, **_kwargs):
        argv = tuple(str(part) for part in cmd)
        if "--agent" in argv:
            bash = use("c1", "Bash", {"command": AGENT_CMD})
            stdout = transcript(bash, result("c1", agent_result))
        elif argv[0] == "claude":
            stdout = transcript(*main_blocks)
        else:
            stdout = ""
        return probe_plugin.proc.CommandResult(argv, 0, stdout, "")

    output = io.StringIO()
    with (
        mock.patch.object(probe_plugin, "run", side_effect=spawn),
        mock.patch.object(probe_plugin, "CLAUDE", "claude"),
        tempfile.TemporaryDirectory() as tmp,
        mock.patch.object(probe_plugin, "REPO", Path(tmp)),
        contextlib.redirect_stdout(output),
    ):
        code = probe_plugin.main([])
    return code, output.getvalue()


def run_with(spawn) -> tuple[int, str]:
    output = io.StringIO()
    with (
        mock.patch.object(probe_plugin, "run", side_effect=spawn),
        mock.patch.object(probe_plugin, "CLAUDE", "claude"),
        tempfile.TemporaryDirectory() as tmp,
        mock.patch.object(probe_plugin, "REPO", Path(tmp)),
        contextlib.redirect_stdout(output),
    ):
        code = probe_plugin.main([])
    return code, output.getvalue()


class ScriptedRunTests(unittest.TestCase):
    def test_help_exits_before_any_session_or_workspace_change(self) -> None:
        with (
            mock.patch.object(probe_plugin, "run") as run,
            mock.patch.object(probe_plugin, "_remove_workspace") as remove,
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            probe_plugin.main(["--help"])
        self.assertEqual(0, raised.exception.code)
        run.assert_not_called()
        remove.assert_not_called()

    def test_a_clean_run_passes_every_check(self) -> None:
        code, out = run_probe(main_session())
        self.assertEqual(0, code, out)
        self.assertIn("9/9 passed", out)

    def test_each_defect_fails_exactly_its_own_check(self) -> None:
        cases = {
            "the guard DENIED the reviewer's denylisted command": (
                main_session(reviewer_result="./README.md"), DENIED
            ),
            "the guard IGNORED the main loop's identical command": (
                main_session(mainloop_result=DENIED), DENIED
            ),
            "the guard DENIED a --agent main session's denylisted command": (
                main_session(), "4 ./README.md"
            ),
            f"{REVIEWER} spawned and returned without error": (
                main_session(reviewer_spawn_error=True), DENIED
            ),
            "the path was EXPANDED, not a literal ${CLAUDE_PLUGIN_ROOT}": (
                main_session(onboard_path="${CLAUDE_PLUGIN_ROOT}/skills/service-onboard/SKILL.md"),
                DENIED,
            ),
        }
        for label, (blocks, agent_result) in cases.items():
            with self.subTest(check=label):
                code, out = run_probe(blocks, agent_result)
                self.assertEqual(1, code)
                failed = [line for line in out.splitlines() if line.startswith("  [FAIL]")]
                self.assertEqual([f"  [FAIL] {label}"], failed, out)

    def test_an_errored_main_loop_result_does_not_prove_the_guard_stayed_silent(self) -> None:
        # A permission refusal or validation error can arrive before the hook runs, so a result
        # without the guard's text only counts when it is not an error.
        blocks = main_session(mainloop_result="Permission to use Bash denied", mainloop_error=True)
        code, out = run_probe(blocks)
        self.assertEqual(1, code)
        failed = [line for line in out.splitlines() if line.startswith("  [FAIL]")]
        self.assertEqual(["  [FAIL] the guard IGNORED the main loop's identical command"], failed)
        self.assertIn("never ran", out)

    def test_a_failed_git_init_runs_no_session(self) -> None:
        spawned: list[tuple[str, ...]] = []

        def spawn(cmd, **_kwargs):
            argv = tuple(str(part) for part in cmd)
            spawned.append(argv)
            if argv[0] == "git":
                return probe_plugin.proc.CommandResult(argv, 127, "", "", failed_to_start=True)
            return probe_plugin.proc.CommandResult(argv, 0, "", "")

        code, _ = run_with(spawn)
        self.assertEqual(1, code)
        self.assertEqual([], [argv for argv in spawned if argv[0] == "claude"])

    def test_a_timed_out_session_fails_and_the_last_leg_still_runs(self) -> None:
        spawned: list[tuple[str, ...]] = []

        def spawn(cmd, **_kwargs):
            argv = tuple(str(part) for part in cmd)
            spawned.append(argv)
            if argv[0] == "claude":
                return probe_plugin.proc.CommandResult(argv, None, "", "", timed_out=True)
            return probe_plugin.proc.CommandResult(argv, 0, "", "")

        code, out = run_with(spawn)
        self.assertEqual(1, code)
        self.assertTrue(any("--agent" in argv for argv in spawned))
        self.assertIn(f"did not answer within {probe_plugin.TIMEOUT}s", out)


class CorrelationTests(unittest.TestCase):
    def test_every_result_is_kept_per_command_and_a_gap_is_none(self) -> None:
        text = transcript(
            use("c1", "Bash", {"command": "find . -exec PROBE"}),
            result("c1", DENIED),
            use("c2", "Bash", {"command": "find . -exec PROBE"}),
            use("c3", "Bash", {"command": ["not", "a", "string"]}),
        )
        self.assertEqual({"find . -exec PROBE": [DENIED, None]}, probe_plugin.bash_results(text))

    def test_the_guarded_verdict_needs_every_observed_result_denied(self) -> None:
        self.assertTrue(probe_plugin.guarded_verdict([DENIED, None])[0])
        for results in (None, [], [None], [DENIED, "ran"], ["Permission denied by Claude Code"]):
            with self.subTest(results=results):
                self.assertFalse(probe_plugin.guarded_verdict(results)[0])

    def test_a_spawn_is_judged_by_its_target_field_not_its_prompt_text(self) -> None:
        text = transcript(
            use("a1", "Agent", {"subagent_type": REVIEWER, "prompt": f"mention {HOMELAB}"}),
            result("a1", "ok"),
        )
        self.assertEqual("ok", probe_plugin.spawn_status(text, REVIEWER))
        self.assertEqual("missing", probe_plugin.spawn_status(text, HOMELAB))


if __name__ == "__main__":
    unittest.main()
