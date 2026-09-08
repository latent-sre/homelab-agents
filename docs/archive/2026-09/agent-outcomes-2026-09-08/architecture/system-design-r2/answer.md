# Decision: separate order compatibility from shipment execution

**Status: proposed for implementation.** [sourced] The platform remains the existing managed
bus, PostgreSQL stores, and transactional outbox. Independent deployments, duplicate delivery,
reordering, 30-day replay, and at least eight weeks of v1 analytics support are requirements
(`task.md:7–14`). [sourced] The legacy worker cannot safely handle splits, and its `order_id`
carrier key has no durable effect ledger (`task.md:16–29`).

**Decision.** [unverified — proposed contract] Keep one truthful v1 order event for analytics.
Add a v2 fulfillment contract and replace shipment execution with a worker that understands
both versions and maintains a durable effect ledger. Remove the original worker's access before
admitting split orders. Deploy these changes separately; enable behavior only after compatibility
gates pass. The supported rollback worker is the compatible worker with split admission disabled.

**Evidence boundary.** [verified] I read the supplied synthetic task and frozen role. No running
system, source implementation, bus capability, carrier implementation, or test was inspected.
Below, [sourced] means a supplied requirement; [unverified] identifies a design decision,
assumption, estimate, or behavior that the builder must establish. No runtime guarantee has
been demonstrated.

## Requirements and limits

[unverified — required invariants]

1. One accepted order has one immutable fulfillment plan. Each group has one stable identity
   and at most one authorized shipment intent. Replays cannot create another intent.
2. The order, plan, and required outbox records commit atomically. Publication order does not
   determine the plan or which consumer may act.
3. Every v2 order produces one v1 order-level analytics event, never one per fulfillment group.
   v1 currency, total, and address retain their existing meanings.
4. The original worker never consumes a split order, including through backlog or replay.
5. Every external attempt has a committed intent first. An ambiguous outcome remains ambiguous
   until evidence resolves it; it is never converted into permission to ship again.
6. Every accepted order can be reconciled against its expected groups, including orders whose
   events never reach the worker. Partial shipment is visible as partial shipment.

[sourced] The carrier guarantees key deduplication and lookup for seven days, and acceptance
can precede a worker crash (`task.md:23–29`). [unverified — feasibility limit] Those facts do
not provide a way to guarantee both eventual shipment and no duplicate after an unresolved
attempt ages out. The safe decision is to stop automatic creation for that group and escalate.
An order may remain unshipped or of unknown shipment status; the system must detect and own it.
If the product requires automatic recovery from arbitrarily long ambiguity, it needs a stronger
carrier contract. That is a requirement gap, not something a local transaction can solve.

[unverified — scope] This migration does not change platforms, support plan amendments, or make
several carrier shipments atomic. A changed destination, new group, or replacement shipment
after acceptance needs a separate business operation; it is not an event replay.

## Alternatives and accepted trade-offs

| Option | Assessment |
| --- | --- |
| [unverified] Keep v1 and leave split admission off | Safe interim state; delivers no split capability and leaves the existing crash ambiguity unresolved. |
| [unverified] Add groups to v1 or send v1 once per group | Reject: a legacy worker can ship incorrectly; per-group events change order-level analytics meaning. |
| [unverified] Dual-publish and let the original and replacement workers both act | Reject: event deduplication does not arbitrate two carrier callers, and different carrier keys can create duplicate shipments. |
| [unverified] Two contracts, one compatible execution authority, durable ledger | Choose: retains analytics compatibility and gives fulfillment durable ownership. Accept a bounded fulfillment dispatch pause, historical reconciliation, retained ledger storage, and manual cases after ambiguous expiry. |

## Contract and ownership

**Orders owns the immutable plan and publication obligation.** [unverified — proposed schema]
Store an order-level `fulfillment_protocol` and the ordered, immutable group list with each new
v2 order. Use a stable `plan_id`, `plan_revision=1`, and `fulfillment_id` values generated once
and persisted. IDs must not depend on event arrival order or the current worker implementation.
Each group contains line-item identities, quantities, and destination. Validate that the groups
cover every fulfillable order item exactly once at its ordered quantity. Reject invalid plans
before committing the order.

**Events.** [unverified — proposed wire contract]

