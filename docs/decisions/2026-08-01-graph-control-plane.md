# A graph control plane for the fleet — independent proposal (Claude)

**Status:** Superseded (absorbed) — the operator ruled on 2026-08-01 (GRAPH-003) that the
acceptance of the sibling record
([`AI graph engineering decision`](2026-07-31-ai-graph-engineering.md)) stands as the
adjudication. This record's distinct contributions were absorbed rather than discarded — the
`contract_digest` dangling-reference finding (roadmap SAFE-003), the typed edge-contract pilot
(roadmap GRAPH-004, trigger-bound), the by-construction ledger/checkpoint argument, and the
generated-prompt provenance control (both folded into the accepted record). Every local claim
verified during adjudication held exactly; verification evidence in the
[`adjudication record`](../archive/2026-08/graph-003-adjudication-2026-08-01.md). This record
carries no implementation authority; its absorbed items are governed by the accepted record and
the roadmap
**Date:** 2026-08-01
**Verified state at writing:** `main` at `a445623`. The rival record
(`docs/decisions/2026-07-31-ai-graph-engineering.md`) and its branch are absent from every ref
reachable from the authoring environment (`git ls-remote --heads origin` lists only `main` and
`updates`); they exist on the operator's machine.

## Provenance and independence

This record was authored from primary research and repository evidence, not as a response to the
rival proposal. Declared plainly: the author read the rival record once, in full, during initial
scoping — before the operator's independence directive. It was never re-opened afterward, and the
remote environment this record was authored in cannot reach it at all (verified above). Nothing
below quotes it, paraphrases it, or argues against a position because the rival holds it. Where
the two records converge, the adjudicator should expect convergence on *repository facts* — both
answer the same question against the same tree — and treat convergence on *structure or framing*
as the signal worth scrutinizing (see W8).

## Decision question

The fleet is already a graph twice over. An **org graph** — who owns what — is authored across
`agents/` and `skills/`: 184 unique namespaced cross-reference edges (`sde-agents:<target>`
occurrences, deduplicated per source file; counted 2026-08-01) and 85 tool-authority edges (sum of
explicit `tools:` grants across the 11 agents) connect 11 agents, 19 skills, and their tool
surface, with 8 routing clusters holding 117 graded cases against the edge descriptions. A **work
graph** — what needs doing now — is implied by `scripts/run_state.py`'s runs, tasks, attempts, and
leases. Neither is represented anywhere as a graph: the validator checks references one at a time
and emits no topology artifact, and the task table is flat.

Should that topology become an explicit control plane — and if so, where is the boundary between
what is **authored** (carries judgment, reviewed like source), what is **derived** (generated
evidence, never authoritative), and what belongs to the **host runtime** (execution)?

## Evidence snapshot

All labels: [verified] means checked in this tree at `a445623` on 2026-08-01.

- [verified] The work graph is flat. The tasks table has no dependency, ready-state, or join
  columns (`scripts/run_state.py:110-119`). Claiming a task checks the run is active and the
  caller's optimistic version, but the only *task-level* eligibility gate is
  `status in {pending, failed}` (`:393`) — nothing about any other task. There is no way to
  express "task B starts when task A's evidence exists."
- [verified] `contract_digest` is a dangling reference. It is validated and stored at run creation
  (`scripts/run_state.py:104`, `:248-271`) and echoed back in status output (`:756-770`, via
  `SELECT *` on runs), but nothing in `scripts/` resolves it — the schema reserved a slot for
  "the contract governing this run" that no code maps to a contract document or enforces.
- [verified] Schema v1 rejects any other version with no migration path
  (`scripts/run_state.py:174-177`), so extending the state store is a real, versioned decision,
  not an incremental patch.
- [verified] The durable primitives are strong and event-shaped already: an append-only event log
  enforced by triggers (`scripts/run_state.py:147-163`), a state database whose path must be
  outside the worker workspace (`:68-76`) — a check that is load-bearing only together with the
  operator-owned OS-identity and ACL separation `README.md:172-175` names as the operator's
  responsibility, since a worker identity that can write outside its checkout is not stopped by
  path placement alone — tamper-evident typed evidence (`scripts/evidence_envelope.py`), and an
  effect broker whose reserve/finish nonce ledger (`scripts/effect_broker.py:420-468`) makes a
  crash between reserve and finish legible as an unknown-effect state instead of a silent maybe.
  The one-ledger design below inherits that identity/ACL prerequisite; it does not replace it.
