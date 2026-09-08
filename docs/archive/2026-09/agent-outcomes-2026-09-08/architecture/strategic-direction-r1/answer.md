# Decision record: a common event contract, with transport chosen by evidence

**Status: proposed strategic direction; bounded evaluation only.** This document does not
authorize a purchase, production change, or migration. **[sourced]** Those are the limits of the
consult in [task.md](task.md:23).

**Decision:** keep the team-owned PostgreSQL outboxes and queues as the current transport, and
make consistent contracts, reconciliation, and replay the destination's first layer. Evaluate
managed transport as the preferred escalation if measured capacity, recovery, or operating cost
outgrows that arrangement. Do not start a self-operated shared event cluster or build a broker.
This is a direction for five years, with evidence gates, rather than a five-year vendor commitment.

**[unverified — architectural judgment]** This approach is most likely to improve the known
cross-team problem within the staffing constraint while retaining a choice of future transport.
It does not establish that the existing system can handle tenfold growth, or that a managed
service can satisfy the requirements.

## Problem, constraints, and success

**[sourced]** Six teams have independent outboxes and queues, inconsistent interfaces and replay,
and an incident that required six reconciliations. Neither the current capacity ceiling nor its
complete cost is measured. Independent service deployment is required, and synchronous global
ordering has no demonstrated need. See [task.md](task.md:12).

The immediate problem is therefore fragmented recovery and contracts. **[unverified]** A single
broker could leave those problems intact: teams would still need to agree on event meaning,
consumer compatibility, and how to repair business state. Conversely, common contracts may
address much of that pain without consolidating infrastructure. The evaluation must test this
hypothesis rather than assume that consolidation is the remedy.

**[sourced]** Traffic is currently 20,000 events/second; planning must consider tenfold growth with
uncertain timing. There are two platform operators and no capacity for a new round-the-clock
team. Customer data must stay in the approved region. Event sizes, retention, and vendor prices,
SLAs, residency, limits, replication, replay, and delivery semantics are unknown.
See [task.md](task.md:7) and [task.md](task.md:18).

Proposed success criteria are:

- Each event stream has a business owner, a documented compatibility and delivery contract, and
  a replay procedure that its consumers can execute without coordinating service deployments.
- A representative cross-team recovery follows one shared procedure with explicit per-team
  checkpoints and completion evidence. It avoids six improvised investigations; it does not
  pretend six distinct business domains have one reconciliation authority.
- The chosen transport meets agreed lag and recovery objectives under a representative load,
  with bounded backlogs, resident data, and a support model the organization can staff.
- Capacity and full cost are measured at today's demand and modeled, with uncertainty, through
  200,000 events/second. A growth scenario is not a promise that today's system supports it.

Non-goals are a custom event platform, global ordering, distributed business transactions,
central ownership of product data, and a mandatory simultaneous migration.

## Durable alternatives

All comparative cost and capability statements below are **[unverified]** hypotheses to test;
none is a product guarantee or a measured conclusion.

| Alternative | Ownership and cost curve | Trade-off and decision |
|---|---|---|
| Keep everything as it is | Each team operates its current outbox, queues, and recovery. Platform ownership stays fragmented. Costs grow with per-team workers, storage, database contention, and repeated recovery work. | Smallest immediate change, but accepts the known inconsistent interfaces and reconciliation burden. Keep as the evaluation control, not the destination. |
| Standardize current transports | Teams retain producers, consumers, queues, and business recovery. The two operators steward a small common contract, measurements, and reusable recovery guidance. Costs remain distributed and include adoption work. | Preserves independent deployment and avoids a new shared transport dependency. Accepts several queue implementations and a measured ceiling that may later force transport change. **Chosen first direction.** |
| Adopt and self-operate an open-source platform | Platform operators would own capacity, upgrades, quorum or replication behavior, storage, restores, security, and transport incidents. Teams still own event semantics and consumers. Infrastructure and operator time grow with replication, retention, throughput, and failure-domain count. | Could offer shared capabilities if proved, but creates a substantial operational mandate. **Not selected under current staffing.** Reconsider only with a demonstrated unmet requirement and a funded support model. Open-source availability does not establish supportability. |
| Buy managed transport | Provider would own only the infrastructure duties established by contract. Operators retain tenancy, identity, quotas, bills, residency configuration, and vendor escalation. Teams retain outboxes, consumer correctness, and reconciliation. Costs depend on the actual billing units, payloads, fan-out, storage, replay, and support. | Potentially reduces infrastructure work; accepts vendor limits, variable bills, provider dependency, and exit cost. **Preferred candidate for escalation, conditional on evidence.** No purchase or migration decision yet. |

