# Roster expansion design — 2026-07-27

> **Status: historical source design, reconciled 2026-07-28.** The detailed component contracts
> and operator-adjudicated constraints below are preserved as design evidence. They are not a live
> implementation queue. Current role conclusions live in the
> [`fleet role-expansion decision`](../../decisions/2026-07-28-fleet-role-expansion.md), and every
> surviving task is named in the [`fleet roadmap`](../../fleet-roadmap.md).

**Question:** which of the eleven brainstormed candidates earn a place in the fleet, at what shape
(agent → skill → reference → convention → drop), and in what order behind the queued Round 1
(powershell/code-craft + lab-audit checks split + three behavioral contracts) and Round 2
(superpowers systematic-debugging → root-cause mining)?

**Method:** every candidate was designed against the existing roster (8 agents, 17 skills read in
full or frontmatter) and against its sibling candidates, under AGENTS.md's validator constraints and
the guard's own docstring. Frontmatter facts below come from the declared single source of truth,
`skills/prompt-craft/references/claude-code-frontmatter.md` — not memory. Routing posture per the
session's operating state: no valid fleet-wide baseline exists; every description change here names
its touched-cluster before/after anchor, because unmeasured overlap is the fleet's named sin.

**Verdict in one line:** two agents (test-engineer, lab-inspector), three skills (security-audit,
release, porting-method), two references (llm-cost, profiling), and four body-level additions —
everything else downgraded or deferred, nothing on the slate revisits a locked NO.

---

## Part 0 — The gap map this delta fills

