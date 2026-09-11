# The engineering program

What this repository is building, mapped to the machinery that implements it. This document is
deliberately mechanism-anchored so it cannot rot into folklore: it names no live roadmap item, no
count, and no measurement — episodes belong to the dated records under `docs/archive/` — and the
fleet validator resolves every concrete path named here against the tree, so a renamed or deleted
mechanism fails T0 instead of quietly outliving its documentation. `AGENTS.md` carries the
compressed form every session loads; this file is what a session reads when it needs to know *why*
a discipline exists before touching it.

The premise all four strands share: **a session is stateless.** Whatever it learned, decided, or
verified dies at exit unless it lands in an artifact, and the next session will read that artifact
with no memory of why it was written — and will trust it more than it should. Each strand is one
consequence of that premise, engineered.

## Handoff engineering — artifacts are the only carrier

A handoff is complete when the receiving session can act correctly with nothing but the artifact.

- **End-of-task packets.** Every agent definition carries a packet contract — the validator
  requires the section and pins the `[verified]/[sourced]/[unverified]` evidence stems exactly, so
  the triad cannot drift file by file. Evidence labels exist because the reader cannot interrogate
  the writer: a claim's strength must travel with the claim.
- **Task briefs.** `agents/homelab-engineer.md` supplies the objective, fixed decisions,
  constraints, acceptance, authority, and remaining work when application development crosses to
  `agents/sde-fullstack.md`. The receiver checks substance rather than a digest or receipt shape;
  existing plan files can carry the brief. No handoff grants permission to apply a live change.
- **Procedure gaps.** `skills/runbook/SKILL.md` separates document authority from an unknown
  procedure. Supported sections can progress while an unsupported command remains a visible,
  non-runnable gap. A proposal carries facts and ownership, not an executable instruction.
- **Design rules that follow.** One writer per artifact (the concurrency rule in `AGENTS.md`);
  receipts prove transfer, not correctness; grade end state over echo. A schema-conformant packet
  can still omit the decisions behind it, so fewer, richer boundaries beat many thin ones.

## Loop engineering — convergence across memoryless sessions

Any process that revisits the same ground — audits, incidents, upgrade campaigns, eval rounds —
must converge even though every iteration starts amnesiac.

- **Durable dispositions.** An audit finding is emitted `open` and flipped to `fixed` or
  `accepted` by the write-authority side (`skills/lab-audit/references/checks.md` owns the row
  format). A written, discoverable exception is what stops a memoryless successor from re-flagging
  the same deliberate choice forever.
- **Recurrence merge.** Re-observed findings update the existing operating record when the
  task permits writing; otherwise the caller receives the evidence and that record's owner.
  A second record for the same unresolved condition splits the next session's view.
- **Status transitions gate authority.** Incident handling holds mitigate-first authority only
  while the situation is an outage; the explicit downgrade to follow-up
  (`skills/lab-incident/SKILL.md`) is the edge that ends the emergency regime.
- **Paired measurement.** A loop that edits graded text owes before/after runs under identical
  recorded conditions; the automated reuse check that once answered whether the before side already
  existed, scripts/eval_baseline.py, was retired 2026-09-01 — a stored capture is now reusable only
  when a session manually confirms cluster, cases, evaluator, and plugin bytes are unchanged.

## Graph engineering — authority is typed edges

Which member may write what, who hands to whom, where approval sits: declared per definition and
enforced per host, never inferred from prose.

- **Explicit grants.** Every agent declares `tools:` — the validator requires the list because
  omission silently inherits every tool, and parenthesized specifiers that read as limits while
  the runtime ignores them are rejected outright.
- **Enforced read-only.** A Bash-holding agent with no write tool must be in
  `scripts/readonly-guard.py`'s roster; unguarded, "read-only" is a promise, not a control. The
  emitter/consumer splits this creates — an auditor that cannot flip its own findings — are
  deliberate edges, not indirection.
- **Enforced interposition.** A live-effect agent gets a fleet-owned prompt, not a promise:
  `scripts/live-effect-gate.py` answers `ask` for listed live-effect argv `homelab-engineer` invokes
  and `deny` when the session cannot prompt, so "managed gate" names a hook the plugin ships
  rather than evidence the model must produce. Unlisted commands and the main loop remain under
  the host's own permissions; the filter is not a sandbox. The same scoping rule as the guard — the payload's
  `agent_type`, never prose — and the same structural exclusion from hosts whose payload cannot be
  scoped.
- **Separated layers.** Authored edges, per-host authority projections, and the routing overlay
  stay three layers kept deliberately apart, because co-membership is not behavioral coverage; the
  offline report that once rendered them together, scripts/capability_graph.py, was retired
  2026-09-01 with no replacement — the separation is now a reviewer discipline, not a generated
  diagram.
- **The boundary decision.** `docs/decisions/2026-07-31-ai-graph-engineering.md` (accepted) owns
  what the graph layer is allowed to become and what evidence reopens it.

## Self-learning — explicit maintainer work

`skills/self-improve-loop` is an explicitly invoked maintainer workflow. Operating agents do not
preload it or carry a mandatory Learning lifecycle in every task packet. Useful discoveries still
have a destination: update the existing owned artifact when authorized, or report the evidence,
remaining gap, and owner. An unverified observation stays unverified.

The maintainer's retro owns candidate evaluation and promotion when that work is requested. Its
record vocabulary is writer discipline, not a claim that a retired ledger or packet checker still
persists or validates state. The scoped retirement and handoff compatibility decision is recorded
in `docs/decisions/2026-09-07-homelab-operating-flow.md`.

## The reading rule

The reader of fleet prose is the next session, not the operator's memory. A fleet of stateless
workers re-creates the conditions organizations invented coordination ceremony for — no shared
memory, artifact-only communication, claims that cannot be trusted unverified — so owner slots,
status lifecycles, contemporaneous capture, and written justifications here are often mechanisms
of the strands above wearing organizational vocabulary. Two questions decide any trim: **who is
the real reader, and what consumes this artifact.** If the honest answers are "only the operator,
today" and "nothing", trim it. If the reader is a future session, or the consumer is a script, a
grader, or a guard, the ceremony is a mechanism and the trim is a regression. The dated records
under `docs/archive/` hold both kinds of verdict with their evidence; re-reading them is cheaper
than re-litigating them.

The counterweight binds with equal force, and the same archive paid for it: coordination is not
free. Prefer fewer handoffs over richer ones; keep one writer per artifact; add structure only at
the boundaries that remain after the handoff count is minimized. A mechanism nobody consumes is
not rigor — it is the next round's finding.
