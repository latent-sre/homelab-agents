# save-toolkit delta scoping — second sibling mining round — 2026-08-29

> **Status: review evidence behind PORT-002; not a task list.** `docs/fleet-roadmap.md` owns the
> work. This file records what was read, at which donor revision, what was verified on both sides,
> and the ranked menu with a disposition per item, so the round can start from a named revision
> without re-deriving any of it. The reader is the next session, which has none of this in memory.

## Scope and method

- **Donor:** [`latent-sre/save-toolkit`](https://github.com/latent-sre/save-toolkit) — the renamed
  `latent-sre/sre-agents` (its `docs/decisions/2026-08-05-save-toolkit-rename.md`; the local
  `F:\repos\sre-agents` checkout has the same remote and was on a work-specific branch, so it was
  not read). Read at pushed `main` **`2a04d357`** (2026-08-28, 1114 commits) from a fresh clone.
  Re-obtain it with `git clone https://github.com/latent-sre/save-toolkit.git` followed by
  `git config core.longpaths true && git restore --source=HEAD :/` — its `docs/reviews/` paths
  overflow the Windows path limit and the first checkout fails without that. The clone lived in the
  session scratchpad and is not retained; every path below is relative to that revision.
- **Our baseline:** the July adjudication
  [`../2026-07/sre-agents-adaptation-backlog.md`](../2026-07/sre-agents-adaptation-backlog.md)
  (imports authored 2026-07-24), and the donor's own reverse import,
  `docs/reviews/2026-08-05-sde-agents-adaptation.md` there, which scanned this fleet at `528fb7d`
  (2026-08-04) and lifted guard hardening, six validator tripwires, and body content into their
  `language-idiom`, `backend-craft`, `ci-actions`, `root-cause`, `postmortem`, `frontend-craft`,
  `obs-alerting`, `eng-ladder`, and `agent-security`. **The flow is bidirectional**: a donor
  passage that reads as new may be our own July text coming back; the per-pair diffs below settle
  that per item.
- **Method:** a scoping read, not the PORT-001 round. Rosters and descriptions were parsed from
  frontmatter on both sides; per-component commit counts since 2026-07-24 located the churn;
  heading and reference-file diffs ran on every matched pair; the five new skills and the reworked
  bodies were read in full; and a presence grep on our side confirmed each candidate is a gap, not
  a paraphrase we already carry. The PORT-001 three blind passes run later, on the chosen set only.
- **Rulings carried forward:** the July "Killed" list still governs — `merge-gate`,
  `production-change-gate`, `service-lifecycle` (was `service-onboarding`), the `sre`/`scribe`
  agents as agents, `agent-authoring`'s body, and all PCF/Splunk/Wavefront/Moogsoft/ThousandEyes/
  Akamai/GCP material — and so does the July headline: on the shared twins this fleet is the more
  evolved descendant, so wholesale import regresses.

## The delta since 2026-07-24

Skills created after our import (their `git log --diff-filter=A`):

| Skill | Created | What it is | Disposition |
|---|---|---|---|
| `operational-learning` | 2026-08-01 | Documentation-only closeout: `prepared`/`proposed`/`blocked`/`duplicate`/`not_applicable` dispositions, service/alert card and knowledge-index templates | Skip as a skill (our learning loop is `self-improve-loop` + `postmortem`'s feed-forward; alert/service cards have no lab consumer). Its disposition vocabulary is already in our `runbook` gate |
| `akamai-edge`, `gcp-ops` | 2026-08-07 | Vendor triage | Skip (Killed-list class) |
| `service-readiness-audit` | 2026-08-23 | Read-only per-service readiness audit with an evidence table | **Candidate 2** |
| `incident-drill` | 2026-08-24 | Explicit-only game day that runs a synthetic incident through the fleet's own lanes; scenario pack, scaffold/lane/report scripts, retro template | Trigger-bound (see method leads) |
| `workflow-graph-engineering` | 2026-08-24 | Runtime-neutral executable-graph design contract | Trigger-bound pointer for GRAPH-004 |
| `incident-investigation` | 2026-08-26 | Evidence-selected incident work mode (first response / hypothesis / systemic) | **Candidate 5** (one section) |

Commits per matched component since 2026-07-24 (their tree): `agent-authoring` 48,
`obs-dashboards` 41, `operational-learning` 25, `incident-command` 23, `runbook` 21,
`production-change-gate` 20, `ci-actions` 19, `stack-profile` 18, `obs-alerting` 17, `obs-logs` 16,
`postmortem` 14, `agent-security` 14, `backend-craft` 12, `language-idiom` 11, `eng-ladder` 10,
`root-cause` 4. Agents: `sre` 33, `observability-engineer` 24, `reviewer` 21, `scribe` 20.
Much of the churn is their SKILL-001 audit (a per-skill "conditional router" cut, 2026-08-23/27)
and the 2026-08-22 removal of a shared evidence banner from 28 skills — structural, not new rules.

## Verified skip — twins where this fleet is equal or ahead

| Pair | Evidence | Verdict |
|---|---|---|
| `root-cause` | Unified diff of the bodies: ours carries the hypothesis table *inside* the loop plus the `lab-incident` deferral; theirs keeps the standalone worked example we trimmed in July (item 3.2) | Skip |
| `eng-ladder` | Diff is naming and routing targets only (`software-engineer`/`ops-tooling` vs our agents/`sre-tool`) | Skip |
| `language-idiom` ↔ `code-craft` | Their references are now smaller than ours after their trim: python 75 vs 223 lines, go 59 vs 211, tdd 36 vs 79, safe-refactor 33 vs 56 | Skip, except the feature wave (candidate 8) |
| `frontend-craft` | Same ten references; their body is a SKILL-001 router (65 lines) over the same material | Skip content; the router *form* is a PROP-lineage method note |
| `argument-hint` | Their audit flagged 18 of 32 missing; ours is 20 of 20 | Not a gap |
| `postmortem` | Near-identical after the 2026-08-05 round trip (near-miss, luck, detection-source, artifact-per-action are ours); two residual clauses remain | Candidate 7 only |
| `researcher`, `repository-investigator` | Their 08-05 record lifted our reframing and deterministic-read rule; nothing new flowed back | Skip |

## Ranked candidates — each a confirmed gap on our side

Size: XS < 20 lines, S ≤ 60, M ≤ 200, L > 200. "Description edit" says whether routing evals are
owed; none of the eight plans one.

### 1. `runbook` ← step craft, responder read-back, living-runbook history — **M**

- **Source:** `skills/runbook/references/step-craft.md` (the eight ways a correct-looking step
  fails at 3 a.m.: ambient target, success-only expected output, out-of-order arrival,
  non-idempotent rollback, destructive step with no look-first, no stop condition, placeholder
  with no source, scope that grew); `skills/runbook/SKILL.md` § "Before you publish — read it
  back as the responder" (four questions) and § "Living runbooks" (held / contradicted / missing per
  step, appended as incident-history rows pinned to the runbook version);
  `skills/runbook/references/living-runbooks.md` (the accretion protocol; sourced 3× MTTR claim).
- **Target:** `skills/runbook/` — a new `references/step-craft.md`, a read-back section in
  `SKILL.md`, and the held/contradicted/missing outcome feeding `postmortem`'s "Runbook updated"
  slot. Our disposition gate (update/create/propose) stays; theirs lacks it.
- **Gap evidence:** 2 hits for the step-craft ideas in our `SKILL.md`, 0 in `references/example.md`;
  no read-back pass; no accretion convention.
- **Adaptation notes:** scrub `cf restart-app-instance`/`cf scale`/PCF-space examples into
  docker-compose / systemd / kubectl-context / ssh-host ones; `scribe` → the `runbook` skill under
  whichever agent holds Write; `operational-learning` disposition → `postmortem` feed-forward.
  Their living-runbook protocol assumes YAML frontmatter with `version`, `last_reviewed`,
  `last_verified`; ours has no frontmatter contract — the round decides adopt-the-two-dates or
  rephrase (their `schemas/runbook-frontmatter-v1.schema.json` is the optional companion). Skip
  the Confluence import section and script entirely.
- **Description edit:** none.

### 2. `lab-audit` ← per-service readiness lens — **M**

- **Source:** `skills/service-readiness-audit/SKILL.md` — the evidence table (ownership and
  boundary; runtime and health; delivery and recovery; telemetry pipeline; dashboards; alerts and
  SLOs; operations knowledge; dependencies and capacity; backup *and a dated restore rehearsal* —
  "existence alone is not restore evidence"; drift), the documentation-gap vs readiness-gap
  split, the verdict stamped with its UTC date and the age of the oldest load-bearing evidence,
  "up to three validated fixes, never padded", and "route the findings, do not file them".
- **Target:** a new section in `skills/lab-audit/references/checks.md` ("9. Service readiness —
  per service"), plus the dated-verdict line in `SKILL.md`'s Output. Not a new skill: the July
  ruling folded service-onboarding into `service-onboard` + `lab-audit`, and proportionality
  forbids a second read-only sweep.
- **Gap evidence:** our eight checks are lab-wide (exposure, containers, certificates, backups,
  monitoring gaps, drift, capacity, updates); no per-service lens, no evidence-age stamp.
- **Adaptation notes:** `stack-profile` → the lab profile convention; `pcf-ops`/`gcp-ops` rows →
  `homelab-platform`; `scribe` closeout → `runbook`/`postmortem`; drop `cf env`/`CF_TRACE` (keep
  the class: never a credential-bearing read). The restore-rehearsal row links `restore-drill`.
- **Description edit:** none planned; if the sweep's description must name services, the
  `homelab-ops` routing cluster is the paired-run owner.

### 3. `observability` ← dashboard hygiene, Alloy failure modes, alerting lifecycle — **M–L**

- **Source:** `skills/obs-dashboards/scripts/dashboard_hygiene.py` (216 lines, stdlib, offline;
  textual panel/variable rules over Classic/V1 dashboard JSON, refuses V2 rather than
  half-checking; exit 0/1/2); `skills/obs-pipeline/references/alloy.md` §§ "Backpressure and loss
  — where data quietly dies", "Debugging a running Alloy", "Health-check the pipeline itself",
  "End-to-end canary"; `skills/obs-alerting/references/grafana-alerting.md` § "The evaluation
  lifecycle — design every rule around all four knobs" (pending period, recovery threshold,
  keep-firing, notification templates); `skills/obs-dashboards/references/json-model.md` § "The
  version ladder" for the served-version facts.
- **Target:** `skills/observability/scripts/dashboard_hygiene.py`, sections in
  `references/pipeline.md` and `references/alerting.md`, a version-ladder note in
  `references/dashboards.md`.
- **Gap evidence:** 0 hits for recovery threshold / notification template / keep-firing in our
  `alerting.md`; 0 for JSON-model or hygiene checks in `SKILL.md`; 3 Alloy mentions in
  `pipeline.md` with no debugging or loss section.
- **Adaptation notes:** keep our dashboards-as-code stance — they dropped theirs on 2026-08-22
  because their team edits in the Grafana UI, a team fact, not a merit finding. Their Grafana
  HTTP-API reference (467 lines) is for live apply by an unguarded agent and stays out. Their
  LogQL/PromQL references (203/220 lines, executed against live datasources 2026-08-22) are
  dialect-neutral but ours are lab-tuned; compare heading by heading in the round rather than
  replacing.
- **Description edit:** none planned. Its own branch: it carries a script and edits near the body
  that the description summarizes.

### 4. `ci-actions` ← safety-contract additions — **S**

- **Source:** `skills/ci-actions/SKILL.md` § "Always-on safety contract": name the exact release a
  SHA pin resolves to (never a floating major alias in the comment); pin what a `run:` step
  installs (lockfile or hash-pinned, lifecycle scripts as a stated decision); "a check that is not
  required blocks nothing" — read the branch ruleset; make gate liveness observable (a
  push-only gate that is switched off looks identical to passing — give it a manual dispatch and a
  scheduled floor). Their 2026-08-26 commits validated these against their own workflow.
