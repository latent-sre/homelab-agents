# Does `tool_used` count an errored spawn? 2026-09-14

The MACH-001 phase-4 precondition the operator chose ("option A"): settle empirically what the
2026-09-13 pilot could only leave open. That pilot established `tool_used` counts CALLS rather
than successful spawns, but the errored call it happened to observe did not match the case's
regex, so it could not say whether a *matching* errored call is counted.

## Answer

**Yes. `tool_used` counts a matching call regardless of whether the spawn succeeded.**

| | |
|---|---|
| CLI | 2.1.270 (the CI pin) |
| Case | `evals/native-pilot/errored-spawn-counted/` |
| Command | `claude plugin eval . --eval-dir evals/native-pilot/errored-spawn-counted --ablation none --runs 3 -j 3 --no-publish --model sonnet --max-cost-usd 3 --keep-temp --trust-plugin` |
| Cost | $0.22 |
| Result | experiment grader PASS 3/3, control grader PASS 3/3, score 1.0 in every run |

The case instructs one `Agent` call with `subagent_type: "sde-agents:no-such-agent-probe"`, which
is not registered. Two graders make the three outcomes distinguishable: the **experiment** matches
that exact non-existent name, and the **control** matches any `subagent_type` at all, so an
experiment FAIL cannot be confused with the session never calling `Agent`.

Confirmed in all three preserved traces that the spawn really did fail:

```
CALL   subagent_type = "sde-agents:no-such-agent-probe"
RESULT is_error=True :: Agent type 'sde-agents:no-such-agent-probe' not found. Available agents: ...
```

## Why this matters for phase 4

`scripts/eval_routing.py` — the runner phase 4 retires — deliberately does the opposite. Its
`_fired_names` collects each `tool_use` naming a fleet member, collects the `tool_use_id`s whose
`tool_result` came back `is_error`, and then counts only the calls that did **not** error:

```python
for tid, names in candidates.items():
    if tid not in errored:
        fired |= names
```

So the two oracles disagree, and the direction of the disagreement depends on polarity:

- **Positive case** — the native grader is WEAKER. A run where the model chose the right component
  but the dispatch failed scores PASS natively and FAIL under the runner. A real routing
  regression could hide behind a dispatch that never succeeded.
- **Negative case** (`min: 0, max: 0`) — the native grader is STRICTER. An attempted-but-errored
  call on a forbidden component fails the negative natively, while the runner ignores it. For
  over-trigger detection that is arguably the better reading: the model made the wrong choice
  whether or not the dispatch landed.

This is not hypothetical: the 2026-09-13 pilot observed a naturally-occurring errored dispatch
(`Agent(sde-agents:root-cause)` — the model tried to spawn a skill as an agent).

One subtlety the runner learned the hard way and any replacement must preserve: **`is_error: true`
is not a reliable failure flag for `Skill`.** A skill that restricts tools is LAUNCHED through a
`tool_result` the CLI marks `is_error: true` with content `Execute skill: <name>`. Treating that as
a failure scored `lab-audit` 0/N despite correct routing on every run, and made an over-trigger of
it on a negative case invisible — a false PASS. Any fleet-side check that re-applies the runner's
semantics must keep the launch-signal exemption.

## Not covered

Whether an `llm` grader can see tool results well enough to substitute. Not tested; it is a paid,
non-deterministic judgment and the routing suite's graders are deliberately free and mechanical.

## Incidental confirmation

The pilot recorded, from docs rather than observation, that an untrusted directory under `--json`
is refused with exit 1 rather than prompted. Observed here on a fresh checkout: the first run
failed with exit 1 and `is not a trusted plugin directory`, and `--trust-plugin` was required.

## Follow-up: the seam option B needs, measured the same day

Accepting that `tool_used` is the weaker oracle leaves one question: can the fleet re-apply its
own reading to the native harness's runs? That needs the per-run transcript, so the shape of
`claude plugin eval --json` was read off a real run rather than from the help text. A throwaway
one-turn case (`schema-probe`, no tools, deleted after the measurement) was run against
`claude 2.1.270`:

- **`--json` carries a per-run `tracePath`.** Under `.cases[].arms.<arm>[].tracePath`, alongside
  `error`, `turns`, `costUsd`, `durationSeconds` and the per-grader verdicts. `error` is the
  invalid-run signal the fleet's scorer already needs: a run with no usable transcript is excluded
  from the rates rather than counted as a miss.
- **The trace is stream-json in the shape the fleet already parses** — `{"type":"assistant",
  "message":{"content":[…]}}` lines with `tool_use` and `tool_result` blocks, so
  `fleet.stream.correlate_tool_results` reads it with nothing new.
- **The trace does NOT survive the run by default.** `tracePath` pointed into
  `/tmp/claude-eval-*/out/`, which is removed when the run ends; the path in the result document
  was already dangling by the time it was read. `--keep-temp` preserves it, verified by reading
  the file back through the path the result gave.
- **`--keep-temp` leaves a directory the harness says it could not seal** when running as root,
  warning that everything outside `out/` may be agent-written. So a recorder must copy `out/` and
  then remove the temp directory itself; leaving them to accumulate is both a disk and a trust
  problem.

### The fleet-side reading reproduces the runner exactly

`fleet/routing.py` is that reading. It was not accepted on inspection: both it and
`scripts/eval_routing.py` were executed against the same generated inputs and their answers
compared.

| Differential | Inputs | Mismatches |
|---|---|---|
| `fired_components` vs `components_fired` | 12,400 transcripts (every tool × input key × value × result-shape combination, plus 4,000 randomized multi-call transcripts) | 0 |
| `grade_case` vs `score_case` | 8,004 case/threshold/run combinations across both polarities, the broad-negative default, invalid runs, and four malformed cases | 0 |

Agreement is only evidence if the comparison could have disagreed, so each differential was
mutation-checked: removing the skill-launch exemption (2,212 mismatches), dropping `Task` from the
routing tools (1,488), ignoring `is_error` (1,468), letting an inconclusive case pass (388),
grading a negative against the threshold instead of zero (879), emptying the broad-negative target
set (1,285), and counting an invalid run as a valid miss (869). All seven were caught.

One asserted difference turned out to be mine, not the runner's: a draft test expected a fleet name
embedded in prose (`"delegate to sde-agents:researcher now"`) to count as a dispatch. The runner
compares `strip_ns(value)` against the roster — the **whole** string value — so it never did, and
widening the reading would score every case whose prompt merely names a sibling as having fired it.
The test was corrected to the runner's semantics, not the reading to the test's.