Building a proprietary broker is rejected: **[unverified — judgment]** the supplied problem does
not justify adding broker correctness and long-term maintenance to this organization's remit.
A small shared contract and recovery procedure are the simpler design to prove first.

## Destination and ownership

The proposed destination has team-owned business data and outboxes, consistent event contracts,
and transport that can evolve by stream. It need not have one physical broker. Product services
continue deploying independently.

| Boundary | Proposed accountable owner | Required contract |
|---|---|---|
| Business state and publication | Each producing product team | Own event meaning and schema; establish whether business change and outbox insertion commit atomically. Define a repair path for any publication source that cannot provide that property. |
| Delivery to business effects | Each consuming product team | Own deduplication, retries, poison-event handling, processing checkpoints, and business reconciliation. Identify irreversible effects before allowing replay. |
| Shared interoperability | Platform owner, with one delegate per team for adoption | Maintain a minimal versioned envelope, compatibility rules, telemetry definitions, and a common replay request/report shape. Each team owns conformance and rollout in its service. |
| Transport operations | Team owners for current queues; platform operators for any later shared tenancy | Own transport health, access, budgets, capacity and recovery evidence. A managed provider's role is limited to its verified agreement. |
| Cross-team incident coordination | A named incident lead from the existing support arrangement | Coordinate shared checkpoints; each team certifies its own business state. The existence and coverage of that arrangement are **[unverified]** and must be established before operational adoption. |
| Residency and commercial acceptance | Organization's designated security/data owner and procurement owner | Accept the approved-region interpretation, evidence, support terms, and cost exposure. These owners must be named; this document cannot supply their approval. |

Proposed interface invariants:

- Use a stable event identifier, event type and schema version, producer identity, and occurrence
  time. Add an entity key and sequence only where the domain needs ordered processing. Treat
  envelope fields as potentially sensitive data too.
- Design consumers to tolerate duplicate delivery and retries. This is a proposed minimum
  contract, not a claim about current or vendor delivery semantics. No end-to-end exactly-once
  promise is made; business effects require their own idempotency and reconciliation.
- Establish per-stream ordering requirements. Do not require global ordering without a business
  invariant that cannot be met through narrower keys or explicit workflow coordination.
- Producers introduce compatible schema changes first; consumers migrate independently.
  Breaking changes use overlapping versions with a retirement period derived from supported
  consumers and replay retention. Avoid a central runtime schema dependency unless a trial
  demonstrates its need.
- A replay specifies stream, event range, consumer scope, initiating owner, rate limit, progress,
  and completion evidence. Replaying must not bypass current access or data-lifecycle rules.
  A failure queue is not the system of record for business state.

These are design requirements. **[unverified]** Existing implementations may not satisfy them.
Do not hide transport-specific limits behind a universal API promising identical behavior.
Record those limits alongside the common contract.

## Failure domains and data movement

**[unverified]** The current queues' hosting, database sharing, credentials, and backup topology
are unknown. Six team-owned queues are not evidence of six independent failure domains.
Inventory those dependencies before describing present-day isolation.

For either current or future transport, map the entire path: business database → outbox →
delivery/retry storage → consumer → downstream business effect, including logs, backups, replay
exports, credentials, and control-plane dependencies. A future shared transport introduces shared
fate through regional service, control plane, capacity limits, and administrative credentials.
Logical namespaces count as isolation only where enforcement and failure behavior are proved.

Proposed safeguards and ownership are:

| Failure | Detection and recovery design | Owner |
|---|---|---|
| Publisher stalls or delivery loses progress | Monitor oldest unpublished age and outbox growth; compare committed source records with publication checkpoints. Bound database pressure and define producer backpressure. | Producing team |
| Consumer poison event, duplicates, or replay overload | Monitor consumer lag, repeated failures, deduplication and replay progress. Quarantine scoped failures; throttle and pause replay independently of live traffic. Reconcile effects before resuming. | Consuming team |
| One team exhausts shared capacity | Measure per-team utilization and throttling; test enforced quotas and recovery under noisy-neighbor load. Separate physical instances if required isolation cannot be established. | Transport owner |
| Schema change or replay reintroduces invalid historical data | Compatibility checks cover retained versions; recovery checks include data lifecycle restrictions and external side effects. Do not rely on delivery success as proof of business correctness. | Producer and affected consumers |
| Shared identity or administration compromise | Use team-scoped identities and least privilege; audit access and administrative changes. Test revocation without disabling unrelated teams. | Transport and security owners |
| Approved region unavailable | Test the permitted restore path and report achieved recovery time and loss window. Do not fail over or export customer data to an unapproved region. | Transport owner; leadership accepts any residual outage exposure |