| Gap today | Consequence today | Filled by |
|---|---|---|
| No component authors tests for code it didn't write | "write tests for X" lands on the builder whose blind spots produced the gap; reviewer findings on test adequacy have no independent fixer | test-engineer |
| Read-only lab sweeps are cooperative, not enforced — `skills/lab-audit/SKILL.md:12` admits it | An audit that mutates is indistinguishable from one that didn't, until it matters | lab-inspector |
| Nobody owns adversary-eyes on the *running* lab (code-reviewer owns code; lab-audit's Exposure row is hygiene-thin) | "what could an attacker reach" has no home; vuln triage never feeds upgrade priorities | security-audit |
| Nobody owns version/changelog/tag/publish discipline; this repo is itself a versioned plugin | Releases are improvised; release rollback conflated with deploy rollback | release |
| The cross-fleet import method lives only in session memory, with Round 2 queued to need it | The proven 4-pass method gets re-derived or skipped per round | porting-method |

---

## Part 1 — Recommended components

### 1.1 `test-engineer` — agent (Round 5)

**Remit.** Authors the tests a codebase is missing, from a context independent of whoever wrote the
code: characterization tests before a refactor (pin current behavior so the refactor can prove
itself), regression tests that pin a fixed bug, edge and property cases for critical paths;
coverage-gap hunting with evidence (the unexercised path *and* the input that walks it — a
percentage without a walkable input is not a finding); and test-suite health audits (flaky, slow,
over-mocked, assertion-free). It completes the fleet's generate→evaluate loop: today
`code-reviewer` can find "these tests assert nothing" but cannot write the fix, so the finding
routes back to the same builder whose assumptions produced the gap. An independent test author is
the missing third corner — builder builds, test-engineer pins, reviewer judges both.

**The known weakness, addressed head-on.** Its tool list is identical to `sde-fullstack` — the
runtime offers no path-scoped write grants (scoped specifiers on `tools:` are inert per the
frontmatter reference), so no tool boundary can split "test files" from "source files". The slot is
therefore earned on remit and independence value alone, exactly as `principal-engineer` /
`distinguished-architect` earn theirs as an altitude pair with near-identical tools, measured by the
`ladder` cluster. The test-file-only mandate is a **cooperative boundary carried in the body and
stated as such** (the `principal-engineer` Write-grant precedent, named in the guard's own comments)
— plus a behavioral-eval contract so the promise is measured, not assumed: *a bug surfaced by a
characterization test is reported in the packet, never fixed in place*. Silent failure of that
promise would be a builder wearing a tester's name, which is why it joins the behavioral suite
alongside the three seeded contracts.

**Draft description** (~700 chars — improves the session draft by adding the independence clause,
which is routing-relevant because it is the *reason* a caller picks this over the builder, and the
evidence phrasing for coverage gaps):

> Authors the tests a codebase is missing, independently of whoever wrote the code —
> characterization tests before a refactor, regression tests that pin a fixed bug, edge and
> property cases for critical paths — hunts coverage gaps with evidence (the unexercised path and
> the input that walks it), and audits test-suite health: flaky, slow, over-mocked, asserting
> nothing. Use for "write tests for X", "pin this behavior before I change it", "what's untested
> here", or "our suite is flaky/slow". Builds and runs tests only: for the feature itself use
> sde-agents:sde-fullstack; for judging a diff's test coverage use sde-agents:code-reviewer; for a
> failing test whose cause is unknown use sde-agents:root-cause.

TDD-the-method deliberately has no route line: it stays with builders via `code-craft`
(`references/tdd.md`), and naming it would invite "do TDD" requests to land on a non-builder.

**Frontmatter:**

```yaml
name: test-engineer
tools: Glob, Grep, Read, Bash, Write, Edit, WebFetch, WebSearch
model: inherit
skills:
  - code-craft
```

- Tools match `sde-fullstack` deliberately (see weakness above); web tools stay because pinning
  framework behavior in a test without checking the framework's documented semantics manufactures
  confident wrong tests — the Pester Discovery/Run class of trap is doc-verifiable, not guessable.
- `code-craft` preload is legal (not `disable-model-invocation`) and earns its ~44 lines: tests are
  this agent's whole job, so the tdd/safe-refactor reference routing is always live, not
  predicate-rare.
- **Guard implications: none.** Holds Bash *with* write tools, so `GUARDED_AGENT_NAMES` does not
  apply and the validator will not compel registration.
- **Packet:** `## Review packet` in the sde-fullstack shape (Changed / Assumptions / Verified /
  Not verified / Check first) plus one required slot — **Found, not fixed**: defects its tests
  surfaced in the code under test, reported for the caller to route. Canonical
  `[verified]/[sourced]/[unverified]` stems copied verbatim from an existing agent per AGENTS.md.
- **Model:** `inherit`, the fleet's uniform choice; escalate a tier only on an observed reasoning
  gap, never as the first response to a miss.

**Eval seeds — NEW cluster `test-work.json`**, members `[test-engineer, sde-fullstack,
code-reviewer, root-cause]` (members legitimately appear in multiple clusters — root-cause and
code-reviewer already sit in `investigation`):

- `pos-characterize-before-refactor`: "I'm about to restructure the billing module. Pin its current
  behavior with characterization tests first so I can prove the refactor changes nothing." →
  test-engineer.
- `pos-coverage-gaps`: "What's untested in src/auth? Find the unexercised paths and write the tests
  that would catch a regression there." → test-engineer.
- `pos-suite-health`: "Our suite takes 20 minutes and three tests fail randomly. Audit it — flaky,
  slow, over-mocked — and tell me what to fix first." → test-engineer.
- `neg-feature-with-tests` (**narrowed negative** — the declared-exemption mechanism from
  evals/README.md, second use in the tree): "Add rate limiting to the API, with tests." →
  `expect_not_fires: [test-engineer]`; sibling sde-fullstack legitimately fires. This is the
  tightest seam in the cluster and the exact over-trigger that would erode the builder boundary.
- `neg-run-the-suite`: "Run the test suite and tell me whether it passes." → no member fires
  (trivial ask; proportionality doctrine — heavy components must not fire on small asks).
- `neg-ci-tests`: "Make CI run the tests on every push to main." → no member fires (ci-actions
  vocabulary decoy).

**Does NOT own:** the code under test — it writes and edits test files and fixtures only; a bug its
tests surface is reported in the packet, never fixed in place.

### 1.2 `lab-inspector` — guarded read-only agent (Round 4)

**Remit.** The enforcement shell for lab inspection: a read-only agent whose Bash sits behind the
plugin's PreToolUse allowlist guard, which works the two audit checklists (`lab-audit` hygiene,
`security-audit` adversary-eyes) and serves as a safe evidence-gatherer on a live system — including
during incidents, where it can look without any possibility of "helpfully" touching. It closes
lab-audit's own admitted gap (`skills/lab-audit/SKILL.md:12`: the reviewer's guard "keys on guarded
*agent* identities", so skill-level read-only-ness is "cooperative, not enforced"). The agent owns
**no checklist content** — the skills own the checks; the agent owns the enforced posture and the
evidence discipline.

**Load-bearing tool decision: no web tools.** An inspector that reads the lab's most secret-dense
surfaces (env files, logs, configs) and can also GET arbitrary URLs assembles the lethal trifecta —
untrusted content (fetched pages, log lines), private data, and an exfiltration channel — inside one
context. WebFetch has no per-agent URL scoping in this runtime, so the leg is cut structurally:
**the inspector gets no WebFetch/WebSearch, and `security-audit`'s vulnerability step hands the
version inventory back to the caller to spawn `sde-agents:researcher` for the advisory pass.** The
split is clean in both directions — inspector sees the lab and no web; researcher sees the web and
no lab (no Bash, no Write). Cost accepted: HTTP health probes and monitoring-stack queries are not
in the inspector's own reach; they land in the coverage denominator as "couldn't run" rows, which
lab-audit's output convention already requires.

**Reach is honestly narrower than the unguarded skill.** No `ssh` (an interpreter — vetting a
command *across* the ssh quoting boundary is exactly the "shell constructs we refuse to reason
about" class the guard's docstring forswears) and no `curl` (its write surface — `-X POST`, `-d`,
`-T` — cannot be bounded by a flag list the guard could defend). So the inspector inspects what the
local host and the lab repo expose read-only; remote hosts appear via their configs in the repo and
otherwise land in the denominator. Both invocation paths deliberately remain: `/sde-agents:lab-audit`
inline in the main session keeps full reach under the user's own eyes and permission prompts
(cooperative); spawning `lab-inspector` trades reach for enforcement. The skill bodies state this
duality; neither path deprecates the other.

**Draft description** (~600 chars):

> Guard-enforced read-only inspector of the running home lab — works the sde-agents:lab-audit
> hygiene sweep and the sde-agents:security-audit adversary sweep, and gathers evidence on a live
> system, with no write tools and a command allowlist behind its Bash. Use for "audit my lab", "is
> anything exposed", "security-check my setup", a scheduled sweep, or safe evidence-gathering while
> something is being fixed. Observes and reports only — every fix and all change authority stay
> with sde-agents:homelab-platform; a live outage needing mitigation is sde-agents:lab-incident
> under that agent; code and diffs are sde-agents:code-reviewer.

**Frontmatter:**

```yaml
name: lab-inspector
tools: Glob, Grep, Read, Bash
model: inherit
skills:
  - lab-audit
  - security-audit
```

- Mirrors `code-reviewer`'s proven guarded shape exactly. Both preloads are legal (neither skill
  sets `disable-model-invocation`; both resolve to `skills/<name>/SKILL.md`), and preloading beats a
  `Skill` grant per the frontmatter reference. After Round 1's split, lab-audit's check detail lives
  in `references/checks.md`, so the preload cost is the small SKILL.md router, not the full check
  text — the JIT shape holding.
