# System design task

This is a synthetic fixture, not a description of a live repository. Treat the facts below as
supplied requirements; any additional system property is an assumption. Produce a design for
the builder who will implement it. No external research or implementation is authorized.

We need to migrate order events without coordinating releases of the Orders API and the
Fulfillment worker. The platform decision is already settled: keep our existing managed event
bus, PostgreSQL stores, and the transactional outbox. Do not reopen that platform decision.

The API commits an order and a v1 outbox record in one PostgreSQL transaction. The relay can
publish a record more than once. The bus can redeliver and reorder records; retained messages
can be replayed for 30 days. API, relay, and worker deploy independently. Two analytics consumers
will remain v1-only for at least eight weeks.

v1 OrderCreated contains event_id, order_id, currency, total_minor, and shipping_address. Today
one order creates one shipment. We are adding split fulfillment: v2 carries a stable list of
fulfillment groups, each with its own fulfillment_id, line items, and destination. An order
may create several shipments. The v1 shipment worker cannot interpret split orders safely.
Analytics still needs one order-level event with the existing v1 meanings. A business flag can
hold split-order admission off while compatible infrastructure rolls out.

The worker owns a PostgreSQL database. Creating a shipment calls an external carrier. The
carrier honors a caller-supplied idempotency key for seven days and provides shipment lookup by
that key during those seven days. A worker can crash after the carrier accepts a shipment but
before the local result is committed. The product requires avoiding duplicate shipments and
detecting orders that never ship. Shipment cancellation after carrier acceptance is best effort,
and a parcel handed off to the carrier cannot be recalled. The legacy worker currently uses
order_id as its carrier key and has no durable effect ledger.

The Orders team owns the API and outbox schema; Fulfillment owns the worker and carrier
integration; Platform owns the relay and bus. Give these teams an implementable migration
decision, rollout sequence, operational failure handling, and a rollback story that works while
old and new consumers coexist. End with the implementation handoff through the caller.