**[unverified]** In-region redundancy, acceptable outage duration, recovery loss limits, and whether
other regions could ever be approved are unresolved. No availability commitment is supportable
until these are resolved. Vendor support access and diagnostic exports are part of the residency
review; a regional endpoint alone is insufficient evidence.

Operational dashboards should show publication age, consumer lag, backlog bytes, replay progress,
failures, per-team quota use, and spend. Page the owner of violated delivery/recovery objectives;
route capacity forecasts and cost trends to working-hours review. **[unverified]** The actual
thresholds and existing pager coverage must be agreed in the evaluation. Managed service support
does not replace responders for application incidents.

## First useful step and bounded evaluation

Propose a four-week evaluation with a ceiling of eight operator-days and twenty product
engineer-days across two representative teams; these are planning caps requiring caller allocation,
not existing commitments. Stop at the cap with a decision record, including unresolved evidence.
Use synthetic, representative payload shapes in isolated existing evaluation capacity. New paid
services, production traffic changes, and real customer-data transfers require a separate decision.

1. **Week 1: establish the baseline and acceptance criteria.** Select two teams spanning a
   cross-team workflow and a contrasting consumer pattern. Collect event-size distributions,
   peak and average rates, fan-out, current resource usage, support effort, and the prior incident's
   reconciliation steps. Each team supplies retention, maximum delivery lag, recovery time, and
   acceptable loss requirements. Platform operators map shared dependencies. Freeze these
   criteria before candidate comparisons; a missing criterion remains an incomplete gate.
2. **Week 2: prove the smallest improvement.** Draft the common contract and rehearse the prior
   incident's recovery on synthetic data, using existing queues. Measure recovery duration,
   manual decisions, handoffs, duplicates, and unreconciled records against the current procedure.
   Exercise consumer version skew and interrupted replay. The deliverable is a reusable contract,
   recovery procedure, baseline, and measured recovery comparison, even if evaluation stops here.
3. **Weeks 3–4: test the riskiest transport assumptions.** Find the current arrangement's stable
   capacity envelope under representative payloads, skew, consumers, and retention. Include a
   worker failure, a stalled consumer, one team's saturation, and replay alongside live-equivalent
   traffic. Investigate no more than two managed candidates through documented evidence and
   non-purchasing evaluation where permitted. Consider a self-operated candidate only far enough
   to establish staffing and capability gaps; do not spend the evaluation building a cluster.

For each runnable option, record sustained throughput, p99 end-to-end lag, backlog growth,
recovery duration, lost/duplicated business effects, resource cost, and operator intervention.
Test today's representative peak mix; explore up to 200,000 events/second where the evaluation
environment permits. A proposed capacity gate is the agreed peak plus 50% headroom for one hour,
including the agreed replay workload, with no growing backlog and all frozen latency/recovery
objectives met. That gate is a design target to ratify, not a measured capability. Extrapolation
from smaller runs must remain labeled **[unverified]**.

For managed options, obtain versioned evidence covering quotas and quota increases, delivery and
ordering, retention, replay limits, failure behavior, availability exclusions, restore and export,
support coverage, and every place customer data can be stored or accessed. Contractual residency
evidence and exercised failure behavior answer different questions; neither substitutes for the
other. Unavailable trials or documentation produce an evidence gap, not a passing result.

Cost the same workload for every option. Storage starts with average events/second × average
encoded bytes/event × retention seconds, then adds the measured effects of replication, indexes,
backups, retries, and replay copies. Network and processing depend on fan-out and replay, not
just ingress rate. Include operator and team time, incident/recovery work, support, migration,
parallel-running costs, and exit export. Use a demand range through tenfold growth and record
quotation dates and uncertainties. **[unverified]** There is currently no defensible dollar
estimate, cost winner, or vendor SLA comparison.

