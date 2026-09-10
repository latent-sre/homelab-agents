# GRAPH-003 adjudication — the rival graph proposal, verified and absorbed — 2026-08-01

**Status: historical decision evidence.** The operator's ruling and the verification that
grounded it. The governing outcomes live in the two decision records and the roadmap; this file
is dated evidence, never a task list.

## The collision

The operator accepted the revised
[`AI graph engineering decision`](../../decisions/2026-07-31-ai-graph-engineering.md) on
2026-08-01 during the WF-001 round. In the same window, PR #54 merged the independently authored
[`graph control-plane proposal`](../../decisions/2026-08-01-graph-control-plane.md) to `main` —
the side-by-side adjudication its provenance section anticipated never happened. GRAPH-003 named
the collision; this review executed it.

## Verification results

Every checkable repository claim in the rival record was verified against the tree
(post-merge `main`, 2026-08-01) and **all held exactly**:

| Claim | Result |
|---|---|
| `contract_digest` dangling — stored/validated/echoed (`run_state.py:104,248-271,886`), resolved by nothing | [verified] |
| Tasks table flat: no dependency/join columns (`:110-119`); eligibility gate only `pending/failed` (`:393`) | [verified] |
| Schema v1 hard-rejects other versions, no migration (`:174-177`) | [verified] |
| A host-native workflow already in-tree, unwired to any ledger (`.claude/workflows/multi-lens-review.js`, tracked since Jul 19) | [verified] |
| 184 cross-reference edges (per-file dedup over all tracked md) | [verified] — exactly 184; the accepted record's 140 uses a narrower rule (cores only), both correct |
| 85 tool-authority edges | [verified] — exactly 85 (YAML-list `tools:` blocks parsed, not just single-line forms) |
| Workflow resume is session-scoped cache (host docs) — checkpoints structurally cannot be the ledger | [verified] — matches WF-001's own round-3 research |

**One citation downgraded:** the record cites *"Graph engineering" (Thariq Shihipar, Anthropic,
with Peter Steinberger, mid-2026)*. Shihipar is real (Claude Code team; author of the
context-engineering post both records cite), but no primary "Graph engineering" publication by
him was findable — the term still traces to Steinberger's 2026-07-18 X post with the
org-graph/work-graph framing carried by secondary blogs. Consistent with the accepted record's
misattribution-chain finding; the rival had itself flagged the domain as unfetchable. The
downgrade does not touch its repository-local case, which was verified in full.

## Corrections to this repository's own story, surfaced by the review

- WF-001's "first workflow" framing holds only for *plugin-shipped*: a project-level workflow
  (`multi-lens-review.js`) predates it by two weeks and was missed by both the round's fresh-main
  survey and its docs. The rival caught it.
- The two records' differing edge counts (140 vs 184) are both correct under their stated
  counting rules — a reminder that topology numbers need their counting rule attached, which is
  itself an argument for the GRAPH-002 derived artifact.

## The ruling

**Absorb** (operator, 2026-08-01): the acceptance stands as the adjudication; the rival is
Superseded (absorbed), not Rejected. Absorbed into the accepted record: the by-construction
ledger argument and the generated-prompt provenance control. Absorbed into the roadmap:
SAFE-003 (`contract_digest` repair) and GRAPH-004 (typed edge-contract pilot, trigger-bound).
Rationale: the rival lost the race, not the argument — the records converge on every
load-bearing boundary (no repo-owned executor, host runtime owns execution, derived topology is
evidence not authority), and its distinct contributions are verified and cheap to keep.