| Contract | Payload and execution rule |
| --- | --- |
| Existing v1 `OrderCreated` | Preserve `event_id`, `order_id`, `currency`, `total_minor`, and `shipping_address`. An old producer's event has no new execution marker and represents one legacy shipment. |
| v1 emitted by a v2-capable producer | Exactly the same v1 payload meanings, plus transport envelope `fulfillment_protocol=v2`. Analytics continues to consume it. The compatible fulfillment worker records or counts it as analytics-only and performs no carrier action. |
| v2 `OrderCreated` | Distinct versioned routing/type, its own stable `event_id`, `order_id`, `plan_id`, revision, order-level currency/total, and the complete stable group list. The worker materializes all expected groups from this event in one database transaction. |

[unverified — publication contract] For a v2 order, Orders commits the order, plan, one v1
outbox row, and one v2 outbox row in the same transaction. Each row has a distinct event ID,
retained across relay retries. `order_id` correlates the two views; `fulfillment_id`, not
`event_id`, identifies a shipment effect. The relay publishes committed bytes without dropping
the execution marker or interpreting group contents. v1-only API instances continue their
existing single-row transactions for singleton orders. A v2 plan may not be added later to an
order originally committed under the legacy protocol.

[unverified — compatibility gate] The envelope is a proposed addition, not a proven feature of
this bus or its consumers. Platform must prove that subscriptions and the relay preserve it,
that analytics accepts it without changing its payload interpretation, and that unknown marker
values are quarantined by fulfillment. An absent marker is valid only for the unchanged legacy
producer path. The v2 producer must not be allowed to publish its v1 projection without the
marker; the business gate remains off until publication and replay prove that invariant.

[unverified — analytics semantic gate] Preserve the original order-level `shipping_address`;
do not choose the first group's address, invent a synthetic address, or duplicate the order.
The task does not establish whether its existing meaning can represent an order with several
different destinations. Orders and the analytics owners must confirm that meaning before
admitting such orders. If it denotes the sole actual destination, different-destination splits
cannot satisfy the unchanged v1 contract: reject that admission shape until a truthful contract
is agreed. Same-destination splits may proceed if their v1 meaning is unchanged. This is a
specific unresolved product decision, not authorization to redefine the field.

**Fulfillment owns shipment identity and state.** [unverified — proposed database contract]

- `order_plan`: unique `order_id`, protocol, plan identity/hash, expected group count, source
  provenance, and aggregate progress. Conflicting immutable plans are quarantined.
- `shipment_effect`: unique `(order_id, fulfillment_id)` and unique carrier key, immutable
  request/hash, state, first possible attempt time, retry cutoff, lease/attempt token, carrier
  shipment ID, reconciliation evidence, and last error.
- `event_inbox`: unique `(event_type, event_id)`, payload hash, and ingestion outcome. A reused
  event ID with changed bytes is a conflict, not a harmless duplicate.
- `legacy_cutover`: durable membership and reconciliation status for orders that could have
  been acted on by the original worker.

[unverified — retention decision] Retain shipment-effect identities and terminal/unknown
outcome tombstones without a time-based deletion in this migration. Keep them through all
allowed replay, recovery, and business recovery periods; do not use the carrier's seven days
or bus's 30 days as a ledger TTL. Separate delivery-address retention from minimal effect
identity retention. Any later purge needs an explicit replay rejection boundary and owner.

**Key continuity.** [unverified — proposed invariant] Legacy singleton orders use a stable
synthetic group identity derived from `order_id` by one specified, versioned encoding, while
their actual carrier key remains exactly the existing `order_id`. Reprocessing or backfilling
must not replace that key. New groups use a persisted, collision-free namespaced key based on
their stable `fulfillment_id`, validated against carrier key constraints before activation.
Protocol is immutable, so an order cannot be shipped first as a legacy singleton and later as
new groups. Unknown key format constraints are a carrier-integration gate.

## Execution and carrier ambiguity

[unverified — worker algorithm]

1. Validate the event and protocol. In one worker-database transaction, deduplicate the inbox,
   check the immutable plan, and create every group's effect row. Commit before acknowledging
   the bus. Analytics-only v1 events cause no effect. A malformed or conflicting plan goes to a
   visible quarantine record, with the order ID and reason.
2. A dispatcher claims a pending effect with a database lease and token. Before any network
   call, commit `attempting`, the exact carrier request/hash and key, and
   `first_possible_attempt_at`. A crash before the actual call is conservatively ambiguous.
   Never hold a PostgreSQL transaction open across a carrier request.
3. Call the carrier with that key and unchanged request. Commit the returned shipment ID and
   `accepted` outcome. A timeout, lost reply, uncertain error, or expired lease after an attempt
   transitions to `unknown`; it does not reset the row to a fresh pending effect.
