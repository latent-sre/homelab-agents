# Event platform direction: standardize now, earn a transport change

Decision record · 2026-09-08 · Proposed for leadership acceptance

**[unverified] Recommendation:** Keep the team-owned outboxes and queues as the present transport.
Make a common event contract, replay procedure, and operational ownership model the platform
standard. Fund a bounded comparison of that improved baseline with managed transport. Prefer a
managed service for a future transport change only if measured requirements, regional controls,
operator effort, economics, and an exit rehearsal justify it. Do not select a vendor, buy a service,
start a migration, or commit to running a new broker fleet through this decision.

This is a five-year direction with evidence gates, not a five-year technology purchase.

## Problem and decision boundaries

**[sourced]** Six product teams operate separate PostgreSQL outboxes and queues. Inconsistent
interfaces and replay contributed to six separate reconciliations during a cross-team incident.
There is no measured throughput ceiling or complete cost baseline, and no demonstrated need for
synchronous global ordering. Independent service deployment must continue.
Source: `task.md:12–16`.

**[unverified] Interpretation:** The demonstrated problem is cross-team recovery and incompatible
interfaces. A broker replacement might leave both intact. Throughput growth is a planning risk,
not evidence that the current transport has failed. Standardization should first make recovery
repeatable and reveal whether transport is actually the limiting factor.

**[sourced] Constraints:** Two operators cannot staff a new round-the-clock team. Current traffic
is 20,000 events/second; planning must include uncertain tenfold growth. Customer payloads must
remain in the approved region. Event sizes, retention, vendor prices, SLAs, residency details,
limits, replication, replay, and delivery guarantees are unknown. Only a bounded evaluation is
funded; procurement and migration are outside this consult.
Sources: `task.md:7–10`, `task.md:18–26`.

**[unverified] Proposed success criteria:** All six teams can publish and evolve compatible event
contracts independently; an affected cohort can be traced and reconciled through one shared
procedure; ownership remains clear when transport or dependencies fail. The selected transport
must meet workload-specific lag and recovery objectives within the existing staffing constraint.
Agree numerical objectives before scoring products; inventing an availability or latency target
now would choose a solution against an imaginary requirement.

Non-goals are synchronous global ordering, rewriting domain services, a universal event-query
platform, and declaring cross-service exactly-once business effects.

## Alternatives and accepted trade-offs

The capability and cost expectations below are **[unverified] design judgments**, not vendor or
current-system measurements.

| Durable option | Ownership and likely cost drivers | Judgment and trade-off |
| --- | --- | --- |
| Keep everything unchanged | Teams retain their queues and recovery procedures; operators coordinate incidents. Cost includes database and queue resources, six implementations, incident work, and reconciliation. | Reject as the direction: it does not deliberately address the supplied recovery problem. It remains the fallback if the first standardization trial adds more work than it removes. |
| Keep and standardize the current system | Teams own their outboxes, workers, schema compatibility, and recovery actions. Operators own the small shared contract and cross-team recovery procedure. Resource cost scales with event bytes, delivery fan-out, retention, retries, and each team's database contention; engineering duplication may remain. | Choose now. We accept multiple transports and residual duplication to gain a useful recovery improvement without committing two operators to a new shared service. Its headroom and operational savings must be measured. |
| Adopt and self-operate an open-source platform | Operators would own capacity, upgrades, replication, storage, patching, disaster recovery, and broker incidents. Teams would still own event meaning and consumer correctness. Compare infrastructure plus recurring labor and failure drills; software licensing cost alone is inadequate. | Do not pursue as the default. A shared broker could introduce a new fleet-wide failure domain and an unsupported response obligation. Reconsider only with evidence that it meets requirements within existing staffed coverage, or an explicitly funded operating model. Product capabilities remain unknown. |
| Buy managed transport | A vendor would own only the operations explicitly covered by a validated contract. Operators retain tenancy, quotas, regional configuration, credentials, monitoring, escalation, costs, and exit capability. Teams retain outboxes or another proven capture path, schemas, idempotency, and business recovery. | Preferred challenger for the evaluation. We accept possible premium pricing and vendor coupling if measured operating effort and requirements justify them. No vendor SLA or managed label proves application recovery, regional compliance, or affordable replay. |

