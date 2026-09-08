# Frontend stack selection

Read this when starting a **greenfield** UI. An existing repository's stack always wins — if you are
working in one, you do not need this file.

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.

When neither the repository nor the user has chosen a framework, the greenfield default is a
**React + TypeScript SPA on Vite**. An explicit Vue, static-HTML, or other framework choice wins.
Keep two layers cleanly separated — enterprise-grade logic, custom-painted SPA:

**Paint — one Tailwind reset, one token system:**
- **Tailwind** for all styling.
- **shadcn/ui pattern on Radix (or Base UI) primitives** — headless, accessible components you style yourself; this owns the calibrated look. Either primitive layer is fine.
- **lucide-react** icons; **Framer Motion** only when CSS transitions aren't enough (CSS is right for hovers, fades, modals).
- Optional, same Tailwind world: **HeroUI** as a styled layer only when it can share the existing reset and token system; **Aceternity / Magic UI** as a sparing garnish for hero / login / empty-state moments — named in the review packet.

**Logic — zero CSS, decoupled from the paint:**
- **TanStack Query** (server state), **TanStack Router** (typed routing + URL state), **TanStack Table** (headless data grids) — one type-safe, zero-CSS suite that *is* the logic layer, painted with Tailwind.
- **Recharts** for ordinary SVG charts; **uPlot** for dense real-time time-series. The chart
  contract and selection criteria live in `references/data-viz.md`.
- **@mantine/hooks** for utility logic (disclosure, debounce, local storage, hotkeys, click-outside, media query, element size); optionally **@mantine/form** for form state. Both ship no CSS and need no provider.
- Accessible *widget* behavior (focus trap, ARIA, roving tabindex) comes from **Radix / Base UI**, not from Mantine hooks.

The existing-stack and deliberate-integration policy lives in `SKILL.md` (State and data).
This greenfield default is a convention, not a claim that Mantine and Tailwind cannot coexist.

For a greenfield UI with no framework choice, use this stack when SPA navigation and shared client
state are actually part of the requested scope. A static or narrowly interactive page gets the
smallest stack that satisfies its contract. Existing repositories and explicit user choices keep
their selected framework. Any greenfield deviation from the default gets one line in the review
packet.
