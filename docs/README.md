# Documentation map

This directory holds current work and the maintainer's reference pages. History lives in Git:
`docs/archive/` and `docs/decisions/` were removed on 2026-10-03, and any file from them can be
read with `git show b78a031:<path>`.

| Document | State | Read it for |
|---|---|---|
| [`fleet-roadmap.md`](fleet-roadmap.md) | Live | Every unfinished, blocked, deferred, and decision-needed item. Nothing else adds work |
| [`engineering-program.md`](engineering-program.md) | Live | The durable map from each program strand — handoff, loop, graph, self-learning — to the mechanisms implementing it and the checks keeping it honest. Mechanism-anchored by rule: no live item IDs, counts, or episodes, and the validator resolves every path it names |
| [`fleet-development.md`](fleet-development.md) | Live | The maintainer's page: which file owns which convention, the porting method, host-specific authority, the Codex lane in detail, how the hook is wired and why, workflows, the validation tiers, and the host probe |
| [`superpowers/specs/lane-001-codex-onboarding-discoverability.md`](superpowers/specs/lane-001-codex-onboarding-discoverability.md) | Approved, round not active | LANE-001's Codex host-evidence prerequisites, discovery/recommendation boundary, acceptance conditions, and rollback; Phase 0 remains outstanding and no paired plan exists |
| [`superpowers/specs/2026-08-18-multi-host-plugin-architecture-design.md`](superpowers/specs/2026-08-18-multi-host-plugin-architecture-design.md) | Implemented 2026-08-18 | The three retired host lanes, why the VS Code lane survives on workspace discovery from `.github/agents`, and the disproved "deliberately empty override" claim — the evidence that a manifest field naming an empty override does not keep a host away from the hooks |

`superpowers/specs/` holds a spec only while its roadmap item is live, and `superpowers/plans/`
holds a plan only while its round is active. A spec headed **drafted** awaits operator approval and
starts no round; the roadmap item's status and next action, not the file's presence, say whether a
round is running.

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
