# Fleet roadmap

> **Status: live.**
> This is the only document that tracks unfinished, blocked, or explicitly deferred fleet work.
> Reviews, decision records, and execution plans supply rationale and implementation detail; they
> do not independently add work to the queue.

This file will contain only unfinished, blocked, or explicitly deferred work for the current
fleet. Landed history lives in Git. Paths under `docs/archive/` and `docs/decisions/` below name
files removed on 2026-10-03; read one with `git show b78a031:<path>`.

## Item contract

Every roadmap item carries:

| Field | Meaning |
|---|---|
| ID | Stable identifier used by plans and decision records |
| Status | `ready`, `active`, `blocked`, `deferred`, or `decision-needed` |
| Outcome | The observable result, not a list of files |
| Source | The decision, review, or specification that established the work |
| Prerequisites | Gates that must land first |
| Constraints | Operator rulings and do-not lines that bind this item, one line each |
| Acceptance | Evidence required to close the item |
| Next action | The smallest safe step that moves it forward |

An item leaves this file when its acceptance evidence is committed; Git history retains the
implementation detail.

Small items (the `Small items` section under Current work) are the deliberate exception: one
line carrying only ID, the observable fix, and source — the tier that keeps tiny defects in this
single tracker instead of leaking into memory or issue lists.

## Current work

### Ready

#### DESIGN-001 — consolidate design ownership

**Status:** `active` — operator-approved merger on `refactor/consolidate-design-ownership`, from main
`8486439`; local implementation, no host installation or publication.

**Outcome:** One principal agent owns system design and strategic architecture, with conditional
depth and preserved builder ownership, document authority, and host controls.

**Source:** Design-agent merger (`docs/decisions/2026-09-07-design-agent-merge.md`).

**Prerequisites:** Regenerated adapters, current inventories, offline validation, and independent
review of the surviving authority and routing contracts.

**Constraints:** Keep principal's name; preserve the rejected branch and unrelated work. Do not
treat source-following exercises as native routing or enforcement evidence.

**Acceptance:** Offline checks pass; system/strategic/consult outcomes preserve the decision
contract; paired ladder and proportionality routing and the native hook probe have fresh evidence
with any failures or inconclusive criteria explicitly dispositioned before publication.

**Evidence disposition:** The 2026-09-08 outcome trials (`docs/archive/2026-09/agent-outcomes-2026-09-08/README.md`)
passed both system and both strategic repetitions. Both embedded consults had a material partial:
compromised deployment-access recovery in one, and CA-rollover validation order in the other.
The source-following architecture aggregate does not pass; no source correction or native
activation claim is implied by these observations.

**Next action:** Resolve the two consult gaps and rerun the unchanged outcome cases. Verify Claude
authentication, capture the untouched main baseline and final candidate under the decision's
identical routing conditions, and run the native hook probe. Keep host synchronization and
publication separate from this source-level evidence.

#### MACH-001 — rebuild the fleet machinery on one kernel

**Status:** `active` — the decision record was accepted 2026-09-13 after phase 0 merged (PR #187).
Phase 1 (rules, policy, findings, CLI, rosters as data) merged in PR #188; phase 2 (host
projections as a counted rewrite table, the verified Codex TOML emitter, `--diff`) is implemented
on `claude/machinery-rewrite-fresh-ar08n6` and merged as PR #189. Phase 3 (probes and doctor on
the kernel, `hypothesis` property tests, PROBE-006 closed) is implemented on the same branch,
restarted from `main`. Phase 4 (routing evals handed to `claude plugin eval`, the verdict kept
fleet-side, provenance moved onto the kernel) merged as PR #191. Phase 5 (`hooks/hooks.json`
rendered from the guard and gate rosters by `fleet/hooks.py` and byte-checked by the adapter
generator) is implemented on the same branch, restarted from `main`. All five phases are then
implemented. The lint ratchet held 27 file entries suppressing 147 findings (counted 2026-09-14
by removing the table and re-running `ruff check .`; an earlier figure of "12 file entries" in
this item was wrong). It is now **three entries, all `E501`, and none of them a backlog** — the
reason for each is beside it in `pyproject.toml`.