- [verified] The fleet's context doctrine is prose-only. Least-context handoffs, "the final
  message is the interface," and budget rules live in `skills/prompt-craft/references/context.md`
  and `agents/multi-agent-architect.md` with no control-plane representation. Meanwhile
  `skills/sre-tool/assets/plan-file.template.md` is a *prose work graph* — its gates are approval
  edges, its counters are cycle budgets, its batch log is an event stream, its safe-resume rule is
  a checkpoint. The fleet already needed a work graph badly enough to reinvent one in Markdown.
- [verified] A host-native work-graph executor is already in the tree:
  `.claude/workflows/multi-lens-review.js` is a Dynamic Workflows script with schema-validated
  `agent()` returns, phases, and an observed-harness-variance note dated 2026-07-19. The question
  is not whether the fleet will use such executors; it already does, unwired to the ledger.
- [verified] The repository has a working discipline for exactly the authored/derived split this
  decision needs: the accepted
  [multi-platform packaging decision](2026-07-30-multi-platform-packaging.md) plus
  `scripts/generate_platform_adapters.py --check`, which compares every generated byte and rejects
  hand edits.

## External evidence

Dated; [sourced] means the claim is cited but the primary page was not fetchable from this
environment (anthropic.com returns 403 through its proxy), so wording was cross-checked against
secondary coverage on 2026-08-01. [verified] means fetched directly on 2026-08-01.

- [sourced] *Building effective agents* (Anthropic engineering, Dec 2024) — the strongest source
  **against** this proposal: "the most successful implementations weren't using complex frameworks
  or specialized libraries. Instead, they were building with simple, composable patterns," and its
  standing advice to find the simplest solution and only add complexity when needed. O1 takes this
  at face value.
- [sourced] *How we built our multi-agent research system* (Anthropic engineering, Jun 2025) —
  multi-agent systems ran ~15× the tokens of a chat interaction and beat a single-agent baseline
  by ~90.2% on their research eval, with token spend explaining most of the variance; the lead
  agent had to be taught to delegate with explicit objectives, output formats, and boundaries per
  subagent. Edges do not carry context for free — someone designs them — and the token multiplier
  is why edge contracts should carry *least* context, not most.
- [sourced] *Writing effective tools for agents* (Anthropic engineering, Sep 2025) — tools are
  contracts between deterministic systems and non-deterministic agents, and description quality
  measurably steers behavior. This grounds the recurring capability-overhang audit in Phase 3: a
  tool or control written for an older model generation can constrain a newer one, and only
  evidence should retire it.
