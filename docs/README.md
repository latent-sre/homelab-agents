# Documentation map

This directory separates current work, durable decisions, active execution plans, and historical
evidence. Mixing those roles is how a landed item becomes an apparently open task, or a dated
review silently starts governing the current fleet.

## Authority

| Document class | Purpose | Authority |
|---|---|---|
| [`fleet-roadmap.md`](fleet-roadmap.md) | Current, deferred, and blocked fleet work | The only live status owner |
| `decisions/` | Proposed or accepted architecture decisions, rejected alternatives, and reopen triggers | An accepted record governs its decision; a proposed record carries no implementation authority |
| `superpowers/specs/` | Scope and acceptance boundaries for a round; each spec's Status header says whether it is drafted or approved | Approved: governs what its paired plan may implement. Drafted: awaiting operator approval, no implementation authority |
| `superpowers/plans/` | Branch-specific execution instructions and exact payloads | Operational only while that round is active |
| [`archive/`](archive/README.md) | Dated reviews, donor adjudication, and completed-plan evidence | Historical evidence only; never a task list |

The roadmap became authoritative after the 2026-07-28 current-tree reconciliation. Historical
files may retain dated “open” sections as evidence of what was believed then; those sections do
not re-enter the queue unless the roadmap imports them.

## Current documents

The roadmap, the engineering-program map, decision records, and any active-round spec/plan listed
below are live. Everything else here is historical evidence.

