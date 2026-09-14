# 2026-09-14 — first routing baseline under `claude plugin eval`

**Complete: all ten clusters, 101 cases, 303 runs, $39.42.**

> **Historical record, NOT a reusable before-side.** These artifacts record evaluator
> `a6fcefed361c` over four files. The evaluator that shipped with the same pull request hashes to
> a different value and includes `fleet/frontmatter.py`, `scripts/eval_clean_room.py` and the
> review fixes made after this batch ran. `AGENTS.md`'s T3 reuse contract requires the evaluator
> bytes to be unchanged, so **no run made with the merged runner may reuse this capture as its
> before-side** — the 'before' side of any future description edit needs a fresh capture. What
> this batch remains good for: what the fleet's routing did on 2026-09-14 under the conditions
> each artifact records, and the case-by-case comparison against the pre-migration baseline below.

| | |
|---|---|
| Overall | **86 / 101** |
| Negatives | **60 / 60 cases**, over **177 usable** negative runs (180 attempted, 3 excluded) |
| Positives | 26 / 41 — **14 of the 15 failures involve no wrong destination** (11 routed nowhere, 3 fired only expected members below the 0.5 threshold); the fifteenth is a destination disagreement, below |
| INCONCLUSIVE | 0 |
| Runs excluded | 6 of 303 (2%) |
| Model observed | `claude-sonnet-5`, uniform across all ten clusters |
| CLI | 2.1.270, uniform |
| Component surface | equal **unions** in all ten clusters — see the caveat below |

| cluster | overall | positives | negatives | excluded | cost |
|---|---|---|---|---|---|
| agent-systems | 3/3 | — | 3/3 | 0 | $1.02 |
| continuous-improvement | 6/6 | — | 6/6 | 0 | $2.37 |
| craft-vs-fullstack | 9/17 | 1/9 | 8/8 | 3 | $5.61 |
| homelab-ops | 31/33 | 16/18 | 15/15 | 0 | $14.62 |
| investigation | 6/7 | 1/2 | 5/5 | 0 | $2.88 |
| ladder | 8/9 | 3/4 | 5/5 | 1 | $4.09 |
| prompt-tooling | 9/12 | 3/6 | 6/6 | 0 | $3.61 |
| proportionality | 5/5 | — | 5/5 | 0 | $1.17 |
| retro-boundary | 5/5 | 1/1 | 4/4 | 0 | $2.16 |
| verification-seam | 4/4 | 1/1 | 3/3 | 2 | $1.89 |

One model and one CLI version across every cluster is what makes these ten artifacts a single
batch rather than ten measurements that happen to share a directory. `models_observed` is read off
the transcripts, so a batch that had silently mixed tiers would say so here instead of echoing the
request.

**The component surface is a weaker claim than the other two, and deliberately stated as one.**
These artifacts record only a UNION per cluster, and equal unions cannot establish that every run
saw the same surface: a component appearing in one run of ten produces the same union as one
present throughout. The `components_uniform` field that answers this was added *after* this batch
ran and appears in none of these files. So: the unions are equal, and whether each run saw that
same surface is unrecorded here.

### The asymmetry is the result

Every negative case passed, and **fourteen of the fifteen positive failures involve no wrong
destination**. Stated precisely: no over-trigger was observed in the 177 negative runs that
produced a usable transcript; the other three produced no routing verdict and are evidence in
neither direction. That split is the documented behaviour of these evals rather than a surprise:
`../../README.md` records that fleet members under-fire in one-shot headless mode, which makes a
positive a weak absolute signal and a negative a strong one. Eleven of the fifteen failures routed
**nowhere at all** — the session completed and declined to dispatch; three more fired only members
the case expects, but in 1 of 3 runs against a 0.5 threshold.

**The fifteenth is not silence, and this summary must not round it off to one.**
`investigation/pos-diagnose-idle-lab-failure` dispatched a fleet member its case does not expect
(`homelab-engineer`) in all three runs. It is the one open routing-boundary decision in this
capture, tracked as ROUTE-001 and described below; an earlier draft of this table said no failure
was a wrong destination, which hid exactly the row a maintainer reading this summary most needs to
see.

So this baseline says the descriptions are not over-claiming; it says much less about whether they
are reachable enough.