## Evolution, reversibility, and decision gates

**Phase 1 — common contracts on existing queues.** After the evaluation and a separate
implementation decision, adopt one stream at a time. Each step yields clearer ownership and
recovery. Keep old consumer versions compatible during transition. This is mainly a **two-way
door**, though published schemas and downstream reliance become expensive to reverse.

**Phase 2 — conditional managed pilot.** Request approval only if a candidate passes residency,
delivery/recovery, independent deployment, isolation, staffing, and full-cost gates. Its business
case must show a measured benefit: closing a capacity/recovery gap or reducing accepted total
operating cost. Start with one bounded stream using an outbox/checkpoint boundary and a shadow
consumer that cannot create business effects. No second live delivery path may independently
apply the same business effect.

Before cutover, prove resumable checkpoints and the ability to reconcile events between old
and new paths. Retain the old path for an agreed recovery window. A lag, correctness, residency,
or isolation gate failure stops the pilot. Rollback pauses delivery as needed, fences the new
consumer's effects, resumes the old path from reconciled progress, and deduplicates overlap.
It does not undo irreversible business actions already taken; those require team-owned repair.

**Phase 3 — expand only on evidence.** Move further streams independently when the pilot has
met the agreed observation window and economic case. Keep a stream on its existing transport
when it gains nothing from moving. Sunset old infrastructure only after retained replay history,
consumer dependencies, and recovery obligations have been resolved.

Transport selection and the small pilot are intended **two-way doors**. Retention history locked
to provider features, long commercial commitments, proprietary event semantics, and deleting
the last recoverable old history are **expensive or one-way doors**. Treat them as separate
approval points with export and recovery evidence. Portability of an envelope alone does not
make accumulated data inexpensive to move.

Revisit at the end of evaluation, quarterly during adoption, and when any of these proposed
triggers occurs:

- Observed peak exceeds two-thirds of the measured stable capacity ceiling, or the demand
  forecast reaches that ceiling inside the measured migration lead time.
- A recurrence shows the common recovery procedure cannot meet the agreed recovery objective.
- Current transport work exceeds the operator/team time allowance established in the baseline.
- A managed candidate demonstrates compliant residency and recovery at a better accepted total
  cost, or a price/limit change removes that advantage.
- A product team demonstrates a necessary semantic requirement that current transports cannot
  meet. Evaluate the narrowest affected workflow before changing the platform standard.
- Leadership funds operational coverage that makes a self-operated option supportable, and
  evidence shows it meets a requirement the other options cannot economically satisfy.

## Design packet

- **Decisions:** standardize contracts and recovery around existing team-owned transports first;
  evaluate managed transport as the conditional next step; do not initiate a shared self-operated
  platform, purchase, or migration. Keep business ownership and independent deployments with
  the six teams. Return any implementation proposal through the caller to
  `sde-agents:sde-fullstack` after the evaluation decision.
- **Assumptions:** **[unverified]** two teams can contribute the proposed evaluation time; existing
  transports can support a useful initial standardization; duplicates can be handled safely for
  the selected workflow; the organization can name incident, security/data, and commercial owners.
- **Weakest point:** there is no measured current capacity or recovery baseline. The chosen
  direction fails if common contracts cannot materially improve recovery, or if current transport
  cannot satisfy today's agreed workload within the staffing allowance.
- **Accepted trade-offs:** retain distributed queue operations and some implementation variety to
  avoid premature shared infrastructure ownership. Spend bounded evaluation and contract-adoption
  effort now, accepting that a later transport move may still be necessary.
- **Falsifying evidence:** a representative trial shows standardization cannot meet recovery
  objectives; the current system lacks near-term capacity headroom; or a managed option proves a
  compliant, supportable, lower-total-cost alternative with acceptable migration and exit costs.
  Conversely, vendor residency or staffing failures disqualify managed adoption despite throughput.
- **Revisit triggers:** evaluation completion, quarterly review, headroom/migration-lead-time
  crossing, recovery failure, operator budget overrun, changed vendor terms, or a demonstrated
  new business invariant.
- **Evidence disposition:** retain unresolved capacity, cost, semantics, residency, and staffing
  questions in this decision record. The caller should assign the evaluation to the platform
  owner and two team delegates; no external artifact or implementation was changed in this consult.

Learning: none — no reusable signal.
