# Contributing

This repository is a tooling kit for one home-lab operator, packaged well enough to hand to
strangers who run the same kind of lab (`docs/decisions/2026-09-02-single-operator-audience.md`).
Most contributors here are agent sessions, so this file states the procedure a session cannot infer
from the diff. The binding rules — what a PR must not do — stay in `AGENTS.md` under "Opening a pull
request"; read both before opening or updating one.

Validation tiers, change playbooks, and the hard rules are owned by `AGENTS.md`. Where this file and
`AGENTS.md` disagree, `AGENTS.md` wins.

## Branches

Branch names use the expanded conventional form `<type>/<kebab-slug>`, so the branch list reads as a
change inventory. The types are `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`, and
`build`. Older branches in this repository predate the convention; new work follows it.

## Commits

Write every line — commit messages included — in the claim-plus-consequence register: what changed
*and* what it means, because a reviewer can only disagree with a decision they can see.

Merge commits keep branch history on the default branch, which is why a canonical edit and
everything it makes necessary land together rather than in a follow-up.

## The pull request

`.github/pull_request_template.md` is the shape, and it owns its own detail. Fill the
conditional-gates rows your change tripped — that table names the situational check each change type
owes, and rows you did not trip are deleted rather than left blank. Keep "Deliberately not done"
honest and the whole template short.

## Review passes — the two are not symmetric

Treating the two reviewers alike is the mistake this section exists to prevent. After opening or
updating a PR, inspect the review summary, requests, and reviewed commit **before** waiting.

**Codex — you may request it.** `@codex review` and the separate `@codex security review` are
supported triggers, and an enabled Codex review can start automatically on open or ready. Request it
within the operator's authorized review budget, then confirm its start and its head.

**Copilot — only the operator can request it.** The reviewer is `copilot-pull-request-reviewer[bot]`,
which `suggestedActors` does not list: `gh pr edit --add-reviewer Copilot` fails to resolve the
login, and a REST `requested_reviewers` post silently leaves `reviewRequests` empty. The PR page's
Reviewers box is the only path that works, so hand this request to the operator and say that you
did.

**An empty `reviewRequests` list proves nothing on its own.** An automatic Codex pass leaves it
empty while running; a missing Copilot request leaves it empty because nobody asked. Same list,
opposite meanings — which is why the inspection above precedes the wait. Never report a PR as
"awaiting review" when nothing was requested.

Historical Copilot API failures do not establish a universal request ban; see
`docs/decisions/2026-08-16-pr-review-gate.md`, which owns this policy and its reopen triggers.