- **Guard implications — the round's real work.** Bash with no write tool means the validator
  *compels* `GUARDED_AGENT_NAMES` registration; `scripts/probe_plugin.py` is then owed (it proves
  the guard fires for the guarded agents *and only them*). The allowlist grows by readers only —
  candidate set in Part 3, each entry with its hazard note, landed with per-entry tests per the
  guard playbook.
- **Packet:** `## Output format` — the active checklist's output shape (coverage denominator first,
  `[P0]`–`[P3]` with command+output evidence, top-three) plus the **findings ledger as output
  convention** established by Round 1: the inspector cannot write the ledger file (no write tools —
  the same reason the skill couldn't own one), so the ledger rows are returned in the final message
  for the caller to persist. Canonical evidence-label stems verbatim.
- **Model:** `inherit`.

**Eval seeds — extend `homelab-ops.json`** (member joins; the Round 4 before/after diff on the whole
cluster is the anchor):

- `pos-inspector-audit`: "Audit my home lab — what's wrong with it?" →
  `expect_fires: [lab-inspector, lab-audit]` (either is a correct route; the pair mirrors the
  homelab-platform/service-onboard positives).
- `pos-inspector-evidence`: "While I fix the proxy, have something safe collect the current state —
  ports, container status, recent logs — without touching anything." → lab-inspector.
- **No narrowed negative for outages, deliberately.** The inspector is a legitimate *spawned*
  assistant during incidents, so "X is down" cases can validly show it firing second; a narrowed
  negative would fail correct behavior. The control is the doctrine's other tool: **watch the
  existing lab-incident positives for regression** in the Round 4 before/after — a drop there is the
  over-trigger signal, per "trust negatives and regressions over absolute agent rates".

**Does NOT own:** any checklist content (the skills own the checks) and any change to the lab
(`homelab-platform` owns every apply, at every tier, always).

### 1.3 `security-audit` — skill (Round 3)

**Remit.** The adversary-eyes sweep of the running lab — the intent-driven counterpart to
lab-audit's hygiene sweep. Checks: trust zones and what the reverse proxy *actually* fronts (vs
what it should); authn on every exposed service; management planes (hypervisor consoles, switch
UIs, IPMI, container APIs) reachable from the wrong zone; default or shared credentials; secrets
posture and rotation (via its own reference, below); image/stack vulnerability triage that feeds
`upgrade-campaign` priorities rather than a raw CVE dump; and personal-data governance at home
scale (what holds family data, where it flows, what backs it up off-site). Read-only in the
lab-audit mold: `disallowed-tools: Write, Edit, NotebookEdit`, surveys and reports, fixes route to
`homelab-platform`. Ships in Round 3 with the same honest "cooperative unless run under a guarded
agent" caveat lab-audit carries; Round 4's inspector then closes it for both.

Two rules imported from adjacent components because their absence would be a silent hole: findings
carry an attack path or are downgraded (code-reviewer's rule — a pattern match with no reachable
path is a P2/P3 note); and evidence of *active compromise* stops the sweep and hands to the human
operator with preserve-evidence framing — never clean up, restart, or rebuild.

**Draft description** (~640 chars):

> An adversary-eyes security sweep of the running home lab — trust zones and what the proxy
> actually fronts, authn on every exposed service, management planes reachable from the wrong
> zone, default credentials, secrets posture and rotation, image and stack vulnerabilities triaged
> into sde-agents:upgrade-campaign priorities, and personal-data governance at home scale. Use for
> "security-audit my lab", "what could an attacker reach", "check my exposure", or after standing
> up anything internet-facing. Surveys and reports; fixes route to sde-agents:homelab-platform.
> For code or a diff, sde-agents:code-reviewer's security pass; for hygiene (backups, drift,
> capacity), sde-agents:lab-audit.

