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


def block_text(content: object, *, separator: str = " ") -> str:
    """Flatten a block's `content` -- a string, or a list of `{"type": "text", ...}` parts.

    Parts that are not dicts, or whose `text` is not a string, are dropped rather than raising:
    the four former copies of this loop agreed on that but disagreed on the separator, which is
    why it is a named parameter here.
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
    return separator.join(texts)


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
    separator: str = " ",
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
                block_text(block.get("content"), separator=separator),
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


# A skill that restricts tools (`allowed-tools` / `disallowed-tools`) is LAUNCHED via a
# `tool_result` the CLI marks `is_error: true` with content "Execute skill: <name>"; a skill
# without restrictions reports "Launching skill: <name>" with `is_error` unset. Both mean the
# skill was invoked. Treating the first as an error silently dropped every tool-restricting
# skill's invocation: `lab-audit` scored 0/N despite routing correctly on every run, and an
# over-trigger of it on a NEGATIVE case was invisible -- a false PASS.
SKILL_LAUNCH_SIGNALS: tuple[str, ...] = ("execute skill:", "launching skill:")


def is_skill_launch_signal(result_text: str) -> bool:
    """Whether an `is_error` tool_result is the Skill tool's launch signal, not a failure.

    Matched at the START of the result, not anywhere inside it. A substring test -- what the
    retiring runner used, and what this inherited -- also matched a genuine failure that happened
    to mention the phrase, such as `Permission denied: could not execute skill: x`, turning a
    failed dispatch into a counted one and letting a positive pass without routing anywhere.

    Deliberately NOT tightened further to require the skill's own name: the exemption exists
    because a tool-restricting skill LAUNCHES through an `is_error` result, and pinning this to
    the CLI's exact message wording would resurrect the original defect -- `lab-audit` scoring
    0/N on correct routing -- the next time that wording changes. Opening-phrase plus the
    caller's tool check is the tightening that does not trade one silent failure for another.
    """
    lowered = result_text.lstrip().lower()
    return any(lowered.startswith(signal) for signal in SKILL_LAUNCH_SIGNALS)


def final_result(text: str) -> dict[str, object] | None:
    """The session's last `result` event, or None if it never reached one.

    Read as the LAST one rather than the first: a transcript can carry more than one, and it is
    the final structured result that says how the session ended.
    """
    found: dict[str, object] | None = None
    for event in iter_events(text):
        if event.get("type") == "result":
            found = event
    return found


def session_completed(text: str) -> bool:
    """Whether the session reached a final result that was not an error.

    This is what separates a silence that is an OBSERVATION from one that is only an unfinished
    run, and getting it wrong is expensive in both directions. A session that completed and routed
    nowhere is real evidence -- a genuine miss on a positive, a genuine pass on a negative. A
    session cut off before it finished has decided nothing, and scoring its silence as "did not
    route" greens negatives vacuously and drops misses out of a positive's denominator.

    Deliberately NOT the same as "the process exited zero": a run cut at its turn or time limit is
    reported as an error by the harness while its transcript may already contain the routing
    decision, and a clean exit with no result event is still silence.
    """
    result = final_result(text)
    return result is not None and not result.get("is_error")


def observed_model(text: str) -> str | None:
    """The model the session ACTUALLY ran on, read off the transcript.

    Independent of any requested model on purpose: routing behaviour varies by tier, so an
    artifact that records the request rather than the observation cannot be validly diffed against
    another -- and the runs a conditions block exists to describe are exactly the pinned ones,
    where the two would agree and hide the bug.
    """
    for event in iter_events(text):
        candidate = event.get("model") or event_message_field(event, "model")
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def registered_components(text: str) -> dict[str, list[str]]:
    """The agents and skills the session's own `init` event says it could route to.

    A measurement condition that must be OBSERVED rather than asserted. A flag claiming isolation
    records what the runner intended; this records what the session actually saw, and the two came
    apart: `--clean-room` relocates `CLAUDE_CONFIG_DIR`, but the native eval harness sets its own,
    so the flag changed nothing while still being stored as a condition. Two artifacts taken
    against different competition are not comparable no matter what either one's flags claimed.
    """
    found: dict[str, list[str]] = {"agents": [], "skills": []}
    for event in iter_events(text):
        if event.get("type") != "system" or event.get("subtype") != "init":
            continue
        for key in ("agents", "skills"):
            value = event.get(key)
            if isinstance(value, list):
                found[key] = sorted(str(v) for v in value if isinstance(v, str))
        break  # the first init describes the session; a later one would be a resume
    return found
