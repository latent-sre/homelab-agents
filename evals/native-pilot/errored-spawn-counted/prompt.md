---
name: errored-spawn-counted
description: MACH-001 phase 4 precondition. Determines whether a `tool_used` grader counts an Agent call whose input MATCHES its regex but whose RESULT is an error. The 2026-09-13 pilot established that the grader counts calls rather than successful spawns, but could not observe this case because the errored call it saw did not match that case's regex.
tags: [native-pilot, harness-semantics]
expected_outcome: The session calls the Agent tool once with subagent_type "sde-agents:no-such-agent-probe", which does not exist and therefore returns an error. What the graders then report is the measurement.
max_turns: 4
timeout_seconds: 180
allowed_tools: [Agent]
---

Call the Agent tool exactly once, with `subagent_type` set to the literal string
`sde-agents:no-such-agent-probe` and any short prompt.

This agent does not exist and the call is expected to fail. That is intentional — this case
measures the harness, not the fleet. Do not substitute a different agent, do not retry with a
corrected name, and do not fall back to another tool. After the call returns, reply with only the
word DONE.