**Files:** `SKILL.md` + `references/checks.md` (check rows in the shape Round 1 gives lab-audit,
each row: what to check, the reader commands, what a finding looks like, the one-line fix class) +
`references/secrets.md` (candidate 4, folded — see 2.1). Every reference linked skill-relative or
the orphan check fails it.

**Eval seeds — extend `homelab-ops.json`** (Round 3's single before/after covers this join plus the
homelab-platform description line, per the batch-the-edits posture):

- `pos-attacker-reach`: "If someone got onto my guest wifi, what could they actually reach? Check my
  lab's exposure." → security-audit.
- `pos-default-creds`: "I never changed the admin passwords on half my containers. Security-audit
  the lab and tell me what's actually at risk." → security-audit.
- `neg-harden-app-code`: "Harden the auth middleware in my Flask app against injection." → no
  cluster member fires (builder/backend-craft territory; "harden"/"auth" are the decoy vocabulary).

**Does NOT own:** code and diff security (`code-reviewer`), CI workflow security (`ci-actions`),
or any fix — it owns the sweep of the *running* lab and the evidence-cited finding.

### 1.4 `release` — skill (Round 6)

**Remit.** Version-and-release discipline for a repository: choosing the bump (and saying why),
changelog from commits, tagging, GitHub Releases, branch-protection and required-check
configuration as settings artifacts, artifact publishing, and **release rollback** — yank, retag,
republish — which is distinct from deploy rollback (reverting a running service), which stays with
`homelab-platform`. The fleet-selfish consumer is real and named in the body: this repo is a
versioned plugin with a marketplace manifest, so its release row includes the manifest version
bump, README inventory regen, and the three validator gates. That stays an inline section, not a
reference — it is one paragraph, and a reference nobody's predicate trips is dead knowledge.

**The merge-gate tripwire, honored.** The backlog killed a `merge-gate` skill because its trigger
("is this ready to merge") collided verbatim with `code-reviewer`'s description. This skill's
description therefore never uses merge-verdict vocabulary: branch protection is framed as
*configuration*, and the negative route to `code-reviewer` is explicit. The eval seeds below pin
that boundary so it cannot drift back in.

**Draft description** (~660 chars):

> Version-and-release discipline for a repo — choosing the version bump, changelog from commits,
> tagging, GitHub Releases, branch-protection and required-check configuration, artifact
> publishing, and rolling back a bad release (yank, retag, republish). Use for "cut a release",
> "tag and publish this", "write the changelog", "set up branch protection", or "v1.2.3 is bad,
> pull it". Covers this plugin's own releases (manifest version, marketplace). For authoring or
> hardening the pipeline that runs the release, use sde-agents:ci-actions; for deploying or rolling
> back a running service, use sde-agents:homelab-platform; for judging whether a diff should merge,
> use sde-agents:code-reviewer.

**Eval seeds — NEW small cluster `release-vs-ci.json`**, members `[release, ci-actions]`:

- `pos-cut-release`: "Cut v0.4.0 of this plugin — changelog from the commits since v0.3.2, tag it,
  publish the GitHub Release." → release.
- `pos-release-pipeline`: "Add a workflow that builds and publishes the artifact whenever I push a
  version tag." → ci-actions.
- `neg-deploy-not-release`: "Roll the new Jellyfin version out to the lab." → neither fires
  (homelab-platform's apply).
- `neg-merge-verdict`: "Is this branch ready to merge?" → neither fires (code-reviewer's literal
  trigger — this case is the standing tripwire for the killed merge-gate collision).

**Does NOT own:** merge verdicts (`code-reviewer`), pipeline authoring (`ci-actions`), or applying
anything to a running service (`homelab-platform`).

### 1.5 `porting-method` — skill (Round 6, with a queue-jump option)

**Remit.** Codifies the cross-fleet import method that currently lives only in session memory and
in the worked example of `docs/archive/2026-07/sre-agents-adaptation-backlog.md`'s Method paragraph: multi-pass
blind review (independent quality pass and gap pass, no sight of each other, then adversarial
verification of the union against the actual files); adaptation-notes-as-spec (author natively
from the notes — the notes are the specification, never a copy source); scrub rules (donor voice,
dead platform references, donor agent names, `~/.claude` paths); provenance stamps in commit
messages; and adapt-don't-copy as the standing posture (this fleet's copies are usually the more
evolved descendants — wholesale import regresses). The backlog's per-import compliance checklist
(namespacing, orphan links, canonical stems, validator gates, routing-eval coverage) becomes the
skill's landing gate, so the method and the gate live in one invocable place instead of one dated
document.

**Why a skill and not an AGENTS.md section:** the method must *travel with the fleet* (the sibling
repo pattern means grafts run in more than one working tree), and a skill's description is what
makes "port X from Y" actually trip the method instead of relying on a session noticing one line in
a hundred-line context file. Cost accepted: one description line in every session everywhere the
plugin loads, for a workflow that runs perhaps monthly — the downgrade path (a `docs/` method file
plus one AGENTS.md pointer) is named here so the operator can take it if that cost ever rankles.

**Sequencing note — the queue-jump.** Round 2 (superpowers mining) is this skill's first consumer.
If Round 2 has not started, landing porting-method first means Round 2 exercises the skill instead
of the memory — the cheapest possible behavioral test of the method file. Flagged as operator
question Q1; the default recommendation is to jump it ahead.

