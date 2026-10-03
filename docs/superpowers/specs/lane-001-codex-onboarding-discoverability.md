# LANE-001 spec — Codex-lane onboarding discoverability

**Status: approved** — drafted 2026-08-02; approved by the operator 2026-08-09 after the design
premise was re-verified against `openai/codex` HEAD `a16863f8` (same-day): explicit-only skills
remain hard-filtered from every model-visible surface including the model's own `skills.list`
tool, and the v2 `spawn_agent` schema still opens "Omit unless explicitly asked". Both
load-bearing files survived three upstream commits since the spec's `2b5bdcf` baseline.
This spec governs the round's scope and acceptance; a paired plan under
`docs/superpowers/plans/` carries the exact payloads. Implementation is additionally gated on
the Phase-0 evidence below.

## Problem

On a Codex session with the fleet installed, plain-language new-service intent has no
model-reachable path to discover `service-onboard` or `host-onboard` (issue #61, field-observed
2026-08-02 on SEC-01). The mechanism is verified upstream (openai/codex @ `2b5bdcf`, HEAD):

1. Skills generated with `allow_implicit_invocation: false` are hard-filtered from every
   model-visible surface, including the model's own `skills.list` tool. The model cannot
   enumerate or recommend them; only a user who already knows the name can type `$skill-name`.
2. Custom-agent descriptions are visible in the `spawn_agent` schema, but its current (v2) text
   instructs "Omit unless explicitly asked" — implicit description-driven delegation, the routing
   model this fleet is built on, is host-suppressed.

So the Claude routing surface (the `homelab-engineer` description, shipped since 2026-07-16 and
present in the generated Codex TOML) is inert on Codex, and the explicit-only skills are
invisible. Field evidence is recorded as learning-ledger candidate `lc_c361b3d3`; the measurement
boundary that let this ship unnoticed is codified in
`docs/decisions/2026-07-30-multi-platform-packaging.md` (retired to Git history).

Operator rulings (2026-08-02): the Codex lane is **supported but limited** — cheap host-neutral
fixes, lane limits codified, no Codex eval harness.

## Scope

1. **New canonical skill `onboarding-map`** (name reviewable): a zero-side-effect,
   model-visible pointer that says which onboarding workflows exist, when each applies (host
   before service), how to invoke them on the current host, and that recommending is not
   executing. It carries **no** `disable-model-invocation`, so Codex generation yields implicit
   visibility — safe by construction because the skill only informs; execution stays behind the
   existing explicit invocations and `homelab-engineer`'s change tiers.
2. **Lane documentation** in `README.md`'s Codex section: the invocation contract (`$skill-name`
   for explicit skills; agents reached by explicit request under the v2 spawn schema), the
   two-halves versioning fact (agent TOMLs are unversioned; a plugin version stamps only the
   skills half), and that `scripts/install_codex_agents.py` is the only agent sync path. The
   `/import` bridge this originally referenced was retired on 2026-08-18; see the packaging
   decision's amendment.
3. **Decision-record amendment** to the 2026-07-30 packaging decision: a reopen trigger for
   "a real workload on a generated lane contradicts a consequence of this record", plus a
   consequence line codifying supported-but-limited. Operator approves via PR review.
4. **Routing-cluster extension** (routing evals were removed 2026-10-03; check these by hand)
   of the homelab-ops cluster: positive discovery-question
   cases for the new skill, with the existing onboarding positives serving as the
   no-displacement guard (below).

## Out of scope

Per issue #61's non-goals and the rulings: no Codex eval harness; no change to
`allow_implicit_invocation`/`disable-model-invocation` on `service-onboard` or `host-onboard`;
no implicit execution path; no new authority; no coupling to OpenBao; the #60 handoff packet and
#62 envelope mechanisms (separate rounds).

## Design decisions

- **D1 — one canonical skill on all hosts, not a Codex-only generated artifact.** A canonical
  skill reuses the whole existing pipeline; a Codex-only emission needs new generator, validator,
  and fixture machinery, which contradicts the smallest-mechanism ruling. The cost is a routing
  surface added to the healthy Claude lane — accepted because that lane has the harness to
  measure it. Fallback: if the before/after diff shows displacement (D2), revisit Codex-only
  emission as its own decision.
- **D2 — the description must lose to `homelab-engineer` on Claude and win alone on Codex.**
  On Claude both surfaces are visible and the skill's negative routing points at the agent; on
  Codex the agent is suppressed, so the skill is the only visible surface and must carry the
  recommendation. This is the crux risk. Gate: existing `pos-add-service` and `pos-host-onboard`
  rates must not regress in the before/after diff. A hard negative (skill must never fire on
  those prompts) is deliberately not seeded — consulting the map en route to the agent is not a
  defect; displacement is. If measurement shows displacement, tighten then.
