---
name: host-onboard
description: The standardization checklist sde-agents:homelab-engineer works when bringing a new or rebuilt machine into the lab — OS and patch baseline, users and SSH with access recovery, package and update policy, firewall and management exposure, systemd health, storage, time and DNS, telemetry enrollment, backup enrollment, and config tracking with rollback. To onboard a host, ask sde-agents:homelab-engineer (it owns change authority and works this checklist under its tiers); a user can also run it directly as /sde-agents:host-onboard.
argument-hint: [host to onboard]
disable-model-invocation: true
---

Bring a new or rebuilt host to a small operational baseline, then add the checks its role needs.
A bounded host request does not automatically include deploying its services or unrelated cleanup.

## Authority and preparation

`sde-agents:homelab-engineer` owns live execution and its host controls. Run live steps in that
owner's execution context; otherwise prepare and return the live steps to the caller for delegation
with the existing authorization. This handoff does not require a fresh session or repeated consent;
operator handoff is needed only when the host cannot delegate or execute. Reading the checklist
does not grant its tools or live authority. Use the owner's bounded-request policy: one
authorization, one target/effect/recovery summary, and effect-specific precautions. Actual host
prompts, denials, and scope/data/access confirmation boundaries still apply.

Read existing lab facts, automation, and operating records; establish the host's role and requested
scope. Reuse applicable evidence, checking material assumptions against the target: a template is
intent, and a rebuild invalidates evidence tied to the previous instance. Mark checked settings
**already satisfied**; change only missing or incorrect in-scope configuration. Read selected fields
without exposing resolved secrets.

Batch independent discovery. Preserve real dependencies: prove recovery before access changes,
validate configuration before applying it, and establish host readiness before deploying services.

## Baseline for every host

1. **Access and exposure.** Verify intended administrative access and trusted users, SSH/sudo, and
   firewall policy against the lab profile (defaults: key-only SSH, root login off, minimal inbound
   exposure). Keep management access on the management network or VPN, off the public internet.
   Use declared service/firewall configuration as the explanation for expected ports; investigate
   unexpected exposure before changing it. Before any lockout-capable change, prove an independent
   recovery path and preserve the current session; a second SSH session alone is not independent
   of the SSH/network settings being changed. A rollback timer alone is not independent recovery.
   Verify available recovery directly; ask for missing access or evidence only when needed.
2. **OS and essential health.** Check supported OS, patch level, package sources, and the lab's
   update policy. Apply updates only within the request. Verify required units and their deliberate
   startup behavior, working time
   synchronization and DNS, and the resolver fallback if DNS depends on another lab service.
3. **Storage and visibility.** Verify required mounts persist, usable capacity fits the role, and
   one useful host health/capacity signal exists. Reuse the lab's monitoring when available; a
   focused host check can suffice without building a monitoring stack. Identify local state and
   its loss tolerance so the applicable protection below is not missed.
4. **Apply and verify.** Keep changed configuration in the lab's existing source of truth. Reference
   concrete rollback/recovery for changed effects in the preparation summary. Validate affected
   configuration and verify access, required units, and the host's intended function after changes.

## Add only when applicable

| Host characteristic | Additional work |
|---|---|
| Irreplaceable local state or recovery material | Verify backup coverage and a usable restore path; reuse applicable restore evidence or obtain missing proof through a safe in-scope scratch restore. This needs no separate consent unless it crosses the owner's boundaries. Unavailable proof remains an owned readiness gap; never overwrite live data merely to prove recovery. |
| Household-critical workloads | Verify actionable alerting and restart/recovery behavior; reuse applicable evidence. Keep needed disruptive checks within the authorized scope/window; missing verification remains a readiness gap. |
| Physical disks controlled by this host | Verify appropriate disk-health/SMART monitoring. Guests reuse the hypervisor's physical-disk coverage. |
| New services included in the request | Work `sde-agents:service-onboard` after the baseline. For existing services on a rebuild, reuse operating records and reverify affected runtime/dependency assumptions. |
| Unexpected failures or exposure | Investigate impact on access, security, storage, recovery, and intended workloads. Block affected readiness when material or unknown; report understood unrelated failures without expanding into cleanup. |

Recreatable images, caches, and source-derived state need no backup machinery solely because they
live on disk. Add centralized logs or dashboards only for an existing lab requirement or a named
operational question. Required protection and unresolved material failures are not optional polish.

## Completion

Write one short result in the existing host inventory or operating record: host/config identity,
changes and already-satisfied checks, verification and applicable protection evidence, and remaining
gaps with impact and owner (the operator by default). Reference existing records and the preparation
summary; no per-command approval packet. Explain non-applicability where otherwise ambiguous.

Ready means the baseline and applicable protections are verified for the intended role. Material
unknowns leave affected readiness incomplete; optional improvements do not hold completion open.
A harmless failed unit need not be repaired merely to reach zero. When services are outside the
request, report host readiness and stop without activating their onboarding.
