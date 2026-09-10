# AI graph engineering boundary for the fleet

**Status:** Accepted -- 2026-08-01 by the operator, amended the same day with the WF-001 probe
evidence below and on 2026-08-12 with the GRAPH-002 operator-consumer ruling; revised 2026-07-31
by an independent cross-model review
**Date:** 2026-07-31
**Evidence snapshot:** `c02d8e12cb2c3d086890b884942908d18bcdbd17`
**Review evidence:**
`graph decision independent review` (retired to Git history)

Git history retains the initial same-day proposal at `b950e43`. This revision keeps every claim of
that proposal that independent verification confirmed, adds the Claude 5-generation counterevidence
the original did not weigh, and narrows the recommended boundary accordingly.

## Decision question

Should this repository turn its implicit fleet topology and its flat durable task state into an
explicit, typed workflow graph? If so, which graph is authoritative, what should execute it, and
which concerns must remain separate?

The revised answer is a **narrower, evidence-gated boundary** in four parts:

1. **Accept the descriptive layer now.** Derive a machine-readable capability graph from the
   canonical `agents/` and `skills/` sources, and add a standard-library workflow-contract parser
   and semantic validator. Validation only -- no executor. This is generated evidence, never a
   second authored fleet.
2. **Accept the effect-broker unknown-outcome reconciliation now, independent of any graph.** A
   crash between reserve, dispatch, and finalization currently leaves a `reserved` action whose
   external outcome is unknown and unrepresentable. That is a defect in shipped code whether or
   not a graph ever executes.
3. **Trigger-bind graph execution.** The original Phases 1--3 (a repo-owned scheduler, run-state
   schema migration, graph graders, controlled dynamic expansion) are deferred behind named reopen
   triggers rather than scheduled. No observed failure currently demonstrates their consumer, and
   the host platform is visibly converging on owning this layer.
4. **Open the counterpart context-engineering round.** The current Claude 5-generation evidence
   locates this fleet's improvement lever in its definitions' prose posture, not its topology.
   That round is CTX-001 on the roadmap and is eval-gated by the repository's own harness.

Do not adopt a universal third-party runtime, replace host-native orchestration, add a knowledge
graph, or permit self-modifying production topology.

## What "AI graph engineering" means here

