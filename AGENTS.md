# Repository guide for coding agents

This repository packages one fleet for Claude Code, Codex, and VS Code: `agents/` and `skills/` are
the only authored source, loaded directly by Claude Code; the other hosts load generated adapters.
Edit canonical files and regenerate — never a generated
copy, never a fleet definition resolved under `~/.claude` (the shipped plugin does not live
there). Every script under `scripts/` states its contract in its docstring — read it before
touching or invoking one.

Where this file paraphrases `README.md` or a script's docstring, the source wins — fix the
paraphrase here, never the source. The validator pins the checkable facts (the `@AGENTS.md`
bridge in `CLAUDE.md`, concrete multi-segment repo paths, the model-alias list) and fails them
on drift. This file is written for the LLM session that loads it on every task: when editing
it, lead each rule with its trigger and imperative, compress rationale to a clause or a
citation, and keep incident narration in its archive or decision record — never here.

## The engineering program

The fleet is one program built on one premise: **a session is stateless.** Whatever it learns,
decides, or verifies dies at exit unless it lands in an artifact — and the next session reads
that artifact with no memory of why it was written, trusting it more than it should. Each strand
below is one engineered consequence; `docs/engineering-program.md` maps each strand to its
mechanisms and checks — read it before touching a discipline.

- **Handoff engineering — artifacts are the only carrier.** A handoff is complete only when the
  receiver can act correctly with nothing but the artifact (briefs, operating records, findings).
- **Loop engineering — convergence across memoryless sessions.** Audits, incidents, campaigns,
  and eval rounds must converge even though every iteration starts amnesiac; written exceptions,
  recurrence-merged rows, and literal status transitions make that possible.
- **Graph engineering — authority is typed edges.** Who may write what, who hands to whom, where
  approval sits: declared per definition, enforced per host, never inferred from prose. Owner:
  `docs/decisions/2026-07-31-ai-graph-engineering.md`.
- **Self-learning — explicit maintainer work.** Invoke `/sde-agents:self-improve-loop` for a
  requested fleet retro. Routine agents preserve useful discoveries in the existing owned
  artifact when authorized, or report the evidence, destination, and owner. They do not emit an
  empty Learning form or start a promotion lifecycle merely to finish a task.

The reading rule for any review of fleet prose: **the reader is the next session, not the
operator's memory.** Apparent ceremony here is usually a strand mechanism. Two questions decide
any trim: who is the real reader, and what consumes the artifact — "only the operator" and
"nothing" means trim it; a future session, script, grader, or guard as consumer means the trim
is a regression. The counterweight: coordination is not free — fewer handoffs over richer ones,
one writer per artifact, structure only at the boundaries that remain.

## Validate before you push

Validation is tiered: depth matches risk, and each tier reuses the last tier's evidence. A
red check is fixed if trivial, else recorded in `docs/fleet-roadmap.md`.

- **T0 — edit loop** (seconds): `python3 scripts/validate_fleet.py` (byte-compares every
  generated adapter, so no separate `--check` run) + the owning test module
  (`python3 -m unittest discover -s tests -p test_<area>.py`); regenerate via
  `generate_platform_adapters.py --write` after canonical edits.
