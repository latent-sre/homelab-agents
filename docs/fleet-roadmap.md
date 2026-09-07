# Fleet roadmap

> **Status: live.**
> This is the only document that tracks unfinished, blocked, or explicitly deferred fleet work.
> Reviews, decision records, and execution plans supply rationale and implementation detail; they
> do not independently add work to the queue.

This file will contain only unfinished, blocked, or explicitly deferred work for the current
fleet. Landed implementation history and donor-by-donor adjudication belong in `docs/archive/`;
architecture decisions and rejected alternatives belong in `docs/decisions/`.

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

An item leaves this file when its acceptance evidence is committed. The source decision remains;
Git history and archived reviews retain the implementation detail.

Small items (the `Small items` section under Current work) are the deliberate exception: one
line carrying only ID, the observable fix, and source — the tier that keeps tiny defects in this
single tracker instead of leaking into memory or issue lists.

Every item below was cut to these fields on 2026-09-01; the narration, dated addenda, and
round-by-round detail removed in that pass live verbatim in
[`roadmap-history-2026-09-01.md`](archive/2026-09/roadmap-history-2026-09-01.md), linked from
each item's Source.

## Current work

### Ready

#### CTX-001 — modernize fleet definitions for Claude 5-generation context rules

**Status:** `ready` — eval-gated experiment; the harness it needs already exists.

**Outcome:** The fleet's 31 canonical definitions are audited against six published Claude
5-generation context shifts, and any edit is justified by paired before/after routing evidence, or
recorded as not transferring.

**Source:**
[AI graph engineering decision](decisions/2026-07-31-ai-graph-engineering.md) ·
[2026-07-31 independent review](archive/2026-07/graph-decision-independent-review-2026-07-31.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ctx-001-modernize-fleet-definitions-for-claude-5-generation-context-rules)

**Prerequisites:** EVAL-003's grading design (negatives, clean-room); one pilot definition before
any fleet-wide edit. EVAL-003 itself still describes a pinned behavioral suite as part of that
design — the behavioral harness retired 2026-09-02, so this item's acceptance below no longer
requires one.

**Acceptance:** For every edited definition: paired before/after routing runs under identical
recorded conditions, no negative-case regression, a written stop rule if the pilot regresses,
regenerated adapters, deterministic gates green. No contract-graded check remains; the probe and
a routing round are the available instruments.

**Next action:** Open a bounded spec choosing the pilot definition (`sde-fullstack` is the
highest-density candidate) and the exact paired-measurement conditions before editing anything.

#### CTX-003 — shrink the per-spawn preload footprint without hollowing the probe's proof

**Status:** `ready` — pass 2 of three; heaviest pass, runs when there is appetite for a routing
round plus a probe re-run per affected agent.

**Outcome:** Per-spawn preload cost drops measurably (e.g. `sde-fullstack`'s ~12.1k preloaded
tokens), with a routing round and the probe showing slimmed bodies still deliver what fat ones
did — the behavioral contracts that once proved this retired 2026-09-02; references stay the
on-demand layer.

**Source:**
[2026-08-16 skill-listing investigation](archive/2026-08/skill-listing-investigation-2026-08-16.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ctx-003-shrink-the-per-spawn-preload-footprint-without-hollowing-the-probes-proof)

**Prerequisites:** None mechanically; `scripts/probe_plugin.py`'s craft canaries must move
deliberately with the body, or stay in it.

**Constraints:** The conditional-reference read is measured intermittent (falsified 2026-08-30) —
re-verify it before shrinking anything into the on-demand layer.

**Acceptance:** Before/after routing runs for every agent whose preloaded set changed; probe
green with canary assertions intact or deliberately migrated; regenerated adapters; doctor and
validator green; byte deltas recorded per skill. No contract-graded check remains.

**Next action:** Restructure `self-improve-loop` first — compact loop plus closeout contract in
SKILL.md, full lifecycle protocol to a reference.

#### CTX-004 — lock the context wins in: settings lines, validator promotion, Copilot cap

**Status:** `ready` — pass 3 of three; CTX-002 closed 2026-09-02 (the roster cut fits the
budget), so the promotion step is no longer gated.

**Outcome:** Three locks: a calibrated `skillListingBudgetFraction` in lab repositories'
settings, the doctor's listing-budget warning promoted to a hard validator rule, and a
generated-adapter size tripwire ahead of GitHub's 30,000-char cap.

**Source:**
[2026-08-16 skill-listing investigation](archive/2026-08/skill-listing-investigation-2026-08-16.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ctx-004-lock-the-context-wins-in-settings-lines-validator-promotion-copilot-cap)

