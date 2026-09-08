---
name: postmortem
description: Writes a blameless postmortem after an incident, outage, or near-miss is resolved — timeline, impact, trigger vs root cause, mitigative vs preventative actions. Use for "write up what happened", "do a retro on the outage", "document that incident", or any recovery worth learning from. Not for a live failure (sde-agents:lab-incident), an undiagnosed bug (sde-agents:root-cause), or routine operating docs (sde-agents:runbook).
argument-hint: [the incident to write up]
---

# Postmortem

A postmortem turns one bad afternoon into a system that fails better next time. Write it after
recovery — same day while the evidence is fresh — and write it **from evidence** (logs, timestamps,
shell history, `git log`, monitoring graphs), never from memory. Memory smooths the timeline and
deletes the dead ends, and the dead ends are where the lessons are.

Blameless, single-operator edition: the question is never "why was I careless" — it is **"what made
the mistake easy?"** Self-blame produces no artifact; a missing guardrail is an action item. This
holds with one operator exactly as it does with forty.

Two boundaries before writing:

- **Separate the record from the investigation.** Cite established diagnosis. If cause remains
  unknown, write the factual recovery record now: label hypotheses, missing evidence, and the
  owner and trigger for further investigation through `sde-agents:root-cause`. Do not invent a
  cause or restart an exhausted investigation merely to fill the template. A final factual
  write-up may retain an unresolved cause and open follow-up actions.
- **The incident must be over.** Mid-outage, mitigation outranks documentation; capture timestamps
  as they happen if you can, write prose only after recovery.

## Required structure (every slot filled or marked "n/a — why")

Copy the template from [assets/postmortem.md](assets/postmortem.md). The slots, and what each is
for:

- **Summary** — what broke, for how long, who or what noticed. Three sentences, no suspense.
- **Impact** — services affected, duration, and **data lost or not, stated explicitly** — "no data
  loss" is a claim that needs evidence, not an assumption of silence.
- **Timeline** — first bad signal → detected → mitigated → resolved, timestamped from evidence,
  each row citing its source. Name the detection source: a *person* noticing is a detection gap,
  and the gap is a finding.
- **Trigger vs root cause** — distinguish the observed event from the condition that made the
  failure possible. Label each as established, hypothesized, or unknown with supporting evidence.
  Recovery does not prove cause removal. For an unresolved cause, record competing hypotheses,
  evidence needed to distinguish them, an investigation owner, and a concrete reopen trigger.
- **What went well / what went poorly** — two honest lists, one line each. "The backup restored
  cleanly" is as load-bearing as any failure.
- **Where we got lucky** — luck is a preventative action item waiting to be written. If the outage
  was short because someone happened to be home, the action item is the alert that removes the
  "happened to".
- **Actions** — split **mitigative** (shrinks the next occurrence: faster detection, smaller blast
  radius, a rehearsed recovery) from **preventative** (stops the recurrence: the config fix, the
  guardrail), with **investigative** actions for unresolved questions. Do not claim that a
  hypothesis-driven action prevents recurrence. Every action names the **artifact** it becomes — a runbook line, an alert, a drill,
  a validator rule — and a **proof-of-done** check. An action with no artifact will not happen.
- **Runbook updated** — which runbook gained a supported symptom/cause/fix or factual recovery
  note, with unresolved cause explicit, or "n/a — why". Last
  slot in the template because it is the one that most often goes unwritten; see Feed it forward.

Label load-bearing claims `[verified]`, `[sourced]`, or `[unverified]` per the fleet evidence
convention — a timeline entry you reconstructed rather than read is `[unverified]` and says so.

## Feed it forward — where the learning goes

A postmortem that ends as a document changed nothing. Before closing out:

- Carry established **symptom → cause → fix** knowledge into the affected runbook under the
  `sde-agents:runbook` admission and write-authority rules. If cause is unknown, preserve the
  observed symptom, verified recovery (or that recovery was spontaneous), evidence gaps, and
  investigation owner without turning a hypothesis into a runnable fix. Correct commands proved
  wrong when authorized; otherwise hand the evidence and destination to the runbook's owner.
- Systemic findings (unmonitored service, undrilled restore, single point of failure) become checks
  for the next `sde-agents:lab-audit` sweep.
- If a contributing cause was **fleet behavior** — a stale runbook trusted, an apply without its
  tier evidence, a skill that misrouted — record the evidence, proposed destination, and owner
  in the action item. A maintainer may explicitly invoke `/sde-agents:self-improve-loop` to
  investigate it; completing this postmortem does not start a fleet retro or authorize fleet edits.
- File it where the lab repo keeps documents — `docs/postmortems/YYYY-MM-DD-<slug>.md` unless the
  repo already has a convention, in which case the existing convention wins.

Near-misses earn the same write-up at half the length: the incident that almost happened is the
cheapest one to learn from.
