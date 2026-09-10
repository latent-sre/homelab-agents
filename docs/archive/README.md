# Archive index

Dated reviews, donor adjudication, and completed-plan evidence. Historical evidence only, never a
task list — `docs/README.md` owns that rule, and only `docs/fleet-roadmap.md` can import work from
anything here.

## Retired records

The 2026-07 and 2026-08 rounds were pruned once their items closed. Records that an **open** roadmap
item still names as `Source:` were kept, because an archive record cited by open work is live
evidence rather than history; it retires when its item does.

Surviving records may link to a retired one. Those links are left as written on purpose: several of
these files — `2026-09/roadmap-history-2026-09-01.md` above all — declare an extracted revision and
promise their bodies are verbatim, so rewriting a link inside one would falsify the guarantee that
makes it evidence. Follow a dead link with Git instead:

```bash
git log --diff-filter=D --name-only -- docs/archive/   # find the removing commit
git show <commit>^:docs/archive/<year-month>/<file>.md # read the record at its last revision
```

Retired in this pass, still referenced from surviving records:

| Record | Referenced by |
|---|---|
| `2026-07/fleet-program-outcomes-2026-07-29.md` | `2026-07/sre-agents-adaptation-backlog.md` |
| `2026-07/sde-fullstack-agent-audit-2026-07-30.md` | `2026-09/roadmap-history-2026-09-01.md` |
| `2026-07/verification-round-outcomes-2026-07-29.md` | `2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/ctx-005-engineering-discipline-audit-2026-08-23.md` | `2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/ladder-001-outcome-2026-08-14.md` | `2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/ladder-002-investigation-2026-08-14.md` | `2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/learn-001-outcome-2026-08-02.md` | `2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/learn-002-offline-repairs-2026-08-17.md` | `2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/loop-001-outcome-2026-08-10.md` | `2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/prop-002-outcome-2026-08-13.md` | `2026-08/save-toolkit-delta-scoping-2026-08-29.md` |
| `2026-08/prop-002-scan-findings-2026-08-13.md` | `2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/rev-001-outcome-2026-08-10.md` | `2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/safe-003-outcome-2026-08-10.md` | `2026-09/roadmap-history-2026-09-01.md` |
| `2026-08/wf-001-outcome-2026-08-01.md` | `2026-09/roadmap-history-2026-09-01.md` |

Other records retired in the same pass are no longer referenced from any surviving file; the Git
commands above reach them too.