**Outcome:** Every maintainer instrument under `scripts/` runs on the `fleet/` kernel with one
implementation per primitive, policy held as data, structured findings, and the routing runner
retired to native `claude plugin eval`; the hooks stay single-file and dependency-free.

**Source:** Machinery rewrite decision (`docs/decisions/2026-09-13-machinery-rewrite.md`).

**Prerequisites:** Phase order as the record states; phase 4 additionally needs CI's CLI at
≥ 2.1.269 (it now floats on latest) with a probe re-run on that CLI, and one live native eval run.

**Constraints:** No runtime dependency in `fleet/`; hooks never import it; each phase keeps the
generated adapters byte-identical and every existing verdict unchanged unless its PR records the
change; the routing runner is not wired onto the kernel before it retires (provenance hole).

**Phase 4's fleet-side verdict and provenance were removed 2026-10-03.** A paired
`prompt-tooling` batch (36 runs) graded the same traces both ways and the native `regex`
grader agreed on every run, so `claude plugin eval` now grades as well as runs, and
`fleet/routing.py`, `fleet/provenance.py`, `scripts/eval_clean_room.py`, and the stored
baselines went with their tests.

**Acceptance:** Per phase, the oracle named in the record's phase table, plus green tiers.
**Amended by operator ruling on 2026-09-14**: the criterion was "the lint ratchet table in
`pyproject.toml` is empty"; it is now "every remaining entry states why it is exempt". MACH-001
therefore closes when the phase-5 PR merges. Adding a fourth entry still owes the same
justification — this is not a reopened backlog.

All three are ruled permanent, and none of them is a cleanup anyone skipped:

- `scripts/probe_plugin.py` — its long lines live inside the triple-quoted prompt and workflow
  source the probe sends to a live model. A physical line inside a triple-quoted string cannot
  carry a `noqa`, and rewrapping it changes the stimulus, so the recorded probe evidence would no
  longer describe the same measurement. The exemption is permanent and the entry is
  documentation, not debt.
- `scripts/readonly-guard.py` and `scripts/live-effect-gate.py` — 11 long lines between them, all
  comments and code rather than emitted bytes, so all reflowable with no behavior change. But
  editing either is a hook change under `AGENTS.md`'s hook playbook and owes a
  `scripts/probe_plugin.py` run. Spending that run to rewrap comments in the fleet's security
  boundary is the wrong trade, for the same reason `[tool.ruff.format]` already excludes the hook
  scripts — so the exemption is permanent and no probe is owed for it.

