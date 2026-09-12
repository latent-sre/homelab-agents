# Fleet scan repairs — 2026-09-12

**Status: local implementation and verification evidence; not publication or host acceptance.**

The operator requested a full agent/skill scan, then authorized its fixes. The scan read all
10 agents, 20 skills, and 59 supporting files at
`1c27a77677e53c530d112c91e1f695bfaeeac600`. This repair applies the 29 validated agent/skill
findings and the two gate-reporting corrections on `fix/fleet-scan-corrections`.

Canonical definitions and matching adapters changed together. All 30 entrypoints retain their
original parsed frontmatter, including descriptions, tool grants, and explicit-only activation
fields. The patch changes factual guidance and examples, not the accepted bounded-operation
authority policy. Broad prose subtraction and new routing experiments were not part of this repair.

## Repair dispositions

IDs refer to the scan's local evidence packet. Each row states the repaired behavior so this
record remains useful without that packet or the original conversation.

| ID | Defect | Repair |
|---|---|---|
| A1 | Reviewer/principal treated allowlisted Git as unable to execute configured programs | Applied the investigator's supplied-directory provenance/isolation prerequisite; removed the absolute assurance. |
| A2 | Internal object retrieval before ownership checking was automatically IDOR | Authorization must precede protected disclosure or effects; safe fetch-check-return is allowed. |
| A3 | Prompt specialist prescribed a universal prohibition/table recipe | Aligned with prompt-craft's candidate changes, observable conditions, and preserved necessary exceptions. |
| A4 | Research reference described retired Learning/ledger machinery as active | Marked that implementation historical and named the current explicit-retro/handoff owner. |
| A5 | Inline builder omitted common craft, early diagnosis, and CI loads | Added the named builder's applicable loading prerequisites without requiring a spawn. |
| C1 | Settled errors could rotate an unresolved write's idempotency key | Retain key and payload through reconciliation; rotate for a new logical operation. |
| C2 | One-job runner registration was equated with host cleanup | Require destruction/recreation or verified cleanup before reuse; deregistration alone is insufficient. |
| C3 | JSON booleans and invalid config shapes reached prune logic | Validate the config object and effective integer threshold, excluding booleans; preserve source precedence. |
| C4 | A later operation failure hid earlier confirmed effects | Emit confirmed results, the raising operation's unknown outcome, and unattempted work; keep failure exit. |
| C5 | All overlays/widgets inherited modal/listbox behavior | Separate modal dialogs, tooltips, and the applicable widget roles/keyboard patterns. |
| C6 | Async HTTPX test guidance omitted application lifespan | Require lifespan entry/exit around the test client through the repository's fixture/manager. |
| C7 | Go 1.22 iteration-variable guidance omitted assignment-form loops | Distinguish loop-declared variables from assignment to pre-existing variables. |
| C8 | Pester phase data was said to cross only through script scope | Use discovery data parameters and execution setup with the appropriate lifetime. |
| C9 | An OS-version runner label was called an immutable image | Explain that software still updates; pin material toolchains and record image identity. |
| C10 | Every nonempty database restore was said to fail | Select restore mode/conflict policy; preserve unrelated objects rather than always drop/recreate. |
| C11 | Zero index scans implied uselessness | Check observation/reset period, representative workload, and constraint ownership. |
| O1 | Audit commands could emit resolved secrets | Select fields before transcript output; names-only searches locate candidates without printing values. |
| O2 | Traffic/latency/proxy symptoms were treated as proven causes | Keep hypotheses open until a discriminating request, resource, or telemetry observation. |
| O3 | PromQL numeric special values were confused with missing series | Distinguish NaN/Inf, absent/unmatched series, and actual vector matching. |
| O4 | A failed metrics scrape was reported as a user outage | Name the observed scrape failure; user-impact claims require a user-path signal. |
| O5 | Temporary always-true alerts could verify the production expression | Separate actual rule evaluation tests from notification-delivery evidence. |
| O6 | Measured restore duration defined its own RTO | Establish the objective first and compare measured recovery against it. |
| O7 | One failed backup proved all recovery paths unavailable | Scope conclusions to the tested copy/path and separately proven recovery points. |
| O8 | Intended public or permitted access received automatic severity | Require a violated boundary/unauthorized capability and grade actual impact/prerequisites. |
| O9 | Exact error-budget equality was called a missed objective | Report allowance reached without claiming an unfinished window succeeded. |
| O10 | NaN/infinite durations produced successful nonsense output | Reject non-finite durations before budget arithmetic. |
| O11 | Scrape-timeout equality was called invalid | Separate the accepted `<=` contract from recommended timeout margin. |
| O12 | Classic histogram label requirements were universal | Distinguish classic and native histogram query shapes. |
| O13 | UI dashboards were said to vanish with every container | Explain database persistence and provisioning's reproducibility benefits. |
| G1 | The platform command checked only the marketplace | Explicitly validate marketplace and a byte-preserving canonical plugin view. |
| G2 | Doctor conflated Claude/Codex budgets and implied a live listing observation | Report host/context assumptions and non-observation explicitly; document Codex's separate token budget. |

