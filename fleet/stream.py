"""Decoding for the line-delimited JSON a headless `claude -p --output-format stream-json` emits.

Two readers and one oracle live here, and the oracle is the reason the module exists.

**Skip, never crash.** Both readers run on every line of every session. `(event.get("message")
or {}).get(...)` crashes on an event whose `message` is a plain string; one such event raised
`AttributeError` out of a scorer and took down a whole paid batch with no benchmark written
(live session, 2026-08-10). A transcript line the reader cannot interpret is skipped: the
sessions are already paid for by the time it is parsed.

**Correlate by `tool_use_id`, never grep the transcript.** A transcript-wide search for a deny
message cannot say WHO was denied, and "who" is exactly what a guard probe tests; a search for an
agent's name matches the probe's own prompt echoed into the verbose stream, so it cannot fail.
The only evidence that a call ran, was denied, or resolved is the `tool_result` block carrying
that call's id -- and its ABSENCE is a correlation gap, never evidence (PROBE-004).
"""

from __future__ import annotations

import json
from collections.abc import Collection, Iterator
from dataclasses import dataclass


def iter_events(text: str) -> Iterator[dict[str, object]]:
    """Yield JSON object events, skipping diagnostics, malformed lines, and scalar values."""
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def event_message_field(event: object, field: str) -> object:
    """Read `event["message"][field]`, tolerating an event that is not shaped that way."""
    if not isinstance(event, dict):
        return None
    message = event.get("message")
    return message.get(field) if isinstance(message, dict) else None


def iter_content_blocks(text: str) -> Iterator[dict[str, object]]:
    """Yield object blocks from mapping messages in transcript order."""
    for event in iter_events(text):
        content = event_message_field(event, "content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict):
                yield block


def block_text(content: object) -> str:
    """Flatten a block's `content` -- a string, or a list of `{"type": "text", ...}` parts.

    Parts that are not dicts, or whose `text` is not a string, are dropped rather than raising.
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    texts = [
        part.get("text")
        for part in content
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ]
    return " ".join(texts)


@dataclass(frozen=True)
class ToolExchange:
    """One `tool_use` block and the `tool_result` that answered it, if any.

    `result` is None when no result block ever named this call's id: a correlation gap, which a
    verdict must report as INCONCLUSIVE rather than as either outcome. An observed `""` is a real
    answer -- a command that ran and printed nothing still ran.
    """

    id: str
    name: str
    input: dict[str, object]
    result: str | None = None
    is_error: bool = False

    @property
    def answered(self) -> bool:
        return self.result is not None


def correlate_tool_results(
    text: str,
    *,
    tool_names: Collection[str] | None = None,
) -> list[ToolExchange]:
    """Every `tool_use` (optionally filtered by tool name) with its own result, in stream order.

    Every call is kept and no precedence is applied across repeated identical calls: merging a
    retry's two results into one was tried twice and failed twice in opposite directions --
    first-wins hid a run behind a denial, then unguarded-wins hid a denial behind a run -- because
    a denial is the failure for one oracle and the pass for another (PR #151). The decision belongs
    to each check, which knows its own polarity; this returns the evidence.

    A `tool_use` whose id or input is missing or malformed is dropped: it cannot be correlated,
    so it cannot be evidence. A later `tool_result` for the same id replaces an earlier one.
    """
    uses: list[ToolExchange] = []
    results: dict[str, tuple[str, bool]] = {}
    for block in iter_content_blocks(text):
        kind = block.get("type")
        if kind == "tool_use":
            tool_id = block.get("id")
            name = block.get("name")
            tool_input = block.get("input")
            if not isinstance(tool_id, str) or not tool_id or not isinstance(name, str):
                continue
            if not isinstance(tool_input, dict):
                continue
            if tool_names is not None and name not in tool_names:
                continue
            uses.append(ToolExchange(tool_id, name, tool_input))
        elif kind == "tool_result":
            tool_id = block.get("tool_use_id")
            if not isinstance(tool_id, str) or not tool_id:
                continue
            results[tool_id] = (
                block_text(block.get("content")),
                bool(block.get("is_error")),
            )
    correlated = []
    for use in uses:
        answer = results.get(use.id)
        if answer is None:
            correlated.append(use)
        else:
            correlated.append(ToolExchange(use.id, use.name, use.input, answer[0], answer[1]))
    return correlated
