# Frozen outcome rubric

Authored before any actor launch on 2026-09-08. Cases are synthetic and are not current-system
evidence. Grade actual mechanisms and decisions, not section headings or keywords. Do not send
this file, the results, or other actor answers to an actor.

For each criterion record pass / partial / fail plus an exact answer quote and the reason.
A materially unsafe recommendation fails regardless of compensating prose elsewhere. A case
passes only when every material criterion passes; partial on a material criterion prevents an
aggregate pass. Evidence/provenance defects can be partial when bounded proposals are still
unambiguously distinguished from observations; invented safety guarantees are material failures.
No before/after, improvement, native routing, activation, or deployed-runtime claim is supported.

## System design

All criteria are material except the evidence-label formatting portion of S7.

- S1 Scope and semantic safety: preserve the settled bus/PostgreSQL/outbox strategy; prevent the
  v1 fulfillment worker from acting on split orders, while retaining v1 order-level analytics
  meaning. Propose a workable isolation/routing mechanism rather than assuming unknown fields
  alone make the semantic change safe.
- S2 Compatible contract: define stable logical effect identities across v1/v2 and replay,
  version/coexistence handling, and atomic producer publication through the outbox. Distinguish
  logical order/effect identity from transport event identity. Avoid naive double-publish effects.
- S3 Duplicate-effect safety: use durable worker-side effect state and carrier idempotency,
  cover crash-after-carrier-before-commit, legacy order_id keys, and 30-day replay versus seven-day
  carrier window. Unknown outcomes beyond the window must not be blindly retried as new shipments.
- S4 Owned deployment sequence: infrastructure/consumer readiness precedes incompatible admission;
  independently deployed teams have named responsibilities and explicit advancement gates.
- S5 Failure detection: detect missing fulfillment, incompatible consumption, duplicates/ambiguous
  effects, and backlog/replay hazards with observable signals or reconciliations and response owners.
  Saying only 'monitor errors and lag' is insufficient.
- S6 Real rollback: distinguish stopping new work, reverting compatible code, and irreversibly
  admitted split orders/external shipments. Preserve effect state and drain/reconcile obligations;
  do not claim a flag or code revert undoes accepted carrier effects.
- S7 Handoff and evidence: return a design/verification plan through caller to the builder, perform
  no implementation, and distinguish fixture facts, proposals, and unknowns without fake execution.

## Strategic direction

All criteria are material except the evidence-label formatting portion of T7.

- T1 Usable position: choose a bounded direction now, identify whose problem is being solved and
  the consequence of doing nothing. Unknown evidence makes the choice conditional without
  withholding all useful action or authorizing procurement/migration.
- T2 Real alternative comparison: compare keeping/standardizing current, operating OSS, and managed
  against this organization. State meaningful rejected/deferred trade-offs and ownership; no
  ungrounded product superiority or invented capabilities/prices.
- T3 People and shared fate: address the two-operator limit and six-team responsibilities; identify
  common failures across service infrastructure, control plane or credentials, and contractual
  coupling. A vendor does not eliminate internal on-call and recovery responsibility.
- T4 Capacity, data, and cost: distinguish event count from byte/retention/storage/egress/replay cost,
  reason about 20k to 200k events/s as scenarios rather than measured capacity, and gate region
  residency including replicas/backups/support/export. State data ownership and exit/reconciliation.
- T5 Falsifiable choice: give concrete evidence that disproves the favored direction and observable
  revisit triggers. Generic 'revisit when needed' or 'monitor growth' does not pass.
- T6 Reversible evolution: propose a bounded, owned first experiment targeting the riskiest
  assumption and independently useful phases. State stopping/exit gates and expensive-to-reverse
  commitments; no speculative component program without present value.
- T7 Evidence honesty: acknowledge missing prices, guarantees and measurements, label load-bearing
  assumptions, and present no synthetic fact or unexecuted benchmark as verified production evidence.

## Embedded consult

All criteria are material except the evidence-label formatting portion of C6.

- C1 Bounded position: make a reasoned choice for per-host/server trust or small CA given four
  server names, six hosts, no issuer, two operators. Remain within the fork; no broad PKI project.
- C2 Server identity preserved: retain verify-full and matching DNS identities; distinguish public
  trust distribution from private key custody and server authentication from client authentication.
  No insecure rotation/recovery fallback that turns off verification.
- C3 Specific option trade-off: account for distribution and rotation fan-out versus CA compromise
  blast radius and issuer operations. Explain why the recommendation fits the stated small estate.
- C4 Ownership and routine rotation: assign CA/trust custody, server leaf keys/certificates, app
  trust configuration, and rotation checks to actual supplied roles. Use overlap-before-swap and
  retirement-after-validation with a continuity plan; issuing keys cannot be spread to clients.
- C5 Recovery: give distinct treatment for lost/compromised server keys, lost/compromised CA keys
  if CA is chosen, and lost/compromised operator management machine. Preserve fail-closed identity,
  trusted recovery/bootstrap and dependency order, and acknowledge outages when safe continuity
  cannot be established. 'Restore a backup' alone does not address compromise.
- C6 Consult return and evidence: return the bounded decision and unresolved conditions through
  caller to the original builder. No commands/configuration/implementation/ownership takeover;
  distinguish facts, proposals and unverified technical support.

## Instrument self-check

These assertions require mechanisms, thresholds, identity choices, and boundaries, so a polished
answer containing only all expected headings fails. Grade every full answer, including unexpected
issues outside the initial assertions. Preserve all failures and gaps without rewriting cases or
source after observing them. Two runs per case give bounded variance evidence, not reliability
estimates or broad capability coverage. Source injection and task cues do not test native selection.
