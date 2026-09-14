"""Check skill-loading evidence and keep its canaries bound to actual skill content.

The builder preloads code-craft and reads backend guidance only for a backend task. Canary
correlation distinguishes those paths; frontend content reveals an unnecessary load. Marker
comments and these source checks keep a copy-edit from silently invalidating that instrument.
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
from tests.support import REPO


class ProbeCanaryTests(unittest.TestCase):
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

    def test_a_root_session_reports_the_workflow_probe_inconclusive_not_failed(self) -> None:
        """PROBE-003: one environment condition read as five fleet defects.

        The five workflow assertions all need `--permission-mode bypassPermissions`, which Claude
        Code refuses under root, so the workflow never launches and every assertion fails as a
        cascade. Telling a broken fleet from a broken environment is the probe's job, and
        INCONCLUSIVE is its documented verdict for the second — reported once, because restating
        a single cause five times is the noise that verdict exists to remove.
        """
        probe = probe_plugin.Probe()
        with (
            mock.patch.object(probe_plugin.os, "geteuid", return_value=0, create=True),
            mock.patch.object(probe_plugin, "run") as run,
            mock.patch.object(probe_plugin.shutil, "copytree") as copytree,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            probe_plugin.probe_workflow_contract(probe)

        run.assert_not_called()
        copytree.assert_not_called()
        self.assertIn("INCONCLUSIVE", output.getvalue())
        statuses = [status for status, *_ in probe.results]
        self.assertEqual([probe_plugin.SKIP], statuses)
        self.assertNotIn(probe_plugin.FAIL, statuses)

    def test_an_uncorrelated_spawn_leaves_the_canaries_unevaluated_not_failed(self) -> None:
        """PROBE-002: "the canary is absent" and "the oracle saw nothing" are different findings.

        The 2026-08-17 run scored 12/19 with both preload canaries failing, and could not say
        whether that was a real regression or the oracle failing to consume an async agent
        launch's result — a signature the 2026-07-30 audit's F-03 had already reproduced. Both
        rendered as FAIL, so settling it needed another paid run. `agent_spawn_results` returning
        nothing now means unevaluated; a result the oracle DID observe, with no canary in it, is
        the real preload failure.
        """
        spawn = json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "toolu_async", "name": "Agent",
                "input": {"subagent_type": "sde-agents:sde-fullstack", "prompt": "build it"},
            }]},
        })
        # The spawn is never correlated to a tool_result, which is the async-launch shape.
        self.assertEqual([], probe_plugin.agent_spawn_results(spawn, "sde-agents:sde-fullstack"))
        # A correlated result with no canary stays a real, distinguishable failure.
        answered = spawn + "\n" + json.dumps({
            "type": "user",
            "message": {"content": [{
                "type": "tool_result", "tool_use_id": "toolu_async",
                "content": "done, no craft content quoted",
            }]},
        })
        results = probe_plugin.agent_spawn_results(answered, "sde-agents:sde-fullstack")
        self.assertEqual(1, len(results))
        self.assertNotIn(probe_plugin.BACKEND_CANARY, results[0])

    def test_an_errored_agent_result_is_not_an_observation(self) -> None:
        """PR #147 round 2: an errored tool_result was read as the agent's answer.

        A timeout or launch failure returns `is_error: true` with error text. Returning that text
        made both preload canaries FAIL — concluding the skills were absent from the agent's
        context when nothing had run. It now reaches the caller's empty-result branch, which
        reports INCONCLUSIVE.
        """
        spawn = json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "toolu_err", "name": "Agent",
                "input": {"subagent_type": "sde-agents:sde-fullstack", "prompt": "build"},
            }]},
        })

        def result(payload: dict) -> list[str]:
            return probe_plugin.agent_spawn_results(
                spawn + "\n" + json.dumps({"type": "user", "message": {"content": [payload]}}),
                "sde-agents:sde-fullstack",
            )

        self.assertEqual([], result({
            "type": "tool_result", "tool_use_id": "toolu_err", "is_error": True,
            "content": "Error: agent timed out",
        }))
        observed = result({
            "type": "tool_result", "tool_use_id": "toolu_err",
            "content": f"{probe_plugin.BACKEND_CANARY} and more",
        })
        self.assertEqual(1, len(observed))

    def test_code_craft_canary_is_present_and_not_supplied_by_the_prompt(self) -> None:
        text = (REPO / "skills" / "code-craft" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(f"**{probe_plugin.CODE_CANARY}**", text)
        for canary in (
            probe_plugin.CODE_CANARY,
            probe_plugin.BACKEND_CANARY,
            probe_plugin.FRONTEND_CANARY,
        ):
            self.assertNotIn(canary, probe_plugin.PROMPT)

    def test_backend_craft_canary_is_present(self) -> None:
        # Asserted via the probe's own constant, not a copied literal: with a duplicate string
        # here, a probe-side canary change would fail live probes while this tripwire stayed
        # green — the exact split-truth this test exists to prevent.
        text = (REPO / "skills" / "backend-craft" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            probe_plugin.BACKEND_CANARY,
            text,
            "scripts/probe_plugin.py uses this canary to prove backend-craft was fetched -- "
            "do not remove or reword it without updating the probe",
        )

    def test_frontend_craft_canary_is_present(self) -> None:
        text = (REPO / "skills" / "frontend-craft" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            probe_plugin.FRONTEND_CANARY,
            text,
            "scripts/probe_plugin.py uses this canary to detect unwanted frontend loading -- "
            "do not remove or reword it without updating the probe",
        )


class BuilderSkillLoadingTests(unittest.TestCase):
    """A backend-only task must prove both selective loading and a real preload."""

    CODE = "Read the neighbors before writing."
    BACKEND = "req_8f3a2c"
    FRONTEND = "color courage"

    @staticmethod
    def call(tool_id, name, **tool_input):
        return {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}

    @staticmethod
    def result(tool_id, content, **fields):
        return {"type": "tool_result", "tool_use_id": tool_id, "content": content, **fields}

    @staticmethod
    def actor_event(actor, block):
        return {"parent_tool_use_id": actor, "message": {"content": [block]}}

    def check_loading(self, *extra, answer=None, fetch=True, fetch_result=True, provenance=True,
                      spawn=None):
        blocks = [spawn if spawn is not None else self.call(
            "builder", "Agent", subagent_type="sde-agents:sde-fullstack",
        )]
        if fetch:
            blocks.append(
                self.call(
                    "backend", "Read", file_path="/plugin/skills/backend-craft/SKILL.md"
                )
            )
            if fetch_result:
                blocks.append(self.result("backend", self.BACKEND))
        blocks.extend(extra)
        if answer is None:
            answer = f"{self.CODE}\n{self.BACKEND}\nNO_FRONTEND_CONTENT"
        if answer is not False:
            blocks.append(self.result("builder", answer))
        events = []
        for block in blocks:
            if "message" in block:
                events.append(block)
                continue
            actor = (
                None
                if block.get("name") == "Agent" or block.get("tool_use_id") == "builder"
                else "builder"
            )
            event = self.actor_event(actor, block)
            if not provenance:
                event.pop("parent_tool_use_id")
            events.append(event)
        transcript = "\n".join(json.dumps(event) for event in events)
        probe = probe_plugin.Probe()
        with contextlib.redirect_stdout(io.StringIO()):
            probe_plugin.probe_builder_skills(probe, transcript)
        return [status for status, *_ in probe.results]

    def test_backend_only_inspection_loads_only_the_needed_layer(self):
        self.assertEqual(["PASS", "PASS", "PASS"], self.check_loading())

    def async_launch(self, *, structured=True):
        # Sanitized shape observed on Claude 2.1.263: the successful tool_result is a launch
        # receipt; task completion arrives later as a root user task-notification.
        event = self.actor_event(None, self.result("builder", [{
            "type": "text",
            "text": "Async agent launched successfully.\nagentId: probe-builder-task\n"
                    "The agent is working in the background.",
        }]))
        if structured:
            event["toolUseResult"] = {
                "isAsync": True, "status": "async_launched", "agentId": "probe-builder-task",
            }
        return event

    def completion(self, *, tool_id="builder", task_id="probe-builder-task", status="completed",
                   actor=None, text_blocks=False):
        content = (
            f"<task-notification>\n<task-id>{task_id}</task-id>\n"
            f"<tool-use-id>{tool_id}</tool-use-id>\n<status>{status}</status>\n"
            f"<result>{self.CODE}\n{self.BACKEND}\nNO_FRONTEND_CONTENT</result>\n"
            "</task-notification>"
        )
        return {
            "type": "user", "parent_tool_use_id": actor,
            "origin": {"kind": "task-notification"},
            "message": {"role": "user", "content": (
                [{"type": "text", "text": content}] if text_blocks else content
            )},
        }

    def test_outer_builder_evidence_requires_root_provenance(self):
        """Matching IDs must not let another actor supply a spawn, answer, or launch receipt."""
        for kind in ("spawn", "answer", "launch", "notification"):
            for origin in ("reviewer", "builder", "missing", "sidechain"):
                with self.subTest(kind=kind, origin=origin):
                    spawn = None
                    extra = []
                    answer = None
                    if kind == "spawn":
                        event = self.actor_event(None, self.call(
                            "builder", "Agent", subagent_type="sde-agents:sde-fullstack",
                        ))
                        spawn = event
                    elif kind == "answer":
                        event = self.actor_event(None, self.result(
                            "builder", f"{self.CODE}\n{self.BACKEND}\nNO_FRONTEND_CONTENT",
                        ))
                        extra = [event]
                        answer = False
                    elif kind == "launch":
                        event = self.async_launch()
                        extra = [event, self.completion()]
                        answer = False
                    else:
                        event = self.completion()
                        extra = [self.async_launch(), event]
                        answer = False
                    if origin == "missing":
                        event.pop("parent_tool_use_id")
                    elif origin == "sidechain":
                        event["isSidechain"] = True
                    else:
                        event["parent_tool_use_id"] = origin
                    self.assertEqual(["INCONCLUSIVE"] * 3, self.check_loading(
                        *extra, spawn=spawn, answer=answer,
                    ))

    def test_async_launch_metadata_is_not_a_completed_builder_answer(self):
        self.assertEqual(
            ["INCONCLUSIVE"] * 3, self.check_loading(self.async_launch(), answer=False)
        )

    def test_correlated_async_completion_supplies_the_builder_answer(self):
        for text_blocks in (False, True):
            with self.subTest(text_blocks=text_blocks):
                self.assertEqual(["PASS"] * 3, self.check_loading(
                    self.async_launch(), self.completion(text_blocks=text_blocks), answer=False,
                ))

    def test_wrong_failed_or_cross_actor_notifications_cannot_complete_the_builder(self):
        for changed in (
            {"tool_id": "another-spawn"}, {"task_id": "another-agent"},
            {"status": "failed"}, {"actor": "reviewer"},
        ):
            with self.subTest(changed=changed):
                self.assertEqual(["INCONCLUSIVE"] * 3, self.check_loading(
                    self.async_launch(), self.completion(**changed), answer=False,
                ))

    def test_stdout_launch_text_still_requires_correlated_completion(self):
        self.assertEqual(["INCONCLUSIVE"] * 3, self.check_loading(
            self.async_launch(structured=False), answer=False,
        ))
        self.assertEqual(["PASS"] * 3, self.check_loading(
            self.async_launch(structured=False), self.completion(), answer=False,
        ))

    def test_notification_without_a_recorded_async_launch_is_not_an_answer(self):
        self.assertEqual(["INCONCLUSIVE"] * 3, self.check_loading(self.completion(), answer=False))

    def test_a_later_failed_notification_does_not_reuse_an_earlier_success(self):
        self.assertEqual(["INCONCLUSIVE"] * 3, self.check_loading(
            self.async_launch(), self.completion(), self.completion(status="failed"), answer=False,
        ))

    def test_an_errored_launch_cannot_be_completed_by_a_notification(self):
        launch = self.async_launch()
        launch["message"]["content"][0]["is_error"] = True
        self.assertEqual(["INCONCLUSIVE"] * 3, self.check_loading(
            launch, self.completion(), answer=False,
        ))

    def test_malformed_or_non_root_notifications_are_not_answers(self):
        for variant in ("unclosed", "duplicate-id", "other-origin", "sidechain"):
            event = self.completion()
            if variant == "unclosed":
                event["message"]["content"] = event["message"]["content"].replace(
                    "</task-notification>", ""
                )
            elif variant == "duplicate-id":
                event["message"]["content"] = event["message"]["content"].replace(
                    "<result>", "<tool-use-id>builder</tool-use-id><result>",
                )
            elif variant == "other-origin":
                event["origin"] = {"kind": "user"}
            else:
                event["isSidechain"] = True
            with self.subTest(variant=variant):
                self.assertEqual(["INCONCLUSIVE"] * 3, self.check_loading(
                    self.async_launch(), event, answer=False,
                ))

    def test_another_actor_cannot_supply_the_builders_backend_read(self):
        for actor in (None, "reviewer"):
            with self.subTest(actor=actor):
                statuses = self.check_loading(
                    self.actor_event(
                        actor,
                        self.call(
                            "elsewhere",
                            "Read",
                            file_path="/plugin/skills/backend-craft/SKILL.md",
                        ),
                    ),
                    self.actor_event(actor, self.result("elsewhere", self.BACKEND)),
                    fetch=False,
                )
                self.assertEqual("INCONCLUSIVE", statuses[1])

    def test_without_actor_provenance_successful_reads_are_inconclusive(self):
        self.assertEqual(["INCONCLUSIVE"] * 3, self.check_loading(provenance=False))

    def test_an_unattributed_fetch_leaves_absence_checks_inconclusive(self):
        self.assertEqual(["INCONCLUSIVE", "PASS", "INCONCLUSIVE"], self.check_loading(
            {"message": {"content": [self.call("unknown", "Read", file_path="/unknown")]}}
        ))

    def test_an_observed_builder_cannot_borrow_a_different_actors_read(self):
        self.assertEqual("FAIL", self.check_loading(
            self.actor_event("builder", {"type": "text", "text": "Inspection finished."}),
            self.actor_event(
                None,
                self.call(
                    "elsewhere", "Read", file_path="/plugin/skills/backend-craft/SKILL.md"
                ),
            ),
            self.actor_event(None, self.result("elsewhere", self.BACKEND)),
            fetch=False,
        )[1])

    def test_no_builder_spawn_leaves_all_loading_checks_inconclusive(self):
        transcript = json.dumps(self.actor_event(
            "reviewer",
            self.call("backend", "Read", file_path="/plugin/skills/backend-craft/SKILL.md"),
        ))
        probe = probe_plugin.Probe()
        with contextlib.redirect_stdout(io.StringIO()):
            probe_plugin.probe_builder_skills(probe, transcript)
        self.assertEqual(["INCONCLUSIVE"] * 3, [status for status, *_ in probe.results])

    def test_the_read_result_must_have_the_same_actor_as_its_call(self):
        self.assertEqual("INCONCLUSIVE", self.check_loading(
            self.actor_event("reviewer", self.result("backend", self.BACKEND)),
            fetch_result=False,
        )[1])

    def test_two_builder_invocations_cannot_pool_read_and_answer_evidence(self):
        statuses = self.check_loading(
            self.actor_event(
                None,
                self.call("builder2", "Agent", subagent_type="sde-agents:sde-fullstack"),
            ),
            self.actor_event(
                "builder2",
                self.call(
                    "backend2", "Read", file_path="/plugin/skills/backend-craft/SKILL.md"
                ),
            ),
            self.actor_event("builder2", self.result("backend2", self.BACKEND)),
            self.actor_event(None, self.result("builder2", "done")),
            fetch=False,
        )
        self.assertNotIn("PASS", statuses)

    def test_another_actors_unrelated_reads_do_not_contaminate_the_builder(self):
        self.assertEqual(["PASS"] * 3, self.check_loading(
            self.actor_event(
                "reviewer",
                self.call(
                    "elsewhere", "Read", file_path="/plugin/skills/code-craft/SKILL.md"
                ),
            ),
            self.actor_event("reviewer", self.result("elsewhere", self.CODE + self.FRONTEND)),
        ))

    def test_missing_or_errored_builder_result_is_inconclusive(self):
        for extra in ((), (self.result("builder", "timed out", is_error=True),)):
            with self.subTest(extra=extra):
                self.assertEqual(["INCONCLUSIVE"] * 3, self.check_loading(*extra, answer=False))

    def test_a_different_agents_answer_cannot_prove_builder_loading(self):
        self.assertEqual(["INCONCLUSIVE"] * 3, self.check_loading(
            self.call("reviewer", "Agent", subagent_type="sde-agents:code-reviewer"),
            self.result("reviewer", f"{self.CODE} {self.BACKEND} NO_FRONTEND_CONTENT"),
            answer=False,
        ))

    def test_answering_without_the_backend_read_does_not_prove_on_demand_loading(self):
        self.assertEqual("FAIL", self.check_loading(
            self.actor_event("builder", {"type": "text", "text": "Inspection finished."}),
            fetch=False,
        )[1])

    def test_missing_backend_result_is_inconclusive_even_if_the_answer_quotes_it(self):
        self.assertEqual("INCONCLUSIVE", self.check_loading(fetch_result=False)[1])

    def test_wrong_or_failed_backend_read_cannot_prove_a_successful_fetch(self):
        for fields in ({}, {"is_error": True}):
            with self.subTest(fields=fields):
                self.assertEqual("FAIL", self.check_loading(
                    self.result("backend", "file unavailable", **fields), fetch_result=False,
                )[1])

    def test_backend_canary_from_an_unrelated_result_is_not_fetch_evidence(self):
        self.assertEqual("INCONCLUSIVE", self.check_loading(
            self.result("unrelated", self.BACKEND), fetch_result=False,
        )[1])

    def test_an_observed_answer_missing_the_requested_content_fails(self):
        self.assertEqual(["FAIL"] * 3, self.check_loading(answer="done"))

    def test_fetching_code_craft_disproves_preload(self):
        for call in (
            self.call("code", "Read", file_path="/plugin/skills/code-craft/SKILL.md"),
            self.call("code", "Skill", skill="sde-agents:code-craft"),
            self.call("code", "Bash", command="cat skills/*/SKILL.md"),
        ):
            with self.subTest(call=call):
                self.assertEqual(
                    "FAIL", self.check_loading(call, self.result("code", self.CODE))[0]
                )

    def test_unwanted_frontend_loading_or_preload_fails(self):
        self.assertEqual(
            "FAIL",
            self.check_loading(answer=f"{self.CODE} {self.BACKEND} {self.FRONTEND}")[2],
        )
        for call in (
            self.call("front", "Read", file_path="/plugin/skills/frontend-craft/SKILL.md"),
            self.call("front", "Skill", skill="sde-agents:frontend-craft"),
            self.call("front", "Bash", command="cat skills/*/SKILL.md"),
        ):
            with self.subTest(call=call):
                self.assertEqual(
                    "FAIL", self.check_loading(call, self.result("front", self.FRONTEND))[2]
                )

    def test_partial_shell_and_search_reads_cannot_prove_unloaded_skills(self):
        """A short read can omit the canary while still fetching forbidden guidance."""
        for skill, index in (("frontend-craft", 2), ("code-craft", 0)):
            for name, inp in (
                ("Bash", {"command": f"head -n 1 /plugin/skills/{skill}/SKILL.md"}),
                ("Grep", {"pattern": "^---", "glob": f"**/{skill}/SKILL.md"}),
                ("Glob", {"pattern": f"**/{skill}/SKILL.md"}),
            ):
                with self.subTest(skill=skill, name=name):
                    self.assertEqual("FAIL", self.check_loading(
                        self.call("partial", name, **inp), self.result("partial", "---"),
                    )[index])

    def test_broad_skill_fetches_with_marker_free_results_contaminate_both_checks(self):
        """Wildcard partial reads cannot establish either preload provenance or absence."""
        for name, inp in (
            ("Bash", {"command": "sed -n '1p' /plugin/skills/*/SKILL.md"}),
            ("Bash", {"command": "head -n 1 /plugin/**/SKILL.md"}),
            ("Grep", {"pattern": "^---", "path": "/plugin/skills"}),
            ("Glob", {"pattern": "**/skills/*/SKILL.md"}),
        ):
            with self.subTest(name=name, inp=inp):
                verdicts = self.check_loading(
                    self.call("broad", name, **inp), self.result("broad", "---"),
                )
                self.assertEqual(["FAIL", "PASS", "FAIL"], verdicts)

    def test_an_unanswered_fetch_cannot_prove_no_canary_leaked(self):
        self.assertEqual(["INCONCLUSIVE", "PASS", "INCONCLUSIVE"], self.check_loading(
            self.call("opaque", "Bash", command="cat unseen-file"),
        ))


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

    def test_an_answered_gate_arm_is_graded_even_when_its_peer_times_out(self) -> None:
        """Drives `_probe_live_effect_gate` itself, because the defect was CONTROL FLOW.

        The first version of this test rebuilt the loop in its own body and inserted the expected
        FAIL by hand. It executed none of the production branch it claimed to cover, so
        reinstating the early return left it green -- a test that reads as enforcement while
        enforcing nothing, which is the class this PR keeps finding (Codex, #190).

        The AGENT arm answers with a transcript showing the live verb RAN unguarded; the MAIN arm
        times out. The observed regression must survive its peer's timeout.
        """
        marker = probe_plugin.GATE_CMD.format(marker="AGENT")
        ran_unguarded = "\n".join(
            json.dumps(event)
            for event in (
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "call_gate",
                                "name": "Bash",
                                "input": {"command": marker},
                            }
                        ]
                    },
                },
                {
                    "type": "user",
                    "message": {
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "call_gate",
                                "content": "GATEPROBE_AGENT\nno such file",
                            }
                        ]
                    },
                },
            )
        )

        def spawn(cmd, **_kwargs):
            argv = tuple(cmd)
            if "--agent" in argv:
                return probe_plugin._proc.CommandResult(argv, 0, ran_unguarded, "")
            return probe_plugin._proc.CommandResult(
                argv, None, "", "", timed_out=True, error="timed out"
            )

        probe = probe_plugin.Probe()
        with (
            mock.patch.object(probe_plugin, "run", side_effect=spawn),
            mock.patch.object(probe_plugin, "CLAUDE", "claude"),
            mock.patch.object(probe_plugin, "existing_path", return_value=None),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            probe_plugin._probe_live_effect_gate(probe, Path("probe-target"))

        verdicts = {label: status for status, label, _ in probe.results}
        self.assertEqual(
            probe_plugin.SKIP,
            verdicts.get("the live-effect gate differential (MAIN arm)"),
            "the timed-out MAIN arm was not reported",
        )
        agent_verdict = verdicts.get(
            "the gate DENIED homelab-engineer's live verb under dontAsk"
        )
        self.assertIsNotNone(
            agent_verdict,
            "the answered AGENT arm was never graded -- the early return is back",
        )
        self.assertEqual(
            probe_plugin.FAIL,
            agent_verdict,
            "the AGENT arm observed the live verb running unguarded, and that verdict was "
            "discarded or downgraded because its peer timed out",
        )

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

    def test_a_timed_out_main_session_still_reaches_the_workflow_leg(self) -> None:
        """The heart of PROBE-006: later legs run their own sessions and must still be reached."""
        reached: list[str] = []

        def spawn(cmd, **_kwargs):
            """Setup succeeds; only the model sessions time out.

            The distinction is the test's whole point. A `git init` that fails means there is no
            repository to probe, and returning early is right; a SESSION that times out must not
            take the legs that drive their own sessions with it.
            """
            argv = tuple(cmd)
            if argv and argv[0] == "git":
                return probe_plugin._proc.CommandResult(argv, 0, "", "")
            return probe_plugin._proc.CommandResult(
                argv, None, "", "", timed_out=True, error="timed out"
            )

        with (
            mock.patch.object(probe_plugin, "run", side_effect=spawn),
            mock.patch.object(probe_plugin, "CLAUDE", "claude"),
            mock.patch.object(probe_plugin, "_remove_workspace"),
            mock.patch.object(
                probe_plugin,
                "probe_workflow_contract",
                side_effect=lambda probe: reached.append("workflow"),
            ),
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(probe_plugin, "REPO", Path(tmp)),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = probe_plugin.main([])

        self.assertEqual(["workflow"], reached, "the run stopped at the timed-out session")
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
        self.assertEqual(
            [],
            probe_plugin.agent_spawn_results(transcript, "sde-agents:sde-fullstack"),
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
        self.assertEqual(
            ["valid spawn"],
            probe_plugin.agent_spawn_results(
                malformed_ids, "sde-agents:sde-fullstack"
            ),
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
        self.assertEqual(
            ["agent ok"],
            probe_plugin.agent_spawn_results(transcript, "sde-agents:sde-fullstack"),
        )


class GateProbeTargetInertness(unittest.TestCase):
    """The gate probe's MAIN arm deliberately RUNS `docker compose ... up -d` under dontAsk.

    Risk hypothesis: that is harmless ONLY while the referenced compose file cannot be loaded.
    The path is fixed and predictable, and the probe's comment asserted it "cannot exist" while
    nothing enforced it — so a file sitting at that path would turn the deny/run differential
    into a real container start against the operator's Docker daemon, with the probe still
    printing a green MAIN leg. An unenforceable safety comment is the failure this watches.
    """

    def test_an_existing_target_is_reported_so_the_probe_can_refuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            present = str(Path(tmp) / "docker-compose.yml")
            Path(present).write_text("services: {}\n", encoding="utf-8")
            absent = str(Path(tmp) / "no-such" / "docker-compose.yml")
            self.assertIsNone(probe_plugin.existing_path([absent]))
            self.assertEqual(present, probe_plugin.existing_path([absent, present]))

    def test_the_checked_paths_are_the_paths_the_command_runs(self) -> None:
        # A guard that inspects a different path than the command uses enforces nothing.
        targets = probe_plugin.gate_targets()
        self.assertEqual(2, len(targets))
        for marker, target in zip(("AGENT", "MAIN"), targets, strict=True):
            with self.subTest(marker=marker):
                self.assertIn(target, probe_plugin.GATE_CMD.format(marker=marker))
                self.assertIn(marker, target)

    def test_live_gate_probe_explicitly_selects_prompt_policy(self) -> None:
        # A probe of interposition must not inherit the host-default no-decision policy.
        with (
            mock.patch.object(probe_plugin, "existing_path", return_value=None),
            mock.patch.object(probe_plugin, "run") as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            run.return_value.stdout = ""
            probe_plugin._probe_live_effect_gate(probe_plugin.Probe(), Path("probe-target"))
        self.assertEqual(2, run.call_count)
        for call in run.call_args_list:
            self.assertEqual("prompt", call.kwargs["env"]["SDE_AGENTS_LIVE_EFFECT_POLICY"])


if __name__ == "__main__":
    unittest.main()
