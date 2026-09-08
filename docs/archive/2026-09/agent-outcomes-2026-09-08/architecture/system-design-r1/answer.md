# Order-event migration and shipment safety decision

Adopt one new fulfillment route on the existing bus, a worker that accepts both legacy single-order
work and v2 plans, and a durable shipment-effect ledger. Keep the existing v1 analytics route.
Enable split orders only after the legacy shipment worker has lost the ability to call the carrier.
This is a proposed design, not an implemented or tested system.

**Evidence and scope.** [sourced] The fixture establishes the existing bus, PostgreSQL and outbox,
independent deployments, duplicate/reordered delivery, 30-day replay, and continuing v1 analytics
consumers (task.md:7–14). It establishes incompatible split semantics and the admission flag
(task.md:16–21), and the seven-day carrier key/lookup window, uncertain crash outcome, and absence
of a legacy effect ledger (task.md:23–30). All new contracts and estimates below are
**[unverified — proposed]**. No source implementation, carrier behavior, or operational capacity
was inspected. The platform choice is fixed; this decision changes its contracts and migration.

**Safety limit.** [unverified — deduction from the supplied carrier contract] The system cannot
guarantee both automatic eventual shipment and zero duplicates for every crash history. After an
ambiguous carrier call ages beyond seven days, the available lookup can no longer establish whether
a shipment exists. Reusing the old key can create a second shipment; inventing a new key is worse.
The chosen policy preserves duplicate avoidance by quarantining unresolved outcomes and alerting
a human. It detects an order that may never ship without pretending that retrying will resolve it
safely. Product must accept that these orders can remain blocked pending external evidence.

**Options and decision.** [unverified — design comparison]

| Option | Benefit | Cost or reason rejected |
|---|---|---|
| Keep v1 and leave splits disabled | No migration risk or new operational burden | Does not deliver split fulfillment; retain as the pre-admission abort option |
| Put split data into v1, or let both workers consume every order | Small apparent event change | Legacy worker may create an order shipment alongside group shipments; cannot preserve its interpretation safely |
| Publish v1 analytics and v2 fulfillment with explicit routing and one shipment owner | Preserves analytics and allows independent releases | Adds one route, a compatibility adapter, ledger, and reconciliation work; chosen |
| Replace the platform or coordinate a simultaneous release | No benefit needed for this migration | Outside the settled platform decision; simultaneous deployment also leaves retained messages and rollback unresolved |

The smaller useful first phase is the compatible worker and ledger with splits still off. It
improves shipment recovery even if the remainder of the migration stops there.

**Orders and Platform: event and routing contract.** [unverified — proposed]

Use the existing v1 route for analytics and one separate fulfillment route for worker work. The
legacy worker currently receiving v1 must be drained and fenced before any split is admitted.
Putting v1 and v2 on different routes does not itself make a still-running v1 worker safe.

Expand the outbox with an immutable routing class and explicit payload schema version. Old API
inserts receive a database default of `legacy-single`; those API versions cannot admit split
orders. The upgraded API explicitly writes `analytics-only` for its v1 row and `fulfillment-plan`
for its v2 row. Relay behavior is:

| Outbox class | Existing analytics route | New fulfillment route |
|---|---|---|
| `legacy-single`, v1 | Original v1 payload | Envelope identifying a v1 single-order payload |
| `analytics-only`, v1 | Original v1 payload | No publication |
| `fulfillment-plan`, v2 | No publication | Versioned v2 fulfillment plan |

For upgraded API requests, commit the order, its immutable group plan, the v1 analytics row, and
the v2 fulfillment row in the same PostgreSQL transaction. A failed transaction emits neither.
Each row has its own persistent `event_id`; retries and relay redelivery preserve it. The two
versions are different events about the same order, not two shipments. Never use `event_id` as a
carrier key. Publication order is irrelevant. The relay marks a row delivered only after all its
required destinations acknowledge it; an incomplete fan-out retries and may duplicate successful
destinations. There is no claim of atomic bus delivery.

