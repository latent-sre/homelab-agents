---
name: sre-tool
description: The full build pipeline for operator tooling — requirements, right-sized design, build, review, verify — with spawned builders and reviewers. Use when building or substantially changing an operator-facing or SRE tool — dashboard, CLI, automation service, monitor, internal web tool. For a feature, fix, or refactor inside an existing codebase, sde-agents:sde-fullstack; for one layer, sde-agents:backend-craft or sde-agents:frontend-craft.
argument-hint: [what the tool should do]
---

**Right-size before Phase 0.** Route a scoped feature, fix, or refactor in an existing project with
an obvious owner and established pattern directly to `sde-agents:sde-fullstack` or the matching
craft skill; its applicable checks still apply.

A small, new single-component tool with clear acceptance criteria and no coordination across
sessions or builders can also run directly under the matching craft skill, even when no existing
pattern exists. Use this short path only when there is no safety-critical behavior, live-system effect,
network exposure, credential handling, or hard-to-reverse design choice. State a short plan,
implement, run meaningful checks, and report the result. No environment card, separate plan or
progress file, spawned agent, or design-approval pause is required solely because the tool is new.
Follow applicable repository rules and preserve decisions needed for any later handoff or resume.

Use the phases below when neither shortcut fits, including new tools needing multiple components
or coordination across sessions or builders. Announce: "Running the sre-tool pipeline:
requirements → right-sized design → build → review → verify."

This pipeline assumes a **spawn-capable context** — Phases 2–3 drive builders and reviewers via the Agent tool. If you cannot spawn agents where you are running, say so up front and degrade deliberately: work the phases inline (Phase 0–1 as written, the build under the craft skills), and flag in the final report that the Phase-3 review was not independent — an inline self-review never counts as the gate.
For safety-critical work, name both consequences: the Phase-3 independent-review gate is
**blocked**, the Phase-4 verification verdict is **inconclusive**, and Phase 5 stays blocked. Execute
the inline checks you can as non-independent evidence, but do not relabel them as either gate.

**Multi-component builds** (e.g. a web UI plus the backend API behind it): the contract, parallel-batch, and review-routing rules live in [`references/multi-component.md`](references/multi-component.md). Read it at Phase 1, the moment the design has more than one component — before spawning any builder. Single-component runs never need it.

## Phase 0 — Requirements (don't skip)

Establish before designing. Infer from context and the codebase where possible; ask the user only what genuinely can't be inferred, batched into one question round:

- **Operator and moment**: who uses this, and when — during an incident (optimize for speed and zero ambiguity) or routine work (optimize for automation)?
- **Inputs, outputs, systems touched** — and whether the tool is read-only or mutating.
- **Placement**: where it runs and deploys — host, container, VM — and which network boundaries it crosses to reach the systems it touches. Placement flips architectures; pin it before design.
- **Blast radius** if the tool itself misbehaves; auth and audit needs.
- **Interface**: CLI, TUI, or web — the thinnest one that serves the operator, not the most impressive one.
- **Success criterion**: the **mission transaction** — the one real-world exchange that proves the tool does its job (for a TLS proxy: a real HTTPS request to a managed route returns the backend). Boot, build-clean, and container-healthy are table stakes, never the criterion.
- **Environment card**: reuse the repository's current project context; fill missing applicable
  facts using [`assets/environment-card.md`](assets/environment-card.md). Use the project-instruction
  file the current host loads; do not create a competing one. For a new cross-host repository,
  prefer root `AGENTS.md`; when Claude participates, add a root `CLAUDE.md` containing `@AGENTS.md`.
  Keep the facts in the imported source, not only in an import bridge. Before handing work to a
  builder, retain the commands, paths, module identity, credential locations (never values), and
  progress location it needs. The mission block carries purpose, the exact mission transaction,
  threat model, and verification limits. Link existing authoritative facts rather than copying
  them into another card; omit inapplicable fields, but name any missing fact that blocks work.
- **Cadence contract**: record existing commit authority, user-requested pause points, and gates
  required by the applicable phases or repository. Ask only for a missing decision that changes
  the work; routine design does not create an additional approval pause. Without an explicit
  grant, never create a commit or move a ref in the source repository. Reuse the existing
  orchestrator-owned plan; use [`assets/plan-file.template.md`](assets/plan-file.template.md) only
  when none exists (default `.agents/plan.md`). Keep authorization, applicable gates and counters,
  and the safe resume point there; builders do not write it. A waiting gate blocks only its own
  scope; independent non-gated work continues.
  If the build may be safety-critical, identify the Phase-4 target here too: an authorized source
  commit or a frozen snapshot with its capture scope and content identity.