**[unverified] Build boundary:** Build only the missing, small contract and recovery aids that the
trial demonstrates are necessary. Do not build a broker, a routing control plane, or a generic
transport abstraction. Adopt an existing compatible tool only when its ownership and maintenance
fit the same evaluation. A common envelope and documented export format are useful exit points;
they do not promise that transports have interchangeable semantics.

## Destination and ownership

**[unverified] Proposed destination:** Teams continue to own their databases and authoritative
business state. Events carry changes between independently deployed services; replay rebuilds or
repairs explicitly named consumer state. A transport is not silently promoted to the permanent
business system of record. Any consumer that needs history longer than the agreed retention must
have a defined snapshot or authoritative resynchronization path before retention is accepted.

The logical flow is producer transaction → team-owned capture/outbox → approved regional
transport → team-owned consumers. The present queues satisfy the transport slot provisionally.
There is no requirement to move all teams onto one physical cluster or one vendor account.

**[unverified] Proposed contract:** Use stable event IDs, event type and version, producer owner,
entity or partition key where needed, occurrence time, and correlation identifiers. Specify
payload classification and compatibility expectations. Require consumers to handle duplicates;
do not assume the current queues provide at-least-once delivery until observed. Document each
flow's actual loss, duplication, and ordering behavior. Introduce per-entity ordering only for a
demonstrated business invariant, with an explicit key and recovery rule.

**[unverified] Deployment rule:** Producers make compatible changes while consumers deploy at
their own pace. Breaking changes use an explicit version, a transition window, and observed
consumer readiness before retirement. Tests against published contracts and replay samples belong
to each team. Avoid a central release approval queue or simultaneous six-team deployment.

**[unverified] Proposed responsibility split:**

| Responsibility | Accountable owner |
| --- | --- |
| Source transaction, outbox retention, publisher behavior, payload classification and schema | Producing product team |
| Consumer effects, idempotency, checkpoints, backlog recovery, and correctness reconciliation | Consuming product team |
| Common contract, compatibility policy, recovery procedure, shared operational views, evaluation coordination | Two platform operators, within a written time allocation |
| Infrastructure and regional controls for today's team queues | Each current owning team; operators coordinate evidence and shared standards |
| A future shared transport, vendor escalation, quotas, cost allocation and tested export | Platform operators, only after a staffing and ownership gate |
| Region approval and retention policy | Named organizational data/security owner; leadership must assign this owner before evaluation uses customer data |
| Budget, coverage gaps, procurement and migration decisions | Leadership |
| Cross-team incident coordination and each service's recovery execution | Named incident coordinator and affected team responders; confirm existing response coverage rather than assume it exists |

**[unverified] Operating budget:** Propose a four-week evaluation capped at eight operator-days
total and two engineer-days per product team. Leadership and team leads must accept this envelope
before scheduling it. Track actual labor. If the evaluation cannot answer the decision within the
cap, return an evidence gap or a narrower recommendation; do not quietly establish a permanent
third operational responsibility.

## Shared fate and recovery

All mitigations below are **[unverified] proposed controls**; none has been exercised in this
fixture.

| Failure or coupling | Detection and proposed containment | Owner |
| --- | --- | --- |
| Broker or regional dependency outage | Measure publish failures, oldest unpublished outbox age, consumer lag, and remaining database/storage headroom. Define bounded retry, backpressure and business degradation before outbox growth threatens production databases. A proposed shared broker must show tenant isolation. | Operators coordinate transport; teams own source databases and service degradation. |
| A shared credential, account, quota or configuration fails | Separate credentials and minimum access by team; inventory shared accounts and quotas. Alert on authentication failures, quota exhaustion and configuration changes. Test revocation and restore in the evaluation. | Operators and each service owner. |
| Poison events or replay cause duplicate business effects | Quarantine with an owner, bound retry, record progress, and reconcile by event ID and business outcome. Rate-limit replay independently of live traffic. Rehearse stopping and restarting it. Never discard failures solely to make lag green. | Consuming team. |
| Schema change breaks a lagging consumer | Contract checks plus runtime parsing-failure signals. Keep compatible versions until consumer readiness is observed; preserve the earlier reader or producer version for rollback. | Producer and consumer teams. |
| Retention expires before recovery completes | Compare oldest recoverable event with measured recovery duration and required recovery horizon. Alert before that margin is consumed; define source resynchronization when history is insufficient. | Product data owner and consuming team. |
| Shared storage, keys, backup, DNS or identity creates correlated loss | Map these dependencies for every candidate. Exercise the highest-risk restoration path, including key availability. Same-region replicas are not independent-region recovery. Region-wide outage handling must respect the supplied residency rule. | Operators, with data/security owner approving permitted locations. |
| Payload or customer-derived metadata leaves the region | Require evidence covering primary storage, replicas, backups, dead-letter data, diagnostics, traces, exports and support handling. An unknown or conflicting location fails the candidate gate. | Data/security owner, operators collecting evidence. |