**Draft description** (~630 chars):

> The fleet's method for importing components from a donor repo or plugin — multi-pass blind
> review (independent quality and gap passes, then adversarial verification), adaptation-notes-as-
> spec, donor-voice and dead-platform scrub rules, provenance stamps, and adapt-don't-copy
> discipline. Use when mining, porting, grafting, or adapting agents, skills, or references from
> another fleet, plugin, or repo — "port X from Y", "is Z worth importing", "run a mining round".
> For authoring a net-new component from scratch, use sde-agents:prompt-craft; for iterating on a
> landed component against measured gaps, use sde-agents:self-improve-loop.

**Eval seeds — extend `prompt-tooling.json`** (porting-method joins; the shared vocabulary is
"write/create/adapt a skill/agent", which is exactly that cluster's guard):

- `pos-port-skill`: "Port the systematic-debugging skill from the superpowers plugin into our fleet
  — adapt it to house conventions, don't just copy it." → porting-method.
- `pos-mining-round`: "Is anything in the official plugin marketplace worth importing into this
  fleet? Run a mining pass and rank the candidates." → porting-method.
- `neg-mechanical-copy`: "Copy skills/runbook/SKILL.md into my other repo's .claude/skills
  directory." → no member fires (a file operation wearing porting vocabulary; no adjudication, no
  authoring).

**Does NOT own:** authoring quality of the landed file (`prompt-craft` / `prompt-engineer` — every
ported description still routes through the eval-first loop) or post-landing iteration
(`self-improve-loop`). It owns selection, adjudication, scrubbing, and provenance.

### 1.6 Reference-shaped additions (Round 7)

- **`prompt-craft/references/llm-cost.md`** — model-tier selection (fleet-local semantics only —
  the cross-fleet assessment's "never transfer sde tier semantics" is a standing rule), prompt-cache
  behavior and what breaks it, and when a subagent spawn is worth its tokens (the spawn's context
  cost vs the caller's context saved — researcher's twenty-pages-becomes-five-sentences trade,
  stated with numbers). Home is right: prompt-craft already owns `context.md`, `tools.md`,
  `agent-security.md`; cost is the fourth authoring-decision axis. One predicate row in the
  SKILL.md table ("choosing a model tier, budgeting a spawn, or chasing a cost regression") — a
  body edit, no routing surface, no eval owed; the orphan check requires the link.
- **`code-craft/references/profiling.md`** — measure-before-optimizing method: profile first, name
  the hot path with evidence, fix one thing, re-measure; per-language profiler idioms matching the
  languages code-craft carries after Round 1 (Python, Bash, PowerShell, Go). One predicate row
  ("a performance problem or an optimization"). Same body-only, orphan-linked posture.
- **`runbook` continuity flavor** (candidate 10) — extends the existing "know which doc you're
  writing" rule with a third flavor: the **break-glass doc**, audience a non-operator (family,
  future operator): plain language, physical locations, where credentials live (never their
  contents), safe-shutdown and who-to-call. Plus `references/continuity.md`, a filled template in
  the runbook example's mold. **No description edit** — the ask is rare and operator-initiated
  (they will say "runbook" or invoke the slash command), and keeping runbook's trigger surface
  unchanged keeps one variable out of Round 3's homelab-ops diff.
- **`hardware-health` check rows** (candidate 9, landing in Round 4 with the guard) — SMART,
  thermals, UPS rows in lab-audit's `references/checks.md` (they are hygiene, not adversary
  material). They land in the *guard* round because their reader commands (`smartctl -a/-H`,
  `sensors`, `upsc`) are allowlist entries: landing the row and its command permissions together
  keeps the inspector's coverage denominator honest from day one — a check row whose commands the
  guard denies would ship pre-broken.

### 1.7 `homelab-platform` trigger line (candidate 11 — LOCKED shape, Round 3)

One line appended after the description's first sentence, adding the trigger vocabulary the rename
would have bought without the rename's blast radius:

> The fleet's SRE for the lab — the home-lab engineer who keeps it running.

Adds "SRE", "home-lab engineer", "keeps it running" as routable phrasings; ~+80 chars keeps the
description well under 1024. Batched into Round 3's single homelab-ops before/after alongside
security-audit's cluster join, so one run anchors both edits.

---

## Part 2 — Downgrades, deferrals, and standing NOs

### 2.1 `secrets-management` → DOWNGRADED to `security-audit/references/secrets.md`

