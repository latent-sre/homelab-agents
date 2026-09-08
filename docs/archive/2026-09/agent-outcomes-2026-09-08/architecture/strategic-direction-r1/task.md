# Strategic direction task

This is a synthetic fixture, not a description of a live organization. Treat the facts below as
supplied inputs; additional properties are assumptions. This is a decision document only.
No external research or implementation is authorized for this consult.

I need a direction for our event platform across six product teams over the next five years.
We have two platform operators, neither available to staff a new round-the-clock team. Current
traffic is 20,000 events/second; planning should consider tenfold growth, although its timing is
uncertain. Event payloads include customer data, which must remain in our approved region.

Today each team uses its own PostgreSQL outbox and worker queues. Interfaces and replay tooling
are inconsistent; a cross-team incident last quarter required six separate reconciliations.
There is no measured throughput ceiling or complete cost baseline for the current setup. No
team has yet proved a need for synchronous global ordering. Team-owned services must continue
deploying independently.

Leadership asks whether to keep and standardize what we have, operate an open-source event
platform, or buy a managed service. We have no validated vendor prices, SLAs, residency details,
or guarantees about limits, replication, replay, or delivery semantics. We also lack representative
event sizes and a retention requirement. Do not fill those gaps with remembered product claims.

Give us a usable strategic decision now, with the durable alternatives and what the six teams
and two operators would own. Explain the destination, the first useful step, and the evidence
that could change the direction. We can fund a bounded evaluation, but this does not authorize
buying a service or starting a platform migration.