- **Verification environment**: before scheduling executable verification, record the supplied
  execution boundary and its owner in the environment card: credential/network/filesystem
  controls, runtime and image digest when container-based, permitted effects, scratch/evidence
  destinations, and whether it is available. No adequate boundary means affected verification
  is inconclusive; resolve that prerequisite through its owner while independent work proceeds.
  If the target uses a machine evidence/state system, identify its schema, validator, and
  transition authority now. This fleet supplies none; without one, use the plan and explicit
  verification packet rather than inventing envelopes or transitions.

## Phase 1 — Right-size the design

Routing rubric lives in the `sde-agents:eng-ladder` skill — that table is the source of truth.

- Single component, low blast radius → design inline at SDE level: a few sentences of plan plus stated assumptions. No ceremony.
- Multiple services, a data migration, or hard-to-reverse choices → spawn the `sde-agents:principal-engineer` agent for a short design doc; surface any one-way doors to the user before proceeding.
- Platform-shaping work (many teams or systems, multi-year consequences) → use the same
  `sde-agents:principal-engineer` engagement at strategic depth, including framing, build/buy
  alternatives, failure domains, and revisit triggers; do not spawn a second design agent.

A multi-component design must also satisfy the contract-artifact, dependency-graph, and mockup-gate rules in [`references/multi-component.md`](references/multi-component.md); the contract artifact is instantiated from [`assets/contract.template.md`](assets/contract.template.md).

Agents do not inherit this conversation. Pass each one full context: the Phase 0 requirements, repo layout and conventions, and constraints.

## Phase 2 — Build

1. **Spawn** `sde-agents:sde-fullstack` with the requirements, the design, exact repo paths and conventions, and the success criterion. The builder preloads code craft and loads layer guidance when the work requires it; supply task scope and constraints instead of copying skill bodies. For trivial scope, implement directly while holding to the same SRE-lens standards (observability, timeouts, idempotency, dry-run for destructive actions).
2. **State a checkpoint contract in every spawn prompt**, shaped by [`assets/spawn-prompt.template.md`](assets/spawn-prompt.template.md) — every slot filled or an explicit "n/a — why": the boundary to run to, the acceptance criteria the builder self-verifies against, scope in *and out*, and the leash — reversible decisions are the builder's to make and log; it returns only at the boundary or on a material fork. What the handoff omits, the agent will improvise.
3. **Accept a builder's review packet on its evidence** (fresh command, own exit status, and
   observed output): re-run declared safety proofs and one spot-check per batch, never the whole
   verification. Apply any caller-supplied machine-record contract identified in Phase 0; otherwise
   record the supported result and remaining gaps in the plan. A progress claim alone is not proof.
4. **Answer status questions from the builders' progress shards** declared in the project context (solo default `.agents/PROGRESS.md`; parallel batches: one `.agents/progress/<component>.md` per builder, one writer per file) — never interrupt a running builder to ask.
5. **Failure path**: a packet that returns short of its checkpoint contract gets one relaunch with the gap named; a second miss escalates to the user. Fix→re-review cycles cap at two rounds, which — counting the build that failed review as the first failed attempt — is `sde-agents:root-cause`'s three strikes reached: the diagnosis is wrong, so switch to that skill's method rather than spending a third fix. Record these counts in the plan file next to the cadence contract — like the contract, they must survive compaction, or a mid-pipeline compaction silently resets the cap.

Multi-component builds add the walking-skeleton, blast-radius-batching, and builder-fleet rules from [`references/multi-component.md`](references/multi-component.md).

Building a **command-line** tool — the streams-and-exit-codes contract, `--json`, config precedence, secrets, and a dry-run whose effect is genuinely gated — follows [`references/cli.md`](references/cli.md); [`assets/cli_skeleton.py`](assets/cli_skeleton.py) is that contract, runnable.

## Phase 3 — Review

1. **Spawn** `sde-agents:code-reviewer` with the mission and **threat model** (from the environment card) and focus files seeded from the builders' "Check first" packet entries. **Seed the gate with those and nothing more — never your diagnosis or your fix.** If you already suspect a specific defect, record it in the plan file and let the reviewer report independently first, then reconcile: a reviewer handed your hypothesis can only confirm it, and you will not be able to tell a discovering gate from an echoing one.
2. **Read the reviewer's independent P0/P1 count in context.** Zero independent P0/P1s on clean work is a valid outcome — the count is never a quota, and a gate must never be pressured toward inventing severity. Judge review quality by declared coverage instead: dimensions reviewed, threat-model paths inspected, evidence cited, scope skipped. What a zero *cannot* do is prove independence by itself — a review that engaged only with your seeded focus files and suspicions, whatever its count, has not independently exercised the code; check the coverage before trusting it.
3. **Reviews are read-only** — run them concurrently with the next build phase unless that phase builds on the reviewed code; only **safety-critical** code (anything that can corrupt production state, delete data, or breach the threat model) treats review as a gate.
4. **Route fixes by evidence and scope.** Send confirmed defects within the authorized build to
   the builder owning the files, including P2/P3 defects; verify the correction and report its
   result. Severity sets urgency and blocking status, not permission to fix. Optional hardening,
   speculative improvements, and changes outside the assigned scope remain recommendations.
   A correction needing new authority or a material design decision waits for that decision;
   independent authorized fixes continue. Reconcile pushback against the evidence. A contested
   safety-critical finding returns to review **once**, then to the user with both evidence sets
   if unresolved. Log the round beside the existing caps; files skipped as mid-edit remain queued
   for review. On **safety-critical** code, give the builder the defect and acceptance test, not
   a dictated implementation; only mechanical fixes need prescribed implementation steps.