- **T1 — before push/PR**: `python3 -m unittest discover -s tests` + `claude plugin validate . --strict`
  (missing CLI defers to CI) + `python3 scripts/fleet_doctor.py`. CI reruns the first two,
  never fleet_doctor (host drift stays invisible). Exit 1 failed, 2 not computed (a clean
  report isn't evidence), 3 warnings. Repair via
  `python3 scripts/install_codex_agents.py --user`; clear warnings before measuring (issue
  #126).
- **T2 — merge/weekly** (CI-owned, nothing to run locally): three-OS matrix on push to
  main, weekly, or dispatch — see the matrix comment in
  `.github/workflows/validate.yml`.
- **T3 — release/CLI pin bump** (manual, real API): `scripts/probe_plugin.py` + every routing
  cluster — no affected-only subset. Before a paired routing run, check by hand
  that a stored capture's cluster, cases, evaluator, and plugin bytes are unchanged **and** its
  recorded conditions — requested model, clean-room setting, threshold, timeout — equal the run
  you are about to make; only then is the before-side reusable. The after-side stays fresh.

Static review converges or stops: at most two deep-review rounds for prose-behavior changes
(agent/skill text), three for other fleet prose. Divergence signal: criticals land in
sentences the prior fix introduced. Close with a behavioral instrument (a routing round
or executed verification); a round past the cap needs an explicit operator ruling.

After **any** canonical agent or skill edit, regenerate the host adapters:

```bash
python3 scripts/generate_platform_adapters.py --write
```

After adding, renaming, or removing a component, also refresh the README inventory:

```bash
python3 scripts/validate_fleet.py --write-inventory
```

## Development loop

Load the plugin from the working tree — `/plugin install` runs from a cached copy, which is the
wrong Claude loop when the plugin is what you are editing:

```bash
claude --plugin-dir .
```

The VS Code and Codex local loops are owned by `README.md`'s Install section.
Standalone Codex agent sync — including the exact-match adoption contract — is owned by the
`scripts/install_codex_agents.py` docstring.

Three checks are manual and on demand, deliberately not CI gates (all drive real model sessions):

- `python3 scripts/probe_plugin.py` — proves the fleet *loads*, `${CLAUDE_PLUGIN_ROOT}` expands,
  the guard fires for the guarded agents and only them, and the live-effect gate denies the gated
  agent under suppressed prompts and only it. Owed at every CLI pin bump (the pin
  lives in CI's `claude-plugin-contract` job): the probe is the only runtime proof the pinned
  binary still honors the guard's payload contract (owner: the `scripts/readonly-guard.py`
  docstring).
- `python3 scripts/eval_routing.py evals/routing/<cluster>.json --runs 3` — routing evals, owed
  before **and** after any description edit (the description playbook owns the recipe). Read
  `evals/README.md` first — it owns the negative-case and narrowing semantics and the headless
  caveat. The behavioral evaluator that once ran deterministic contract evals alongside it retired
  2026-09-02.

## Change playbooks

**Any edit** — run T0. If you touched text that paraphrases another file,
find the declared owner and fix in the right direction (see "The source wins on drift" below).

**Editing any canonical agent or skill** — run
`python3 scripts/generate_platform_adapters.py --write` after the canonical edit. Generated copies
are consequences, never edit targets. The validator compares every generated byte and rejects
missing, stale, extra, or hand-edited output.

**Editing a description** (agent or skill) — descriptions drive routing. Run the overlapping
cluster in `evals/routing/` before and after, and diff the rates. The 'before' side may be
satisfied by a stored benchmark whose cluster, cases, evaluator, and plugin bytes are unchanged
since capture and whose recorded model, clean-room setting, threshold, and timeout equal the
planned run, checked by hand; the 'after' side is always a fresh run. Cross-references to other fleet
members must use the plugin namespace (`sde-agents:code-reviewer`, `/sde-agents:backend-craft`);
a bare backticked name is only for content already in context, such as a preloaded skill.

**Adding an agent** — the checklist the validator will hold you to:

- kebab-case `name:` equal to the filename; description ≤ 1024 chars, with trigger phrasings and
  negative routing ("Not for X — use `sde-agents:Y`").
- An explicit `tools:` list. Omitting it is not a harmless default — the agent **inherits every
  tool**. No parenthesized specifiers: `Bash(git diff:*)` and `Agent(worker)` are silently ignored
  by the runtime while reading as limits, so the validator rejects them. New built-in tools outside
  the fleet's adopted set must be added to `FLEET_TOOLS`; exact MCP tools go in
  `FLEET_MCP_TOOLS`. Add either deliberately — every entry is authority, and server-wide MCP
  grants are rejected because they silently acquire future tools.
- `model:` must be an alias (`inherit`, `haiku`, `sonnet`, `opus`, `fable`). A full model ID is a
  valid runtime value but banned: it goes stale silently while an alias follows the model upgrade.
- An end-of-task packet section (`## Output format` or a `## … packet` heading). If the body uses
  evidence labels, copy the canonical `[verified]/[sourced]/[unverified]` stems verbatim from an
  existing agent — the validator pins the exact phrasing so the triad cannot drift file by file.
- `skills:` entries must resolve to `skills/<name>/SKILL.md` and must not name a
  `disable-model-invocation` skill — such a skill cannot be preloaded, so listing it configures
  nothing.
- Holding `Bash` with no write tool (`Write`/`Edit`/`NotebookEdit`) makes it a read-only agent, and
  it **must** be added to `GUARDED_AGENT_NAMES` in `scripts/readonly-guard.py` or the validator
  fails: unguarded, its "read-only" is a promise, not a control.
- Regenerate every host adapter and refresh the README inventory; seed or extend a routing cluster
  if the remit overlaps an existing member (overlap is fine — unmeasured overlap is not).

**Adding a skill** — directory name equals `name:`; every path a SKILL.md mentions under
`references/`, `assets/`, or `scripts/` must exist, and every file under `references/` must be
linked from SKILL.md by a **skill-relative** path (an unlinked reference file is dead knowledge
that looks shipped — the orphan check fails it). A skill with side effects sets
`disable-model-invocation: true`, which also removes it from `Skill`-tool reach and from agent
preloading — route to it via a slash command or an agent that works its checklist.
Regenerate afterward: Copilot retains that explicit-invocation frontmatter, while Codex expresses
the same policy through each skill's generated OpenAI agent-policy file.

**Editing a workflow** — files under `workflows/`. The Workflow runtime wraps the body, so a
whole-file `node --check` (or equivalent syntax parse) fails identically on committed and edited
bytes at the top-level `return`; that instrument is invalid here. Offline proof is
`python3 scripts/validate_fleet.py` (the meta contract) plus evaluating the extracted `meta`
export; validator-green is never reported as loadable. A change to workflow-shape bytes is
exercised by at least one live workflow load before the release containing it closes.

**Touching a Claude hook — the read-only guard or the live-effect gate** — read the docstrings in
`scripts/readonly-guard.py` and `scripts/live-effect-gate.py` and the hook section of
`docs/fleet-development.md` first;
then run the tests *and* the probe. Non-negotiables: the guard's allowlist grows by adding a
*reader*, never an interpreter (no `python`, `pytest`, `npm`, `make`, no exemption for this repo's
own scripts); the gate's roster grows by adding a *live effect an incident or drill showed
unlisted*, never by exempting one; both resolve their script through `${CLAUDE_PLUGIN_ROOT}` so a
repository under review or operation can never supply it; the guard fails closed for guarded
agents, the gate falls back to `ask` (and to `deny` when the payload says prompts are suppressed)
for the gated agent, and both no-op for everyone else; and the 42/43/44/45 exit-code contract
between the scripts and the hook shell strings stays intact — it is how the hook tells a script's
answer from a stand-in interpreter that merely exits 0. An agent is on one roster or neither,
never both. Do not port either hook to Codex or VS Code: their `PreToolUse` payload does not
supply the active-agent identity used for scoping. Preserve the host-specific tool or sandbox
controls instead. Keep a non-Claude host away from the hooks **structurally** — no file at that
host's own hook-config path, which is why `plugins/sde-agents/` has no `hooks/`. A manifest field
naming an empty override does not do it
(`docs/superpowers/specs/2026-08-18-multi-host-plugin-architecture-design.md`).

**Changing validator behavior** — add a fixture under `tests/fixtures/` that violates exactly the
rule you are adding — or, for an invariant about this repo's real wiring, a mutation test in
`tests/test_validate_fleet.py` that copies the repo and breaks the one link — plus a test that
fails without your change. Match the existing error-message
register: each message says what broke *and why it would have failed silently*.

**Changing a validated on-disk record shape** — state the migration decision (one-shot,
version-gated, or a permanent compatibility reader with the dual-form cost accepted) and say
what rollback does to a record that already moved. Unstated dual-shape readability is not a
decision.

**Adding a defensive branch to a fleet script** — a crash-recovery, authority, or
input-validation guard lands in the same change as a test that makes it fire; when the trigger is
hard to stage, prove the branch non-vacuous by mutation (remove it and watch the test fail). An
untested guard reads as enforcement while enforcing nothing — the exact silent failure the
validator rules exist to catch, and it will pass every existing check because no check knows the
branch is there. The doc-side twin is equally binding: prose that calls an invariant "validated"
or "enforced" lands with the reader check and its firing test, or it is reworded as writer
behavior — a prose claim of enforcement with no guard behind it survives every check for the
same reason an untested guard does (executed-verification finding, 2026-08-10). A diagnostic
that names an external authority as the source of truth compares against a value independently
obtained from that authority — captured once and reused is fine — never against a copy the
compared party authored itself.

**Retiring a tripwire whose risk is structurally gone** — the symmetric half of the
defensive-branch rule above. A tripwire test names the silent failure it watches for (its
docstring's risk hypothesis); a change that makes that failure impossible *by construction* —
consolidating the second parser a drift test watched, removing the config surface a guard
checked — retires the test in the same change, with the elimination stated in the commit. The
suite is evidence, not a ledger of past fears: a test whose hypothesis can no longer occur
re-proves nothing (the proportionality rule already bans that) while still taxing every edit
that touches its fixtures. The bar is structural impossibility, not "hasn't fired lately" — a
quiet tripwire watching a still-possible failure stays, and when the two readings are arguable
the test stays and the doubt is recorded in the test's docstring, beside the risk hypothesis it
questions.

**Closing a task that surfaced a discovery** — update the existing owned artifact within the
current scope, report the evidence and owner of a remaining gap, or drop the lead with its reason.
Use the explicit maintainer retro only when requested; its deeper routing method lives in
`skills/self-improve-loop/references/discovery-routing.md`. `docs/fleet-roadmap.md` remains the only
task tracker; a GitHub issue adds work only when the roadmap imports it (`docs/README.md` rule 7).

## Opening a pull request

Work reaches the default branch through a topic branch and a merge-commit PR, never a direct
push — every gate in this section attaches to the PR mechanism, and a direct push bypasses them
all silently. Branch names use the expanded conventional form `<type>/<kebab-slug>` (`feat`,
`fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`, `build`), so the branch list reads as a
change inventory. Merge commits keep branch history on the default branch, so a canonical edit
and everything it makes necessary — regenerated adapters, a refreshed README inventory, a
guard-list entry — land in the same commit, keeping every commit validator-green for bisect and
revert (writer discipline, not an enforced gate: CI validates the PR head, not each commit).

`.github/pull_request_template.md` is the shape, and it owns its own detail. Write every line —
commit messages included — in the claim-plus-consequence register the template models: what
changed *and* what it means, because a reviewer can only disagree with a decision they can see.
Fill the conditional-gates rows your change tripped — the table names the situational check each
change type owes. Keep "Deliberately not done" honest and the whole template short.

After opening or updating a PR, inspect the review summary, requests, and reviewed commit before
waiting. Enabled Codex reviews can start automatically on open/ready; an empty GitHub
`reviewRequests` list does not prove none is running. If an owed Codex pass has not started on the
current head, request it within the operator's authorized review budget using `@codex review` or
`@codex security review`, then confirm its start and head. Use each other reviewer's supported
request path; hand off to the operator only when this host cannot make that request. Historical
Copilot API failures do not establish a universal request ban — see the review-gate decision.

Wait for both passes **on the current head** — a review-driven edit mints bytes the cleared
passes never saw, so the last edit owes another wait — and disposition every comment: applied, or
declined with the reason. At most **three** review-driven edit rounds per PR; a later finding is
dispositioned in the thread without new bytes (declined with the reason, or recorded as owed work
in `docs/fleet-roadmap.md`) unless an explicit operator ruling buys one further round, the same
one-round escape as the deep-review bound's round past the cap. The cap bounds edits, never
waits. Provenance: `docs/decisions/2026-08-16-pr-review-gate.md`.

## Hard rules with no playbook exceptions

- **Standard library only.** Fleet Python — validators, generators, installers, guard, tests —
  imports only the Python standard library. Never add a dependency, a requirements file, or an
  install step.
- **Never hand-edit a generated adapter.** The generated trees are `.github/agents/`,
  `.github/skills/`, `.codex/agents/`, and `plugins/sde-agents/skills/`. Edit the
  canonical file or the generator and regenerate — byte-drift validation proves the result. Adding
  or retiring a tree edits `generate_platform_adapters.py`'s `GENERATED_ROOTS`; the validator
  derives its scan targets from that tuple.
- **One parser per fact.** A script that needs frontmatter, `tools:` values, or namespaced
  references builds on the records from `scripts/fleet_records.py`; to read a new fact, extend
  the records. A second parser lets two reports about the same tree disagree with nothing to
  arbitrate them.
- **Authority is the host's own control, never prose.** Claude's guard, VS Code's
  omission of `execute`, and Codex's `sandbox_mode` are distinct controls — express an agent's
  authority with the target host's control. Never port a Claude hook (the payload cannot be
  scoped elsewhere; see the hook playbook) and never reference `workflows/` from another host
  (no runtime exists there, so the reference reads as available and fails silently).
- **Never add `hooks:`, `mcpServers:`, or `permissionMode:` to a plugin agent.** Claude Code
  silently ignores them there — a guard declared in frontmatter looks like armor and is
  nothing. The validator rejects these and every unknown key, because the runtime is not
  guaranteed to fail loudly on a typo.
- **Proportionality gates both directions.** Before adding a check, confirm no existing check
  proves the same fact — reuse its evidence. Before claiming an optimization, measure it
  before/after on the same machine — or ship the change without the claim. Before building a
  new mechanism — abstraction, config surface, component, gate — name the task that consumes it
  now; with none, record it trigger-bound in `docs/fleet-roadmap.md` instead of building it.
- **One writer per checkout.** Concurrent work — a second session, a background job — gets its
  own git worktree, and a measurement (an eval capture, the probe, the test suite) runs only
  against a tree nothing else is writing: a benchmark against a moving tree or an overwritten
  edit never announces itself (learn-001 outcome, 2026-08-02). The parallel test runner is
  sanctioned — its workers assert against isolated copies (`tests/support.py`) — but two
  adapter tests touch the live checkout, so the suite itself obeys the same rule. Read a named
  revision as that revision's bytes (`git show <rev>:<path>`), not a working tree standing in
  for it: HEAD identity is not byte identity, and `git status` does not report every divergence
  (untracked-but-ignored paths; tracked paths with assume-unchanged or skip-worktree). A tree
  read records that it was tree-based so a later reader knows which guarantee it carries.
- **The source wins on drift.** When a deliberate paraphrase disagrees with its owner, fix the
  paraphrase; a defect in the source is fixed at the source and re-propagated to its copies.
  The ownership list lives in `docs/fleet-development.md` under "Working on the fleet itself".

## Style

- Wrap new or edited Markdown prose at roughly 100 columns where practical. Existing files contain
  legacy longer lines, so this is a forward-looking target rather than a current-tree invariant.
- Agent and skill names are kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`).
- Comments in the scripts explain *why* an invariant exists, not what the next line does — match
  that register when editing them. Descriptions lead with capability, then triggers, then negative
  routing.