The relay validates the class/version combinations and fails visibly on unknown combinations.
Only the relay may publish the fulfillment route. Persist routing information with retained
envelopes and replay it unchanged. A raw analytics v1 message is never accepted as fulfillment
work: once splits exist, that payload cannot tell a safe single order from a split order.
Old retained messages lacking routing provenance require the migration inventory to establish
their single-order origin; they must not gain fulfillment eligibility from a guessed default.

V1 retains exactly its order-level meanings: original `order_id`, `currency`, `total_minor`, and
`shipping_address`, with one logical OrderCreated per order. Do not emit one v1 event per group,
replace its amount with a group amount, or choose a group's destination as a surrogate address.
Duplicate transport delivery remains possible as it is today. Orders must explicitly define and
persist the order-level `shipping_address` for split orders under the existing analytics meaning.
If split checkout has no valid value with that meaning, split admission remains off until Product
and analytics owners settle that contract; fabricating a representative address is not compatible.

V2 contains `event_id`, `order_id`, schema version, and a complete, immutable plan with stable
`fulfillment_id`, line-item identifiers and positive quantities, and destination per group.
Orders validates that the groups cover the accepted order items exactly once, including quantity
splits, before committing. IDs and grouping do not change on publish retry or API redeploy. Any
future regrouping or order amendment requires a separate protocol; a conflicting second
OrderCreated cannot mutate an already dispatched plan.

Old API orders retain their legacy-single representation. Upgrading the API does not re-create
their events as new v2 work. The compatible worker preserves the existing single-shipment
workflow for v1: v1 has no line items, so its adapter must not invent them. A v2 singleton uses the
same documented singleton identity mapping as a legacy order, for example an injective encoding
of `(legacy-single, order_id)`. Split group IDs occupy a disjoint namespace. A representation
conflict for the same order is quarantined before it can schedule additional shipments.

**Fulfillment: receipt, ledger, and carrier protocol.** [unverified — proposed]

The worker database owns these durable records:

- An inbox keyed by route and `event_id`, retaining payload digest and processing outcome. The
  same identity with different bytes is a contract error, not a harmless duplicate.
- An order plan keyed by `order_id`, retaining representation, expected fulfillment IDs,
  destinations and immutable plan digest. Event identity alone is insufficient: another event ID
  for the same order must not create another plan.
- An effect row per `fulfillment_id`, with unique carrier key, request digest, state, first possible
  dispatch time, last attempt, claim token/lease, carrier shipment ID, and resolution evidence.
  Preserve completed identity tombstones with the order history, beyond the 30-day replay window;
  routine inbox pruning must never erase effect deduplication. An administrative replay has no
  permission to delete or reset these records.

For legacy orders and v2 singletons, the carrier key remains the exact legacy `order_id` encoding.
For split groups, derive a stable namespaced key from `fulfillment_id`. Fulfillment must verify
the carrier's key length, character, and account scope before implementing that encoding; no
truncation that can collide is allowed. The request associated with a key is immutable.

In one worker transaction, validate the message, insert or compare the inbox and plan, and create
all missing effect rows. Acknowledge the bus only after this commits. Dispatch runs from these
rows, so an acknowledged event cannot disappear between receipt and scheduling. There is no
database transaction held across the carrier call.

Use states `PLANNED`, `ATTEMPTING`, `UNCERTAIN`, `ACCEPTED`, `DEFINITELY_REJECTED`, and
`QUARANTINED`. A bounded dispatcher claims one row and commits `ATTEMPTING`, its request digest,
and first possible dispatch time before calling the carrier. `ACCEPTED` stores the returned
shipment ID. A crash after acceptance leaves an ambiguous row that recovery looks up using the
same key. A positive lookup commits that result without creating another shipment. A timeout,
missing response, or expired lease does not mean the carrier rejected the shipment.

