---
name: upgrade-campaign
description: Plans and sequences a batch of version upgrades across a home lab — what to update, in what order, a rollback per step, a verification per service. Use for "update everything", "monthly patching", "patch day", "upgrade my stack", or a major-version move with breaking changes. Applies run under sde-agents:homelab-engineer's change tiers. Not for a single routine image bump (sde-agents:homelab-engineer) or a currently broken service (sde-agents:lab-incident).
argument-hint: [what to upgrade, or "everything"]
---

# Upgrade campaign

Finish the named upgrades with working services and a recoverable state. Use
`sde-agents:homelab-engineer`'s authority rules: a bounded user request covers in-scope execution,
verification, and recovery. Preserve real host gates and any explicit command or window limits;
add no campaign approval tier. A version label alone requires neither a new decision nor a new
session.

On Claude Code, live steps run only inside `sde-agents:homelab-engineer`, whose plugin hook scopes
to that agent. A direct main-loop invocation may prepare the campaign but must hand live work to
that agent through the caller; it has no scoped live-effect gate of its own. Do not execute live
steps in the main loop or change agent identity to avoid a gate. Other hosts follow the engineer's
generated host policy and available tools; user authorization does not create a missing tool.

## Prepare once, reuse what applies

1. **Bound the work.** Resolve the named services/hosts and maintenance window from the request and
   current lab inventory. If "everything" has no established scope, inventory first and resolve
   that scope before applying. Separate OS package patching, native binaries, containers, and
   shared infrastructure; use their existing runbooks, pin inventories, and deployment tools.
   Compare declared versions with actual running versions and relevant upstream releases. An
   update notification is a lead, not runtime proof or permission to adopt every newest major.
2. **Check the upgrade path.** Use upstream release/migration guidance covering the deployed →
   target range, including intervening breaking changes. A supported cumulative guide can cover
   that range; do not reread every release entry when it adds no missing compatibility fact.
   Record config changes, minimum dependencies, migrations, and one-way effects. Reuse sourced
   notes for the same versions; resolve gaps before the affected apply. External lookup follows
   the engineer's research boundary: send one sanitized batch of questions through the caller to
   `sde-agents:researcher`, without private configuration or credentials.
3. **Order by compatibility, then risk.** Check supported intermediate states and rollback for
   dependencies actually affected. If A2 needs B2, B-first works only if B2 supports A1. If neither
   order works, prepare a compatibility bridge or a coordinated maintenance step within the
   authorized scope. Prefer low-risk leaves among safe next steps. Parallelize independent reads
   and preparation; serialize deployment and verification on shared live paths and honor existing
   deployment locks.
4. **Establish recovery.** Reference the existing rollback procedure and applicable restore
   evidence. Reuse a drill when the backup method, restore procedure, and required versions remain
   applicable; a new version label alone does not invalidate it. For state migrations, identify
   the compatible old runtime, config, and pre-upgrade data needed for rollback. Reverting an image
   does not reverse a schema change. Obtain and verify the required consistent backup immediately
   before that service's risky step, with a freshness/data-loss bound appropriate to its writes.
   Do not require a data backup for a disposable, reproducible service.

Keep one compact ordered list: current → target, material effect/dependency, rollback reference,
verification, and any unresolved decision. Reuse it as the execution record. Take another session
only when the operator requests it or a real context/window limit requires a handoff; preserve
completed work and remaining dependencies instead of restarting discovery.

## Apply and verify

For each service, recheck material target/config/runtime and recovery assumptions just before
acting. Reuse unchanged evidence; refresh affected checks after drift, delay, or another writer.
Observed current-state drift calls for reassessment, not automatic reapproval. A different
selected target release or artifact digest requires confirmation unless the user explicitly
authorized that substitution; do not treat registry re-resolution as merely refreshed evidence.
Other changes escalate when the engineer's authority boundary or an explicit operator limit is
crossed.
When the approved artifact is still available and valid, use it without renewed approval; a
pending substitution does not block that apply or independent authorized work.

- Pin a specific release or digest and retain the prior runtime/config needed for recovery.
- Apply with the existing native tool, observe startup and relevant logs, then exercise the
  user-visible function and affected dependents before the next deployment. Reuse an existing
  application probe when it tests that function; container status alone is insufficient.
- Record the applied version and meaningful verification result in the same list. Update the
  canonical runbook only when a current fact or procedure changes; link existing evidence.

## Handle a failure at its actual scope

- **Observation failed:** a broken shell wrapper or probe timeout does not prove deployment
  failure. Correct the observation, reconcile live state, and verify before deciding to repeat or
  roll back a deployment. Do not restart a healthy service to repair a check.
- **Deployment failed or outcome unknown:** pause affected work, reconcile state, and use the
  authorized rollback/recovery path. If the change actually succeeded and is healthy, record it
  without replaying. Do not blindly revert across a state migration or repeat an uncertain write.
  For an unknown/in-flight migration, observe and establish safe interruption/recovery first:
  stopping writers, snapshotting, or taking a cold copy is not automatically safe or read-only.
  Missing recovery evidence stops those mutations; do not invent a recovery procedure.
- **Recovery verified:** defer the failed upgrade and continue already-authorized independent
  services only after proving they do not share the fault or depend on its target version.
- **Recovery unresolved, shared fault, or unsafe intermediate state:** stop dependent work and
  report the last known state and next decision. An expanded target set or previously undisclosed
  destructive consequence uses the engineer's confirmation boundary. Do not loop on unchanged
  failures; a further attempt needs new evidence and a bounded corrective step.

## Finish

Return one concise result: upgraded and verified, recovered/deferred and why, and material remaining
work. Keep runtime/config/recovery identities in the existing task or operating record so another
session can resume. Omit empty sections and duplicate packets.

After a storage or recovery-path change, use `sde-agents:restore-drill` to prove the affected path
when existing evidence no longer applies. Distinguish rollback into the old version from recovery
into the new version; do not demand that an old physical backup restore directly into a new format.
State any missing recovery proof rather than treating the campaign as fully verified. A routine
recovery gets a short note; use `sde-agents:postmortem` when recovery exposed a reusable gap or a
recurring/material incident, and scale its record to that consequence.

Label load-bearing claims `[verified]`, `[sourced]`, or `[unverified]`: cite release guidance and
report only exercised behavior as verified.
