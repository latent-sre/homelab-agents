---
type: tool_used
tool: Agent
input_match: '"subagent_type"'
---

THE CONTROL. Matches any Agent call whatsoever. Without it, a failing experiment grader is
ambiguous: it could mean the harness does not count errored spawns, or simply that the session
never called Agent at all. Read the two together — experiment FAIL plus control FAIL is an
unusable run, not an answer.
