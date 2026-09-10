# Group 1 rescan — paired capture for the lab-incident edits (2026-08-13)

Its `before/` and `after/` captures retired to Git history on 2026-08-17 under the retention rule
in `../README.md`, and **this file is their record** — the checkout no longer contains them.
Recover the whole directory with `git show f4b119c:evals/baselines/2026-08-13-group1-rescan/` (or
a single file by appending its path); `f4b119c` is the last revision that carried it.

One case, `incident-mitigate-first`, measured before and after two body edits to
`skills/lab-incident/SKILL.md`: the Step 3 note-durability clause (the timestamped note is emitted
as you go, because a session that ends mid-incident takes everything unwritten with it) and the
Step 4 authority-edge clause (the outage→follow-up downgrade is what ends the mitigate-first
inversion).

**Why paired:** the file is graded by this contract, and the PROP-002 round measured an
adjacent-sentence edit degrading a sibling contract 3/3 → 2/3 → 1/3 (the adjacent-context-bleed
correction in `docs/archive/2026-08/prop-002-scan-findings-2026-08-13.md` (retired to Git history)). An unmeasured edit to
contract-graded text knowingly repeats that pattern.

**Conditions, identical both sides:** sonnet, `--clean-room`, 3 runs, this container's CLI
(recorded in each `benchmark.json`'s conditions block with provenance). `before/` is the
pre-edit bytes (`dcd8954`); `after/` is the edited bytes with regenerated adapters.

**Verdict:** 3/3 == 3/3. Both edits kept. n=3 per side — the claim is the paired direction under
identical conditions, not statistical significance.
