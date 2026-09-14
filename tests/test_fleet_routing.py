"""The routing verdict, and the two readings of `is_error` that a false PASS taught the fleet.

Phase 4 hands the RUNNING of routing cases to `claude plugin eval` but not the VERDICT, because
the native `tool_used` grader counts a call whose input matches whether or not the spawn succeeded
(measured 2026-09-14, `docs/archive/2026-09/native-grader-errored-spawn-2026-09-14.md`). These
tests pin the reading this module keeps instead.
"""

from __future__ import annotations

import json
import unittest

from fleet import routing

ROSTER = frozenset({"root-cause", "lab-audit", "code-reviewer", "researcher"})


def transcript(*blocks: dict) -> str:
    """A stream-json transcript carrying the given content blocks, one event per block group."""
    lines = []
    for block in blocks:
        role = "user" if block.get("type") == "tool_result" else "assistant"
        lines.append(json.dumps({"type": role, "message": {"content": [block]}}))
    return "\n".join(lines)


def call(tool: str, call_id: str, **inputs: object) -> dict:
    return {"type": "tool_use", "id": call_id, "name": tool, "input": inputs}


def result(call_id: str, content: str, *, is_error: bool = False) -> dict:
    return {"type": "tool_result", "tool_use_id": call_id, "content": content, "is_error": is_error}


class FiredComponentTests(unittest.TestCase):
    def test_a_successful_dispatch_fires(self) -> None:
        text = transcript(
            call("Agent", "a1", subagent_type="sde-agents:root-cause"),
            result("a1", "done"),
        )
        self.assertEqual({"root-cause"}, routing.fired_components(text, ROSTER))

    def test_a_genuinely_errored_dispatch_does_not_fire(self) -> None:
        """The whole reason this module exists rather than trusting `tool_used`."""
        text = transcript(
            call("Agent", "a1", subagent_type="sde-agents:root-cause"),
            result("a1", "Agent type 'sde-agents:root-cause' not found.", is_error=True),
        )
        self.assertEqual(set(), routing.fired_components(text, ROSTER))

    def test_a_skill_launch_signal_is_not_a_failure(self) -> None:
        """The `lab-audit` trap: a tool-restricting skill LAUNCHES through an is_error result.

        Reading that as a failure once scored lab-audit 0/N despite correct routing on every run,
        and hid an over-trigger of it on a negative case -- a false PASS. Both spellings the CLI
        uses are covered, because only one of them is the restricted form.
        """
        for content in ("Execute skill: lab-audit", "Launching skill: lab-audit"):
            with self.subTest(content=content):
                text = transcript(
                    call("Skill", "s1", command="sde-agents:lab-audit"),
                    result("s1", content, is_error=True),
                )
                self.assertEqual({"lab-audit"}, routing.fired_components(text, ROSTER))

    def test_a_name_is_matched_as_a_whole_value_not_inside_prose(self) -> None:
        """The runner matched `strip_ns(value)` against the roster -- the WHOLE string value.

        A fleet name mentioned inside a sentence therefore never counted as a dispatch, and
        this kernel keeps that: the tool input's own fields carry the routing decision, while
        prose in a `prompt` is the model talking about a component, not calling one. Widening
        this to a substring scan would make every case that merely names a sibling in its
        instructions score as firing it.
        """
        for inputs, expected in (
            ({"subagent_type": "sde-agents:researcher"}, {"researcher"}),
            ({"command": "researcher"}, {"researcher"}),
            ({"nested": ["sde-agents:researcher"]}, {"researcher"}),
            ({"prompt": "delegate to sde-agents:researcher now"}, set()),
        ):
            with self.subTest(inputs=inputs):
                text = transcript(call("Agent", "a1", **inputs), result("a1", "ok"))
                self.assertEqual(expected, routing.fired_components(text, ROSTER))

    def test_a_component_outside_the_roster_is_ignored(self) -> None:
        text = transcript(call("Agent", "a1", subagent_type="general-purpose"), result("a1", "ok"))
        self.assertEqual(set(), routing.fired_components(text, ROSTER))

    def test_an_uncorrelated_call_still_fires(self) -> None:
        """No result block at all is not an error result; the dispatch was still made.

        `ToolExchange.is_error` defaults False for an unanswered call, so this states the
        behaviour rather than leaving it to the default's discretion.
        """
        text = transcript(call("Skill", "s1", command="root-cause"))
        self.assertEqual({"root-cause"}, routing.fired_components(text, ROSTER))


