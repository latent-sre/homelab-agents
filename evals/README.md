# Routing evals

`agents/prompt-engineer.md` mandates eval-first prompt changes — baseline, repetitions, fresh
contexts, measured against a previous version. The fleet shipped none, so it preached a practice it
didn't follow. This directory is that practice: it measures whether a realistic request **routes to
the right agent or skill**, and whether near-miss requests that only share vocabulary route
elsewhere.

## Why routing, and why here

The agents and skills have deliberately overlapping remits — `prompt-engineer` (agent) and
`prompt-craft` (skill) both cover "creating or fixing anything an LLM consumes"; `sde-fullstack`
overlaps `backend-craft`/`frontend-craft`; `homelab-engineer` overlaps `service-onboard`,
`lab-audit`, and `runbook`. Overlap is fine — until a description drifts and a request starts landing
on the wrong member. Nothing measured that, so nothing would catch the regression. These evals do.

## Format

Cases follow the [Agent Skills eval shape](https://agentskills.io/skill-creation/evaluating-skills)
(a realistic `prompt` plus an expectation), adapted so the graded assertion is a **routing fact read
off the transcript** — which component actually fired — rather than output quality. That makes
grading deterministic and free (no judge model). One file per overlap cluster under `routing/`:

```json
{
  "cluster": "prompt-tooling",
  "members": ["prompt-craft", "prompt-engineer"],
  "cases": [
    { "id": "pos-...", "prompt": "...", "polarity": "positive",
      "expect_fires": ["prompt-craft", "prompt-engineer"], "tags": ["..."] },
    { "id": "neg-...", "prompt": "...", "polarity": "negative",
      "expect_not_fires": ["prompt-craft", "prompt-engineer"], "tags": ["near-miss"] }
  ]
}
```

- **positive** — an expected cluster member should fire.
- **negative** — a near-miss that shares vocabulary (write / fix / optimize / rewrite) but should
  route to NO cluster member.

`expect_not_fires` is what a negative is graded against, and it defaults to the whole cluster — so
an ordinary near-miss passes only when nothing in the cluster fires. A case may **narrow** it to
name a *disambiguation* boundary instead: the components that must not fire, while a named sibling
legitimately may. `neg-resolved-not-incident` is the clearest one — an already-resolved outage
must not reach the mitigation skills, but `postmortem` (a cluster member) is the correct
destination, so grading it cluster-wide failed the case for its sibling doing the right thing. Keep
the narrowing rare and visible: it is a declared exemption, the runner prints the forbidden set it
actually used, and every name in it must be a cluster member (a typo would forbid nothing and pass
vacuously).

**Narrowing is no longer rare, and that is a measured coverage cost** (counted 2026-09-07:
**16** of 60 negatives narrow to a strict subset of their cluster). Each narrowing buys a correct
verdict for one disambiguation and gives up over-trigger detection for every member it stops
forbidding, so a cluster that narrows most of its negatives stops watching most of its members:
`continuous-improvement` narrows **6 of 6** negatives to a single forbidden component each,
leaving five of its six members with no over-trigger coverage in that cluster at all, and
`agent-systems` narrows 3 of 3, leaving `principal-engineer` uncovered. Read a narrowed
cluster's clean negative side as "no member named in these exemptions over-fired", never as
"nothing in this cluster over-fires". Before adding a narrowing, prefer reshaping the prompt —
that is what the `ladder` cluster's `neg-embedded-decision-not-principal-owned` repair did, and
its note records why firing-based grading cannot express "may fire, for the right reason".

**A negative earns its session by being *near*.** The definition above is load-bearing: a near-miss
*shares vocabulary* with the components it must not reach. A prompt that shares nothing with any
member is a **far**-miss — it passes almost by construction, and it proves less than the tight cases
in the same cluster already do, because a description broad enough to catch a far-miss would be
catching every near-miss too. Three such cases were retired from `prompt-tooling` on 2026-08-17
(a PR-review request, a lab-audit request, and a build-a-dashboard request, none of which shares
vocabulary with `prompt-craft` or `prompt-engineer`); the six that remain each name their shared
term in `expected_output` — "'optimize' is shared vocabulary, but a query is not a prompt", and
`neg-reword-error-message`, which the file itself calls the tightest near-miss in the set. When you
add a negative, state the vocabulary it shares. If you cannot, it is a far-miss and the sessions are
better spent elsewhere. The exception is a cluster whose *whole purpose* is distance:
`proportionality` is negative-only and deliberately fires trivial asks at heavy components, so low
overlap there is the measurement rather than a defect.

**A prompt with a deictic reference must carry its referent.** Every run executes in a fresh empty
working directory, so "assess this change" or "review this branch" has nothing to point at, and the
*correct* behavior — asking for the missing artifact — scores zero. Eleven such cases existed as of
2026-08-17: seven left with the agent-only positives and four now inline their artifact
(`pos-engladder-assess`, `craft-vs-fullstack`'s `neg-review`, `pos-engladder-growth-feedback` with a
body of eight PRs and design notes, and `pos-iterate-draft` with its draft, findings, and checklist).
Supplying the artifact in the prompt is the pattern the retired behavioral suite used. On the
negative side the defect is quieter and worse: a near-miss with no referent has nothing to route to,
so its pass was never evidence of a correctly narrow description.

This paragraph used to claim the class was empty at nine cases, and it was wrong twice over — the
same change that retired seven added `pos-engladder-growth-feedback` with the defect, and the sweep
that caught it also found `pos-iterate-draft`, which predated the change. So the claim is no longer
prose: `test_no_prompt_points_at_an_artifact_it_does_not_carry` fails any short prompt that points at
an artifact it does not supply. Emptiness asserted in a README is worth what the last author's grep
was worth.

The runner rejects any polarity other than literal `positive` or `negative`, a positive case with
no valid `expect_fires` member, an explicitly empty or invalid negative target set, and a threshold
outside `(0, 1]`. These are configuration errors, not low scores: each could otherwise make a case
pass without testing the declared routing boundary.

## Running

The runner takes **one cluster file per invocation**, and defaults to `prompt-tooling.json` when
given none — there is no all-clusters mode, so "I ran the evals" without naming a file means one
default cluster was measured:

```bash
# one cluster, 3 runs per case (the methodology's default), ~4 parallel
python3 scripts/eval_routing.py evals/routing/prompt-tooling.json --runs 3

# every cluster — what "the full suite" actually takes
for f in evals/routing/*.json; do python3 scripts/eval_routing.py "$f" --runs 3; done

# cheap smoke check of ONE cluster (prompt-tooling, the default)
python3 scripts/eval_routing.py --runs 1

# just the negatives, still one cluster at a time
python3 scripts/eval_routing.py evals/routing/homelab-ops.json --case 'neg-*'

# a run whose numbers will be COMPARED to another's: pin the model, and give a slower
# model room to reach its first tool call before the timeout cuts the session
python3 scripts/eval_routing.py evals/routing/homelab-ops.json --runs 3 --model opus --timeout 420
```

### Pin the model, or the comparison is not one

**`--model` is required for any run you intend to diff against another.** Without it each session
takes whatever the CLI defaults to, and that default is **not** inherited from the session that
launched the runner — a `/model` change in an interactive session does not reach the eval's
child sessions. This silently invalidated a comparison here: two runs of `craft-vs-fullstack` believed to
differ by model tier were both sonnet, so their near-identical results said nothing about the tier.

Every `benchmark.json` therefore records a `conditions` block — `cli_version`, `model_requested`,
`models_observed` (read off the transcripts, i.e. what actually ran), `timeout_s`, `threshold`,
concurrency, Python runtime, and non-secret authentication/provider mode. Its provenance separately
hashes the exact eval definitions, selected cases, plugin under test, and executing evaluator and
grader files. Both runners self-bootstrap from one checked source buffer and compile imported
graders from likewise registered buffers, so those hashes name what executed rather than a later
read of the same paths. Provenance schema v4 executes a private copy of the identified plugin bytes,
so an A -> B -> A edit to the source checkout cannot make concurrent sessions load mixed content
while leaving equal endpoint hashes. Persistent mutation of the private snapshot aborts the artifact. A
same-user session can transiently mutate and restore that snapshot unless the host sandbox denies
writes; endpoint hashing does not claim to detect that, so host write isolation remains part of the
trust boundary. The conditions block records `.` for the current plugin and
`<external-plugin-dir>` for any external baseline; the content identity carries the comparable
provenance without publishing an operator account or workstation path. A benchmark without these
identities is not a baseline: it cannot state what it measured. If a single run mixes models, the
runner also says so loudly.

### `INCONCLUSIVE` is not a failure

A run whose transcript cannot support a verdict — a timeout cut before anything fired, a spawn that
produced nothing — is **excluded from the rates**, and a case whose every run was excluded is
reported `INCONCLUSIVE` rather than failed. A measurement failure and a routing failure are
different facts, and conflating them sends you to audit descriptions when the problem is the clock.
When you see it, raise `--timeout` and re-run those cases; they are evidence in neither direction.

The test is usability, not silence. A session that reached a non-error `result` event **is** graded
for routing even if the CLI then exited non-zero — it routed somewhere, possibly off the fleet
entirely, and that is a real negative sample and a real positive miss. A structured error result is
never a no-route sample; a component firing observed before that error may remain explicitly
labeled partial evidence. The retired behavioral suite's assertions were stricter: they required
exit zero and a final non-error result. Authentication failure, missing namespaced fleet
registration, or absence of any agent member in the selected routing cluster aborts the whole
batch with exit 2 and writes no benchmark. These rules prevent quota, API, runner,
expired-session, partial-plugin, or absent-plugin
state from becoming a false green.

The default 180s timeout was tuned when sessions were faster. A more deliberative model can spend
longer than that before its first tool call, so **the timeout and the model are one decision** —
pin both together, and both are recorded in `conditions` (`timeout_s`, `model_requested`) because
a shorter timeout excludes more runs and therefore moves every rate in the artifact.

`claude plugin eval` runs the sessions; the fleet grades them. The cluster JSON is projected into
native case directories under `evals/generated/` (git-ignored, rewritten every run — edit the
cluster, never the generated copy), and the harness owns isolation, per-case runs, concurrency,
cost ceilings and its own JSON result and HTML report.

**The verdict is not the harness's.** Its `tool_used` graders are kept as a tripwire, but the
score is computed by `fleet/routing.py` from each run's trace, for two measured reasons
(`docs/archive/2026-09/native-grader-errored-spawn-2026-09-14.md`): `tool_used` counts a call
whose input matches whether or not the spawn SUCCEEDED, so on a positive a regression can hide
behind a dispatch that never landed; and a positive passes when ANY expected destination fires, a
disjunction that spans the Agent and Skill tools in every multi-target positive here and that no
combination of `tool_used` graders can state.

**The routing competition is recorded as observed, never as requested.** Read off real sessions'
own `init` events on 2026-09-14: the harness sets its own config directory, so the operator's
personal components do **not** reach the child — but sixteen of the CLI's own bundled skills do,
`code-review`, `debug` and `verify` among them, all competing for the same routing decisions.

`--clean-room` relocates `CLAUDE_CONFIG_DIR` (`scripts/eval_clean_room.py`) and was measured to
change **nothing** here: the child's surface was byte-identical with and without it, because the
harness overrides the variable. It is kept for a non-native caller and recorded as
`clean_room_requested`, which is what it is — a request, not evidence. The condition that matters
is `components_observed`, read off each session's own `init` event. Two artifacts whose non-fleet
components differ measured different competitions and must not be diffed as one baseline, whatever
either run's flags claimed.

`CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1` does shrink that surface (sixteen non-fleet skills to one,
measured the same day) and is deliberately **not** set: bundled skills are identical on every
machine for a given CLI version, which `cli_version` already records, so they are part of the
platform the fleet routes against rather than per-operator contamination. A baseline without them
would measure a surface no real user has.

**`--max-turns` is a measurement condition, not a convenience.** A routing decision missed because
the session ran out of turns is not a routing failure, and the runner does not score it as one: a
run counts as a measurement only when something fired or the session reached a non-error final
result. Everything else is excluded and reported, so a rate always says how many runs it rests on. The runner prints per-case pass/fail and rates; pass `--output-dir <path>`
to also write a `benchmark.json` there for before/after diffing. Exit codes separate the two things
you would do about them — `0` all passed, `1` a case failed (a routing verdict to investigate), `3`
nothing failed but something was `INCONCLUSIVE` (re-run it; nothing was measured), `2` a usage,
authentication, or registration error for which no benchmark was written. You *can* gate on
non-zero — but see the caveat.

## How to read the results, and the caveat

Routing is **probabilistic**: a skill or agent fires perhaps half the time on a clear match, with
real run-to-run variance. So results are **rates over `--runs`, not booleans**, and a single low
positive rate is as likely to be variance as a real problem. The load-bearing signals are the ones
that survive that noise:

- **Regression** — a positive whose rate *drops* between two runs of this suite, e.g. right after a
  description edit. That is the eval-first check `prompt-engineer` asks for: run it before and after.
- **Over-trigger** — a negative that fires *at all*. A near-miss landing on the cluster means the
  description is too broad, and it's a defect regardless of variance (which is why negatives pass
  only at a 0% fire rate). Read that asymmetrically: **one fire is proof of a defect, but zero
  fires is weak proof of its absence** — "0% fire rate" describes the three runs, not the
  component. At `--runs 3` a negative whose true over-trigger rate is 10% passes about 73% of the
  time (20% → about 51%), so a clean negative side bounds over-triggering loosely rather than
  refuting it.

