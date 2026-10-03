"""The probe's offline logic: transcript correlation, verdict polarity, and timeout recovery.

The probe itself drives paid sessions and runs by hand; these tests pin how it reads a
transcript, so a parser change cannot turn a guard failure into a pass without a live run.
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import probe_plugin


class ProbeCliTests(unittest.TestCase):
    def test_help_exits_before_any_live_probe_or_workspace_change(self) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(probe_plugin, "run") as run,
            mock.patch.object(probe_plugin, "_remove_workspace") as remove_workspace,
            contextlib.redirect_stdout(output),
            self.assertRaises(SystemExit) as raised,
        ):
            probe_plugin.main(["--help"])

        self.assertEqual(0, raised.exception.code)
        self.assertIn("usage:", output.getvalue())
        run.assert_not_called()
        remove_workspace.assert_not_called()

class ProbeTimeoutRecoveryTests(unittest.TestCase):
    """PROBE-006: a leg that never answers must not discard the rest of the run.

    The probe used to spawn through `run_completed`, so a session that hit the 600-second limit
    raised `TimeoutExpired` out of whatever leg was running. Every later check -- and every
    result already collected -- went with it, and the operator paid for a full probe to learn
    nothing. Reproduced at the operator's limit in the 2026-09-07 diagnostic correction.
    """

    def test_the_runner_returns_a_timeout_instead_of_raising(self) -> None:
        with mock.patch.object(
            probe_plugin._proc,
            "run",
            return_value=probe_plugin._proc.CommandResult(
                ("claude",), None, "partial transcript", "", timed_out=True, error="timed out"
            ),
        ):
            result = probe_plugin.run(["claude", "-p", "hello"])
        self.assertTrue(result.timed_out)
        # The transcript the run already paid for survives the failure.
        self.assertEqual("partial transcript", result.stdout)

    def test_an_unanswered_leg_is_inconclusive_with_its_own_cause(self) -> None:
        timed_out = probe_plugin._proc.CommandResult(
            ("claude",), None, "", "", timed_out=True, error="timed out"
        )
        never_started = probe_plugin._proc.CommandResult(
            ("claude",), 127, "", "", failed_to_start=True, error="No such file"
        )
        answered = probe_plugin._proc.CommandResult(("claude",), 0, "ok", "")

        self.assertIn("did not answer within 600s", probe_plugin.unanswered_cause(timed_out))
        self.assertIn("could not be started", probe_plugin.unanswered_cause(never_started))
        self.assertIsNone(probe_plugin.unanswered_cause(answered))

        for result in (timed_out, never_started):
            with self.subTest(result=result):
                probe = probe_plugin.Probe()
                with contextlib.redirect_stdout(io.StringIO()):
                    proceeded = probe.answered(result, "a leg that got no answer")
                self.assertFalse(proceeded)
                self.assertEqual([probe_plugin.SKIP], [s for s, *_ in probe.results])
                self.assertNotIn(probe_plugin.FAIL, [s for s, *_ in probe.results])

    def test_an_unclassified_failure_is_reported_not_silenced(self) -> None:
        """The default is to REPORT. Forgetting a classification must never hide a regression.

        The flag marks the ABSENCE side precisely so this is true: a presence-based FAIL added
        later, or simply missed, stays a FAIL on partial evidence. Noisy is recoverable; a
        silently downgraded security regression is not. Four unmarked presence-based verdicts
        were found across three review rounds under the opposite default, which is why the
        default moved rather than the list growing again.
        """
        timed_out = probe_plugin._proc.CommandResult(
            ("claude",), None, "partial", "", timed_out=True, error="timed out"
        )
        probe = probe_plugin.Probe()
        with contextlib.redirect_stdout(io.StringIO()):
            probe.reading(timed_out)
            probe.check(probe_plugin.FAIL, "a denylisted command RAN unguarded")
            probe.check(probe_plugin.FAIL, "a canary was not present", absence=True)
        statuses = {label: status for status, label, _ in probe.results}
        self.assertEqual(
            probe_plugin.FAIL,
            statuses["a denylisted command RAN unguarded"],
            "an unclassified verdict was silenced by a truncated transcript",
        )
        self.assertEqual(probe_plugin.SKIP, statuses["a canary was not present"])

    def test_every_downgradable_verdict_fails_on_a_falsy_predicate(self) -> None:
        """Structural, because prose is not checkable and my first attempt at this lied.

        The earlier version of this test matched the detail text for absence words and flagged
        `PASS if default_hits else FAIL` -- a genuine absence whose prose happens to describe the
        consequence rather than the gap. Classifying semantics from wording produces both false
        alarms and false confidence, so this asserts the shape instead.

        A `probe.check(PASS if X else FAIL, ...)` reaches FAIL when X is FALSY: something was not
        found. A bare `probe.check(FAIL, ...)` is reached because a branch condition was TRUE:
        the oracle saw something. Only the first form may carry `absence=True`, and that is
        decidable from the syntax tree rather than from how the message reads.
        """
        source = Path(probe_plugin.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        offenders = []
        marked = 0
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "check"
                and any(kw.arg == "absence" for kw in node.keywords)
            ):
                continue
            marked += 1
            verdict = node.args[0] if node.args else None
            conditional_on_a_predicate = isinstance(verdict, ast.IfExp) and isinstance(
                verdict.orelse, ast.Name
            ) and verdict.orelse.id == "FAIL"
            if not conditional_on_a_predicate:
                offenders.append(node.lineno)
        self.assertTrue(marked, "no absence-based verdicts marked; the cascade is unsuppressed")
        self.assertEqual(
            [],
            offenders,
            f"lines {offenders} pass absence=True on an unconditional FAIL. That verdict is "
            f"reached because something WAS observed, and marking it downgradable silences it "
            f"on a truncated transcript.",
        )

    def test_an_unanswered_agent_session_reports_why_not_just_that(self) -> None:
        """A timeout and a launch failure must not read as "never attempted".

        They send the operator to different places -- wait and re-run, versus repair the
        environment -- and `reading()` stores the cause without putting it in the verdict, so the
        unconditional SKIP on this branch dropped it.
        """
        for result, expected in (
            (
                probe_plugin._proc.CommandResult(
                    ("claude",), None, "", "", timed_out=True, error="timed out"
                ),
                "did not answer within 600s",
            ),
            (
                probe_plugin._proc.CommandResult(
                    ("claude",), 127, "", "", failed_to_start=True, error="No such file"
                ),
                "could not be started",
            ),
        ):
            with self.subTest(result=result):
                probe = probe_plugin.Probe()
                with contextlib.redirect_stdout(io.StringIO()):
                    probe.reading(result)
                    cause = probe_plugin.unanswered_cause(result)
                    probe.check(
                        probe_plugin.SKIP,
                        "the guard DENIED a --agent main session's denylisted command",
                        cause or "the session never attempted the command",
                    )
                detail = probe.results[0][2]
                self.assertIn(expected, detail)
                self.assertNotIn("never attempted", detail)


    def test_an_errored_spawn_is_told_apart_from_an_absent_one(self) -> None:
        """`spawn_succeeded` returning False conflated two different findings.

        No correlated result at all is an absence and means nothing on a partial transcript. A
        result that came back marked `is_error` is a plugin-loading or name-resolution failure
        the oracle positively saw, and marking the combined predicate downgradable silenced it.
        """
        agent = "sde-agents:code-reviewer"
        errored = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_1",
                            "name": "Agent",
                            "input": {"subagent_type": agent},
                        }
                    ]
                },
            }
        ) + "\n" + json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "tool_use_id": "call_1", "is_error": True,
                         "content": "boom"}
                    ]
                },
            }
        )
        self.assertTrue(probe_plugin.spawn_errored(errored, agent))
        self.assertFalse(probe_plugin.spawn_succeeded(errored, agent))

        # An absent result is neither a success nor an observed error.
        absent = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_2",
                            "name": "Agent",
                            "input": {"subagent_type": agent},
                        }
                    ]
                },
            }
        )
        self.assertFalse(probe_plugin.spawn_errored(absent, agent))
        self.assertFalse(probe_plugin.spawn_succeeded(absent, agent))

    def test_an_answering_leg_clears_the_previous_session_truncation(self) -> None:
        """`answered` begins reading its result, so a leg that answered is judged on its own.

        Two entry points where only one reset the state: `answered` returned True without
        clearing, so a real regression found by a leg that DID answer was downgraded to
        INCONCLUSIVE because an unrelated earlier session had timed out.
        """
        timed_out = probe_plugin._proc.CommandResult(
            ("claude",), None, "", "", timed_out=True, error="timed out"
        )
        answered = probe_plugin._proc.CommandResult(("claude",), 0, "ok", "")
        probe = probe_plugin.Probe()
        with contextlib.redirect_stdout(io.StringIO()):
            probe.reading(timed_out)
            self.assertTrue(probe.answered(answered, "a leg that did answer"))
            probe.check(probe_plugin.FAIL, "a real regression this leg found")
        statuses = {label: status for status, label, _ in probe.results}
        self.assertEqual(probe_plugin.FAIL, statuses["a real regression this leg found"])

    def test_a_failed_setup_command_is_the_legs_inconclusive_not_a_fleet_failure(self) -> None:
        """Setup is environment. A repository that was never initialised proves nothing."""
        missing_git = probe_plugin._proc.CommandResult(
            ("git", "init", "-q", "/tmp/x"), 127, "", "", failed_to_start=True, error="No such file"
        )
        timed_out = probe_plugin._proc.CommandResult(
            ("git", "add", "-A"), None, "", "", timed_out=True, error="timed out"
        )
        ok = probe_plugin._proc.CommandResult(("git", "init"), 0, "", "")

        self.assertIsNone(probe_plugin.setup_failure([ok, ok]))
        for broken in (missing_git, timed_out):
            with self.subTest(result=broken):
                cause = probe_plugin.setup_failure([ok, broken, ok])
                self.assertIsNotNone(cause)
                self.assertIn("probe setup command", cause)
                self.assertIn(broken.argv[0], cause)

    def test_a_broken_workspace_stops_the_run_before_any_paid_session(self) -> None:
        """No repository means nothing to probe, so the run must not spend on sessions."""
        spawned: list[tuple[str, ...]] = []

        def spawn(cmd, **_kwargs):
            argv = tuple(cmd)
            spawned.append(argv)
            if argv and argv[0] == "git":
                return probe_plugin._proc.CommandResult(
                    argv, 127, "", "", failed_to_start=True, error="No such file"
                )
            return probe_plugin._proc.CommandResult(argv, 0, "", "")

        with (
            mock.patch.object(probe_plugin, "run", side_effect=spawn),
            mock.patch.object(probe_plugin, "CLAUDE", "claude"),
            mock.patch.object(probe_plugin, "_remove_workspace"),
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(probe_plugin, "REPO", Path(tmp)),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = probe_plugin.main([])

        self.assertEqual(2, code, "a broken workspace is INCONCLUSIVE, never a fleet FAIL")
        self.assertEqual(
            [], [argv for argv in spawned if argv and argv[0] == "claude"],
            "the probe spent on a model session against a repository that does not exist",
        )

    def test_a_truncated_transcript_makes_later_checks_unevaluated_not_failed(self) -> None:
        """The PROBE-002 distinction, applied to the whole run.

        A transcript that stops mid-session cannot tell "the canary is absent" from "the oracle
        saw nothing", so a confident FAIL on that evidence is the cascade that made one
        environment condition read as a dozen fleet defects.
        """
        timed_out = probe_plugin._proc.CommandResult(
            ("claude",), None, "", "", timed_out=True, error="timed out"
        )
        answered = probe_plugin._proc.CommandResult(("claude",), 0, "ok", "")
        probe = probe_plugin.Probe()
        with contextlib.redirect_stdout(io.StringIO()):
            probe.check(probe_plugin.FAIL, "before truncation", absence=True)
            probe.reading(timed_out)
            probe.check(probe_plugin.FAIL, "after truncation", absence=True)
            probe.check(probe_plugin.PASS, "a pass is still a pass")
            # A later leg drives its OWN session; a timeout in the previous one must not
            # silence its verdicts.
            probe.reading(answered)
            probe.check(probe_plugin.FAIL, "the next session answered", absence=True)

        statuses = {label: status for status, label, _ in probe.results}
        self.assertEqual(probe_plugin.FAIL, statuses["before truncation"])
        self.assertEqual(probe_plugin.SKIP, statuses["after truncation"])
        # A PASS on partial evidence is still real: the canary was observed, not merely absent.
        self.assertEqual(probe_plugin.PASS, statuses["a pass is still a pass"])
        self.assertEqual(probe_plugin.FAIL, statuses["the next session answered"])
        detail = next(d for _, label, d in probe.results if label == "after truncation")
        self.assertIn("unevaluated", detail)

    def test_a_timed_out_main_session_still_reaches_the_last_leg(self) -> None:
        """The heart of PROBE-006: later legs run their own sessions and must still be reached."""
        sessions: list[str] = []

        def spawn(cmd, **_kwargs):
            """Setup succeeds; only the model sessions time out.

            The distinction is the test's whole point. A `git init` that fails means there is no
            repository to probe, and returning early is right; a SESSION that times out must not
            take the legs that drive their own sessions with it.
            """
            argv = tuple(cmd)
            if argv and argv[0] == "git":
                return probe_plugin._proc.CommandResult(argv, 0, "", "")
            sessions.append(" ".join(str(part) for part in argv))
            return probe_plugin._proc.CommandResult(
                argv, None, "", "", timed_out=True, error="timed out"
            )

        with (
            mock.patch.object(probe_plugin, "run", side_effect=spawn),
            mock.patch.object(probe_plugin, "CLAUDE", "claude"),
            mock.patch.object(probe_plugin, "_remove_workspace"),
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(probe_plugin, "REPO", Path(tmp)),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = probe_plugin.main([])

        # The --agent session is the last leg; reaching it means no earlier timeout ended the run.
        self.assertTrue(
            any("--agent" in session for session in sessions),
            "the run stopped at a timed-out session before the last leg",
        )
        # INCONCLUSIVE, never a green run and never a fleet defect.
        self.assertEqual(2, code)


class ProbeInconclusiveReportingTests(unittest.TestCase):
    """The epilogue must not assert one cause for every inconclusive check.

    Codex review on #151: `report()` attributed every SKIP to Claude Code's sandbox refusing the
    command and told the operator to re-run outside a Claude Code session. That was already wrong
    for a command the agent never attempted and for PROBE-002's uncorrelated spawn; the
    correlation-gap SKIP added in this PR makes it wrong a third way. A probe that prints an
    accurate per-check cause and then contradicts it in the summary sends the operator to fix
    the wrong thing.
    """

    @staticmethod
    def _report(*results: tuple[str, str, str]) -> tuple[int, str]:
        probe = probe_plugin.Probe()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            for status, label, detail in results:
                probe.check(status, label, detail)
            code = probe.report()
        return code, buffer.getvalue()

    def test_the_epilogue_does_not_blame_the_sandbox_for_a_correlation_gap(self) -> None:
        code, out = self._report((
            probe_plugin.SKIP,
            "the guard DENIED a --agent main session's denylisted command",
            "the call was emitted but no tool_result ever correlated to it, so the oracle saw "
            "no verdict: the session exited or truncated first.",
        ))
        self.assertEqual(2, code)
        self.assertIn("no tool_result ever correlated", out, "the real cause must still print")
        self.assertNotIn(
            "Claude Code's own sandbox refused the command",
            out,
            "the summary asserted a cause this check did not report",
        )

    def test_a_sandbox_refusal_still_gets_its_actionable_advice(self) -> None:
        _code, out = self._report((
            probe_plugin.SKIP,
            "the guard DENIED the reviewer's denylisted command",
            "Claude Code's own permission layer refused it before the guard's verdict mattered.",
        ))
        self.assertIn("plain terminal", out)

    def test_a_clean_run_prints_no_inconclusive_epilogue(self) -> None:
        code, out = self._report((probe_plugin.PASS, "everything held", ""))
        self.assertEqual(0, code)
        self.assertNotIn("UNPROVEN", out)


class ProbeTranscriptParserTests(unittest.TestCase):
    def test_tool_consumers_ignore_non_object_tool_input(self) -> None:
        transcript = json.dumps(
            {
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "bash-bad",
                            "name": "Bash",
                            "input": "legacy string input",
                        }
                    ]
                }
            }
        )

        self.assertEqual([], probe_plugin.tool_calls(transcript))
        self.assertEqual({}, probe_plugin.bash_results(transcript))

    def test_bash_results_ignore_non_string_commands_and_correlation_ids(self) -> None:
        transcript = "\n".join(
            (
                json.dumps({
                    "message": {"content": [{
                        "type": "tool_use", "id": "bad-command", "name": "Bash",
                        "input": {"command": ["not", "a", "string"]},
                    }]}
                }),
                json.dumps({
                    "message": {"content": [{
                        "type": "tool_use", "id": ["bad-id"], "name": "Bash",
                        "input": {"command": "echo BAD"},
                    }]}
                }),
                json.dumps({
                    "message": {"content": [{
                        "type": "tool_result", "tool_use_id": ["bad-result-id"],
                        "content": "ignored",
                    }]}
                }),
                json.dumps({
                    "message": {"content": [
                        {
                            "type": "tool_use", "id": "bash-good", "name": "Bash",
                            "input": {"command": "echo GOOD"},
                        },
                        {
                            "type": "tool_result", "tool_use_id": "bash-good",
                            "content": "good result",
                        },
                    ]}
                }),
            )
        )

        self.assertEqual({"echo GOOD": ["good result"]}, probe_plugin.bash_results(transcript))

    def test_an_uncorrelated_bash_call_is_inconclusive_not_an_unguarded_run(self) -> None:
        """PROBE-004: a Bash call with no correlated tool_result proves nothing about the guard.

        `bash_results` supplied "" for such a call, so `result_for` returned an empty string
        rather than signalling the gap; the guard checks then fell through to their FAIL branch
        and recorded "the command RAN UNGUARDED" with an empty Result. A session that emitted
        the call and then exited nonzero or truncated is the probe's INCONCLUSIVE case - the
        same distinction PROBE-002 and PROBE-003 already draw.
        """
        transcript = json.dumps({"message": {"content": [{
            "type": "tool_use", "id": "bash-uncorrelated", "name": "Bash",
            "input": {"command": "find . -exec AGENTFLAG_PROBE"},
        }]}})

        pairs = probe_plugin.bash_results(transcript)
        self.assertEqual({"find . -exec AGENTFLAG_PROBE": [None]}, pairs)

        attempted, result = probe_plugin.result_for("AGENTFLAG_PROBE", pairs)
        self.assertTrue(attempted, "the call WAS emitted; the session simply never answered it")
        self.assertEqual([], probe_plugin.observed(result),
                         "no correlated result, so there is nothing to grade")

    def test_a_repeated_command_keeps_its_observed_result_over_a_later_gap(self) -> None:
        """Codex review on #151: the map is command-keyed, so a duplicate call overwrote evidence.

        An agent that retries the same denylisted command produces two `tool_use` ids for one
        command string. If the first RAN and returned a result, and the retry was emitted before
        the transcript truncated, later-wins replaced the observed result with the correlation
        gap -- and the guard check downgraded a detected FAILURE to INCONCLUSIVE. A gap is the
        absence of evidence and must never displace evidence.
        """
        def transcript(*blocks: dict) -> str:
            return json.dumps({"message": {"content": list(blocks)}})

        ran_then_truncated = transcript(
            {"type": "tool_use", "id": "call-1", "name": "Bash",
             "input": {"command": "find . -exec REVIEWER_PROBE"}},
            {"type": "tool_result", "tool_use_id": "call-1", "content": "ran unguarded"},
            {"type": "tool_use", "id": "call-2", "name": "Bash",
             "input": {"command": "find . -exec REVIEWER_PROBE"}},
        )
        self.assertEqual(
            {"find . -exec REVIEWER_PROBE": ["ran unguarded", None]},
            probe_plugin.bash_results(ran_then_truncated),
            "the observed result is the evidence; the retry's gap must not displace it",
        )
        self.assertEqual(
            ["ran unguarded"],
            probe_plugin.observed(
                probe_plugin.result_for(
                    "REVIEWER_PROBE", probe_plugin.bash_results(ran_then_truncated)
                )[1]
            ),
        )

        truncated_then_ran = transcript(
            {"type": "tool_use", "id": "call-1", "name": "Bash",
             "input": {"command": "find . -exec REVIEWER_PROBE"}},
            {"type": "tool_use", "id": "call-2", "name": "Bash",
             "input": {"command": "find . -exec REVIEWER_PROBE"}},
            {"type": "tool_result", "tool_use_id": "call-2", "content": "ran unguarded"},
        )
        self.assertEqual(
            {"find . -exec REVIEWER_PROBE": [None, "ran unguarded"]},
            probe_plugin.bash_results(truncated_then_ran),
            "order must not decide it either: the correlated result wins from either side",
        )

    def test_every_correlated_result_is_kept_for_a_repeated_command(self) -> None:
        """Retires the merge-precedence tests: there is no merge left to get wrong.

        Two rounds of review killed two opposite precedences -- first-wins hid a run behind a
        denial, unguarded-wins hid a denial behind a run -- because the reviewer check and the
        main-loop check read the SAME evidence with opposite polarity. One value cannot serve
        both, so the parser now returns all of them and each check decides. The old tests pinned
        a decision that no longer exists; these pin the evidence and the two verdicts instead.
        """
        def transcript(*results: str) -> str:
            blocks = []
            for index, body in enumerate(results):
                blocks.append({"type": "tool_use", "id": f"c{index}", "name": "Bash",
                               "input": {"command": "find . -exec PROBE"}})
                if body is not None:
                    blocks.append({"type": "tool_result", "tool_use_id": f"c{index}",
                                   "content": body})
            return json.dumps({"message": {"content": blocks}})

        RAN = "total 12 drwxr-xr-x repo"
        both = probe_plugin.bash_results(transcript(probe_plugin.GUARD_DENY, RAN))
        self.assertEqual({"find . -exec PROBE": [probe_plugin.GUARD_DENY, RAN]}, both)
        self.assertEqual(
            both, probe_plugin.bash_results(transcript(probe_plugin.GUARD_DENY, RAN)),
            "order is preserved, not resolved",
        )

    def test_each_check_reads_the_shared_evidence_with_its_own_polarity(self) -> None:
        """The reviewer must be denied; the main loop must not. Same input, opposite verdicts."""
        RAN = "total 12 drwxr-xr-x repo"
        DENY = probe_plugin.GUARD_DENY

        for label, results in (
            ("denied then ran", [DENY, RAN]),
            ("ran then denied", [RAN, DENY]),
        ):
            with self.subTest(order=label):
                seen = probe_plugin.observed(results)
                # Reviewer polarity: any unguarded run is the failure.
                self.assertTrue(
                    probe_plugin.unguarded_runs(seen),
                    "a guard that allowed one attempt has not held",
                )
                # Main-loop polarity: any denial is the failure.
                self.assertTrue(
                    [r for r in seen if DENY in r],
                    "the guard caught the user's own Bash at least once",
                )

        denied_twice = probe_plugin.observed([DENY, DENY])
        self.assertEqual([], probe_plugin.unguarded_runs(denied_twice),
                         "denied twice is denied -- the aggregate must not invent a failure")

        gap_only = probe_plugin.observed([None, None])
        self.assertEqual([], gap_only, "a correlation gap is never evidence in either direction")

    def test_a_command_never_attempted_stays_distinct_from_one_never_answered(self) -> None:
        """The two INCONCLUSIVE causes need different operator actions, so they stay separable."""
        self.assertEqual((False, []), probe_plugin.result_for("ABSENT_PROBE", {}))

    def test_a_correlated_empty_result_remains_a_real_gradeable_answer(self) -> None:
        """An empty tool_result is the command running and printing nothing - that IS evidence.

        The repair must not swallow it: only the absence of any correlated result is the gap.
        """
        transcript = json.dumps({"message": {"content": [
            {"type": "tool_use", "id": "bash-empty", "name": "Bash",
             "input": {"command": "find . -exec MAINLOOP_PROBE"}},
            {"type": "tool_result", "tool_use_id": "bash-empty", "content": ""},
        ]}})

        pairs = probe_plugin.bash_results(transcript)
        self.assertEqual({"find . -exec MAINLOOP_PROBE": [""]}, pairs)
        self.assertEqual((True, [""]), probe_plugin.result_for("MAINLOOP_PROBE", pairs))

    def test_agent_consumers_ignore_non_object_tool_input(self) -> None:
        transcript = json.dumps(
            {
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "agent-bad",
                            "name": "Agent",
                            "input": "sde-agents:sde-fullstack",
                        },
                        {
                            "type": "tool_result",
                            "tool_use_id": "agent-bad",
                            "content": "not a valid spawn",
                            "is_error": False,
                        },
                    ]
                }
            }
        )

        self.assertFalse(
            probe_plugin.spawn_succeeded(transcript, "sde-agents:sde-fullstack")
        )

        malformed_ids = "\n".join((
            json.dumps({
                "message": {"content": [{
                    "type": "tool_use",
                    "id": ["bad-agent-id"],
                    "name": "Agent",
                    "input": {"subagent_type": "sde-agents:sde-fullstack"},
                }]}
            }),
            json.dumps({
                "message": {"content": [{
                    "type": "tool_result",
                    "tool_use_id": ["bad-result-id"],
                    "content": "ignored",
                    "is_error": False,
                }]}
            }),
            json.dumps({
                "message": {"content": [
                    {
                        "type": "tool_use",
                        "id": "agent-good",
                        "name": "Agent",
                        "input": {"subagent_type": "sde-agents:sde-fullstack"},
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "agent-good",
                        "content": "valid spawn",
                        "is_error": False,
                    },
                ]}
            }),
        ))

        self.assertTrue(
            probe_plugin.spawn_succeeded(
                malformed_ids, "sde-agents:sde-fullstack"
            )
        )

    def test_spawn_success_prefers_the_structured_agent_target(self) -> None:
        transcript = json.dumps({
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "agent-wrong",
                        "name": "Agent",
                        "input": {
                            "subagent_type": "sde-agents:code-reviewer",
                            "prompt": "Discuss sde-agents:sde-fullstack.",
                        },
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "agent-wrong",
                        "content": "review complete",
                        "is_error": False,
                    },
                ]
            }
        })

        self.assertFalse(
            probe_plugin.spawn_succeeded(transcript, "sde-agents:sde-fullstack")
        )

    def test_consumers_skip_invalid_shapes_without_losing_correlations(self) -> None:
        transcript = "\n".join(
            (
                "not json",
                "42",
                json.dumps({"message": "diagnostic"}),
                json.dumps(
                    {
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "bash-1",
                                    "name": "Bash",
                                    "input": {"command": "echo PROBE"},
                                },
                                {
                                    "type": "tool_use",
                                    "id": "agent-1",
                                    "name": "Agent",
                                    "input": {
                                        "subagent_type": "sde-agents:sde-fullstack"
                                    },
                                },
                                "non-object block",
                            ]
                        }
                    }
                ),
                json.dumps(
                    {
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "bash-1",
                                    "content": "bash ok",
                                },
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "agent-1",
                                    "content": [{"text": "agent ok"}],
                                    "is_error": False,
                                },
                            ]
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            ["bash-1", "agent-1"],
            [call["id"] for call in probe_plugin.tool_calls(transcript)],
        )
        self.assertEqual({"echo PROBE": ["bash ok"]}, probe_plugin.bash_results(transcript))
        self.assertTrue(probe_plugin.spawn_succeeded(transcript, "sde-agents:sde-fullstack"))


if __name__ == "__main__":
    unittest.main()
