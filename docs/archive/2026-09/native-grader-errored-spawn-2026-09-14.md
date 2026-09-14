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
