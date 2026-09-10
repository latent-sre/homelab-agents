# ECC component import review — July 2026

> **Status: historical adjudication archive.**
> This file combines the two July 2026 reviews of `affaan-m/ECC`. It preserves what was accepted,
> rejected, or deferred and why. It is not a task list; current survivors live in
> [`fleet-roadmap.md`](../../fleet-roadmap.md).

## Source snapshots and method

### Batch 1

Four targets were read with all supporting references, scripts, templates, and examples:

- `skills/frontend-a11y`
- `skills/frontend-design-direction`
- `skills/agent-self-evaluation`
- `agents/homelab-architect`

Source: `affaan-m/ECC` at `a3130f9ebfae`, shallow-cloned 2026-07-23.

### Batch 2

Ten further targets were fetched in full:

- agents: `agent-evaluator`, `architect`, `homelab-architect`;
- skills: `agent-architecture-audit`, `agent-eval`, `agentic-engineering`,
  `ai-first-engineering`, `api-connector-builder`, `api-design`, `article-writing`.

Source: `affaan-m/ECC` `main`, fetched 2026-07-24. The GitHub API was outside that session's scope,
so Batch 2 is dated but not SHA-pinned.

### Comparison method

Each target was compared with the fleet definitions, tool authority, guard, skill-loading model,
routing evals, and existing portfolio. The review asked:

1. Does ECC expose a capability gap?
2. Is the useful content agent-, skill-, reference-, script-, or sentence-shaped?
3. Would importing the component create routing or authority overlap?
4. Does its example actually satisfy the rule it teaches?
5. Can the fleet adopt the residue without importing weaker architecture?

ECC is MIT-licensed. Substantial adaptations require provenance in their landing commit.

## Overall conclusion

The comparison validated this fleet's architecture more often than it challenged it:

- ECC repeated a six-bullet prompt-defense block across almost every agent, while this fleet uses
  role-specific data-not-instructions wording plus tool controls where enforcement is possible.
- ECC agents named skills they had no mechanism to preload or invoke; this fleet validates
  resolution and namespacing.
- ECC shipped overlapping components with no negative routing or measured overlap.
- Several ECC examples were larger than the rule they taught and one accessibility “good”
  example omitted the active-descendant behavior needed by a screen reader.
- Numeric self-evaluation averaged past hard failures and rewarded confident silence, conflicting
  with this fleet's evidence labels and fresh-context review.

The right import unit was usually a small rule, reference block, or deterministic mechanism—not a
new component.

## Direct answer: hooks and loops

### Hooks

None of the ten Batch 2 components declared, shipped, or wired a hook. `agent-evaluator` carried
only an in-body read-only Bash promise. Batch 1's `agent-self-evaluation` included optional
Stop/PostToolUse reminder hooks; those were rejected because they add unconditioned session noise
and do not enforce quality.

### Loops

No reviewed component shipped a recurring or hook-driven loop:

- `agentic-engineering` described an eval-first prose sequence;
- `agent-eval` wrapped a loop implemented by an external CLI;
- `agent-architecture-audit` diagnosed hidden repair/retry loops in target systems;
- the remaining files were linear methods or checklists.

The fleet's measured routing/behavioral evals and bounded self-improvement loop were stronger than
the reviewed ECC mechanisms.

## Batch 1 decisions

### 1. `frontend-a11y` — adopt interaction coverage, not the component

**Verdict:** Accepted as stack-neutral additions to `frontend-craft`; landed.

The fleet already covered semantic HTML, labels, keyboard reachability, visible focus, AA
contrast, reduced motion, route focus, touch targets, and chart alternatives. ECC exposed five
missing interaction details:

- label/control and error/input wiring;
- async status announcements;
- overlay focus save, move, trap, and restore;
- custom-widget keyboard grammar and ARIA state; and
- anti-patterns such as positive `tabIndex`, placeholder-only labels, or focusable hidden content.

**Landed form**

- form wiring in `skills/frontend-craft/references/forms.md`;
- `skills/frontend-craft/references/interaction-a11y.md` for overlays, widgets, and announcements;
- a core requirement that async state is announced, not only rendered; and
- a keyboard-only pass in the quality gate.

