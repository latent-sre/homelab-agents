# PR review gate: request explicitly, wait on the head, bound the disposition loop

**Status:** Accepted — consolidates rules already operative in `AGENTS.md` ("Opening a pull
request") together with the incident evidence that minted them; it proposes nothing new. The
escape semantics were unified to one-further-round-per-ruling across both convergence bounds on
2026-08-16 (`c2865eb`). The PR cap was raised from two rounds to **three** by operator ruling on
2026-08-17. The trigger/request guidance was corrected on 2026-09-08 after observed platform
behavior met this record's reopen trigger; the global cap and current-head gate remain unchanged.
**Date:** 2026-08-16 (amended 2026-08-17 and 2026-09-08)
**Corroborating archive evidence:**
[`prop-001 outcome`](../archive/2026-08/prop-001-outcome-2026-08-13.md) (records the
review-latency and operator-step findings contemporaneously with PROP-001).

## The rules this record evidences

The governing text is `AGENTS.md`; this record is its provenance, kept out of the per-session
context on purpose. Inspect actual review activity and its commit before waiting or requesting.
Use the configured reviewer's supported trigger within operator authorization; an operator UI
step is a fallback for a request the host cannot make. Both passes are waited for on the current
head, and a review-driven edit owes another wait; every comment is dispositioned as applied or
declined with the reason. At most three review-driven edit rounds land per PR, with an explicit
operator ruling buying one further round.

## Historical evidence (2026-08-16)

1. **Reviews are request-triggered and land roughly ten minutes after the request, not after PR
   creation.** Every bot pass in this repository's history is preceded by a `review_requested`
   event. PR #124: review requested at 07:07:07, passes at 07:17:28 and 07:17:44.
2. **The request cannot be automated from an agent session.** The reviewer is
   `copilot-pull-request-reviewer[bot]`, which `suggestedActors` does not list; `gh pr edit
   --add-reviewer Copilot` fails to resolve the login, and a REST `requested_reviewers` post
   silently leaves `reviewRequests` empty. The PR page's Reviewers box is the only path that
   works. The Codex connector has followed Copilot's request without needing one of its own.
3. **Merging without waiting costs reverts.** A PR merged four minutes after opening carried a P1
   finding that landed two minutes after the merge and cost a revert.
4. **Unread comments carry real refutations.** A later PR's unread review comments correctly
   refuted a claim that would otherwise have promoted an unsupported rule into `AGENTS.md`.
5. **PR #128 merged unreviewed** while a session waited for a pass nobody had asked for. The
   guide then described the reviews as arriving "two to five minutes behind `gh pr create`",
   which read as a wait to serve rather than a step to take; the rule was reworded to name
   requesting as an action, and on this repository an operator one.
6. **The head-binding clause closed a loophole in the rule's own first draft**, which would have
   let the gate be satisfied by a review of code a later fix had already replaced.
7. **PR #136 ran ten review-driven rounds** after the two-round deep-review cap was written,
   because that cap bound the static-review gate and left the disposition loop open. That is the
   origin of the PR cap (set at two, raised to three in 2026-08-17's ruling below), and of
   stating explicitly that the cap bounds edits, never
   waits.

## Trigger correction (2026-09-08)

PR #177 at `2dcffc46bb8bd16f934d5d282752db70fbb4921b` was marked ready at 06:59:53 UTC.
Its [Codex review summary](https://github.com/latent-sre/homelab-agents/pull/177#issuecomment-5580706356)
reported both Code Review and Security Review starting at 07:00:01 UTC with trigger
`Draft marked ready`. While both ran, GitHub's `reviewRequests` array was empty. The captured
completion times were 07:07:47 UTC for Code Review and 07:07:08 UTC for Security Review; the code
review is independently bound to that head by
[review 5138464308](https://github.com/latent-sre/homelab-agents/pull/177#pullrequestreview-5138464308).
The summary comment is mutable, so its later contents must not be treated as the original capture.

[Current official documentation](https://learn.chatgpt.com/docs/third-party/github), fetched on
2026-09-08, documents automatic reviews when enabled, the manual `@codex review` trigger, and the
separate `@codex security review` trigger. This contradicts the old universal claims that creating
a reviewable PR never starts review and that every review requires an operator-only request.
It does not establish that Copilot's API behavior changed, that every repository enables automatic
reviews, or that a new push automatically received either pass. Check the actual head and status.

Evidence items 1–2 above remain historical observations of the prior integration. Their blanket
request restriction is superseded; the cap, reviewer obligations, disposition rule and fresh-head
wait remain. For PR #177 only, the operator authorized four rounds on 2026-09-08. That exception
does not raise the fleet-wide three-edit-round limit.

## The operator ruling (2026-08-17)

The cap is **three** review-driven edit rounds per PR, not two. Evidence item 7 minted *a* cap and
still stands — ten unbounded rounds is the failure mode — but two rounds proved too tight against
observed review behavior: a first round routinely draws a follow-up finding on the bytes it just
minted (PR #142's round 2 caught defects in that branch's own round-1 fixes), which consumed the
budget before any independent third look could land. Three rounds lets that self-correcting
sequence finish inside the cap instead of spending the operator escape on it. The escape survives
unchanged on top, so a ruling still buys a fourth round when one is genuinely owed.

## Rejected alternative

Keeping this chronicle inline in `AGENTS.md` — rejected 2026-08-16. The narrative served the
rules' editors, not the next session (the guide's own reading rule), and cost roughly 530 tokens
in every session's context on every host. This record is the durable home; the guide cites it by
path, and the validator's stale-path tripwire fails the build if the record goes missing — so the
citation is machine-checked where the inline narrative never was.

## Reopen trigger

A change in the review platform's behavior — the bot becoming requestable via API, review passes
firing on PR creation, or a different reviewer identity — invalidates evidence items 1–2 and
reopens the operator-step rule. The caps (items 3–7) reopen only on an operator ruling.
