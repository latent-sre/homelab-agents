---
name: lab-incident
description: Mitigate-first response while a home-lab service is down or degraded — restore service now, diagnose after. Use for "X is down", "the lab is unreachable", "everything broke after the update", "nothing loads" — an active outage affecting someone right now. Mitigations apply under sde-agents:homelab-engineer's change tiers. Not for a resolved incident (sde-agents:postmortem), a bug with no live outage (sde-agents:root-cause), or a routine health sweep (sde-agents:lab-audit).
argument-hint: [what is down]
---

# Lab incident — mitigate first

**Restoring service outranks understanding it.** This is the one place the fleet's
diagnose-before-you-touch rule is deliberately inverted: `sde-agents:root-cause` is right for a bug
and wrong mid-outage, because every minute spent on a clean diagnosis is a minute the service is
still down. Mitigate, confirm recovery, *then* run the loop on the cause with the pressure off.

Announce at start: "Using lab-incident: mitigate → confirm → diagnose after."

**Authority: you hold none of your own.** Every action below is an apply under
`sde-agents:homelab-engineer`'s change tiers, with that agent's approval evidence. Speed is not a
tier exemption — an outage makes the blast-radius question *more* important, not less, because the
system is already degraded and a second change lands on top of the first.

Use the bounded request's recovery authority. State the concrete mitigation and recovery limit
once; traverse actual host controls without adding another conversational decision. Reconcile
unexpected results before another live step. A corrected command within the same authorized
outcome is not automatically a new approval; an expanded target set, undisclosed destructive
consequence, or other engineer confirmation boundary is. Do not stack speculative mitigations or
infer permission from urgency.

## Step 1 — read the signals before touching anything (60 seconds, not 10 minutes)

One pass, time-boxed, to tell an outage from a symptom: what is actually broken, how wide, and
what changed. The signal read and the "what changed" checklist live in
[`references/golden-signals.md`](references/golden-signals.md) — read it now if the shape of the
failure isn't obvious in the first look.

Two questions decide everything that follows:

- **Blast radius** — one service, one host, or the shared path (DNS, reverse proxy, storage,
  network)? A single service that's down is a service problem; three unrelated services down
  together is a shared-dependency problem, and restarting any one of them wastes the outage.
- **What changed** — an update, a config edit, a reboot, a certificate expiry, a full disk, an
  upstream ISP event. Most outages are the last change. If you know the change, the mitigation is
  usually to undo it, and you are done with this step.

## Step 2 — pick the smallest mitigation that restores service

| Situation | Mitigation | Not this |
|---|---|---|
| Broke right after a deploy or image change | Roll back to the previous known-good tag (`compose` file pinned back, `up -d`) | Debugging the new version while it's down |
| Config edit broke it | Revert the config from git and reload the service | Hand-editing the live config further |
| Route or proxy returns errors, upstream is healthy | Revert the proxy route/vhost change and reload | Restarting the healthy upstream |
| Process wedged, no recent change, logs show a hang | Restart the one service — **once** | A stack-wide `down`/`up` that widens the outage |
| Disk full | Free the specific space (rotate/prune the identified consumer), then restart what failed | `docker system prune -a` mid-outage, which deletes images you may need to roll back to |
| Shared dependency down (DNS, proxy, storage) | Fix the dependency; leave the dependents alone until it's healthy | Restarting dependents, which only refreshes the same failure |
| Data loss or corruption suspected | Establish safe containment and recovery per the runbook; for an unknown/in-flight migration, observe and prove safe interruption before stopping writers or snapshotting | Treating a cold stop/copy as read-only or restoring without a verified recovery path |
| Cause unknown and impact is spreading | Deliberately reduce scope: stop the noisy component, serve a maintenance page, degrade the feature | Broad speculative restarts |

**Restart is a stopgap, never a fix.** A service that came back after a restart with no explanation
is still broken — it will be back, usually at a worse hour. Note it as an unresolved cause; the
postmortem's preventative action is what closes it.

## Step 3 — one change, then observe

Make **one** change and watch the signal you expect it to move, for long enough to be real (a
health check passing twice, not once). Then decide: recovered, no effect, or worse.

- **No effect** → undo it before trying the next thing. Stacked half-mitigations are why an outage
  becomes a mystery: at the end nobody knows which change is load-bearing, and the postmortem's
  timeline is unreconstructible.
- **Worse** → revert immediately, and treat that as information about the cause.
- Keep a running timestamped note as you go — what you ran, at what time, what happened —
  emitted as you go, not saved up for the end: a session that ends mid-incident takes everything
  unwritten with it. You are writing the postmortem's timeline right now, and memory will smooth
  it later.

## Step 4 — confirm recovery honestly

Recovered means the *user-visible* thing works, verified end to end — the page loads, the file
saves, the stream plays — not that the container says healthy. Then confirm the signals hold at
their normal baseline for a few minutes; a flapping service that happened to be up when you looked
is not recovered. **Only then** downgrade the situation from "outage" to "follow-up" — an
authority edge, not a label: the downgrade is what ends this skill's mitigate-first inversion and
returns the lab to diagnose-before-you-touch.

## Step 5 — hand off, don't stop

An outage is over when service is restored *and* the work it created has an owner:

- Cause still unknown → `sde-agents:root-cause` now, with the outage evidence and your notes. This
  is the moment the diagnose-first loop becomes correct again.
- Recovery wasn't obvious, the incident recurred, or it exposed a gap worth fixing →
  `sde-agents:postmortem` for the write-up, which turns your timestamped notes into actions. A
  wedged container restarted once, with an obvious cause, owes the runbook a line — not a document.
- A mitigation you had to invent because the runbook lacked it → that's a `sde-agents:runbook`
  edit, and it's part of finishing, not optional cleanup.

## Security carve-out — the one case where you do not mitigate

If the failure looks like a compromise — an unexplained process or container, a modified binary,
credentials in an unexpected place, outbound traffic to somewhere unaccounted for — **stop and hand
it to the operator.** Do not restart, rebuild, or clean the box: restarting destroys the volatile
evidence (running processes, open sockets, memory) that identifies what happened, and re-imaging
before you know the entry point re-creates the vulnerability. Isolate rather than repair if
containment can't wait — pull it off the network, keep it powered — and preserve what you have.
Uptime is not worth reinfection.

Label load-bearing claims `[verified]`, `[sourced]`, or `[unverified]` per the fleet evidence
convention — mid-outage especially, where "the disk was full" is often inference rather than a
number someone read.