class GradingTests(unittest.TestCase):
    MEMBERS = ["root-cause", "lab-audit", "code-reviewer"]

    def _runs(self, *fired: str | None) -> list[frozenset[str] | None]:
        """Per-run firing sets, built by running real transcripts through `fired_components`.

        Grading takes firing sets, but a test that hand-writes them would only check the
        arithmetic. Piping a transcript through the reader keeps these end-to-end, so a change
        that breaks the reading is caught here too. `None` is a run with no usable transcript;
        `""` is a run that routed somewhere outside the cluster.
        """
        roster = frozenset(self.MEMBERS)
        out: list[frozenset[str] | None] = []
        for name in fired:
            if name is None:
                out.append(None)
                continue
            if name == "":
                text = transcript(call("Agent", "x", subagent_type="general-purpose"))
            else:
                text = transcript(call("Agent", "x", subagent_type=name), result("x", "done"))
            out.append(frozenset(routing.fired_components(text, roster)))
        return out

    def test_a_positive_passes_when_an_expected_member_fires_often_enough(self) -> None:
        case = {"id": "pos", "polarity": "positive", "expect_fires": ["root-cause"]}
        verdict = routing.grade_case(case, self.MEMBERS, self._runs("root-cause", "root-cause", ""))
        self.assertEqual(2 / 3, verdict.rate)
        self.assertTrue(verdict.passed(0.5))
        self.assertFalse(verdict.passed(0.9))

    def test_a_negative_passes_only_when_nothing_forbidden_fires(self) -> None:
        case = {"id": "neg", "polarity": "negative", "expect_not_fires": ["code-reviewer"]}
        clean = routing.grade_case(case, self.MEMBERS, self._runs("", "root-cause"))
        self.assertTrue(clean.passed(0.5), "an unrelated member firing is not an over-trigger")
        dirty = routing.grade_case(case, self.MEMBERS, self._runs("", "code-reviewer"))
        self.assertFalse(dirty.passed(0.5), "one over-trigger fails the negative")

    def test_a_negative_without_narrowing_forbids_the_whole_cluster(self) -> None:
        case = {"id": "broad", "polarity": "negative"}
        verdict = routing.grade_case(case, self.MEMBERS, self._runs("lab-audit"))
        self.assertEqual(frozenset(self.MEMBERS), verdict.targets)
        self.assertFalse(verdict.passed(0.5))

    def test_an_invalid_run_is_excluded_rather_than_scored_as_a_miss(self) -> None:
        """A measurement failure and a routing failure are different facts."""
        case = {"id": "pos", "polarity": "positive", "expect_fires": ["root-cause"]}
        verdict = routing.grade_case(case, self.MEMBERS, self._runs("root-cause", None, None))
        self.assertEqual(1, verdict.valid_runs)
        self.assertEqual(2, verdict.invalid_runs)
        self.assertEqual(1.0, verdict.rate, "the invalid runs must not dilute the rate")

    def test_a_case_with_no_valid_run_is_inconclusive_and_never_passed(self) -> None:
        for case in (
            {"id": "pos", "polarity": "positive", "expect_fires": ["root-cause"]},
            {"id": "neg", "polarity": "negative", "expect_not_fires": ["code-reviewer"]},
        ):
            with self.subTest(polarity=case["polarity"]):
                verdict = routing.grade_case(case, self.MEMBERS, self._runs(None, None))
                self.assertTrue(verdict.inconclusive)
                self.assertIsNone(verdict.rate)
                self.assertFalse(
                    verdict.passed(0.5),
                    "an unmeasured case was reported as a result",
                )

    def test_a_malformed_case_is_refused_rather_than_graded(self) -> None:
        for case, expected in (
            ({"id": "x", "polarity": "maybe"}, "polarity must be exactly"),
            ({"id": "x", "polarity": "positive", "expect_fires": []}, "non-empty list"),
            (
                {"id": "x", "polarity": "positive", "expect_fires": ["not-a-member"]},
                "invalid cluster member",
            ),
        ):
            with self.subTest(case=case):
                with self.assertRaisesRegex(ValueError, expected):
                    routing.grade_case(case, self.MEMBERS, [])


if __name__ == "__main__":
    unittest.main()
