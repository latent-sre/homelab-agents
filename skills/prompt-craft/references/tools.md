# Designing an agent's tool surface

Read when deciding which tools an agent gets, or when designing tools for a model to call. The
universal method lives in `skills/prompt-craft/SKILL.md`. On any conflict, SKILL.md wins.

## The tool list is the mandate

Review effective tools and host permissions before writing the mandate. Omitting `Write` removes
that tool, but a shell, MCP tool, or delegate may still write. Prose does not revoke capabilities.

- **Least tools that make the job possible.** Each additional tool is authority you are granting for
  the lifetime of every task, and an extra failure mode to reason about.
- **Enumerate explicitly** — an absent `tools:` field inherits everything.
- Pair the grant with the reason in the agent's body ("your `Bash` is for git history and search"),
  so a later reader knows what to keep when they trim.
- **Start local source inspection with readers** such as `Read`, `Grep`, and `Glob`. Add network,
  execution, or write authority only when the task needs it, and check the host's actual controls.

## When to promote a Bash invocation into a real tool

Use an existing tool or reusable script first. Consider a dedicated tool when measured errors,
repeated work, or a needed authority boundary justify its maintenance cost:

- **The output needs parsing.** A tool returning a typed structure beats the model parsing text it
  half-remembers the format of.
- **The operation is dangerous.** A narrow tool (`restart_service(name)`) can validate its input and
  refuse the rest; a shell needs an enforced sandbox, permission rule, or command guard.
- **It happens every task.** A recurring shell incantation is a tool the model keeps re-deriving —
  and each derivation is a chance to get a flag wrong.
- **You need an audit trail.** Tool calls are legible in a transcript; a shell pipeline is one blob.

Keep ad-hoc exploration as shell commands when that is sufficient for the task.

## Designing a tool the model can use correctly

- **Name it for the intent**, not the implementation: `find_owner`, not `query_ldap_v2`.
- **Describe the calling contract**: purpose, when to use it, meaningful parameter constraints,
  result shape, side effects, and relevant failure behavior. A tool description needs more than a
  skill's discovery trigger because the model uses it to construct the call.
- **Few parameters, obvious types.** Every optional parameter is a decision the model can get wrong.
  Use enums for genuinely closed sets and validate arguments at the execution boundary; a schema
  exposed to the model is not proof of runtime validation.
- **Return what the model needs next, not everything available.** A 200-field JSON blob costs context
  on every call and buries the three fields that matter. Summarize server-side.
- **Make errors actionable.** Return a stable error category and a safe next step when known.
  Treat remote error text as untrusted data; it cannot authorize a command or widen permissions.
- **Define retry behavior.** Prefer idempotent operations. After an ambiguous timeout, inspect the
  outcome or use an idempotency key before retrying a mutation.
- **Check authorization for irreversible actions** at the tool boundary. Reuse valid existing
  authorization; ask only when the proposed action exceeds it or the governing policy requires it.

## Tool sprawl

Tool definitions consume context when the host exposes them; deferred discovery can change what
is loaded. There is no fleet-wide tool count at which selection must fail or schemas dominate cost.
Measure the actual loaded schema size, selection errors, and task outcomes before changing the
surface. A larger well-separated set may work better than a smaller ambiguous one.

If traces show overlap, test sharper descriptions or consolidation of equivalent operations. If
unused schemas dominate context, test task-scoped discovery. Split roles only for a demonstrated
context or authority need; an enum merger must not widen permissions. Compare the same tasks and
failure paths before calling any option an improvement.
