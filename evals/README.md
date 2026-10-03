# Routing evals

The fleet's components overlap on purpose: `prompt-engineer` and `prompt-craft` both cover anything
an LLM consumes, `sde-fullstack` overlaps `backend-craft`/`frontend-craft`, `homelab-engineer`
overlaps the lab skills. Overlap is fine until a description drifts and a request lands on the
wrong member. These evals measure whether a realistic request **routes to the right component**,
and whether a near-miss that only shares vocabulary routes elsewhere. Run a cluster before and after
any description edit.

## Format

One file per overlap cluster under `routing/`:

```json
{
  "cluster": "prompt-tooling",
  "members": ["prompt-craft", "prompt-engineer"],
  "cases": [
    { "id": "pos-...", "prompt": "...", "polarity": "positive",
      "expect_fires": ["prompt-craft", "prompt-engineer"], "tags": ["..."] },
    { "id": "neg-...", "prompt": "...", "polarity": "negative", "tags": ["near-miss"] }
  ]
}
```

- **positive** passes when one of `expect_fires` is dispatched.
- **negative** passes when none of `expect_not_fires` is dispatched. It defaults to the whole
  cluster. Narrowing it to a subset exempts a sibling that may legitimately fire, and stops
  watching every member it drops: 16 of 60 negatives narrow today, and `continuous-improvement` and
  `agent-systems` narrow all of theirs. Prefer reshaping the prompt to adding a narrowing.

`scripts/validate_fleet.py` rejects malformed clusters: a bad polarity, an empty or non-member
target list, a duplicate id. A typo there would otherwise pass vacuously.

## Writing a case

- **A negative must be near.** It shares vocabulary (write / fix / optimize / review) with the
  members it must not reach; say which term in `expected_output`. A far-miss passes by
  construction. `proportionality` is the exception: it is negative-only and deliberately fires
  trivial asks at heavy components.
- **A prompt that points at an artifact carries it.** "Review this diff" with no diff makes the
  correct answer, asking for it, score as a miss. `tests/test_validate_routing.py` fails a short
  deictic prompt with no inlined artifact.
- **No agent-only positives.** A headless one-shot session tends to do the work itself rather than
  delegate, so an agent-only positive measures that reluctance, not the description. Negatives
  still guard every agent in `members`.

## Running

```bash
python3 scripts/eval_routing.py evals/routing/prompt-tooling.json --runs 3 --model sonnet
python3 scripts/eval_routing.py evals/routing/homelab-ops.json --case 'neg-*' --max-cost-usd 5
python3 scripts/eval_routing.py evals/routing/ladder.json --dry-run   # write cases, print commands
```

The driver writes the native case layout to `evals/generated/<cluster>/` (git-ignored, rewritten
every run) and runs `claude plugin eval` once per polarity: positives at `--threshold 0.5`,
negatives at `--threshold 1.0`. It exits with the worse of the two: 0 every case met its bar, 1 a
case fell short, 2 the harness could not complete. Results and the HTML report land under the
generated directory.

Each case gets one `regex` grader over the trace that matches an Agent `subagent_type` or a Skill
`skill` naming a target, namespaced or bare (`fleet/nativecases.py`). It counts a dispatch whose
spawn returned an error; the retired fleet-side grader did not, and the two agreed on all 36 runs
of a paired `prompt-tooling` batch.

**Pin `--model` for any run you will compare.** The skill listing is character-budgeted per context
window, and a smaller window degrades plugin skills to bare names, where description routing
cannot fire. Two runs on different models are not a before/after.

## Reading the results

Routing is probabilistic, so a result is a rate over `--runs`, not a boolean.

- **Over-trigger:** a negative that fires at all is a defect. Zero fires is weak evidence: at 3
  runs, a negative with a true 10% over-trigger rate passes about 73% of the time.
- **Regression:** a positive whose rate drops after a description edit.
- **Three runs express four rates** (0, 1/3, 2/3, 1). The pass bar is one run wide, a component
  firing half the time coin-flips its verdict, and a 1/3 to 2/3 move is noise. When a comparison
  must carry a conclusion, raise `--runs` on the cases that moved.

This is a manual, paid instrument, deliberately not a CI gate.

## Coverage

101 cases across ten clusters (41 positive, 60 negative); a full sweep at `--runs 3` is 303
sessions.

| Cluster | Members | Guards |
|---|---|---|
| `prompt-tooling` | prompt-craft, prompt-engineer | authoring an LLM artifact vs near-misses sharing write/fix/optimize |
| `homelab-ops` | homelab-engineer and eleven lab skills | a lab request reaches the right lab component; near-misses reach none |
| `craft-vs-fullstack` | backend-craft, frontend-craft, sde-fullstack, code-craft, ci-actions | single-layer vs cross-layer builder routing |
| `ladder` | sde-fullstack, principal-engineer, eng-ladder | eng-ladder firing and its bypass negatives |
| `proportionality` | sre-tool, eng-ladder, principal-engineer | small asks fire no heavy component (negative-only) |
| `investigation` | researcher, repository-investigator, code-reviewer, root-cause, application-security-auditor | external research vs local evidence vs a diff, failure, or audit |
| `agent-systems` | multi-agent-architect, prompt-engineer, principal-engineer | agent-system design vs one prompt or ordinary architecture |
| `verification-seam` | verification-engineer, sde-fullstack, code-reviewer, root-cause | execute verification vs fix vs review vs diagnosis |
| `retro-boundary` | self-improve-loop, postmortem | explicit-only retro vs the incident write-up |
| `continuous-improvement` | self-improve-loop, runbook, postmortem, root-cause, prompt-craft, prompt-engineer | the retro's negative boundaries |