5. **The gate keys on the file, not the size of the diff**: any later edit to a safety-critical file — including a one-line "nit" you are tempted to apply directly — re-enters review before it ships. "Too small to review" is how an unreviewed change lands in exactly the code the gate exists to protect.
6. For anything network-exposed or auth-bearing, add a **security review** before deploy artifacts
   ship — spawn `sde-agents:application-security-auditor` on the tool's repository: whole-surface
   source-to-sink threat modeling is that agent's remit, and a depth the diff-scoped reviewer pass
   cannot reach. Keep it independent of the correctness review. Only when that agent cannot be
   spawned, fall back to a second `sde-agents:code-reviewer` pass seeded with a security-only threat
   model (or the CLI's built-in `/security-review`), and say in the final report which gate
   actually ran. A **confirmed critical or high** auditor finding is blocking, equivalent to the
   reviewer's P0/P1 route: give the finding and acceptance test to the owning builder, then re-run
   the auditor on the affected source-to-sink path. Deploy artifacts do not ship while one remains
   open or contested; after one re-audit, a still-contested finding escalates to the user with both
   evidence sets. A probable or possible critical/high candidate leaves the security gate
   **inconclusive** and still blocks deploy until the auditor confirms or rejects it, or the user
   explicitly accepts the risk — note that acceptance, and what evidence would settle it, in the
   final report.
   Apply Step 4's evidence-and-scope rule to medium and low findings too; record fixed defects and
   remaining recommendations in the result.

## Phase 4 — Verify and hand over

**Clean baseline first.** Before the first mission-transaction apply, assert that no stale process the pipeline — or an earlier detour — spawned is still bound to the target's ports, and that the target admin API answers. A stale process serving a *previous* config can return a green that proves nothing — more dangerous than the failed apply it might instead cause. Any process the pipeline launches is the pipeline's to tear down at hand-over.

**Safety-critical work gets an independent verdict.** Anything that met Phase 3's safety-critical bar has its verification executed by `sde-agents:verification-engineer`. Bind that verdict to immutable product bytes:

- A clean committed target is a source commit with a currently unique short ID; resolve it in the
  target repository before handing it to the verifier.
- If the cadence contract grants a source commit, commit at the named green boundary and pass that
  SHA.
- Without source-commit authority, use a frozen snapshot under the verifier's capture and
  identity rules. Preserve its original, execute from a separate copy, and keep product changes,
  test additions, and build output distinguishable. If a complete target cannot be captured and
  independently identified, the affected verdict is inconclusive. Snapshot evidence attests those
  bytes; it does not grant formal commit approval, publication, or live activation.

Spawn the verifier with that exact commit or snapshot, the mission transaction, acceptance criteria, and
the environment card's available execution boundary and evidence destination. Cite its
pass/fail/inconclusive verdict in the final report rather than your
own run: the orchestrator that drove the build wants a green result, which is exactly the interest
that agent exists to remove. Your own spot-checks (Phase 2.3) continue, but they are checks, not the
verdict. If the Agent tool is unavailable, those spot-checks remain non-independent evidence only;
the safety-critical verdict is **inconclusive**, and Phase 5 stays blocked.

When Phase 0 identified an existing machine evidence/state system, use its named schema and
validator, bind its records to the matching attempt and immutable target, and leave transitions to
its declared authority. Do not replace that system's required record with prose. Without such a
system, the verifier's explicit packet is the completion input: record its criterion-level verdicts
and evidence in the plan, keep gaps open, and claim no automated record validation or transition.

For everything else, run the tool and execute the **mission transaction from the environment card, verbatim** — not just the test suite, and not a substitute flow that happens to work. Deploy/install docs are runbooks: every command executed as written or labeled `unverified`. Final report: what was built, how to run it, what was verified end to end, the review verdict, and known gaps.

## Phase 5 — Deploy and onboard

If the tool lands on the lab, hand off to `sde-agents:homelab-engineer` with the `sde-agents:service-onboard` checklist and the tool's runbook as acceptance criteria — built-but-never-onboarded is not done. Name this gate in the Phase 0 cadence contract.