**Rejected form**

The 446-line skill and its 16 TSX blocks were not imported. Its flagship dropdown moved a visual
highlight without `aria-activedescendant`, so the example did not fully deliver the screen-reader
behavior it claimed. The fleet retained rules plus a small verified example instead of adopting an
example library with unearned authority.

**Remaining evidence**

Behavioral verification waits for the next applicable UI task and is tracked as `EVAL-004`.

### 2. `frontend-design-direction` — adopt two invariants

**Verdict:** Two body/reference additions landed; no component imported.

Accepted:

- make audience and interaction tone an explicit design-plan decision; and
- reserve layout space so state, labels, counts, badges, and narrow-width text do not move
  neighboring controls.

Rejected:

- “no cards inside cards” as a symptom already covered by the fleet's elevation hierarchy;
- landing-page “first viewport” doctrine for operator tools;
- dependency guidance already owned by bundle and repository-stack rules.

### 3. `agent-self-evaluation` — reject the rubric, adopt deterministic linting

**Verdict:** Numeric self-grading rejected; deterministic packet linting landed.

The rubric conflicted with fleet doctrine:

- a self-assigned `4.6/5` is uncalibrated precision;
- same-context self-grading is weaker than a fresh evaluator;
- averaging lets a material failure hide behind clarity points; and
- its script started at five and deducted for honest hedge phrases, so silence scored better than
  `[unverified]`.

The useful mechanism was inverted:

- required packet slots are checked mechanically;
- unlabeled uncertainty is flagged, while labeled uncertainty passes;
- a “tests pass” claim without evidence fails;
- missing evidence never defaults to correctness.

This landed as `scripts/packet_lint.py`, fixture tests, and behavioral-runner integration. It was
deliberately not installed as a live output hook because that would train packet-shaped evasion.

One assessor-hygiene sentence also landed in `eng-ladder`: assess what was requested, and do not
invent missing work merely to appear rigorous.

### 4. `homelab-architect` — reject the duplicate agent, adopt two network invariants

**Verdict:** Agent rejected; network safety residue landed in `homelab-platform`.

The ECC agent was a planning-only subset of this fleet's tiered operator and named four skills it
could not actually load. Two concrete invariants were absent here:

- do not cut DHCP over to a local resolver until it has a static address, health evidence, and a
  fallback path;
- sequence VLAN/segmentation work so gateway, switch, AP, DNS, internet, and operator management
  access remain recoverable.

Those rules landed in the existing authority owner. A second home-lab architect would have split
one operational boundary.

## Batch 2 decisions

| Component | Verdict | Accepted residue |
|---|---|---|
| `agent-evaluator` | Reject | None beyond Batch 1's already-landed assessor hygiene |
| `architect` | Reject | None; weaker duplicate of the engineering ladder |
| `homelab-architect` | Confirm Batch 1 | No additional residue |
| `agent-architecture-audit` | Adopt diagnostics, reject component | Wrapper regression and hidden-layer failure taxonomy |
| `agent-eval` | Reject external wrapper, adopt doctrine | Deterministic asserts, pinned fixtures, cost beside pass rate |
| `agentic-engineering` | Reject component | Escalate model tier only after a demonstrated reasoning gap |
| `ai-first-engineering` | Reject | Optional AI-maintainer sentence was later closed as nuance without evidence |
| `api-connector-builder` | Adopt method, reject component | Read multiple in-repo exemplars before vendor docs |
| `api-design` | Reject bulk, adopt residue | Version lifecycle and rate-limit budget headers |
| `article-writing` | Reject by default | Off-remit; no routing home |

### `agent-evaluator`

Its evidence-symmetric scoring improved on the Batch 1 script but remained inside the rejected
numeric rubric. Its prose Bash allowlist was advisory where this fleet's read-only guard is an
enforced control. No new content survived.

### `architect`

Its pattern menus, scaling table, ADR template, and design checklist were weaker forms of
`principal-engineer`, `distinguished-architect`, and `eng-ladder`. It also overlapped ECC's own
home-lab architect without negative routing. Rejected.

