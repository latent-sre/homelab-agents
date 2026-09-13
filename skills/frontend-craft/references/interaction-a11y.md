# Interaction accessibility — overlays, widgets, announcements

Read this when the view involves a modal, drawer, menu, tooltip, or tabs — any custom interactive
widget — or announces async status (toasts, inline save/error states, live-updating values).

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md
wins. The baseline (semantic elements, labeled inputs, keyboard reachability, visible focus) lives
there; this file owns the interaction-level wiring. Attribute names are the web platform's and
apply in any stack; form-field wiring (labels, error linking) lives in `references/forms.md`.

## Modal dialogs — focus is part of the state change

- Opening moves focus into the overlay; closing returns it to the element that opened it. Store
  the opener before moving focus — the browser won't restore it for you.
- Trap Tab/Shift+Tab inside while open, using native `<dialog>` or the repo's established
  dialog/focus-trap primitive — never hand-rolled: dynamic content and nested portals break naive
  traps.
- `role="dialog"`, `aria-modal="true"`, labeled by the overlay's heading; Escape closes it.
- Apply these rules only to a modal dialog (including a drawer implemented as one). A tooltip keeps
  focus on its trigger and connects through `aria-describedby`; it does not trap focus or become a
  dialog. Non-modal popovers and drawers follow their chosen interaction pattern without claiming
  `aria-modal`. See the [APG patterns](https://www.w3.org/WAI/ARIA/apg/patterns/).

## Custom widgets — you own the whole keyboard grammar

- Reach for the platform element (`<select>`, `<details>`, `<dialog>`) or the repo's component
  library first; building custom means owning everything below.
- Select the widget's APG pattern before assigning roles or key handling. Listboxes contain
  `option` elements; menus use `menuitem` variants; tabs use `tab` inside `tablist` with associated
  `tabpanel` elements. These roles and selection/expansion attributes are not interchangeable.
- For a combobox or listbox using active-descendant focus, keep DOM focus on the combobox/listbox
  and set `aria-activedescendant` to the highlighted option's id. An expandable trigger carries
  `aria-expanded` and `aria-controls`; selected options carry `aria-selected`. A roving-tabindex
  implementation instead moves DOM focus according to that pattern.
- Implement that pattern's keyboard grammar, including arrow orientation, selection versus
  activation, and optional keys. Tab normally leaves a composite widget; trapping it belongs to a
  containing modal dialog, not to a menu, listbox, or tablist.

## Announcing async status

- Status that appears without navigation — a toast, "Saved", an inline error, a failed background
  action — renders into a live region (`role="status"`; `role="alert"` only for urgent errors),
  or assistive tech never hears it. Mount the region once and swap its text content; a region
  injected together with its first message is often not announced.
- This completes the Resilience UX rule in SKILL.md: every designed loading/error/empty
  transition a sighted user can see, a screen-reader user can hear.

## Icons and images

- An icon-only button gets `aria-label`; the icon inside it gets `aria-hidden="true"`.
- Decorative images: `alt=""`. Meaningful images: alt text that says what the image conveys, not
  that it exists.

## Anti-patterns

- Positive `tabIndex` values — they create an unpredictable tab order; only `0` and `-1`.
- `aria-hidden` on a focusable element — keyboard focus lands on something assistive tech says
  isn't there.
- `role="button"` (or an onClick) on a div without `tabIndex="0"` and Enter/Space handling — the
  role announces an ability the element doesn't have.
- ARIA replacing a native element that already does the job — wrong ARIA is worse than no ARIA.
- A placeholder as the only label — it vanishes on focus. `references/ux-writing.md` carries the
  voice half of this rule, `references/forms.md` the wiring half.