- **Target:** `skills/ci-actions/SKILL.md` "four rules" and `references/hardening.md`.
- **Gap evidence:** 1 hit in `SKILL.md` and 3 in `hardening.md` across the related terms —
  partial; the ruleset and liveness rules are absent. Our own T2 tier already practises the liveness
  rule (weekly sweep plus manual dispatch), so encoding it is consistent, not new policy.
- **Adaptation notes:** drop the protected-environment-secrets-not-OIDC team default and every
  PCF/Bamboo line.
- **Description edit:** none.

### 5. `lab-incident` ← "the ladder has a bottom" and the incident spine — **S**

- **Source:** `skills/incident-investigation/SKILL.md` § "The ladder has a bottom" — a proposed
  `no-incident` finding when the symptom does not reproduce, no impact is evidenced, and the
  golden signals are at baseline, blocked by two conditions: *baseline that is really absence*
  (confirm signals arrive before reading flat as healthy) and *a symptom that recovered on its own*
  (self-recovery removes the trigger, not the mechanism — route to lower-urgency diagnosis, never
  close); "raising an alarm must stay cheap, and it only does when closing one that came to nothing
  carries no blame". § "Preserve the incident spine": severity and impact, blast radius and trend,
  UTC timeline, hypotheses with evidence for and against, mitigation performed or recommended —
  each `[unverified]` rather than invented.
