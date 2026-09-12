# TypeScript — idioms and the traps that pass review

Read before writing TypeScript or JavaScript in any framework. The universal rules live in
`skills/code-craft/SKILL.md`. On any conflict, SKILL.md wins; the repository's own conventions
outrank both. Layer boundary: `sde-agents:frontend-craft` owns the UI layer — state placement
across the app, resilience UX, accessibility. This file owns what the code does inside a module or
component.

## Make the compiler catch what review would miss

- **Brand your ids.** `type UserId = string & { readonly __brand: 'UserId' }` costs nothing at
  runtime and stops an order id crossing into a user-id slot at check time. Two ids of the same
  primitive type in one signature is the bug the checker can't see until you brand them.
- **Variants are a discriminated union**, not a string field plus `if`s:
  `type State = { status: 'success'; data: T } | { status: 'error'; error: E }` — narrow with a
  `switch` on the discriminant, and give the `default` branch a `never` assignment so adding a
  variant fails compilation everywhere it isn't handled.
- **Separate input types from output types.** What callers send (`CreateTaskInput`) and what you
  return (`Task`, with server-owned id and timestamps) drift independently; one shared type grows
  optional fields that lie in both directions.

## The traps that produce wrong behavior, not errors

- **A floating promise swallows its rejection.** An `async` call without `await` fails silently —
  enable the lint rule (`no-floating-promises`) and treat every exception it flags as a decision to
  justify. `void` only discards the promise; it observes nothing, so fire-and-forget still needs a
  `.catch` that reports to your error boundary. `void someCall()` with a comment is a silenced
  lint, not a handled failure.
- **Sequential awaits on independent work** is the number-one performance defect class: three
  `await`s in a row are three round trips; `Promise.all` makes them one. Waterfalls compound in
  server components and route handlers where every render pays them.
- **Don't await before the branch that needs it.** A fetch above an early return blocks the path
  that never uses the result — move each `await` into the branch that consumes it, cheapest guard
  first.
- **Module scope on a server is process-wide shared memory.** Concurrent renders and requests
  share it: a `let currentUser` written by one request and read by another leaks one user's data
  into another's response. Request data travels through props and arguments; module scope is for
  immutable config and deliberately shared, correctly keyed caches.
- **Barrel imports load the whole library.** A package's `index` entry can re-export thousands of
  modules, and tree-shaking often fails to rescue an external dependency — it depends on the
  package's module format and side-effect declarations, which you don't control. Import deep from
  the module you use, or turn on the framework's import optimizer; deep paths in some libraries
  ship no `.d.ts` and go implicit-`any` under `strict` — check before committing to that form.

## Framework boundary

React and Vue rendering, state, lifecycle, SSR, and component-composition rules live in
`sde-agents:frontend-craft`'s conditional framework references. This language reference still
applies inside their `.ts`, `.tsx`, and `<script lang="ts">` code, but JSX/TSX or the word
"component" alone does not identify a framework.

## The write path (any app with a query/cache layer)

- **The optimistic lifecycle is five beats, in order**: cancel in-flight queries → snapshot every
  affected cache → patch instantly → on error, restore the exact snapshot → on settle (success
  *and* error), invalidate so server-computed fields refetch. Skipping cancel is the classic
  flicker: an already-in-flight refetch resolves after your patch and clobbers it. Rollback
  restores the snapshot verbatim, never a re-derivation.
- **Know when not to be optimistic**: a create returning server-owned fields runs as a pending
  mutation that seeds the cache from the response; a destructive or money-moving write confirms
  first; and server state lives in the query cache only — never mirrored into a client store.
- **One entity lives in many caches** — its detail plus every filtered list page. Patch and
  snapshot all of them through a hierarchical query-key factory, or the badge in the list
  disagrees with the detail view after the write.
- **Mint the idempotency key once per logical write** — at first intent (form init or the click
  that starts the operation) — and thread that same key through every retry of it. A key generated
  inside the mutation function regenerates per retry and protects nothing: that is the
  double-charge bug. Keep the key and payload across automatic and manual retries while the outcome
  is unknown — exhausting retries or settling a rejected Promise does not prove the server did not
  commit. Reconcile that outcome before starting another logical write; rotate the key for the new
  write once the prior outcome is known. An "add another" flow then gets its own key instead of
  replaying the first result. Pair it with disabled-while-pending so a user can't fire a second
  distinct write. [Stripe's error guide](https://docs.stripe.com/error-low-level) illustrates the
  unknown-outcome boundary; follow the target API's retention and reconciliation contract.
- **Retries are stratified by safety**: reads retry with backoff; a non-idempotent write
  auto-retries only when the same server-enforced idempotency key rides along, and never on 4xx. A
  bare network error is ambiguous — the server may have committed before the connection dropped —
  so without a key, a "pure network error" retry is a duplicate charge. A `409` never auto-retries:
  surface the conflict, invalidate, and let the user decide on fresh data.

## Verify

Before "done": the typechecker at the repo's configured strictness and the linter are clean
(`no-floating-promises` on), tests pass per [tdd.md](tdd.md), and anything rendered was
exercised in a real browser — that gate, and where state should live at all, belong to
`sde-agents:frontend-craft`.
