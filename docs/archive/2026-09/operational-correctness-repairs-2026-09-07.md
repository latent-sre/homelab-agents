# Operational conclusions and verification contracts — 2026-09-07

Operator-selected correctness repairs on `refactor/consolidate-design-ownership`, following the
design-agent merger at `07facd8`. This record describes the repaired guidance and its evidence;
it is not a claim that a deployed lab or installed fleet was tested.

## Corrected behavior

| Surface | Previous defect | Correction |
|---|---|---|
| Upgrade campaign | Dependencies always went last, even when the new consumer required a newer dependency. | Every intermediate and rollback combination must be supported; risk breaks ties among safe next steps. |
| Incident diagnosis | A healthy container excluded the application as the cause of a failed route. | Compare equivalent requests and correlated logs; shallow liveness leaves application and dependency faults possible. |
| Backup freshness | A job-wide newest timestamp hid stale distinct targets. | Preserve every target/dataset identity; check missing expected identities separately. |
| PowerShell | Stop/try-catch was presented without native exit handling. | Check the native process's own exit status immediately; version-gate optional native error preferences. |
| PostgreSQL plan inspection | SELECT was classified as reads-only, and rollback was presented as universally safe. | Classify called functions and planning/execution effects; retain sequence and external-effect limits. |
| Alloy preflight | Formatting was called reload validation. | Separate formatting from component validation, then verify actual ingestion after an authorized reload. |
| CLI starter | Interactive confirmation polluted JSON stdout. | Prompt on stderr, read stdin without a prompt, and preserve confirmation/automation controls. |
| CI starter | Ruff-only checks promised type checking. | Name the step lint and formatting. |
| Reviewer identity | Approval always named the candidate's immediate parent as its base. | Name the exact base actually reviewed, including the resolved merge-base for a PR review. |
| Verifier evidence | A retired linter and undefined schema supposedly enforced every packet. | Require explicit target, criteria, command, own status/result, isolation and evidence; machine validation is conditional on a supplied schema and validator. |
| SRE-tool handoff | Typed state transitions were assumed, and isolation could first be discovered missing at final verification. | Identify the environment owner and available boundary early; name any existing state provider or use the explicit packet and plan. |

Execution isolation and independent verdict ownership remain mandatory for the verifier.
No schema, state controller, packet linter, container image, or provisioning framework was added.
The existing caller-supplied execution boundary remains the prerequisite; absence produces an
inconclusive criterion rather than permission to execute on the host.

## Evidence

- **Executed:** validator passed for 10 agents and 20 skills; 179 host adapters regenerated.
  Full unittest discovery passed **494 tests in 76.033 seconds, 2 skipped**, exit 0. Whitespace
  check passed. Strict Claude directory validation passed for the marketplace manifest.
- **CLI red/green:** the new actual-starter tests first reproduced invalid JSON and leaked
  confirmation text. After the fix, interactive confirmation, unattended refusal/explicit yes,
  decline, and dry-run cases passed; a deletion spy proved which paths could act.
- **PowerShell behavior:** the test extracts the documented recipe and substitutes a harmless
  native process returning 7. Stop-only continued to the dependent marker; the corrected recipe
  returned failure and never reached it. Passed on PowerShell 7 and Windows PowerShell 5.1.
- **Numerical backup counterexample:** under one job, targets aged 1h and 72h caused the old
  maximum-timestamp expression to miss the stale target. Per-target arithmetic selected only
  the 72h target at a 26h threshold. This was arithmetic, not a PromQL-engine execution.
- **Fresh-context source-following exercise:** four scenarios produced compatible upgrade and
  rollback ordering, an incident response that retained application faults as hypotheses,
  inconclusive verification without an enforced boundary, and the actual reviewed merge-base
  in approval identity. These are bounded output observations, not native routing rates.
- **Independent static review:** two rounds, no remaining material findings. Review inspected
  source and generated contracts; it did not independently execute the tests.

No Prometheus, Alloy, or PostgreSQL service was run for these changes. Their corrected contracts
are source-backed; component behavior and deployment acceptance remain checks for the operating
task. Native routing and hook-probe evidence still outstanding for the earlier design-agent merger
remains tracked by DESIGN-001 in the fleet roadmap; these checks do not close that gate.

## Primary contracts checked

Context7 supplied the official documentation contract; GitHits independently read the Alloy
upstream CLI documentation. They agreed on formatting versus component validation.

- [Prometheus aggregation operators](https://prometheus.io/docs/prometheus/latest/querying/operators/)
  and [absence semantics](https://prometheus.io/docs/prometheus/latest/querying/functions/#absent).
- [PowerShell external-program error handling](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_error_handling)
  and [native error preference](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables#psnativecommanduseerroractionpreference).
- [Alloy fmt](https://github.com/grafana/alloy/blob/main/docs/sources/reference/cli/fmt.md)
  and [Alloy validate](https://github.com/grafana/alloy/blob/main/docs/sources/reference/cli/validate.md).
- [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/sql-explain.html)
  and [function volatility](https://www.postgresql.org/docs/current/sql-createfunction.html).
