# Repository guide for coding agents

This repository packages one fleet for Claude Code, Codex, and VS Code: `agents/` and `skills/` are
the only authored source, loaded directly by Claude Code; the other hosts load generated adapters.
Edit canonical files and regenerate — never a generated copy, never a fleet definition resolved
under `~/.claude`: the discovery roots there hold no fleet, and Claude Code's own cached copy of
the plugin is replaced by the next reinstall, so an edit in either never reaches this repository or
the fleet's checks (`README.md` owns the install detail). Every script under `scripts/` states its
contract in its docstring — read it before touching or invoking one.

Where this file paraphrases `README.md`, `docs/engineering-program.md`, or a script's docstring,
the source wins (see "The source wins on drift"). The validator pins the checkable facts
(the `@AGENTS.md` bridge in `CLAUDE.md`, concrete multi-segment repo paths, the model-alias list)
and fails them on drift. This file is written for the LLM session that loads it on every task: when
editing it, lead each rule with its trigger and imperative, state each rule once, compress
rationale to a clause, and cite a file only when it owns something the reader must act on.
Incident narration and provenance stay in the archive or decision record — never here.

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
- **Self-learning — explicit maintainer work.** A fleet retro (`/sde-agents:self-improve-loop`)
  runs only on request. Routine agents carry no Learning form or promotion lifecycle; they route a
  discovery as "Closing a task that surfaced a discovery" below says.

**When reviewing fleet prose, identify the reader or consumer and the decision, action, recovery,
or check that needs each detail.** Preserve those facts and boundaries; remove repetition or link
the owning source when the reader can resolve it at the point of use. A future reader alone does
not justify a field. Preserve machine-consumed contracts or migrate their consumers and checks
together, then verify the result against its consumer or a representative task. Prefer fewer
handoffs and one owned record per fact. `docs/engineering-program.md` owns this reading rule.

## Validate before you push

Validation is tiered: depth matches risk, and each tier reuses the last tier's evidence. A
red check is fixed if trivial, else recorded in `docs/fleet-roadmap.md`.

- **T0 — edit loop** (seconds): `python3 scripts/validate_fleet.py` (byte-compares every
  generated adapter, so no separate `--check` run; `python3 -m fleet validate --json` is the same
  run with rule ids) + the owning test module
  (`python3 -m unittest discover -s tests -p test_<area>.py`) + `ruff check .` **and**
  `ruff format --check fleet` (the lint gate; `pyproject.toml` owns its rule set and the per-file
  ratchet for legacy findings). Run BOTH — CI runs both, and `ruff check` passes on code the
  formatter would rewrite, so running only the first sends a red commit to CI that was green
  locally. CI installs the latest `ruff`, and the formatter's output moves between releases, so
  run the latest locally too (`uvx ruff@latest`); an older local ruff can pass what CI fails.
  After **any** canonical agent or skill edit, regenerate the host adapters with
  `python3 scripts/generate_platform_adapters.py --write` (`--diff` previews it); after adding,
  renaming, or removing a component, also refresh the README inventory with
  `python3 scripts/validate_fleet.py --write-inventory`.