- [sourced] Four sources gathered 2026-07-31 in the scoping session; the publishing domains are
  not fetchable from the authoring environment, so each is cited by exact title, venue, and date
  for independent retrieval: *"The new rules of context engineering for Claude 5 generation
  models"* (claude.com engineering blog, ~2026-07-24; >80% of Claude Code's system prompt removed
  for the new tier with no eval loss, rules replaced by judgment, examples by typed interfaces);
  *"Graph engineering"* (Thariq Shihipar, Anthropic, with Peter Steinberger, mid-2026),
  distinguishing the stable **org graph** from the ephemeral **work graph**, with context flowing
  only over designed edges; *"Seeing like an agent"* (AI Engineer World's Fair 2026 talk; agent
  failures are usually interface failures); and the Claude Code team fireside (2026-07-21,
  summarized on simonwillison.net; examples removed because the model was "more creative than the
  examples"). One meta-fact matters as much as any single claim: the 2025 guidance praised
  worked examples and the 2026 guidance removed them — **context doctrine is model-generation
  dependent**, so anything this decision hard-codes must be dated and audit-retirable.
- [verified] Claude Code Dynamic Workflows documentation (code.claude.com/docs/en/workflows,
  fetched 2026-08-01). Load-bearing facts: available since CLI v2.1.154 on all paid plans and on
  Bedrock, Google Cloud Agent Platform, and Microsoft Foundry — no longer preview-gated; the
  runtime tracks each agent's result and persists the run's script under the session directory;
  resume replays cached results in agent start order, stopping at the first unfinished agent; and
  decisively for this record: **"Resume works within the same Claude Code session. If you exit
  Claude Code while a workflow is running, the next session starts the workflow fresh."** The
  host's own contract makes workflow checkpoint state a session-scoped cache. It structurally
  cannot be the durable ledger, which settles the double-bookkeeping question (W3) by
  construction rather than by policy.
- [sourced] Third-party landscape, headline-only by design: LangGraph reached 1.0 in Oct 2025
  (durable execution, human-in-the-loop, memory) with broad production adoption; OpenAI's AgentKit
  ships platform-coupled visual workflow tooling. Both are rejected below without a deep read —
  the rejection turns on repository invariants, not on their feature lists.

## Options

**O1 — status quo.** Buys the simplicity doctrine at full strength: 11 agents and 19 skills are
reviewable by eye, loops are forgiving, and nothing new can drift. Costs: the topology stays
invisible (edge changes are reviewable only as prose diffs; routing evals measure them only
statistically), `contract_digest` stays dangling, and the flat work graph keeps forcing prose
plan-files to reinvent scheduling — an observed cost, not a hypothetical one.

**O2 — derived artifact only.** Emit a machine-readable topology/capability artifact from
`validate_fleet.py` and stop. Buys most of the observability value at near-zero risk under an
existing discipline. Costs: does nothing for the work graph, and creates the
artifact-read-as-authority hazard (W5) without the contract layer that would earn it.

**O3 — bespoke scheduler in `run_state.py`.** Add dependency tables, ready-states, and joins to
the state store. Rejected: it rebuilds executor semantics (crash recovery, joins, retries) that
the fleet's primary host now ships natively, takes them on forever in a stdlib-only repository,
and contradicts the repository's own posture of translating authority per host rather than
reimplementing hosts.

**O4 — contracts, not executor (recommended).** The repository owns *authored, host-neutral*
graph contracts and the durable ledger; execution is a host adapter concern. Detailed below.

**O5 — defer until the executor landscape settles.** Was the honest fallback while Dynamic
Workflows was preview-gated. The 2026-08-01 fetch shows it generally available across all paid
plans and three cloud providers, which removes the strongest reason to wait — and Phases 0–1
never depended on any executor at all. Kept live as the fallback if a reopen trigger fires.

## Recommendation: O4 — contracts, not executor

Four commitments, each with the weakness it must survive stated in place:

**1. A derived org-graph artifact.** `validate_fleet.py` gains emission of a machine-readable
topology artifact — nodes are agents, skills, and tools; edges are cross-references, tool grants,
and preloads — `--check`-gated and byte-drift-validated exactly like the host adapters, and marked
non-authoritative in the same breath that generates it. *(W5, artifact read as authority: same
mitigation the generated adapters already use — the accepted packaging decision and docs rule 6
already state that definitions remain canonical in `agents/` and `skills/`; the artifact adds one
more generated consequence, not a second source. W6, "does 11 agents need this": at this scale the
value is not navigation but drift detection — 184 edges are already too many to diff by eye, and
routing evals grade edges only as rates over runs; the artifact makes an edge change a reviewable
diff line.)*

**2. Edges are typed context contracts.** Each handoff declares the context it carries and the
evidence that means "done," in schemas and enums rather than prose rule lists — formalizing the
doctrine `context.md` and `multi-agent-architect.md` already state, in the direction the
Claude-5-generation guidance points (constraints in typed interfaces, judgment in prose).
`contract_digest` stops dangling: it becomes the digest of the contract document governing the
run, and the state store gains a resolver. *(W1, cross-host portability: the contract layer is
host-neutral JSON validated by stdlib code; only executors are host-specific — the same shape as
the accepted packaging decision, where one authored source projects to per-host artifacts.)*

**3. Host-native execution, one ledger.** On Claude, a work graph runs as a Dynamic Workflows
script *generated from* the contract — a projection, with exactly the standing of a generated
adapter; on hosts without a workflow executor, the same contract drives the existing `run_state`
lease loop. That fallback carries a stated deployment prerequisite rather than an implied one:
the generated Copilot, VS Code, and Codex artifacts deliberately do not package the
runtime-control scripts and require an operator-provided trusted copy (`README.md:176-178`), so
on those hosts the contract binds only where the operator has provisioned the control plane — a
source checkout or a trusted copy — and the cross-host claim is bounded to exactly that.
Authority never moves: a step is "done" only when its evidence envelope is written to
the ledger, and workflow checkpoints are cache — which the host's own resume contract already
enforces by making them session-scoped. This generalizes the effect broker's reserve/finish
insight to every step: a crash between an agent finishing and its evidence landing must be
legible as unknown, never silently absorbed. *(W3, double bookkeeping: settled by construction,
see the [verified] Workflows facts above; the Phase 2 crash test proves reconciliation rather than
assuming it. W2, version coupling: the Workflows behavior surface visibly churns across CLI
minor versions — the docs carry min-version gates from 2.1.196 through 2.1.219 — so the pilot
pins the CLI exactly as CI's plugin-contract job already does, and only Phase 2 touches the
executor at all.)*

**4. A judgment boundary, and an audit that can retire controls.** The anti-second-fleet rule,
stated falsifiably: anything containing judgment — prompts, heuristics, branching rationale —
lives in authored agents, skills, and contracts; generation is mechanical and `--check`-gated.
Byte-drift alone cannot enforce this: it proves the tracked output matches the generator, and a
generator that hard-codes new prompt wording regenerates cleanly — the adapter generator already
carries authored text replacements, legitimately. So the rule needs two controls with different
targets: generated workflow prompts are *assembled from canonical fields*, never from generator
literals, and a provenance check fails generation when prompt text has no canonical source;
byte-drift then covers only what it actually covers — out-of-band edits to generated files. A
prompt-shaped literal appearing in a generator diff is the violation, and it is caught in review
of the generator, not in validation of its output. *(W4, second authored fleet: this rule
is the mitigation, and it is checkable, not aspirational.)* Alongside it, a recurring
capability-overhang audit: each control-plane control carries the evidence that justifies it, and
is retired only against measured non-failure (incidents become eval cases first), at
model-generation cadence, not calendar cadence. *(W7, audit churn: the evidence bar and the
generation-boundary cadence are the caps; an audit that cannot cite a measurement changes
nothing. W8, convergence hazard: disclosed in the provenance section; the audit discipline —
evidence before change — is also the honest answer to it.)*

### Phased sequence (contingent on acceptance; no phase starts under Proposed status)

- **Phase 0 — derived artifact.** Emission from `validate_fleet.py`, `--check`-gated. Acceptance:
  regenerates byte-identical in CI on all three platforms; documented as non-authoritative; zero
  canonical fleet definitions changed.
- **Phase 1 — edge-contract schema pilot.** One real handoff (builder → reviewer is the natural
  candidate) expressed as a typed contract; `contract_digest` resolvable, with a schema-version
  decision honoring `run_state.py:174-177` rather than working around it. Acceptance: a resolver
  test maps digest → contract document; violations fail with messages in the validator's
  what-broke-and-why-it-was-silent register.
- **Phase 2 — Dynamic Workflows pilot with a ledger-reconciliation crash test.** Generate the
  executor script from the Phase 1 contract (the in-tree `multi-lens-review.js` flow is the
  candidate to re-derive); kill the run between an agent completing and its evidence landing;
  acceptance: the ledger shows the step incomplete/unknown, a re-run converges, and no judgment
  text exists in the generated script absent from its canonical source.
- **Phase 3 — first capability-overhang audit.** Acceptance: a dated audit record listing each
  control with the evidence that retains or retires it; no fleet definition edited except through
  that evidence.

## Rejected and deferred

- **O3, the bespoke scheduler** — rejected above; recorded here so it is not re-derived.
- **Third-party graph runtimes.** LangGraph is mature and production-proven, and is still
  rejected — on the right ground: the standard-library-only rule scopes to the validators,
  generators, installers, guard, hook, and tests, so it does not by itself ban a separate runtime
  component. What rejects LangGraph is that it installs a second orchestration authority beside
  the hosts the fleet already targets — the multi-host analog of the rejected "maintain four
  authored fleets" — with the new dependency-and-maintenance surface counted as an additional
  cost, not the disqualifier. OpenAI AgentKit is additionally host-coupled. Neither rejection
  required a deep read.
- **Compiling routing clusters into the artifact.** The clusters measure *behavior* (rates over
  runs); the artifact records *structure*. Folding one into the other would let a declaration
  stand in for a measurement — the exact failure the eval discipline exists to prevent. The
  artifact records which edges exist; the clusters keep owning whether they fire.
- **Fleet unhobbling** — applying the Claude-5-generation context-engineering rules to the
  fleet's own agent and skill definitions is real, evidenced follow-up work, and is deliberately
  **not** part of this decision. It is a separate future round; this record only names it so the
  roadmap can hold it without this decision absorbing it.

## Reopen triggers

- Dynamic Workflows makes resume/journal state durable across sessions, or otherwise changes the
  checkpoint contract this record's W3 argument rests on — in either direction.
- A breaking change to the Workflows script surface (`meta`/`agent()`/`pipeline()`/resume), or a
  second host ships a native workflow executor worth a projection.
- The Phase 2 crash test, if reached, observes ledger/checkpoint divergence the reconciliation
  design cannot express.
- The GRAPH-001 adjudication itself: acceptance of the rival record supersedes this one;
  acceptance of this record converts the phased sequence into roadmap items with their own
  acceptance evidence.

## Amendment 2026-09-01

`scripts/effect_broker.py` was retired 2026-09-01
(`docs/decisions/2026-08-20-effect-transport-policy.md`). The `[verified]` bullet above citing
`scripts/effect_broker.py:420-468` stands as a dated observation of the pre-retirement design and
is not corrected.

`scripts/run_state.py`, `scripts/evidence_envelope.py`, and `scripts/verification_sandbox.py` were
also retired 2026-09-01 (operator ruling: the audience is a single home-lab operator, not a
multi-worker control plane). Every citation above naming those three files — the run/task/attempt
schema, the trigger-enforced constraints, the typed evidence envelope — stands as a dated
observation of the pre-retirement design and is not corrected.
