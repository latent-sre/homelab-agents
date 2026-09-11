# Homelab proportional operations: one Tier 2 decision, bounded standing policy

> **Authority update, 2026-09-11:** The accepted
> [bounded-campaign decision](2026-09-11-bounded-upgrade-campaign.md) supersedes this record's
> exact-command-only authorization, automatic fresh-Tier-3 decision, and prompt-only transport
> requirements. Its applicable host controls and unrelated decisions remain in force. The
> original rationale and evidence below are retained as history.

- **Date**: 2026-08-23
- **Status**: accepted
- **Owner**: `agents/homelab-engineer.md` (change authority and deployment standards)
- **Amends**: [`2026-08-20-effect-transport-policy.md`](2026-08-20-effect-transport-policy.md)
  for Tier 2 decision sources, preflight reuse, and the treatment of standing host policy
- **Operator ruling**: implement the policy and onboarding proportionality changes now; defer the
  separate always-loaded body reduction

## Context

The 2026-08-20 transport decision correctly retired a broker that the estate did not run, but its
replacement still imposed two avoidable forms of toil:

1. A reversible Tier 2 effect needed conversational approval and then a second human answer in the
   host's managed prompt, even though the prompt displayed and bound the exact invocation.
2. Every pre-authorized command was treated as a blanket bypass, so a narrowly scoped policy owned
   by the operator could not represent an earlier decision.

The onboarding definitions carried the same shape at a different layer: backup, TLS, auth, metrics,
a dashboard, a full runbook, resource limits, and a restart rehearsal read as universal service
requirements. Some are a sensible floor; the rest protect specific risks. Requiring all of them for
a disposable internal service spends more effort proving the checklist than operating the service.

This change does not lower Tier 3, remove recovery evidence, weaken drift handling, or compact the
agent's worked example and Work Order sections. That body reduction is deliberately separate.

## External evidence

### Documented host contracts — Context7

Context7 returned the current official host contracts, kept separate from the OSS adoption evidence
below:

- Claude Code's permission callback supports `once`, `always`, and `no`; an `always` decision can
  persist an operator-selected permission, while permission modes and deny/ask/allow rules remain
  distinct controls. Its bypass mode disables ordinary prompts, so bypass is not evidence of a
  decision. A `PreToolUse` hook can return `permissionDecision: ask` before execution, giving the
  fleet a host-owned way to prove interposition without issuing the effect. Sources:
  [user-input permission callback](https://code.claude.com/docs/en/agent-sdk/user-input),
  [permission modes](https://code.claude.com/docs/en/permission-modes),
  [hooks](https://code.claude.com/docs/en/hooks).
- Codex command approval exposes `accept`, `acceptForSession`, and an exec-policy amendment response.
  Its exec-policy engine reports the matched rules and effective `allow`, `prompt`, or `forbidden`
  decision, and `codex execpolicy check` evaluates an argv without executing it. Sources:
  [command approval protocol](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md),
  [exec-policy contract](https://github.com/openai/codex/blob/main/codex-rs/execpolicy/README.md).

The inference used here is narrow: both hosts can carry a decision either at invocation time or in
operator-managed policy. Neither contract says that every allow rule is safe enough for every
effect, so the fleet still defines which standing rules qualify.

### Real homelab adoption — GitHits

GitHits showed the risk boundary in public homelab source rather than a universal checklist:

- One PostgreSQL migration deliberately avoids jobs and a backup PVC because they would be more
  moving parts than a 10 MB migration; it instead keeps an off-cluster dump and leaves the old PVC
  untouched for rollback. [mortennordbye/homelab, `docs/postgres-18-migration.md`](https://github.com/mortennordbye/homelab/blob/main/docs/postgres-18-migration.md#L90-L106)
- The same repository's node-upgrade plan explicitly excludes PV data that the upgrade cannot touch
  and backs up the two irreplaceable databases plus recovery material. That is predicate-driven
  backup coverage, not "all stateful bytes." [mortennordbye/homelab, `docs/talos-kubernetes-upgrade.md`](https://github.com/mortennordbye/homelab/blob/main/docs/talos-kubernetes-upgrade.md#L268-L285)
- A Home Assistant migration deploys, verifies containers, bindings, user access, automations, and
  unaffected dependencies before cleanup; old PVCs wait roughly a week. This supports sequential
  apply/verify and delayed irreversible cleanup. [pablodelarco/kubernetes-homelab, `docs/ha-migration-plan.md`](https://github.com/pablodelarco/kubernetes-homelab/blob/main/docs/ha-migration-plan.md#L375-L472)
- A destructive Proxmox-to-NixOS migration keeps a full Go/No-Go gate: current backups, sampled
  restore proof, emergency access, evaluated target configuration, rollback, and announced downtime.
  [ec0m3x/nix-configs, `docs/homelab-migration.md`](https://github.com/ec0m3x/nix-configs/blob/main/docs/homelab-migration.md#L27-L41)

These repositories are examples, not authority for this fleet. Their common boundary supports the
local decision: simplify routine reversible work; preserve heavier evidence at data-loss and
access-path boundaries.

## Decision

### 1. A managed prompt may be the one human decision

For a new Tier 2 effect, the agent first presents the visible effect, target, exact invocation,
blast radius, rollback, and verification. The agent first obtains non-executing, pre-invocation
evidence that the effective host control will prompt for that exact argv and identifies the matched
rule or hook. If that trusted managed prompt then displays and binds the invocation, accepting it is
the explicit human decision. A separate chat confirmation is not required.

The command itself is never used to discover whether a prompt will fire: an allow or bypass mode
could execute the effect before a human decision. If interposition cannot be proven, the agent uses
a qualifying standing policy or hands the exact command to the operator.

If the operator already approved the exact effect or a finite plan in conversation, the host may
still prompt because transport enforcement is per invocation. The second click is not described as
a second justification or a missing approval.

### 2. Narrow operator-owned host policy may authorize Tier 2

A standing policy qualifies only when its rule and effective match are observable, operator-owned,
outside the agent's writable authority, bounded to the executable/arguments/target, and limited to
a reversible effect with rollback and verification. Wrapper shells, variable targets, unrestricted
argument tails, broad prefixes admitting unshown effects, session-wide bypass, agent-writable rules,
and undocumented claims of a rule do not qualify.

The durable review artifact records the policy location or identifier, a stable identity for the
matched rule such as its digest or version, and the effective exact match. A later session can then
identify the authorization actually used rather than trusting a transient claim that some rule
matched.

Tier 3 and irreversible/custody effects never use standing authorization. If a standing allow would
prevent a fresh managed prompt from interposing on Tier 3, the agent hands the command to the
operator instead of running it.

### 3. One decision may cover a finite ordered routine plan

An operator may approve one finite list of exact routine Tier 2 effects when every command, target,
visible effect, rollback, and verification is disclosed up front. Applies remain sequential; every
command passes its host transport and every service is verified before the next. The first failure,
unexpected result, material drift, or required command change stops the plan and opens a new
decision. Notable, major, one-way, shared-dependency, and Tier 3 steps stay separate.

### 4. Stable Tier 2 preflight reuses sentinels

The full preflight records the smallest identities that cover the decision: config hash, image
digest, target identity, and relevant state markers. Immediately before Tier 2 execution, only those
sentinels need rechecking when execution is prompt, inputs are versioned and transparent, and no
other writer can race them. Delay, opaque or unversioned state, another writer, incomplete sentinel
coverage, or any mismatch requires the full preflight and may reopen the decision. Tier 3 always
gets a fresh full preflight.

### 5. Service onboarding is predicate-driven

Every service retains a small floor: version-pinned source configuration, deliberate restart
behavior, one useful health signal, rollback, and an end-to-end check. Four predicates add work:

- irreplaceable persistent data → backup, restore ownership, and restore evidence;
- trust-boundary exposure → proxy/TLS/auth and a probe through that boundary;
- household-criticality → actionable alert, recovery documentation, and restart recovery evidence;
- privilege or resource contention → least-privilege isolation, limits, and capacity visibility.

A false predicate is recorded as not applicable. It does not require backup machinery, a public
route, dedicated metrics/dashboard, a full runbook, or an extra restart rehearsal. The canonical
inventory or runbook persists all four outcomes and their supporting operator facts, whether the
service takes the light or risk-triggered path.

## Typed packet and compatibility decision

The additive vocabulary is:

- `Gate: <consolidated|new|standing>`
- `Transport: <managed gate|operator handoff|standing policy>`

Existing `new`, `consolidated`, `managed gate`, and `operator handoff` packets remain valid. There
is no on-disk record migration: these fields are evaluation-time declarations, and historical
transcripts are immutable evidence. Rollback removes the two additive values together with the
definitions and cases that emit them; a new packet using those values would then correctly fail an
older linter rather than be silently reinterpreted.

The onboarding operating record is unversioned Markdown rather than a validated schema. No bulk
migration rewrites existing lab repositories; the writer adds all four predicate outcomes whenever
it creates or next updates a service's canonical inventory or runbook record, and an older record
without them is reported as incomplete rather than treated as proof. Rolling this fleet change back
leaves those additive facts readable and inert, so no reverse migration is required.

## Controls deliberately preserved

- Tier 0 capture-safe discovery and the dry-run/check-mode caveat.
- Visible effect first, exact target/command, rollback, verification, and no argument widening.
- One change at a time on live paths, with observation between applies.
- Material drift reopens the decision; Tier 3 never consolidates or stands.
- Proven recovery and out-of-band access for destructive/access-path work.
- No wrapper-shell substitution or session-wide permission bypass.
- Restore drills use scratch targets; upgrades stop on the first failure; suspected compromise
  preserves volatile evidence instead of restarting.
- The runbook skill's closed proposal grammar and caller-authority ceiling.

## Out of scope

Reducing the always-loaded `homelab-engineer` body — including moving or compressing the worked
example and Work Order contract — is explicitly deferred to the next round. This change edits those
sections only where their current words would contradict the new behavior.

## Verification

- Offline behavioral contracts cover proven versus unproven managed-prompt interposition, standing
  Tier 2 versus Tier 3 with durable rule identity, independent finite-plan stop conditions, and
  paired light versus risk-triggered onboarding with durable predicate outcomes.
- The red-first proportionality class produced 18 failures when those assertions were absent; its
  13 tests now pass, including one-at-a-time omission mutations for every reviewed condition.
- `packet_lint.py` mirrors the two additive values and its canonical-source drift test remains the
  owner check.
- Adapter regeneration wrote 182 files; `python3 scripts/validate_fleet.py` validated 11 agents and
  20 skills, and `python3 scripts/run_tests.py` passed 1,005 tests across 33 modules.
- `claude plugin validate . --strict` passed. On the clean committed candidate, `fleet_doctor.py`
  reported no failures and two warnings: the unchanged fleet skill descriptions total about 9,983
  characters against the host's 8,000-character default, and the installed Codex agents do not yet
  match this uninstalled candidate. Intentional host synchronization remains an installation step;
  neither warning is presented as green.
- The canonical agent body is 28,129 bytes and the largest generated projection is 28,844 bytes.
  This round did not claim a body-size improvement; the separately authorized compaction round owns
  that work.
- The paid behavioral lane remains an explicit operator purchase; offline oracle controls prove
  the new graders fire but do not claim live model behavior.

## Amendment 2026-09-01

The `python3 scripts/run_tests.py` line above stands as a dated record of what ran on 2026-08-23;
`scripts/run_tests.py` was retired 2026-09-01, and the equivalent check today is
`python3 -m unittest discover -s tests`.

A 2026-09-02 correction: the behavioral harness retired that day under the single-operator
audience decision. "The paid behavioral lane remains an explicit operator purchase" above is a
dated record of what was true on 2026-08-23; that purchase will not be made. The offline behavioral
contracts and oracle controls cited in this record retired with `evals/behavioral/contracts.json`;
routing evals and the probe are the remaining paid instruments.

## Amendment 2026-09-07

The operator selected the main-based operating-flow simplification in
[the operating-flow decision](2026-09-07-homelab-operating-flow.md). It retires exact packet
grammar, the work-order digest/receipt, and routine Learning closeout while preserving the
permission tiers, actual execution transports, recovery evidence, and retry/reconciliation
boundaries. Earlier grammar and probe descriptions above remain dated evidence.

That selection supersedes CTX-005's earlier contract-preserving diet, including its prohibition
on mixing policy changes into that experiment. CTX-005 closes as **superseded**, not accepted:
its failed candidate remains historical no-go evidence, and its missing acceptance evidence is
not converted into a pass. LABFLOW-001 owns the newly authorized scope and its explicit verification
limits. The [original outcome](../archive/2026-08/gate-006-outcome-2026-08-30.md) and
[CTX-005 history](../archive/2026-09/roadmap-history-2026-09-01.md#ctx-005-shrink-homelab-engineers-always-loaded-body)
retain the failed results. No old candidate or capture was reused as the new implementation.