Only one current dispatcher owns a row; use database conditional updates and claim tokens to
prevent ordinary concurrent dispatch and stale local commits. A database lease cannot revoke an
external call already in flight. All attempts, including delayed ones, must use the same key and
request. Disable hidden SDK/proxy retries beyond the worker's attempt policy.

Within the carrier window, a retry after an ambiguous outcome is allowed only with the same key,
under the carrier's stated idempotency guarantee and a bounded dispatch/request lifetime. Measure
the window conservatively from the earliest locally authorized attempt, never the latest retry.
Propose a six-day automatic-recovery cutoff, leaving one day of margin; an expiring window is an
operational escalation, not permission to issue a final blind attempt. Fulfillment must establish
request timeouts and that a suspended old dispatcher cannot resume an expired call before enabling
automatic ambiguous-call retries. If that bound cannot be established, leave such retries
disabled and use lookup plus human resolution. A local lease alone is insufficient evidence.

At the cutoff or when original dispatch age is unknown, quarantine any unresolved outcome.
Beyond seven days, neither a missing lookup result nor the unchanged key proves that resubmission
is safe. Never reset the first-attempt timestamp, allocate a replacement group ID, or use a new
carrier key to clear this state. An operator can resolve it with authoritative carrier records
or confirmed shipment evidence; absent that evidence, it stays blocked. A documented definitive
rejection with no carrier effect may be retried under an explicitly classified error policy;
unknown errors remain uncertain.

Persist success per group. If two groups are accepted and a third fails, retry or investigate
only the third; never replay the whole order as a fresh unit. Cancellation is a separate recorded
operation with its own result. A cancellation request is not proof a shipment was cancelled.

**Migration sequence and release gates.** [unverified — proposed]

1. **Expand with splits off.** Orders adds the backward-compatible outbox fields and stable ID
   contract; Platform upgrades every relay to understand all routing classes and creates the
   fulfillment route and access controls. Keep new-class emission disabled until no old relay can
   misroute or silently drop it. Fan-out legacy-single messages into the new route while its
   shipment dispatcher is disabled. Capture the migration inventory before any source/outbox
   pruning. Stopping here leaves the old system serving single orders.
2. **Prepare durable ownership.** Fulfillment deploys the dual-format worker with intake and
   reconciliation enabled but carrier dispatch disabled. Build an order-by-order inventory of
   historical, queued, and in-flight legacy work. Existing shipment records, carrier evidence
   within seven days, and explicit unresolved entries seed the effect ledger. Do not classify an
   old order as unshipped merely because the new ledger is empty. If local legacy history cannot
   prove an outcome and carrier lookup has expired, seed `QUARANTINED` with the original key.
3. **Transfer carrier authority.** Stop legacy intake and new legacy dispatch; keep admission of
   single orders running and let their events queue. Drain and reconcile outstanding carrier
   requests, then terminate legacy workers and revoke their carrier access. Account for accepted
   in-flight calls before enabling the replacement. Use separately controlled credentials or an
   equivalent enforceable egress boundary so an old deployment cannot resume. If credentials are
   shared today, separating them is a gate. Reconcile inventory through the final stop boundary,
   seed results and unknowns, and then enable new dispatch. Replays of already shipped orders hit
   ledger outcomes; unresolved historical orders remain held. This requires a bounded fulfillment
   pause, not a simultaneous API/worker release.
4. **Prove single-order operation.** Let old API versions continue producing legacy-single work.
   Exercise duplicate delivery, backlog drain and carrier recovery with the new owner. The
   admission gate requires complete accounting of migration inventory, even if some rows remain
   explicitly quarantined, and no unidentified in-flight legacy caller. Set an agreed limit on
   the unresolved backlog before increasing traffic.
5. **Enable the upgraded producer, then splits.** Deploy upgraded API versions with dual outbox
   emission enabled for new orders and splits initially off. Old API versions may continue making
   single orders. Prove analytics parity and v2 singleton behavior, then canary split admission
   only on compatible API instances. An old instance must never receive a split request or silently
   downgrade one; enforce capability routing and reject unsupported admission. Expand based on
   reconciliation and effect-state metrics, not just successful HTTP requests.
