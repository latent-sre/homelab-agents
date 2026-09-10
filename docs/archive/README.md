# Archive index

Dated reviews, donor adjudication, and completed-plan evidence. Historical evidence only, never a
task list — `docs/README.md` owns that rule, and only `docs/fleet-roadmap.md` can import work from
anything here.

## Retired records

The 2026-07 and 2026-08 rounds were pruned once their items closed. Records that an **open** roadmap
item still names as `Source:` were kept, because an archive record cited by open work is live
evidence rather than history; it retires when its item does.

Surviving files may cite a retired record by path or title. Historical bodies and frozen captures
keep those references as written: several files — `2026-09/roadmap-history-2026-09-01.md` above all —
declare an extracted revision and promise their bodies are verbatim, so rewriting a link inside
one would falsify the guarantee that makes it evidence. Live documents mark retired records as
such; links to retained records still resolve in the tree. Retrieve a retired record with Git:

```bash
git log --diff-filter=D --name-only -- docs/archive/   # find the removing commit
git show <commit>^:docs/archive/<year-month>/<file>.md # read the record at its last revision
```

Retired in this pass, with surviving references inventoried across all tracked files on 2026-09-10,
including code, evaluator documentation, and frozen captures. Record paths are relative to
`docs/archive/`; referring paths are repository-relative. Title-only mentions count too.

| Record | Referenced by |
|---|---|
| `2026-07/fleet-program-outcomes-2026-07-29.md` | `docs/archive/2026-07/sre-agents-adaptation-backlog.md` |
| `2026-07/fleet-quality-review.md` | `docs/fleet-roadmap.md` |
| `2026-07/p0-p1-safety-controls-outcomes-2026-07-31.md` | `docs/decisions/2026-08-20-effect-transport-policy.md` |
| `2026-07/sde-fullstack-agent-audit-2026-07-30.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md` |
| `2026-07/verification-round-outcomes-2026-07-29.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md`; `evals/README.md`; `scripts/eval_clean_room.py` |
| `2026-08/agent-skill-full-audit-findings-2026-08-30.md` | `docs/decisions/2026-09-02-single-operator-audience.md` |
| `2026-08/ctx-005-engineering-discipline-audit-2026-08-23.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/gate-001-outcome-2026-08-10.md` | `docs/decisions/2026-08-29-homelab-live-effect-gate.md` |
| `2026-08/ladder-001-outcome-2026-08-14.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/ladder-002-investigation-2026-08-14.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md`; `evals/baselines/2026-08-14-ladder/decisions.md` |
| `2026-08/learn-001-outcome-2026-08-02.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/learn-002-offline-repairs-2026-08-17.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/loop-001-outcome-2026-08-10.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/prop-001-outcome-2026-08-13.md` | `docs/decisions/2026-08-16-pr-review-gate.md`; 18 frozen CTX-002 captures listed below |
| `2026-08/prop-002-outcome-2026-08-13.md` | `docs/archive/2026-08/save-toolkit-delta-scoping-2026-08-29.md` |
| `2026-08/prop-002-scan-findings-2026-08-13.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md`; `evals/baselines/history/2026-08-13-group1-rescan.md` |
| `2026-08/rev-001-outcome-2026-08-10.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/safe-003-outcome-2026-08-10.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md`; `docs/decisions/2026-07-31-ai-graph-engineering.md` |
| `2026-08/vscode-discovery-investigation-2026-08-18.md` | `docs/decisions/2026-07-30-multi-platform-packaging.md`; `docs/superpowers/specs/2026-08-18-multi-host-plugin-architecture-design.md` |
| `2026-08/wf-001-outcome-2026-08-01.md` | `docs/archive/2026-09/roadmap-history-2026-09-01.md`; `docs/decisions/2026-07-31-ai-graph-engineering.md` |

The PROP-001 references in frozen CTX-002 `benchmark.json` files are under
`evals/baselines/2026-08-18-ctx-002/`. For each row, every named cluster directory contains one
referencing `benchmark.json` file; these are retained evidence, not current path inventories.

| Stage directory | Cluster directories |
|---|---|
| `before/` | `continuous-improvement`, `craft-vs-fullstack`, `homelab-ops`, `investigation`, `prompt-tooling`, `proportionality`, `retro-boundary`, `verification-seam` |
| `after/` | `continuous-improvement`, `craft-vs-fullstack`, `homelab-ops`, `investigation`, `prompt-tooling`, `proportionality`, `retro-boundary`, `verification-seam` |
| `after-repair/` | `craft-vs-fullstack`, `prompt-tooling` |

The inventory found surviving references to 20 of the 34 archive records retired in this pass.
The other 14 had no surviving path or title references at that check; the Git commands above reach
them too.