**Prerequisites:** None — CTX-002 closed 2026-09-02.

**Acceptance:** Settings lines landed with each environment's live-probe calibration; the
promoted validator rule with a failing fixture; the Copilot-cap tripwire with a firing test;
regenerated adapters; green tiers.

**Next action:** Ship the Copilot-cap tripwire first — prerequisite-free, small, and its
measurement is already committed evidence.

#### CTX-005 — shrink `homelab-engineer`'s always-loaded body

**Status:** `decision-needed` — one authorized safety repair and one behavioral round are spent;
the branch is no-go evidence, not merge-ready.

**Outcome:** The safety repair improved fresh behavior (45/125 to 55/125, new safety case 5/5)
but regressed three baseline-perfect contracts to 4/5 (60/130 overall); acceptance still fails.

**Source:**
[Homelab proportional operations decision](decisions/2026-08-23-homelab-proportional-operations.md) ·
[CTX-005 discipline audit](archive/2026-08/ctx-005-engineering-discipline-audit-2026-08-23.md) ·
[GATE-006 outcome](archive/2026-08/gate-006-outcome-2026-08-30.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ctx-005-shrink-homelab-engineers-always-loaded-body)

**Prerequisites:** GATE-006 (landed). Its after-side lane cannot serve as this diet's before
side — a fresh baseline must be captured.

**Constraints:**
- EVAL-011 closed won't-do 2026-09-02 with the behavioral harness it would have gated this item
  through; the biased-rate concern it named cannot be resolved by re-measuring, since no
  contract-graded instrument remains. Verify with a routing round and the probe instead, and note
  that neither measures the inspect-first discipline the always-loaded body carries as directly as
  a behavioral contract did.
- Do not mix another policy change into the diet.

**Acceptance:** Before/after character counts under the same instrument; a routing round shows no
regression on affected homelab clusters; probe stays green; adapters match sources; the outcome
names what was removed, compressed, or kept and why. No contract-graded check remains.

**Next action:** No further review-driven bytes or capture retries are planned; a later ruling
reopening work restarts root-cause analysis from refreshed main.

#### LABSEC-002 — add a guard-enforced lab inspector

**Status:** `ready` — Option A accepted 2026-07-31; normal-session probes proved registration,
denial, and exclusion.

**Outcome:** Add an optional read-only agent working the hygiene (`lab-audit`) or adversary
(`security-audit`) checklist under guard enforcement, with no change authority or web access;
this item is purely the enforcement shell.