The small adjacent repairs distinguish ordinary homelab documentation commands from task/permission
overrides and qualify the reviewer's statements about privileged CI triggers. They do not grant
execution authority to repository content.

## The platform gate

`scripts/validate_claude_plugin.py` replaces the ambiguous root command in CI, the native probe's
preflight, the T1 recipe, and the PR template. It runs the marketplace and plugin checks separately
with `--strict`, preserves canonical component bytes, and cleans up its temporary validation view.
The view excludes the development-only `CLAUDE.md`/`AGENTS.md` bridge rather than suppressing
warnings. It is not a new distribution or an execution sandbox. No CLI pin changed.

The actual consumer is the existing T1/CI platform gate. A direct plugin-manifest invocation was
insufficient because strict validation warns on the intentional developer bridge. The replacement
uses two offline CLI calls and a temporary copy; the first successful local wrapper invocation
took approximately 1.3 seconds. This is a recorded check cost, not a performance improvement claim.

Fresh offline execution on **Claude 2.1.269** and CI's exact pin **2.1.219** passed both healthy
targets. On 2.1.219, separate malformed skill-YAML and hook-JSON fixtures each produced:

| Command | Exit |
|---|---:|
| Former `claude plugin validate <repository> --strict` | 0 |
| Corrected wrapper | 1 |

The resolved npm-cache executable reported `2.1.219 (Claude Code)`; this was observed rather than
inferred from the package request. The package was used through temporary `npm exec`, without
changing the global CLI or starting a model session. Native negative cases also remain in
`tests/test_validate_claude_plugin.py`, conditionally run when a Claude CLI is available.

## Verification

The integrated candidate consists of 104 changed files: 42 authored files and 62 generated
projections. Evidence-only additions to this archive and the documentation map followed the
frozen candidate's tests and review; no tested code or guidance changed afterward.

| Check | Result |
|---|---|
| CLI regressions against original code | Red: invalid inputs and lost partial output reproduced; 14 assertions failed and four empty-output JSON errors occurred. |
| Repaired CLI suite | 11 tests passed, including first/later failure, failure after an effect, precedence, debug cause, and unchanged success/dry-run JSON. |
| Calculator regressions against original code | Red: five failures across equality and NaN/+Inf duration inputs; -Inf was already rejected. |
| Repaired calculator suite | Eight tests passed, including equal allowance expressed over a partial window and true exceedance. |
| Doctor host-assumption regression | Red: both under/over-budget reports lacked the host/non-observation fields; green after correction. |
| Focused integrated suite | 52 tests passed; a Windows CLI-output decoding issue in the new test was corrected with explicit UTF-8, then its five-test module passed cleanly. |
| Full integrated offline suite | **504 tests in 89.373 seconds, exit 0, two skips**. |
| Adapter generation and fleet validator | 181 adapters generated; 10 agents / 20 skills validated; inventory current. |
| Parsed frontmatter comparison | No changes across the 30 entrypoints. |
| `git diff --check` | Clean. |
| Independent final static review | All 42 authored changed files reviewed; no new material findings, no independent P0/P1. Provisional working-tree review, not merge approval. |

