# Roadmap item history — extracted 2026-09-01

**State:** Historical record. This document is not a task list. Only docs/fleet-roadmap.md can
import work from it.

**Extracted revision:** `9191d8033b82130526e690da129142520a238e5e`

On 2026-09-01 `docs/fleet-roadmap.md` was cut to its contract fields to bring the file under
budget; everything removed from that pass to make room lives here verbatim, organized by the
roadmap item and field it came from.

## LEARN-002 — close the Learning-contract compliance gap

**Closed 2026-09-02 by operator ruling (won't-do).** Every contract this item measured belongs to `self-improve-loop`, which leaves the shipped fleet under the single-operator audience decision; the paid batch and the deferred envelope ruling were never bought. Decision: `../../decisions/2026-09-02-single-operator-audience.md`.

### Status narration
the measured residual of the merged LEARN-001 round, plus the six LOOP-001/REV-001 contracts this
docket now owns. The 2026-08-15 paired round landed the three canonical text repairs and both
halves' three-run baselines. The 2026-08-17 offline round then worked every sub-item that does not
need a paid session: the filed grader defects are repaired against the sentences that exposed
them, the runner enforces `allowed_tools: []` and stops grading a resultless session as a contract
failure, and the reference/skill grammar conflict is gone. **Nothing in that round is measured.**
What remains under **Next action** is the paid half — one batch that settles the repairs, the
two-consecutive-batch clause, the unmeasured skill sentences — plus one operator ruling. Read that
list, not this sentence, before scoping the item: a headline is not an inventory, and this one has
already been wrong twice by lagging the list beneath it.

### Outcome
(1) Each of the seven behavioral contracts failing 0/3 under the final closed graders
(`self-improve-lifecycle-merge`, `self-improve-promotion-gate`,
`self-improve-canonical-triaged-candidate`, `runbook-disposition-propose`,
`learning-slot-readonly-agent`, `learning-slot-operational-agent`,
`learning-runbook-namespaces`) either holds 3/3 across two consecutive clean-room sonnet batches
or has its grammar amended with a recorded rationale — settling empirically whether the closed
contracts or the skill text carried the defect. No grader is silently loosened.
(2) Each of the six contracts the closed LOOP-001/REV-001 round authored
(`loop-capture-is-not-closure`, `loop-duplicate-merges-provenance`,
`loop-source-pass-is-not-released-pass`, `reviewer-approval-does-not-transfer`,
`verifier-envelope-mismatch-fails-closed`, `reviewer-formal-approval-emits-envelope`) has a
three-run clean-room baseline under recorded conditions and either holds its acceptance rate
or has a grammar/text repair with a recorded rationale — the first-contact single runs in
`evals/baselines/history/2026-08-10-learn-002.md` are diagnostic only and do not close this
half. Closing the original seven without settling these six is not closing LEARN-002.

### Source
live rates in `evals/baselines/2026-08-01-self-improve/final-live/`; the six contracts' first
contact and ownership handoff in the LOOP-001 and REV-001 outcome records.

### Prerequisites
the behavioral harness and pinned conditions are ready. Description edits, if any emerge, owe the
overlapping routing cluster before/after per standing law.

### Acceptance
Per-contract behavioral runs under identical recorded conditions for the original
seven; deterministic gates green; the two 2/3-flaky contracts re-measured alongside; the
watch-metrics (Learning-slot `none`-rate, ledger organic-candidate count) reported at close. The
paired-run clause is satisfied by a single batch on the current tree for every contract whose
repair was grader-side: both sides of such a pair would run the same session text through the same
graders, so a 'before' capture under the repaired graders measures nothing the 'after' does not.
A contract whose repair is TEXT still owes a genuine pair. **And**, for each of the six
LOOP-001/REV-001 contracts: a three-run clean-room baseline under recorded conditions committed
under `evals/baselines/`, plus either a hold at the acceptance rate or a grammar/text repair with
rationale — first-contact single runs and deferred repairs do not satisfy this clause.

### Dated addenda — 2026-08-19 settling batch
**2026-08-19 settling batch — first half spent; read
`evals/baselines/2026-08-19-settling/decisions.md` before scoping anything here.** Confirmed:
`learning-slot-readonly-agent` 3/3 and `self-improve-canonical-triaged-candidate` 3/3 (first of
the two consecutive clean batches each needs). Expected reds behaved as predicted (items 2 and
3, unchanged and still owed). Four new grader defects found and repaired offline in the same
change (producer live-apply x2, re-enable-swap, parsed-membership). Four contracts
(`loop-capture`, `loop-duplicate`, `loop-source-pass`, `reviewer-approval-does-not-transfer`)
failed 0/3 on **fresh paraphrases of plainly compliant conduct** — the third consecutive round
in which repairing exposed sentences minted new misses. **New operator fork:** widen the
vocabularies once more, or redesign those four contracts' grammars structurally (the
`researcher-unestablished-claim` co-location precedent). `verifier-envelope-mismatch-fails-closed`
is now measured genuinely tool-denied and cannot complete by construction (all three sessions
died reaching for the identity check its own method mandates) — decide: grant its one read-only
command via the proven `--allowedTools` mechanism, or stipulate the check in the fixture. The
settling directory's decisions.md carries its own retirement trigger — its benchmarks are the
second batch's 'before' side.

### Next action (narration)
**One paid batch, and one operator ruling.** Every offline repair this docket
owed is landed and pinned in both directions (see the numbered list below); none of it is
measured, and the settling runs are T3. The batch to buy: the seven original contracts plus the
five unsettled LOOP/REV ones, under recorded conditions on the current tree, with
`learning-runbook-namespaces-compose` re-checked first for its n=3 drop and the decorated-echo
repair confirmed across **all four** contracts it touches rather than the one it was filed under.
Two cases have no repair to confirm and are expected to stay red until their owners move —
`reviewer-formal-approval-emits-envelope` (item 3, operator ruling deferred 2026-08-17) and
`learning-slot-operational-agent` (item 2, a TEXT repair not yet written). Do not diff the result
against the 2026-08-15 artifacts: evaluator bytes moved, so that round is history, not the before
side. The historical account below is retained because it is what the repairs were written from.

### Dated addenda — repair ledger and rides
The 2026-08-10 and 2026-08-15 calibration rounds landed and settled the pattern-setter question
for the original seven — closed contracts right, skill text carried the defect — then shipped
three text repairs (`Learning:` value grammar, `Provenance:` triad-first grammar, add-vs-merge)
that moved the two measured assertions 0/9 → 9/9 and 1/9 → 9/9. Full numbers and per-case
decisions: [`2026-08-10-learn-002`](../../../evals/baselines/history/2026-08-10-learn-002.md) and
[`2026-08-15-learn-002`](../../../evals/baselines/history/2026-08-15-learn-002.md). **The six
LOOP-001/REV-001 contracts now have their three-run clean-room baselines on both sides**,
superseding their first-contact single runs — but that satisfies only the *baseline* half of
their Acceptance clause. The clause also requires each of the six to hold its acceptance rate or
receive a repair with rationale, and five of the six do neither yet, so the clause as written is
**not** met.

What this item still owes. The 2026-08-17 offline round closed the repair half of items 1, 2, 5,
6, 8 and 9; each entry below now states what was done and what is still owed, because a repair
with no measurement behind it is a hypothesis, not a result.

**What the offline round changed, and what that costs.** Full record, including the reasoning for
the three ORACLE small items this round closed (005, 006, 007 — their roadmap lines are deleted,
as a closed small item's are), the ten graded-pattern and four `packet_lint` repairs, and their
paired mutation-proof tests:
[`learn-002-offline-repairs-2026-08-17`](../2026-08/learn-002-offline-repairs-2026-08-17.md).
Two consequences a later session must not miss: **the 2026-08-15 rates are no longer the before
side for anything here** (evaluator bytes moved; the next batch is a fresh baseline), and
**several cases now measure something different** because item 6 made `allowed_tools: []` actually
deny — a rate change there is a true finding about a no-tool session, not a regression.

1. **Five grader defects repaired offline; confirmation owed across all four contracts the
   decorated-echo repair touches** (`self-improve-lifecycle-merge`,
   `self-improve-canonical-triaged-candidate`, `learning-slot-operational-agent`'s duplicate
   `Learning:` field, and the one it was filed under) — validating only the filed-under contract
   would read as settled while three others still fail on it. Repair mechanics: the offline-repairs
   record above.
2. **`learning-slot-readonly-agent`'s grader defect is repaired** (rationale after an exact-value
   field is now allowed). **`learning-slot-operational-agent`'s duplicate-`Learning:`-field cause
   is TEXT, not grader — repair not yet written** (still 1/3; a real back-reference-vocabulary
   problem, not a paraphrase gap). The `(proposed recommendation)` abbreviation this item once
   carried does **not** occur in any of the six after-side runs; do not revive it.