**[unverified] Response policy:** Page the existing accountable responder for an actionable threat
to the agreed business objective, not every retry. Shared views should show publish and consume
lag, unreconciled event counts, headroom, recovery horizon, and cost by team. If existing coverage
cannot meet the accepted objective, leadership must change the objective or fund coverage before
approving a new shared transport. The two operators are not an implied 24/7 team.

## Bounded evidence plan and independently useful phases

**[unverified] Phase 1 — first useful step, within the evaluation:** Select one event chain crossing
two teams, including a consumer with a meaningful business effect. Record its current recovery
procedure, time, manual interventions, reconciliation mismatches, and operator effort. Draft the
minimum common contract and a single recovery runbook for that chain. Rehearse the procedure
with representative synthetic data in an isolated environment. Exercise duplicate delivery,
consumer interruption, incompatible data, and a stopped/restarted replay. Success requires zero
unexplained lost or duplicate business effects in the tested cohort and less manual reconciliation
than the baseline, without coordinated application releases.

This phase leaves a usable recovery procedure and workload inventory even if no transport change
is ever approved. Changes to production services remain a separately authorized implementation
step; drafting and evaluating the procedure do not start a platform migration.

**[unverified] Phase 2 — comparison within the same time cap:** All six teams provide event-size
distributions, peak and burst rates, fan-out, backlog patterns, retention and recovery needs,
regional dependencies, and current resource and labor costs. Select representative small/high-rate,
large-payload, and replay-heavy flows from that inventory. Include skewed keys and an outage
backlog. Freeze the requirements and comparable scenarios before obtaining candidate results.

Evaluate the standardized current system first. Compare a small shortlist of managed candidates
against the same scenarios; use isolated synthetic fixtures and no customer data or purchase
commitment. Obtain written vendor evidence for every material semantic and regional claim.
If vendor access or a load run requires procurement or exceeds the evaluation envelope, mark that
evidence unavailable and bring the exact next authorization to leadership.

**[unverified] Sizing and economics:** The growth scenario is 200,000 events/second, derived from
the supplied 20,000 × 10; it is not a measured forecast. Stored logical bytes scale approximately
as rate × mean event bytes × retention seconds; actual storage also depends on replication,
indexes and overhead. Delivery work additionally depends on consumer fan-out and replay. Compare
current, intermediate and tenfold rates using measured event distributions, equal retention,
failure recovery and sustained peak windows. Report tested ceilings separately from extrapolation.

Compare total annual cost as infrastructure or vendor charges + support + engineering and
operator labor + retention/replay/export charges + migration and exit effort. Show uncertainty
ranges and sensitivity to event size, fan-out and recovery frequency. No dollar ranking is justified
until those inputs and vendor terms exist.

**[unverified] Gate to a later migration proposal:** A challenger must pass approved regional
controls; demonstrate the agreed loss, duplication, ordering, lag and recovery behavior; survive
the selected failure scenarios; fit agreed operator capacity; provide priced limits and growth
scenarios; and export/replay a representative cohort into an independent recovery target. It must
also improve a measured shortcoming of the standardized baseline enough to justify transition
cost. Passing permits leadership to consider a migration proposal, not automatic procurement.

**[unverified] Subsequent evolution:** After explicit approval, extend the common contracts and
recovery practice to the remaining teams in small independent increments. Retain present transport
where it meets requirements. If the gate supports managed transport, propose one team-owned
event flow as a migration pilot with explicit exit criteria. Over years two through five, review
the evidence annually and on the triggers below; choose further consolidation by measured need,
not by a calendar promise or desire for one platform diagram.

## Reversal and decision triggers

