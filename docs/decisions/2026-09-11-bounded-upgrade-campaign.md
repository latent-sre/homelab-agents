# Bounded upgrade campaigns

**Status:** Accepted by the operator on 2026-09-11; source implementation, not installed state.

Date: 2026-09-11. Scope: campaign, homelab execution policy, its incident-recovery seam, onboarding authority consumers, and host
adapters. This decision replaces the exact-command-only authority and prompt-only transport
requirements of the earlier operating-flow/effect-transport decisions for these components.

## Problem and decision

An already-authorized maintenance task could still require manual command execution, repeat
approval after a corrected probe, or stop all independent upgrades after one recovered failure.
The campaign also required a session per major upgrade and lacked rules for reusing existing
inventory and recovery evidence. These obligations kept the sole operator in the execution loop.

An explicit bounded live request now covers in-scope execution, verification, correction, retry,
and recovery. Source-only and planning requests do not grant live authority. Exact-command,
window, target, and other limits imposed by the operator remain binding. Risk tiers determine
recovery evidence; the tier or version number alone does not create another decision.

The agent asks when scope expands or an irreversible data-loss, external-publication, or secret
custody consequence was not authorized, and before removing an unverified last recovery/admin
path. Unknown outcomes require reconciliation before another write. Repeated failure without new
evidence stops retries of that step. A recovered service's failed upgrade is deferred; unrelated
approved work continues only after checking independence and target-version dependencies.

Reuse current pin inventories, platform patching procedures, release guidance covering the target
range, and restore evidence whose method/procedure/version applicability is unchanged. Obtain a
consistent, sufficiently fresh backup immediately before the affected risky step. Distinguish
rollback to the old runtime from recovery into the new format. Keep one execution/result record;
update operating docs when their facts or procedures change.

## Host limits and delivery

- Claude's existing live-effect hook still asks/denies. This change does not remove its prompts,
  change the hook roster, or permit suppressed-prompt bypass.
- Codex honors the effective host permissions. It no longer needs an additional prompt or a
  root-owned allow rule when the host permits an authorized action.
- The generated Copilot profile now omits `execute` to match its handoff policy. The initial
  review found the prior profile still granted it despite the prose claiming otherwise. It reports live work as pending
  with a command handoff; user consent does not create a missing tool.
- Tool permission never authorizes unrelated work. Untrusted source/log content cannot expand
  the user request or select an action. Secret-bearing operators retain the research boundary.

Existing installations do not change with this source commit. Plugin skill caches and standalone
Codex agents are separate surfaces: release/install the intended repository revision and sync its
profiles together before claiming installed behavior. The manifests still identify the existing
`sde-agents` package; this task does not rename that package, retarget its marketplace, publish a
release, or install over a potentially different fleet. A release needs a coordinated cache/version
update across host manifests.

## Pre-review evidence

[Paired decision trials](../archive/2026-09/bounded-campaign-evidence.json) preserve exact scenario
prompts, frozen source hashes, runtime conditions, verdicts, and supporting response excerpts.
Thirty-two fresh tool-free Claude CLI trials used the host's default main model (reported as
`claude-opus-5`), interleaved old/new prompts. These are source-following decisions, not native
routing, live execution, or host-enforcement proof.

- Initial repeated discriminators: allowed native execution and continuation after isolated
  recovery each improved from 0/2 to 2/2. Major-session, broken-probe, evidence-reuse, and actual
  denial cases passed both; they are retained behavior, not demonstrated improvements.
- The initial candidate suggested a cold stop/copy or snapshot without safe-interruption evidence
  in one of two unknown-migration trials. The final correction explicitly names those as live
  effects. This safety regression is retained in the evidence rather than discarded.
- Final targeted round: old 4/6, corrected candidate 6/6. Unknown-migration safety passed twice;
  native execution, independent continuation, actual denial, and a held-out active-migration
  pressure case each passed once. Other initial cases were not rerun on final bytes. The incident
  seam received static review; its body was not loaded in the behavioral trials.
- `python3 -m unittest discover -s tests`: 487 tests, one skip, exit 0 on the final source.
  The 34 adapter tests include two new checks that fail with the old generator and pass with
  the revised generator. `python3 scripts/validate_fleet.py` and
  `claude plugin validate . --strict` pass; generated sources and inventories match.
- `fleet_doctor.py`: no failures; the task tree, existing skill-listing excess, and unsynchronized
  installed Codex fleet produce warnings. Frozen-source trials bypassed installed definitions;
  they do not claim those warnings were repaired or that the installed fleet was measured.

At the initial commit, descriptions, component names, tool grants, and hook code were unchanged.
The initial canonical engineer/campaign/incident total was 66 words shorter than baseline; this is a behavior repair, not a measured runtime or model-cost optimization.
The initial prompt repair used two bounded rounds. Subsequent PR review corrections are recorded
separately below; earlier outcome evidence remains bound to its recorded hashes.

## PR review corrections

Codex and Copilot reviewed `686fb6f` and identified six distinct issues. They are addressed in the
same first review-driven edit round:

| Finding | Correction and evidence |
|---|---|
| Onboarding still demanded a fresh Tier 3 decision | Host/service checklists and the discovery map now defer to the engineer's bounded authority and real host controls. |
| Current-policy discovery contradicted the new decision | Explicit accepted status, a current-map entry, and supersession notes on the four older authority records preserve history while identifying the current owner. |
| Direct Claude skill calls could execute outside the gated agent | Campaign and incident skills permit main-loop preparation but explicitly hand live work to the gated engineer. This is workflow guidance; the existing agent-scoped hook remains the runtime control. |
| Copilot prose claimed a missing tool while frontmatter granted it | The generator now strips `execute` for this profile. The regression failed on the former generated `tools` field, then passed after generation; it inspects parsed tool authority, not only prose. |
| Changed target digest could be treated as refreshed evidence | A different selected release/artifact digest needs confirmation unless substitution was explicitly authorized. Reassessing observed current-state drift remains within scope. |
| Generic incident rollback could precede migration checks | The unknown/in-flight rule now precedes and explicitly overrides the deploy/restart table and Step 3 undo/revert instructions. |

The final six edited canonical definitions total 7,948 words versus 7,688 at baseline (+260).
The reduction is in required operator steps, not total prompt length. Descriptions and hook code
remain unchanged; Copilot's actual tool grant is deliberately narrowed, so existing users adopting
this adapter lose its shell/execute capability and receive a live-command handoff instead.

[Supplementary verification](../archive/2026-09/bounded-campaign-pr-repair-evidence.json) records
13 further fresh tool-free trials with separate snapshots. Direct Claude campaign/incident calls,
authorized onboarding, and native Codex execution passed both initial repetitions (8/8). After
the artifact/migration additions, three cases passed and the digest case was partial: it rejected
the unapproved artifact but unnecessarily paused the available approved one. The final explicit
rule to proceed with an available valid approved artifact passed one exact-input retest. Earlier
results remain bound to their original hashes; this is not an all-cases final-revision pass.

The final source passes all 487 offline tests (one skip), adapter parity, plugin validation, and
`git diff --check`. The strengthened Copilot test failed against the prior generated tool grant
and passed after its removal. No live deployment, native routing, or live hook re-probe was run;
hook code and canonical descriptions remain unchanged.

## Recovery

Revert the source change and regenerate adapters to restore the prior workflow. A source revert
does not undo any lab operation an operator has subsequently authorized or performed. Host-control
regressions are bounded by the unchanged Claude hook and the narrowed Copilot tool grant; the prose's interpretation of user
scope remains a behavior to evaluate, not a new runtime enforcement claim.