3. **An operator ruling on `reviewer-formal-approval-emits-envelope`** — whether stipulated
   evidence substitutes for seen bytes. Not a grammar problem, and unchanged at 0/3. Put to the
   operator on 2026-08-17 and **deferred**, so the contract stays red and the ruling stays owed.
   The choice is three-way: the case is wrong and the refusal is correct conduct (an instrument
   defect, as LADDER-002's assess 0/3 turned out to be); the agent should approve, which is a
   shipped-behavior change to `agents/code-reviewer.md`'s bind-to-bytes rule; or it approves with
   the stipulation labelled, which needs both an agent clause and a case amendment.
4. **The two-consecutive-batches clause** for the seven, which no single round can satisfy.
   `learning-runbook-namespaces-compose`'s 3/3 → 2/3 drop is dispositioned as variance at n=3 and
   is the first thing the next batch re-checks.
5. **Five of the six LOOP-001/REV-001 contracts have repairs; each still owes a hold.**
   `loop-capture-is-not-closure` 0/3, `loop-duplicate-merges-provenance` 0/3,
   `loop-source-pass-is-not-released-pass` 1/3 (its second pattern — whether the ledger's literal
   `record-retest` may be replaced by a mechanism description — is deliberately untouched; that
   design question stays undecided, and the literal is what makes the ledger step actionable; do
   not widen it without settling that), `reviewer-approval-does-not-transfer` 0/3 (item 1), and
   `reviewer-formal-approval-emits-envelope` 0/3 (item 3, unrepaired pending the ruling). The
   sixth, `verifier-envelope-mismatch-fails-closed`, held 3/3 — but that pass was measured with
   `Glob`/`Grep` reachable and the case is now genuinely tool-denied (item 6), so its next run
   measures a different thing and the 3/3 does not carry forward. Repair mechanics: the
   offline-repairs record above.
6. **`allowed_tools: []` now denies** — the runner used to turn an empty allowlist into
   `--tools ""`, which bounds nothing; 47 of the suite's cases declared one, and 42 had a tool
   still reachable. Fixed once, for all 47, in `eval_behavioral.session_denylist` (mechanics:
   offline-repairs record above). **Still owed:** the MCP half — `RUNTIME_TOOLS` is built-ins
   only, so `researcher-unestablished-claim-stays-unverified` keeps MCP retrieval reachable and
   says so in its own `expected`; closing it needs a probed `mcp__…` denial vocabulary or a grader
   assertion on observed tool calls, since an unprobed denylist entry would be a control in name
   only.
7. **Two SKILL.md sentences plus item 9's reference repair ship unmeasured.** Both measured
   assertions (`0/9 → 9/9`, `1/9 → 9/9`) remain evidence only for the byte-identical `c8312b3`
   text — full pin detail in
   [`2026-08-15-learn-002`](../../../evals/baselines/history/2026-08-15-learn-002.md). Two
   review-driven amendments landed after that pin with **no** behavioral evidence: the no-signal
   literal (the live risk — it changes what every no-signal scan emits, and the next batch
   measures it) and the `Destination:` clarification. Item 9's reference repair is unmeasurable by
   this suite **by construction** now that item 6 lands — these cases run fully tool-denied, so no
   session can open a `references/` file; its consumer is a `Read`-capable session in ordinary
   use, not a contract here.
8. **A resultless (`Claude exited 1`) session is now a measurement failure, not a graded FAIL** —
   it had converted three working contracts into apparent 0/3s before this landed. Mechanics:
   offline-repairs record above. **Still owed:** the root cause; the workaround meanwhile is
   `--concurrency 1` for the affected case.
9. **Landed** — `references/retro-protocol.md`'s Provenance template now matches the
   triad-first grammar `packet_lint` and `SKILL.md` require, closing the two-canonical-files
   contradiction. Detail: offline-repairs record above.

Two results are recorded against interest and must not be re-reported as wins: the add-vs-merge
repair has **no measured effect** (its target case was already 3/3 before the edit, on model
drift), and two contracts improved between 2026-08-10 and this round on drift alone.

**Rides this item (PROP-002 deferrals, 2026-08-13).** Three proportionality trims sit in files
this item already pays to re-measure, so they ride its runs instead of buying their own — full
list, file paths, and rationale in
[`prop-002-scan-findings-2026-08-13.md`](../2026-08/prop-002-scan-findings-2026-08-13.md).
Optional to this item's acceptance, but must not be made *without* its measurement, and
**closing this item owes each ride-along a disposition** (worked, re-homed to a named live item,
or dropped with reason) — a silent close would strand them in archive evidence outside this
tracker, the only live owner a deferral can have (PR #133 review finding). Note the constraint
that record's Correction 8 establishes before touching `runbook`: its propose grammar cannot move
to `references/`, because the contract that grades it runs skill-only and has no `Read`.

### Original fields (pre-cut)
**Status:** `ready` — the measured residual of the merged LEARN-001 round, plus the six
LOOP-001/REV-001 contracts this docket now owns. The 2026-08-15 paired round landed the three
canonical text repairs and both halves' three-run baselines. The 2026-08-17 offline round then
worked every sub-item that does not need a paid session: the filed grader defects are repaired
against the sentences that exposed them, the runner enforces `allowed_tools: []` and stops
grading a resultless session as a contract failure, and the reference/skill grammar conflict is
gone. **Nothing in that round is measured.** What remains under **Next action** is the paid half
— one batch that settles the repairs, the two-consecutive-batch clause, the unmeasured skill
sentences — plus one operator ruling. Read that list, not this sentence, before scoping the
item: a headline is not an inventory, and this one has already been wrong twice by lagging the
list beneath it.

**Outcome:** (1) Each of the seven behavioral contracts failing 0/3 under the final closed
graders (`self-improve-lifecycle-merge`, `self-improve-promotion-gate`,
`self-improve-canonical-triaged-candidate`, `runbook-disposition-propose`,
`learning-slot-readonly-agent`, `learning-slot-operational-agent`,
`learning-runbook-namespaces`) either holds 3/3 across two consecutive clean-room sonnet
batches or has its grammar amended with a recorded rationale — settling empirically whether
the closed contracts or the skill text carried the defect. No grader is silently loosened.
(2) Each of the six contracts the closed LOOP-001/REV-001 round authored
(`loop-capture-is-not-closure`, `loop-duplicate-merges-provenance`,
`loop-source-pass-is-not-released-pass`, `reviewer-approval-does-not-transfer`,
`verifier-envelope-mismatch-fails-closed`, `reviewer-formal-approval-emits-envelope`) has a
three-run clean-room baseline under recorded conditions and either holds its acceptance rate
or has a grammar/text repair with a recorded rationale — the first-contact single runs in
`evals/baselines/history/2026-08-10-learn-002.md` are diagnostic only and do not close this
half. Closing the original seven without settling these six is not closing LEARN-002.

**Source:** [`LEARN-001 outcome record`](../2026-08/learn-001-outcome-2026-08-02.md);
live rates in `evals/baselines/2026-08-01-self-improve/final-live/`; the six contracts' first
contact and ownership handoff in the
[LOOP-001](../2026-08/loop-001-outcome-2026-08-10.md) and
[REV-001](../2026-08/rev-001-outcome-2026-08-10.md) outcome records.

**Prerequisites:** None — the behavioral harness and pinned conditions are ready. Description
edits, if any emerge, owe the overlapping routing cluster before/after per standing law.

**Acceptance:** Per-contract behavioral runs under identical recorded conditions for the original
seven; deterministic gates green; the two 2/3-flaky contracts re-measured alongside; the
watch-metrics (Learning-slot `none`-rate, ledger organic-candidate count) reported at close. The
paired-run clause is satisfied by a single batch on the current tree for every contract whose
repair was grader-side: both sides of such a pair would run the same session text through the same
graders, so a 'before' capture under the repaired graders measures nothing the 'after' does not.
A contract whose repair is TEXT still owes a genuine pair. **And**, for each of the six
LOOP-001/REV-001 contracts: a three-run clean-room baseline under recorded conditions committed
under `evals/baselines/`, plus either a hold at the acceptance rate or a grammar/text repair with
rationale — first-contact single runs and deferred repairs do not satisfy this clause.

**Next action:** **One paid batch, and one operator ruling.** Every offline repair this docket
owed is landed and pinned in both directions (see the numbered list below); none of it is
measured, and the settling runs are T3. The batch to buy: the seven original contracts plus the
five unsettled LOOP/REV ones, under recorded conditions on the current tree, with
`learning-runbook-namespaces-compose` re-checked first for its n=3 drop and the decorated-echo
repair confirmed across **all four** contracts it touches rather than the one it was filed under.
Two cases have no repair to confirm and are expected to stay red until their owners move —
`reviewer-formal-approval-emits-envelope` (item 3, operator ruling deferred 2026-08-17) and
`learning-slot-operational-agent` (item 2, a TEXT repair not yet written). Do not diff the result
against the 2026-08-15 artifacts: evaluator bytes moved, so that round is history, not the before
side. The historical account below is retained because it is what the repairs were written from.


## CTX-001 — modernize fleet definitions for Claude 5-generation context rules

### Status narration
eval-gated experiment; the harness it needs already exists.

### Source
measurement basis (~190 prohibition-style lines across the fleet, `sde-fullstack` leading at 24)
in the 2026-07-31 independent review.

### Prerequisites
EVAL-003's grading evidence governs the measurement design: agent-expecting
routing positives under-fire in headless mode, so grade with negatives, clean-room conditions, and
the pinned behavioral suite. One pilot definition before any fleet-wide edit.

### Next action (narration)
Open a bounded spec choosing the pilot definition (`sde-fullstack` is the
highest-density candidate) and the exact paired-measurement conditions before editing anything.
Named audit material from the 2026-08-09 estate feedback: the Learning-bullet specification is
~9 of 15 packet bullet-lines in each of 11 always-loaded definitions for a field whose ordinary
value is one line — a compression candidate gated on the pinned learning-slot behavioral
contracts holding.

### Original fields (pre-cut)
**Status:** `ready` — eval-gated experiment; the harness it needs already exists.

**Outcome:** The fleet's 31 canonical definitions are audited against the six published shifts for
Claude 5-generation models (rules→judgment, examples→interface design, upfront→progressive
disclosure, repetition→tool definitions, manual memory→auto-memory, simple specs→rich references),
and any edit is justified by paired before/after routing and behavioral evidence — or the audit
records that the published claim did not transfer to this artifact class.

**Source:** Revised
[`AI graph engineering decision`](../../decisions/2026-07-31-ai-graph-engineering.md) (accepted work),
grounded in the 2026-07-24 context-engineering rules; measurement basis (~190 prohibition-style
lines across the fleet, `sde-fullstack` leading at 24) in the
[`2026-07-31 independent review`](../2026-07/graph-decision-independent-review-2026-07-31.md).

**Prerequisites:** EVAL-003's grading evidence governs the measurement design: agent-expecting
routing positives under-fire in headless mode, so grade with negatives, clean-room conditions, and
the pinned behavioral suite. One pilot definition before any fleet-wide edit.

**Acceptance:** For every edited definition, paired before/after runs under identical recorded
conditions with no negative-case regression and behavioral contracts green; a written stop rule if
the pilot regresses; regenerated adapters and the deterministic gates green.

**Next action:** Open a bounded spec choosing the pilot definition (`sde-fullstack` is the
highest-density candidate) and the exact paired-measurement conditions before editing anything.
Named audit material from the 2026-08-09 estate feedback: the Learning-bullet specification is
~9 of 15 packet bullet-lines in each of 11 always-loaded definitions for a field whose ordinary
value is one line — a compression candidate gated on the pinned learning-slot behavioral
contracts holding.


## CTX-002 — fit the model-visible skill listing inside the 8,000-char host budget

**Closed 2026-09-02 by operator ruling (met by construction).** The roster cut's 16 model-visible skills measure 6,946 characters against the 8,000-character budget without a description edit, so no paired routing run is owed; the doctor's headroom check is run in the roster PR. Decision: `../../decisions/2026-09-02-single-operator-audience.md`.

### Status narration
pass 1 of the three-pass context remediation (CTX-002 listing layer,
CTX-003 invocation layer, CTX-004 environment and enforcement); passes 1 and 3 share no files
with pass 2 and may run independently of it.

### Outcome (narration)
Bundled skills are budget-exempt and charged first, so
trimming alone cannot guarantee full survival where the bundled share is large (measured
~5.5–6k chars in the investigation container: a ~3.9k-char trimmed listing still lost 8 of 18
descriptions at the default budget) — the settings-side completion and the enforcement
promotion are CTX-004's remit, gated on this trim landing first.

### Source
(CLI 2.1.233 binary constants; live listing state by model; behavioral routing A/B — the
`continuous-improvement` positive fired 0/2 with a bare name and 2/2 with the description
restored; mitigation calibration — fraction 0.02 measured partial, 0.05 full; trim simulation).
Platform facts recorded in `skills/prompt-craft/references/claude-code-frontmatter.md`; the
LADDER-002 investigation's "full description visible at 2.1.231 despite ~11k listing volume"
observation is explained by the window scaling — that probe ran on a large-window model.

### Prerequisites
none — but every description edit owes the standing paired routing-eval
discipline, so the work batches naturally with any LADDER-002 repairs the operator buys.

### Acceptance (narration)
A live listing probe on a
200k-window model after the trim, recording how many entries survive at the default budget —
survivors are maximized here; full survival on bundled-rich hosts closes in CTX-004.

### Dated addenda — Evidence capital
**Evidence capital:** `evals/baselines/2026-08-18-ctx-002/` holds this item's paired v4
benchmarks; they are the reusable 'before' sides for the held eng-ladder and onboarding-map
trims and must not be retired while this item or LANE-001 is open — the directory's decisions.md
carries the full retirement trigger.

### Next action (narration)
Trim the three largest entries first — `self-improve-loop` (951-char
description), `deep-review` (~940-char workflow meta description), `onboarding-map` (873) — the
listing needs ~3.9k chars cut. The consuming-repo mitigation available meanwhile is
`skillListingBudgetFraction: 0.05` in `.claude/settings.json` (verified full restoration in the
investigation container; 0.02 measured partial there — calibrate with a live listing probe, not
by assumption).

### Original fields (pre-cut)
**Status:** `ready` — pass 1 of the three-pass context remediation (CTX-002 listing layer,
CTX-003 invocation layer, CTX-004 environment and enforcement); passes 1 and 3 share no files
with pass 2 and may run independently of it.

**Outcome:** The fleet's model-visible listing (non-DMI skills plus workflows, currently ~11.9k
chars across 19 entries) fits the 8,000-char worst-case budget with stated headroom — which
fully fixes Codex (whose 8,000 budget carries no bundled-skill share) and maximizes surviving
entries on 200k-context Claude hosts. Bundled skills are budget-exempt and charged first, so
trimming alone cannot guarantee full survival where the bundled share is large (measured
~5.5–6k chars in the investigation container: a ~3.9k-char trimmed listing still lost 8 of 18
descriptions at the default budget) — the settings-side completion and the enforcement
promotion are CTX-004's remit, gated on this trim landing first.

**Source:** [2026-08-16 skill-listing investigation](../2026-08/skill-listing-investigation-2026-08-16.md)
(CLI 2.1.233 binary constants; live listing state by model; behavioral routing A/B — the
`continuous-improvement` positive fired 0/2 with a bare name and 2/2 with the description
restored; mitigation calibration — fraction 0.02 measured partial, 0.05 full; trim simulation).
Platform facts recorded in `skills/prompt-craft/references/claude-code-frontmatter.md`; the
LADDER-002 investigation's "full description visible at 2.1.231 despite ~11k listing volume"
observation is explained by the window scaling — that probe ran on a large-window model.

**Prerequisites:** none — but every description edit owes the standing paired routing-eval
discipline, so the work batches naturally with any LADDER-002 repairs the operator buys.

**Acceptance:** Paired before/after routing runs for the overlapping clusters of every edited
description (`scripts/eval_baseline.py` may satisfy the 'before' side); doctor check reporting
`pass` with headroom on the trimmed tree; regenerated adapters. A live listing probe on a
200k-window model after the trim, recording how many entries survive at the default budget —
survivors are maximized here; full survival on bundled-rich hosts closes in CTX-004.

**Next action:** Trim the three largest entries first — `self-improve-loop` (951-char
description), `deep-review` (~940-char workflow meta description), `onboarding-map` (873) — the
listing needs ~3.9k chars cut. The consuming-repo mitigation available meanwhile is
`skillListingBudgetFraction: 0.05` in `.claude/settings.json` (verified full restoration in the
investigation container; 0.02 measured partial there — calibrate with a live listing probe, not
by assumption).


## CTX-003 — shrink the per-spawn preload footprint without hollowing the probe's proof

### Status narration
pass 2 of the three-pass context remediation; independent of CTX-002 and
CTX-004, and the heaviest pass (behavioral-contract rounds), so it runs when there is appetite
for that instrument rather than blocking the other two.

### Outcome (narration)
`sde-fullstack`
currently loads ~12.1k tokens of skill bodies (48,317 bytes across five preloads) on top of its
own ~4.9k-token body, and `self-improve-loop` (largest body: 18.1k bytes, 272 lines, ~4.5k
tokens) is preloaded by three agents that already carry the Learning closeout stanza inline —
with behavioral contracts proving the slimmed bodies still deliver what the fat ones did.
References stay the on-demand layer (probe-verified 2026-08-16: conditional reference reads
work; preloading takes the SKILL.md body only). **That verification no longer holds unconditionally
— falsified 2026-08-30.** A probe run on merged `main` reported `[FAIL] sde-fullstack read
references/consuming-apis.md when the task called an upstream API`: the builder wrote an API client
without loading the integration discipline, which is this design's Risk 1 realised. It has now
failed twice and passed twice across the four runs that reached it, so the read is **intermittent**,
not simply broken — and an intermittent conditional read is the worse finding for this item, because
the whole plan rests on references arriving when their predicate trips. Re-verify before shrinking
anything into the on-demand layer; a slimmed body plus a reference that loads two times in three is
a net loss of guidance the fat body delivered every time.

### Source
"Preload and body footprint" — byte counts, the redundancy of the preloaded Learning protocol
against the agents' inline closeout stanzas, and the probe-canary constraint.

### Prerequisites (narration)
none mechanically — but the probe-canary constraint is a design decision
inside the pass, not an accident to stumble into: `scripts/probe_plugin.py` asserts craft-skill
canary content is *preloaded* by quoting it from the body, so a body-to-reference move either
keeps the canaries in the body or moves them deliberately with a probe update in the same
change. A silent move fails the probe — or worse, quietly hollows out what "preloaded" proves.

### Acceptance (narration)
Byte deltas recorded per skill in the closing record.

### Next action (narration)
Restructure `self-improve-loop` first — compact loop plus closeout contract in
SKILL.md, full lifecycle protocol to a reference — because it pays three times per fleet-heavy
session and its behavioral contracts (the learning-closeout cases) already exist as the
instrument.

### Original fields (pre-cut)
**Status:** `ready` — pass 2 of the three-pass context remediation; independent of CTX-002 and
CTX-004, and the heaviest pass (behavioral-contract rounds), so it runs when there is appetite
for that instrument rather than blocking the other two.

**Outcome:** The per-spawn context cost of preloading drops measurably — `sde-fullstack`
currently loads ~12.1k tokens of skill bodies (48,317 bytes across five preloads) on top of its
own ~4.9k-token body, and `self-improve-loop` (largest body: 18.1k bytes, 272 lines, ~4.5k
tokens) is preloaded by three agents that already carry the Learning closeout stanza inline —
with behavioral contracts proving the slimmed bodies still deliver what the fat ones did.
References stay the on-demand layer (probe-verified 2026-08-16: conditional reference reads
work; preloading takes the SKILL.md body only). **That verification no longer holds unconditionally
— falsified 2026-08-30.** A probe run on merged `main` reported `[FAIL] sde-fullstack read
references/consuming-apis.md when the task called an upstream API`: the builder wrote an API client
without loading the integration discipline, which is this design's Risk 1 realised. It has now
failed twice and passed twice across the four runs that reached it, so the read is **intermittent**,
not simply broken — and an
intermittent conditional read is the worse finding for this item, because the whole plan rests on
references arriving when their predicate trips. Re-verify before shrinking anything into the
on-demand layer; a slimmed body plus a reference that loads two times in three is a net loss of
guidance the fat body delivered every time.

**Source:** [2026-08-16 skill-listing investigation](../2026-08/skill-listing-investigation-2026-08-16.md),
"Preload and body footprint" — byte counts, the redundancy of the preloaded Learning protocol
against the agents' inline closeout stanzas, and the probe-canary constraint.

**Prerequisites:** none mechanically — but the probe-canary constraint is a design decision
inside the pass, not an accident to stumble into: `scripts/probe_plugin.py` asserts craft-skill
canary content is *preloaded* by quoting it from the body, so a body-to-reference move either
keeps the canaries in the body or moves them deliberately with a probe update in the same
change. A silent move fails the probe — or worse, quietly hollows out what "preloaded" proves.

**Acceptance:** Before/after behavioral-contract runs (`scripts/eval_behavioral.py`) for every
agent whose preloaded set changed; the probe green with its canary assertions intact or
deliberately migrated; regenerated adapters; the doctor and validator green throughout. Byte
deltas recorded per skill in the closing record.

**Next action:** Restructure `self-improve-loop` first — compact loop plus closeout contract in
SKILL.md, full lifecycle protocol to a reference — because it pays three times per fleet-heavy
session and its behavioral contracts (the learning-closeout cases) already exist as the
instrument.


## CTX-004 — lock the context wins in: settings lines, validator promotion, Copilot cap

### Status narration
pass 3 of the three-pass context remediation; the promotion step is gated
on CTX-002, the other two deliverables are not.

### Outcome (narration)
Three locks, one per discovered cliff. (1) Consuming lab repositories carry a
probe-calibrated `skillListingBudgetFraction` line in `.claude/settings.json` (0.05 verified
full in the investigation container; 0.02 measured partial — each environment calibrates by
live listing probe because the bundled share differs). (2) The doctor's
`repository.skill-listing-budget` warning is promoted to a `validate_fleet.py` hard rule with a
fixture that fails without it, so listing regrowth fails T0 instead of failing silently at
runtime — honest only once CTX-002 makes the tree fit. (3) A generated-adapter size tripwire
warns before GitHub's 30,000-character `.agent.md` hard cap — `homelab-engineer.agent.md` is at
24,019 chars (80%, re-measured 2026-08-17) and the fleet's fastest-growing body, so today the
first signal would be a host rejecting the profile. Three small-item review passes there netted
**-39 chars** overall (detail:
[`learn-002-offline-repairs-2026-08-17`](../2026-08/learn-002-offline-repairs-2026-08-17.md))
— nobody measured until the number was asked for, which is the point of the tripwire.

### Source
(mitigation calibration table; the Copilot cap under "Preload and body footprint").

### Prerequisites
CTX-002 for the promotion step only.

### Acceptance (narration)
thresholds stated in the rule's message with the consequence named.

### Next action (narration)
The Copilot-cap tripwire — it is prerequisite-free, small, and the 82%
measurement is already committed evidence.

### Original fields (pre-cut)
**Status:** `ready` — pass 3 of the three-pass context remediation; the promotion step is gated
on CTX-002, the other two deliverables are not.

**Outcome:** Three locks, one per discovered cliff. (1) Consuming lab repositories carry a
probe-calibrated `skillListingBudgetFraction` line in `.claude/settings.json` (0.05 verified
full in the investigation container; 0.02 measured partial — each environment calibrates by
live listing probe because the bundled share differs). (2) The doctor's
`repository.skill-listing-budget` warning is promoted to a `validate_fleet.py` hard rule with a
fixture that fails without it, so listing regrowth fails T0 instead of failing silently at
runtime — honest only once CTX-002 makes the tree fit. (3) A generated-adapter size tripwire
warns before GitHub's 30,000-character `.agent.md` hard cap — `homelab-engineer.agent.md` is at
24,019 chars (80%, re-measured 2026-08-17) and the fleet's fastest-growing body, so today the
first signal would be a host rejecting the profile. Three small-item review passes there netted
**-39 chars** overall (detail:
[`learn-002-offline-repairs-2026-08-17`](../2026-08/learn-002-offline-repairs-2026-08-17.md))
— nobody measured until the number was asked for, which is the point of the tripwire.

**Source:** [2026-08-16 skill-listing investigation](../2026-08/skill-listing-investigation-2026-08-16.md)
(mitigation calibration table; the Copilot cap under "Preload and body footprint").

**Prerequisites:** CTX-002 for the promotion step only.

**Acceptance:** Settings lines landed in the lab repositories with each environment's live-probe
calibration recorded; the promoted validator rule with its failing fixture; the Copilot-cap
tripwire with a test that makes it fire (a synthetic body over threshold), thresholds stated in
the rule's message with the consequence named; regenerated adapters and green tiers.

**Next action:** The Copilot-cap tripwire — it is prerequisite-free, small, and the 82%
measurement is already committed evidence.


## CTX-005 — shrink `homelab-engineer`'s always-loaded body

### Status narration
after the five-round experiment, the operator authorized exactly one
safety repair and one fresh behavioral round. The repair restored the retry-state boundary and its
new negative case passed 5/5, but three baseline-perfect contracts regressed to 4/5. The branch is
no-go evidence only, not a merge-ready result.

### Outcome
The corrected baseline is 27,987 canonical characters, 27,938 in the Copilot
projection (93.1% of its 30,000-character cap), and 28,702 in the Codex projection. The
operator-authorized safety repair (tree-based sizes 24,884 / 24,847 / 25,611; Copilot 17.18%
headroom) improved fresh behavior across the original 25 cases from 45/125 at baseline to 55/125
with the new safety case at 5/5 — but three baseline-perfect contracts regressed to 4/5 (60/130
overall), so acceptance still fails and this is no-go evidence, not a merge-ready result. Two
further review-response rounds fixed deterministic contract defects only (final tree-based sizes
25,347 / 25,310 / 26,074; Copilot 15.63% headroom); **no fresh behavioral lane ran against either
review-response tree**, so neither supersedes the exact-hash 60/130 no-go result or establishes an
accepted compact floor. Full round-by-round sizes, the rejected initial candidate, and every
fixed defect: the CTX-005 discipline audit.

### Source (narration)
whose operator ruling explicitly defers the body reduction to the next round; CTX-004 owns the
separate cap tripwire; and the CTX-005 discipline audit, which records the corpus, consumer
inventory, external lanes, edit rounds, and exact no-go evidence.

### Prerequisites (narration)
GATE-006 landed 2026-08-30 (PR #164, merge `5dda85d`;
[outcome](../2026-08/gate-006-outcome-2026-08-30.md)). **Its after-side lane is NOT available
as this diet's before side** — the lane was deliberately stopped at 20 of 265 sessions, so the
planned baseline does not exist and must be captured fresh. Do not mix another policy change into
the diet.

### Acceptance (narration)
Before/after character counts use the same instrument; every affected homelab
behavioral contract passes in the required fresh lane; the probe and full offline suite stay green;
generated adapters match canonical sources; and the outcome names what was removed, compressed,
or kept because a future session, script, grader, or guard consumes it.

### Next action (narration)
The operator-requested pull request is kept as no-go evidence; neither candidate was
merged as completed CTX-005. The operator's additional edit/model round and the two bounded
review-response rounds are spent; no further review-driven bytes or model capture retries are
planned. If a later ruling reopens work, restarting root-cause analysis from refreshed main and
separating packet serialization reliability from grader-lexicon defects before proposing another
body change remains the recorded approach.

### Original fields (pre-cut)
**Status:** `decision-needed` — after the five-round experiment, the operator authorized exactly one
safety repair and one fresh behavioral round. The repair restored the retry-state boundary and its
new negative case passed 5/5, but three baseline-perfect contracts regressed to 4/5. The branch is
no-go evidence only, not a merge-ready result.

**Outcome:** The corrected baseline is 27,987 canonical characters, 27,938 in the Copilot
projection (93.1% of its 30,000-character cap), and 28,702 in the Codex projection. The
operator-authorized safety repair (tree-based sizes 24,884 / 24,847 / 25,611; Copilot 17.18%
headroom) improved fresh behavior across the original 25 cases from 45/125 at baseline to 55/125
with the new safety case at 5/5 — but three baseline-perfect contracts regressed to 4/5 (60/130
overall), so acceptance still fails and this is no-go evidence, not a merge-ready result. Two
further review-response rounds fixed deterministic contract defects only (final tree-based sizes
25,347 / 25,310 / 26,074; Copilot 15.63% headroom); **no fresh behavioral lane ran against either
review-response tree**, so neither supersedes the exact-hash 60/130 no-go result or establishes an
accepted compact floor. Full round-by-round sizes, the rejected initial candidate, and every
fixed defect:
[CTX-005 discipline audit](../2026-08/ctx-005-engineering-discipline-audit-2026-08-23.md).

**Source:**
[Homelab proportional operations decision](../../decisions/2026-08-23-homelab-proportional-operations.md),
whose operator ruling explicitly defers the body reduction to the next round; CTX-004 owns the
separate cap tripwire; and the
[CTX-005 discipline audit](../2026-08/ctx-005-engineering-discipline-audit-2026-08-23.md),
which records the corpus, consumer inventory, external lanes, edit rounds, and exact no-go evidence.

**Prerequisites:** GATE-006 landed 2026-08-30 (PR #164, merge `5dda85d`;
[outcome](../2026-08/gate-006-outcome-2026-08-30.md)). **Its after-side lane is NOT available
as this diet's before side** — the lane was deliberately stopped at 20 of 265 sessions, so the
planned baseline does not exist and must be captured fresh. Do not mix another policy change into
the diet. **EVAL-011 gates this item**: 25 of the 27 cases in that lane declare `allowed_tools: []`,
and a permission-cut turn is currently scored as a contract failure, so the rates this diet would
cut against measure the harness as well as the prose. Cutting always-loaded body on those numbers
would run the wrong way on purpose — the bias penalises the inspect-first discipline the body exists
to carry, so the passages most likely to look unearned are the safety ones. Re-measure after
EVAL-011, or state in the outcome why a biased instrument was accepted.

**Acceptance:** Before/after character counts use the same instrument; every affected homelab
behavioral contract passes in the required fresh lane; the probe and full offline suite stay green;
generated adapters match canonical sources; and the outcome names what was removed, compressed,
or kept because a future session, script, grader, or guard consumes it.

**Next action:** The operator-requested pull request is kept as no-go evidence; neither candidate was
merged as completed CTX-005. The operator's additional edit/model round and the two bounded
review-response rounds are spent; no further review-driven bytes or model capture retries are
planned. If a later ruling reopens work, restarting root-cause analysis from refreshed main and
separating packet serialization reliability from grader-lexicon defects before proposing another
body change remains the recorded approach.


## LABSEC-002 — add a guard-enforced lab inspector

### Status narration
DEPLOY-001 accepted Option A on 2026-07-31, and normal-session probes proved
namespaced registration, guarded-agent denial, and main-loop exclusion.

### Outcome (narration)
Both checklists now exist — LABSEC-001 landed 2026-07-29 — so this
item is purely the enforcement shell.

### Prerequisites (narration)
Satisfied: LABSEC-001, DEPLOY-001, GOV-001, and EVAL-001 landed. The implementation
must still independently threat-review the proposed reader, regression-test every allowlist
addition, and retain hook/guard roster synchronization.

### Original fields (pre-cut)
**Status:** `ready` — DEPLOY-001 accepted Option A on 2026-07-31, and normal-session probes proved
namespaced registration, guarded-agent denial, and main-loop exclusion.

**Outcome:** Add an optional read-only agent that can work the hygiene (`lab-audit`) or adversary
(`security-audit`) checklist under guard enforcement, without taking change authority or combining
lab secrets with web access. Both checklists now exist — LABSEC-001 landed 2026-07-29 — so this
item is purely the enforcement shell.

**Source:** Archived
[`roster expansion design`](../2026-07/roster-expansion-design.md), reconciled by the role
decision.

**Prerequisites:** Satisfied: LABSEC-001, DEPLOY-001, GOV-001, and EVAL-001 landed. The implementation
must still independently threat-review the proposed reader, regression-test every allowlist
addition, and retain hook/guard roster synchronization.

**Acceptance:** The agent has no write or web tools; every additional allowlisted command is
read-only by tested verb/flag policy; the POSIX plugin probe proves the guard fires for the exact
roster and ignores the main session; routing preserves outage/change authority in
`homelab-engineer`.

**Next action:** Open a bounded spec/plan for the inspector, beginning with the smallest required
read-only command surface and a threat review of every new verb/flag before changing the guard.


## HANDOFF-001 — evidence-bound onboarding handoff packet

**Closed 2026-09-02 by operator ruling (won't-do).** Work Order v1's only consumer was its own eval fixture; the roster cut deletes it from `homelab-engineer` and `sde-fullstack`. For one operator, onboarding is done in place or handed to the builder with the plan file, without a digest. Decision: `../../decisions/2026-09-02-single-operator-audience.md`.

### Status narration
Claude manager-owned amendment authorized by the operator 2026-08-11;
original spec approved 2026-08-09. The REV-001 sequencing condition is met: that round closed
2026-08-10 (outcome record) with the envelope idiom settled — `candidate_sha`/`base_sha`/`tree_oid`
and the six-field approval envelope.

### Source (narration)
issue #60 with three-occurrence recurrence evidence and its field-derived section list.

### Prerequisites (narration)
REV-001's idiom is settled in source (merged in PR #109). The 1.7.3
release stamp is REL-173's evidence, not a gate on this item.

### Acceptance (narration)
The spec's list — issue #60's paired evals plus the three closeout fixtures.

### Dated addenda — Current evidence
**Current evidence.** The 2026-08-11 Terra/medium round (full record:
[`2026-08-11-handoff-001`](../../../evals/baselines/history/2026-08-11-handoff-001.md)) proved the
producer 3/3 but left five strict cases unresolved, triggering this amendment; commit `dc02bed`
replaced the builder echo with manager-owned work-order identity, added a digest-mismatch receipt
and declarative builder fixture, and passed red-before-green, T0, the module, T1, and
`claude plugin validate . --strict` (its evaluator-test counts are stale — re-run T1 rather than
compare against that commit's figure).

The plan's three-session Claude diagnostic then ran (operator-approved `claude-sonnet-5`,
candidate `7074d8d`, CLI 2.1.233; full record:
[`2026-08-15-handoff-001-sonnet5`](../../../evals/baselines/history/2026-08-15-handoff-001-sonnet5.md)).
Only the producer returned a usable result (1/1); both builder cases came back **VOID, not
FAIL** — `scripts/eval_behavioral.py:502` granted the tool *surface* via `--tools` but no
*permission*, so the mandated `python -I` and hash commands never executed
(`hash_command_observed: false`). That VOID is the defect the 2026-08-15 `--allowedTools` fix
(see Next action) targets; the void sessions still showed the functional case's end state graded
`acceptance: PASS` and the digest case's workspace left unchanged with no accept issued on trust.

**2026-08-19 settling batch (first paid round on the repaired graders):** full record in
`evals/baselines/2026-08-19-settling/decisions.md`. The runner-grant fix is proven live —
`handoff-builder-applies-work-order` 2/3 with the mandated command executed and
`acceptance: PASS` in all runs, lifting the VOID — and `handoff-builder-rejects-digest-mismatch`
held its substance in every run (mismatch computed, no trusting accept, workspace unchanged) but
fails only `$`-anchored receipt lines the prompt never states, so it owes either prompt grammar or
labeled-line anchors. The parsed-membership grader miss is settled: `member` vs `membership`,
widened with a control in the same change.

**Salvaged parallel evidence (2026-08-12 arc, landed from branch
`claude/sonnet-testing-cf6bfc`):** three producer batches plus digest diagnostics under
`evals/baselines/2026-08-12-handoff-001-*/` produced the three producer grader repairs now in
`handoff-producer-preserves-discovered-constraints` (pinned in `HandoffProducerGraderRepairsTest`;
rate acceptance folds into this item's paid re-runs). Still open from that arc: the producer's
parsed-membership `must_match` missed at 2/3 in the retained 2026-08-18 rerun
(`2026-08-18-handoff-001-producer-r2-x3`) — the last unexplained miss on that contract — and the
`disable_mlock` forbidden sibling carries the same fixed-width-lookbehind blind spot the
live-apply repair fixed, deliberately left until evidence indicts it. Recorded against interest:
the co-occurrence guard's clause exemption admits `assum\w*`/`fail\w*` clauses, and the parity
requirement skips any sentence carrying a negator even when the assertion itself is affirmative.
The arc's runner half is deliberately **not** ported: main's 2026-08-15 `--allowedTools` fix
supersedes its grant mechanism, its digest-case redesign would move evaluator bytes this item's
pending re-run counts on, and its per-command outcome evidence is EVAL-010. **Retirement
triggers** for the salvaged raw: the producer batches retire once the producer contract settles
green in LEARN-002's second batch; the digest diagnostics retire only after
`handoff-builder-rejects-digest-mismatch` resolves with a written receipt grammar and distilled
outcome summary; the 2026-08-18 rerun capture retires with the producer batches.

### Next action (narration)
The runner grant is **fixed** (2026-08-15): `run_session` now passes `--tools`
for the surface bound its comment argues for **and** `--allowedTools` for permission, with a test
proven to fail without it by mutation; an empty allowlist deliberately gets no permission flag,
since `--tools ""` leaves nothing to permit. T0, the module, T1 (full offline suite), and
`claude plugin validate . --strict` are green. What remains is the paid half: **re-run the two
void cases** — `handoff-builder-applies-work-order` and `handoff-builder-rejects-digest-mismatch`
— under recorded conditions, and confirm the mandated `python -I` commands now execute
(`hash_command_observed: true` is the digest case's tell). **This is not only a HANDOFF-001
repair:** five behavioral cases grant `Bash` (`packet-slots-builder`, `ladder-report-not-absorb`,
`verifier-fails-honestly-no-product-edit`, and the two here), so any stored rate for the other
three may have measured the permission gate rather than the contract and should be re-read before
being cited. The fix moves evaluator bytes and so invalidates comparison with the 2026-08-15
artifacts, the producer result included. Only after the two re-runs are sound should a full paired
capture be proposed. Do not compare Claude results with the archived Terra approximation.

### Original fields (pre-cut)
**Status:** `active` — Claude manager-owned amendment authorized by the operator 2026-08-11;
original spec approved 2026-08-09. The REV-001 sequencing condition is met: that round closed
2026-08-10
([outcome record](../2026-08/rev-001-outcome-2026-08-10.md)) with the envelope idiom
settled — `candidate_sha`/`base_sha`/`tree_oid` and the six-field approval envelope.

**Outcome:** Onboarding work delegates through one manager-owned, digest-bound work order whose
sections carry failed assumptions, verification-method validity, the executable-transport contract,
irreversible postconditions, authority lifetimes, inventory invariants, and secret-safe capture
— the builder returns only an accepted/input-required receipt, and the known-failed-assumption
fixture is graded from resulting state rather than a second prose copy.

**Source:** [`HANDOFF-001 spec`](../../superpowers/specs/handoff-001-onboarding-handoff-packet.md) and
its [paired lean plan](../../superpowers/plans/handoff-001-plan.md);
issue #60 with three-occurrence recurrence evidence and its field-derived section list.

**Prerequisites:** None — REV-001's idiom is settled in source (merged in PR #109). The 1.7.3
release stamp is REL-173's evidence, not a gate on this item.

**Acceptance:** The spec's list — issue #60's paired evals plus the three closeout fixtures.

**Next action:** The runner grant is **fixed** (2026-08-15): `run_session` now passes `--tools`
for the surface bound its comment argues for **and** `--allowedTools` for permission, with a test
proven to fail without it by mutation; an empty allowlist deliberately gets no permission flag,
since `--tools ""` leaves nothing to permit. T0, the module, T1 (full offline suite), and
`claude plugin validate . --strict` are green. What remains is the paid half: **re-run the two
void cases** — `handoff-builder-applies-work-order` and `handoff-builder-rejects-digest-mismatch`
— under recorded conditions, and confirm the mandated `python -I` commands now execute
(`hash_command_observed: true` is the digest case's tell). **This is not only a HANDOFF-001
repair:** five
behavioral cases grant `Bash` (`packet-slots-builder`, `ladder-report-not-absorb`,
`verifier-fails-honestly-no-product-edit`, and the two here), so any stored rate for the other
three may have measured the permission gate rather than the contract and should be re-read before
being cited. The fix moves evaluator bytes and so invalidates comparison with the 2026-08-15
artifacts, the producer result included. Only after the two re-runs are sound should a full paired
capture be proposed. Do not compare Claude results with the archived Terra approximation.


## LANE-001 — Codex-lane onboarding discoverability

### Status narration
spec approved by the operator 2026-08-09, with the design premise
re-verified same-day against upstream HEAD `a16863f8` (skill filtering and spawn-schema
suppression both hold). The host-neutral implementation **landed** in PR #107, merged 2026-08-11 — a
model-visible `onboarding-map` skill with its cluster cases, README lane section, and decision
amendment — and its deterministic gates and adapter parity are green. That is packaging evidence,
not lane evidence: nothing on that branch measures a Codex host, the spec's Phase-0 host evidence
is still outstanding, and `superpowers/plans/` holds no LANE-001 plan, so no round is running.

### Source (narration)
issue #61 (failure layer identified 2026-08-02: skills hard-hidden from the model, agent
delegation v2-suppressed); operator rulings 2026-08-02 (supported-but-limited lane, smallest
mechanism); learning-ledger candidate `lc_c361b3d3`.

### Prerequisites (narration)
the spec's Phase 0, still blocking; the LANE-001 spec owns both
one-liners and their exact form, and its 2026-08-11 amendment note records the one mechanical
change they have had. Read them there rather than from this paraphrase: `codex --version` and the
unmanaged-TOML check, both from the SEC-01 Linux host, with **empty output as the pass** — the
exit status is not the signal, since `grep` returns 1 for no match and 2 for an unreadable path.
That distinction is the point of the amended form: absent directory is a clean pass through the
`-d` guard, while a genuine read error still reaches stderr instead of being silenced into the
same empty output. No codex-cli version has ever been measured on that host. The only Codex CLI
version this repository records from a run is `codex-cli 0.145.0` (2026-07-31 SAFE-001 host
conformance, `evals/baselines/2026-07-31-p0-p1/host-conformance/`). `rust-v0.147.0` is an upstream
GitHub release tag quoted in a researcher packet — `learning/candidates/`, candidate
`lc_9e5728c32b23494296f9bec3881c12d2` — not an observation of any host, and citing it as one is
what let this item read as evidence-backed. Waiving Phase 0 takes an operator-approved spec
amendment, not a roadmap sentence.

### Acceptance (narration)
The spec's list. Three gates are open, all operator-owned:

1. Phase 0's two one-liners from SEC-01, or that spec amendment.
2. The paired `homelab-ops` before/after captures. `eval_baseline.py` returns `STALE` for this
   cluster, so the 'before' side is a fresh capture at merge base `4fef0ce`, not a stored reuse.
3. The recorded Codex smoke run (spec line 92), which must exercise a **released** artifact. The
   last release to record its skill inventory captured 19 skills
   (`evals/baselines/2026-08-10-rel-173/conditions.md`, taken under the pre-correction `1.7.3`
   label) and this map would be the twentieth, so the run waits on the **next release tail** and is
   filed through the ledger's `record-release`/`record-retest` — LOOP-001's rule below, that source
   PASS is never reportable as released-artifact PASS, is exactly this case. Name the version from
   the manifests at that time, not from this entry: the fleet corrected its numbering to the
   `0.7.x` line, so the `1.7.x` labels in older evidence and in the ledger's stored release stamps
   are historical, not a series that continues.

### Next action (narration)
Operator runs the two Phase-0 one-liners on the SEC-01 Linux host, then captures
the paired routing run; the smoke run follows the next release.

### Dated addenda — Rides this item
**Rides this item (PROP-002 deferral, 2026-08-13).** `onboarding-map`'s description restates "this
authorizes nothing" a fourth time; the body's three other copies were reconciled in `eb53758`, but
the description drives routing and this skill sits in the `homelab-ops` cluster whose paired
'before' capture this item owes at merge base `4fef0ce`. Trimming it first would invalidate that
side. The CTX-002 round stored a qualifying capture at
`evals/baselines/2026-08-18-ctx-002/before/homelab-ops/` (merge base differs from `4fef0ce` —
re-verify with `eval_baseline.py` before reuse); that benchmark must outlive this item. Optional to
acceptance; not to be made without the capture — and this item's closeout owes the ride-along a
disposition (worked, re-homed to a named live item, or dropped with reason) rather than a silent
close that strands it in archive evidence.

### Original fields (pre-cut)
**Status:** `ready` — spec approved by the operator 2026-08-09, with the design premise
re-verified same-day against upstream HEAD `a16863f8` (skill filtering and spawn-schema
suppression both hold). The host-neutral implementation **landed** in PR #107, merged 2026-08-11 — a
model-visible `onboarding-map` skill with its cluster cases, README lane section, and decision
amendment — and its deterministic gates and adapter parity are green. That is packaging evidence,
not lane evidence: nothing on that branch measures a Codex host, the spec's Phase-0 host evidence
is still outstanding, and `superpowers/plans/` holds no LANE-001 plan, so no round is running.

**Outcome:** On a Codex session with the fleet installed, plain-language new-service or new-host
intent yields a model recommendation of the explicit onboarding workflow — never an implicit
execution — and the Claude lane's measured routing rates do not regress.

**Source:** [`LANE-001 spec`](../../superpowers/specs/lane-001-codex-onboarding-discoverability.md);
issue #61 (failure layer identified 2026-08-02: skills hard-hidden from the model, agent
delegation v2-suppressed); operator rulings 2026-08-02 (supported-but-limited lane, smallest
mechanism); learning-ledger candidate `lc_c361b3d3`.

**Prerequisites:** the spec's Phase 0, still blocking; the
[LANE-001 spec](../../superpowers/specs/lane-001-codex-onboarding-discoverability.md) owns both
one-liners and their exact form, and its 2026-08-11 amendment note records the one mechanical
change they have had. Read them there rather than from this paraphrase: `codex --version` and the
unmanaged-TOML check, both from the SEC-01 Linux host, with **empty output as the pass** — the
exit status is not the signal, since `grep` returns 1 for no match and 2 for an unreadable path.
That distinction is the point of the amended form: absent directory is a clean pass through the
`-d` guard, while a genuine read error still reaches stderr instead of being silenced into the
same empty output. No codex-cli version has ever been measured on that host. The only Codex CLI
version this repository
records from a run is `codex-cli 0.145.0` (2026-07-31 SAFE-001 host conformance,
`evals/baselines/2026-07-31-p0-p1/host-conformance/`). `rust-v0.147.0` is an upstream GitHub
release tag quoted in a researcher packet — `learning/candidates/`, candidate
`lc_9e5728c32b23494296f9bec3881c12d2` — not an observation of any host, and citing it as one is
what let this item read as evidence-backed. Waiving Phase 0 takes an operator-approved spec
amendment, not a roadmap sentence.

**Acceptance:** The spec's list. Three gates are open, all operator-owned:

**Next action:** Operator runs the two Phase-0 one-liners on the SEC-01 Linux host, then captures
the paired routing run; the smoke run follows the next release.


## LADDER-002 — decide the eng-ladder description round

**Closed 2026-09-02 by operator ruling (won't-do).** `eng-ladder` is deleted in the roster cut, which answers the pending ruling: neither repair is bought, and the `ladder` routing cluster retires with the skill. Decision: `../../decisions/2026-09-02-single-operator-audience.md`.

### Status narration
the diagnosis is done; which repairs (if any) to buy is the operator's ruling.

### Source (narration)
eng-ladder's three modes fired 3/3 (altitude), 0/3 (assess), 0/3 (consult-fork) — diagnosed by the
2026-08-14 investigation: schema cleared by probe, the assess 0/3 is an **eval-case artifact**
(dangling referent in the runner's empty cwd), and the consult-fork 0/3 is provisionally attributed
to **do-the-work bias** — provisional either way, since half (b)'s behavioral port validates the
*verdict's content*, not why the routing positive failed. The Group 4 rescan's upheld Mode 3
finding rides here unchanged.

### Prerequisites (narration)
A fresh 'before' capture is owed — the stored capture no longer resolves.
`eval_baseline.py evals/routing/ladder.json --model sonnet --clean-room` reports
`STALE: diverged on evaluator, plugin` for `evals/baselines/2026-08-14-ladder/benchmark.json`,
verified 2026-08-17 on CPython 3.11.15 — the capture's *own* recorded runtime, so the
runtime is no longer the binding cause. Two identities moved since the capture:
`scripts/eval_clean_room.py` (a `routing_evaluator_paths()` member, edited by `4bddd9d`/`8253f2c`
the day after) and the plugin hash. Reuse remains identity-bound in general — the evaluator
identity does pin the runtime, so another Python would also diverge — but on every host today
this cluster owes a fresh capture, not a reuse. (`evals/baselines/2026-08-11-ladder/`, salvaged
2026-08-19, is a pre-PR#145 historical anchor only — never a 'before'; it retires when this item
closes.)

### Acceptance (full)
For each half the operator elects: (a) **Mode 3 trim** — the rescan's remedy is
description **plus** body: remove the growth-feedback clause from the description and the body's
Mode 3 section in the same delta (a description-only trim would close this item while the
duplicate stateless remit survives in the body). Electing this half is a values call, not a
dead-code removal: review named the candidate reader the upheld finding does not cover — the
human operator, whose own diffs Mode 3 could assess at a ladder bar, a consumer neither
`self-improve-loop` nor `prompt-engineer` serves — so the ruling weighs that route's worth
against its per-session description surface. **The cluster could not witness this trim, and now can**:
`evals/routing/ladder.json` carried no Mode 3 growth-feedback positive, so a paired run on those
cases would have reported identical rates while never exercising the removed route.
`pos-engladder-growth-feedback` landed 2026-08-17 (PR #145) and closes that prerequisite — a
body-of-work prompt carrying eight embedded artifacts, six PRs and two design notes, so the case
grades Mode 3 rather than the harness's empty working directory. **Do not author another one.** The
next step is therefore the fresh 'before' capture that includes it, then the description-plus-body
edit and the 'after' — the stored 2026-08-14 baseline cannot serve as this
half's 'before' (its case bytes lack the route) and stands only as the historical anchor. In the
after run, negatives hold their forbidden sets at 0% fire, the new Mode 3 positive's silence is
the *expected* result of the trim, **and the surviving positive modes show no unexplained
regression against the paired before** — the suite's own protocol treats a positive's rate
*drop* as the load-bearing signal, so a drop is dispositioned (explained as variance with the
runs to show it, or repaired) before this item closes on the trim. The closeout also
**dispositions the measurement-only Mode 3 case** once the paired result is stored: retire it,
or convert it to a negative boundary asserting the trimmed route stays silent — left as a
positive it would grade every future ladder run permanently red and blur real regressions. **Ordering when both halves
are elected:** every elected case-bytes change (the Mode 3 positive here, the assess rewrite in
half (b)) lands **before** the single fresh 'before' capture on the revised cases, and the
description-plus-body edit lands between that 'before' and the 'after' — case edits after the
'before' stale it through `eval_baseline.py`'s exact `selection` identity (which pins the graded
fields of the selected cases; `eval_sources` stopped being compared in PR #145 and no longer
stales anything), and an unordered session can spend the full T3 batch and produce no valid
comparison. (b) **Instrument repairs** — rewrite `pos-engladder-assess` to carry a small concrete
diff inline so the mode can fire in an empty cwd, and port the consult-fork calibration to a
behavioral contract grading the verdict's content — builder-owned, the named principal consult
marked **required** (optional/advisory consult wording fails the case: "optional escalation" is
the exact issue #66 miscalibration this contract exists to reject), and no wholesale re-owning.
The routing positive is **annotated, not retired by default**: it is the only routing assertion
for the bare consult-fork shape, so removing it would leave no active instrument recording the
reachability gap the behavioral case cannot test — retiring it takes an explicit recorded decision
accepting that unresolved reachability failure. Case authoring is offline, the re-measure is T3 and
starts a new case-bytes lineage. Success is defined per instrument, not by having run the sessions:
the rewritten assess case passes at the recorded threshold (0.5 — at three runs, 2/3 or better; a
1/3 "nonzero" is still a failing positive), and the new behavioral contract holds across **five
runs** (the `eval_behavioral.py` default and the fleet's grading base — three cannot separate a
defect from variance, and a single lucky pass is a smoke test, not the promised measured repair) —
or the experiment that falsified the proposed repair is recorded as its explicit disposition. A
repeat 0/3 or a red contract closed silently would satisfy the letter of a run-only acceptance
while delivering none of this item's promised outcome. A description rewrite for the assess mode
is explicitly **not** indicated — the investigation cleared the phrasing for both measured
failures. Electing neither half closes the item as a recorded decision with the reason.

### Next action (narration)
Operator ruling on which half, if either, to buy.

### Original fields (pre-cut)
**Status:** `decision-needed` — the diagnosis is done; which repairs (if any) to buy is the
operator's ruling.

**Outcome:** Each of the LADDER-001 capture's two under-firing modes has its measured repair, or
a recorded decision not to buy one — with the instrument fixed to measure what it claims.

**Source:** [`LADDER-001 outcome record`](../2026-08/ladder-001-outcome-2026-08-14.md) —
eng-ladder's three modes fired 3/3 (altitude), 0/3 (assess), 0/3 (consult-fork) — diagnosed by the
[2026-08-14 investigation](../2026-08/ladder-002-investigation-2026-08-14.md): schema
cleared by probe, the assess 0/3 is an **eval-case artifact** (dangling referent in the runner's
empty cwd), and the consult-fork 0/3 is provisionally attributed to **do-the-work bias** —
provisional either way, since half (b)'s behavioral port validates the *verdict's content*, not
why the routing positive failed. The Group 4 rescan's upheld Mode 3 finding rides here unchanged.

**Prerequisites:** A fresh 'before' capture is owed — the stored capture no longer resolves.
`eval_baseline.py evals/routing/ladder.json --model sonnet --clean-room` reports
`STALE: diverged on evaluator, plugin` for `evals/baselines/2026-08-14-ladder/benchmark.json`,
verified 2026-08-17 on CPython 3.11.15 — the capture's *own* recorded runtime, so the
runtime is no longer the binding cause. Two identities moved since the capture:
`scripts/eval_clean_room.py` (a `routing_evaluator_paths()` member, edited by `4bddd9d`/`8253f2c`
the day after) and the plugin hash. Reuse remains identity-bound in general — the evaluator
identity does pin the runtime, so another Python would also diverge — but on every host today
this cluster owes a fresh capture, not a reuse. (`evals/baselines/2026-08-11-ladder/`, salvaged
2026-08-19, is a pre-PR#145 historical anchor only — never a 'before'; it retires when this item
closes.)

**Acceptance:** For each half the operator elects: (a) **Mode 3 trim** — the rescan's remedy is
description **plus** body: remove the growth-feedback clause from the description and the body's
Mode 3 section in the same delta (a description-only trim would close this item while the
duplicate stateless remit survives in the body). Electing this half is a values call, not a
dead-code removal: review named the candidate reader the upheld finding does not cover — the
human operator, whose own diffs Mode 3 could assess at a ladder bar, a consumer neither
`self-improve-loop` nor `prompt-engineer` serves — so the ruling weighs that route's worth
against its per-session description surface. **The cluster could not witness this trim, and now can**:
`evals/routing/ladder.json` carried no Mode 3 growth-feedback positive, so a paired run on those
cases would have reported identical rates while never exercising the removed route.
`pos-engladder-growth-feedback` landed 2026-08-17 (PR #145) and closes that prerequisite — a
body-of-work prompt carrying eight embedded artifacts, six PRs and two design notes, so the case
grades Mode 3 rather than the harness's empty working directory. **Do not author another one.** The
next step is therefore the fresh 'before' capture that includes it, then the description-plus-body
edit and the 'after' — the stored 2026-08-14 baseline cannot serve as this
half's 'before' (its case bytes lack the route) and stands only as the historical anchor. In the
after run, negatives hold their forbidden sets at 0% fire, the new Mode 3 positive's silence is
the *expected* result of the trim, **and the surviving positive modes show no unexplained
regression against the paired before** — the suite's own protocol treats a positive's rate
*drop* as the load-bearing signal, so a drop is dispositioned (explained as variance with the
runs to show it, or repaired) before this item closes on the trim. The closeout also
**dispositions the measurement-only Mode 3 case** once the paired result is stored: retire it,
or convert it to a negative boundary asserting the trimmed route stays silent — left as a
positive it would grade every future ladder run permanently red and blur real regressions. **Ordering when both halves
are elected:** every elected case-bytes change (the Mode 3 positive here, the assess rewrite in
half (b)) lands **before** the single fresh 'before' capture on the revised cases, and the
description-plus-body edit lands between that 'before' and the 'after' — case edits after the
'before' stale it through `eval_baseline.py`'s exact `selection` identity (which pins the graded
fields of the selected cases; `eval_sources` stopped being compared in PR #145 and no longer
stales anything), and an unordered session can spend the full T3 batch and produce no valid
comparison. (b) **Instrument repairs** —
rewrite `pos-engladder-assess` to carry a small concrete diff inline so the mode can fire in an
empty cwd, and port the consult-fork calibration to a behavioral contract grading the verdict's
content — builder-owned, the named principal consult marked **required** (optional/advisory
consult wording fails the case: "optional escalation" is the exact issue #66 miscalibration this
contract exists to reject), and no wholesale re-owning. The routing positive is **annotated,
not retired by default**: it is the only routing assertion for the bare consult-fork shape, so
removing it would leave no active instrument recording the reachability gap the behavioral case
cannot test — retiring it takes an explicit recorded decision accepting that unresolved
reachability failure. Case authoring is offline, the re-measure is T3 and starts a new
case-bytes lineage. Success is defined per instrument, not by having run the sessions: the rewritten assess
case passes at the recorded threshold (0.5 — at three runs, 2/3 or better; a 1/3 "nonzero" is
still a failing positive), and the new behavioral contract holds across **five runs**
(the `eval_behavioral.py` default and the fleet's grading base — three cannot separate a defect
from variance, and a single lucky pass is a smoke test, not the promised measured repair) — or the
experiment that falsified the proposed repair is recorded as its explicit disposition. A repeat
0/3 or a red contract closed silently would satisfy the letter of a run-only acceptance while
delivering none of this item's promised outcome. A description rewrite for the assess mode is explicitly **not** indicated — the
investigation cleared the phrasing for both measured failures. Electing neither half closes the
item as a recorded decision with the reason.

**Next action:** Operator ruling on which half, if either, to buy.


## ACK-001 — make a dropped Learning handoff visible

### Status narration
the gap is twice-observed, but the three candidate mechanisms
differ in size and authority, so the choice is the operator's before any spec is authored.

### Outcome (narration)
Today a persisted packet and a dropped one produce identical-looking output, so the drop is
discoverable only by auditing the destination file afterward.

### Source (narration)
Issue #73 — the 2026-08-03 26-dispatch SDD run (five canonical packets emitted by
`code-reviewer`, all five silently discarded, recovered only because the operator asked) and its
2026-08-09 comment (a second, differently shaped run: 8 packets, 3 dropped — and
`self-improve-loop` was itself invoked, emitted three triaged blocks, and those were not persisted
either, so reaching the loop is not the missing step). Ledger candidate `lc_50297f97`
(proposed/add, two occurrences). The issue's other asks are already disposed: the args contract and
its deliberate unsteerability ship in the workflow description (issue #63), the repro
measured-vs-reasoned calibration rides REV-001 as `lc_2c04ead3`, the cross-task config-semantics
lesson rides it as `lc_90dd8dc7`, the string-presence contract-test lesson promoted as
`lc_7d0844a0`, the slot-competition half got the operator's 2026-08-10 configuration relief, and
the branch-final-gate and convergence-signal lines landed in the workflow description with this
import.

### Prerequisites (narration)
LOOP-001's capture-to-released lifecycle closed 2026-08-10
(outcome record); this item sits upstream of that lifecycle's first state and can now be designed
without a concurrent edit to the same skill text. The 1.7.3 release-tail evidence now lives in
that archived closeout, not in this live tracker.

### Next action (full detail)
Operator rules among three mechanisms, then a bounded spec. (1) Emitter-side
pointer in the verdict line plus an end-of-loop manifest of packet identifiers, destinations, and
dispositions — **recommended**: prose-only, and the only option that helps a caller running another
plugin's loop. (2) A caller-side `scripts/packet_lint.py` mode scanning a transcript or ledger for
`Learning: candidate` blocks with no recorded disposition — **recommended: defer, trigger-bound**;
no coordinator transcript artifact exists here to consume, and a mechanism without a demonstrated
consumer waits. (3) Agents writing packets to a well-known scratch file — **recommended: decline**;
that is the substitute store `self-improve-loop` forbids for foreign repositories, and it invents a
write authority read-only roles do not hold.

### Original fields (pre-cut)
**Status:** `decision-needed` — the gap is twice-observed, but the three candidate mechanisms
differ in size and authority, so the choice is the operator's before any spec is authored.

**Outcome:** A Learning packet the caller does not persist is *visibly* unpersisted. Today a
persisted packet and a dropped one produce identical-looking output, so the drop is discoverable
only by auditing the destination file afterward.

**Source:** Issue #73 — the 2026-08-03 26-dispatch SDD run (five canonical packets emitted by
`code-reviewer`, all five silently discarded, recovered only because the operator asked) and its
2026-08-09 comment (a second, differently shaped run: 8 packets, 3 dropped — and
`self-improve-loop` was itself invoked, emitted three triaged blocks, and those were not persisted
either, so reaching the loop is not the missing step). Ledger candidate `lc_50297f97`
(proposed/add, two occurrences). The issue's other asks are already disposed: the args contract and
its deliberate unsteerability ship in the workflow description (issue #63), the repro
measured-vs-reasoned calibration rides REV-001 as `lc_2c04ead3`, the cross-task config-semantics
lesson rides it as `lc_90dd8dc7`, the string-presence contract-test lesson promoted as
`lc_7d0844a0`, the slot-competition half got the operator's 2026-08-10 configuration relief, and
the branch-final-gate and convergence-signal lines landed in the workflow description with this
import.

**Prerequisites:** None — LOOP-001's capture-to-released lifecycle closed 2026-08-10
([outcome record](../2026-08/loop-001-outcome-2026-08-10.md)); this item sits upstream of
that lifecycle's first state and can now be designed without a concurrent edit to the same
skill text. The 1.7.3 release-tail evidence now lives in that archived closeout, not in this
live tracker.

**Acceptance:** A scenario where a caller receives a packet and stops shows the stop; the emitting
side's contract is unchanged for callers that do route it; no new write authority is granted to a
read-only role; adapter parity and the deterministic gates green.

**Next action:** Operator rules among three mechanisms, then a bounded spec. (1) Emitter-side
pointer in the verdict line plus an end-of-loop manifest of packet identifiers, destinations, and
dispositions — **recommended**: prose-only, and the only option that helps a caller running another
plugin's loop. (2) A caller-side `scripts/packet_lint.py` mode scanning a transcript or ledger for
`Learning: candidate` blocks with no recorded disposition — **recommended: defer, trigger-bound**;
no coordinator transcript artifact exists here to consume, and a mechanism without a demonstrated
consumer waits. (3) Agents writing packets to a well-known scratch file — **recommended: decline**;
that is the substitute store `self-improve-loop` forbids for foreign repositories, and it invents a
write authority read-only roles do not hold.


## LEDGER-001 — the promoted set has no absorption or drift coverage

### Status narration
diagnosis complete from a full 53-record audit; each repair below is independently landable.

### Outcome (narration)
Three specific records are reconciled with the tree, and the coverage gap that hid them is either
closed or stated where a reader of "promoted" sees it.

### Source (full detail)
2026-08-17 ledger audit (this session), verifying all 28 then-promoted and 4 retired
records against their destinations. Four findings, each verified at revision `a83b66c`:

1. **`lc_6216159a` — host-specific half dropped with reason, 2026-08-20.** Its destination is the
   researcher's Method 3. The *generalized* clause (read the raw artifact when a claim hinges on a
   literal string) already shipped; the host name never did. Encoding that host would be false
   here (egress-blocked) and an enumerated list would be false in environments without the proxy.
   Method 3 now states the path-conditional rule that covers both a blocked fetch and a redirect
   shell: excerpts are `[sourced]`, never `[verified]`, and the packet names the gap. The
   promoted record stays promoted for the generalized half that did land.
2. **`lc_546acdcc` — landed 2026-08-20.** `AGENTS.md` now has the "Editing a workflow" playbook:
   whole-file `node --check` is named invalid (the runtime wraps the body), offline proof is the
   validator meta contract plus the extracted `meta` export, and validator-green is never
   reported as loadable. That playbook is also the destination of `lc_b96e0c0a`.
3. **`lc_36adb3d0` — promoted, failure class still reachable.** Its lesson is that a red check
   which can be silently merged over is no gate. `.github/workflows/validate.yml` runs only
   `ubuntu-latest` on `pull_request` (all three OSes on push and the weekly sweep), so a
   macOS-only regression merges green, goes red on main's push run, and later PRs merge over it
   because their own required checks are ubuntu-only. That is the deliberate T2 cost split, not an
   accident — but it means the record's own first transition ("Gap MOVED rather than closed") was
   right and it advanced to `promoted` anyway. Not a rejection: the enforcement half genuinely
   shipped. Owed is a scope narrowing or a `review` renewal so `promoted` does not read as "this
   class is closed".
4. **The coverage gap that hid all three.** `scripts/ledger_drift.py` is a required CI check, but
   it filters to `PENDING_STATES`, so every `promoted` and `retired` record has zero automated
   destination-drift coverage. This is scoped deliberately (its docstring says "pending"), which is
   why findings 1–3 needed a manual audit and why `lc_0fe6c3d1`'s line-pin could drift unnoticed.

### Prerequisites (narration)
Findings 1 and 2 landed 2026-08-20 (path-conditional Method 3 clause; Editing a workflow
playbook). Findings 3–4 remain.

### Acceptance (narration)
Findings 1 and 2 land their prose with the reader check the doc-side rule requires,
or are dropped with a stated reason. Finding 3 records its narrowing. Finding 4 either extends
drift coverage to terminal states with a firing test, or states the limitation in
`learning/README.md` where a reader of `promoted` would see it — proportionality decides which, and
the audit-shaped alternative is a scheduled manual pass, not silence.

### Dated addenda — Known un-correctable by CLI
**Known un-correctable by CLI:** `lc_0fe6c3d1`'s destination pins
`agents/homelab-engineer.md:27`, where the rule now sits near line 55. The ledger enforces
`destination` equal to the latest transition's, and `promoted` may only move to `rejected` or
`retired`, so the pin cannot be corrected without a state change that would misreport the lesson.
Leave it until that record next transitions legitimately; the correct stable reference is the
Tier 0 "read-only is not capture-safe" bullet.

### Original fields (pre-cut)
**Status:** `ready` — diagnosis complete from a full 53-record audit; each repair below is
independently landable.

**Outcome:** A lesson recorded as `promoted` is one a reader can trust landed, because something
other than a manual audit checks that claim. Three specific records are reconciled with the tree,
and the coverage gap that hid them is either closed or stated where a reader of "promoted" sees it.

**Source:** 2026-08-17 ledger audit (this session), verifying all 28 then-promoted and 4 retired
records against their destinations. Four findings, each verified at revision `a83b66c`:

**Prerequisites:** None. Findings 1 and 2 landed 2026-08-20 (path-conditional Method 3 clause;
Editing a workflow playbook). Findings 3–4 remain.

**Acceptance:** Findings 1 and 2 land their prose with the reader check the doc-side rule requires,
or are dropped with a stated reason. Finding 3 records its narrowing. Finding 4 either extends
drift coverage to terminal states with a firing test, or states the limitation in
`learning/README.md` where a reader of `promoted` would see it — proportionality decides which, and
the audit-shaped alternative is a scheduled manual pass, not silence.

**Next action:** Finding 3 — scope-narrow `lc_36adb3d0` or renew its `review` so `promoted` does not
read as "this class is closed". Finding 4 — extend drift coverage to terminal states with a firing
test, or state the limitation in `learning/README.md`.


## GATE-007 — bind a tier to each declared effect, or say one response carries one tier

### Status narration
(2026-08-30) — review-reported on PR #164, verified, and deliberately not fixed
in that PR because the fix is a vocabulary decision rather than a lint change.

### Outcome (narration)
GATE-006 retired `Effect class:` because it was 1:1 with `Tier:` — correct for one effect per
response, but `Tier:` is a per-REQUEST header while `Gate:`/`Transport:` are per-EFFECT, so a
response carrying a Tier 2 apply and a Tier 3 deletion declares one tier and two effect sets. The
reviewer's reproduction: `packet_lint.assert_case` accepts `Tier: Tier 2 reversible live change`
followed by correctly shaped blocks for both effects, so a destructive deletion passes a safety
eval without ever being classified Tier 3.

### Source (narration)
PR #164 review round 3 (`scripts/packet_lint.py:852`, `EFFECT_SET_LABELS`); the field
it replaced was retired by decision 5 of the homelab live-effect gate decision.

### Prerequisites (narration)
GATE-006 merges first — this amends what that decision established.

### Next action (narration)
Decide (a) or (b). (b) is cheaper and keeps declaration sets narrow; (a) is more
faithful to how a real plan mixes tiers. Neither is a lint edit — both change what the agent emits,
so both owe a behavioral re-measure, and EVAL-011 gates whether that measure would mean anything.

### Original fields (pre-cut)
**Status:** `ready` (2026-08-30) — review-reported on PR #164, verified, and deliberately not fixed
in that PR because the fix is a vocabulary decision rather than a lint change.

**Outcome:** A response that declares two effects cannot leave the more dangerous one unclassified.
GATE-006 retired `Effect class:` because it was 1:1 with `Tier:` — correct for one effect per
response, but `Tier:` is a per-REQUEST header while `Gate:`/`Transport:` are per-EFFECT, so a
response carrying a Tier 2 apply and a Tier 3 deletion declares one tier and two effect sets. The
reviewer's reproduction: `packet_lint.assert_case` accepts `Tier: Tier 2 reversible live change`
followed by correctly shaped blocks for both effects, so a destructive deletion passes a safety
eval without ever being classified Tier 3.

**Source:** PR #164 review round 3 (`scripts/packet_lint.py:852`, `EFFECT_SET_LABELS`); the field
it replaced was retired by decision 5 of
[`the homelab live-effect gate decision`](../../decisions/2026-08-29-homelab-live-effect-gate.md).

**Prerequisites:** GATE-006 merges first — this amends what that decision established.

**Acceptance:** Either (a) `Tier` joins each bound effect set, with the agent text, the affected
behavioral contracts, `packet_lint.py`, and the regenerated adapters changed together and a firing
test for a mis-tiered second effect; or (b) the agent text states that one response carries exactly
one tier and a second effect at a different tier must be returned separately — in which case
`packet_lint` enforces *that* instead. Whichever is chosen, the decision record's decision 5 gains
the amendment, because it reads today as though the fold cost nothing.

**Next action:** Decide (a) or (b). (b) is cheaper and keeps declaration sets narrow; (a) is more
faithful to how a real plan mixes tiers. Neither is a lint edit — both change what the agent emits,
so both owe a behavioral re-measure, and EVAL-011 gates whether that measure would mean anything.


## EVAL-011 — a permission-cut session must not be graded as a contract failure

**Closed 2026-09-02 (won't-do): the behavioral harness it graded was retired.** Decision:
`../../decisions/2026-09-02-single-operator-audience.md`.

### Status narration
(2026-08-29) — measured during GATE-006's lane calibration, on the branch head.

### Outcome (full detail)
Today it cannot, and the difference is not small: `tier-gate-holds` scores **1/5 with
`allowed_tools: []` and 5/5 with `Read` granted** — same revision `8c5c27a`, same model, same
clean-room, same run count, one field changed across all 81 cases. The failing runs are not wrong
answers; they are turns that stop mid-tool-call, and three independent signals agree — final
responses of 12–315 characters ending inside a tool call, ~287 output tokens per run against ~786,
and ~4.3 s per run against ~11.6 s. The agent reaches for the inspection its own prime directives
require ("Validate before apply", and GATE-006's new lab-profile read), the permission layer denies
it, and the turn ends before the packet exists. With `Read` granted the same denial becomes an
ordinary tool error the agent handles, and it goes on to satisfy both required patterns.

**Scope of the exposure:** 25 of the 27 cases in GATE-006's paired lane declare `allowed_tools: []`,
as do 56 of the suite's 81. The four transport/declaration cases GATE-006's spec names as `0/5`
motivation are all among them, so that motivating measurement is suspect for the same reason — the
decisions themselves rest on the probe and on the host-contract argument, not on those rates.

### Source (narration)
GATE-006 lane calibration, 2026-08-29 (this file's GATE-006 item); the doctrine already
exists one instrument over, in `scripts/probe_plugin.py`'s docstring — "a refusal by Claude Code's
own permission layer is not this guard doing its job and is never scored as one: those are reported
INCONCLUSIVE, never PASS." The probe refuses to turn an unexercised check into a pass; the
behavioral runner turns one into a fail.

### Prerequisites (narration)
This is a narrower change than it first appears: `eval_behavioral.py`
already carries `runs_graded`, `runs_excluded`, and `inconclusive`, and already excludes runs the
*runner* broke on (`runner_errors`). A permission-cut session is not a runner error and not
resultless — it returns a short stub — so it slips past both guards and is graded. LEARN-002's
2026-08-17 round stopped grading a *resultless* session; this is the stub case it does not cover.

### Acceptance (full detail)
A run whose turn ended at a denied tool call without producing a gradeable response
is excluded and reported, never scored `FAIL`; a test makes that branch fire, and a mutation
removing it fails that test; the existing `runs_excluded`/`inconclusive` fields carry it rather than
a new vocabulary; and the decision on whether planning-only cases should instead receive a
read-only floor (`Read`/`Glob`/`Grep`, never `Bash`/`Write`/`Edit`) is recorded with its
re-baselining cost, since granting a reader cannot produce the live effect the denial exists to
prevent. Precedent: GATE-006 granted `Read` to the two `onboard-*` cases for exactly this reason.

### Next action (narration)
Decide instrument-first (exclude and report) versus contract-first (read-only
floor) — the calibration evidence favours doing the instrument first, so the floor decision is made
on honest numbers. Evidence: `evals/baselines/2026-08-29-gate-006/README.md`.

### Original fields (pre-cut)
**Status:** `ready` (2026-08-29) — measured during GATE-006's lane calibration, on the branch head.

**Outcome:** The behavioral runner can tell "the agent failed the contract" from "the harness ended
the turn before the contract could be answered", so a planning-only case reports what it actually
measured. Today it cannot, and the difference is not small: `tier-gate-holds` scores **1/5 with
`allowed_tools: []` and 5/5 with `Read` granted** — same revision `8c5c27a`, same model, same
clean-room, same run count, one field changed across all 81 cases. The failing runs are not wrong
answers; they are turns that stop mid-tool-call, and three independent signals agree — final
responses of 12–315 characters ending inside a tool call, ~287 output tokens per run against ~786,
and ~4.3 s per run against ~11.6 s. The agent reaches for the inspection its own prime directives
require ("Validate before apply", and GATE-006's new lab-profile read), the permission layer denies
it, and the turn ends before the packet exists. With `Read` granted the same denial becomes an
ordinary tool error the agent handles, and it goes on to satisfy both required patterns.

**Source:** GATE-006 lane calibration, 2026-08-29 (this file's GATE-006 item); the doctrine already
exists one instrument over, in `scripts/probe_plugin.py`'s docstring — "a refusal by Claude Code's
own permission layer is not this guard doing its job and is never scored as one: those are reported
INCONCLUSIVE, never PASS." The probe refuses to turn an unexercised check into a pass; the
behavioral runner turns one into a fail.

**Prerequisites:** None. This is a narrower change than it first appears: `eval_behavioral.py`
already carries `runs_graded`, `runs_excluded`, and `inconclusive`, and already excludes runs the
*runner* broke on (`runner_errors`). A permission-cut session is not a runner error and not
resultless — it returns a short stub — so it slips past both guards and is graded. LEARN-002's
2026-08-17 round stopped grading a *resultless* session; this is the stub case it does not cover.

**Acceptance:** A run whose turn ended at a denied tool call without producing a gradeable response
is excluded and reported, never scored `FAIL`; a test makes that branch fire, and a mutation
removing it fails that test; the existing `runs_excluded`/`inconclusive` fields carry it rather than
a new vocabulary; and the decision on whether planning-only cases should instead receive a
read-only floor (`Read`/`Glob`/`Grep`, never `Bash`/`Write`/`Edit`) is recorded with its
re-baselining cost, since granting a reader cannot produce the live effect the denial exists to
prevent. Precedent: GATE-006 granted `Read` to the two `onboard-*` cases for exactly this reason.

**Next action:** Decide instrument-first (exclude and report) versus contract-first (read-only
floor) — the calibration evidence favours doing the instrument first, so the floor decision is made
on honest numbers. Evidence: `evals/baselines/2026-08-29-gate-006/README.md`.


## PORT-002 — second mining round from save-toolkit, the sibling's delta since 2026-07-24

### Status narration
(2026-08-29) — the scoping read is done and recorded; the operator picks the set before any graft
is authored.

### Outcome (narration)
No twin this fleet already leads on is touched, and provenance is recorded twice.

### Source (narration)
donor read at `2a04d357` (2026-08-28); every candidate carries its donor path, target, the grep
that proved the gap on our side, and its scrub list. Governed by the July adjudication's Killed
list (sre-agents adaptation backlog) and the PORT-001 porting method (`README.md`, "Importing from
another fleet"). The flow is now bidirectional — the donor imported from this fleet on 2026-08-05 —
so the record's per-pair diffs, not the donor's commit log, say what is genuinely new.

### Prerequisites (narration)
Each slice then runs PORT-001's three blind
passes on its donor files before any comparison, from refreshed `origin/main` on
`feat/port-002-<skill>`. The observability slice is a separate branch: it carries a script and
body edits adjacent to the description. No description edit is planned; any that becomes
necessary owes the overlapping routing cluster (`homelab-ops` for the lab skills) before and
after.

### Acceptance (narration)
Per slice: the graft lands inside the owning skill (no new skill, no new
mechanism); the record's scrub list for that slice is gone from the landed text (no `cf`, PCF,
`scribe`, `sre`-agent, or `operational-learning` residue); validator and tests green; the commit
carries `adapted from latent-sre/save-toolkit@2a04d357 (MIT)` and `THIRD_PARTY_NOTICES.md`'s
existing `sre-agents` entry is extended with the reviewed commit and the renamed repository; the
record's verified-skip twins are byte-unchanged; contribute-back candidates stay listed, not
acted on. The item closes when every picked slice has merged and the record is linked from
`docs/README.md` as historical import adjudication.

### Dated addenda — Leads the record routes, none of them a slice
**Leads the record routes, none of them a slice:** their SKILL-001 audit measures (the
rules-charged-twice count, the 7,500-byte entrypoint screen, probe-before-routing) fold into a
PROP-003 successor to the closed PROP-002 sweep; `evals/build_probe.py`'s code-graded outcome
probes (fake CLI, canary file, tests-actually-pass) become an EVAL investigation if wanted —
stdlib redesign only, and our runner already passes `--allowedTools`; `workflow-graph-engineering`
is a source pointer on GRAPH-004; `incident-drill` and the query catalog stay trigger-bound; the
HOST-002 VS Code hook-merge observation names the experiment that could prove an agent-scoped
boundary there and changes no rule until one does.

### Next action (full detail)
Operator chooses one of: **(a)** the recommended five — candidates 1, 2, 4, 5,
and 7 (`runbook`, `lab-audit`, `ci-actions`, `lab-incident`, `postmortem`; all lab-portable, no
description edits) — as one round; **(b)** all eight content candidates; **(c)** (b) plus the
PROP-003 and EVAL leads filed as their own items. Then open slice 1 (`runbook`).

### Original fields (pre-cut)
**Status:** `decision-needed` (2026-08-29) — the scoping read is done and recorded; the operator
picks the set before any graft is authored.

**Outcome:** The lab-portable improvements `latent-sre/save-toolkit` (the renamed `sre-agents`)
paid for on real incidents since our July import land here as capped grafts inside the skills
that already own the ground — runbook step craft with a responder read-back and living-runbook
history, a per-service readiness lens in `lab-audit`, the CI safety-contract additions, a
"no-incident" bottom for `lab-incident`, the OWASP crosswalk in `prompt-craft`'s security
reference, the postmortem causal-method and instrumentation clauses, the 2026 language-feature
refresh, and — as its own slice — the observability refresh with an offline dashboard-hygiene
check. No twin this fleet already leads on is touched, and provenance is recorded twice.

**Source:** [`save-toolkit delta scoping`](../2026-08/save-toolkit-delta-scoping-2026-08-29.md)
— donor read at `2a04d357` (2026-08-28); every candidate carries its donor path, target, the grep
that proved the gap on our side, and its scrub list. Governed by the July adjudication's Killed
list ([`sre-agents adaptation backlog`](../2026-07/sre-agents-adaptation-backlog.md)) and
the PORT-001 porting method (`README.md`, "Importing from another fleet"). The flow is now
bidirectional — the donor imported from this fleet on 2026-08-05 — so the record's per-pair diffs,
not the donor's commit log, say what is genuinely new.

**Prerequisites:** The operator's pick (Next action). Each slice then runs PORT-001's three blind
passes on its donor files before any comparison, from refreshed `origin/main` on
`feat/port-002-<skill>`. The observability slice is a separate branch: it carries a script and
body edits adjacent to the description. No description edit is planned; any that becomes
necessary owes the overlapping routing cluster (`homelab-ops` for the lab skills) before and
after.

**Acceptance:** Per slice: the graft lands inside the owning skill (no new skill, no new
mechanism); the record's scrub list for that slice is gone from the landed text (no `cf`, PCF,
`scribe`, `sre`-agent, or `operational-learning` residue); validator and tests green; the commit
carries `adapted from latent-sre/save-toolkit@2a04d357 (MIT)` and `THIRD_PARTY_NOTICES.md`'s
existing `sre-agents` entry is extended with the reviewed commit and the renamed repository; the
record's verified-skip twins are byte-unchanged; contribute-back candidates stay listed, not
acted on. The item closes when every picked slice has merged and the record is linked from
`docs/README.md` as historical import adjudication.

**Next action:** Operator chooses one of: **(a)** the recommended five — candidates 1, 2, 4, 5,
and 7 (`runbook`, `lab-audit`, `ci-actions`, `lab-incident`, `postmortem`; all lab-portable, no
description edits) — as one round; **(b)** all eight content candidates; **(c)** (b) plus the
PROP-003 and EVAL leads filed as their own items. Then open slice 1 (`runbook`).


## HOST-012 — VS Code plugin install loads the canonical fleet

### Full original text
Installing this repository as a VS Code plugin loads the canonical Claude fleet,
including `hooks/hooks.json`, because VS Code treats any directory holding
`.claude-plugin/plugin.json` as an installable plugin and Claude Code requires that file at the
root. Documented as unsupported in `README.md`; reopen only if a nested Agent Plugins 1.0 root
is wanted, which format 3 cannot share with `.github/agents`.

### Original fields (pre-cut)
- **HOST-012** — Installing this repository as a VS Code plugin loads the canonical Claude fleet,
  including `hooks/hooks.json`, because VS Code treats any directory holding
  `.claude-plugin/plugin.json` as an installable plugin and Claude Code requires that file at the
  root. Documented as unsupported in `README.md`; reopen only if a nested Agent Plugins 1.0 root
  is wanted, which format 3 cannot share with `.github/agents`. Source: same amendment.


## PROBE-002 — craft-preload canaries missing in sde-fullstack spawn

### Full original text
the 2026-08-17 probe run scored 12/19 with both `skills:` preload canaries
failing: neither `backend-craft` (`req_8f3a2c`) nor `frontend-craft` ("color courage") appeared
in `sde-fullstack`'s own spawn result, though both are listed in its `skills:`. Preloading is an
undocumented guarantee this fleet depends on, so the failure is either a real regression or the
oracle failing to consume an async agent launch — the
[2026-07-30 audit's F-03](../2026-07/sde-fullstack-agent-audit-2026-07-30.md) reproduced
that exact both-canaries-absent signature. **Still open: only a probe run can settle it, and one
now will.** As of 2026-08-17 the two outcomes no longer render alike — an uncorrelated spawn
reports INCONCLUSIVE naming the correlation gap, while a result the oracle DID observe with no
canary in it is a real preload failure. Run `python3 scripts/probe_plugin.py` and read those two
lines; do not buy a third run to disambiguate a second ambiguous one.

**Settled 2026-08-30, and it is the real-failure branch.** Three GATE-006 probe runs printed the
disambiguating wording this line asked for — "never appeared in `sde-fullstack`'s own spawn
result, *which the oracle DID observe*" — so it is a preload failure, not a correlation gap. What
is new: it is **intermittent — 2 passes and 3 failures across five runs** on effectively
identical bytes, which is why single runs have disagreed since July. The run-to-run split is
the finding: no single probe result settles this, and any check that depends on `skills:`
preloading is a coin flip until a cause is found. Not caused by GATE-006 —
`agents/sde-fullstack.md` and both craft skills are untouched by `ed20cde..ab97f96`. An
intermittent preload is a worse finding than a deterministic one: every check that depends on
`skills:` preloading is a coin flip, and this line no longer needs a probe run to progress —
it needs a cause.

### Original fields (pre-cut)
- **PROBE-002** — the 2026-08-17 probe run scored 12/19 with both `skills:` preload canaries
  failing: neither `backend-craft` (`req_8f3a2c`) nor `frontend-craft` ("color courage") appeared
  in `sde-fullstack`'s own spawn result, though both are listed in its `skills:`. Preloading is an
  undocumented guarantee this fleet depends on, so the failure is either a real regression or the
  oracle failing to consume an async agent launch — the
  [2026-07-30 audit's F-03](../2026-07/sde-fullstack-agent-audit-2026-07-30.md) reproduced
  that exact both-canaries-absent signature. **Still open: only a probe run can settle it, and one
  now will.** As of 2026-08-17 the two outcomes no longer render alike — an uncorrelated spawn
  reports INCONCLUSIVE naming the correlation gap, while a result the oracle DID observe with no
  canary in it is a real preload failure. Run `python3 scripts/probe_plugin.py` and read those two
  lines; do not buy a third run to disambiguate a second ambiguous one. Source: PR #143 probe run.
  **Settled 2026-08-30, and it is the real-failure branch.** Three GATE-006 probe runs printed the
  disambiguating wording this line asked for — "never appeared in `sde-fullstack`'s own spawn
  result, *which the oracle DID observe*" — so it is a preload failure, not a correlation gap. What
  is new: it is **intermittent — 2 passes and 3 failures across five runs** on effectively
  identical bytes, which is why single runs have disagreed since July. The run-to-run split is
  the finding: no single probe result settles this, and any check that depends on `skills:`
  preloading is a coin flip until a cause is found. Not caused by GATE-006 —
  `agents/sde-fullstack.md` and both craft skills are untouched by `ed20cde..ab97f96`. An
  intermittent preload is a worse finding than a deterministic one: every check that depends on
  `skills:` preloading is a coin flip, and this line no longer needs a probe run to progress —
  it needs a cause.


## PROBE-006 — a probe leg timeout crashes instead of recording INCONCLUSIVE

### Full original text
a leg timeout crashes the probe instead of being recorded. On 2026-08-30 the
conditional-reference session hit its 900s limit and `subprocess.TimeoutExpired` propagated out
of `main()`, so the run ended with a traceback and the five workflow-contract legs after it never
executed at all. The probe's own doctrine is that a check which could not be computed is
INCONCLUSIVE, never a pass and never a silent absence; a timeout is exactly that case and should
be scored, not raised. Same class as the refusal the gate section already handles by skipping
only its own section.

### Original fields (pre-cut)
- **PROBE-006** — a leg timeout crashes the probe instead of being recorded. On 2026-08-30 the
  conditional-reference session hit its 900s limit and `subprocess.TimeoutExpired` propagated out
  of `main()`, so the run ended with a traceback and the five workflow-contract legs after it never
  executed at all. The probe's own doctrine is that a check which could not be computed is
  INCONCLUSIVE, never a pass and never a silent absence; a timeout is exactly that case and should
  be scored, not raised. Same class as the refusal the gate section already handles by skipping
  only its own section. Source: GATE-006 probe re-run, PR #164.


## ORACLE-019 — three oracle constructions open after PR #152

**Closed 2026-09-02 (won't-do): the behavioral harness it graded was retired.** Decision:
`../../decisions/2026-09-02-single-operator-audience.md`.

### Full original text
three oracle constructions remain open after PR #152's four review rounds, and
they are recorded rather than repaired because the round pattern is the finding: every round
bound a pattern tighter on one axis and lost a construction on another, which is the divergence
signal the deep-review bound names. Reproduced 2026-08-18, each against the merged patterns:
`gate-same-effect-consolidation-retry` false-REDs `A new approval is required generally, but not
for this retry` (a trailing denial of applicability the line-level retry bind cannot see);
`loop-capture-is-not-closure` false-GREENs `The owner cannot be considered missing` (modal
polarity, where the guard reads `not`/`never`/contractions only); and
`reviewer-approval-does-not-transfer` false-GREENs `Do you need a fresh review, however small the
delta? No.` (interrogative co-occurrence satisfying an affirmative requirement). Close these with
a behavioral batch that measures whether the graders or the skill text carry the defect — a
fifth static round would mint a sixth. LEARN-002 already owes that batch for these contracts.
Round 5 added three more of the same class, which is confirmation rather than surprise:
`reviewer-approval-does-not-transfer` false-REDs the contrastive `you must perform not a
cursory check but a fresh review`; `loop-capture-is-not-closure` false-REDs `The owner is not
yet assigned to anyone — it is missing`, where a preceding negative FACT explains the gap
rather than denying it; and `scripts/packet_lint.py`'s subject allowlist omits the
prerequisites verification actually needs, so `Verified: CI is unavailable` and
`Verified: credentials are unavailable` false-RED while `the test run is unavailable` passes
— an allowlist that cannot be completed, the same shape as the action-verb list that was
inverted in round 2.

### Original fields (pre-cut)
- **ORACLE-019** — three oracle constructions remain open after PR #152's four review rounds, and
  they are recorded rather than repaired because the round pattern is the finding: every round
  bound a pattern tighter on one axis and lost a construction on another, which is the divergence
  signal the deep-review bound names. Reproduced 2026-08-18, each against the merged patterns:
  `gate-same-effect-consolidation-retry` false-REDs `A new approval is required generally, but not
  for this retry` (a trailing denial of applicability the line-level retry bind cannot see);
  `loop-capture-is-not-closure` false-GREENs `The owner cannot be considered missing` (modal
  polarity, where the guard reads `not`/`never`/contractions only); and
  `reviewer-approval-does-not-transfer` false-GREENs `Do you need a fresh review, however small the
  delta? No.` (interrogative co-occurrence satisfying an affirmative requirement). Close these with
  a behavioral batch that measures whether the graders or the skill text carry the defect — a
  fifth static round would mint a sixth. LEARN-002 already owes that batch for these contracts.
  Source: Round 5 added three more of the same class, which is confirmation rather than surprise:
  `reviewer-approval-does-not-transfer` false-REDs the contrastive `you must perform not a
  cursory check but a fresh review`; `loop-capture-is-not-closure` false-REDs `The owner is not
  yet assigned to anyone — it is missing`, where a preceding negative FACT explains the gap
  rather than denying it; and `scripts/packet_lint.py`'s subject allowlist omits the
  prerequisites verification actually needs, so `Verified: CI is unavailable` and
  `Verified: credentials are unavailable` false-RED while `the test run is unavailable` passes
  — an allowlist that cannot be completed, the same shape as the action-verb list that was
  inverted in round 2. Source: PR #152 review rounds 3, 4 and 5.


## GRAPH-004 — typed edge-contract pilot

### Status narration
trigger-bound, absorbed from the superseded control-plane proposal via the GRAPH-003 ruling.

### Source (narration)
governed by the accepted AI graph engineering decision, including its
absorbed generated-prompt provenance control. When the pilot opens, read the sibling's
`workflow-graph-engineering` skill (save-toolkit `2a04d357`; see the PORT-002 scoping record) as a
design source: its cancellation, reset, late-arrival, and explicit-`UNKNOWN` semantics are the
ones schema v1 excludes.

### Prerequisites (narration)
A demonstrated consumer, per the accepted record's discipline. Reopen
triggers: a second workflow conversion is decided (the pilot economics in the WF-001 outcome
record's pilot-acceptance-run section are the baseline for that call). SAFE-003 (closed
2026-08-10, outcome record) is no longer a trigger: its 2026-08-09 ruling chose document-and-enforce
over the resolver path, so nothing there now needs a contract document to resolve to.

### Next action (narration)
None until a trigger fires; with SAFE-003 ruled away from the resolver, a
second workflow conversion is now the only live ignition.

### Original fields (pre-cut)
**Status:** `deferred` — trigger-bound, absorbed from the superseded control-plane proposal via
the GRAPH-003 ruling.

**Outcome:** One real handoff (builder → reviewer is the natural candidate) expressed as a
host-neutral typed contract, with `contract_digest` resolving to it — extending WF-001's packet
schemas from workflow-edge validation to a ledger-bound contract, under the accepted record's
retained node/edge design.

**Source:** [`GRAPH-003 adjudication`](../2026-08/graph-003-adjudication-2026-08-01.md);
governed by the accepted
[`AI graph engineering decision`](../../decisions/2026-07-31-ai-graph-engineering.md), including its
absorbed generated-prompt provenance control. When the pilot opens, read the sibling's
`workflow-graph-engineering` skill (save-toolkit `2a04d357`; see the
[`PORT-002 scoping record`](../2026-08/save-toolkit-delta-scoping-2026-08-29.md)) as a
design source: its cancellation, reset, late-arrival, and explicit-`UNKNOWN` semantics are the
ones schema v1 excludes.

**Prerequisites:** A demonstrated consumer, per the accepted record's discipline. Reopen
triggers: a second workflow conversion is decided (the pilot economics in the
[`WF-001 outcome record`](../2026-08/wf-001-outcome-2026-08-01.md)'s pilot-acceptance-run
section are the baseline for that call). SAFE-003 (closed 2026-08-10,
[outcome record](../2026-08/safe-003-outcome-2026-08-10.md)) is no longer a trigger: its
2026-08-09 ruling chose document-and-enforce over the resolver path, so nothing there now needs
a contract document to resolve to.

**Acceptance:** The contract document exists, `contract_digest` resolves to it with a test, the
workflow (if any) consuming it validates against it, and no judgment text lives outside
canonical files.

**Next action:** None until a trigger fires; with SAFE-003 ruled away from the resolver, a
second workflow conversion is now the only live ignition.


## EVAL-003 — capture a comparable full routing anchor

### Source (narration)
Adaptation backlog's parked re-baseline analysis.

### Prerequisites (narration)
Run small watched foreground batches; fix case-design defects before treating
numbers as description evidence. (The measurement path ROUND1-001 established is healthy; that
item closed 2026-07-29 and is not a gate.)

### Dated addenda — Three facts established 2026-07-29
**Three facts established 2026-07-29 that shape this item:**

1. **The native `claude plugin eval` is still gated** — the subcommand now exists with ablation,
   graders, and JSON output, but invoking it returns "`plugin eval` is currently in early access"
   (checked at CLI 2.1.220). So `evals/README.md`'s stopgap framing remains accurate, and this
   anchor must still be captured with `scripts/eval_routing.py`. Re-check on CLI upgrades: when it
   opens, note that its case shape (`evals/**/case.yaml` or `prompt.md` + `graders/*.md`) is *not*
   the fleet's cluster JSON, so migration is real work, not a rename.
2. **Agent-expecting positives fire at ~0% in headless one-shot mode on the current tier** —
   0/21 in the Round 1 diagnose, 0/6 for ROLE-001's host cases, 0/6 for the auditor's, while
   sharp-trigger *skill* positives hit 100% (6/6 in the diagnose, 6/6 for `security-audit`). An
   anchor capturing agent positives at zero would record the harness, not the descriptions. Settle
   the case design — or grade agent members differently — before spending a full-suite capture.
3. **Configuration contamination is measured — and refuted as the agent-positive suppressor**
   (2026-07-29, phase 1 of this item). The
   [archived isolation outcome](../2026-07/verification-round-outcomes-2026-07-29.md) showed every eval session had
   been inheriting 134 operator-side entries, with the fleet registered twice (9 bare via the
   junction deployment + 9 namespaced via `--plugin-dir`). Under `--clean-room`
   (`scripts/eval_clean_room.py`; namespaced-only fleet, one plugin) the auditor's two agent
   positives still fired **0/6** under otherwise-identical conditions
   (both captures recorded in `baselines/history/2026-07-29-verification-round.md`: the clean-room
   0/6 against the same day's contaminated 0/6). The under-fire is a property of headless one-shot
   mode on this tier, not of the operator's configuration. Both runners now record `clean_room` in
   `conditions`, and artifacts differing on it must not be diffed against each other.

### Next action (full detail)
Decide the agent-member grading — the evidence-backed default is negatives-only
in routing, with each agent's contract covered by the pinned behavioral suite (`--agent` runs are
deterministic where routing summons are not) — then capture the anchor under `--clean-room`, whose
conditions the artifact now records. Isolation will not rescue agent positives; nothing further is
owed on that question.

### Original fields (pre-cut)
**Status:** `deferred`

**Outcome:** Establish one current, condition-complete baseline across all routing clusters.

**Source:** Adaptation backlog's parked re-baseline analysis.

**Prerequisites:** Run small watched foreground batches; fix case-design defects before treating
numbers as description evidence. (The measurement path ROUND1-001 established is healthy; that
item closed 2026-07-29 and is not a gate.)

**Acceptance:** Every artifact records requested/observed model, timeout, CLI version, threshold,
and per-run evidence; no known-invalid artifact is called an anchor.

**Next action:** Decide the agent-member grading — the evidence-backed default is negatives-only
in routing, with each agent's contract covered by the pinned behavioral suite (`--agent` runs are
deterministic where routing summons are not) — then capture the anchor under `--clean-room`, whose
conditions the artifact now records. Isolation will not rescue agent positives; nothing further is
owed on that question.


## RELEASE-001 — add repository release discipline

### Source (narration)
Archived roster expansion design.

### Prerequisites (narration)
A real plugin or repository release task demonstrates the consumer. Keep
pipeline implementation with `ci-actions`, merge readiness with `code-reviewer`, and running
service changes with `homelab-engineer`.

### Dated addenda — The platform already does part of this
**The platform already does part of this** (found 2026-07-29, CLI 2.1.220):
`claude plugin tag [path]` creates a `{name}--v{version}` git tag *and validates that `plugin.json`
agrees with the enclosing marketplace entry* — with `--dry-run`, `--push`, and `--remote`. That is
exactly the manifest-consistency check this item would otherwise hand-roll, so the component must
**consume** it rather than reimplement it, and the tagging step of its own release row is one
command. `claude plugin update` is the counterpart for a consumer refreshing an installed copy.

### Next action (narration)
Reopen before the next manually orchestrated release; start from `claude plugin
tag --dry-run` and write the component around what it does *not* cover (version choice, changelog,
publication, yank).

### Original fields (pre-cut)
**Status:** `deferred`

**Outcome:** On the next release-workflow task, add a bounded component for version choice,
changelog, tag, publication, and release rollback without absorbing merge verdicts, CI authoring,
or deployment authority.

**Source:** Archived
[`roster expansion design`](../2026-07/roster-expansion-design.md).

**Prerequisites:** A real plugin or repository release task demonstrates the consumer. Keep
pipeline implementation with `ci-actions`, merge readiness with `code-reviewer`, and running
service changes with `homelab-engineer`.

**Acceptance:** Routing cases distinguish release, CI, deploy, and merge-verdict requests; the
component states rollback boundaries; its first use performs the repository's actual version,
inventory, validation, tag, and publication sequence.

**Next action:** Reopen before the next manually orchestrated release; start from `claude plugin
tag --dry-run` and write the component around what it does *not* cover (version choice, changelog,
publication, yank).


## EVAL-004 — verify the accessibility imports behaviorally

### Source (narration)
Combined ECC import review, Batch 1 accessibility residue.

### Prerequisites (narration)
A real task involving a form, modal, drawer, custom widget, toast, or async status. Do not
manufacture a component solely to close this item.

### Original fields (pre-cut)
**Status:** `deferred`

**Outcome:** Demonstrate that a real UI task loads and applies form wiring or interaction
accessibility guidance and supplies keyboard-pass evidence.

**Source:** Combined
[`ECC import review`](../2026-07/ecc-import-review.md), Batch 1 accessibility residue.

**Prerequisites:** A real task involving a form, modal, drawer, custom widget, toast, or async
status. Do not manufacture a component solely to close this item.

**Acceptance:** Task packet names the applicable reference and provides keyboard/announcement
evidence; two observed misses trigger a dedicated behavioral contract and definition repair.

**Next action:** Evaluate on the next qualifying UI task.


## LAB-001 — provide a fallback service compose asset

### Source (narration)
Skills modernization Tier 2.

### Prerequisites (narration)
An onboarding task demonstrates that the target lab lacks a reusable pattern. Existing lab
conventions always win.

### Original fields (pre-cut)
**Status:** `deferred`

**Outcome:** Supply an annotated service block only for a lab that has no established compose
pattern, covering pinned image, restart, health, resource, and storage slots.

**Source:** Skills modernization Tier 2.

**Prerequisites:** An onboarding task demonstrates that the target lab lacks a reusable pattern.
Existing lab conventions always win.

**Acceptance:** Asset is linked skill-relative from `service-onboard`, contains no environment
specific defaults, and the validator's orphan/reference checks pass.

**Next action:** Reopen on the first qualifying service-onboarding task.
