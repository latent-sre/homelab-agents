---
type: tool_used
tool: Agent
input_match: '"subagent_type"\s*:\s*"sde-agents:no-such-agent-probe"'
---

THE EXPERIMENT. This matches the Agent call that is guaranteed to ERROR, because no such agent is
registered. If this grader PASSES, `tool_used` counts a matching call regardless of whether the
spawn succeeded — meaning a migrated routing case can pass on a spawn that failed, an oracle
strictly weaker than the retiring runner's `spawn_succeeded`. If it FAILS while the control below
passes, the grader requires a successful spawn and the oracles are equivalent.