### `agent-architecture-audit`

The 12-layer apparatus and JSON report schema were rejected, but six diagnostic moves landed in
`multi-agent-architect`:

- compare direct-model behavior with wrapped behavior before blaming the model;
- find hidden repair, retry, and summarize passes that mutate output;
- prevent an agent's assertions from auto-admitting into durable memory;
- detect the same fact duplicated through prompt, history, and memory;
- separate generation correctness from transport/rendering corruption; and
- enforce required tool use in code rather than prompt prose.

### `agent-eval`

The component wrapped a third-party CLI and had no fleet consumer. Its doctrine was accepted:

- every behavioral case has a deterministic assertion;
- fixtures are pinned and versioned as code; and
- token cost belongs beside pass rate.

The first two are present. Behavioral usage/condition accounting remains `EVAL-002` in the live
roadmap.

### `agentic-engineering`

Its eval-first loop already existed in `prompt-craft` and the eval harness. One cost-discipline line
landed in `multi-agent-architect`: escalate model tier only when a lower tier fails with an
identified reasoning gap, never as the first response to a miss.

### `ai-first-engineering`

Most content concerned organizational process and hiring, outside a single-operator fleet. A
possible sentence treating AI agents as a stricter maintainer class was registered, then closed
during reconciliation because explicit-boundary and deterministic-test doctrine already carried
the value and no observed failure justified more nuance.

### `api-connector-builder`

The component's distinct method landed in
`skills/backend-craft/references/consuming-apis.md`:

1. read at least two existing connectors;
2. map layout, config, auth, retry/pagination, registry wiring, and tests;
3. prefer the newest in-repo pattern over an older one; and
4. count registration, tests, and docs as part of done.

A separate skill would have duplicated `backend-craft`'s existing third-party API trigger.

### `api-design`

Most of the 524-line skill re-derived `backend-craft` with more examples and weaker failure-first
discipline. Its nested `{"error": {...}}` envelope conflicted with RFC 9457 and was permanently
excluded.

Accepted:

- define breaking versus additive API changes;
- keep at most two live versions;
- publish a dated `Sunset`, then return `410 Gone`; and
- expose rate-limit budget headers so clients can self-throttle.

These landed in `backend-craft`. The fleet's own nested-envelope defect was separately corrected
to top-level `application/problem+json`.

### `article-writing`

The skill was competent but outside the SDE/SRE remit, depended on an absent `brand-voice`
component, and had no routing home. Reconciliation closed the import. Reopen only if the operator
intentionally expands the plugin into editorial work.

## Architecture lessons retained

1. **Resolvable references beat aspirational names.** A component cannot “use” a skill it cannot
   preload, invoke, or read by a valid path.
2. **Descriptions route; bodies condition.** “When to use” text below the routing decision cannot
   make a component fire.
3. **Measure overlap.** Multiple components sharing vocabulary require negative routing and evals.
4. **Enforcement beats recitation.** One scoped control is stronger than boilerplate repeated in
   every prompt.
5. **Import the smallest useful unit.** A rule, reference, or script can carry the value without
   introducing another routing surface.
6. **Examples must earn authority.** A large “good” example that misses its own accessibility
   contract is worse than a concise invariant plus a verified example.
7. **Evidence gates do not average.** A material failure or unsupported verification claim remains
   visible regardless of clarity elsewhere.

## Resolution ledger

| Accepted item | Current state |
|---|---|
| Form and interaction accessibility | Landed |
| Audience/tone decision and layout stability | Landed |
| Packet lint and assessor hygiene | Landed |
| Resolver and management-plane safety | Landed |
| Wrapper-stack diagnostics | Landed |
| Model-tier escalation rule | Landed |
| Connector exemplar-first method | Landed |
| API version lifecycle and rate-limit headers | Landed |
| Deterministic behavioral assertions and pinned cases | Landed |
| Accessibility behavioral evidence | Deferred as roadmap `EVAL-004` |
| Behavioral condition/token accounting | Ready as roadmap `EVAL-002` |

Everything else reviewed here was explicitly rejected, superseded, or closed during the 2026-07-28
current-tree reconciliation.