- **T1 — before push/PR**: `python3 -m unittest discover -s tests` +
  `python3 scripts/validate_claude_plugin.py` (`claude plugin validate --strict` on the marketplace
  and the canonical plugin; with no Claude CLI it exits 2 and CI's run supplies the result) +
  `python3 scripts/fleet_doctor.py`. CI reruns the first two, never fleet_doctor (host drift stays
  invisible). Exit 1 failed, 2 not computed (a clean report isn't evidence), 3 warnings. Repair via
  `python3 scripts/install_codex_agents.py --user`; clear warnings before measuring.
- **T2 — merge/weekly** (CI-owned, nothing to run locally): three-OS matrix on push to
  main, weekly, or dispatch — see the matrix comment in
  `.github/workflows/validate.yml`.
- **T3 — release/CLI upgrade** (manual, real API): `scripts/probe_plugin.py` + every routing
  cluster — no affected-only subset. Before a paired routing run, check by hand
  that a stored capture's cluster, cases, evaluator, and plugin bytes are unchanged **and** its
  recorded conditions equal the run you are about to make. The condition list is **the artifact,
  not a list restated here**: `runs_per_case` plus every key of the capture's own `conditions`
  block, minus three exceptions, with `models_observed` holding exactly one model and
  `components_uniform` true on **both** sides — `evals/README.md` owns the exceptions and the
  reasons. Only then is the before-side reusable. The after-side stays fresh.

## Development loop

Load the plugin from the working tree — `/plugin install` runs from a cached copy, which is the
wrong Claude loop when the plugin is what you are editing:

```bash
claude --plugin-dir .
```

The VS Code and Codex local loops are owned by `README.md`'s Install section.
Standalone Codex agent sync — including the exact-match adoption contract — is owned by the
`scripts/install_codex_agents.py` docstring.

Two checks are manual and on demand, deliberately not CI gates (both drive real model sessions):

- `python3 scripts/probe_plugin.py` — proves the fleet *loads*, `${CLAUDE_PLUGIN_ROOT}` expands,
  the guard fires for the guarded agents and only them, and the live-effect gate denies the gated
  agent under suppressed prompts and only it. Owed before every release and after a CLI-caused
  red run of CI's `claude-plugin-contract` job, which floats on the latest CLI: the probe is the
  only runtime proof the current binary still honors the guard's payload contract (owner: the
  `scripts/readonly-guard.py` docstring).
- `python3 scripts/eval_routing.py evals/routing/<cluster>.json --runs 3` — routing evals, owed
  before **and** after any description edit (the description playbook owns the recipe).
  `claude plugin eval` runs the sessions; the fleet computes the verdict from their traces, because
  a native `tool_used` grader counts a dispatch that errored and cannot express a positive's
  agent-or-skill disjunction. Read `evals/README.md` first — it owns the negative-case and
  narrowing semantics, the headless caveat, and why a baseline's routing competition is read from
  `components_observed` rather than from `--clean-room`.

## Change playbooks

**Adding an agent or skill · editing a workflow · changing a validated on-disk record shape ·
retiring a tripwire whose risk is structurally gone** — these fire rarely, so
`docs/fleet-development.md` owns them under "Change playbooks for less frequent work". Read that
section before starting one; the validator holds you to the component contracts either way.

**Setting `model:` on any agent** — it must be an alias (`inherit`, `haiku`, `sonnet`, `opus`,
`fable`). A full model ID is a valid runtime value but banned: it goes stale silently while an
alias follows the model upgrade.

**When adapter generation fails naming a rewrite id, a host projection's count moved** — the
correction it carries is the only thing keeping a Claude-only authority claim out of a host that
cannot honour it, so never regenerate past the message. The failure says which direction:
**landed fewer** means a sentence it anchors on was reworded or removed, so re-anchor it in
`fleet/hosts/table.py` (or delete it, if what it corrected is gone); **landed more** usually means
a new canonical occurrence that needs the same projection, so read each one and raise its
`expect` to the new total.

**Editing a description** (agent or skill) — descriptions drive routing. Run the overlapping
cluster in `evals/routing/` before and after, and diff the rates. The 'before' side may reuse a
stored benchmark only when it passes the T3 reuse check — the list is the T3 one above, and
`evals/README.md` owns it; the 'after' side is always a fresh run. Cross-references to other
fleet members must use the plugin namespace (`sde-agents:code-reviewer`,
`/sde-agents:backend-craft`); a bare backticked name is only for content already in context, such
as a preloaded skill.

**Touching a Claude hook — the read-only guard or the live-effect gate** — read the docstrings in
`scripts/readonly-guard.py` and `scripts/live-effect-gate.py` and the hook section of
`docs/fleet-development.md` first;
then run the tests *and* the probe. **A roster changes in the script, never in `hooks/hooks.json`**:
that file is rendered from `GUARDED_AGENT_NAMES` and `GATED_AGENT_NAMES` by `fleet/hooks.py`, so
edit the constant and regenerate. Changing the shell semantics means editing the template there,
which is a hook change and owes the probe. Non-negotiables: the guard's allowlist grows by adding a
*reader*, never an interpreter (no `python`, `pytest`, `npm`, `make`, no exemption for this repo's
own scripts); the gate's roster grows by adding a *live effect an incident or drill showed
unlisted*, never by exempting one; both resolve their script through `${CLAUDE_PLUGIN_ROOT}` so a
repository under review or operation can never supply it; the guard fails closed for guarded
agents; in `prompt` policy the optional gate falls back to `ask` (or `deny` when prompts are suppressed)
for the gated agent, and both no-op for everyone else; and the 42/43/44/45 exit-code contract
between the scripts and the hook shell strings stays intact — it is how the hook tells a script's
answer from a stand-in interpreter that merely exits 0. An agent is on one roster or neither,
never both. Beyond never porting either hook ("Authority is the host's own control"), keep a
non-Claude host away from them **structurally** — no file at that host's own hook-config path,
which is why `plugins/sde-agents/` has no `hooks/`. A manifest field naming an empty override does
not do it.

**Changing validator behavior** — a rule is a pure function over the snapshot in `fleet/rules/`,
registered with a stable id and a one-sentence why; a vocabulary it judges against lives in
`fleet/policy.toml`, never in the rule. Add a fixture under `tests/fixtures/` that violates
exactly the rule you are adding and pin its rule id in `tests/test_fleet_rules.py` — or, for an
invariant about this repo's real wiring, a mutation test in `tests/test_validate_fleet.py` that
copies the repo and breaks the one link — plus a test that fails without your change. Match the
existing error-message register: each message says what broke *and why it would have failed
silently*.

**Adding a defensive branch to a fleet script** — a crash-recovery, authority, or
input-validation guard lands in the same change as a test that makes it fire; when the trigger is
hard to stage, prove the branch non-vacuous by mutation (remove it and watch the test fail). An
untested guard reads as enforcement while enforcing nothing — the exact silent failure the
validator rules exist to catch, and it will pass every existing check because no check knows the
branch is there. The doc-side twin is equally binding: prose that calls an invariant "validated"
or "enforced" lands with the reader check and its firing test, or it is reworded as writer
behavior — a prose claim of enforcement with no guard behind it survives every check for the
same reason an untested guard does. A diagnostic that names an external authority as the source
of truth compares against a value independently obtained from that authority — captured once and
reused is fine — never against a copy the compared party authored itself.

**Closing a task that surfaced a discovery** — update the existing owned artifact within the
current scope, report the evidence and owner of a remaining gap, or drop the lead with its reason.
Use the explicit maintainer retro only when requested; its deeper routing method lives in
`skills/self-improve-loop/references/discovery-routing.md`. `docs/fleet-roadmap.md` remains the only
task tracker; a GitHub issue adds work only when the roadmap imports it (`docs/README.md` rule 7).

## Opening a pull request

Work reaches the default branch through a topic branch and a merge-commit PR, never a direct
push — every gate here attaches to the PR mechanism, and a direct push bypasses them all silently.
A canonical edit and everything it makes necessary — regenerated adapters, a refreshed README
inventory, a guard-list entry — land in the same commit, keeping every commit validator-green for
bisect and revert (writer discipline, not an enforced gate: CI validates the PR head, not each
commit).

Obtain one independent review by default. Add a second for changes to authority or security
boundaries, broad refactors, or unresolved material disagreement. Record each review's commit
and scope; disposition every comment as applied or declined with its reason.

After an edit, inspect the delta from the reviewed commit. Material changes require fresh,
focused independent review of affected behavior and interfaces; unchanged scope retains its
earlier evidence. Record non-material final deltas and why they need no additional review.
Never describe an earlier review as having examined later bytes.

Cap new broad review rounds: static reviews at two for prose-behavior changes (agent or skill
text) and three for other fleet prose; PR reviews at three. A cap bounds repeated broad review and
speculative redesign, never focused checks or corrections of demonstrated in-scope defects — make
those, run the affected checks, and get focused review when needed under existing authorization.
Stop an oscillating correction loop or repeated failures that bring no new evidence; keep the
unresolved defect on record and report it. Close a prose change with a behavioral instrument or
executed verification. Exhausting a review budget never makes a material defect merge-safe;
another broad round beyond a cap, or material scope expansion, requires an explicit operator
ruling.

`CONTRIBUTING.md` owns the procedure and is read before opening or updating a PR: branch naming,
the pull-request template and its conditional gates, and supported reviewer triggers, with operator
handoff when the host cannot request a pass.

## Hard rules with no playbook exceptions

- **Keep isolated hooks dependency-free.** `hooks/hooks.json` launches `scripts/readonly-guard.py`
  and `scripts/live-effect-gate.py` with `python -I -S`; keep their imports in the standard library,
  and never import `fleet/` from either. A missing dependency makes the read-only guard deny and
  the live-effect gate ask or deny every scoped Bash call. This runtime constraint does not impose
  a dependency ban on other tooling: `pyproject.toml`'s dev group is tooling for the maintainer
  loop, and `fleet/` itself stays standard-library so it can never become a hook import.
- **Never hand-edit generated output.** The generated trees are `.github/agents/`,
  `.github/skills/`, `.codex/agents/`, and `plugins/sde-agents/skills/`, plus `hooks/hooks.json`
  (rendered from the hook rosters; the hook playbook owns roster edits). Edit the canonical file or
  the generator, because byte-drift validation erases anything else. Adding a tree edits
  `generate_platform_adapters.py`'s `GENERATED_ROOTS`; retiring one **moves** it to
  `RETIRED_GENERATED_ROOTS`, because only a still-declared root makes `--write` delete the obsolete
  copies instead of leaving a second plausible fleet. A generated file that is **not** the whole
  contents of its directory goes in `GENERATED_FILES` instead, which gives it the same byte checks
  without handing `--write` a directory it would clear.
- **One parser per fact.** Frontmatter, `tools:` values, and namespaced references come from
  `fleet/frontmatter.py` and `fleet/references.py`, re-exported by `scripts/fleet_records.py`;
  the validator judges one `fleet/snapshot.py` snapshot of the tree, loaded once. Extend the
  records or the snapshot to read a new fact. A second parser re-derives the bugs this one already
  fixed, and lets two reports about the same tree disagree with nothing able to arbitrate them.
  The same rule covers every primitive in `fleet/` (link checks, the subprocess runner, stream
  decoding, digests, the exit ladder, the host prose projections and the Codex TOML emitter): an
  instrument imports the kernel's copy, never keeps its own.
- **Authority is the host's own control, never prose.** Claude's guard, VS Code's omitted
  `execute`, and Codex's `sandbox_mode` are distinct controls; use the target host's. Never port a
  Claude hook — another host's `PreToolUse` payload lacks the active-agent identity it scopes on —
  and never reference `workflows/` from another host, where no runtime exists and the reference
  fails silently.
- **Never put `hooks:`, `mcpServers:`, or `permissionMode:` in a plugin agent's frontmatter.**
  Claude Code silently ignores all three there, so a guard declared in frontmatter is armor that
  is not — worse than none, because nobody checks it. They belong at the plugin level, where
  `hooks/hooks.json`, `.mcp.json`, and `plugin.json` are read normally. The validator rejects these
  and every unknown key; the rationale is in `fleet/policy.toml` beside the key tables.
- **Proportionality gates both directions.** No check that re-proves an existing fact; no
  optimization claim without a before/after on one machine; no new mechanism without a task
  consuming it now — with none, record it trigger-bound in `docs/fleet-roadmap.md`. Nothing
  enforces this one: surplus passes every test here, and its cost lands on the next maintainer.
- **One writer per checkout.** Concurrent work gets its own git worktree, and a measurement (an
  eval capture, the probe, the test suite) runs only against a tree nothing else is writing,
  because a benchmark on a moving tree never announces itself. The parallel runner is sanctioned —
  its workers assert against isolated copies (`tests/support.py`) — but some adapter tests write to
  the live checkout, so the suite obeys the rule too.
- **Read a revision as bytes, never a working tree standing in for it.** `git show <rev>:<path>`.
  HEAD identity is not byte identity, and `git status` misses untracked-but-ignored paths and
  assume-unchanged or skip-worktree entries. Record that a read was tree-based, so a later reader
  knows which guarantee it carries.
- **Name commits for the reader.** Use the plain-English commit title by default in human-facing
  updates and summaries. Include an unambiguous short object ID only when an exact revision matters
  — for example, in a review packet, evidence-bound handoff, history claim, or permalink. Resolve it
  in the named repository (`git rev-parse --short=12 <rev>`); an ambiguous ID is not evidence.
  File and image digests are cryptographic values, not commit IDs; retain full values in machine
  evidence and omit them from routine human-facing reports.
- **Keep workflow `permissions:` at `contents: read`.** Workflows reference third-party GitHub
  Actions by major version tag, an accepted mutable-upstream risk (owner:
  `docs/decisions/2026-09-23-float-toolchain-versions.md`), so a moved tag must never be able to
  write with the job token.
- **The source wins on drift.** Fix the paraphrase, not its owner; fix a real defect at the source
  and re-propagate it. The ownership list is in `docs/fleet-development.md` under "Working on the
  fleet itself".

## Style

- Wrap new or edited Markdown prose at roughly 100 columns where practical; leave untouched legacy
  lines as they are.
- Comments in the scripts explain *why* an invariant exists, not what the next line does — match
  that register when editing them.
- Descriptions lead with capability, then triggers, then negative routing.
