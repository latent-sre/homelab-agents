"""Grade routing evidence the way the retiring runner did, over any transcript source.

Phase 4 hands the RUNNING of routing cases to `claude plugin eval` -- isolation, runs,
concurrency, cost caps, JSON results and exit codes all become the platform's. It does not hand
over the VERDICT, and that distinction was measured rather than assumed
(`docs/archive/2026-09/native-grader-errored-spawn-2026-09-14.md`): the native `tool_used` grader
counts a call whose input matches its regex **whether or not the spawn succeeded**, while
`scripts/eval_routing.py` deliberately excludes a dispatch that came back `is_error`.

On a positive case that difference is a weaker oracle -- a routing regression can hide behind a
dispatch that never landed -- so this module keeps the runner's reading and applies it to the
native harness's own traces. The native graders stay in each case as a cheap tripwire; the score
this module computes is the one the paired-run oracle compares.

The `is_error` subtlety is the reason this cannot be a one-line filter, and it was learned from a
false PASS rather than from the docs: a skill that restricts tools is LAUNCHED through a
`tool_result` the CLI marks `is_error: true` with content `Execute skill: <name>`. Treating that
as a failure scored `lab-audit` 0/N despite correct routing on every run, and hid an over-trigger
of it on a negative case. `fleet.stream.is_skill_launch_signal` owns that fact; nothing here
re-derives it.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from fleet import stream

# The tools a routing decision can travel through. `Task` is the older spelling of `Agent` and is
# still accepted, because a stored transcript may predate the rename.
ROUTING_TOOLS = ("Skill", "Agent", "Task")

# The default plugin namespace. Callers grading a plugin other than this repository's own pass
# the namespace explicitly: a roster read from one checkout and a namespace read from another is
# how a confident verdict gets produced about the wrong plugin.
PLUGIN_NAMESPACE = "sde-agents"


# The input key each routing tool carries its DESTINATION in, as observed in real traces
# (`docs/archive/2026-09/native-grader-errored-spawn-2026-09-14.md` records a live
# `subagent_type`; the skill form is `command`). Read the destination alone when the call has
# one: scanning every value also matched a sibling field whose whole value happens to be a
# component name -- `{"subagent_type": "general-purpose", "prompt": "root-cause"}` scored
# `root-cause` as dispatched, which can pass a positive or fail a negative on a call that never
# went there.
DESTINATION_FIELDS = {
    "Skill": ("command",),
    "Agent": ("subagent_type",),
    "Task": ("subagent_type",),
}


def destination_value(name: str, call_input: object) -> object | None:
    """The destination field of a routing call, or None when the call carries none of them.

    None is NOT "nothing fired": it means this payload does not match the shapes we have
    observed, and the caller falls back to scanning the whole input. Narrowing without that
    fallback would turn an unannounced schema change into every case silently scoring zero --
    a false green across the whole suite, which is worse than the false dispatch it fixes.
    """
    if not isinstance(call_input, dict):
        return None
    for field in DESTINATION_FIELDS.get(name, ()):
        if field in call_input:
            return call_input[field]
    return None


def _named_components(
    value: object, roster: frozenset[str], namespace: str = PLUGIN_NAMESPACE
) -> set[str]:
    """Every roster component named by a tool call's input, namespace stripped.

    Scans all values it is given, because the name arrives under different keys --
    `subagent_type` for an agent, `command` for a skill -- and a routing decision is the same
    fact whichever field carried it. `fired_components` narrows WHAT it is given to the
    destination field first, which is where that generality became a false dispatch.

    A value matches only as a WHOLE string (optionally namespaced), never as a substring: the
    retiring runner compared `strip_ns(value)` against the roster, and a name mentioned inside a
    sentence therefore never counted. Widening this to a substring scan would score every case
    whose prompt merely names a sibling as having fired it.
    """
    if isinstance(value, str):
        explicit, _, bare = value.partition(":")
        if not _:
            return {value} & roster  # a bare name is this plugin's, by the roster it is matched to
        # An EXPLICIT namespace must be this plugin's. Accepting any of them let a dispatch to
        # `other-plugin:root-cause` count as the fleet's `root-cause`, so a positive could pass
        # without its expected destination ever being called.
        return ({bare} & roster) if explicit == namespace else set()
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, (list, tuple)):
        found: set[str] = set()
        for item in value:
            found |= _named_components(item, roster, namespace)
        return found
    return set()


def fired_components(
    transcript: str, roster: frozenset[str], namespace: str = PLUGIN_NAMESPACE
) -> set[str]:
    """Roster components a transcript shows actually dispatched.

    A call whose `tool_result` came back `is_error` did NOT fire -- except for the skill-launch
    control signal, which is how a tool-restricting skill reports a successful launch.
    """
    fired: set[str] = set()
    for exchange in stream.correlate_tool_results(transcript, tool_names=ROUTING_TOOLS):
        # The destination field alone when this call has one; the whole input only when it does
        # not, so an unobserved payload shape degrades to the old reading rather than to silence.
        destination = destination_value(exchange.name, exchange.input)
        scanned = exchange.input if destination is None else destination
        named = _named_components(scanned, roster, namespace)
        if not named:
            continue
        launched = exchange.name == "Skill" and stream.is_skill_launch_signal(exchange.result or "")
        if exchange.is_error and not launched:
            continue  # a genuine dispatch failure is not a routing decision
        fired |= named
    return fired


def validated_threshold(value: object) -> float:
    """A positive's pass bar, refused unless it is a real number in (0, 1].

    `True` is deliberately rejected even though `0 < True <= 1` holds: a bool arriving here is a
    caller mistake, and accepting it would silently set the bar to "every run".
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"threshold must be a number in (0, 1] (got {value!r})")
    if not 0 < value <= 1:  # also rejects nan, which fails every comparison
        raise ValueError(f"threshold must be > 0 and <= 1 (got {value!r})")
    return float(value)


