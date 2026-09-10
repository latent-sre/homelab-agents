# `evals/baselines/` — what is actually in here

The name is aspirational. A **baseline** is a stored capture a future paired run can reuse as its
'before' side, and no capture in this directory qualifies for that job — every routing cluster
resolves `STALE` against the current evaluator/plugin identity, and the script that once automated
that check (`eval_baseline.py`) was retired 2026-09-01. What remains here is retained for a
narrower reason: something outside this directory still names it or still needs it.

**2026-09-01 consolidation.** Every raw capture no live document reached — an uncited directory,
or a cited one whose summary already carried its outcomes — was `git rm`'d in one pass. **2026-09-02
consolidation.** The operator's closure of CTX-002, LEARN-002, HANDOFF-001, and LADDER-002
(`docs/decisions/2026-09-02-single-operator-audience.md`) removed the pins those four items held on
this directory; every capture they pinned and nothing else was `git rm`'d in a second pass. Neither
pass's bytes are gone: `git show <rev>:<path>` recovers any of them from history before this commit.
What is left below is only what a live document (`docs/fleet-roadmap.md`, `docs/README.md`, a
decision record, `evals/README.md`, or a script/test) still links to, names by path, or states an
explicit reason to keep.

## `history/` — round records, no captures

Distilled measurement records: what a round measured, under what conditions, and what it concluded.
The only thing most citations actually consume. These are archive records that happen to sit next
to the suite they describe; if `docs/archive/` ever becomes their home instead, nothing breaks but
the paths.

Mostly Markdown, with one exception that states the rule for any future one:
`2026-08-15-learn-002-tool-events.json` is raw `stream-json` retained **because its record's claim is
not checkable without it** — the `allowed_tools: []` finding turns on `tool_use` blocks correlated
with their results, and the behavioral runner grades and discards the transcript. Distillation is for
evidence a summary can carry; a record that says "the raw is why you can believe this" keeps its raw
beside it, named for the record it belongs to. Retiring this file once (PR #145) broke exactly the
claim it backed, which is how the exception earned its sentence here.

## What survives outside `history/`, and why

Every one of these is named by path (or by an explicit retirement condition) in a live document.
Where only a directory's summary is named, its raw capture was cut; where a live document says a
capture must not retire yet, the raw stays until that condition is met.

- **`2026-07/README.md`, `2026-07-24/behavioral/README.md`, `2026-07-24/homelab-ops/README.md`** —
  self-contained routing/behavioral narratives (every rate, every case) named by `evals/README.md`
  as historical cluster anchors for `homelab-ops`'s pre-/post-`postmortem` membership shapes.
- **`2026-07-31-p0-p1/host-conformance/`** — the only Codex CLI run this repository has ever
  recorded (`codex-cli 0.145.0`), cited by exact version in `evals/README.md`. Unrelated to the
  2026-09-02 closures.
- **`2026-08-01-self-improve/README.md`** — the LEARN-001/LEARN-002 round's distilled record: every
  generation's rates, verified against the captures before any were removed. `final-live/` was the
  one raw capture this directory still held, kept only while `docs/fleet-roadmap.md` cited it as
  LEARN-002's live rates; LEARN-002 closed 2026-09-02 (won't-do), so that pin is gone and
  `final-live/` retired with it — the README's own text records the change and every rate it held.
- **`2026-08-10-gate-001-first-live/verifier.json`** — `scripts/packet_lint.py` quotes this file
  verbatim as the worked example of an honest no-evidence verification packet.
- **`2026-08-10-rel-173/conditions.md`** — cited by `evals/README.md` for the pre-correction `1.7.3`
  skill-inventory count. Unrelated to the 2026-09-02 closures.
- **`2026-08-13-prop-001/README.md`** — already summary-only; unrelated to the 2026-09-02 closures.
- **`2026-08-14-ladder/`** — kept whole (`benchmark.json` and `decisions.md`) as the stored
  LADDER-001 capture. Both former external pins are gone: `docs/README.md`'s inventory row naming
  this exact directory path went with that record's retirement to Git history, and LADDER-002
  closed 2026-09-02 (won't-do). The directory is retained on its own account as capture evidence —
  delete it only against a fresh reading of what still cites it.
- **`2026-08-18-ctx-002/`** — `before/`, `after/`, `after-repair/`, and `decisions.md` stay:
  `decisions.md`'s own retirement trigger requires **both** CTX-002 and LANE-001 closed before this
  raw retires, and LANE-001 is still `ready` on `docs/fleet-roadmap.md`. CTX-002 itself closed
  2026-09-02, but that satisfies only half the trigger. `disposition/` did not wait for that pair —
  `decisions.md` states its retirement is unconditional on CTX-002's own close ("`disposition/`
  retires with CTX-002's close regardless"), so it retired in this pass while its siblings stay.
- **`2026-08-19-eval009/decisions.md`** — already summary-only (its raw retired in the 2026-09-01
  pass); a self-contained record unrelated to the 2026-09-02 closures.
- **`2026-08-29-gate-006/README.md`** — a comprehensive distillation cited by path from
  `docs/decisions/2026-08-29-homelab-live-effect-gate.md`. Unrelated to the 2026-09-02 closures.

## What retired 2026-09-01/02, and why

Raw captures pinned only by CTX-002, LEARN-002, HANDOFF-001, or LADDER-002 retired once the
operator's 2026-09-02 ruling closed all four
(`docs/decisions/2026-09-02-single-operator-audience.md`) — their bytes live in git history before
this commit, not in this directory:

- **`2026-08-11-ladder/benchmark.json`** — its only trigger was "retires when LADDER-002 closes."
- **`2026-08-12-handoff-001-diagnostic/`, `-digest-diagnosable/`, `-digest-outcomes/`,
  `-digest-reader/`, `-digest-refix/`, `-producer-amended-x3/`, `-producer-x3/`, and
  `2026-08-18-handoff-001-producer-r2-x3/`** — the salvaged 2026-08-12 sonnet-testing arc and its
  rerun; their triggers were producer-contract and digest-mismatch conditions inside LEARN-002's and
  HANDOFF-001's second batches, neither of which will now happen.
- **`2026-08-19-settling/`** (raw and its gitignored `failing-run-evidence.json` sidecars) — its
  trigger was LEARN-002's second settling batch and HANDOFF-001's confirmation run, both won't-do.
- **`2026-08-01-self-improve/final-live/`** — LEARN-002's pin lifted; see above.
- **`2026-08-18-ctx-002/disposition/`** — its own unconditional CTX-002-close trigger fired; see
  above.

## The retention rule for anything added here going forward

A raw capture retires once a summary carries every outcome it would be consulted for, **and** no
live document states a reason it must still exist raw (a pending pair, an unmet retirement
trigger, a fact only the raw contains). Write the summary before deleting anything — a citation
survives deletion, the ability to check it does not — and if a live document ties a capture's
retirement to a condition, name that condition in the capture's own note so the next consolidation
pass does not have to re-derive it from context.

## If you are adding a capture

It goes in a new dated directory here (`--output-dir`), and it owes a summary in the same change —
either beside it or in `history/`. That is what makes it retirable later without losing what it
measured.