**Evidence disposition:** The specifier claim was re-probed on 2.1.270 on 2026-09-13 (three
runs; the specifier restricts nothing, the validator's rule stands) and the CI pin moved to
2.1.270 with the probe re-run — pin refresh evidence (`docs/archive/2026-09/pin-refresh-evidence-2026-09-13.md`).

**Phase 5 found a live defect in the check it replaces.** The validator's `plugin.hooks.gate`
cross-check took the *last* `case` block as the gate's no-interpreter fallback. The gate nests a
`case "$IN"` inside that fallback to separate a prompt-suppressed session from an interactive one,
and the nested block names `homelab-engineer` only inside an English denial reason — so the rule
was reading prose as a roster. Measured: replacing the gate's real `case "$SQ"` roster with a name
that gates nobody left `validate_fleet.py` at exit 0 and `tests.test_fleet_rules` green; only
`tests/test_hook_wiring.py`, which executes the shell string, caught it (11 failures). The rule now
selects each block by the variable that opened it, with the mutation pinned in
`tests/test_fleet_hooks.py`. The shipped hook was never wrong; the check was.

**Next action:** Open the phase-5 PR (`fleet/hooks.py` renders both roster copies from the hook
scripts' own constants; `hooks/hooks.json` joins the generator's byte-checked outputs as a
standalone `GENERATED_FILES` entry rather than a deletable root; the gate cross-check defect above
is fixed). **The probe is not run for this phase, and the reason is on the record**: the shipped
`hooks/hooks.json` is byte-identical to the file the last probe ran against (3,035 bytes), so a
run would re-prove an existing fact, which proportionality forbids. What changed is where those
bytes come from, and byte-identity is the stronger evidence for that than a live session would
be. The next probe — owed before the next release — is the first to exercise a machine-produced
hook file, and that is the run to read carefully. Then the ratchet.

#### LABFLOW-001 — simplify the homelab operating path

**Status:** `active` — the operator selected main-review items 1, 2, 3, 5, and 6 on 2026-09-07;
implementation is on `refactor/homelab-operating-flow`. Offline checks and bounded behavior probes
passed; two static review rounds ended with no remaining material findings. The full runtime probe
retains its recorded coverage gaps. Publication is authorized; host installation is outside scope.

**Outcome:** Routine work keeps useful evidence and ownership without mandatory Learning forms,
digest receipts, repeated approval proposals, or unrelated builder preloads.

**Source:** Operating-flow decision (`docs/decisions/2026-09-07-homelab-operating-flow.md`) and
2026-09-12 proportional controls (`docs/decisions/2026-09-12-proportional-homelab-controls.md`).

**2026-09-12 follow-up:** Items 1–8 are implemented on `fix/proportional-homelab-controls` after
base `10b6131d2605`: proportional verification/snapshots, optional live-effect interposition,
operating triage, and review-policy corrections. Offline and scenario checks passed; independent
review has no remaining material findings. The three native hook checks could not execute because
Claude OAuth expired. Evidence (`docs/archive/2026-09/proportional-controls-evidence-2026-09-12.md`)
retains exact coverage and source identities; no installed-state claim is made.

**Prerequisites:** Main-based implementation; existing host permission controls and roster retained.

**Acceptance:** Canonical/adapter parity, focused and full offline checks, reviewed final diff,
paired source-following outcome probes, and a revised runtime probe with its observed limits.

**Next action:** Refresh Claude authentication and rerun the affected native hook checks on the
identified source. Reconcile publication state before any subsequent PR work; this local follow-up
did not inspect or change hosted PRs or installations.

#### CTX-001 — modernize fleet definitions for Claude 5-generation context rules

**Status:** `ready` — eval-gated experiment; the harness it needs already exists.

**Outcome:** The fleet's 31 canonical definitions are audited against six published Claude
5-generation context shifts, and any edit is justified by paired before/after routing evidence, or
recorded as not transferring.

**Source:**
AI graph engineering decision (`docs/decisions/2026-07-31-ai-graph-engineering.md`) ·
2026-07-31 independent review (`docs/archive/2026-07/graph-decision-independent-review-2026-07-31.md`)

**Prerequisites:** EVAL-003's agent-member grading decision; one pilot definition before any
fleet-wide edit. EVAL-003 itself still describes a pinned behavioral suite as part of that
design — the behavioral harness retired 2026-09-02, so this item's acceptance below no longer
requires one.

**Acceptance:** For every edited definition: paired before/after routing runs under identical
recorded conditions, no negative-case regression, a written stop rule if the pilot regresses,
regenerated adapters, deterministic gates green. No contract-graded check remains; the probe and
a routing round are the available instruments.

**Next action:** Open a bounded spec choosing the pilot definition (`sde-fullstack` is the
highest-density candidate) and the exact paired-measurement conditions before editing anything.

#### CTX-003 — verify the implemented preload cut

**Status:** `active` — narrowed on 2026-09-07 to remaining verification of LABFLOW-001.
The old instruction to compact a routine closeout contract into `self-improve-loop` is retired:
that skill is explicit-only maintainer work and is no longer a per-spawn consumer.

**Outcome:** Establish the evidence still owed for the implemented conditional preload, without
repeating the cut or restoring automatic learning scans.

**Source:**
operating-flow implementation and limits (`docs/decisions/2026-09-07-homelab-operating-flow.md`)

**Evidence disposition:** Adapter regeneration and validator parity passed. The bounded native
builder capture demonstrated the requested preload/read/absence canaries; scorer regressions are
covered by deterministic tests. Retro-boundary and continuous-improvement routing were measured,
but they do not substitute for every affected agent's before/after routing. A complete green
runtime probe, remaining affected-agent routing, and per-skill before/after preload byte deltas
are still owed. Doctor listing-budget and installed-agent drift warnings remain open; no host
installation or warning waiver is implied by publication of LABFLOW-001. The 2026-09-13 probe on
CLI 2.1.270 FAILED the conditional-reference check once (the builder wrote an API client without
reading `references/consuming-apis.md`), while the three preload canaries were inconclusive —
evidence (`docs/archive/2026-09/pin-refresh-evidence-2026-09-13.md`); a single run, not a rate. Both
checks were removed from the probe on 2026-10-03, so no instrument now measures builder preload or
conditional-reference reads; "a complete green runtime probe" here means the guard and loading
checks only.

**Next action:** Compare the existing LABFLOW-001 evidence with those remaining checks, bind any
new measurement to immutable before/after plugin bytes, and run only the missing checks. Do not
edit the explicit-only retro skill to reduce preload cost or treat an unrun check as accepted.

#### CTX-004 — lock the context wins in: settings lines, validator promotion, Copilot cap

**Status:** `ready` — pass 3 of three. The validator-promotion step is gated on ROSTER-001: the
roster cut that closed CTX-002 never landed, and the listing measures ~9,174 characters against
the 8,000-character assumption, so a hard rule would fail today.

**Outcome:** Three locks: a calibrated `skillListingBudgetFraction` in lab repositories'
settings, the doctor's listing-budget warning promoted to a hard validator rule, and a
generated-adapter size tripwire ahead of GitHub's 30,000-char cap.

**Source:**
2026-08-16 skill-listing investigation (`docs/archive/2026-08/skill-listing-investigation-2026-08-16.md`)

**Prerequisites:** ROSTER-001 for the validator promotion; the settings lines and the
Copilot-cap tripwire have none.

**Acceptance:** Settings lines landed with each environment's live-probe calibration; the
promoted validator rule with a failing fixture; the Copilot-cap tripwire with a firing test;
regenerated adapters; green tiers.

**Next action:** Ship the Copilot-cap tripwire first — prerequisite-free, small, and its
measurement is already committed evidence.

#### ROSTER-001 — land or retire the 2026-09-02 roster cut

**Status:** `decision-needed` — the audience ruling implies a 5-agent, 16-skill roster, but the
cut was never tracked or landed, and the later design-agent merger assumes `eng-ladder` survives.
CTX-002, closed on 2026-09-02 as met by construction, is reopened here: the construction never
happened.

**Outcome:** The shipped roster matches the audience ruling, or the ruling is amended to the
roster that ships, and the Claude skill listing fits the 8,000-character budget at 200k context.

**Source:** Single-operator audience decision (`docs/decisions/2026-09-02-single-operator-audience.md`) ·
design-agent merger (`docs/decisions/2026-09-07-design-agent-merge.md`).

**Prerequisites:** None.

**Constraints:** The audience stays one home-lab operator. Reconcile `eng-ladder` with the
design-agent merger before deleting it. If `eng-ladder` is kept, LADDER-002's won't-do reason
("the roster cut deletes it") lapses: reopen LADDER-002 or re-justify it. A description edit in
the surviving roster owes routing evals.

**Acceptance:** `agents/` and `skills/` match the ruled roster; `fleet_doctor.py`'s
`repository.skill-listing-budget` passes; routing clusters for removed components are retired;
green tiers.

**Next action:** Operator rules on `eng-ladder` (delete per the audience ruling, or keep it and
amend that ruling's roster); then open the cut from main.

#### LABSEC-002 — add a guard-enforced lab inspector

**Status:** `ready` — Option A accepted 2026-07-31; normal-session probes proved registration,
denial, and exclusion.

**Outcome:** Add an optional read-only agent working the hygiene (`lab-audit`) or adversary
(`security-audit`) checklist under guard enforcement, with no change authority or web access;
this item is purely the enforcement shell.

**Source:**
roster expansion design (`docs/archive/2026-07/roster-expansion-design.md`)

**Prerequisites:** None — LABSEC-001, DEPLOY-001, GOV-001, EVAL-001 landed.

**Acceptance:** The agent has no write or web tools; every added allowlisted command is
read-only by tested verb/flag policy; the plugin probe proves the guard fires for the exact
roster and ignores the main session; routing preserves `homelab-engineer`'s outage/change
authority.

**Next action:** Open a bounded spec/plan, starting with the smallest read-only command surface
and a threat review of every new verb/flag.

#### LANE-001 — Codex-lane onboarding discoverability

**Status:** `ready` — spec approved 2026-08-09; host-neutral packaging landed in PR #107, but no
round is running and no Codex host evidence exists yet.

**Outcome:** On a Codex session with the fleet installed, plain-language onboarding intent
yields a model recommendation of the explicit workflow, never implicit execution, with the
Claude lane's measured routing rates unaffected.

**Source:**
[LANE-001 spec](superpowers/specs/lane-001-codex-onboarding-discoverability.md)

**Prerequisites:** The spec's Phase 0 (two SEC-01 one-liners), still blocking; waiving it takes
an operator-approved spec amendment.

**Acceptance:** The spec's list: Phase 0's one-liners (or amendment); the paired `homelab-ops`
before/after capture at merge base `4fef0ce`; a recorded Codex smoke run against a released
artifact, filed through the ledger's release/retest rule.

**Next action:** Operator runs the two Phase-0 one-liners on the SEC-01 Linux host, then
captures the paired routing run; the smoke run follows the next release.

#### GATE-007 — bind a tier to each declared effect, or say one response carries one tier

**Status:** `ready` — review-reported on PR #164; not fixed there because the fix is a
vocabulary decision, not a lint change.

**Outcome:** A response declaring two effects can no longer leave the more dangerous one
unclassified, closing the gap where a Tier 3 deletion could pass a safety eval declared only as
Tier 2.

**Source:**
homelab live-effect gate decision (`docs/decisions/2026-08-29-homelab-live-effect-gate.md`)

**Prerequisites:** GATE-006 (landed) — this amends what that decision established.

**Constraints:** The behavioral harness that would have re-measured either fix, and EVAL-011 (the
item that would have gated whether such a re-measure meant anything), both retired 2026-09-02; a
routing round and `scripts/probe_plugin.py` are the remaining paid instruments, though neither
measures tier-effect binding directly. `packet_lint.py`'s `EFFECT_SET_LABELS` check, which either
option below would have extended, retired 2026-09-02 with the harness — the linter half of this
item is moot; only the agent-text half remains.

**Acceptance:** Either (a) `Tier` joins each bound effect set, with agent text and adapters
changed together; or (b) the agent text states one response carries one tier. Neither option has
a linter or contract check behind it anymore — the closing commit records the choice either way.

**Next action:** Decide (a) or (b); both change what the agent emits. Verify with a routing round
and the probe; no contract-graded re-measure is available.

#### DIALECT-001 — the frontmatter reader strips quotes instead of parsing the scalar

**Status:** `decision-needed` — found by the phase-3 property tests over `fleet/frontmatter.py`;
latent today. The only next action is choosing between two incompatible parser policies, and
neither has been selected, so this is an operator choice rather than work underway (the same shape
as PORT-002 above). Marking it `active` would tell a later stateless session that someone is
already on it.

**Outcome:** `parse_lines` reads a quoted scalar with `value.strip("'\"")` — a crude strip of
quote characters from both ends, not a scalar parser. Two consequences share that one cause:

- It never decodes YAML's double-quoted escapes, while the hosts that load the definitions do.
  `yaml_scalar('say "hi"')` is read back by the fleet as `say \"hi\"` and by a host as
  `say "hi"`. 25 generated frontmatter values carry such an escape today, all of them descriptions
  containing a quoted phrase (`.github/agents/code-reviewer.agent.md` is the clearest).
- It strips ANY quote character repeatedly, so the emitted `"say 'hi'"` reads back as `say 'hi`:
  a trailing apostrophe in a description is silently lost.

Both are **latent**, and the claim is checkable rather than asserted: nothing in the fleet compares
a description read back from a generated file against its canonical source, which is the only
place the two readings would meet. The boundary is pinned by
`test_a_value_carrying_no_quote_or_escape_round_trips_exactly`, so the day something does compare
them, that test still says exactly how far the round trip holds.

**Acceptance:** Either a real double-quoted scalar reader (decode the escapes YAML defines, strip
only the delimiter that actually opened the value), with every rule's verdict re-checked against
the corpus; or a recorded decision that the dialect's subset excludes quoted scalars, enforced by
a rule that refuses one in a canonical file. Not both, and not neither.

**Next action:** Decide which of the two the dialect is. The fix is not urgent, but it must not
stay undecided: the reader and the hosts disagree today, and only the absence of a comparison
keeps that from mattering.

#### PORT-002 — second mining round from save-toolkit, the sibling's delta since 2026-07-24

**Status:** `decision-needed` — scoping read done and recorded; operator picks the set before
any graft is authored.

**Outcome:** Lab-portable improvements from `latent-sre/save-toolkit` since the July import land
as capped grafts inside the skills that already own the ground, with no twin this fleet leads on
touched and provenance recorded twice.

**Source:**
save-toolkit delta scoping (`docs/archive/2026-08/save-toolkit-delta-scoping-2026-08-29.md`) ·
sre-agents adaptation backlog (`docs/archive/2026-07/sre-agents-adaptation-backlog.md`)

**Prerequisites:** The operator's pick (Next action); each slice then runs PORT-001's three
blind passes from refreshed `origin/main`.

**Constraints:** No description edit is planned; if one becomes necessary it owes the routing
cluster before/after.

**Acceptance:** Per slice: graft lands inside the owning skill; the scrub list is gone from
landed text; validator and tests green; commit carries attribution, every adapted code file
names its source and license, and the commit message records the reviewed donor commit and
renamed repository; verified-skip twins stay byte-unchanged. Closes when every picked slice
merges.

**Next action:** Operator chooses (a) the recommended five candidates, (b) all eight, or (c) (b)
plus filing the PROP-003/EVAL leads as their own items; then open slice 1 (`runbook`).

### Small items

The deliberate lightweight tier: defects and gaps too small for the full item contract, so they
do not leak into session memory or issue lists as a shadow queue. One line each — ID, the
observable fix, and source. No prerequisites and no acceptance section: the fix plus green
deterministic gates closes a line, and closing it means deleting it. A line that turns out to
need prerequisites or acceptance evidence beyond itself graduates to a full item above. A line
naming a GitHub issue **is** that issue's roadmap import under `docs/README.md` rule 7.

- **HOST-012** — Installing this repository as a VS Code plugin loads the canonical Claude
  fleet, which is unsupported. Source: [README.md](../README.md).
- **PROBE-002** — Settled 2026-08-30 as a real, intermittent craft-preload failure (2 passes, 3
  failures across five runs); not caused by GATE-006. The probe check that observed it was
  removed 2026-10-03, so the failure is now unmeasured rather than fixed. Source:
  GATE-006 outcome (`docs/archive/2026-08/gate-006-outcome-2026-08-30.md`).

## Deferred decisions

#### GRAPH-004 — typed edge-contract pilot

**Status:** `deferred` — trigger-bound, absorbed from the superseded control-plane proposal.

**Outcome:** One real handoff (builder to reviewer) expressed as a host-neutral typed contract,
with `contract_digest` resolving to it.

**Source:**
GRAPH-003 adjudication (`docs/archive/2026-08/graph-003-adjudication-2026-08-01.md`) ·
AI graph engineering decision (`docs/decisions/2026-07-31-ai-graph-engineering.md`)

**Prerequisites:** A demonstrated consumer — a second workflow conversion decided.

**Acceptance:** The contract document exists, `contract_digest` resolves to it with a test, the
workflow (if any) consuming it validates against it, and no judgment text lives outside
canonical files.

**Next action:** None until a trigger fires — a second workflow conversion is the only live
ignition.

#### EVAL-003 — decide how agent-member routing positives are graded

**Status:** `active` — narrowed 2026-10-03. Stored captures and their reuse contract were removed
with `evals/baselines/`, and every before-side is now a fresh run, so the comparable anchor this
item was opened for is no longer needed; the grading decision below remains.

**Outcome:** One recorded ruling on whether routing positives for agent members stay graded or
are retired.

**Source:** this roadmap; earlier detail is in Git history.

**Prerequisites:** Run small watched foreground batches; fix case-design defects before treating
numbers as description evidence.

**Acceptance:** The ruling is recorded here and the affected cases are changed to match it.

**Next action:** Make the agent-member grading decision, now with evidence rather than a default.
The full 2026-09-14 capture (10 clusters, 101 cases, 303 runs, since deleted) split cleanly:
negatives **60/60**; positives 26/41, where **14 of the 15 failures involve no
wrong destination** (11 routed nowhere, 3 fired only expected members below the 0.5 threshold) and
the fifteenth dispatched a member its case does not expect in all three runs — ROUTE-001 below,
which this record must not round off to under-firing. That is the shape the deferred default
predicted, so decide whether routing positives for agent members stay graded or are retired
(the behavioral suite that was a third option retired 2026-09-02) — and record the ruling here. Until then, read this capture's
positive side as a reachability signal, not as description evidence.

#### ROUTE-001 — settle `pos-diagnose-idle-lab-failure`: `root-cause` or `homelab-engineer`

**Status:** `active` — a case and the fleet disagree about a destination, consistently.

**Outcome:** One recorded ruling on where "monitoring found a stopped container, nobody affected,
find out why it exited" belongs, and the case or the description changed to match it.

**Source:** the 2026-09-14 full routing capture (since deleted) — the case fired
`homelab-engineer` in 3/3 runs and `root-cause` in 1/3, while asserting `root-cause`. Not a
silence failure like the other fourteen: the sessions routed somewhere, deliberately and
repeatably. A 2026-08-18 native pilot recorded the same destination 6/6 under that agent's
previous name (`homelab-platform`), so the behaviour long predates the harness migration.

**Prerequisites:** None.

**Acceptance:** Either the case's `expect_fires` names the destination the fleet actually chooses
and says why in `expected_output`, or `root-cause`'s description is changed to win this prompt and
the overlapping cluster is re-run before and after per the description playbook. A rate that moves
because the case was rewritten to match observed behaviour is not evidence of improved routing,
and the ruling must say which of the two happened.

**Next action:** Read the prompt against both descriptions and decide which is wrong — the
assertion or the description. Do not treat this as a rate to improve until that is settled.

#### RELEASE-001 — add repository release discipline

**Status:** `deferred`

**Outcome:** On the next release-workflow task, add a bounded component for version choice,
changelog, tag, publication, and rollback, without absorbing merge verdicts, CI authoring, or
deployment authority.

**Source:**
roster expansion design (`docs/archive/2026-07/roster-expansion-design.md`)

**Prerequisites:** A real plugin or repository release task demonstrates the consumer.

**Acceptance:** Routing cases distinguish release, CI, deploy, and merge-verdict requests; the
component states rollback boundaries; its first use performs the repository's actual version,
inventory, validation, tag, and publication sequence.

**Next action:** Reopen before the next manually orchestrated release; start from `claude plugin
tag --dry-run` and build around what it does not cover.

#### EVAL-004 — verify the accessibility imports behaviorally

**Status:** `deferred`

**Outcome:** Demonstrate that a real UI task loads and applies form wiring or interaction
accessibility guidance and supplies keyboard-pass evidence.

**Source:**
ECC import review (`docs/archive/2026-07/ecc-import-review.md`)

**Prerequisites:** A real task involving a form, modal, drawer, custom widget, toast, or async
status.

**Constraints:** Do not manufacture a component solely to close this item.

**Acceptance:** Task packet names the applicable reference and provides keyboard/announcement
evidence; two observed misses trigger a dedicated behavioral contract and definition repair.

**Next action:** Evaluate on the next qualifying UI task.

#### LAB-001 — provide a fallback service compose asset

**Status:** `deferred`

**Outcome:** Supply an annotated service block for a lab with no established compose pattern,
covering pinned image, restart, health, resource, and storage slots.

**Source:**
skills modernization plan (`docs/archive/2026-07/skills-modernization-plan.md`)

**Prerequisites:** An onboarding task demonstrates the target lab lacks a reusable pattern.

**Constraints:** Existing lab conventions always win over this asset.

**Acceptance:** Asset is linked skill-relative from `service-onboard`, contains no
environment-specific defaults, and the validator's orphan/reference checks pass.

**Next action:** Reopen on the first qualifying service-onboarding task.