The candidate's content is already three-quarters owned: CI secrets (`ci-actions`),
secrets-never-in-argv (`sre-tool`'s CLI contract), app-side config-from-environment
(`backend-craft`), never-committed/never-baked (`homelab-platform`'s standards). A standalone skill
would be a fourth owner of one topic — the two-owners-of-one-gate failure the backlog killed
`production-change-gate` for. What is genuinely unowned is lab-scale *posture*: .env sprawl
assessment, encryption at rest (sops/age-class tooling), and rotation-after-incident. That is
audit-shaped, so it homes as a reference under security-audit, where each check row carries its fix
class (the lab-audit convention: finding + one-line fix) and the fix itself routes to
`homelab-platform`. The reference opens with the ownership map above, so the boundary is in the
file that would otherwise erode it. **Verify against the lab repo before authoring** — the
brainstorm says sops/age, but documenting tooling the lab doesn't run would be a reference that
audits a fiction [unverified].

### 2.2 `performance` → SPLIT: profiling recommended (1.6), load-testing/capacity DEFERRED

Profiling has a live consumer class ("why is this script slow" recurs in real sessions) and a
natural home in code-craft's predicate table. Load testing and capacity planning at household scale
have no observed consumer: lab-audit's Capacity row (disk, growth, 80%) plus observability's
SLO/burn-rate content cover what a one-operator lab actually decides. Landing them now would be
authoring knowledge ahead of any predicate that trips it — dead reference weight. Reopen when a
real task needs a load model, and home them then by where the miss occurred (a service's limits →
backend-craft; a lab-wide signal → observability).

### 2.3 `linux` references → DEFERRED with a named trigger

Real knowledge, no clean owner: code-craft owns *authoring* craft (a systemd-debugging reference
there would stretch the skill's stated remit), and agents cannot own references — only skills carry
them. Forcing a home now picks an owner by convenience, and a reference filed under the wrong
predicate is never read, which is indistinguishable from never shipped. Trigger to reopen: the
third time a lab session re-derives systemd/journald/permissions facts, home the reference by where
the misses actually occurred — `lab-incident` if they were diagnostic reads mid-failure,
`code-craft` if they were unit-file authoring. The miss pattern is the routing evidence a guess now
would lack.

### 2.4 Candidate 12 — the locked NOs, restated so this document can't be read as reopening them

No SRE agent (the function exists, distributed across homelab-platform + the ops skills — a second
owner would split one authority). No Linux agent (a platform is not a role; roles route, platforms
inform). No merge of multi-agent-architect + prompt-engineer (an altitude pair, measured by
prompt-tooling — the same justification the ladder pair carries). QA is not "TDD-lover" framing —
test-engineer's description leads with what it *builds*, and TDD-the-method stays with builders.

---

## Part 3 — Overlap adjudications (the seams, settled explicitly)

### 3.1 The inspector / lab-audit / security-audit triangle

**Content lives in skills; enforcement lives in the agent; authority lives in homelab-platform.**

- `lab-audit` = hygiene checklist (is the lab well-kept: backups, monitoring, drift, capacity,
  updates, container hygiene, plus the new hardware rows). Keeps its quick Exposure row — ports vs
  proxy list is hygiene.
- `security-audit` = adversary checklist (can someone get in, move, or take: zones, authn,
  management planes, creds, secrets, vulns, personal data). Owns adversarial *depth* on exposure;
  its checks.md cross-references lab-audit's row in one line, and vice versa, so a drift in either
  is visible in both.
- `lab-inspector` = the shell that works either checklist under enforcement, and the incident
  evidence-gatherer. Owns zero check content — so a new check never raises "which component gets
  it": hygiene row or adversary row, never an agent-body row.
- Fixes, always and only: `homelab-platform`. During incidents the *main session* runs the fan-out
  (homelab-platform mitigates, inspector observes) — homelab-platform holds no Agent tool
  [sourced: agents/homelab-platform.md tools line], so the parallelism is the caller's to
  orchestrate, and the inspector's body says so rather than implying it can be summoned by its
  sibling.

### 3.2 release / ci-actions / homelab-platform

`release` owns the decision and the artifact (what version, what changelog, tag, publish, yank).
`ci-actions` owns the machinery that executes it (the workflow, its pins, its permissions — release
integrity/SBOM stays its line). `homelab-platform` owns anything that touches a running service,
including deploy rollback. Release rollback ends at the artifact registry; the moment a running
service must change, the tier gate owns it. The `neg-merge-verdict` eval case is the standing
tripwire against this skill re-growing toward the killed merge-gate.

### 3.3 secrets / security-audit / backend-craft / ci-actions / sre-tool

One reference, opening with the ownership map: app config-from-env → backend-craft; CI secrets →
ci-actions; argv discipline → sre-tool's CLI contract; lab posture, encryption at rest, rotation →
this reference, audited by security-audit, fixed by homelab-platform. Five owners already existed;
the design adds a map, not a sixth owner.

### 3.4 porting-method / prompt-craft / self-improve-loop

Time-ordered, no shared step: porting-method selects, adjudicates, scrubs, stamps (pre-landing);
prompt-craft/prompt-engineer make the landed file good (authoring, eval-first); self-improve-loop
iterates it against measured gaps (post-landing). Each description names the next hop.

### 3.5 test-engineer / sde-fullstack / code-reviewer / root-cause / code-craft

test-engineer builds tests for code it didn't write; sde-fullstack builds features *with* their
tests (and keeps TDD via code-craft); code-reviewer judges adequacy but writes nothing; root-cause
diagnoses a failing test whose cause is unknown. The narrowed `neg-feature-with-tests` case pins
the builder boundary; the `investigation` cluster already pins the reviewer/diagnosis boundaries.

### 3.6 The guard allowlist expansion (Round 4's enumerated proposal)

One global allowlist for all guarded agents, per the guard's own philosophy (simplicity and
defensibility over granularity; every entry still a reader, so the docstring's guarantee — nothing
outside a short reviewed list of readers ever runs — is preserved). Per-agent allowlists are the
named escalation if a lab reader ever proves too wide for the reviewer; not taken now because they
double the test matrix of the fleet's most safety-critical file for a hypothetical.

Candidate entries, each landing with its own test per the guard playbook — hazard notes are the
review surface, not footnotes [unverified until probed against installed binaries]:

| Entry | Shape | Hazard to gate |
|---|---|---|
| `docker` | verb-gated like `_GIT_READ_VERBS`: `ps`, `inspect`, `images`, `logs`, `stats --no-stream`, `version`, `info`, `port`, `top` | `exec/run/rm/cp` never; `logs -f` and bare `stats` hang a session (deny follow/stream flags) |
| `docker compose` | verb-gated: `ps`, `config`, `images`, `logs`, `ls`, `top` | `up/down/exec/run` never; `logs -f` as above |
| `systemctl` | verb-gated: `status`, `show`, `cat`, `is-active`, `is-enabled`, `list-units`, `list-timers`, `list-unit-files` | `start/stop/restart/edit/daemon-reload` never |
| `journalctl` | allowed with flag denials | `--vacuum-*` deletes logs; `-f` hangs; `--flush/--rotate/--relinquish-var` mutate |
| `ss` | simple reader | none known |
| `ip` | verb-gated: `addr/route/link/neigh` + explicit `show` only | bare `ip addr` defaults to show but `add/del/set` mutate — require the explicit read verb, deny-by-default like `git reflog` |
| `df`, `free`, `uptime`, `lsblk`, `lscpu`, `id`, `hostname` | simple readers | none known (`du`, `stat`, `ls` already listed) |
| `smartctl` | flag-gated: `-a`, `-H`, `-i`, `-l` | `-t` starts self-tests (device state change); `-s` toggles SMART |
| `sensors`, `upsc` | simple readers | `sensors -s` writes limits — deny the flag |
| `openssl` | verb-gated: `x509`, `verify` (file mode) | `s_client` opens network connections — excluded |
| `dig` | optional, flagged for operator call | a network query; read-only semantics but the first network-touching entry — include only if DNS checks prove needed |

Explicitly refused, with the docstring's own reasons: `ssh` (interpreter across a quoting boundary
the guard refuses to parse), `curl`/`wget` (unboundable write surface), any container `exec`. The
honest boundary stands: `docker logs` and `journalctl` read secret-bearing streams — "a reviewer
that can read files can read secrets" already concedes this class; OS-level least privilege remains
the load-bearing control.

---

## Part 4 — Sequencing

Rounds sized to Round 1's scale (one skill restructure + one reference + one description batch +
eval work). Rounds 3/4 are ordered (content before enforcement; the guard isolated in its own
round because it is the highest-risk edit class in the repo). Round 5 is independent of 3/4 and can
swap forward if the operator wants capability before enforcement.

