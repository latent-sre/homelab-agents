# Documentation map

This directory holds current work and the maintainer's reference pages. History lives in Git:
`docs/archive/` and `docs/decisions/` were removed on 2026-10-03, and any file from them can be
read with `git show 690f28f:<path>`.

| Document | State | Read it for |
|---|---|---|
| [`fleet-roadmap.md`](fleet-roadmap.md) | Live | Every unfinished, blocked, deferred, and decision-needed item. Nothing else adds work |
| [`engineering-program.md`](engineering-program.md) | Live | The durable map from each program strand — handoff, loop, graph, self-learning — to the mechanisms implementing it and the checks keeping it honest. Mechanism-anchored by rule: no live item IDs, counts, or episodes, and the validator resolves every path it names |
| [`fleet-development.md`](fleet-development.md) | Live | The maintainer's page: which file owns which convention, the porting method, host-specific authority, the Codex lane in detail, how the hook is wired and why, workflows, the validation tiers, and the host probe |

## Rules

1. A historical review may explain why a decision was made; it never proves that work is still
   open.
2. The roadmap names current work. The commit or pull request that made a change owns its
   rationale.
3. Nothing here is a second record of what Git already holds: no dated reviews, decision records,
   or outcome records.
4. An active plan may be detailed and branch-specific. When its round completes, delete the spec
   and plan; the closing commit states the lasting decision and Git history keeps the payload.
5. When a file moves or is consolidated, update every tracked reference in the same commit.
6. Agent and skill definitions remain canonical in `agents/` and `skills/`; documentation and
   generated host adapters never override them.
7. GitHub issues are evidence-bound intake, never a second work tracker. An issue adds work only
   when the roadmap imports it (the roadmap entry names the source issue); an issue that is not
   imported is field evidence awaiting triage, and letting the two lists drift is how the same
   work gets tracked twice or dropped once.