4. Resolve an unknown outcome by carrier lookup with the same key while the lookup window is
   valid. A found shipment becomes `accepted`. A missing or transient lookup result is not
   proof that no delayed request can succeed. Within the safe retry window only, another create
   may use that same key and request because carrier deduplication covers it.
5. Use a conservative automatic create-retry cutoff of six days from the first possible attempt,
   reserving the remaining day for reconciliation. Persist the cutoff; retries never extend it.
   After cutoff, stop create calls and continue lookup only within the supported window. After
   seven days, unresolved effects become `manual_hold`. No key rotation or automatic resend.

[unverified — operating assumption] The six-day cutoff reserves a one-day safety allowance; it
is not a demonstrated bound. Fulfillment must establish carrier retention start semantics,
maximum request/retry lifetime, and a bound on delayed outbound work. Enforce deadlines on the
actual dispatch path, disable uncontrolled SDK retries, check expiration before each dispatch,
and fence terminated worker instances from carrier access. A local lease is not a carrier
fence. If a suspended process or delayed request can issue a create arbitrarily late, the
supplied seven-day guarantee cannot prove duplicate freedom. Do not claim that stronger result
without an enforceable bound or stronger carrier support.

[unverified — recovery policy] An authorized Fulfillment operator may resolve a manual hold
using independent carrier or business evidence that identifies the shipment, or establishes
non-acceptance and excludes outstanding requests. Record evidence and actor. An inconclusive
lookup after seven days, customer uncertainty, or lack of a local success row is insufficient.
Never mark such a group successfully shipped or safely retryable merely to close an alert.

[unverified — partial orders] Groups execute independently. One accepted group and one failed
group means a partially fulfilled order; retry only the eligible failed group. Do not replay
the entire order as compensation. `accepted` means carrier acceptance, not parcel handoff or
delivery. Any later shipment milestone needs its own evidence source. Until the product names
that milestone, alert separately for overdue acceptance and accepted shipments with no
subsequent operational confirmation.

## Rollout: independent releases with explicit activation gates

[unverified — sequence and exit criteria]

1. **Orders and Platform prepare additively; split admission stays off.** Add nullable/new
   schema fields without changing old API writes. Add versioned routing, envelope transport,
   backlog metrics, and an Orders-owned reconciliation inventory. Keep old publication working.
   Deploy the relay changes before producing records it cannot preserve. Reject a relay
   rollback to incompatible bytes once those records exist.
2. **Fulfillment prepares the compatible worker with outbound dispatch disabled.** Exercise
   ingestion against isolated fixtures, not a production effect ledger populated with pretend
   successes. It supports legacy v1, marked analytics-only v1, and v2. Verify all carrier-facing
   paths use the ledger before switching authority.
3. **Platform and Fulfillment fence the original worker.** Pause fulfillment consumption and
   carrier dispatch, stop all old instances and retry jobs, drain or account for in-flight
   requests, and revoke the old deployment's subscription and carrier credentials. A rolling
   period in which an unmodified old caller and the ledger worker can both act is forbidden.
   APIs may keep accepting singleton orders into the outbox during this fulfillment pause.
4. **Reconcile historical ambiguity before enabling the replacement dispatcher.** After the
   old callers are fenced, Orders takes a consistent snapshot of all committed order IDs and
   exports its membership to `legacy_cutover`. Every member could have a legacy effect. Import
   existing trustworthy shipment evidence if available; use `order_id` carrier lookup only
   within its valid window. Quarantine unresolved historical orders, especially older ones.
   Orders committed after this snapshot could not have been acted on by the fenced worker and
   may enter the new ledger normally. A transaction committing after the snapshot is likewise
   safe because old dispatch was already stopped. Inventory completeness, including archived
   replayable orders, must be proven; an unexplained old ID is held, never assumed new.
5. **Run the compatible worker on legacy traffic.** Resume one bounded set of singleton orders,
   verify acceptance and crash recovery, then expand dispatch. Historical holds remain visible
   and owned; they do not authorize blanket resend. Platform retains the old-worker access
   prohibition for queue replay and disaster recovery configurations too.
6. **Deploy v2-capable APIs with split admission off.** First emit a small cohort of singleton
   v2 plans plus their marked v1 analytics projections. Old API instances continue legacy v1.
   Verify both event arrival orders, replay, one actual shipment per order, unchanged analytics
   totals, and expected-group reconciliation. Stop expansion if any v1 projection reaches an
   execution path as legacy.
