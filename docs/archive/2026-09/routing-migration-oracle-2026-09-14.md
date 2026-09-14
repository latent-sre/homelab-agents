# MACH-001 phase 4 oracle: did handing the runner to `claude plugin eval` change any verdict?

## What the oracle had to be, and why the record's wording could not be taken literally

The decision record words phase 4's oracle as "one paired run under both instruments on the same
plugin bytes agrees on every case verdict". Read literally — two live batches, one per instrument
— it cannot work. Routing is stochastic: two batches of the same cluster disagree case by case
from variance alone, so the comparison would measure the model's run-to-run spread and say nothing
about the migration.

The claim that needs proving is narrower and sharper: **the migration changed no verdict.** So
both instruments grade the SAME runs. One live batch goes through the new path with its traces
preserved, and the retiring runner's own reader and scorer are then applied to those identical
traces. Any disagreement can only come from the code.

## The run

| | |
|---|---|
| Cluster | `prompt-tooling` (12 cases: 6 positive, 6 negative) |
| Runs per case | 3 (36 sessions, 36 traces, all matched to their case) |
| CLI | 2.1.270 (the CI pin) |
| Model observed | `claude-sonnet-5` |
| max_turns / timeout | 6 / 180s |
| clean_room | false |
| Plugin identity | `95810e765cf00922…` |
| Cost | $3.67 |

## Result: 12 of 12 case verdicts agree

Agreement was checked on four things per case, not just the pass flag: `passed`, `inconclusive`,
the count of runs excluded as unusable, and the per-run firing sets.

| case | old | new | agree |
|---|---|---|---|
| pos-skill-never-triggers | PASS | PASS | yes |
| pos-write-an-agent | PASS | PASS | yes |
| pos-ignores-instruction | PASS | PASS | yes |
| pos-tighten-tool-desc | fail | fail | yes |
| pos-fires-too-often | fail | fail | yes |
| pos-rewrite-system-prompt | fail | fail | yes |
| neg-backend-retry | PASS | PASS | yes |
| neg-write-runbook | PASS | PASS | yes |
| neg-optimize-sql | PASS | PASS | yes |
| neg-reword-error-message | PASS | PASS | yes |
| neg-multi-agent-design | PASS | PASS | yes |
| neg-quick-draft-not-prompt-engineer | PASS | PASS | yes |

The table is discriminating rather than uniformly green: three positives pass and three fail, so a
grader that simply answered PASS to everything would not produce it.

## Two ways this oracle was wrong before it was right

**A vacuous roster.** The first attempt loaded the retiring runner from a path outside the
repository. Its fleet roster is built at import from `Path(__file__).parents[1]`, so it resolved
empty, and with an empty roster nothing ever fires: every positive "failed" and every negative
"passed". That produced six confident disagreements that were entirely the oracle's. The runner is
now copied into `scripts/` for the comparison, and the corrected run asserts the roster is the
expected 30 components before comparing anything.

**A vacuous match.** The second attempt matched each trace to its case by the prompt, read from
the trace. The trace begins at the system `init` event and never echoes the prompt, so zero traces
matched and the comparison reported twelve agreements over nothing. The prompt lives in the
session history beside the trace (`config/projects/*/*.jsonl`), and the oracle now asserts at
least one trace matched before printing a table.

Both failures had the same shape, and it is the shape this repository keeps finding: a check that
passes because it examined nothing.

## What this oracle does NOT cover, measured rather than assumed

Mutating the new grader three ways and re-running the comparison:

| mutation | disagreements |
|---|---|
| drop `Task` from the routing tools | 5 |
| drop the skill-launch exemption | 0 |
| ignore `is_error` entirely | 0 |

The last two are not caught, and the reason is the corpus, not the code. Across all 36 traces
there were 17 routing calls, **zero** of which came back an error, and zero skill-launch control
signals. (The 21 errored tool results in the corpus are on other tools — a denied `Write`, a
`Glob` that matched nothing.) So this live oracle cannot exercise the `is_error` handling that is
the whole reason the verdict stayed fleet-side.

That semantics is covered instead by the synthetic differential recorded in
`native-grader-errored-spawn-2026-09-14.md`: 12,400 transcripts through the reader and 8,004
case/threshold/run combinations through the scorer, zero mismatches, with all seven injected
faults — the skill-launch exemption and the `is_error` filter among them — caught.

Together: the synthetic differential proves the semantics, this oracle proves they survive contact
with the real harness's own traces. Neither alone is the phase-4 evidence.

## One difference this oracle deliberately does not measure

Grading the same traces isolates the GRADING change, which is what "the migration changed no
verdict" means. It says nothing about whether the new harness produces different traces than
`claude -p` did — different allowed tools, a turn cap instead of a wall clock, and the
operator-surface contamination recorded in the companion note all can move rates. Those are
measurement CONDITIONS, and the benchmark records each of them so two artifacts that differ are
visibly not comparable. Any rate comparison across the migration boundary needs a fresh baseline,
not the stored pre-migration one.