| Round | Contents | Gates owed |
|---|---|---|
| 1 (queued, approved) | powershell.md + code-craft widening; lab-audit checks split + ledger-as-output; three behavioral contracts | per its own plan |
| 2 (queued) | superpowers systematic-debugging → root-cause mining | per its own plan; consumes porting-method if Q1 jumps it |
| **3** | `security-audit` skill (SKILL + checks.md + secrets.md); homelab-platform trigger line | validator+tests+strict; README inventory; **one homelab-ops before/after** covering both edits; prompt-engineer eval-first pass on the new description |
| **4** | `lab-inspector` agent; guard allowlist expansion (3.6) + `GUARDED_AGENT_NAMES`; hardware-health rows in checks.md; lab-audit/security-audit body paragraphs naming the enforced path | guard tests per entry; **probe_plugin.py re-run** (guard fires for the new agent and only the guarded set); homelab-ops before/after (member join; watch lab-incident positives for regression); inventory |
| **5** | `test-engineer` agent; NEW `test-work` cluster; behavioral contract "found, not fixed" | stub-first routing run (see cheapest test); cluster baseline capture; prompt-engineer pass; inventory |
| **6** | `release` skill + NEW `release-vs-ci` cluster; `porting-method` skill + prompt-tooling extension (unless jumped ahead per Q1) | cluster runs for both; prompt-tooling before/after (member join); inventory |
| **7** | llm-cost.md (prompt-craft), profiling.md (code-craft), runbook continuity flavor + continuity.md | body-only: validator+tests+strict, orphan links; no routing runs owed |

Standing rule for every round: each new or edited description routes through
`sde-agents:prompt-engineer`'s eval-first loop before landing — this document designs the system;
that agent makes each prompt actually work. Every round fills the PR template's conditional-gates
rows it tripped.

Net roster after Round 7: 10 agents, 20 skills — a +2/+3 delta for five named gaps, with four
candidates deliberately kept below component shape.

---

## Part 5 — Open questions for the operator (one round, defaults attached)

