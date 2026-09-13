"""Kernel stream-json decoding: skip what cannot be read, correlate by id, keep every result."""

from __future__ import annotations

import json
import unittest

from fleet import stream


def _event(*blocks: dict) -> str:
    return json.dumps({"type": "assistant", "message": {"content": list(blocks)}})


def _use(tool_id: str, name: str, **tool_input: object) -> dict:
    return {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}


def _result(tool_id: str, content: object, *, is_error: bool = False) -> dict:
    block = {"type": "tool_result", "tool_use_id": tool_id, "content": content}
    if is_error:
        block["is_error"] = True
    return block


class ReaderTests(unittest.TestCase):
    def test_malformed_scalar_and_oddly_shaped_lines_are_skipped_not_fatal(self) -> None:
        text = "\n".join(
            [
                "not json",
                json.dumps(42),
                json.dumps({"type": "system", "message": "a plain string, not a mapping"}),
                json.dumps({"type": "assistant", "message": {"content": "text not list"}}),
                _event({"type": "text", "text": "hello"}, "not a block"),
            ]
        )
        self.assertEqual(len(list(stream.iter_events(text))), 3)
        self.assertEqual(
            list(stream.iter_content_blocks(text)), [{"type": "text", "text": "hello"}]
        )
        self.assertIsNone(stream.event_message_field({"message": "string"}, "content"))
        self.assertIsNone(stream.event_message_field("not an event", "content"))

    def test_block_text_flattens_only_string_parts(self) -> None:
        parts = [{"type": "text", "text": "a"}, "junk", {"text": 7}, {"type": "text", "text": "b"}]
        self.assertEqual(stream.block_text(parts), "a b")
        self.assertEqual(stream.block_text(parts, separator="\n"), "a\nb")
        self.assertEqual(stream.block_text("plain"), "plain")
        self.assertEqual(stream.block_text(None), "")


class CorrelationTests(unittest.TestCase):
    def test_every_call_keeps_its_own_result_in_stream_order(self) -> None:
        text = "\n".join(
            [
                _event(_use("t1", "Bash", command="find . -exec rm {} ;")),
                _event(_result("t1", "denied: read-only agent")),
                _event(_use("t2", "Bash", command="find . -exec rm {} ;")),
                _event(
                    _result(
                        "t2", [{"type": "text", "text": "ran"}, {"type": "text", "text": "fine"}]
                    )
                ),
                _event(_use("t3", "Bash", command="cat README.md")),
            ]
        )
        exchanges = stream.correlate_tool_results(text, tool_names={"Bash"})
        self.assertEqual([e.id for e in exchanges], ["t1", "t2", "t3"])
        # Two identical commands stay two exchanges: merging them served one oracle and broke the
        # other, because a denial is a pass for the guarded check and a failure for the main loop.
        self.assertEqual(exchanges[0].result, "denied: read-only agent")
        self.assertEqual(exchanges[1].result, "ran fine")
        self.assertIsNone(exchanges[2].result)
        self.assertFalse(exchanges[2].answered)

    def test_uncorrelatable_calls_are_dropped_and_errors_are_flagged(self) -> None:
        text = "\n".join(
            [
                _event({"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}),  # no id
                _event({"type": "tool_use", "id": "", "name": "Bash", "input": {"command": "ls"}}),
                _event({"type": "tool_use", "id": "x", "name": "Bash", "input": "not a dict"}),
                _event(_use("a1", "Agent", subagent_type="sde-agents:code-reviewer")),
                _event(_result("a1", "spawn failed", is_error=True)),
                _event(_result("", "orphan")),
            ]
        )
        exchanges = stream.correlate_tool_results(text)
        self.assertEqual(len(exchanges), 1)
        self.assertTrue(exchanges[0].is_error)
        self.assertEqual(exchanges[0].name, "Agent")
        self.assertEqual(exchanges[0].input, {"subagent_type": "sde-agents:code-reviewer"})

    def test_a_later_result_for_the_same_id_replaces_the_earlier_one(self) -> None:
        text = "\n".join(
            [
                _event(_use("t1", "Bash", command="ls")),
                _event(_result("t1", "first")),
                _event(_result("t1", "second")),
            ]
        )
        self.assertEqual(stream.correlate_tool_results(text)[0].result, "second")

    def test_tool_name_filter_keeps_results_for_other_tools_out(self) -> None:
        text = "\n".join(
            [_event(_use("t1", "Read", file_path="x")), _event(_use("t2", "Bash", command="ls"))]
        )
        self.assertEqual(
            [e.name for e in stream.correlate_tool_results(text, tool_names={"Bash"})], ["Bash"]
        )


class SkillLaunchSignalTests(unittest.TestCase):
    def test_launch_control_signals_are_not_failures(self) -> None:
        self.assertTrue(stream.is_skill_launch_signal("Execute skill: lab-audit"))
        self.assertTrue(stream.is_skill_launch_signal("launching SKILL: runbook"))
        self.assertFalse(stream.is_skill_launch_signal("Error: unknown skill"))


if __name__ == "__main__":
    unittest.main()
