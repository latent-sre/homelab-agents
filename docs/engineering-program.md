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
- **Optional interposition.** `scripts/live-effect-gate.py` defaults to no decision (`host`
  policy), preserving the host's actual permission flow. Operator-selected `prompt` policy adds
  `ask` for listed or unparseable live-effect commands from `homelab-engineer`, and `deny` when
  prompts are suppressed. This is a partial command filter, not a sandbox or a grant of task
  authority. The guard's agent-identity scoping and structural exclusion from unsupported hosts
  still apply; its own read-only enforcement is unchanged.
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

Before trimming fleet prose, identify its reader or consumer and the decision, action, recovery,
or check that depends on it. A future session needs enough context to act without the operator's
memory; that need does not make every repeated paragraph or template field necessary.

Preserve decision-changing facts, authority boundaries, unresolved uncertainty, and evidence
needed to resume. Remove redundant wording or replace it with a reference when the reader can
resolve the owning source at the point of use. If a script, grader, or guard consumes an exact
field or shape, preserve that contract or migrate the consumer and its checks in the same change;
do not delete it as prose cleanup. Check the resulting artifact against its actual consumer or a
representative task, and state what was not exercised.

Prefer fewer handoffs, one writer per artifact, and one owned record for each fact. Add structure
only where a remaining handoff, recovery step, or check needs it. The dated records under
`docs/archive/` retain prior decisions and evidence; consult the relevant record when a proposed
trim would change that decision.