- **D3 — recommend-only is a content property, not a frontmatter one.** The skill body contains
  no commands, no checklist steps, and no authority language — only the map and the invocation
  contract. That keeps implicit visibility compatible with the explicit-only execution design
  the 2026-07-30 decision chose.

## Acceptance

- [ ] Fresh `homelab-ops` baseline captured **before** any canonical edit (Phase 1); after-run
      under identical conditions shows no regression on existing positives and no negative
      firing at all (standing law: a negative firing is a defect regardless of variance).
- [ ] New positive cases fire: discovery-question prompts (e.g. "is there a checklist for adding
      a service to my lab?") route to `onboarding-map` and/or `homelab-engineer`.
- [ ] `skills/onboarding-map/SKILL.md` exists; description ≤ 1024 chars with capability, triggers,
      and negative routing; adapters regenerated; parity (`--check`), validator, and tests green;
      README inventory refreshed; the generated Codex `openai.yaml` for the new skill does **not**
      carry `allow_implicit_invocation: false`.
- [ ] README lane section landed; decision amendment merged with operator approval.
- [ ] One recorded Codex smoke run on the SEC-01 Linux host (protocol below), evidence filed with
      the round's outcome record.
- [ ] Issue #61 updated with the measured before/after evidence and closed or re-scoped.

## Codex smoke protocol (manual, once, evidence-recorded)

Record `codex --version` first, then in a fresh session with the fleet installed:

1. "Add OpenBao as a new service in my home lab." → transcript shows the model recommending
   `$service-onboard` (naming `homelab-engineer` is also acceptable); no execution.
2. `$service-onboard <service> on <host>` → invokes exactly once.
3. "Add a CSV export feature to my web app's reports page." → no onboarding recommendation.
4. "Build a new VM and put a service on it." → host-onboard named first, service-onboard second.

## Blocking prerequisites (Phase 0)

- `codex --version` from the SEC-01 Linux host. The design premise is the v2 spawn schema; if
  that host runs v1 (no "omit unless explicitly asked" line), the diagnosis shifts back toward
  description quality and this spec returns to review before implementation.
- `[ ! -d "${CODEX_HOME:-$HOME/.codex}/agents" ] || grep -RL --include='*.toml' "Managed by
  sde-agents" "${CODEX_HOME:-$HOME/.codex}/agents"` — any unmarked file is import-vintage; a stale
  `homelab-engineer` there would confound the smoke run. **Empty output is the pass.**

  *Amended 2026-08-11 (mechanical only, semantics unchanged): the original one-liner was
  `grep -L "Managed by sde-agents" $CODEX_HOME/agents/*.toml` (default `~/.codex/agents`). With
  `CODEX_HOME` unset — the documented default — it expanded to `/agents/*.toml` and inspected
  nothing, and with the directory absent or holding no TOMLs the glob did not expand and `grep`
  errored on a literal pattern, so the two states that mean "nothing unmanaged" read as failures.
  It also recurses with `-R` rather than `-r`, because `-r` does not follow symlinks and a
  symlinked stray TOML the host still loads would have read as a clean pass. The gate, its
  blocking status, and what counts as a pass are unchanged; only the expansion and the traversal
  are. Merging the pull request that carries this amendment is the operator's approval of it.*

## Rollback and freshness

The skill is purely additive: rollback is deleting `skills/onboarding-map/`, regenerating
adapters, and reverting the cluster and README edits — one revert commit. The decision amendment
reverts by PR revert. Upstream findings are from unpinned HEAD; the packaging decision's existing
freshness trigger (a Codex CLI upgrade re-runs the adoption live check — the `/import` check it
named was retired on 2026-08-18) also triggers re-reading the spawn-schema and skill-visibility
behavior this spec relies on.

## Round exit

On completion, this spec and its plan are deleted (docs rule 4); LANE-001 leaves the roadmap when the acceptance evidence is committed.

## Appendix — candidate skill description (payload; final text lives in the plan)

> Maps the fleet's explicit-only onboarding workflows without executing them: which exist
> (`sde-agents:service-onboard` for a new or ad-hoc service, `sde-agents:host-onboard` for a new
> or rebuilt machine), the order (host first, then its services), and how to invoke each on the
> current host — plain-language routing or the slash command on Claude Code, `$service-onboard`
> on Codex, where agent delegation is host-suppressed. Use when someone asks whether an
> onboarding checklist or workflow exists, how to start onboarding a service or host, or states
> new-service or new-host intent where no routing agent is reachable. Recommending is not
> executing: the checklists run under `sde-agents:homelab-engineer`'s change tiers, and this
> skill grants no authority. Not for performing lab changes or the onboarding itself — use
> `sde-agents:homelab-engineer`.
