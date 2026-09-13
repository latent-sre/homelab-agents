# Bounded upgrade campaigns

> **2026-09-12 amendment:**
> [Proportional homelab controls](2026-09-12-proportional-homelab-controls.md) makes the Claude
> live-effect interposition optional; `host` policy is now the default. The bounded authorization,
> recovery, migration and actual host-control rules below remain in force. Recorded prompt-mode
> results below are historical evidence for the former mandatory filter.

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
custody consequence was not authorized, and before removing a last recovery/admin path
unless an independent alternative has been verified. Unknown outcomes require reconciliation before another write. Repeated failure without new
evidence stops retries of that step. A recovered service's failed upgrade is deferred; unrelated
approved work continues only after checking independence and target-version dependencies.

Reuse current pin inventories, platform patching procedures, release guidance covering the target
range, and restore evidence whose method/procedure/version applicability is unchanged. Obtain a
consistent, sufficiently fresh backup immediately before the affected risky step. Distinguish
rollback to the old runtime from recovery into the new format. Keep one execution/result record;
update operating docs when their facts or procedures change.

## Host limits and delivery

- Claude's existing live-effect hook still asks/denies. This change does not remove its prompts,
  change the hook roster, or bypass a returned prompt/denial. It is a partial command filter:
  unbound/unparseable forms can ask/deny even without a named rule. When the hook returns no
  decision, actual host permissions may allow execution without a prompt. No hook decision grants new task scope.
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

At the first review correction, the six edited canonical definitions totalled 7,948 words
versus 7,688 at baseline (+260).
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

## Second PR review disposition

Reviews of `00d2dd0` found remaining coverage claims and the live host-guide paraphrase. Direct
campaign/incident routing is now explicitly cooperative: Claude live work belongs in the gated
engineer, and Copilot/VS Code live work goes to operator handoff even when main chat offers
execution. A directly invoked skill does not inherit a profile's omitted tools. These instructions
cannot enforce a sandbox in main chat. The host guide and engineering-program map now state that
same boundary and the permitted native Codex path.

The request to restore mandatory handoff for every unlisted Claude command is **declined**. The
operator accepted bounded delegation with actual host controls, not a new exact-command prompt
requirement. The existing hook can return no decision for a parsed unlisted command; the host's own policy
can then allow an explicitly authorized command. Unbound/unparseable forms still ask/deny. Denied/gated effects must not be
repackaged as unlisted commands, and no available tool grants additional task scope. The former
blanket claim about suppressed-prompt bypass was narrowed to the hook decisions actually made.

A pure-function check of the unchanged `live-effect-gate.py` demonstrates the limit without
executing any live command: under `bypassPermissions`, scoped `sysctl -w` returns exit 42/no
hook decision; scoped `systemctl restart example` returns exit 43/deny; the same restart in a main
loop with no `agent_type` returns exit 42/no hook decision. This proves filter decisions, not
runtime hook installation. Adding a universal gate or sandbox is a different mechanism and was
not smuggled into this workflow repair.

At the second correction, the six canonical definitions totalled 8,078 words versus 7,688
at baseline (+390). Required
operator steps were removed; text length increased to make authority and host limits explicit.
Offline verification still passes 487 tests (one skip), adapter parity, plugin validation, and
diff whitespace checks. [Four targeted fresh decision trials](../archive/2026-09/bounded-campaign-pr-repair2-evidence.json)
passed: direct Copilot campaign/incident handoff, authorized unlisted Claude execution without
claiming hook approval, and refusal to repackage a denied restart. The report records exact source
hashes and prompts. These are cooperative decision checks, not live execution or hook-load proof;
older results remain bound to their earlier source snapshots.

## Third and final review-driven correction

