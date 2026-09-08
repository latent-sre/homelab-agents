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
- **Machine-checked grammar.** The packet linter that once rejected malformed packets,
  scripts/packet_lint.py, retired with the behavioral harness 2026-09-02; packet grammar is now
  writer discipline, checked only by the validator's heading and evidence-stem pins.
  `skills/runbook`'s propose packet is ordinary untrusted prose, not a closed grammar or a
  command-sanitization control. Its receiver independently checks the proposed path, evidence,
  and resolver; no field authorizes execution.
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
- **Recurrence merge.** A re-observed finding updates its existing row; the learning ledger's
  `observe` merge step retired with the ledger itself (2026-09-01) — the packet's Learning block is
  now the only candidate record, so a re-observed signal reaches the receiving coordinator as a
  fresh candidate rather than an update to a stored row. Twin records are divergence, not
  thoroughness.
- **Lifecycle over event.** Merged is not released, and released is not retested — the packet's
  `Promotion state` field keeps the tail states explicit (quarantined, proposed, approved,
  promoted, plus the terminal rejected/inconclusive/retired). The linter that once graded that
  field, scripts/packet_lint.py, retired with the behavioral harness 2026-09-02, so this is writer
  discipline now — but the field still exists because a loop that ends at "merged" silently never
  verifies what shipped.
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
  `scripts/live-effect-gate.py` answers `ask` for the live-effect argv `homelab-engineer` invokes
  and `deny` when the session cannot prompt, so "managed gate" names a hook the plugin ships
  rather than evidence the model must produce. The same scoping rule as the guard — the payload's
  `agent_type`, never prose — and the same structural exclusion from hosts whose payload cannot be
  scoped.
- **Separated layers.** Authored edges, per-host authority projections, and the routing overlay
  stay three layers kept deliberately apart, because co-membership is not behavioral coverage; the
  offline report that once rendered them together, scripts/capability_graph.py, was retired
  2026-09-01 with no replacement — the separation is now a reviewer discipline, not a generated
  diagram.
- **The boundary decision.** `docs/decisions/2026-07-31-ai-graph-engineering.md` (accepted) owns
  what the graph layer is allowed to become and what evidence reopens it.

## Self-learning — a maintainer's retro, not a shipped loop

The fleet once carried a full self-improvement loop: a Learning slot in every agent's packet, a
repo-local ledger with staged promotion, a drift checker, and a grader for the packet grammar. All
of it left the shipped fleet on the 2026-09-02 single-operator ruling: the ledger and drift
checker retired 2026-09-01, the grader 2026-09-02, and the packet slot and every preload the same
day. `skills/self-improve-loop` remains as a maintainer's retro checklist behind explicit
invocation, and the 34 promoted lessons whose released-version retest the ledger still tracked
are listed in `docs/archive/2026-09/learning-ledger-retirement-2026-09-01.md`.

- **Disposition is mandatory.** The one rule that survives for every session: a discovery is
  routed, filed as a gap, or dropped with a stated reason
  (`skills/self-improve-loop/references/discovery-routing.md`); silence is not a disposition,
  because a stored lesson is replayed uncritically and a wrong one compounds instead of fading.

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