### What `--runs 3` can and cannot resolve

Three runs express exactly four rates — 0, 1/3, 2/3, 1 — so the default `--threshold 0.5` means
"at least 2 of 3", and **the pass boundary is a single run**. Consequences to hold on to before
reading any positive rate as signal:

- At the ~50% fire rate this section describes as normal for a clear match, a correctly described
  component **coin-flips its verdict** (P(pass) = 0.5). At a true 0.3 it still passes 22% of the
  time; at 0.7 it fails 22% of the time.
- A **1/3 ↔ 2/3 movement is not signal.** Between two runs of an unchanged tree at p=0.5, the
  chance of observing some strict rate increase is about 1 in 3. Treat single-step movement as
  noise unless a mechanism explains it.
- A `1/3` positive is a **failing** positive, not a partial success — the roadmap states this for
  the ladder cluster and it generalizes.
- Never diff an `n=1` capture against an `n=3` one. Stored rows of that shape exist in
  `baselines/history/2026-08-10-learn-002.md`, and that record retracts two of them itself.

When a paired comparison must actually support a conclusion, raise `--runs` on the specific cases
in the diff rather than trusting a boundary crossing at three.

Because of that variance, this suite is meant to be run **manually, on demand** — before and after a
prompt change — not as a hard CI gate that would flake-fail honest PRs. It is intentionally *not*
wired into CI.