**[unverified] Two-way doors:** Draft standards, trial tooling, isolated evaluations and compatible
contract additions can be withdrawn or revised. A failed standardization trial returns to the
documented existing procedure, preserving its evidence. Existing event versions remain supported
during any later contract transition.

**[unverified] Expensive doors:** A long vendor commitment, proprietary retained history,
consumer coupling to transport-specific semantics, deletion of old history, and a fleet-wide
cutover can make reversal costly or irreversible. Delay those decisions until measured need and
exit evidence exist. Expired or deleted history cannot be restored by reverting configuration.

**[unverified] Future pilot rollback requirement:** Keep the authoritative source and recoverable
outbox/history until reconciliation and the rollback window complete. Start with a shadow consumer
whose business effects are disabled. For cutover, designate one authoritative delivery path for
business effects and record event IDs/checkpoints; any overlap requires demonstrated idempotency.
Rollback pauses the new path, fences its effects, reconciles the cohort, and resumes the earlier
path from proven checkpoints. Do not call rollback available if old retention has expired or the
source no longer captures events. Exact transport-specific sequencing belongs in the later pilot
design before implementation.

**[unverified] Evidence that changes this recommendation:**

- If standardization fails to reduce recovery effort or cannot preserve independent deployments,
  revise the contract and ownership design before investing further. Transport alone has not been
  shown to solve that failure.
- If the current system misses an agreed objective at observed workload or measured headroom
  will be consumed within the documented procurement-and-migration lead time, advance the
  transport decision. Do not wait for tenfold growth to arrive.
- If managed candidates cannot prove regional controls, exit, required semantics or affordable
  operating limits, retain the current transport and assess the specific unmet requirement.
- If a managed candidate meets those gates and produces a material measured recovery, capacity,
  or labor advantage at an accepted total cost, propose procurement and a bounded migration pilot.
- If self-operated adoption demonstrably meets the same requirements within accepted staffing
  and coverage, reconsider it. A new funded operating team or support arrangement also reopens
  that option; neither is presumed today.
- A proved global-ordering business requirement, changed residency policy, major retention
  change, vendor terms change, or repeated cross-team recovery incident triggers an ADR review.

## Decisions needed and implementation handoff

**[unverified] Before evaluation execution:** Leadership names the decision owner, confirms the
time cap, and assigns data/security and incident-response owners. Product teams agree flow-level
lag, recovery-time, tolerated-loss and retention objectives, and disclose current response coverage.
Operators produce the comparison and evidence gaps. Unanswered vendor questions remain explicit
gate failures rather than defaults taken from a product category.

Return this decision to the caller for acceptance. Any subsequent implementation belongs with
`sde-agents:sde-fullstack` under a separately authorized work order specifying the selected flow,
contract, owner, recovery assertions and rollback criteria. No implementation is performed here.

## Design packet

- **Decisions:** Standardize event contracts and recovery around the current transport now;
  evaluate managed transport as the preferred challenger; defer self-operated infrastructure,
  procurement and migration until evidence and operating authority support them.
- **Assumptions:** **[unverified]** A minimum shared contract can reduce reconciliation without
  forcing synchronized releases; the teams can provide a bounded evaluation contribution; current
  transport can remain in service during that evaluation. No throughput or vendor guarantee is
  assumed.
- **Weakest point:** **[unverified]** Neither the baseline recovery cost nor the current system's
  capacity and staffing burden is measured. The first two-team recovery trial and six-team workload
  inventory must test whether the proposed first step addresses the costly failure.
- **Accepted trade-offs:** **[unverified]** Preserve transport diversity and some duplication to
  avoid premature shared operational responsibility. Accept managed-service dependency only if
  validated economics, residency, recovery and exit outweigh it.
- **Falsifying evidence and revisit triggers:** **[unverified]** No measurable recovery improvement,
  a deployment-independence regression, insufficient measured headroom, failed vendor gates, or
  changed operating capacity changes the direction as specified above. Review annually and on
  those events.
- **Evidence limitation and disposition:** **[sourced]** This is a synthetic decision based only on
  `task.md:3–5`; no live organization, vendor, benchmark or operational control was verified.
  Outstanding measurements and vendor claims are assigned above to evaluation owners. They are
  retained here as decision gaps, not promoted to reusable platform facts.