6. **Retire compatibility deliberately.** Keep v1 analytics for at least eight weeks and until both
   consumers confirm migration. Remove legacy-single fulfillment support only after the last old
   producer, its undelivered outbox rows, and its 30-day retained replay horizon are gone, with
   historical replay policy and unresolved orders accounted for. The eight-week analytics period
   and 30-day replay period are independent clocks. Retiring a route or schema is a separate gate;
   ledger identity records remain.

**Detection, recovery, and operational ownership.** [unverified — proposed]

| Failure | Detection | Response and owner |
|---|---|---|
| Outbox fan-out partially succeeds or the bus is unavailable | Oldest unpublished row, errors by destination | Retry stable events; Platform owns recovery and checks destination completion |
| Event is lost from the expected workflow, poisoned, or never scheduled | Orders-to-worker reconciliation; quarantine age; oldest unaccepted plan | Orders owns missing source intent, Platform missing delivery, Fulfillment receipt/dispatch failures |
| Duplicate, reordered, or conflicting events | Inbox/plan identity comparison and conflict counter | Duplicates converge; conflicting plans stop before side effects; Orders and Fulfillment resolve |
| Carrier accepts and worker crashes | Aged `ATTEMPTING`/`UNCERTAIN`; lookup result | Fulfillment records the existing shipment or quarantines; never fabricates a safe retry |
| One split group stalls | Expected group count versus accepted groups, oldest pending group | Fulfillment investigates that group; Product/support handles customer impact |
| Old worker resumes or analytics traffic reaches fulfillment | Legacy credential use/denial; unexpected route or envelope | Disable split admission, fence the caller, investigate affected orders; Platform and Fulfillment |
| Database restore discards effect history | Restore checkpoint versus carrier/outbox audit history | Hold dispatch until reconciliation; a restored empty ledger is not permission to resend |

Run an incremental reconciliation at least every 15 minutes, using an Orders-owned read API or
export of committed expected fulfillment intents. This is proposed interface work, not an assumed
existing API. Compare all committed orders across a durable high-water mark, overlap late records,
and advance only after pages are accounted for. It must find orders whose event never reached the
worker, not only scan the worker's known rows. A daily full reconciliation provides coverage for
checkpoint or late-data defects. Persist discrepancies until resolved.

Separate carrier acceptance from physical shipment. The supplied interface proves creation, not
parcel handoff. Product must define the ship-by deadline and what counts as shipped; if physical
handoff is required, Fulfillment must add a confirmed tracking/handoff observation to this plan's
verification gate. Meanwhile report accepted groups and pending groups honestly. Before canary,
configure a receipt delay target, an acceptance deadline, and customer escalation ownership;
page Fulfillment immediately for ambiguous outcomes, and escalate unresolved cases again well
before day six. Do not wait until the idempotency window is about to expire to alert.

Use existing monitoring for dashboards covering orders missing plans, oldest incomplete order,
group states, uncertainty age, replay/conflict rate, and relay lag. Platform owns transport alerts;
Fulfillment owns shipment safety and recovery on-call; Orders owns plan validity and source
reconciliation. Support/Product owns customer decisions when shipment outcome cannot be proved.
Cap dispatcher concurrency to a configured carrier limit and backlog recovery rate. Database work
and ledger storage grow with total fulfillment groups, not just orders; carrier calls grow with
groups plus bounded recovery lookups. Actual capacity, pricing, and staffing are unknown. Measure
them with singleton traffic before splitting multiplies the effect rate. No new broker or service
framework is required, but the reconciliation job and exception queue create ongoing owner work.

**Rollback.** [unverified — proposed]