@dataclass(frozen=True)
class CaseVerdict:
    """One case's outcome across its runs, with the invalid runs held apart from the rates.

    `valid_runs` excludes runs that produced no usable transcript. A measurement failure and a
    routing failure are different facts, and scoring the first as the second let negatives pass
    vacuously on empty transcripts.
    """

    case_id: str
    polarity: str
    targets: frozenset[str]
    hits: int
    valid_runs: int
    invalid_runs: int

    @property
    def inconclusive(self) -> bool:
        return self.valid_runs == 0

    @property
    def rate(self) -> float | None:
        return None if self.inconclusive else self.hits / self.valid_runs

    def passed(self, threshold: float) -> bool:
        """A case is never `passed` while it is inconclusive, in either polarity.

        The threshold is validated HERE rather than at the caller because this is the only place
        it changes a verdict: a threshold of 0 passes every positive on zero correct runs, and a
        bool or a string would compare without raising and silently decide cases.
        """
        threshold = validated_threshold(threshold)
        if self.inconclusive:
            return False
        rate = self.rate or 0.0
        return rate >= threshold if self.polarity == "positive" else rate == 0.0


def scoring_targets(case: dict, members: Iterable[str]) -> tuple[str, frozenset[str]]:
    """The polarity and the component set this case is graded against.

    A negative that omits `expect_not_fires` is graded against the WHOLE cluster: that omission is
    the documented broad negative, not a missing field.
    """
    polarity = case.get("polarity")
    if polarity not in ("positive", "negative"):
        raise ValueError(
            f"case {case.get('id')!r} polarity must be exactly 'positive' or 'negative' "
            f"(got {polarity!r})"
        )
    if polarity == "positive":
        field = "expect_fires"
        raw = case.get(field)
    elif "expect_not_fires" in case:
        field = "expect_not_fires"
        raw = case[field]
    else:
        return polarity, frozenset(members)
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"case {case.get('id')!r} {field} must be a non-empty list")
    member_set = set(members)
    invalid = [t for t in raw if not isinstance(t, str) or not t.strip() or t not in member_set]
    if invalid:
        raise ValueError(
            f"case {case.get('id')!r} {field} contains invalid cluster member(s): {invalid!r}"
        )
    return polarity, frozenset(raw)


def grade_case(
    case: dict,
    members: Iterable[str],
    runs: Iterable[frozenset[str] | set[str] | None],
) -> CaseVerdict:
    """Grade one case from its per-run firing sets.

    Takes firing sets rather than transcripts so the caller reads each transcript ONCE against
    the whole fleet roster: the verdict only needs the cluster members, but the diagnostic of
    what else fired -- a negative correctly landing on a component outside the cluster -- is only
    visible against the full roster, and re-reading per case would re-derive it.

    A `None` run is one that produced no usable transcript. It is excluded from the rates rather
    than counted as a miss, because a measurement failure and a routing failure are different
    facts; counting the first as the second let negatives pass vacuously on empty transcripts.
    """
    polarity, targets = scoring_targets(case, members)
    hits = 0
    valid = 0
    invalid = 0
    for fired in runs:
        if fired is None:
            invalid += 1
            continue
        valid += 1
        if fired & targets:
            hits += 1
    return CaseVerdict(
        case_id=str(case.get("id")),
        polarity=polarity,
        targets=targets,
        hits=hits,
        valid_runs=valid,
        invalid_runs=invalid,
    )