7. **Enable split admission gradually.** Orders owns the business switch and revalidates it at
   the committing admission path. Gate on the truthful v1 projection, immutable group validation,
   fenced legacy callers, bounded carrier retries, no unresolved canary duplicates, and working
   detection of missing groups. Begin with a bounded cohort and fulfillment capacity limit.
   Operators may disable admission without disabling completion of already committed plans.
8. **Keep compatibility through eight weeks and the replay tail.** Retire v1 publication only
   after both analytics consumers migrate and their owners confirm backlog/replay handling.
   Retain legacy decoding and its identity mappings for at least 30 days after the last legacy
   publication, and longer if unpublished outbox rows, dead letters, archives, or recovery
   workflows can still supply it. Calendar age alone is not a retirement gate.

[unverified — migration limitation] The fixture does not promise complete historical shipment
records. This design cannot reconstruct an accepted shipment outside carrier retention from
missing data. Those orders become explicit exceptions with Fulfillment ownership. If Orders
cannot provide a complete cutoff inventory, keep dispatch paused for affected unknown orders;
do not silently classify missing ledger entries as never attempted.

## Operations, detection, and ownership

[unverified — reconciliation interface] Orders supplies a cursor-based inventory of committed
orders and their required fulfillment protocol/plan, expected group IDs, acceptance time, and
current business status. It includes legacy singleton expectations and is derived from Orders'
database, not solely from published events or worker rows. Fulfillment polls it with overlapping
watermarks and periodic full coverage checks. A missing worker plan triggers an alert and an
idempotent re-emission of the same immutable event/plan through the Orders outbox. Reconciliation
never bypasses the shipment ledger to call the carrier.

| Failure | Detection and response | Accountable team |
| --- | --- | --- |
| [unverified] Order committed but event not published/consumed | Compare Orders inventory with worker plans; alert on oldest unfulfilled commitment, outbox lag and stalled reconciliation watermark. Repair relay or re-emit immutable records. | Orders for commitments; Platform for transport |
| [unverified] Duplicate/reordered v1 and v2 deliveries | Inbox deduplication plus immutable protocol/effect identity; monitor conflicting hashes. Do not rely on message ordering. | Fulfillment |
| [unverified] Carrier accepts, local commit is lost | Unknown-attempt age and time remaining before retry/lookup cutoffs; look up the same key, then commit evidence. | Fulfillment |
| [unverified] Some groups never ship | Expected-versus-accepted group counts, per-group age and partial-order age, including groups missing locally. Assign one order-level case with group details. | Fulfillment |
| [unverified] Poison event or ledger conflict | Durable quarantine and oldest-item alert; acknowledge only after preserving the failure for recovery. Correct the source or explicitly resolve the conflict. | Orders for bad plans; Fulfillment for ingestion |
| [unverified] Carrier outage or ledger database outage | Carrier error/latency, unknown outcomes, database availability, lease backlog; stop new dispatch when durable intent cannot be committed. | Fulfillment |
| [unverified] Old deployment or unsafe replay reappears | Denied old credentials/subscription access, deployment policy check and an alert on attempted legacy access. Keep split admission disabled until fencing is restored. | Platform and Fulfillment |
| [unverified] Ledger restore loses recent accepted outcomes | Fence all dispatch first; reconcile the database-loss interval against Orders and carrier evidence. Quarantine gaps older than retention. Bus replay alone is not recovery proof. | Fulfillment |

[unverified — initial operational policy] Run reconciliation every five minutes and page if
its coverage is stale for 15 minutes. Page unknown carrier outcomes unresolved for 15 minutes;
escalate any unresolved case at five days, before the six-day retry cutoff. These are proposed
defaults, not existing SLOs. Orders and Fulfillment must set a shipment-acceptance deadline from
the actual service promise before activation; overdue order and group alerts use that deadline.
Analytics owners receive v1 count/amount parity reports, with no carrier operational authority.

[unverified — cost] No new service platform is required: the existing worker hosts dispatch and
reconciliation loops. Costs grow with orders, groups, retained effect rows, and carrier lookup
attempts. Shipment calls grow with groups rather than orders. No workload or price figures were
supplied, so capacity and cost are unmeasured. Fulfillment owns ledger storage, backups, recovery,
carrier limits, dashboards, and the manual exception queue. Platform owns transport capacity and
old-caller fencing. Orders owns plan validation, dual publication, admission, and inventory.