**Source:**
[roster expansion design](archive/2026-07/roster-expansion-design.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#labsec-002-add-a-guard-enforced-lab-inspector)

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
[LANE-001 spec](superpowers/specs/lane-001-codex-onboarding-discoverability.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#lane-001-codex-lane-onboarding-discoverability)

**Prerequisites:** The spec's Phase 0 (two SEC-01 one-liners), still blocking; waiving it takes
an operator-approved spec amendment.

**Acceptance:** The spec's list: Phase 0's one-liners (or amendment); the paired `homelab-ops`
before/after capture at merge base `4fef0ce`; a recorded Codex smoke run against a released
artifact, filed through the ledger's release/retest rule.

**Next action:** Operator runs the two Phase-0 one-liners on the SEC-01 Linux host, then
captures the paired routing run; the smoke run follows the next release.

#### ACK-001 — make a dropped Learning handoff visible

**Status:** `decision-needed` — gap twice-observed; candidate mechanisms differ in size and
authority, so the operator chooses before any spec.

**Outcome:** A Learning packet the caller does not persist becomes visibly unpersisted, instead
of looking identical to a persisted one.

**Source:**
Issue #73 ·
[LOOP-001 outcome](archive/2026-08/loop-001-outcome-2026-08-10.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ack-001-make-a-dropped-learning-handoff-visible)

**Prerequisites:** None — LOOP-001's capture-to-released lifecycle closed 2026-08-10.

**Constraints:** `scripts/learning_ledger.py` and the `learning/` store were retired 2026-09-01;
this item is moot unless the ledger returns.

**Acceptance:** A scenario where a caller receives a packet and stops shows the stop; the
emitting side's contract is unchanged for callers that do route it; no new write authority
granted to a read-only role; adapter parity and deterministic gates green.

**Next action:** Operator rules among three mechanisms (emitter-side pointer plus manifest —
recommended; caller-side lint scan — deferred, trigger-bound; scratch-file write — declined),
then a bounded spec.

#### LEDGER-001 — the promoted set has no absorption or drift coverage

**Status:** `ready` — diagnosis complete from a full 53-record audit; each repair below is
independently landable.

**Outcome:** A lesson recorded as `promoted` is one a reader can trust landed, verified by
something other than manual audit; three specific records are reconciled with the tree, and the
coverage gap that hid them is closed or stated.

**Source:**
[history](archive/2026-09/roadmap-history-2026-09-01.md#ledger-001-the-promoted-set-has-no-absorption-or-drift-coverage)

**Prerequisites:** None. Findings 1 and 2 landed 2026-08-20; findings 3–4 remain.

**Constraints:** `scripts/learning_ledger.py` and the `learning/` store were retired 2026-09-01;
this item is moot unless the ledger returns.

**Acceptance:** Findings 1–2 land their prose with the required reader check, or drop with a
stated reason. Finding 3 records its narrowing. Finding 4 extends drift coverage to terminal
states with a firing test, or states the limitation in `learning/README.md`.

**Next action:** Finding 3 — scope-narrow `lc_36adb3d0` or renew its `review`. Finding 4 —
extend drift coverage to terminal states or document the limitation.

#### GATE-007 — bind a tier to each declared effect, or say one response carries one tier

**Status:** `ready` — review-reported on PR #164; not fixed there because the fix is a
vocabulary decision, not a lint change.

**Outcome:** A response declaring two effects can no longer leave the more dangerous one
unclassified, closing the gap where a Tier 3 deletion could pass a safety eval declared only as
Tier 2.

**Source:**
[homelab live-effect gate decision](decisions/2026-08-29-homelab-live-effect-gate.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#gate-007-bind-a-tier-to-each-declared-effect-or-say-one-response-carries-one-tier)

**Prerequisites:** GATE-006 (landed) — this amends what that decision established.

**Constraints:** The behavioral harness that would have re-measured either fix, and EVAL-011 (the
item that would have gated whether such a re-measure meant anything), both retired 2026-09-02; a
routing round and `scripts/probe_plugin.py` are the remaining paid instruments, though neither
measures tier-effect binding directly. `packet_lint.py`'s `EFFECT_SET_LABELS` check, which either
option below would have extended, retired 2026-09-02 with the harness — the linter half of this
item is moot; only the agent-text half remains.

**Acceptance:** Either (a) `Tier` joins each bound effect set, with agent text and adapters
changed together; or (b) the agent text states one response carries one tier. Neither option has
a linter or contract check behind it anymore — the decision record gains the amendment either way.

**Next action:** Decide (a) or (b); both change what the agent emits. Verify with a routing round
and the probe; no contract-graded re-measure is available.

#### PORT-002 — second mining round from save-toolkit, the sibling's delta since 2026-07-24

**Status:** `decision-needed` — scoping read done and recorded; operator picks the set before
any graft is authored.

**Outcome:** Lab-portable improvements from `latent-sre/save-toolkit` since the July import land
as capped grafts inside the skills that already own the ground, with no twin this fleet leads on
touched and provenance recorded twice.

**Source:**
[save-toolkit delta scoping](archive/2026-08/save-toolkit-delta-scoping-2026-08-29.md) ·
[sre-agents adaptation backlog](archive/2026-07/sre-agents-adaptation-backlog.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#port-002-second-mining-round-from-save-toolkit-the-siblings-delta-since-2026-07-24)

**Prerequisites:** The operator's pick (Next action); each slice then runs PORT-001's three
blind passes from refreshed `origin/main`.

**Constraints:** No description edit is planned; if one becomes necessary it owes the routing
cluster before/after.

**Acceptance:** Per slice: graft lands inside the owning skill; the scrub list is gone from
landed text; validator and tests green; commit carries attribution, every adapted code file
names its source and license, and the dated adjudication record is extended with the reviewed
commit and renamed repository; verified-skip twins stay byte-unchanged. Closes when every
picked slice merges and the record is linked from `docs/README.md`.

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
  fleet, which is unsupported. Source: [README.md](../README.md);
  [history](archive/2026-09/roadmap-history-2026-09-01.md#host-012-vs-code-plugin-install-loads-the-canonical-fleet).
- **GATE-008** — Diagnostic false-prompt correction is implemented on `fix/homelab-diagnostic-gate`;
  offline checks and direct native read/deny checks passed; PR review and merge remain. Source:
  [2026-09-07 correction evidence](archive/2026-09/diagnostic-gate-2026-09-07.md).
- **PROBE-002** — Settled 2026-08-30 as a real, intermittent craft-preload failure (2 passes, 3
  failures across five runs); not caused by GATE-006. Source:
  [GATE-006 outcome](archive/2026-08/gate-006-outcome-2026-08-30.md);
  [history](archive/2026-09/roadmap-history-2026-09-01.md#probe-002-craft-preload-canaries-missing-in-sde-fullstack-spawn).
- **PROBE-006** — A probe leg timeout raises `TimeoutExpired` instead of recording INCONCLUSIVE,
  discarding every later check. Source:
  [GATE-006 outcome](archive/2026-08/gate-006-outcome-2026-08-30.md);
  [history](archive/2026-09/roadmap-history-2026-09-01.md#probe-006-a-probe-leg-timeout-crashes-instead-of-recording-inconclusive).
  The [2026-09-07 diagnostic correction](archive/2026-09/diagnostic-gate-2026-09-07.md) uses the
  operator's 600-second limit; timeout recovery remains separate and reproduced at that limit.

## Deferred decisions

#### GRAPH-004 — typed edge-contract pilot

**Status:** `deferred` — trigger-bound, absorbed from the superseded control-plane proposal.

**Outcome:** One real handoff (builder to reviewer) expressed as a host-neutral typed contract,
with `contract_digest` resolving to it.

**Source:**
[GRAPH-003 adjudication](archive/2026-08/graph-003-adjudication-2026-08-01.md) ·
[AI graph engineering decision](decisions/2026-07-31-ai-graph-engineering.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#graph-004-typed-edge-contract-pilot)

**Prerequisites:** A demonstrated consumer — a second workflow conversion decided.

**Acceptance:** The contract document exists, `contract_digest` resolves to it with a test, the
workflow (if any) consuming it validates against it, and no judgment text lives outside
canonical files.

**Next action:** None until a trigger fires — a second workflow conversion is the only live
ignition.

#### EVAL-003 — capture a comparable full routing anchor

**Status:** `deferred`

**Outcome:** Establish one current, condition-complete routing baseline across all routing
clusters.

**Source:**
[history](archive/2026-09/roadmap-history-2026-09-01.md#eval-003-capture-a-comparable-full-routing-anchor)

**Prerequisites:** Run small watched foreground batches; fix case-design defects before treating
numbers as description evidence.

**Acceptance:** Every artifact records requested/observed model, timeout, CLI version,
threshold, and per-run evidence; no known-invalid artifact is called an anchor.

**Next action:** Decide agent-member grading (evidence-backed default: negatives-only in
routing, agent contracts covered by the behavioral suite), then capture the anchor under
`--clean-room`.

#### RELEASE-001 — add repository release discipline

**Status:** `deferred`

**Outcome:** On the next release-workflow task, add a bounded component for version choice,
changelog, tag, publication, and rollback, without absorbing merge verdicts, CI authoring, or
deployment authority.

**Source:**
[roster expansion design](archive/2026-07/roster-expansion-design.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#release-001-add-repository-release-discipline)

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
[ECC import review](archive/2026-07/ecc-import-review.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#eval-004-verify-the-accessibility-imports-behaviorally)

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
[skills modernization plan](archive/2026-07/skills-modernization-plan.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#lab-001-provide-a-fallback-service-compose-asset)

**Prerequisites:** An onboarding task demonstrates the target lab lacks a reusable pattern.

**Constraints:** Existing lab conventions always win over this asset.

**Acceptance:** Asset is linked skill-relative from `service-onboard`, contains no
environment-specific defaults, and the validator's orphan/reference checks pass.

**Next action:** Reopen on the first qualifying service-onboarding task.

## Reconciliation record

Reconciled against commit `ab896b2` on 2026-07-28: every item a historical document still called
open was checked against current definitions, scripts, eval cases, and inventory. Detail lives in
each source below, not here; every "Survives" finding is already tracked live above (LAB-001,
EVAL-003, EVAL-004, LABSEC-002, RELEASE-001) or, for LABSEC-001, recorded landed in LABSEC-002.

- **Quality and deep-review findings** — nearly all landed:
  [`archive/2026-07/fleet-quality-review.md`](archive/2026-07/fleet-quality-review.md).
- **Modernization and adaptation items** — landed except LAB-001, EVAL-003 above:
  [`archive/2026-07/skills-modernization-plan.md`](archive/2026-07/skills-modernization-plan.md).
- **ECC residue** — landed except EVAL-004 above:
  [`archive/2026-07/ecc-import-review.md`](archive/2026-07/ecc-import-review.md).
- **Role and governance review** — all six candidates landed:
  [`decisions/2026-07-28-fleet-role-expansion.md`](decisions/2026-07-28-fleet-role-expansion.md).
- **Roster-expansion design branch** — landed/rejected except LABSEC-002, RELEASE-001 above:
  [`archive/2026-07/roster-expansion-design.md`](archive/2026-07/roster-expansion-design.md).
