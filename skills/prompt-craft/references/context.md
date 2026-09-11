# Managing an agent's context

Read when an agent's problem is what it knows, when to load it, or that long runs degrade. The
universal method lives in `skills/prompt-craft/SKILL.md`. On any conflict, SKILL.md wins.

Context can be a limiting resource, but an error alone does not establish context exhaustion.
Inspect the actual inputs, loaded instructions, tool results, and runtime conditions. Treat missing,
stale, conflicting, or excessive context as hypotheses alongside tool and task-capability failures.

## Load context when it is needed

Load what the current step needs. Preload material required throughout the task.

- **Pointers over payloads.** A path, a query, or an identifier the agent can resolve costs a few
  tokens; loading the content adds to the active context. Use pointers only when the receiver
  can resolve them, and bind them to a revision when the exact bytes matter.
- **Predicate-keyed references** are the fleet's working form of this: a table that says "if the task
   involves X, read Y first". Keep the trigger in the entrypoint and load the depth when it applies.
- **Splitting an oversized file** into an entry plus siblings: the test of a boundary is that the
  entry stays comprehensible alone — needing a sibling open to follow it means the cut is in the
  wrong place. Name siblings by content role (`verification.md`, not `notes.md`) so the filename is
  the trigger, and write pointers that name both trigger and target ("touching migrations? read
  `migrations.md` first"). Splitting removes nothing — delete obsolete content outright — and stop
  splitting while the entry file is still legible.
- **What must be up front** is what changes behavior on *every* step: the mandate, the output
  contract, the hard prohibitions. Anything conditional belongs behind a predicate.
- Beware the opposite failure: an agent that must fetch three files before it can start has traded
  tokens for latency and for the chance it fetches the wrong ones. Preload what it always needs.

## Specify context and handoffs

A spawned agent receives what the host's selected context or fork mode supplies. Check the
actual mode; a separate context window can contain inherited conversation history. Specify the
goal, constraints, paths, acceptance criteria, and exclusions in the handoff instead of relying
on implicit inheritance. For an independent eval, keep prior attempts and expected answers out
of the context given to the agent under test; the grader receives the evaluation criteria.

Specify what the receiver needs in the return message or linked artifact: findings, evidence,
constraints, and unresolved work. A schema helps detect omissions; it does not guarantee that the
content is correct, complete, or safe to act on.

## Preserve evidence through long runs

- **Compaction** summarizes history to free space. It is lossy in a specific way: the summary keeps
  what looked important and drops the rest, so anything load-bearing must be written **outside** the
  context in an authorized, task-owned artifact. Preserve the plan, decisions and their reasons,
  counts and caps, paths in flight, and evidence needed to resume.
- **Prefer compaction at a task boundary when you control it.** If compaction occurs mid-debug,
  preserve observations, failed hypotheses, and the next discriminating check as well as conclusions.
- **Repeated failed corrections need diagnosis.** Check whether the cause is contradictory
  history, missing evidence, a tool/runtime failure, or an incorrect hypothesis. When accumulated
  context is implicated, try a fresh context carrying the goal, constraints, findings, and remaining
  uncertainty. Compare outcomes; restarting alone does not establish or repair the cause.
- **Delegate bounded exploration when useful.** Use an available, authorized subagent when its
  focused result saves more context than the handoff costs; local targeted reads remain valid.
- **Start unrelated work in a fresh session when stale context would interfere.** Carry forward
  relevant decisions explicitly; related follow-ups can reuse useful context.

## Durable state lives in files

For work spanning sessions or agents, preserve needed state in the existing authorized artifact.
Do not create competing trackers or store sensitive material merely to survive compaction.
Before resuming an action, reconcile recorded progress with actual external state; a file alone
does not prove whether an interrupted action completed or make its retry safe.

## Diagnosing a possible context problem

| Symptom | Discriminating check | Act on the evidence |
|---|---|---|
| Ignores an instruction it followed earlier | Was the instruction loaded, contradicted, truncated, or superseded? Did a tool or permission fail? | Repair the identified loading/conflict/tool issue; shorten context only if implicated. |
| Re-reads a file repeatedly | Did the file change, did the earlier read truncate, or are usable notes absent? | Refresh changed or incomplete evidence; persist a concise finding when repeated discovery is the cause. |
| Confidently wrong about a changed fact | Compare the supplied source/version and any retrieval cache with current authority. | Refresh the stale source or correct interpretation; don't assume a context reset is needed. |
| Worker does a different job | Compare the handoff, worker definition, effective tools, and inputs actually received. | Fix the mismatched contract or missing input at its owner. |
| Errors appear late in a session | Compare preserved constraints and earlier traces; check tool expiry, truncation, changing state, and task difficulty. | Restore a missing fact or resolve the external failure; test compaction or a fresh handoff when context is the supported cause. |

A symptom chooses the next observation, not the diagnosis. A successful short-session comparison
is evidence for that comparison's conditions, not a universal context-length rule.