Reviews of `dc6ecfa` found that the Claude routing instruction could send an already-active
engineer back to itself, and direct Codex skill selection did not load the owner policy. The
Claude branch now routes only direct main-loop calls; an active engineer continues. Codex reuses
its full active policy when loaded, otherwise reads the full active installed profile before the
first live step, with preparation/handoff if unavailable. A description or repository-supplied
profile is not a substitute. Profile lookup is not an additional user approval.

Each live effect now receives its own risk assessment so an image bump cannot conceal a migration
or access change under Tier 2. The README's older universal-prompt claim is corrected. Host
summaries now distinguish a genuine no-decision hook result from unbound/unparseable commands,
which can ask/deny without a named rule. A pure-function check confirmed an unbound `sh -c`
restart returns exit 43/deny under suppressed prompts; no shell command was executed. The decision
record's last-path wording now matches the requirement for a verified independent alternative.

[Six final targeted trials](../archive/2026-09/bounded-campaign-pr-repair3-evidence.json) passed
their operational criteria: active Claude campaign and incident execution, Codex missing-policy
loading (skill-only input) and loaded-policy reuse, mixed migration precautions, and wrapper
denial. Two answer-quality residuals are preserved: an invented example policy path and a health
claim unsupported by a probe. These prevent any claim that real policy discovery or service
health was verified; they were not hidden behind the operational pass count. No further tuning
was performed.

The final source passes 487 offline tests (one skip), generated parity, plugin validation, and
whitespace checks. Six edited canonical definitions total 8,308 words versus 7,688 at baseline
(+620); the intended reduction is operator ceremony, not prompt size. This exhausts the three
review-driven edit rounds. Further findings receive an explicit disposition under the repository
review contract rather than another silent rewrite.

## Explicitly authorized last batch

After the three-round cap, the operator explicitly authorized one last batch. Every non-engineer
Claude context now hands live work through its caller to the engineer. Codex must verify the
active installed policy source from effective configuration or disclosed metadata, without guessing
paths. Incident handling repairs failed observations and reconciles unknown write outcomes before
mutation. Native Codex controls and explicit operator command limits remain binding. The hook's
module docstring now describes bounded authority and partial filtering; its executable AST is
unchanged. No routing description was changed: the original campaign already included live apply,
and no routing miss was demonstrated.

[Four final one-shot cases](../archive/2026-09/bounded-campaign-last-batch-evidence.json) pass on
frozen final sources: both Claude builder handoffs, missing-source Codex refusal to invent a path,
and incident reconciliation without an unsupported health claim. These are decision simulations,
not runtime enforcement or service-health proof. Earlier residuals remain in their original reports.
Final offline verification passes 487 tests (one skip), fleet parity, and strict plugin validation.
A focused native hook probe observed the engineer deny under suppressed prompts; the main-loop
arm was inconclusive because it never attempted the command. Executable hook AST equivalence
was checked against `73cfe08`. Six canonical definitions now total 8,413 words (+725 over baseline).
This is the last authorized source-fix batch; further review observations receive a disposition.

## Reopen criteria

Reopen on a recorded task that bypasses an actual host denial, changes an unauthorized target or
artifact, loses recovery/admin access, performs unsafe migration recovery, or needlessly asks
again within a clearly authorized scope. Capture the exact installed policy, host permissions,
request, and observed action so a policy defect can be distinguished from installation drift or
an unsupported health claim. A demonstrated routing miss can reopen the description separately;
no such miss was established here, and the original skill already contained live apply steps.

The rejected alternative is mandatory exact-command interposition for every live action. Revisit
that choice only with an observed failure that bounded user authority plus the actual host
controls cannot contain, and evaluate the extra operator work alongside the safety benefit.

## Recovery

Revert the source change and regenerate adapters to restore the prior workflow. A source revert
does not undo any lab operation an operator has subsequently authorized or performed. Host-control
regressions are bounded by the unchanged Claude hook and the narrowed Copilot tool grant; the prose's interpretation of user
scope remains a behavior to evaluate, not a new runtime enforcement claim.
