# Managing an agent's context

Read when an agent's problem is what it knows, when to load it, or that long runs degrade. The
universal method lives in `skills/prompt-craft/SKILL.md`. On any conflict, SKILL.md wins.

Context can be a limiting resource, but an error alone does not establish context exhaustion.
Inspect the actual inputs, loaded instructions, tool results, and runtime conditions. Treat missing,
stale, conflicting, or excessive context as hypotheses alongside tool and task-capability failures.

## Just-in-time beats up-front

Load what the current step needs, when it needs it — not everything that might be relevant.

- **Pointers over payloads.** A path, a query, or an identifier the agent can resolve costs a few
  tokens; the resolved content costs thousands and sits there for the rest of the run.
- **Predicate-keyed references** are the fleet's working form of this: a table that says "if the task
  involves X, read Y first". The router is always loaded and cheap; the depth loads only when its
  predicate trips. That is why the craft skills are structured the way they are.
- **Splitting an oversized file** into an entry plus siblings: the test of a boundary is that the
  entry stays comprehensible alone — needing a sibling open to follow it means the cut is in the
  wrong place. Name siblings by content role (`verification.md`, not `notes.md`) so the filename is
  the trigger, and write pointers that name both trigger and target ("touching migrations? read
  `migrations.md` first"). Splitting removes nothing — delete obsolete content outright — and stop
  splitting while the entry file is still legible.
- **What must be up front** is what changes behavior on *every* step: the mandate, the output
  contract, the hard prohibitions. Anything conditional belongs behind a predicate.
- Beware the opposite failure: an agent that must fetch three files before it can start has traded
  tokens for latency and for the chance it fetches the wrong ones. Preload the two things it always
  needs.

## Where context comes from, and what a subagent does not get

A spawned agent receives its definition, the project context, its preloaded skills, and the prompt
you wrote — **not** the parent's conversation. Everything the worker needs must be in that prompt:
the goal, the constraints, the paths, the acceptance criteria, and what is out of scope.
Underspecified handoffs are the most common multi-agent bug, and they present as the worker
confidently doing a slightly different job.

Corollary: the worker's *return message is the entire interface*. Specify its shape. Free prose loses
constraints at every hop; a schema (or a required slot list) survives.

## Long runs: compaction, and why rewind beats correction

- **Compaction** summarizes history to free space. It is lossy in a specific way: the summary keeps
  what looked important and drops the rest, so anything load-bearing must be written **outside** the
  context — a progress file, the repo, a commit — or it is gone after the next compaction. Facts that
  must survive: the plan, decisions and their reasons, counts and caps, file paths in flight.
- **Compact at a boundary, never mid-debug.** A summary taken halfway through an investigation keeps
  the conclusions and loses the evidence, which is exactly backwards.
- **Repeated failed corrections need diagnosis.** Check whether the cause is contradictory
  history, missing evidence, a tool/runtime failure, or an incorrect hypothesis. When accumulated
  context is implicated, try a fresh context carrying the goal, constraints, findings, and remaining
  uncertainty. Compare outcomes; restarting alone does not establish or repair the cause.
- **Isolate exploration.** Reading twenty files to answer one question should happen in a subagent
  whose context you can throw away; the parent keeps the answer, not the twenty files.
- **A new task gets a new session.** Compaction manages a long run; it does not make a finished
  task's residue useful to the next one. Carrying a window across unrelated tasks buys nothing and
  costs attention.

## Durable state lives in files

For anything that spans sessions or agents: the spec, the backlog, the progress notes, and the
decisions belong in the repository. A context window is working memory; the repo is storage. An
unattended loop that keeps its state in files can be restarted at any point, and one that keeps it in
context cannot be restarted at all.

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
