# Selected recommendation review and corrections — 2026-09-07

The operator selected recommendations **3, 4, 5, 6, 7, 10, 13, and 21**, with a pre-edit stop
condition: stop and report if the recommendation was incorrect or required a substantial change.
All eight survived source review. The corrections are confined to ten canonical guidance files
and their twenty generated projections; no description, tool grant, roster, or runtime mechanism
changed. Work follows `8d01aad` on `refactor/consolidate-design-ownership`.

Main advanced separately to `5ab9903` through PR #176. Its diagnostic-gate changes do not alter
these selected source files. This batch preserves the existing branch's earlier repairs.

## Pre-edit findings and disposition

| Item | Evidence and verdict before editing | Correction |
|---|---|---|
| 3 — researcher example | HTTPX 0.27.2 already distinguishes omitted timeout from explicit None; 0.28.0 retains that behavior. The claimed upgrade change is wrong. | Use a version-pinned example with real links; label hypothetical caller evidence and omit stale latest-release/advisory claims. |
| 4 — failure diagnosis | The agent treated undesired output as proof of an ambiguous specification. A correct tool call returning 401 is a counterexample. | Inspect loaded instructions, context, tool and runtime evidence before selecting a prompt change; keep routing and variance diagnoses conditional. |
| 5 — draft/repair/tuning | The skill offers first drafts but required a prior observed failure for every edit and handoff. | Carry requirements for drafts, evidence for repairs, and a baseline/metric for tuning through method, handoff, and change packet. Preserve honest untested labels and paired measurement for improvement claims. |
| 6 — model-generation claims | No primary source substantiated the cited 80% reduction. The context article recommends compact representative examples. Absence of support does not prove the numerical claim false. | Remove the unsupported attribution and universal trend; evaluate simplification and example changes on representative tasks. Preserve security and authority invariants. |
| 7 — HTTP methods | RFC 5789 does not guarantee PATCH idempotency; repeated increment/append can repeat effects. | Define retry behavior per operation, with supported deduplication/preconditions and unknown-outcome reconciliation. |
| 10 — UI stack | Mantine officially supports third-party styling and documents Tailwind integration. | Preserve the chosen stack and deliberate integration; coordinate versions, reset ownership, CSS order/layers, and tokens, then check rendered states. |
| 13 — unresolved postmortem | Recovery can be established while cause remains unknown. The old template equated recovery with cause removal. | Permit a factual record with explicit uncertainty, investigation owner/evidence/reopen trigger; distinguish investigative actions and verified recovery from a speculative fix. |
| 21 — context/tool hypotheses | A total tool count cannot establish actual loaded-schema cost under deferred discovery. Truncated reads, changed files, and expired access are alternative causes of the listed symptoms. | Diagnose from discriminating observations; restructure tools or reset context only when evidence supports the intervention. |

No pre-edit stop condition was triggered. The prompt specialist independently challenged items
4/5/6/21 before changes; the parent checked primary sources for the technical claims and the
remaining selected recommendations. This did not reopen unselected security-severity, audit,
restore-isolation, or catalog-budget work.

## Verification and its limits

The [fixed scenario inputs](selected-guidance-cases-2026-09-07.json) and
[source identities, check exits, and output excerpts](selected-guidance-evidence-2026-09-07.json)
preserve the comparison for review. Assessment was manual; this is not a new executable evaluator.

- Validator: **10 agents / 20 skills**, generated parity and inventory current. Regeneration
  emitted 179 adapter files. A diff search confirmed component metadata was unchanged.
- Full suite on the final canonical bytes: **494 tests in 83.600 seconds, OK with 2 skipped**,
  process exit 0. Git whitespace check passed. Claude strict directory validation passed for the
  marketplace manifest; it is not a native plugin-loading verdict.
- Ten source fingerprints were captured before and after the test process; they matched.
  Baseline sources were captured directly from `8d01aad` before edits.
- Two final source-following comparisons used fresh default Codex subagents with identical case
  tasks and the same read-only exercise restrictions. Each side answered eleven scenarios:
  HTTPX, retrieval 401, new draft, existing repair, model upgrade, PATCH retry, deliberate Mantine
  integration, unknown/known-cause postmortems, deferred tools, and misleading context symptoms.
  The baseline and final candidate each had two fresh batches; each final batch met the intended
  case behaviors. Inputs and canonical sources were fixed across those final comparisons.
- Baseline agents already worked around most incorrect instructions. Both baseline HTTPX answers
  appropriately declined to establish the unsupported version claim; both final answers supplied
  the corrected guidance-backed answer while preserving external-verification and local-code
  limits. This supports improved source accuracy and answerability, not a general model-quality
  or routing-rate claim. No baseline agent invented an upgrade fact to satisfy the example.
- Both final unknown-cause records explicitly retained unresolved cause, unverified data-loss
  status, Sam's investigation ownership, and a recurrence/new-evidence reopen condition. The
  known-cause controls retained established causality. No exercise claimed actual filing, lab
  operations, browser tests, or external research.
- An initial comparison preceded the final small consistency edits and is not counted as
  final-byte evidence. The two static review stages were the pre-edit gate and final review.
  Final review found retained failure-only handoff/changelog and routing/variance clauses; those
  were corrected and verified by source inspection, the final paired exercises, and the full
  suite. No third static round was requested.
- These are source-following exercises, not native activation tests or a new evaluator framework.
  No description changed, so this batch does not claim a routing experiment. Earlier native
  routing/hook evidence owed by DESIGN-001 remains separate.

The ten complete canonical files grew from **58,020 to 62,235 Unicode characters** (+4,215),
measured on this machine with normalized text reads. This includes metadata and conditional
references, not just startup context. The additional text makes conditions and diagnostic checks
explicit. No token-cost, latency, or general performance improvement is claimed.

## Primary evidence

Context7 established current HTTPX and Mantine documentation contracts. GitHits read HTTPX's
0.27.2 implementation and Mantine's upstream integration page. GitHits returned a backend error
for HTTPX 0.28.0; the matching tagged upstream file was then read directly.

- [HTTPX 0.27.2](https://github.com/encode/httpx/blob/0.27.2/httpx/_client.py#L68-L85)
  and [HTTPX 0.28.0](https://github.com/encode/httpx/blob/0.28.0/httpx/_client.py).
- [RFC 5789, section 2](https://www.rfc-editor.org/rfc/rfc5789#section-2).
- [Mantine third-party styling](https://github.com/mantinedev/mantine/blob/master/apps/help.mantine.dev/src/pages/q/third-party-styles.mdx)
  and [CSS layer guidance](https://mantine.dev/styles/mantine-styles/).
- [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).
  The selected correction removes an unsupported attribution; it does not assert that the
  underlying numerical claim was disproved by search absence.
- [Google SRE follow-up rigor](https://sre.google/workbook/on-call/): when the cause cannot be
  established, improve the evidence available for the next occurrence. Preserving a factual
  unresolved postmortem is this fleet's application of that principle.
