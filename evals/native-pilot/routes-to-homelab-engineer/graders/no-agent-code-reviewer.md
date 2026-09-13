---
type: tool_used
tool: Agent
min: 0
max: 0
arm: both
input_match: '"subagent_type"\s*:\s*"(?:sde-agents:)?code-reviewer"'
---

The Agent tool was never called with subagent_type code-reviewer, namespaced or bare. A diff
verdict is the wrong destination for an observed container failure.
