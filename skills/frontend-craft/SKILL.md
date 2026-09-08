---
name: frontend-craft
description: Design-forward, failure-first web-UI engineering rules — layout, visual character, state, resilience UX, accessibility, testing. Use when building or changing a web UI — pages, dashboards, forms, admin panels, config editors — from a single page to a full SPA. Owns the UI layer; for the backend layer, sde-agents:backend-craft; for end-to-end work spanning both, sde-agents:sde-fullstack.
argument-hint: [the UI to build or change]
---

# Frontend craft

**You write the actual code.** Complete, runnable files — components, styles, config, wiring — never pseudo-code, never "you could use X," never TODO stubs. If a decision is needed, make it, state it in one line, and build. Exception — a material fork (the answer changes what gets built: data model, auth, interface scope) that can't be inferred goes back as one batched question round with recommended defaults *before* building; a materially better alternative to the requested approach gets one recommendation line with the trade-off, then build what was chosen — never silently substitute.

This skill is general-purpose — any web UI, not just operator tooling — held to an SRE-grade bar: failure-first, verifiable, operable. The examples lean ops-flavored; the engineering rules are domain-neutral and apply to a SaaS product or a hobby project the same way. The stack and the design language, though, are **defaults with a carve-out**:

**An existing repository's stack always wins.** The library names below (TanStack, Tailwind, shadcn) are the **default stack** — chosen in `references/stack.md` for greenfield work. In a repo built on other libraries, match that repo and apply the same rules through its equivalents; never rewrite toward the default stack as part of a task.

**An existing design system wins the same way.** The **default design language** (sidebar rail, dark-first, the accent-and-glow language) lives in `references/design-language.md` and applies only to greenfield or unbranded work. In a repo or brand with an established design system — a light-first identity, Material, a corporate token set, a settled shell convention — match it and apply the same discipline (hierarchy, spacing, designed states, accessibility) through its vocabulary; never restyle toward this default as part of a task.

## Layout — organized, uncluttered, space-efficient

- **Hierarchy first**: one primary action per view; group related controls; the eye should land on what matters without hunting.
- **Spacing grid**: consistent scale (4/8px steps), generous whitespace at decision points, higher density where data lives — tables and lists earn compactness, forms and actions earn air.
- **Constrain line lengths**: max content width; multi-column only when content genuinely parallels.
- **Stable under state change**: reserve space for the longest content a slot can hold — labels, counts, badges, hover affordances — so interaction and data updates never shift neighboring layout; verify text fit at narrow widths (long labels wrap or truncate by design, never overflow).
- **Typography**: 4–5 sizes total; hierarchy through size and weight, never color alone.
- **Color & theme**: all color through theme tokens, both themes from day one. Ship a manual light/dark/system toggle, persisted and defaulting to the OS setting — and set the theme class in an inline `<head>` script *before first paint* so there's no flash of the wrong theme on load.

## Visual character & motion — designed, not default

<!-- "color courage" is FRONTEND_CANARY in scripts/probe_plugin.py: its presence reveals
     unwanted frontend context during a backend-only probe. Reword around the phrase, never
     through it, unless the probe and its elicitation change together. -->
Organized and uncluttered is the floor, not the ceiling: keep the color courage turned up — never ship something mistakable for an unstyled admin template. The default design language — app shell, dark-first surfaces, the accent-and-glow palette, motion timings — lives in [`references/design-language.md`](references/design-language.md); read it **before** styling greenfield or unbranded work (in a branded repo, the existing design system wins — see above). Two rules are universal regardless of design system: animate `opacity` and `transform` only (compositor-friendly — no layout thrash), and respect `prefers-reduced-motion`.

**Self-critique as you build** — screenshot what you made and look at it: would a stranger read it as a templated default? Generated UIs cluster around a few stock looks (cream page + serif display + terracotta accent; near-black + one acid accent; hairline-rule broadsheet) and stock component tells (uniform rounded-2xl, purple-to-indigo gradients, a shadow on every surface) — a look you fell into is not a decision you made; change one real thing. Spend your boldness in one place: one deliberate risk you can justify, everything around it quiet. Bespoke or branded work sources its distinctive choices from the subject's own world — its materials, instruments, vernacular — never a house style carried from the last project. (A brief or design system that *asks* for a stock look wins, as always.)

## State and data

- **Preserve the chosen styling system.** In the default Tailwind stack, prefer its existing
  components rather than adding a second styled library without a task need. Mantine components
  can coexist with Tailwind when the repository or user deliberately chooses that combination:
  inspect the installed versions, assign reset/preflight ownership, and coordinate CSS import or
  layer order and theme tokens. Check representative component states in the browser. Preserve
  working integrations instead of banning `@mantine/core`; hooks/form utilities do not introduce
  the styled components' CSS. This is the styling policy's owner; references point here.
- Server state lives in the query/cache layer — TanStack Query in the default stack — with caching, retries, and invalidation; UI state stays local. No global store until two distant components genuinely share state.
- **Typed API client derived from the contract** — the OpenAPI spec or shared types are the source of truth; never hand-maintain response shapes in two places.
- Every async view has designed **loading, error, and empty states**. The empty state is a real design ("no targets configured yet — add one") — never a blank region.
- **Live data**: prefer **SSE** (`EventSource`) for one-way server→client streams (status, metrics, logs) — simpler than WebSocket and it auto-reconnects; use WebSocket only when the client must push too. Feed updates into the Query cache so streamed and fetched data share one source of truth; fall back to interval polling when no stream exists.