1. **porting-method timing.** Jump it ahead of Round 2 so the superpowers mining consumes the skill
   instead of session memory? *Default: yes* — it is self-contained, and Round 2 becomes its free
   behavioral test.
2. **Inspector posture.** Accept the no-web/no-ssh/no-curl trifecta cut, with remote-host and HTTP
   evidence landing in the coverage denominator and advisory lookups split to
   `sde-agents:researcher`? *Default: yes* — enforcement over reach; the unguarded
   `/sde-agents:lab-audit` path remains for full-reach sweeps under your own eyes. (If no: the
   alternative is per-agent allowlists plus a vetted network reader set — roughly double the
   guard-test surface.)
3. **test-engineer confirmation.** Accept +1 agent whose tool scope duplicates sde-fullstack, slot
   earned on remit + independence, with the stub-first routing run as the go/no-go gate? *Default:
   yes, gated* — if the stub's positives can't clear the negatives' zero-fire bar after one
   prompt-engineer iteration, downgrade to a `test-craft` reference row and close the candidate.
4. **Secrets tooling reality.** Is sops/age actually the lab's encryption-at-rest stack, or should
   `references/secrets.md` document something else? *Default: verify against the lab repo while
   authoring; write to what exists, not to the brainstorm.*
5. **`dig` on the allowlist.** First network-touching reader — include? *Default: no* — add it only
   when a sweep's denominator shows DNS checks failing for its absence.

**Adjudicated 2026-07-27 (operator, in-session):** Q1 — yes: porting-method jumps ahead of Round 2,
which now consumes the skill as its first behavioral test. Q2 — yes, posture as designed (the
mechanics were walked through in-session before the call). Q3 — yes, gated on the stub-first
routing run. Q4 and Q5 — defaults adopted (secrets.md written against the lab's actual tooling at
authoring time; `dig` excluded until a denominator row proves the need). No open questions remain.

---

## Design packet

- **Decisions.**
  - Two agents, not five: only test-engineer and lab-inspector clear the bar where a skill's inline
    context genuinely can't do the job (independent context; enforced tool posture) — every other
    candidate is method or knowledge, which skills and references carry more cheaply.
  - Inspector mirrors code-reviewer's guarded shape and cuts the trifecta by tool omission —
    structural beats cooperative for an agent whose whole point is enforcement.
  - Content (skills) landed one round before enforcement (agent + guard), so the fleet is never
    routing to descriptions whose components don't exist, and the guard edit sits alone in the
    highest-scrutiny round.
  - One global guard allowlist, per-agent lists named as the escalation — matching the guard's own
    simplicity doctrine rather than my granularity instinct.
  - secrets downgraded to a reference because four owners already exist; the deliverable is a map,
    not a fifth owner.
  - No runbook description edit for continuity — keeps one variable out of Round 3's homelab-ops
    diff; the flavor is reachable by invocation, which matches how the ask actually arrives.
- **Assumptions.**
  - Round 1 lands as described (checks.md split, ledger-as-output, description widening) — the
    inspector's preload economics and the hardware rows' home depend on it [unverified — state
    received from the operator session].
  - The lab spans multiple hosts and the workstation cannot read them without ssh, making the
    denominator honesty load-bearing rather than cosmetic [unverified].
  - The plugin loads in repos beyond this one, which is what makes porting-method's
    description-cost trade real [unverified].
  - Description drafts fit ≤1024 chars — counted approximately here; the validator is the gate at
    authoring time [unverified].
  - Allowlist hazard notes are from documented flag surfaces, not probes of installed binaries —
    Round 4's per-entry tests are where they become [verified] [unverified].
- **Weakest seam.** The Round 4 guard expansion: a mis-vetted reader arms every guarded agent at
  once, and the failure mode is silent by construction (an allowed command simply runs). Second:
  the test-engineer/sde-fullstack routing boundary, held by nothing but description text and one
  narrowed negative — identical tools mean a misroute has no tool-level backstop.
- **Cheapest test.** Before any body is written: land frontmatter-only stubs of the two agents on a
  branch, run the touched clusters (`test-work` seeds, homelab-ops) at `--runs 3` with `--model`
  pinned, and check the negatives hold at zero-fire and no existing positive regresses — routing is
  the only property a stub can't fake, and it is the property most of this design rests on. For the
  guard: run the Part 3.6 candidate commands under the *current* guard first and capture the
  denials, so Round 4's diff is written against observed behavior, not the table above.

Load-bearing sources for this design: `AGENTS.md` (validator constraints, playbooks);
`skills/prompt-craft/references/claude-code-frontmatter.md` (tool/model/preload facts — the fleet's
declared single source of truth, read before drafting any frontmatter above);
`scripts/readonly-guard.py` docstring and allowlist body (guard growth rules, 42/43 contract);
`evals/README.md` (rates-over-runs, negative-zero-fire, narrowing mechanism, agent under-fire
caveat); `skills/lab-audit/SKILL.md:12` (the cooperative-not-enforced admission);
`docs/archive/2026-07/sre-agents-adaptation-backlog.md` (killed merge-gate precedent, porting method seed, parked
baseline state).