As of this date, **"graph engineering" is contested community discourse, not a discipline and not
any vendor's guidance**. The term's July 2026 spread traces to social-media debate (catalyzed by a
July 18 Peter Steinberger post), and the viral claims that an Anthropic engineer published a
"Graph Engineering" paper are a misattribution chain: the document behind them is an official
cookbook guide about constructing knowledge graphs *from documents*
([Knowledge graph construction with Claude](https://platform.claude.com/cookbook/capabilities-knowledge-graph-guide)),
which never uses the term and contains no orchestration content. LangChain's own founder posted
that he did not know what graph engineering is. The most durable framing in the debate is the
oldest one: agent graphs are state machines, and the loops-versus-graphs argument is a rediscovery
of decades-old software engineering trade-offs.

This record therefore uses the label only for the engineering of explicit relationships around an
AI system: legal transitions, data flow, authority, recovery, evidence, and evaluation.

Several different graphs are commonly conflated:

| Graph | Nodes and edges mean | Relevance to this repository |
|---|---|---|
| Workflow/control | Work units and legal transitions | The gap is real; the consumer is unproven |
| Agent communication | Agents and the messages or delegations between them | Partly described in prompts; not machine-enforced |
| Capability/authority | Agents, skills, tools, trust zones, and grants | Already implicit and partly validated |
| State/provenance | Runs, attempts, events, artifacts, evidence, and lineage | Strong primitives; incomplete lineage |
| Knowledge/retrieval | Entities, relationships, claims, and source documents | A different problem; no current need proves it |
| Reasoning/thought | Candidate thoughts and dependencies inside inference | Experimental optimization; not a control plane |

The first four can form one operational architecture. Knowledge graphs and graph-of-thought methods
may later consume or emit artifacts, but they must not be allowed to redefine authority or legal
workflow transitions.

## External evidence

### Provider and framework convergence (verified 2026-07-31)

Every claim in this section was independently checked against its primary source during the
review; verification details and nuances live in the archived review evidence.

Anthropic distinguishes **workflows**, whose paths are predefined in code, from **agents**, whose
models direct their own process. It recommends starting with the simplest arrangement, then adding
prompt chains, routing, parallel work, orchestrator-workers, evaluator-optimizer loops, or autonomous
agents only when evaluation proves the added complexity. See
[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents).

Anthropic's production research system adds the economic and coordination evidence: independent
breadth-first work benefits from parallel agents, but their reported system uses roughly 15 times the
tokens of chat, and "most coding tasks involve fewer truly parallelizable tasks than research."
Delegations need an objective, output format, tool/source guidance, and boundaries. See
[How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system).

Anthropic's managed-agent architecture separates three stable interfaces: an append-only session
log, a replaceable harness, and replaceable sandboxes/tools. See
[Scaling Managed Agents](https://www.anthropic.com/engineering/managed-agents).

OpenAI's platform emphasizes durability primitives over topology: durable sessions and resumable
run state, approval as a pause in the same run, validation beside the tool that creates a side
effect, sandbox separation of control plane from model-directed compute, and trace grading of
end-to-end decisions. See
[Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents),
[Guardrails and human review](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals),
[Sandbox Agents](https://developers.openai.com/api/docs/guides/agents/sandboxes), and
[Trace grading](https://developers.openai.com/api/docs/guides/trace-grading).

Google ADK 2.0 describes graph workflows as explicit nodes and edges with typed node inputs and
outputs. Its join warning matters here: a join that expects every predecessor can stop forever when
one predecessor fails to emit an output ("If one of the upstream nodes fails to provide output, the
JoinNode is stuck"), so every join requires a declared failure policy. See
[Graph-based agent workflows](https://adk.dev/graphs/) and
[Graph routes](https://adk.dev/graphs/routes/). Per-node timeout semantics were not confirmed on a
primary page and are not relied on by this record.

Microsoft Agent Framework defines workflows as directed graphs of executors and edges, validates
type compatibility and reachability when building them, and executes them in bulk-synchronous
supersteps; its Durable Extension adds persisted sessions and restart recovery. See
[Workflow builder and execution](https://learn.microsoft.com/en-us/agent-framework/workflows/workflows)
and the
[Durable Extension](https://learn.microsoft.com/en-us/agent-framework/integrations/durable-extension).
An independent critique of that framework --
[Still Not Durable](https://www.diagrid.io/blog/still-not-durable-how-microsoft-agent-framework-and-strands-agents-repeat-the-same-mistake)
-- argues that persisting state is the easy part and that real durability needs automatic failure
detection, duplicate-execution prevention, and fine-grained restart semantics. This repository's
`run_state.py` already carries lease expiry and a unique active-attempt index, which is why
extending it beat adopting a framework in the option analysis below.

LangGraph's implementation and documentation make the replay hazard explicit: checkpoints are saved
at superstep boundaries, and resuming an interrupted node runs that node again from its beginning.
Effects before the pause therefore need idempotency keys, upserts, or another reconciliation
mechanism. See the
[interrupts documentation](https://docs.langchain.com/oss/python/langgraph/interrupts).

### Claude 5-generation counterevidence (added by the 2026-07-31 review)

The original proposal cited Anthropic for session/harness separation but did not weigh the current
Anthropic-side guidance that cuts against building new orchestration scaffolding:

- [The new rules of context engineering for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)
  (Thariq Shihipar, 2026-07-24) reports that over 80% of Claude Code's system prompt was removed
  for the Claude 5 generation with no measurable loss, and names six shifts: strict rules toward
  model judgment, detailed examples toward interface design, upfront information toward progressive
  disclosure, repeated instructions toward tool definitions, manual memory toward auto-memory, and
  simple specs toward rich references. It does not discuss orchestration graphs at all.
- [Scaling Managed Agents](https://www.anthropic.com/engineering/managed-agents) states the
  doctrine the original omitted: harnesses encode assumptions about what the model cannot do, and
  those assumptions go stale as models improve -- scaffolding built for one model generation became
  "dead weight" on the next. A versioned, validator-enforced workflow-contract layer is a highly
  fossilizable harness assumption.
- [Building a C compiler with a team of parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler)
  (2026-02-05) ran 16 parallel agents to 100k lines of working code with, in the author's words, no
  orchestration agent: coordination was git lock files, and the binding constraint was verifier
  quality, not topology.
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  and
  [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
  resolve long-horizon work with compaction, structured note-taking, and role-based splits
  (initializer/coder, generator/evaluator) -- minimal structure, never a typed multi-node graph.
- The host platform now owns deterministic orchestration in a form a plugin can pin: plugin-shipped
  `workflows/` scripts are documented and GA (CLI v2.1.154, 2026-05-28), and were probe-verified on
  CLI 2.1.220 (2026-08-01): namespaced resolution (`/sde-agents:<name>`), `agentType` spawning of
  canonical fleet agents, PreToolUse delivery with plugin-namespaced `agent_type` inside
  workflow-spawned agents (the read-only guard denied a non-allowlisted command there, including
  under `bypassPermissions`), a distinct `workflow-subagent` identity for default workflow agents,
  and schema-validated returns with a five-retry ceiling (CHANGELOG v2.1.186). Pinnable is
  demonstrated; *stable* is not claimed -- the feature is two months old with an active bugfix
  stream, resume does not survive session exit, and no first-party plugin ships one.

### Research direction

Berkeley's compound-AI-systems framing explains why explicit structure matters when it does:
leading systems combine models, retrievers, tools, filters, and traditional code, which requires
traces of intermediate behavior, not just model-level metrics. See
[The Shift from Models to Compound AI Systems](https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/).

Berkeley's 2026 data-systems perspective argues large agent fleets need a substrate for durable
state, coordination, concurrent work, failure handling, and result reuse; its text-to-SQL
experiments found only 10--20% of multi-agent subplans distinct, and it warns against admitting raw
failed traces into memory. See
[Intelligence is Free, Now What?](https://bair.berkeley.edu/blog/2026/07/07/intelligence-is-free-now-what/).

Research systems such as
[Language Agents as Optimizable Graphs](https://arxiv.org/abs/2402.16823),
[AFlow](https://arxiv.org/abs/2410.10762),
[AgentPrune](https://arxiv.org/abs/2410.02506), and
[Agent Lightning](https://arxiv.org/abs/2508.03680)
show that prompts, topology, communication edges, and trajectory credit can be optimized. Their
method shape is consistent with an offline experimentation lane, but the offline-only restriction
is **this repository's policy**, not the papers' prescription -- GPTSwarm markets itself as
self-improving. The policy stands on authority-safety grounds: benchmark gains do not establish
authority safety, recovery correctness, or transfer to this repository's workloads.

Knowledge-graph retrieval is a separate decision. Microsoft GraphRAG extracts entities,
relationships, claims, communities, and summaries from unstructured text to improve retrieval; it
does not supply workflow durability or effect safety. See the
[GraphRAG overview](https://microsoft.github.io/graphrag/index/overview/).

## Current repository topology

The following counts were measured from the evidence snapshot named above and re-verified by the
independent review:

- 11 canonical agents and 19 canonical skills form 30 fleet-member nodes.
- Their definitions contain 140 distinct namespaced cross-reference edges.
- Agent frontmatter contains 85 tool-authority edges.
- `sde-fullstack` has four explicit skill-preload edges.
- Eight routing clusters contain 38 member-to-cluster edges and 117 cases: 64 positive and 53
  negative. They cover 29 distinct members.

Those facts show that this repository already has a substantial **implicit static graph**. The
validator checks namespaced targets and the kind of slash-command target, but it does not emit one
topology artifact, reason about trust paths, or validate executable workflow transitions. See
[`validate_fleet.py`](../../scripts/validate_fleet.py).

The runtime control plane is close to a graph substrate:

- `run_state.py` (retired 2026-09-01) durably recorded runs, tasks, attempts, leases,
  immutable events, cancellation, supersession, target revisions, and evidence links.
- `evidence_envelope.py` (retired 2026-09-01) defined typed producer, context,
  target, criterion, command, environment, isolation, artifact, and limitation fields.
- `effect_broker.py` (retired 2026-09-01) bound one signed approval to one exact action,
  target, executable digest, argument vector, expiry, and nonce.
- `verification_sandbox.py` (retired 2026-09-01) separated verification from the
  builder's mutable workspace.
- [`hosts.json`](../../evals/conformance/hosts.json) keeps host lanes separate and pins the one
  required OpenAI baseline to `gpt-5.6-sol`, high effort, and a read-only sandbox.
- [`multi-agent-architect.md`](../../agents/multi-agent-architect.md) already describes pipeline,
  fan-out/barrier, adversarial verification, bounded-loop, and completeness-critic patterns.

The structural gap is real: tasks under a run are a flat set. A task can be claimed while any
other task is pending or failed. There is no task dependency table, node input/output contract,
condition, join, ready-state calculation, failure edge, compensation edge, or cycle budget. A run's
`contract_digest` proves that some contract was named, but the state store does not persist or
validate the corresponding graph.

**What no evidence shows is the failure that gap should have caused.** No archived review, outcome
record, or roadmap item records a worker claiming logically blocked work, a fan-in deadlock, or a
handoff corrupted between agents in a real run. The gap table below is a priori; the roadmap's own
discipline (LAB-001, EVAL-004, RELEASE-001) is that work waits for a demonstrated consumer.

## Maturity model

Graph maturity is assessed per dimension. **The levels are situational fits, not a ladder to
climb**: the Claude 5-generation evidence above shows deliberately low levels winning for
high-interdependency coding work, and higher levels earning their cost only for parallelizable,
high-value, low-interdependency workloads.

| Level | Topology and contracts | Runtime and recovery | Evidence and improvement |
|---|---|---|---|
| 0 -- prompt loop | One model loop; paths live in prose | Context is the state | Final-output spot checks |
| 1 -- composed workflow | Named chains, routers, workers, and judges | Host session plus manual handoffs | Routing and outcome evals |
| 2 -- explicit graph | Versioned nodes, typed edges, budgets, joins, and legal transitions | Ready-state and path validation | Node, edge, path, and terminal graders |
| 3 -- durable graph | Immutable graph version and typed artifacts | Checkpoint, resume, leases, cancellation, replay, and reconciliation | End-to-end trace lineage and recovery tests |
| 4 -- adaptive graph | Bounded dynamic expansion and subgraphs | Distributed scheduling and cache-safe reuse | Offline topology and policy optimization |
| 5 -- federated graph | Capability negotiation across organizations and protocols | Cross-domain identity, policy, and durable task exchange | Interoperability and ecosystem-level assurance |

This fleet is deliberately uneven: prompt patterns and routing suites at Level 1, implicit
capability topology near Level 2, and Level-3 state/lease/evidence pieces without Level-2
execution. The accepted work below completes the *descriptive* half of Level 2 and repairs a
Level-3 defect; the *executable* half of Level 2 waits for its trigger.

## Gaps that matter before graph execution

| Gap | Current evidence | Consequence |
|---|---|---|
| No workflow definition | Runs store only a contract digest | The legal path cannot be reconstructed or validated |
| No dependency edges | Tasks contain only `run_id`, description, status, and version | Workers may claim logically blocked work |
| No typed node handoff | Evidence is typed, ordinary outputs are not | Telephone-game loss remains a prompt concern |
| No join/failure policy | No all/any/quorum or failed-predecessor state | Fan-in can deadlock or silently skip work |
| No cycle contract | Loop limits exist only in prose | A dynamic loop can spend indefinitely |
| No graph-level trace | Evidence links to attempts, not input/output lineage edges | A final result cannot be traced through every transformation |
| No graph-level eval | Routing cases grade selection, not legal paths or terminal state | A topology regression can remain green |
| No version migration | Run-state schema version 1 rejects mismatches | Adding graph tables needs an explicit migration/rollback contract |
| Ambiguous effect crash | Broker reserves a nonce before execution and finalizes afterward | A crash after the effect but before finalization leaves an unreplayable `reserved` action with unknown outcome |
| No cross-host lifecycle API | Hosts expose different orchestration and authority controls | A claimed universal executor would be cooperative on some hosts |

The effect crash is not solvable by calling it "exactly once." For an arbitrary external system,
the safe contract is at-most-once dispatch plus an explicit **unknown-effect** state, operator or
target-system reconciliation, and target-native idempotency keys where available. A scheduler --
or an operator -- must never automatically replay a reserved effect whose outcome is unknown.
This is the one gap accepted for immediate repair (SAFE-002), because it is a live defect in the
broker regardless of any graph decision.

## Options

### Option A -- keep the graph implicit

Zero implementation cost, but leaves dependency order, joins, retries, budgets, and failure paths
as prompt prose and leaves the broker defect in place. Not adopted.

### Option B -- adopt a third-party graph runtime as the fleet core

LangGraph, Google ADK, and Microsoft Agent Framework contain useful reference implementations. A
direct dependency conflicts with this repository's standard-library-only control-plane rule, adds a
runtime that none of the four supported hosts uniformly embeds, and -- per the durable-execution
critique above -- would import frameworks whose recovery semantics are themselves contested. Not
adopted.

### Option C -- descriptive graph only

Deriving the fleet's capability graph improves review, reachability analysis, and visualization at
low risk. It does not stop a worker from claiming a task whose predecessors are incomplete -- but
no observed failure yet shows that enforcement is needed. Adopted, extended with the
workflow-contract *validator* from Option D.

### Option D -- repo-native two-layer graph control plane

The original recommendation: derive the static graph, then add versioned JSON workflow contracts
executed by repository-owned standard-library code. Its descriptive and validation layers are
adopted (as Option C+); its execution layers (scheduler, migration, graph graders, dynamic
expansion) are **deferred behind the reopen triggers below**, because their consumer is unproven,
their scaffolding is the most fossilizable kind, and the host platform is converging on the same
layer. The graph contract design below is retained so that, if a trigger fires, execution starts
from a reviewed design rather than a blank page.

## Retained graph contract design (for the deferred execution phases)

### Node kinds

The first schema should support only kinds with distinct execution or authority semantics:

- `deterministic` -- trusted code that transforms typed input without model discretion;
- `agent` -- one canonical agent identity invoked by a host driver;
- `tool` -- a bounded tool call with a declared authority and trust zone;
- `human` -- an input or decision pause in the same run;
- `verifier` -- an independent attempt whose evidence gates a transition;
- `effect` -- an approved action executed only through the effect broker;
- `subgraph` -- a versioned nested workflow exposed through a typed boundary.

Nodes should declare an input schema identifier, output schema identifier, trust zone, timeout,
retry policy, idempotency class, evidence requirements, and token/tool/iteration budget where
applicable. A graph must reference canonical agent and skill names; it must not duplicate their
instructions, tools, or model aliases.

### Edge kinds

Edges should distinguish what they authorize rather than use one generic arrow:

- `control` -- a predecessor's terminal state enables a successor;
- `data` -- a typed artifact or value becomes a successor input;
- `condition` -- a finite, validated route based on typed state or evidence;
- `approval` -- an operator decision enables a bounded effect;
- `evidence` -- a criterion must pass before the successor becomes ready;
- `failure` -- a declared failed, timed-out, or inconclusive path;
- `compensation` -- a separately approved recovery action, never an assumed rollback.

Fan-in must declare `all`, `any`, or `quorum`, plus timeout and missing/failed-predecessor behavior.
Cycles must be explicit and carry both a machine-enforced maximum iteration count and a terminal
condition. Arbitrary executable expressions in edge conditions should be rejected; the first
version should use finite enums over typed state.

### Required invariants

1. The graph is immutable for a run and bound to `contract_digest`; dynamic expansion creates a new
   versioned proposal or append-only patch event, not an in-place topology rewrite.
2. A task is claimable only when its incoming control, approval, and evidence edges are satisfied.
3. Node output is persisted as a digest-bound artifact before downstream nodes become ready.
4. Cancellation and supersession dominate late completion across the entire graph.
5. Every cycle has an iteration ceiling; every join has failure and timeout behavior.
6. Every effect routes through the broker, and an unknown effect blocks automatic continuation until
   reconciled.
7. The validator rejects unreachable nodes, duplicate edges, incompatible data schemas, missing
   terminals, illegal trust-zone paths, and effects without approval edges.
8. Credentials remain outside worker and sandbox reach; graph data never grants authority by prose.
9. Traces preserve graph version, node, edge, attempt, artifact, evidence, cost, latency, and model
   observation separately from the final outcome.

Contract references to canonical member names are the load-bearing validator check: a contract that
silently survives a member rename is a second source in waiting, so reference validation ships in
the first descriptive slice, not with the executor.

## Accepted and deferred work

### Accepted -- descriptive compiler and contract validator (former Phase 0)

- Derive a machine-readable capability graph from canonical agent and skill definitions.
- Add a standard-library workflow-contract parser and semantic validator.
- Validate reachability, node IDs, canonical member references, typed schema compatibility,
  terminals, cycle budgets, join policies, trust paths, and effect approval edges.
- Export JSON and optional Mermaid as review evidence; generated output is not committed as a second
  source unless a later decision names a consumer that needs it.
- The derived graph's checks include, at minimum: components no other member references, routing
  edges no eval cluster covers, self-loops, hub-concentration reporting, and a reachability view
  of which prompt surfaces can reach which tools (the 2026-08-01 independent research round
  converged on the same check list from external evidence; see the WF-001 spec's research notes).

This work does not execute models and therefore needs no model baseline.

**Amended 2026-08-12 (operator-consumer ruling, GRAPH-002 drafting):** the descriptive layer's
consumer is the operator, not the T0 validator -- both tools ship as on-demand operator CLIs, and
`validate_fleet.py` gains no graph semantic checks in this round; that wiring, like contract
resolution, is GRAPH-004's when a committed contract and runtime consumer exist. Schema v1 is
deliberately narrower than the retained contract design (no cycles, `all` joins only); the
retained envelope remains the target for the deferred execution phases, reachable only through a
schema-version change. The "Consequences, as realized" list below states the outcome of this
ruling directly, so it needs no discounting.

### Accepted -- effect-broker unknown-outcome reconciliation (SAFE-002)

- Represent the unknown state explicitly: a `reserved` action whose process died after dispatch
  must become `unknown`, never silently replayable and never assumed failed.
- Provide an operator reconciliation path that lists unresolved reservations with their exact
  approved action, target, and argv, and records the operator's resolution as evidence.
- Automatic replay of an unknown effect remains prohibited.

### Accepted -- context-engineering modernization (CTX-001)

Audit the fleet's 30 canonical definitions against the six published shifts for Claude
5-generation models. The fleet currently carries roughly 190 prohibition-style lines
("never/do not/don't"), led by `sde-fullstack` at 24 -- the pattern the current guidance says
degrades frontier-model output. The claim is testable with this repository's own harness:
before/after routing and behavioral runs under paired conditions, negatives-first per EVAL-003's
grading evidence, one pilot definition before any fleet-wide edit. If the evals refute the
published claim for this artifact class, the definitions stand and the result is recorded.

### Accepted -- WF-001 host-workflow pilot (added 2026-08-01)

One bounded adoption of the host's native workflow layer — executed and closed 2026-08-01; the
governing spec retired with its round to the
WF-001 outcome record (retired to Git history):
a plugin-shipped `deep-review` workflow (parallel guarded reviewer lanes with schema-typed packet
contracts and deterministic merge gates), a probe extension codifying the verified platform
contract, and the Claude-only platform boundary. The pilot does not write `run_state.py`; if the
deferred execution phases reopen, that spec decides integration -- workflow scripts cannot touch
the filesystem, so integration would route authority through agent prose, which invariant #8
prohibits.

### Absorbed from the superseded sibling record (2026-08-01, GRAPH-003 ruling)

The independently authored
[`graph control-plane proposal`](2026-08-01-graph-control-plane.md) was superseded by this
record's acceptance; adjudication verified its repository evidence exactly and absorbed its
distinct contributions rather than discarding them:

- **The ledger/checkpoint boundary is settled by construction, not policy.** The host's own
  resume contract makes workflow checkpoint state a session-scoped cache ("If you exit Claude
  Code while a workflow is running, the next session starts the workflow fresh"), so a workflow
  run can never be the durable record and `run_state.py` keeps ledger authority without a
  design decision to defend. This sharpens the WF-001 boundary language above.
- **`contract_digest` is a dangling reference** — stored, validated, and echoed by
  `run_state.py` while nothing resolves it. A reserved slot that resolves to nothing reads as
  enforcement and enforces nothing. Repair closed as SAFE-003 (2026-08-10,
  outcome record retired to Git history): document-and-enforce at
  run creation, required lowercase 64-hex shape, resolution left trigger-bound on GRAPH-004.
- **A typed edge-contract pilot** (one real handoff as a host-neutral contract,
  `contract_digest` made resolvable) is worthwhile but not yet consumer-proven — GRAPH-004,
  trigger-bound per this record's own discipline.
- **Generated-prompt provenance control**, adopted as a standing rule for any future
  contract-to-workflow generation: byte-drift validation only proves generated output matches
  its generator — a generator that hard-codes new prompt wording regenerates cleanly. Generated
  workflow prompts must be assembled from canonical fields, never from generator literals, and a
  prompt-shaped literal appearing in a generator diff is the violation, caught in review of the
  generator. (WF-001's `deep-review.js` is authored, not generated, so the rule binds nothing
  today; it exists so the first generated workflow inherits it rather than rediscovering it.)

### Deferred -- graph execution (former Phases 1--3)

One bounded executable pilot (the `sre-tool` lifecycle, whose value is **gate enforcement** --
review and verification cannot be skipped -- not parallelism, since coding pipelines are the
documented anti-fit for parallel decomposition), graph traces and graders, and controlled dynamic
expansion. Deferred behind the reopen triggers below. If reopened, the retained contract design
and the original acceptance-evidence list govern the spec.

### Future experiments (former Phase 4, unchanged)

- Cache or deduplicate deterministic and research nodes by graph version, input digest, target
  revision, and policy version.
- Test communication-edge pruning and topology search offline against the eval bank.
- Consider A2A Agent Cards generated from canonical role metadata if the fleet later exposes remote
  agents. A2A (Linux Foundation, v1.0, 150+ supporting organizations) complements MCP by describing
  agent capability and task exchange; it does not replace local authority controls. See
  [Google's protocol guide](https://developers.googleblog.com/en/developers-guide-to-ai-agent-protocols/).
- Consider structured corrective memory only after admission, provenance, conflict, and deletion
  policies exist.
- Consider GraphRAG only if a measured retrieval workload needs relationship- or whole-corpus
  reasoning that the current local-first references cannot provide.

## Acceptance evidence for the accepted work

- **Descriptive layer:** a fixture or mutation test for every new validator invariant; graph
  parser/validator tests for valid, unreachable, incompatible, cyclic, unbounded, deadlocked,
  trust-violating, and unapproved-effect contracts; unchanged canonical-source and
  generated-adapter validation; no new runtime dependency.
- **SAFE-002:** tests for a crash at each point between reservation, dispatch, and finalization;
  proof that an `unknown` action blocks replay and requires recorded operator resolution.
- **CTX-001:** paired before/after routing and behavioral runs under identical recorded conditions
  for every edited definition, honoring EVAL-003's agent-positive evidence; a written stop rule if
  the pilot regresses.
- Model baselines: none are owed for the descriptive layer or SAFE-002. Any later Codex/OpenAI
  model baseline in this program uses `gpt-5.6-sol` only, per the operator's SAFE-001 mandate.

## Rejected and deferred applications

- **A universal cross-host scheduler now:** rejected because the hosts do not expose one common,
  enforceable lifecycle and authority interface.
- **A graph database now:** rejected because JSON plus SQLite is sufficient for the current graph
  size and keeps the control plane standard-library only.
- **The maturity ladder as a program:** rejected; levels are situational fits, and climbing them
  without a demonstrated consumer builds exactly the scaffolding the current model generation is
  shedding.
- **GraphRAG as fleet memory:** deferred until a measured retrieval problem exists and memory
  admission can distinguish sourced facts, corrections, and failed traces.
- **Graph-of-thought prompting by default:** deferred; it is an inference strategy, not durable
  orchestration, and must earn its cost on task-specific evals.
- **Automatic production topology optimization:** rejected; the optimizable-graph research
  motivates an offline proposal lane as this repository's policy, not self-authorizing mutation.
- **One global shared state object for every node:** rejected because it collapses least-context and
  trust-zone boundaries. Edges should carry the smallest typed artifact a successor needs.
- **Exactly-once claims for arbitrary effects:** rejected because the broker and an external target
  cannot commit atomically without target support.

## Consequences, as realized

- `agents/` and `skills/` remain the only authored fleet-member definitions.
- The capability graph is generated evidence; workflow contracts, when any are authored, may only
  reference canonical members and are validator-checked from the first slice.
- `run_state.py` is **not** migrated in this round; its schema changes only if a reopen trigger
  fires and a spec defines migration and rollback.
- The effect broker gains the unknown-outcome reconciliation contract now.
- The fleet validator gains **no** graph semantic checks (2026-08-12 amendment above): both graph
  tools ship as on-demand operator CLIs, and that wiring is GRAPH-004's if a runtime consumer
  appears. GRAPH-002 additionally *removed* a test pinning live counts, because an advisory report
  that gates merges makes every topology observation a blocker.
- CTX-001 edits canonical definitions only behind paired eval evidence.
- Host adapters remain host-specific; unsupported runtime controls stay labeled cooperative.

## Reopen triggers for the deferred execution phases

- A real multi-agent run in this repository demonstrates an ordering, join, or handoff failure
  that prose contracts plus `run_state.py` failed to prevent.
- ~~Claude Code's native workflow/task orchestration stabilizes into an API a plugin can pin to~~
  **Partially fired 2026-08-01** (see the probe-verified facts above): pinnable via the CLI pin
  plus probe, not yet mature. The authorized response is the bounded WF-001 host-layer pilot in
  the accepted work above -- adopting the host layer, not the deferred repo-owned executor. The
  remaining maturity conditions (resume surviving sessions, first-party dogfooding, a stable
  documented hook contract for workflow agents) keep the rest of this trigger live.
- An `sre-tool` run large enough that a gate (review, verification, approval) was actually
  skipped or attempted out of order.
- A workflow framework becomes a host-neutral standard already present on all supported hosts.
- A measured retrieval workload demonstrates that a knowledge graph materially improves grounded
  answers over local files and ordinary search.
- Effect targets adopt idempotency or transaction protocols strong enough to narrow the
  unknown-effect state.
- Offline graph optimization shows repeatable gains across the fleet's own eval bank with
  acceptable token, latency, and safety cost.

## Amendment 2026-09-01

`effect_broker.py` was retired 2026-09-01
(`docs/decisions/2026-08-20-effect-transport-policy.md`); the list item above is corrected to say
so rather than link a path that no longer exists. `scripts/workflow_contract.py`, the offline
workflow design validator, was retired the same day: GRAPH-004, its only consumer, is deferred and
trigger-bound, and no role or check names the validator while that trigger stays unfired. GRAPH-004
reinstates or rewrites it if that trigger fires.

The rest of the runtime control plane named above did not survive the same day: `run_state.py`,
`evidence_envelope.py`, and `verification_sandbox.py` were all retired 2026-09-01 (the operator
ruling that the audience is a single home-lab operator, not a multi-worker control plane). The
list above is corrected the same way as the `effect_broker.py` entry — plain backticks with the
retirement noted, rather than links to paths that no longer exist.