Before carrier ownership transfers, disable the new worker and new publishing; the legacy path
continues for single orders. Discarding a shadow deployment must not discard the migration
inventory. After transfer, roll back only to a ledger-aware, dual-format worker release. Restoring
the original ledger-free worker would bypass imported outcomes and is not an acceptable rollback.
If no compatible release is sound, pause dispatch and retain work while fixing forward.

After any split order is admitted, turn its admission flag off to limit further exposure; existing
split plans still need completion. Keep v2 consumption and v1 analytics publication running.
An API rollback may resume single-order admission only if it preserves existing split records,
pending v2 outbox rows, and routing metadata. Otherwise use the last compatible API release or
stop affected admission. Never down-convert a split plan to v1 for fulfillment. Relay rollback must
retain the routing classes; pause publishing rather than run a relay that misroutes them.

Schema expansion, extra routing, and pre-admission canaries are two-way doors while retained
compatible readers exist. Carrier acceptance is an irreversible business effect: cancellation is
best effort, and handed-off parcels cannot be recalled [sourced: task.md:27–28]. Split admission
therefore commits the system to retain compatible processing for outstanding orders. Do not drop
expanded schema, purge effect records, or retire readers as part of an emergency rollback. A
backup restore likewise pauses dispatch until external effects since the restored checkpoint are
reconciled.

**Verification and implementation handoff through the caller.** [unverified — required checks]

The builder should demonstrate these outcomes in an isolated environment before opening the
admission gates; no checks were executed for this design:

- Old API plus new relay/worker creates exactly one singleton shipment. Upgraded API preserves
  one logical v1 order event and creates exactly one shipment per v2 group. Analytics v1 for a
  split order is never accepted as fulfillment work.
- Duplicate delivery, reordered dual publications, relay fan-out failure, and 30-day replay leave
  the same effect rows and carrier shipments. A conflicting event or plan creates an actionable
  exception without new effects.
- Crashes before call, after carrier acceptance, and before local result commit recover by the
  original key. Test at days six, seven, and thirty: an unresolved expired outcome cannot issue a
  create call. Include a suspended/stale dispatcher and SDK retry behavior; do not infer external
  fencing from a successful lease test.
- Migration with a known shipped legacy order, a recent uncertain one, an old unknown one, and a
  queued unsent order seeds respectively accepted, recoverable, quarantined, and planned work.
  A legacy worker restart cannot call the carrier after transfer.
- Missing outbox delivery, lost worker intake, and a stuck group are found by reconciliation
  within the configured targets. Partial split success survives restart and rollback without
  repeating completed groups. A restore that loses ledger history holds dispatch.
- With old and new API releases coexisting, split admission reaches only capable producers;
  disabling admission leaves existing split work processable. Prove the compatible rollback
  release and absence of v1 semantic changes with analytics owners.

**Design packet.** Decisions: separate analytics from fulfillment; introduce one compatible
shipment owner and durable effect ledger; preserve original legacy keys; quarantine expired
uncertainty; gate split admission on ownership transfer. Assumptions: routing provenance can be
persisted, legacy carrier authority can be revoked, and Orders can supply an authoritative
reconciliation inventory. These are unverified release gates, not current capabilities. Weakest
point: legacy shipment history and bounded external dispatch may be insufficient to prove safe
recovery. Evidence of unresolvable legacy outcomes or unbounded late calls changes rollout scope
to held orders and lookup-only recovery, not relaxed deduplication. The seven-day/30-day mismatch
is recorded in this decision; Fulfillment owns its recovery policy and Product owns acceptance of
the resulting blocked-order behavior.

Return this design through the caller to `sde-agents:sde-fullstack` for implementation: Orders
owns immutable plans, compatible outbox writes, v1 meaning, and reconciliation export; Platform
owns routing, relay fan-out, replay provenance, and the legacy dispatch fence; Fulfillment owns
the compatible worker, imported effect ledger, carrier protocol, reconciliation, and rollback
release. The caller should sequence those team-owned changes against the numbered gates above
and obtain the named product decisions before split admission.