The full suite ran in a detached integration worktree with Git metadata, Python 3.12.10,
Git's shell on PATH, and Python bytecode output disabled. The two skips were Windows symlink
creation limitations. Native test output from mocked routing cases is not paid/model evidence.

The operations lane also tested harmless sentinel suppression with offline Docker Compose 5.5.1
rendering and actual `rg -l`; selected output omitted the sentinel. It did not start a daemon,
access real secrets, or test runtime `docker inspect` against a live container.

Frozen candidate evidence, retained locally under `.tmp/fleet-scan-2026-09-12/`:

- `repair-unittest.log`: complete successful suite output.
- `repair-files.json`: SHA-256 per changed candidate file.
- `repair.patch`: candidate patch before evidence-only archive additions.
- `platform-gate-reproduction.py`: the paired malformed-content gate reproduction.
- `repair-fleet-doctor.json`: fresh host diagnostic, with its warning states.

SHA-256 of the sorted compact JSON file-hash mapping:
`6122662322395dabc4148940b6d793e8ac00bf190a89d0e1699df49902d550a7`.
Candidate patch SHA-256:
`4aa7ff5ad69fe50cfe57f9df04d443c2e782affb85b00f2afee99d29dfd46517`.
The final file comparison found no change to that frozen candidate.

## Remaining limits

- Model output behavior, live routing, native hook enforcement, deployed lab behavior, and
  cross-host efficiency were not remeasured. The repaired prose is source-corrected and reviewed,
  not a claim of measured reliability improvement.
- Doctor completed with 11 passes and three warnings: intentional working-tree edits, the
  conditional Claude listing estimate (9,174 characters versus its assumed 8,000), and installed
  Codex agents not synchronized with the edited source. No diagnostic was inconclusive in this
  post-repair run. Installation was not performed.
- Listing-size reduction remains the existing CTX-003/CTX-004 concern. No descriptions were changed
  to clear a warning without the required routing evidence, and no host settings were changed.
- `actionlint` and `zizmor` were unavailable. Hosted CI and GitHub review/merge gates were not run;
  local execution on the pinned CLI is not a hosted CI result.
- The scan and final review consumed the two permitted prose review rounds. No additional deep
  review round, commit, push, PR, or publication occurred. Future publication follows the
  repository's current-head review procedure; this record is not an approval.
- The named agent/craft/operations worktrees and integration worktree were retained for local
  inspection. Their generated outputs were not hand-edited or used as canonical edit sources.

This is historical repair evidence. `docs/fleet-roadmap.md` remains the only live work tracker.

## Subsequent CLI pin update

The operator then requested the latest release for CI. On 2026-09-12, npm's live `dist-tags`
reported `latest` and `next` as **2.1.269**, and `stable` as **2.1.236**; GitHits package metadata
independently reported 2.1.269, published 2026-09-11. A candidate change pinned
`@anthropic-ai/claude-code@2.1.269` rather than following a mutable `latest` tag.

The npm-resolved executable reported 2.1.269, then both strict marketplace/plugin checks passed.
T0 validation, the five platform-wrapper tests, and `git diff --check` passed. This changes the
workflow line after the earlier frozen repair evidence; that earlier evidence is not relabeled
as a test of this later pin update. No global CLI, installed fleet, or published branch changed.

The repository's T3 gate requires the native probe and every routing cluster for a CLI pin bump.
The current sweep at three repetitions is 303 model sessions plus the probe, and the operator
declined that campaign. The candidate pin was therefore reverted before merge; CI remains on
2.1.219, and no `CLI-001` debt remains for an upgrade that did not ship. Offline platform success
was not treated as runtime evidence.