## The behavioral harness (retired 2026-09-02)

The behavioral evaluator (`scripts/eval_behavioral.py`), its packet linter
(`scripts/packet_lint.py`), and its case inventory (`evals/behavioral/contracts.json`) retired
2026-09-02 under `docs/decisions/2026-09-02-single-operator-audience.md`: the grader produced most
of a year's false-red churn and no shipped role ran it. Routing evals in this file remain the
fleet's one paid instrument; the guarantees the harness graded — read-only enforcement and
live-effect interposition — rest on the two PreToolUse hooks (`scripts/readonly-guard.py`,
`scripts/live-effect-gate.py`) instead of a contract run.

## Baseline retention: what a stored capture is still for

A capture under `baselines/` has exactly two possible jobs, and they retire on different schedules.
Keeping this straight is the difference between an archive and a graveyard.

1. **Reuse** — serving as the 'before' side of a paired run. This job is **fragile by design** and
   usually already over: a stored capture is reusable only if its cluster, cases, evaluator, and
   plugin bytes are all unchanged since capture **and** its recorded conditions — requested
   model, clean-room setting, threshold, timeout — equal the planned run; checked by hand (the
   script that once automated this comparison, `eval_baseline.py`, was retired 2026-09-01) — so
   any of a schema bump, a case edit, an evaluator change, a fleet edit, or a different model or
   setting ends it permanently.
   **As of 2026-08-17 no stored capture holds this job** — all ten clusters resolve `STALE`, and
   the v3→v4 schema move plus the case retirement made that final rather than incidental. Every
   paired round from here starts with a fresh capture on both sides.
