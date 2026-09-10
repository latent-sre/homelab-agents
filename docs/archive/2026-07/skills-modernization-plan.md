# Skills modernization & portfolio plan — July 2026

> **Status: partly landed / partly superseded — verified against the tree 2026-07-24.**
> `docs/fleet-roadmap.md` owns the live status. Landed since this plan was
> written: **item 2** (routing evals — five clusters seeded and four baselined, shipped as
> `evals/routing/homelab-ops.json`, not the `homelab.json` this plan names) and **Tier 3 item 10**
> (`skills/runbook/references/example.md`). **Superseded: item 3** — `incident` was split by
> backlog 1.4/1.5, and its postmortem half already shipped as the standalone `skills/postmortem`;
> do not rebuild it here. Also stale below: the "7 agents + 13 skills" arithmetic (the tree has 11
> skills), and two references to "backend-craft's envelope" — backend-craft now mandates top-level
> RFC 9457 problem+json and explicitly *bans* the nested envelope (backlog 1.3, landed 2026-07-24),
> so read those as "backend-craft's error shape".

Synthesis of four reviews (two expert: skill anatomy, fleet portfolio; two independent: spec
structure, user journeys) answering one question: **improve existing skills, add new ones, or
both — and where does the modern skill anatomy (references/, scripts/, assets/, schemas) actually
pay?**

**Answer: both — with all additions clustered under the home-lab hub, and the anatomy upgrades
concentrated where output shape is consistency-critical.** The SDE side of the fleet is essentially
complete; the gaps are the *recurring operational calendar* (outages → postmortems, monthly
updates, restore drills, host lifecycle, quarterly trends), where the right agent exists but works
from memory. Reviewers converged independently on the same top items; disagreements are recorded
below rather than papered over.

Fleet size after Tier 1+2: 7 agents + 13 skills — acceptable because every addition deepens the
existing `homelab-platform` hub (no new routing frontier), three of four new skills are
invocation-disabled checklists, and each partitions from its neighbors by an observable predicate.

---

## Tier 1 — strongest convergence (3–4 reviewers each)

### 1. sre-tool coordination templates (all three structural reviewers ranked this #1) — **done**

Landed as four assets (the three below plus `assets/spawn-prompt.template.md`, added when a later
handoff-package finding independently converged on the same gap: the spawn prompt is the fleet's
handoff, and it needed a shape — objective, scope in/out, acceptance criteria, boundary, inputs
with contract version, leash, return contract).

The pipeline mandates repo artifacts in prose and gives none of them a shape; every run re-derives
slots, and compaction-survival promises ride on ad-hoc structure. Add three assets, each linked
from SKILL.md with an "instantiate at Phase X" instruction:

- `skills/sre-tool/assets/environment-card.md` — labeled slots for the Phase 0 card + mission
  block (toolchain, ports, run/test commands, module identity, credentials location, progress-file
  path; purpose, mission transaction, threat model, pipeline blind spots), each marked
  `required: fill or "none — why"`.
- `skills/sre-tool/assets/plan-file.template.md` — cadence contract, named gates + status,
  fix-cycle and relaunch counters per builder (the compaction-reset hole), parked reviewer
  hypotheses (never shown to the reviewer), batch/checkpoint log.
