# Contributing

This repository is a tooling kit for one home-lab operator, packaged well enough to hand to
strangers who run the same kind of lab.
Most contributors here are agent sessions, so this file states the procedure a session cannot infer
from the diff. The binding rules — what a PR must not do — stay in `AGENTS.md` under "Opening a pull
request"; read both before opening or updating one.

Validation tiers, change playbooks, and the hard rules are owned by `AGENTS.md`. Where this file and
`AGENTS.md` disagree, `AGENTS.md` wins.

## Branches

Conventional branch names: `<type>/<kebab-slug>`, using the commit types below
(`fix/guard-exec-holes`), so the branch list reads as a change inventory.

A branch an AI session creates goes under `ai/` with the same form inside it
(`ai/fix/guard-exec-holes`), never a vendor prefix such as `claude/`, `codex/`, or `copilot/`, so
the list shows who did the work without tying it to a tool. `main` is the only other exception;
older branches predate the convention.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope>): <summary>`, with
the scope optional and the summary in the imperative.

- **Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`, `build`, `revert`.
- **Scopes** name the area touched: `agents`, `skills`, `guard`, `generator`, `validator`, `probe`,
  `docs`, `ci`. Omit the scope when a commit spans several.
- **Breaking changes** for someone who already installed the plugin — a renamed or removed
  component, a tightened tool grant, a new gate — get a `!` (`feat(agents)!: ...`) and a
  `BREAKING CHANGE:` footer saying what they will notice.
- **The body** says what changed *and* what it means, because a reviewer can only disagree with a
  decision they can see.

Exceptions: the merge commit GitHub writes for a PR, and the message `git revert` generates, keep
their default form.

Merge commits keep branch history on the default branch, which is why a canonical edit and
everything it makes necessary land together rather than in a follow-up.

## The pull request

`.github/pull_request_template.md` is the shape, and it owns its own detail. Fill the
conditional-gates rows your change tripped — that table names the situational check each change type
owes, and rows you did not trip are deleted rather than left blank. Keep "Deliberately not done"
honest and the whole template short.

## Requesting review

Choose the independent review coverage required by `AGENTS.md`, then inspect actual activity,
scope, and reviewed commit before requesting or waiting. Codex and Copilot are available request
paths, not two obligatory passes.

**Codex — you may request it.** `@codex review` and the separate `@codex security review` are
supported triggers, and an enabled Codex review can start automatically on open or ready. Request it
within the operator's authorized review budget, then confirm its start and its head.

**Copilot — use a supported request path available to the host.** Confirm that the request starts
a review of the intended head. The 2026-08-16 `gh` login-resolution and REST request failures are
historical observations, not a ban on another supported integration. If the host cannot request
the pass, hand the operator the PR and the Reviewers-box action, and say that the request remains
unmade.

**An empty `reviewRequests` list proves nothing on its own.** An automatic Codex pass leaves it
empty while running; a missing Copilot request leaves it empty because nobody asked. Same list,
opposite meanings — which is why the inspection above precedes the wait. Never report a PR as
"awaiting review" when nothing was requested.

Historical Copilot API failures do not establish a universal request ban. `AGENTS.md` owns the
current policy.