2. **Evidence** — being the record of a number some doc, decision, or roadmap item relies on. This
   job does not expire, but it is served by the *distilled summary*, not the raw capture, once one
   exists.

**The retention rule.** A capture keeps its raw `benchmark.json` files while it can still be
reused, or while its numbers exist nowhere else. Once neither holds, the summary stays and the raw
files retire to Git history. Three consequences worth stating, because each has bitten:

- **Distil before you delete, never after.** 14 of the 28 baseline directories have no summary
  file, so for those the raw capture is the only record and removing it destroys the measurement
  rather than compressing it. Writing the summary is authoring work and belongs to whoever
  understands the round — it is not a cleanup step.
- **"Nothing cites it" is necessary but not sufficient.** A directory no doc names may still hold
  the only derivation of a number quoted elsewhere. The quoted claim survives deletion; the ability
  to check it does not.
- **A before/after pair retires together or not at all.** Dropping one side while keeping the
  other's summary leaves a delta nobody can re-derive. `2026-07-29-roles-before` and
  `-roles-after` are the live example: the 'after' directory's only prose is a note explaining a
  regrade, not a delta record, so neither side is retirable until the pair's rates are written down.

**Applied so far:** `2026-07-30-deep-review-r1`'s raw captures were retired on 2026-08-17 (2,914
lines across five run directories) because its `README.md` carries the complete verdict — negatives
18/18 clean both sides, `pos-incident-after-update` 33%→67%, the two recheck recoveries to 5/5,
`pos-audit-security` 8/8→4/8, and the ablation's explicit no-causal-claim caveat — and nothing in
the tree cited the directory.