- **Target:** one section in `skills/lab-incident/SKILL.md` (mitigate-first structure unchanged);
  the spine fields into its handoff step.
- **Gap evidence:** 0 hits for no-incident / self-recovery / false-alarm in `SKILL.md` and
  `references/golden-signals.md`.
- **Adaptation notes:** the mode ladder itself (first response / hypothesis / systemic) is not
  imported — `root-cause` and `lab-incident` already split that; `sre`-agent ownership language is
  dropped.
- **Description edit:** none.

### 6. `prompt-craft` security reference ← OWASP LLM Top-10 crosswalk, integration controls — **S**

- **Source:** `skills/agent-security/references/owasp-llm-top-10.md` (23 lines, the crosswalk from
  the five-question review to the OWASP categories, corrected 2026-08-23) and
  `references/integration-controls.md` (60 lines: webhook/log/MCP integration controls).
- **Target:** our `agent-security.md` reference (90 lines; 0 OWASP mentions), as a closing
  crosswalk table and an integration-controls subsection.
- **Adaptation notes:** the July ruling stands — never import `agent-security/SKILL.md` as a
  skill; the plugin-false hook claims stay out.
- **Description edit:** none.

### 7. `postmortem` ← causal-method clause, instrumentation prerequisite — **XS**

- **Source:** `skills/postmortem/SKILL.md` — "Five Whys is one option, not a required five-line
  quota; a branching incident may need a fault tree or causal graph — name the method"; "every
  action names its instrumentation prerequisite: the signal, exporter, or pipeline change its
  proof depends on, `none` only when the proof is independent of missing telemetry".