| Document | State | Read it for |
|---|---|---|
| [`archive/2026-09/pr178-repair-budget-check-2026-09-10.md`](archive/2026-09/pr178-repair-budget-check-2026-09-10.md) | Behavioral evidence | Paired fresh-context repair-budget decisions and return packets; four synthetic cases, with real delegation and repeated-run reliability unmeasured |
| [`fleet-roadmap.md`](fleet-roadmap.md) | Live | Every unfinished, blocked, deferred, and decision-needed item. Nothing else adds work |
| [`engineering-program.md`](engineering-program.md) | Live | The durable map from each program strand — handoff, loop, graph, self-learning — to the mechanisms implementing it and the checks keeping it honest. Mechanism-anchored by rule: no live item IDs, counts, or episodes, and the validator resolves every path it names |
| [`fleet-development.md`](fleet-development.md) | Live | The maintainer's page: which file owns which convention, the porting method, host-specific authority, the Codex lane in detail, how the two hooks are wired and why, workflows, the validation tiers, and the host probe — the long-form material the root README no longer carries |
| [`decisions/2026-09-07-homelab-operating-flow.md`](decisions/2026-09-07-homelab-operating-flow.md) | Accepted scope, under verification | Main-based simplification of routine closeout, task briefs, runbooks, approval presentation, and conditional builder guidance; compatibility, unchanged controls, and outcome checks |
| [`decisions/2026-09-07-design-agent-merge.md`](decisions/2026-09-07-design-agent-merge.md) | Accepted | Why `distinguished-architect` was absorbed into `principal-engineer` instead of kept as a second label: identical tools, document-only writing mandate, guarded inspection shell and caller-mediated handoff, leaving reasoning depth and time horizon as the only real distinction — and what now triggers the deeper framing inside one engagement |
| [`decisions/2026-09-02-single-operator-audience.md`](decisions/2026-09-02-single-operator-audience.md) | Accepted, amended 2026-09-02 | The audience ruling — one home-lab operator, packaged to share — and what it closes: CTX-002 (met by the roster cut), LEARN-002, HANDOFF-001, and LADDER-002 (won't-do), each with its reason and what a reopen would need; the amendment records the behavioral harness retirement as a consequence, closing EVAL-011 and ORACLE-019 with it |
| [`decisions/2026-08-29-homelab-live-effect-gate.md`](decisions/2026-08-29-homelab-live-effect-gate.md) | Accepted, amended 2026-09-01 and 2026-09-02 | The seven GATE-006 decisions: the plugin ships `homelab-engineer`'s managed gate as a second PreToolUse hook (ask, or deny when the session cannot prompt), transport evidence becomes structural, standing policy is host-specific, one retry, `Effect class:` folded into `Tier:`, no web tools, `service-onboard` owns the predicates — with the documented host contract they rest on and the reopen triggers |
| [`decisions/2026-08-23-homelab-proportional-operations.md`](decisions/2026-08-23-homelab-proportional-operations.md) | Accepted, amended 2026-08-29, 2026-09-01, and 2026-09-02 | Amends the homelab Tier 2 policy so a managed prompt can be the single human decision, tightly bounded operator-owned host policy can be standing authorization, finite routine plans and stable sentinels avoid repeated ceremony, and onboarding controls follow four risk predicates; Tier 3 and the separate body-compaction round remain unchanged |
| [`decisions/2026-08-20-effect-transport-policy.md`](decisions/2026-08-20-effect-transport-policy.md) | Accepted, amended 2026-08-23, 2026-09-01, and 2026-09-02 | Retires the Tier 2/3 effect-broker mandate from `homelab-engineer` in favour of host-native transport and operator handoff; owns the original transport correction and provenance, while the 2026-08-23 record above governs managed prompts as decisions and bounded standing Tier 2 policy |
| [`decisions/2026-08-16-pr-review-gate.md`](decisions/2026-08-16-pr-review-gate.md) | Accepted | Provenance for the PR review-gate rules in `AGENTS.md` — request is an operator step, passes are waited on the current head, every comment dispositioned, three review-driven edit rounds with a one-round operator escape (raised from two by the 2026-08-17 operator ruling recorded there); consolidates the incident chronicle formerly inline in the guide, with its reopen trigger |
| [`decisions/2026-08-01-graph-control-plane.md`](decisions/2026-08-01-graph-control-plane.md) | Superseded (absorbed), amended 2026-09-01 | The second, independently authored GRAPH-001 proposal. The operator's GRAPH-003 ruling (2026-08-01) let the sibling record's acceptance stand and absorbed this record's distinct contributions: SAFE-003, GRAPH-004, the ledger-by-construction argument, and the generated-prompt provenance control |
| [`decisions/2026-07-31-ai-graph-engineering.md`](decisions/2026-07-31-ai-graph-engineering.md) | Accepted, amended 2026-09-01 | The graph boundary: descriptive layer, SAFE-002, CTX-001, and the WF-001 pilot accepted; graph execution trigger-bound. Accepted 2026-08-01, amended with the WF-001 probe evidence, and extended with the absorbed sibling-record contributions per the GRAPH-003 ruling |
| [`decisions/2026-07-30-multi-platform-packaging.md`](decisions/2026-07-30-multi-platform-packaging.md) | Accepted | Canonical-source ownership, generated host adapters, per-host authority controls, and Codex's separate custom-agent sync |
| [`decisions/2026-07-29-deployment-mode.md`](decisions/2026-07-29-deployment-mode.md) | Accepted | Option A governs daily Claude use: installed, namespaced plugin mode with no active fleet junctions; includes normal-session guard evidence and rollback |
| [`decisions/2026-07-28-fleet-role-expansion.md`](decisions/2026-07-28-fleet-role-expansion.md) | Accepted | ROLE-001, ROLE-002, and LABSEC-001 accepted and implemented 2026-07-29 (PRs #37–#42); ROLE-003 was accepted later the same day and landed with ROLE-004's `verification-engineer` (PR #43), so the record holds no open work. Its one recorded departure: the record proposed `WebSearch`/`WebFetch` for the auditor, and the shipped agent is local-only |
| [`superpowers/specs/lane-001-codex-onboarding-discoverability.md`](superpowers/specs/lane-001-codex-onboarding-discoverability.md) | Approved, round not active | LANE-001's Codex host-evidence prerequisites, discovery/recommendation boundary, acceptance conditions, and rollback; Phase 0 remains outstanding and no paired plan exists |
| [`superpowers/specs/2026-08-18-multi-host-plugin-architecture-design.md`](superpowers/specs/2026-08-18-multi-host-plugin-architecture-design.md) | Implemented 2026-08-18 | The three retired host lanes (Codex `/import` staging, the Copilot CLI lane, the stray `.codex-plugin/`), why the VS Code lane survives on workspace discovery from `.github/agents`, and the disproved "deliberately empty override" claim — the standing evidence for AGENTS.md's rule that a manifest field naming an empty override does not keep a host away from the hooks |
| [`superpowers/specs/handoff-001-onboarding-handoff-packet.md`](superpowers/specs/handoff-001-onboarding-handoff-packet.md) | Closed 2026-09-02 (won't-do) | HANDOFF-001's scope, twelve required semantics, paired-eval acceptance, non-goals, and rollback boundary |
| [`superpowers/plans/handoff-001-plan.md`](superpowers/plans/handoff-001-plan.md) | Closed 2026-09-02 (won't-do) | The active lean HANDOFF-001 payload: one six-line producer packet, one builder consumer, six focused cases, and no global packet gate |
| [`archive/2026-08/save-toolkit-delta-scoping-2026-08-29.md`](archive/2026-08/save-toolkit-delta-scoping-2026-08-29.md) | Review evidence behind PORT-002 | Donor delta, ranked grafts, per-graft scrub lists, and rejected leads; PORT-002 owns scope and status |
| [`archive/2026-09/agent-outcomes-2026-09-08/`](archive/2026-09/agent-outcomes-2026-09-08/) | Historical outcome record | The six design outcome trials and the independent private-frontend verification run after the principal/distinguished merger: four design passes, two embedded consults with material partials, and the withheld overall verification pass over a pre-existing accessibility issue — with frozen definitions, synthetic architecture cases, rubric and per-run grades. Public evidence only; DESIGN-001 owns the remaining design work |
| [`archive/2026-09/diagnostic-gate-2026-09-07.md`](archive/2026-09/diagnostic-gate-2026-09-07.md) | Implementation evidence | Diagnostic false-prompt reproductions, conservative parsing boundary, review repair, and the ten-minute probe timeout |
| [`archive/2026-09/operational-correctness-repairs-2026-09-07.md`](archive/2026-09/operational-correctness-repairs-2026-09-07.md) | Historical outcome record | The operator-selected correctness repairs following the design-agent merger: upgrade-campaign ordering that must support every intermediate and rollback combination, incident diagnosis beyond shallow liveness, per-target backup freshness, and PowerShell native exit handling — recorded explicitly as repaired guidance, not as a tested lab or installed fleet |
| [`archive/2026-09/selected-guidance-corrections-2026-09-07.md`](archive/2026-09/selected-guidance-corrections-2026-09-07.md) | Historical review evidence | The eight operator-selected recommendations (3–7, 10, 13, 21) that survived source review under a stop-and-report condition, the corrections confined to ten canonical guidance files and their twenty generated projections, and the confirmation that no description, tool grant, roster, or runtime mechanism changed. Paired machine evidence: `selected-guidance-cases-2026-09-07.json` and `selected-guidance-evidence-2026-09-07.json` |
| [`archive/2026-09/roadmap-history-2026-09-01.md`](archive/2026-09/roadmap-history-2026-09-01.md) | Historical record | Every sentence cut from `fleet-roadmap.md` on 2026-09-01 when its items were compressed to contract fields — status narration, outcome detail, dated addenda, and full acceptance enumerations — verbatim, one section per roadmap item, linked from that item's Source |
| [`archive/2026-09/learning-ledger-retirement-2026-09-01.md`](archive/2026-09/learning-ledger-retirement-2026-09-01.md) | Historical record | The 34 promoted learning candidates whose released-version retest the retired ledger still tracked (19 awaiting release, 15 awaiting retest), by destination, with the last commit holding the records — so a session meeting one of those destinations knows no retest was taken |

`superpowers/plans/` is empty when no round is active, and `superpowers/specs/` holds only specs
whose roadmap item is live: a spec headed **drafted** awaits operator approval and starts no round
(REV-001, HANDOFF-001, and LANE-001 all sat here in that state before their 2026-08-09 approvals);
the roadmap item's status and next action, not the file's presence, say whether a round is
running. A *finished* round's spec and plan still retire to their outcome record under rule 4 — a
plan file lying around after its round is how a finished task keeps reading as pending work.

## Rules

1. A historical review may explain why a decision was made; it never proves that work is still
   open.
2. The roadmap names current work. A source review or decision record owns the detailed rationale.
3. A decision record states its status, what is proposed or chosen, what lost, and what evidence
   should reopen it. Only an accepted record governs implementation; it never becomes an execution
   checklist.
4. An active plan may be detailed and branch-specific. Once complete, its lasting decisions and
   evidence move to a short outcome record; Git history retains the exact execution payload.
5. When a file moves or is consolidated, update every tracked reference in the same commit.
6. Agent and skill definitions remain canonical in `agents/` and `skills/`; documentation and
   generated host adapters never override them.
7. GitHub issues are evidence-bound intake, never a second work tracker. An issue adds work only
   when the roadmap imports it (the roadmap entry names the source issue); an issue that is not
   imported is field evidence awaiting triage, and letting the two lists drift is how the same
   work gets tracked twice or dropped once.