## Routing & URL state

- Typed routing (TanStack Router in the default stack): typed routes, nested layouts under the app shell, route-based code splitting so each view lazy-loads.
- **The URL is state.** Search text, active filters, page, sort, and the open tab/detail live in URL search params — the back button works, links are shareable, a refresh restores the view. Never keep that state only in component memory.

## Resilience UX — failure-first, for any app

The SRE lens is just good engineering pointed at the screen: assume every call can fail or hang, and design that path first. True for a SaaS app or a hobby project as much as an ops console.

- **Error boundaries per panel**: a view is many independent widgets; one failing query shows a small inline error in *its* card, never a white screen for the page.
- Errors say what happened *and* what to do next; raw stack traces never reach the user.
- Buttons disable while pending (no double-submits); no infinite spinners — every wait times out into an actionable error state.
- Optimistic updates only with visible rollback on failure.
- **Toasts** confirm actions (saved / deleted / failed) and carry the retry for a failed background action; they never replace inline validation.

## Interface copy — words are design material

- Words exist to make the UI easier to understand and use, never to decorate — same intent as spacing and color. Write from the user's side of the screen: name things by what people control and recognize, never by system architecture ("Notifications," not "webhook config"). Specific beats clever.
- A control says exactly what happens when used ("Save changes," not "Submit"), and an action keeps one name through its whole flow — the button that says **Publish** produces the toast that says **Published**. One term per concept everywhere; consistent vocabulary is how people learn the product.
- **Real content only** — never lorem or placeholder filler. If the content doesn't exist yet, writing it is part of the job.
- The *mechanics* of loading/error/empty states live in Resilience UX above; their *wording* lives in `references/ux-writing.md` (see the table below).

## Accessibility (baseline, not optional)

Semantic HTML first; every input labeled; keyboard reachable with visible focus; contrast at AA. If a div has an onClick, it wanted to be a button. On route change, move focus to the main heading and scroll to top — SPA navigation is silent to a screen reader otherwise. Async status is announced, not just rendered — a toast a screen reader never hears is an undesigned state (wiring in `references/interaction-a11y.md`, per the table below). Responsive by default: the sidebar collapses to a drawer on narrow viewports, touch targets are ≥44px, and data tables reflow or scroll rather than overflow the page.

## Performance

- Route-based code splitting (lazy-load each view) and lazy-load heavy widgets — charts, editors, anything not needed on first paint.
- **Prefetch on intent**: prefetch a route's data (TanStack Query) on hover/focus of its link, so navigation feels instant.
- Fetch in parallel, never in a waterfall; let TanStack Query dedupe. Watch bundle size — a dashboard shouldn't ship a megabyte of JS to show five numbers.

## Testing & quality gate

- Component/logic units in the repo's test runner (Vitest + React Testing Library in the default stack) — test behavior the user can observe (validation, conditional rendering, error/empty states), not implementation details.
- **Playwright** (or the repo's E2E runner) for the few end-to-end flows whose breakage would interrupt someone — the paged flows in a product, the ones that block household use in a lab.
- Before "done": it typechecks, lints, unit + E2E tests pass, the dev server runs, and the primary flow was exercised in a **real browser render**, including a keyboard-only pass — evidence in the review packet. A UI that compiles but was never rendered is written, not verified.

The **review packet** is the end-of-task report defined by the calling agent
(`sde-agents:sde-fullstack` loads this skill for frontend work). Invoked standalone with no packet
convention in context, end with: Changed / Assumptions / Verified / Not verified.

## Before you write it — load the reference for what you're building

Everything above applies to every UI task. The rules below apply only when the view involves the thing
named. Read the file **before** writing that code, not after — and name what you read in your review
packet.

| If the view involves… | Read first |
|---|---|
| styling greenfield or unbranded work (no design system to match) | `references/design-language.md` |
| choosing a stack for a greenfield UI | `references/stack.md` |
| a table, list, or grid of records | `references/data-views.md` |
| a chart, graph, or metric visualization | `references/data-viz.md` |
| a form or any user input to submit | `references/forms.md` |
| a modal, drawer, menu, tooltip, or tabs — any custom interactive widget — or announcing async status | `references/interaction-a11y.md` |
| writing or changing user-facing text — labels, buttons, headings, empty/error copy | `references/ux-writing.md` |
| login, tokens, or route guarding | `references/auth.md` |
| React UI code — the request names React, touched code imports React, the target UI package declares `react`/`react-dom`, or the greenfield stack selected React | `references/react.md` |
| Vue UI code — the request names Vue, the target is a Vue `.vue` SFC or Vue composable, or touched code imports from `vue` | `references/vue.md` |

“Component,” “SPA,” JSX, or a `.tsx` suffix is not framework evidence. Preact, Solid, and other JSX
runtimes are not React. If neither the request nor the target UI package/touched code identifies
React or Vue, read neither framework reference.

Trips two predicates? Read both. Trips none? The core above is the whole job.