- **Target:** two sentences in `skills/postmortem/SKILL.md` and one template slot in
  `assets/postmortem.md`. 0 hits for either on our side.
- **Description edit:** none.

### 8. `code-craft` ← 2026 language-feature wave — **XS**

- **Source:** their 2026-08-21 "second feature wave": Python t-strings, TypeScript `satisfies` and
  `using`, React Actions / `useActionState`, Vue macros (`language-idiom/references/python.md`,
  `typescript.md`; `frontend-craft/references/react.md`, `vue.md`).
- **Target:** `skills/code-craft/references/{python,typescript}.md`,
  `skills/frontend-craft/references/{react,vue}.md`. 0 hits for t-strings and `satisfies`/`using`
  in ours; 1 for React Actions.
- **Adaptation notes:** re-verify each against current upstream by deterministic reads before
  landing (their `researcher` did so at their date; provider docs outrank the donor's prose).
- **Description edit:** none.

## Method and infrastructure leads — dispositions

| Lead | What it is | Disposition |
|---|---|---|
| SKILL-001 audit method | Their per-skill screen: a 7,500-immutable-byte entrypoint limit (owner-set, from 5,000); the "rules charged twice" measure (body sentences that restate a reference which loads alongside it — `agent-authoring` echoed 18 of 82); *probe before routing* (clean-room probes asking whether the model produces the content unprompted — if yes it is recitation and is cut, not routed); a confirmed conditional body becomes an "if the question involves X, read Y" router. Records: `docs/reviews/2026-08-26-three-pass-skill-audit.md`, `2026-08-27-skill-001-frontend-craft.md`, `2026-08-27-skill-001-agent-authoring.md`, roadmap `SKILL-001` there | **Fold into a PROP-003 successor** to the closed PROP-002 sweep ([`prop-002-outcome-2026-08-13.md`](prop-002-outcome-2026-08-13.md)); `self-improve-loop` (265 lines, six references) is the first entrypoint through that screen. Method, not content |
| `evals/build_probe.py` | Fixture-backed, tool-bearing, *code-graded* agent probes: a seeded repo with a two-release history; a fake CLI on PATH that must never receive the dangerous verb; a booby-trapped canary file on a fork branch that must never execute; "did the tests it wrote pass when the probe ran them"; "did a test command run before Verified was claimed"; two isolation levels (allowlisted env, and `docker run --rm --network none` via `CLAUDE_CODE_SHELL_PREFIX`); INCONCLUSIVE never becomes a verdict. Runs `claude -p --agent` with `--tools`, `--allowedTools`, `--disallowedTools`, `--permission-mode dontAsk` | **Investigate as an EVAL item.** Our `scripts/eval_behavioral.py` already passes `--allowedTools` (measured 2026-08-15), so the permission flag is not the novelty; the outcome grading and `dontAsk` are. It imports PyYAML (their 2026-08-23 ADR allows third-party deps) — only the design ports under the stdlib rule |
| `incident-drill` | Game day against the fleet's own lanes: ~90 minutes, ~USD 7, eight lanes, ground truth held out of packets, human gates recorded, retro separates fleet findings from harness defects | **Trigger-bound.** A lab drill would run `lab-incident` → `homelab-platform` → `postmortem`; it has no consumer until an operator wants a measured answer to "would our agents hold the line". Record on the roadmap, do not build |
| `workflow-graph-engineering` | Runtime-neutral design contract: typed state, node/edge classes, fan-out/fan-in, retries with idempotency keys and an explicit `UNKNOWN` outcome, approvals, durability, cancellation, termination, taint, graph-level evals; six predicate-keyed references, a fourteen-section template | **Source pointer for GRAPH-004** (deferred, trigger-bound). Its cancellation/reset/late-arrival semantics are exactly what `workflow_contract.py`'s schema v1 excludes |
| HOST-002 VS Code observation | Their probe (VS Code 1.134.0): a plugin-wide `PreToolUse` payload has no custom-agent identity, but VS Code merges hooks from the selected custom `.agent.md` before invoking Copilot Chat — "a generated agent-scoped hook is the candidate boundary"; `hooks/copilot-hooks.json` is deliberately empty until a canary proves merge and denial. Record: `docs/reviews/2026-08-24-host-002-vscode-tool-enforcement.md` | **Roadmap note only.** Does not overturn our "never port the hook to VS Code" rule — the boundary is unproven there too; it names the experiment that could |
| `scripts/mutation_guard.py` | Single-module mutation check: derives the test files, applies one small logic mutation, stops at the first survivor; refuses fleet-wide sweeps by design | **Skip for now.** `AGENTS.md` already mandates the by-hand mutation test for validator and guard changes; a tool needs a consuming task (proportionality). Reopen if a PROP/validator round wants the instrument |
| `scripts/check_stale_names.py` | Rejects retired component names under live trees | Skip: no renamed component is pending here; the validator's namespace check covers references |
| Gate A glob-derived test enrollment | `gate_a.py` enrols `scripts/test_*.py` by glob after a 236-line test was found wired into nothing | Skip: `scripts/run_tests.py` discovers `tests/test_*.py` already |
| `check_query_catalog.py` + `obs-logs/references/query-catalog.md` | A team catalog of starting queries (question / applies-to / query / reads-as / healthy-looks-like / owner / verified) with a validator that rejects tokens, session ids, and raw payloads | Trigger-bound: a lab query catalog is worth having once a second incident reuses a query; the validator's three content classes are the reusable part |
| `operational-learning` cards | Service card, alert card, knowledge index templates with `last_reviewed`/`last_verified` semantics | Skip: no lab consumer; `service-onboard`'s operating doc and `runbook` cover the lab's need |
| Runbook frontmatter schema | `schemas/runbook-frontmatter-v1.schema.json` + `scripts/test_runbook_schema.py` | Optional companion to candidate 1; decide there |
| `commands/adr.md` | ADR scaffold slash command | Skip: `distinguished-architect` writes ADRs into `docs/decisions/` already |
| `copilot-hooks.json`, `guard-session-preflight.py` | Empty Copilot hook file; a SessionStart hook that probes the resolved interpreter with an allow and a deny payload | Skip the first (structural rule here: no file at that host's hook path). The second is a **small candidate for the guard**: it turns "guard unavailable" from a silent per-call deny into a session-start message — file under the guard playbook if the fail-closed message has ever surprised an operator |

## Everything else seen, with a reason

`backend-craft` gained "Resource modeling & HTTP semantics" and "Collections" sections plus a
Spring Boot reference — the Java reference is out of scope; the two sections are **unverified**
against our `references/api-design.md` (not read side by side) and are the one content item this
record leaves open for the round to check. `incident-command` (23 commits) is P1–P4 severity,
command roles, and stakeholder communications — enterprise coordination with no single-operator
analogue. `stack-profile` (18) stays a convention, per July item 3.7. `agent-authoring`'s new
references — `roster.md` (165 lines), `delegation-graph.md`, `skill-portability.md`,
`artifact.md` — overlap `multi-agent-architect` and `prompt-craft`; the July ruling against the
body stands, and the references were not diffed against ours (**unverified**; `skill-portability`'s
"portable six" frontmatter fields and host size limits are the likeliest residue). Their
multi-engine eval contract, evidence-capture pipeline (`EVIDENCE-001`), `sre-context` resolver, and
`context-requirements.yaml` per skill belong to a framework this fleet does not run.

## Contribute-back candidates (recorded, not acted on)

Their 2026-08-05 record protected their guard, adapters, and clean room; what they did not take
and we still hold: `learning_ledger.py`'s admission-gated promotion (they declined it as a large
single-writer surface), `effect_broker.py`/`run_state.py` (declined pending their own consumer),
the routing-benchmark provenance sidecar, `capability_graph.py`, and the `runbook` disposition
gate. Listed here so the round's bidirectional-delta step starts with a list, per PORT-001 step 2.

## Not read, and instrument errors corrected

- Not read end to end: their obs references beyond the headings and sections named above;
  `agent-authoring/references/*`; `backend-craft/references/api-design.md`; the eval runner and
  graders (`run_evals.py`, `graders.py`, `execution_profiles.py`).
- Two mid-run instrument errors were caught and corrected before anything rested on them: a
  doubled frontmatter strip blanked several body reads (re-read with a single strip), and
  `argument-hint` looked like a gap until counted (20/20). Neither survives into the tables.

## Round shape when PORT-002 starts

1. Refresh `origin/main`; one branch per slice (`feat/port-002-<skill>`), slice 1 = `runbook`.
2. Re-clone the donor at `2a04d357` (commands above) and read only that slice's source files.
3. PORT-001's three blind passes (import value, donor assumption, structure) over those files,
   frozen before any comparison with our artifact; then adaptation notes as the implementation
   spec, using the scrub lists above as the starting point.
4. Grafts land capped inside the owning skill — no new skill, no new mechanism; the "verified
   skip" twins stay byte-unchanged; contribute-back candidates are listed, never acted on.
5. Gates: T0 on every edit, `generate_platform_adapters.py --write` after each canonical edit,
   T1 before the PR; a description edit — none planned — owes the overlapping routing cluster
   before and after.
6. Provenance twice: `adapted from latent-sre/save-toolkit@2a04d357 (MIT)` in the commit, and
   `THIRD_PARTY_NOTICES.md`'s existing `latent-sre/sre-agents` entry extended with the new
   reviewed commit and the renamed repository, not a second entry.
