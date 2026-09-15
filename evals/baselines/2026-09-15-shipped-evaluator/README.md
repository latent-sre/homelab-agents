# 2026-09-15 — routing anchor on the shipped evaluator bytes

**Complete: all ten clusters, 101 cases, 303 runs, $39.57.**

> **This is a reusable before-side**, and the first capture that is. Every artifact here records
> evaluator `892f52b3dcaf` — the bytes merged in PR #193 — against plugin `4478a262f814` at
> `git_head c40fa6238657` with `git_dirty: false`, and all ten carry one identical condition set
> on every field `AGENTS.md`'s T3 reuse contract compares. It replaces
> `../2026-09-14-native-migration/`, which disqualified itself as a before-side because its
> evaluator predated the review fixes that shipped with it.
>
> **The reuse contract still has to be checked per use, not assumed from this banner.** A run that
> wants to reuse this capture must match the recorded conditions in the artifact it reuses — read
> that `conditions` block, not this file. One field deserves advance warning: these ran on **CLI
> 2.1.272**, while CI's `claude-plugin-contract` job pins **2.1.270**. An after-side run on the
> pinned version does not match this capture's conditions and may not pair with it.

| | |
|---|---|
| Overall | **89 / 101** |
| Negatives | **60 / 60 cases**, over **178 usable** negative runs |
| Positives | 29 / 41 — **no failure anywhere involves a wrong destination** |
| INCONCLUSIVE | **1** — `craft-vs-fullstack/pos-typescript-branded-ids` |
| Runs excluded | 5 of 303 (2%) |
| Model observed | `claude-sonnet-5`, uniform across all ten clusters |
| CLI | 2.1.272, uniform |
| Component surface | `components_uniform: true` in all ten — per-run, not merely equal unions |

| cluster | overall | positives | negatives | excluded | cost |
|---|---|---|---|---|---|
| agent-systems | 3/3 | — | 3/3 | 0 | $0.98 |
| continuous-improvement | 6/6 | — | 6/6 | 0 | $2.31 |
| craft-vs-fullstack | 9/17 | 1/9 | 8/8 | 3 | $5.88 |
| homelab-ops | 33/33 | 18/18 | 15/15 | 1 | $14.83 |
| investigation | 7/7 | 2/2 | 5/5 | 0 | $2.86 |
| ladder | 8/9 | 3/4 | 5/5 | 1 | $4.28 |
| prompt-tooling | 9/12 | 3/6 | 6/6 | 0 | $3.44 |
| proportionality | 5/5 | — | 5/5 | 0 | $1.19 |
| retro-boundary | 5/5 | 1/1 | 4/4 | 0 | $2.00 |
| verification-seam | 4/4 | 1/1 | 3/3 | 0 | $1.80 |

One model, one CLI version, and one component surface across every cluster is what makes these ten
artifacts a single anchor rather than ten measurements that happen to share a directory.
`models_observed` and `components_observed` are read off the transcripts, so a batch that had
silently mixed tiers or surfaces would say so here instead of echoing the request.

**`components_uniform` is the claim the previous batch could not make.** That batch recorded only
an equal UNION per cluster, which cannot establish that every run saw the same surface: a component
appearing in one run of ten produces the same union as one present throughout. The field that
answers it existed for this capture and reads `true` in all ten clusters, so per-run uniformity is
established here rather than unknown.

## The asymmetry, and the one row that is not a rate

Every negative case passed, and **every one of the twelve positive failures involves no wrong
destination**: eleven routed nowhere or fired only expected members below the 0.5 threshold, and
the twelfth produced no usable transcript at all. That split is the documented behaviour of these
evals rather than a surprise — `../../README.md` records that fleet members under-fire in one-shot
headless mode, which makes a positive a weak absolute signal and a negative a strong one.

| cluster | case | rate | what fired |
|---|---|---|---|
| `craft-vs-fullstack` | `pos-backend-pagination` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-backend-resiliency` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-frontend-table` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-frontend-form` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-code-craft-idioms` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-ci-actions-harden` | 0.333 | `ci-actions` |
| `craft-vs-fullstack` | `pos-powershell-pester` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-typescript-branded-ids` | — | **INCONCLUSIVE** (3 of 3 runs excluded) |
| `ladder` | `pos-embedded-principal-fork-consult-required` | 0.0 | — (routed nowhere) |
| `prompt-tooling` | `pos-tighten-tool-desc` | 0.0 | — (routed nowhere) |
| `prompt-tooling` | `pos-fires-too-often` | 0.0 | — (routed nowhere) |
| `prompt-tooling` | `pos-rewrite-system-prompt` | 0.0 | — (routed nowhere) |

