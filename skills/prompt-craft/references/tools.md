# Designing an agent's tool surface

Read when deciding which tools an agent gets, or when designing tools for a model to call. The
universal method lives in `skills/prompt-craft/SKILL.md`. On any conflict, SKILL.md wins.

## The tool list is the mandate

An agent's capabilities are its tools, not its prose. "You are a read-only reviewer" plus `Write` is
a suggestion; omitting `Write` is a fact. Design the list first, then write the prose to match — and
when the two disagree, the list wins at runtime no matter which one is more eloquent.

- **Least tools that make the job possible.** Each additional tool is authority you are granting for
  the lifetime of every task, and an extra failure mode to reason about.
- **Enumerate explicitly** — an absent `tools:` field inherits everything.
- Pair the grant with the reason in the agent's body ("your `Bash` is for git history and search"),
  so a later reader knows what to keep when they trim.
- **A read-only agent is the cheap, safe default** for anything investigative: no writes, no network,
  no shell. Most "look at this and tell me" work needs `Read`, `Grep`, `Glob` and nothing else.

## When to promote a Bash invocation into a real tool

An agent that shells out to accomplish something structured is a tool waiting to be written. Promote
when any of these hold:

- **The output needs parsing.** A tool returning a typed structure beats the model parsing text it
  half-remembers the format of.
- **The operation is dangerous.** A narrow tool (`restart_service(name)`) can validate its input and
  refuse the rest; `Bash` cannot be narrowed after the fact.
- **It happens every task.** A recurring shell incantation is a tool the model keeps re-deriving —
  and each derivation is a chance to get a flag wrong.
- **You need an audit trail.** Tool calls are legible in a transcript; a shell pipeline is one blob.

Keep it as `Bash` when the work is genuinely ad-hoc exploration, or when writing the tool costs more
than the risk it removes. Say which, rather than drifting.

## Designing a tool the model can use correctly

- **Name it for the intent**, not the implementation: `find_owner`, not `query_ldap_v2`.
- **Description = when to use it**, in the words the calling context will contain. This is the same
  routing rule as an agent description, and it fails the same way: too vague and it never fires, too
  broad and it fires on everything.
- **Few parameters, obvious types.** Every optional parameter is a decision the model can get wrong.
  Enums over free strings wherever the set is known — an enum is a constraint the runtime enforces,
  a string is a hope.
- **Return what the model needs next, not everything available.** A 200-field JSON blob costs context
  on every call and buries the three fields that matter. Summarize server-side.
- **Errors are instructions.** "Not found" teaches nothing; "no user named X; call list_users to see
  valid names" tells the model its next move. A good error message is the cheapest agent improvement
  available.
- **Idempotent where possible**, and explicit where not — the model *will* retry.
- **Confirm irreversible actions** at the tool boundary, not by asking the model to be careful.
- **One tool per responsibility.** Two tools that could both handle a request produce inconsistent
  routing; if they overlap, merge them or make the boundary explicit in both descriptions.

## Tool sprawl

Tool definitions consume context when the host exposes them; deferred discovery can change what
is loaded. There is no fleet-wide tool count at which selection must fail or schemas dominate cost.
Measure the actual loaded schema size, selection errors, and task outcomes before changing the
surface. A larger well-separated set may work better than a smaller ambiguous one.

If traces show overlap, test sharper descriptions or consolidation of equivalent operations. If
unused schemas dominate context, test task-scoped discovery. Split roles only for a demonstrated
context or authority need; an enum merger must not widen permissions. Compare the same tasks and
failure paths before calling any option an improvement.