- `skills/sre-tool/assets/contract.template.md` — owner, endpoints table, request/response example
  payload pairs, error cases (shaped per backend-craft's envelope), change log with
  propagated-to; instantiation instruction lives in `references/multi-component.md`.

### 2. Seed the missing routing-eval clusters — BEFORE landing new skills (both independents: P1)

`evals/routing/` ships 1 of 4+ named clusters, and the fleet's own doctrine is eval-first. The
homelab cluster is the riskiest unmeasured surface (shared vocabulary over a live lab). Order of
work: seed `evals/routing/homelab.json` (baseline `homelab-platform` vs
`service-onboard`/`lab-audit`/`runbook`), then add the new skills and diff; then
`evals/routing/craft-vs-fullstack.json`. Negative cases to include: "my test is failing" must not
fire `incident`; "Grafana is down" must not fire `root-cause` first; "add Jellyfin" must route to
`homelab-platform`.

### 3. Three new skills (portfolio + journey reviewers converged independently)

All three run under `homelab-platform`'s change tiers, copying `service-onboard`'s
authority-deference pattern (including the #22345 caveat).

- **`incident`** — model-invocable. Reconciles both reviewers' scopes: mitigate-first triage
  doctrine (severity by who's affected → stabilize → mitigate via known-good rollback → verify
  users restored → *then* hand to `root-cause`) **plus** the postmortem
  (`references/postmortem.md`: blameless template — timeline, impact, detection gap, action items
  routed to `runbook` "Common failures" and the next `lab-audit`). One reviewer found the
  doctrinal inversion (root-cause's diagnose-before-fix is backwards mid-outage); the other found
  the missing postmortem owner; the skill needs both halves. Requires a one-clause deferral added
  to `root-cause`'s description and an eval cluster entry.
- **`restore-drill`** — invocation-disabled checklist. Closes the fleet's cleanest broken loop:
  `lab-audit` demands "date of the last actual restore test" and nothing can produce it. Restore
  newest backup to a **scratch path, never a live path** (hard prohibition + rationalization
  table — this is the rule that breaks under pressure) → app-level integrity check → time it (real
  RTO) → record date + duration in the runbook Recovery slot (the record `lab-audit` reads) →
  tear down. Standalone skill, not a reference inside service-onboard: it's invoked on its own
  ("test my backups") and service-onboard is container-scoped and invocation-disabled.
- **`upgrade-campaign`** — invocation-disabled checklist. Works `lab-audit`'s Updates queue as a
  campaign and resolves, in writing, the internal collision in `homelab-platform` ("one change at
  a time" vs a 15-container month): inventory → risk-order (security-exposed surface first) →
  changelog check per item `[sourced]` → **one consolidated Tier-2 approval gate for the batch
  table** → apply one at a time with per-item verify → stop rule: any failure halts the campaign
  and enters `root-cause` → end packet (versions before→after, skipped-and-why).

### 4. `skills/sre-tool/references/security-seed.md` — a reference, NOT a component

Resolves the security-review pointer without a new component: a per-surface threat-model seed
(network-exposed, auth-bearing, secrets handling, container privileges, untrusted/LLM-generated
input reaching shells) for the second `code-reviewer` pass in Phase 3.6. A `security-reviewer`
component was explicitly rejected — "review" vocabulary would collide with the fleet's most
trigger-sensitive description.

---

## Tier 2 — clear value, one or two reviewers

5. **`host-onboard`** (new skill, invocation-disabled) — service-onboard's granularity hole: a new
   *machine* (base-OS hardening, SSH/user policy, firewall baseline, exporter + scrape target,
   backup enrollment, DNS, config-repo enrollment, end-to-end verify). Mirrors service-onboard
   exactly; several steps are Tier 3. Cross-reference from service-onboard step 1.
6. **lab-audit determinism package** — `references/checks.md` (the exact read-only command set per
   check area, including the outside-in exposure set: NAT/forward table, IPv6, UPnP, WAN probe)
   **plus a findings-ledger format** (stable finding IDs, e.g. `.agents/lab-audit/YYYY-MM.md`) so
   consecutive audits diff as new/fixed/still-open and the quarterly review stops being prose
   diffing. Also: `allowed-tools` pre-approvals for the enumerated read-only commands (verbs
   pinned — `Bash(docker ps *)`, never `Bash(docker *)`), add `NotebookEdit` to
   `disallowed-tools`, and one worked example finding in the Output section.
7. **`frontend-craft/references/design-language.md`** — move the default aesthetic (Visual
   character, sidebar-rail specifics, motion timings) behind the predicate its own prose already
   declares ("greenfield or unbranded UI → read first", first row of the table); body keeps the
   universal discipline plus a one-line bar statement. Third independent flag for this across
   review rounds; also cuts every `sde-fullstack` spawn by several hundred preloaded words.
   **Done** — landed as the response to the fourth raise of the preload finding.
8. **`service-onboard/assets/compose.template.yml`** — annotated service block with every step-2
   slot (pinned tag, restart policy, healthcheck, resource limits, named volume); used only when
   the lab has no existing pattern (carve-out mirrors frontend-craft's).
9. **prompt-craft eval wiring** — one predicate-keyed line in Method step 4: editing a description
   in a repo with routing evals → run the harness before/after instead of ad-hoc reps. Optionally
   `assets/eval-case.schema.json` pinning the cluster-file shape.

---

## Tier 3 — cheap polish

10. `runbook/references/example.md` — one complete filled runbook (including an honest `n/a` and
    an `unverified` command); the inline template stays inline (externalizing it was considered
    and rejected — it's needed on every invocation).
11. `root-cause/references/intermittence.md` (optional) — repro-rate measurement and the rep-count
    math for probabilistic bugs (how many clean runs prove a 1-in-5 flake fixed).
12. Text fixes: eng-ladder's routing line gains the infra-that-is-also-a-migration exception
    (currently resolved only in homelab-platform's Boundaries); H1-title convention across skills;
    frontmatter reference's "Fleet decisions" section gains `context`/`agent`/`paths` rationale
    (e.g. lab-audit deliberately not `context: fork` — it needs the caller's lab knowledge).

---

## Adjudicated disagreements & explicit rejections

- **backend-craft `error-envelope.schema.json`** — experts split: one ranked it #3, the structure
  auditor rejected it ("the inline example is the contract; a schema file implies validation
  tooling the skill doesn't run"). Verdict: **optional, low priority** — the OpenAPI contract the
  skill already mandates carries the error shape; revisit only if drift is observed in practice.
- **`lab-audit/scripts/collect-evidence.sh`** — one expert recommends (with load-bearing caveats:
  POSIX, feature-detecting, loud `SKIPPED:` lines); the journey reviewer wants the command
  *reference* instead. Verdict: **checks.md first (Tier 2), script as a later phase** — lab
  heterogeneity makes false coverage confidence the real risk, and the reference delivers most of
  the determinism with none of it.
- **Rejected outright** (with the reviewers' reasons): any new agent; a security-review component;
  in-skill `evals/` directories (repo-level cluster convention wins — routing overlap is
  pairwise); artifacts for `root-cause`'s method or `eng-ladder` (judgment loops; a rubric
  template would create a third paraphrase surface); frontend design assets/boilerplate (would
  fight the design-system carve-out); externalizing runbook's template; data-migration,
  test-strategy, ADR-template, CI-troubleshooting, release-workflow, observability-design,
  dependency-audit, and cost-review skills (each already owned or topic-shaped — full ledger in
  the portfolio review).

## Sequencing

1. Seed `evals/routing/homelab.json` (baseline the existing cluster).
2. Land Tier 1 items 1, 3, 4 (+ root-cause deferral clause); extend the eval cluster; diff.
3. Tier 2, then Tier 3, re-running the validator, tests, and evals at each step.