**The INCONCLUSIVE row is a hole in this anchor, not a zero.** All three runs of
`pos-typescript-branded-ids` ended without a usable transcript, so this capture records nothing
about where that prompt routes. A later description edit touching `code-craft` has **no
before-value here to pair against** and must capture one. The previous batch lost one of that
case's three runs and scored the other two; this one lost all three. Reading the row as 0.0 would
turn an absence of evidence into evidence of absence — the one claim these artifacts must never
make.

## What changed since 2026-09-14, and why none of it is attributable

Against the previous batch: 89/101 here against 86/101 there, and three cases moved up —
`homelab-ops/pos-host-onboard` (1/3 → 3/3), `homelab-ops/pos-discovery-question` (0/3 → 3/3),
and `investigation/pos-diagnose-idle-lab-failure` (1/3 → 2/3, crossing the threshold) — while
`craft-vs-fullstack/pos-typescript-branded-ids` fell from scored to INCONCLUSIVE.

**None of that is evidence that routing improved, and this file must not be read as saying so.**
No `description:` line changed between the two captures' heads (`b34f5a807521` and
`c40fa6238657`), so the routing inputs are identical. Three other things did change at once: the
CLI (2.1.270 → 2.1.272), the plugin bytes, and the evaluator — the last by roughly 1,058 lines
across seven of its eight files, including `fleet/routing.py` and `fleet/nativecases.py`, which
are the firing-detection and prompt-generation modules. A grading fix that recognises firings the
old instrument missed would produce exactly a 0/3 → 3/3 jump. This capture cannot separate that
from CLI drift or run-to-run variance, and does not try to. The comparison is context for a reader,
not a result.

For the same reason the two batches are **not comparable case-for-case**, which is what the
previous README already said of itself when it declined to serve as a before-side.

### ROUTE-001 moved verdict without changing behaviour

`investigation/pos-diagnose-idle-lab-failure` now **passes** at 2/3. The disagreement ROUTE-001
tracks is unchanged: `homelab-engineer` still co-fires, and the case still asserts `root-cause`.
Only the rate crossed the threshold. A reader scanning the green `investigation 7/7` row would
conclude the decision closed; it has not, and this section exists so that reading is not available.

## Command

```bash
for f in evals/routing/*.json; do
  python3 scripts/eval_routing.py "$f" \
      --runs 3 --model sonnet \
      --output-dir <scratch>/$(basename "$f" .json)
done
```

One cluster per invocation, sequential, so a failure in one does not take the batch and each
cluster's `benchmark.json` lands the moment it finishes — a container recycle during an earlier
attempt at this capture destroyed an unbanked parallel batch, which is why.

Two details of how these were produced, because they affect what the artifacts mean:

- **The measured tree was a git worktree pinned to `c40fa6238657`, and nothing wrote to it.**
  Output went to a scratch directory outside that tree and was copied here afterwards. Writing
  results into the tree being hashed would have changed its plugin hash between clusters and
  destroyed the single-anchor property. `git_dirty: false` in all ten artifacts records that it
  held.
- **`--clean-room` was not passed**, so `clean_room_requested` reads `false` here against `true` in
  the previous batch. It is one of the three fields the reuse contract excludes from comparison,
  and `--clean-room` was measured on 2026-09-14 to change nothing under the native harness, which
  sets its own config directory and overrides the variable the flag moves.

## Conditions

Each `benchmark.json` carries its own `conditions` block; read that rather than this file. The
values shared by all ten:

| field | value |
|---|---|
| `harness` | `claude plugin eval` |
| `cli_version` / `native_claude_version` | 2.1.272 |
| `model_requested` | `sonnet` |
| `models_observed` | `claude-sonnet-5` |
| `runs_per_case` | 3 |
| `threshold` | 0.5 |
| `timeout_s` | 180 |
| `max_turns` | 6 |
| `concurrency` | 4 |
| `components_observed` | 16 agents, 37 skills |
| `components_uniform` | `true` |
| `auth_provider` | anthropic, host-managed-provider |

`model_requested` is not evidence — the CLI's default is not inherited from the launching session,
and a run that silently served another tier would still echo the request. More than one entry in
`models_observed` would mean the batch was not uniform and not a single anchor.

**The routing competition is `components_observed`**, read off each session's own `init` event:
the fleet plus roughly sixteen of the CLI's bundled skills (`code-review`, `debug`, `verify` and
others) and six built-in agents. Those are deliberately present — identical on every machine for a
given CLI version, which `cli_version` pins, so they are the platform the fleet routes against
rather than per-operator contamination.

## Reading a rate

A case's rate rests only on its **valid** runs. A session that ran out of turns without dispatching
produced no routing decision, so it is excluded and counted in `runs_excluded` rather than scored as
a routing failure — `detail` says so whenever it happened. A case with no valid run is
`INCONCLUSIVE` and never counts as passed, in either polarity: no transcript is not evidence that
nothing fired.