`2026-08-01-self-improve` then went through the distil-first path the rule requires: its seven
generations were summarized into that directory's new `README.md` — every rate verified against the
captures before anything was removed — and six uncited generations retired (4,986 lines).
`final-live/` was retained in full while `docs/fleet-roadmap.md` cited it as LEARN-002's live
rates; LEARN-002 closed 2026-09-02 (won't-do), so that pin is gone and the capture retired to Git
history in this pass. That summary also
preserves something no single capture held: three conditions moved mid-round (opus → sonnet, the
600s → 420s behavioral timeout, provenance none → v1 → v3), so only within-generation pairs are
like-for-like — and `self-improve-lifecycle-merge` reached 3/3, fell to 0/3, and is still 0/3, which
is a different problem from never having passed and is visible only across generations.

Then two whole **families** were combined, which is the cheaper move where one round was split across
many paths. `2026-07-27-{before,after,diagnose}` became
`2026-07-27-craft-vs-fullstack/README.md`, and the seven directories of the 2026-07-29 verification
and role-expansion round (`2026-07-29/`, `-isolation/`, `-labsec/`, `-roles-before/`,
`-roles-after/`, `-verification-seam/`, `-verifier-contracts/`) became
`2026-07-29-verification-round/README.md`. Ten directories to two, 2,966 lines retired, fifteen
rates verified against the captures first, and the four citations that pointed into the old paths
repointed in the same commit. The roles pair's rates are now written down, which is what the
pair rule required before either side could go.

Combining is usually better than deleting one directory at a time, because a round's finding often
lives *between* its captures. The 2026-07-29 family is the example: routing could not see the agents
firing (0/6 twice, and 0.0 on every host and verification-seam positive) while the behavioral
captures from the same day, same model, confirmed those agents' contracts held once pinned. No single
directory contains that sentence, and it is the whole argument for the agent-only-positive
retirement carried out three weeks later.

Finally the rule was applied at scale, with one correction to it. The rule's caution — distil before
you delete — protects against losing a number. **Git history already provides that protection**: a
retired capture's exact rates come back with one `git show`, verified. So the rule only needs to bite
where **no summary exists at all**; where one does, holding the raw as well protects nothing.

What decides it per directory is therefore not "does a summary exist" but **does the summary carry
the raw's outcomes**. Measured on 2026-08-17: six directories named every one of their cases *and*
every outcome value — `2026-08-10-learn-002`, `2026-08-11-handoff-001`, `2026-08-13-group1-rescan`,
`2026-08-13-prop-001`, `2026-08-15-handoff-001-sonnet5`, `2026-08-15-learn-002` — and their raw
retired (79 files, 11,679 lines), leaving each directory as its summary alone. Six others have a
summary that names only 18–54% of their cases, so their raw stays until the summary is extended; a
summary that mentions a round without recording its rates is not a substitute for one.

Baselines grew from 9,371 lines across 13 top-level directories to 18,120 across 22 by the
CTX-002 paired captures (PR #154), the salvaged 2026-08-12 sonnet-testing arc, the 2026-08-19
settling and EVAL-009 batches, and the 2026-08-29 GATE-006 calibration slice, after the
original retirement cut 31,656 across 28 —
a 70% cut with nothing a reader consumes removed on the retirement side. A 2026-09-01
consolidation pass then cut every raw capture no live document reaches (uncited captures with an
existing summary, plus directories no live document names at all) down to 18,120/22; each
surviving capture's reason for staying is recorded in `evals/baselines/README.md`. A second pass
on 2026-09-02 retired what the operator's closure of CTX-002, LEARN-002, HANDOFF-001, and
LADDER-002 had pinned
(`docs/decisions/2026-09-02-single-operator-audience.md`) — the ten handoff-001, ladder, and
settling directories those items pinned in full, plus `2026-08-01-self-improve/final-live/` and
`2026-08-18-ctx-002/disposition/` (the latter's own unconditional trigger, independent of the
still-open LANE-001) — bringing the total to 11,440 lines across 12 top-level directories. The
2026-09-14 native-migration anchor then added a thirteenth, and nearly doubled the tree on its own:
**22,530 lines across 13 top-level directories**. Ten `benchmark.json` files account for 10,965 of
those lines, because each records `fired_per_run` for every case — the audit trail that lets a
surprising verdict be explained from the artifact instead of by paying for the batch again. That
is the trade this directory exists to make, but it is also why a full anchor is captured
deliberately rather than routinely.
What remains: 1,369 lines of distilled record
under `history/`, the raw of the partially-summarized directories, and
the directories with no summary at all — the set is whatever `git ls-files evals/baselines`
shows minus the summarized ones, not a list this paragraph could keep current (it went stale at
four entries while eleven existed) — where the raw *is* the record until someone who understands
the round writes its summary.

Reproduce both totals with `git ls-files -z evals/baselines | xargs -0 wc -l | tail -1`, and the
same over `evals/baselines/history` for the distilled figure — newline counts over tracked files,
which is exactly what `test_readme_inventory_figures_match_the_shipped_suites` recomputes. The
command is stated because two earlier attempts at this number disagreed with each other and with
the tree: one counted `splitlines()`, which adds one for a file with no trailing newline, so the
check agreed with itself while being 16 lines off. A figure bound to a computation no reader would
run is not bound to anything. `2026-07-31-p0-p1` matters most of
those: it holds the only Codex CLI run this repository has ever recorded.

## Relationship to `claude plugin eval`

The migration happened on 2026-09-14 (MACH-001 phase 4). `claude plugin eval` now runs every
routing case: isolation, per-case runs, concurrency, cost ceilings, timeouts, the JSON result and
the HTML report are all the platform's, and `scripts/eval_routing.py` dropped from about 1,450
lines to 479.

What the fleet kept is what the platform does not do — the verdict, the clean room, and
measurement provenance. Each was a measured decision rather than a preference; the "Running"
section above states the first two, and `fleet/provenance.py` holds the third, because nothing in
the native result document identifies the plugin bytes a result was taken against.

The oracle for the migration is recorded in
`docs/archive/2026-09/routing-migration-oracle-2026-09-14.md`: one live batch of `prompt-tooling`
graded by BOTH the retiring runner and the replacement, on identical traces, agreeing on all 12
case verdicts. It also records what that oracle could not exercise and why.

**A rate from before the migration is not comparable to one from after it.** The sessions now run
under a declared tool set and a turn cap rather than the old wall clock, so the conditions block
moved even where the grading did not. Re-baseline rather than diffing across the boundary.

## Coverage

Ten clusters are seeded — every overlap this README names, plus the altitude,
simple-stays-simple, and read-only-investigation seams:

| Cluster file | Members | Guards |
|---|---|---|
| `prompt-tooling.json` | prompt-craft, prompt-engineer | authoring/fixing an LLM artifact vs near-misses that share write/fix/optimize |
| `homelab-ops.json` | homelab-engineer and eleven lab-operation skills | a lab request → the right lab component; near-miss → no lab component (the highest-risk overlap, over a live lab) |
| `craft-vs-fullstack.json` | backend-craft, frontend-craft, sde-fullstack, code-craft, ci-actions | single-layer vs cross-layer builder routing (the layer-ownership boundary this repo re-drew) |
| `ladder.json` | sde-fullstack, principal-engineer, eng-ladder | eng-ladder firing and named bypass negatives; principal owns system and strategic design, whose output quality is checked separately |
| `proportionality.json` | sre-tool, eng-ladder, principal-engineer | simple-stays-simple (negative-only): small asks must fire NO heavy component; a builder/craft firing instead is correct |
| `investigation.json` | researcher, repository-investigator, code-reviewer, root-cause, application-security-auditor | trust-separated investigation: external/public research vs local/private source evidence vs a diff, failure, or source-to-sink audit |
| `agent-systems.json` | multi-agent-architect, prompt-engineer, principal-engineer | AI-agent system design and wrapper diagnosis vs one prompt or ordinary software architecture |
| `verification-seam.json` | verification-engineer, sde-fullstack, code-reviewer, root-cause | execute verification vs implement a fix vs static review vs root-cause diagnosis |
| `retro-boundary.json` | self-improve-loop, postmortem | explicit-only maintainer retro boundaries vs the resolved-incident write-up; "retro"/"postmortem" vocabulary collisions and a live outage must reach neither |
| `continuous-improvement.json` | self-improve-loop, runbook, postmortem, root-cause, prompt-craft, prompt-engineer | explicit-only maintainer retro negative boundaries against diagnosis, direct authoring, incidents, prompt repair, and ordinary builds |

`homelab-ops` is re-run and diffed whenever its membership changes. The captured baseline under
`baselines/2026-07/` predates `postmortem` joining the cluster on 2026-07-24 (4 members / 15 cases
there); the capture under `baselines/2026-07-24/` records the later 5-member / 18-case shape. Both
are *historical* anchors, not like-for-like comparisons with the current 12-member / 33-case
cluster. Re-baseline whenever membership changes.

**Suite size, as of 2026-09-07:** 101 routing cases across the ten clusters (41 positives, 60
negatives), so a full sweep at the methodology's `--runs 3` is **303 sessions**. The 2026-08-23
suite had 111 cases / 333 sessions; eight automatic retro positives retired when the maintainer
skill became explicit-only. Before starting a paired round, account for both sides: the 'before'
and 'after' sides each cost a full sweep unless a
stored capture is checked by hand — same bytes, same recorded model, clean-room setting,
threshold, and timeout — and found reusable.

### Measurement caveat: skills fire, agents must be delegated to

This runner grades on which component the headless session actually **invoked** — a Skill tool call
(a skill fired) or an Agent/Task spawn (a subagent fired). Those are not equally likely. A skill is
invoked inline in the main session; an **agent** only registers when the main session chooses to
**delegate** to it, and a one-shot `claude -p` session tends to just start doing the work (often with
`Bash`) rather than spawn a subagent — so **agent positives systematically under-fire here relative
to skill positives**, and a low agent-positive rate is partly a property of headless one-shot mode,
not only of the description. Read the clusters accordingly:

- **Skill-heavy clusters** (`prompt-tooling`, the skill positives of `homelab-ops`) measure routing
  cleanly.
- **Agent positives** (`homelab-engineer`, the `ladder` and `craft-vs-fullstack` agent members) are
  a weaker signal one run at a time; trust the **negatives** (over-trigger is a real defect at any
  rate) and **regressions across runs** over an absolute agent-positive rate.
- **This is now the suite's design, not just a caveat.** Routing carries **no agent-only
  positives** — 26 were retired on 2026-08-17, because a case only a delegation can score measures
  the harness's reluctance to delegate rather than the description, and nothing in the scoring
  compensated: `--threshold` is one global value applied identically to every positive regardless
  of component kind. Of the 41 positives that remain, 23 are skill-only and 18 are mixed (a skill
  route can score them). An agent's over-trigger coverage stays here regardless — cutting agent
  positives cost nothing on that axis, because a negative's forbidden set defaults to the whole
  member list, so every agent in `members` is still guarded against firing on a near-miss. The
  behavioral harness that once held an agent's positive-firing coverage of record retired
  2026-09-02; that gap is currently unmeasured by either remaining instrument.
- **Adding an agent-only positive is therefore a regression**, not extra coverage: it re-buys three
  sessions per run to publish a rate that is a property of one-shot headless mode. If an agent's
  reachability genuinely needs measuring, that is what the native `claude plugin eval` lane below
  is for.
- The native `claude plugin eval` (see below) delegates properly and will tighten the agent signal;
  these case files migrate to it unchanged.
- **Skill positives are only as visible as the listing the eval model saw.** The skill listing is
  character-budgeted per model context window (8,000 chars at 200k; see the skill-listing budget
  entry in `skills/prompt-craft/references/claude-code-frontmatter.md`), and over-budget plugin
  entries degrade to bare names — a state in which description-driven skill routing cannot fire at
  all. Probed 2026-08-16 on CLI 2.1.233: a 200k-window model saw 18 of 19 fleet entries name-only
  while larger-window models saw all in full. The recorded `models_observed` condition therefore
  carries listing state implicitly: skill-routing rates measured on a 200k-window model are not
  comparable with rates measured on a larger-window model, and a paired before/after run must hold
  the model — and with it the listing state — fixed. `scripts/fleet_doctor.py` reports the fleet's
  current footprint (`repository.skill-listing-budget`).

## Homelab operating-flow change

The automatic positives for `self-improve-loop` retired when it became explicit-only maintainer
work. Its negative boundaries remain; routing does not measure an explicit invocation. Body changes
to homelab closeout, task briefs, runbooks, and conditional builder loading use the outcome cases in
`docs/decisions/2026-09-07-homelab-operating-flow.md`; routing rates alone do not prove those outcomes.