## Rollback and reversibility

[unverified — two-way doors] Turn off split admission; stop expansion; pause dispatch; revert
new API logic to the earlier singleton path while retaining additive schema and pending outbox
rows. Drain committed v2 orders using the last known-good compatible worker. Preserve envelope
handling, v2 subscriptions, the ledger, carrier keys, and reconciliation. If that worker is not
safe, hold dispatch until it is repaired; continued API acceptance needs backlog/capacity limits.

[unverified — one-way doors] A carrier-accepted shipment and a published split plan cannot be
undone by rolling back code. A legacy-only worker is not an acceptable rollback once v2 orders
exist or once its state-free dispatch could bypass the ledger. Never flatten outstanding groups
into a v1 singleton. Never restore an older worker database and replay events with carrier
dispatch enabled until its lost-effect interval is reconciled.

[sourced] Cancellation is best effort, and a parcel handed off to the carrier cannot be recalled
(`task.md:27–29`). [unverified — rollback handling] Stop unattempted groups only under the
applicable business cancellation decision; record them as intentionally withheld or cancelled,
not shipped. Reconcile unknown attempts before cancellation decisions. Request cancellation for
accepted groups if appropriate, record the actual result, and surface failed cancellation for
customer handling. Mixed accepted/cancelled/unknown groups remain a partial order, not a rolled
back transaction. Old analytics continues receiving truthful v1 events throughout this process.

## Builder verification and remaining decisions

[unverified — required executed evidence, not performed here] Before the corresponding rollout
gate opens, demonstrate:

- Duplicate and reordered v1/v2 delivery, including distinct event IDs describing the same
  fulfillment, creates one ledger intent and one carrier shipment per group; mutated payloads
  conflict instead of changing an accepted intent.
- Old and new API instances interleave singleton commits safely; split v1 projections never
  invoke shipment execution, and the original worker cannot reacquire queue or carrier access.
- Crashes before intent commit, after intent commit, after carrier acceptance, and after local
  success but before bus acknowledgement recover without changing the carrier key.
- A seven-day-expired ambiguous attempt and a 30-day replay cause no new carrier create;
  a proven never-attempted post-fence group can still ship. Historical missing records are held.
- Concurrent dispatchers, lease expiry, paused workers, SDK retries, and delayed responses obey
  the outbound deadline and fencing assumptions. If the bound cannot be established, report
  the duplicate-avoidance limitation and do not claim the gate passed.
- Deliberately suppress publication/consumption of an entire order and one group's progress;
  independent Orders reconciliation detects both. Partial success does not replay accepted groups.
- Turn off split admission and roll back APIs during partial fulfillment. The compatible worker
  finishes or explicitly holds committed plans, and analytics still counts one order with the
  original total and address meaning.
- Rehearse restoration of a worker database missing recent successes. Dispatch remains fenced
  until the lost interval is reconciled; expired uncertainty stays held.

**Decisions.** [unverified — proposed] Preserve the platform; dual-publish truthful order views;
use one compatible shipment execution authority; retain durable effects; fail closed on expired
ambiguity; roll back admission and code without discarding committed plans or shipment history.

**Assumptions and decisions needed.** [unverified] Platform must establish envelope preservation
and effective old-caller fencing. Orders and analytics must settle multi-destination v1 address
meaning. Fulfillment must establish carrier request/key constraints and bounded retry delivery.
Orders must establish inventory completeness; the teams must agree the shipping milestone and
deadline. These are activation gates with the named owners, not implied existing capabilities.

**Weakest point.** [unverified] Carrier ambiguity outlives the seven-day evidence window, especially
for historical orders and database-loss recovery. The design deliberately buys duplicate avoidance
by withholding uncertain shipments and funding manual resolution. A requirement for automatic
eventual completion of those cases would disprove the sufficiency of the current carrier contract.

**Implementation handoff through the caller.** Hand this document to `sde-agents:sde-fullstack`
for implementation in team-owned changes: Orders owns plan/schema/outbox/admission/inventory;
Platform owns relay transport, subscriptions and legacy fencing; Fulfillment owns the compatible
worker, ledger, carrier state machine, migration reconciliation and operations. Use the contracts,
ordered activation gates, and verification scenarios above as acceptance criteria. Return unresolved
semantic or carrier-contract decisions to the caller before enabling the affected behavior.
No implementation, deployment, tests, or external verification were performed for this design.