| cluster | case | rate | what fired |
|---|---|---|---|
| `craft-vs-fullstack` | `pos-backend-pagination` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-backend-resiliency` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-frontend-table` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-frontend-form` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-code-craft-idioms` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-ci-actions-harden` | 0.333 | `ci-actions` |
| `craft-vs-fullstack` | `pos-powershell-pester` | 0.0 | — (routed nowhere) |
| `craft-vs-fullstack` | `pos-typescript-branded-ids` | 0.0 | — (routed nowhere) |
| `homelab-ops` | `pos-host-onboard` | 0.333 | `homelab-engineer` |
| `homelab-ops` | `pos-discovery-question` | 0.0 | — (routed nowhere) |
| `investigation` | `pos-diagnose-idle-lab-failure` | 0.333 | `homelab-engineer`, `root-cause` |
| `ladder` | `pos-embedded-principal-fork-consult-required` | 0.0 | — (routed nowhere) |
| `prompt-tooling` | `pos-tighten-tool-desc` | 0.0 | — (routed nowhere) |
| `prompt-tooling` | `pos-fires-too-often` | 0.0 | — (routed nowhere) |
| `prompt-tooling` | `pos-rewrite-system-prompt` | 0.333 | `prompt-craft` |

One of those is a different animal and is tracked separately (ROUTE-001 in
`docs/fleet-roadmap.md`): `investigation/pos-diagnose-idle-lab-failure` did not fail by silence.
It routed to `homelab-engineer` in all three runs, consistently and deliberately, while the case
asserts `root-cause`. The archived 2026-08-18 pilot recorded the same destination 6/6 under the
previous name. A case and the fleet disagree about where a prompt belongs; that is a decision to
make, not a rate to improve.

### Does this measure the same thing the old runner did?

Against the stored pre-migration `craft-vs-fullstack` baseline (2026-08-18, CLI 2.1.235, sonnet):
old 8/17, new 9/17, and case-for-case the pattern is identical — every positive failing now failed
then at rate 0.0, every negative passed in both, and the single case that moved
(`pos-backend-webhook`, 0.0 → 0.667) improved. Corroborating only: the CLI version differs and
`max_turns` did not exist before. The controlled proof that the migration changed no verdict is
the paired oracle in `docs/archive/2026-09/routing-migration-oracle-2026-09-14.md`, which grades
one batch's identical traces with both instruments.

## Why this baseline exists

MACH-001 phase 4 moved the routing evals onto `claude plugin eval`. The migration changed no
verdict — proved by grading one live batch's identical traces with both instruments
(`docs/archive/2026-09/routing-migration-oracle-2026-09-14.md`) — but it did change the
measurement **conditions**: the sessions now run under a declared tool set and a turn cap instead
of the old wall clock. So every stored pre-migration rate stopped being comparable.

This run is **not** the replacement reference point — see the banner at the top. Its evaluator
predates the fixes that shipped in the same pull request, so the reuse contract disqualifies it as
a before-side, and the next description edit needs a fresh capture of its own. What this run
established is that the migration changed no verdict; what it cannot do is serve as the other half
of a future comparison.

## Command

```bash
for f in evals/routing/*.json; do
  python3 scripts/eval_routing.py "$f" \
      --runs 3 --model sonnet --clean-room --concurrency 4 \
      --output-dir evals/baselines/2026-09-14-native-migration/$(basename "$f" .json)
done
```

One cluster per invocation, sequential, so a failure in one does not take the batch and each
cluster's `benchmark.json` lands the moment it finishes.

## Conditions, and the one that is not what it looks like

Each `benchmark.json` carries its own `conditions` block; read that rather than this file. Two
deserve calling out:

- **`model_requested: sonnet`, and `models_observed` read off the transcripts.** The requested
  model is not evidence — the CLI's default is not inherited from the launching session, and a
  run that silently served another tier would still echo the request. More than one entry in
  `models_observed` means the batch was not uniform and is not a single baseline.
- **`clean_room_requested: true` does NOT mean the sessions were isolated.** `--clean-room` was
  measured on 2026-09-14 to change nothing under the native harness, which sets its own config
  directory and overrides the variable the flag moves. It is recorded as a request because that
  is all it is. **The routing competition is `components_observed`**, read off each session's own
  `init` event: the fleet plus roughly sixteen of the CLI's bundled skills (`code-review`,
  `debug`, `verify` and others) and six built-in agents. Those are deliberately present —
  identical on every machine for a given CLI version, which `cli_version` pins, so they are the
  platform the fleet routes against rather than per-operator contamination.

## Reading a rate

A case's rate rests only on its **valid** runs. A session that ran out of turns without
dispatching produced no routing decision, so it is excluded and counted in `runs_excluded` rather
than scored as a routing failure — `detail` says so whenever it happened. A case with no valid run
is `INCONCLUSIVE` and never counts as passed, in either polarity: no transcript is not evidence
that nothing fired.
