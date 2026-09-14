# 2026-09-14 — first routing baseline under `claude plugin eval`

> **STATUS: RUN IN PROGRESS — THIS IS NOT YET A BASELINE.**
> Only the cluster directories present below have been measured. A missing cluster was not
> measured, has not failed, and must not be read as either. This banner is replaced by the
> summary when all ten clusters finish; if you are reading it in a merged commit, the run was
> interrupted and the directory is partial evidence, not a baseline.

## Why this baseline exists

MACH-001 phase 4 moved the routing evals onto `claude plugin eval`. The migration changed no
verdict — proved by grading one live batch's identical traces with both instruments
(`docs/archive/2026-09/routing-migration-oracle-2026-09-14.md`) — but it did change the
measurement **conditions**: the sessions now run under a declared tool set and a turn cap instead
of the old wall clock. So every stored pre-migration rate stopped being comparable, and this run
is the replacement reference point for future description edits.

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
