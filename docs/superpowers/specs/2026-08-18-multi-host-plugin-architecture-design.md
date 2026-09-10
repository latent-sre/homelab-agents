# Retire three dead lanes

- Date: 2026-08-18
- Status: Implemented 2026-08-18 on `chore/retire-dead-host-lanes`
- Evidence: `docs/archive/2026-08/vscode-discovery-investigation-2026-08-18.md` (retired to Git history)
- Amends: `docs/decisions/2026-07-30-multi-platform-packaging.md` (host table, Copilot lane)

## Scope

Three retirements, agreed 2026-08-18. Nothing else changes.

1. The Codex `/import` staging lane (`.claude/agents/`)
2. The Copilot **CLI** lane (root `plugin.json`, `hooks/copilot-hooks.json`)
3. The stray empty `.codex-plugin/` at the repository root

**The VS Code lane is kept.** It is served by workspace discovery from `.github/agents`, which is
generated independently of everything retired here — see "VS Code is unaffected" below.

## R1 — Delete the Codex `/import` staging lane

`.claude/agents/` holds 11 generated Markdown profiles whose only purpose was a one-time Codex
`/import` migration. `install_codex_agents.py` already documents that `/import` "skips existing
destinations, so it is not an update mechanism"; `.codex/agents` is the real Codex lane.

Meanwhile `.claude/agents/` **is** Claude Code's project-agent path and **is** a VS Code agent-discovery
path. It is why Claude offers 22 agents for 11 roles with `cwd` set to this repository, and why VS Code
does the same. The staging copies are also strictly worse for both readers: they carry Codex-specific
prose ("in Codex, select skills with the skill picker") that the canonical `agents/*.md` do not.

Call sites:

| File | What | Action |
|---|---|---|
| `generate_platform_adapters.py:41` | `CLAUDE_IMPORT_AGENTS` constant | delete |
| `generate_platform_adapters.py:48` | its `GENERATED_ROOTS` entry | delete |
| `generate_platform_adapters.py:869` | `render_codex_import_agent()` | delete |
| `generate_platform_adapters.py:1288-1289` | output emission | delete |
| `generate_platform_adapters.py:14` | docstring line describing the staging lane | delete |
| **`validate_fleet.py:2029-2035`** | **`GENERATED_ADAPTER_TREES`** — a *second* list of the same generated trees, consumed only at `:2047` and **covered by no test** | drop `.claude/agents` |
| `install_codex_agents.py:3-8` | docstring: the `/import` sentence, **and** the "The repository *therefore* keeps…" sentence that depends on it | rewrite both |
| `tests/…:292` | `test_write_replaces_claude_import_agents_without_touching_claude_siblings` | delete test |
| `tests/…:428` | `test_codex_import_adapters_preserve_source_authority_and_toml_contract` | delete test |
| `tests/…:392` | `test_preloaded_claude_skills_become_explicit_host_requirements` | drop one path |
| `tests/…:418-426` | `test_codex_sandbox_mode_tracks_canonical_write_authority` | drop `import_fields` block |
| `tests/…:516` | `test_handoff_owner_reference_is_translated_for_generated_hosts` | drop one path |
| `tests/…:528` | `test_host_agent_adapters_have_no_claude_runtime_references` | drop one glob |

(`tests/…` is `tests/test_platform_adapters.py`.) Then delete the 11 tracked files under
`.claude/agents/`.

**Leave alone — a true statement that only looks related:** `generate_platform_adapters.py:684` contains
a regex matching ``` `.claude/agents/*.md` in a project, `agents/*.md` in a plugin ```. That is
`multi-agent-architect` prose describing where agents live in Claude Code *generally*, rewritten for the
Codex host. It is correct and unrelated to this staging directory.

**Note the duplicate fact.** `GENERATED_ROOTS` (generator) and `GENERATED_ADAPTER_TREES` (validator) are
two hand-maintained lists of the same set, in different files, which must be edited together. That is
the "one parser per fact" smell the repo bans elsewhere; consolidating them is out of scope here but
belongs in `docs/fleet-roadmap.md`.

*Effect: Claude 22 agents → 11. VS Code 22 agents → 11.*

## R2 — Delete the Copilot CLI lane

Copilot CLI is dropped as a target. Remove root `plugin.json`, `hooks/copilot-hooks.json`, and the
`COPILOT_COMPONENTS` block that emits the manifest.

**This is not a clean two-file deletion.** The root `plugin.json` is also the source of the plugin
*name* for four consumers that have nothing to do with Copilot. Each repoints to
`.claude-plugin/plugin.json`, which carries the same `"name": "sde-agents"`:

| Site | Consequence if not repointed |
|---|---|
| `tests/test_fleet_records.py:19` | module-level read — **ImportError**, the whole module fails |
| `tests/test_capability_graph.py:726` | in-test read — that test fails |
| `scripts/capability_graph.py:571` | takes its refusal path; emits a blank topology |
| `scripts/eval_routing.py:91` | `PLUGIN_RUNTIME_FILES` entry — part of the benchmark hash identity |

Also: `generate_platform_adapters.py:1435` (`copilot_path = root / "plugin.json"`) and `:1457-1462` (the
`COPILOT_COMPONENTS` parity loop in `validate_platform_contracts`), plus two tests:

- **`tests/test_platform_adapters.py:679` — `test_non_claude_plugins_do_not_load_the_claude_guard`.
  This is the test that made the false `AGENTS.md` claim look enforced.** Its Copilot half asserts
  `copilot["hooks"] == "./hooks/copilot-hooks.json"` and that the file's `hooks` object is empty — a
  manifest field VS Code never reads, so the assertion is green and proves nothing about VS Code. Delete
  that half; **keep the Codex half** (`assertNotIn("hooks", codex)` and that
  `plugins/sde-agents/hooks/hooks.json` does not exist), which is a real structural check. Rename the
  test, since after the edit it covers one host, not "non-Claude plugins" generally.
- `tests/test_platform_adapters.py:700` — `test_manifest_identity_and_versions_cannot_drift`
  (lines 703, 705, 712) compares the three manifests; drop the Copilot one.

`scripts/eval_routing.py:91` is a clean removal rather than a repoint: `PLUGIN_RUNTIME_DIRS` at `:90`
already contains `.claude-plugin`, so `.claude-plugin/plugin.json` stays inside the hash set.

**Known side effect:** removing `plugin.json` from `PLUGIN_RUNTIME_FILES` changes the plugin hash, so
stored routing baselines will most likely stop reporting `REUSABLE` and the "before" side of any paired
routing run must be measured fresh. Check `scripts/eval_baseline.py` before assuming otherwise.

**Orphaned by this change, deliberately left in place:** `platforms/copilot/skills/` (20 generated skill
directories) loses its only manifest reference. No host discovers that path, so it is now generated
output nothing reads. It is kept because the agreed scope is these three retirements; retiring or
relocating it is tracked in `docs/fleet-roadmap.md`.

## R3 — Delete the stray `.codex-plugin/`

An empty, untracked `.codex-plugin/` sits at the repository root. Inert today — Codex requires
`.codex-plugin/plugin.json` — but a manifest landing there would make the repository root a Codex
plugin root alongside the intended nested one at `plugins/sde-agents/`.

## VS Code is unaffected

Two different things share the "copilot" name in this repository, and only one is being retired:

- `COPILOT_AGENTS = .github/agents` — a `GENERATED_ROOTS` entry, generated independently of
  `COPILOT_COMPONENTS`. **VS Code discovers this directory with no manifest at all.** It stays.
- `COPILOT_COMPONENTS` — the field block written into the root `plugin.json`. VS Code never reads it:
  the manifest is rejected for lacking a valid `$schema`, after which detection falls to
  `.claude-plugin/plugin.json`.

So after these retirements VS Code still discovers 11 agents from `.github/agents`, and R1 removes the
duplicate 11 it was also picking up from `.claude/agents`.

## Not fixed by this change

- **VS Code still discovers zero skills.** The 20 adapted skills sit in `platforms/copilot/skills/`;
  VS Code's skill-discovery paths are `.agents/skills`, `.github/skills`, `.claude/skills`, none of which
  exist here. Moving them to `.github/skills/` was scoped out.
- **Installing this repository as a VS Code plugin still loads the canonical Claude fleet** — agents,
  skills, and `hooks/hooks.json`. VS Code treats any directory holding `.claude-plugin/plugin.json` as an
  installable plugin and classifies it format 1; Claude Code requires that file at the root, so this
  cannot be closed from inside the repository. The VS Code lane is workspace discovery; installing the
  repository as a plugin is unsupported and `README.md` should say so.

Both belong in `docs/fleet-roadmap.md`.

## Documentation this forces

`AGENTS.md` loads on every task here, so a stale line teaches every future session something false.

1. **`AGENTS.md:210-211` — a false claim, independent of this change.** It states
   `hooks/copilot-hooks.json` "is the deliberately empty override that keeps Copilot and VS Code from
   loading the Claude guard — leave it empty, it is doing its job." The VS Code half is false: VS Code
   reads component overrides from `.claude-plugin/plugin.json`, never from the root `plugin.json` that
   references this file, and therefore falls back to format 1's `hooks/hooks.json` — the guard itself.
   R2 deletes the file and the sentence goes with it. This is the repo's own rule at `AGENTS.md:291`,
   *authority is the host's own control, never prose*, applied to a case where the prose had quietly
   become the only control.
2. **`AGENTS.md:283-285` — generated-tree list.** Drops `.claude/agents/`; becomes `.github/agents/`,
   `.codex/agents/`, `platforms/copilot/skills/`, `plugins/sde-agents/skills/`.
3. **`AGENTS.md:3` — host list.** Drops `GitHub Copilot CLI`.
4. **`AGENTS.md:105` — local-loop pointer.** Drops the Copilot CLI loop; `README.md`'s Install section
   owns the detail and drops it too.
5. **`AGENTS.md:106-107` — `/import` paraphrase.** Follows the `install_codex_agents.py` docstring edit
   in R1, not the reverse: the docstring is the declared owner.
6. **Amend the 2026-07-30 ADR** (third amendment): Copilot lane narrowed to VS Code, `/import` dropped,
   host artifact table updated.

## Verified, and not

Everything below was re-run on 2026-08-18 as a full recheck, not carried over from earlier notes.

**Baseline measured (not assumed):**

```
python scripts/validate_fleet.py            -> "Validated 11 agents and 20 skills"    EXIT=0
python -m unittest ... test_platform_adapters.py -> Ran 29 tests  OK                  EXIT=0
python scripts/run_tests.py                 -> Ran 953 tests / 33 modules  FAILED     EXIT=1
```

**The full suite is red before this change touches anything.** Two errors, both in
`test_eval_behavioral.SessionOutcomeClassificationTest`, both
`OSError: [WinError 1314] A required privilege is not held by the client` from `os.symlink`. Creating
symlinks on Windows needs Developer Mode or elevation; neither test guards for it with a skip, so on an
unprivileged Windows host they error rather than skip. Environment-dependent, pre-existing, unrelated to
these retirements, and **not currently in `docs/fleet-roadmap.md`** — record it there per the
already-red-check rule before starting.

**Verified by command:**

- Every generator line cited (`:14, :41, :48, :869, :1288-1289`) and `validate_fleet.py:2029-2035`.
- `.claude/agents/`: 11 files on disk, 11 tracked in git. Frontmatter is valid and carries
  `name: "code-reviewer"`, so Claude Code does load these as project agents.
- Root `.codex-plugin/`: 0 entries, 0 tracked.
- `hooks/copilot-hooks.json` is exactly `{"version": 1, "hooks": {}}`.
- Root `plugin.json` and `.claude-plugin/plugin.json` both carry `name == "sde-agents"`, so the four
  repointed consumers get an identical value.
- **`.github/agents` generation is independent of the deleted manifest.** `COPILOT_AGENTS` is used at
  `:39`, `:46` (`GENERATED_ROOTS`) and `:1282` (emission); `COPILOT_COMPONENTS` only at `:83` and `:1457`
  (a validation loop). Deleting the latter cannot stop the former. This is what keeps the VS Code lane
  intact.
- All ten `AGENTS.md` line citations, read back individually against a control.
- The R1 test list is **six tests in exactly one module**, proven by a union of two patterns
  (`.claude/agents` literals *and* `CLAUDE_IMPORT`/`codex_import` symbols) — a single-pattern grep missed
  `test_write_replaces_claude_import_agents_without_touching_claude_siblings`, which references the
  constant rather than the path. `test_validate_fleet.py`, `test_fleet_doctor.py` and
  `test_install_codex_agents.py` return zero hits, and each was controlled for existence and size
  (716/489/201 lines; 60/27/10 tests) so the zeros are absences, not a broken detector.

**Not verified:**

- No running VS Code was observed loading this repository. VS Code facts are code-read only; they are
  recorded with their source in the investigation note.
- The eval-baseline invalidation in R2 is predicted from how `PLUGIN_RUNTIME_FILES` feeds the plugin
  hash. Not measured — check `scripts/eval_baseline.py` before relying on a stored "before" side.
- `claude plugin validate . --strict` and `python scripts/fleet_doctor.py` were **not** run in this
  recheck. `fleet_doctor` was reported WARNing on `host.codex.custom-agents` earlier in the session and
  that drift is unresolved.
- The `ImportError` prediction for `tests/test_fleet_records.py` is inferred from the read being at
  module level (column 0, outside any function), not demonstrated by deleting the file.

**Most likely to be wrong:**

1. **Grep-derived inventories.** Two separate passes each missed sites the other caught — six on the
   first pass, and one more on the union pass. Treat the tables as a strong starting point, not a
   closed set, and run the full suite rather than the platform-adapter module alone.
2. **Ordering.** Removing `.claude/agents/` before the generator and validator are updated will trip
   both `repository.generated-adapters` and `GENERATED_ADAPTER_TREES`. Change generator and validator
   first, regenerate, then delete.
3. **`GENERATED_ADAPTER_TREES` has no test.** Editing it has no safety net; a mistake there fails
   silently until some later validator run. Per the repo's own rule, a fixture proving the edited list
   still rejects what it should is owed alongside the change.

## Implementation record, 2026-08-18

Built on `chore/retire-dead-host-lanes`. Gate results at completion:

```
python scripts/generate_platform_adapters.py --write  -> Generated 182 platform adapter files   EXIT=0
python scripts/validate_fleet.py                      -> 11 agents, 20 skills, inventory current EXIT=0
claude plugin validate . --strict                     -> Validation passed                       EXIT=0
python scripts/run_tests.py                           -> 953 tests / 33 modules                  EXIT=1
python scripts/fleet_doctor.py                        -> pass=11 warn=3 fail=0                   EXIT=3
```

`run_tests.py` exits 1 on the **pre-existing** Windows symlink errors in `test_eval_behavioral.py`
only — the same two that were red before any edit (filed as TEST-006). `fleet_doctor` exits 3 on
three warnings, all pre-existing or expected: dirty worktree, the skill-listing budget, and
`host.codex.custom-agents` drift.

### What the spec predicted incorrectly

1. **`GENERATED_ADAPTER_TREES` is not "covered by no test."** It had partial coverage through
   `validate_workflow_host_boundary` tests — but for only one of its four trees. Two tests were added
   in `tests/test_validate_workflows.py`: one pinning the validator tuple against the generator's
   `GENERATED_ROOTS` (the drop case, which the per-tree test cannot catch because it iterates the
   tuple), and one planting a workflow reference in every declared tree. Both were mutation-proven:
   removing `.codex/agents` from the tuple fails the first, and making the scan skip that tree fails
   the second.
2. **Six call sites the spec's tables did not list**, all found by running the gates rather than by
   grep:
   - `scripts/generate_platform_adapters.py` — a `hook_value = copilot.get("hooks")` block validating
     the empty override. This was the *validator* half of the false claim, and it crashed the
     validator with `name 'copilot' is not defined` once the manifest read was removed.
   - `tests/test_support.py` — four sites using `plugin.json` as an arbitrary repo file for
     repo-pool restore tests; repointed to `.claude-plugin/plugin.json`.
   - `tests/test_capability_graph.py` — four synthetic fixtures writing `<root>/plugin.json`, which
     `capability_graph` no longer reads.
   - `tests/test_platform_adapters.py` — `test_manifest_identity_and_versions_cannot_drift` hard-coded
     `* 3` manifests and asserted the Copilot component fields.
   - `scripts/fleet_doctor.py` — a `host.copilot.cli` availability check and its read-only allowlist
     entry, both probing a host no longer targeted.

### Improvements on the specified approach

- **`.claude/agents/` was retired through `RETIRED_GENERATED_ROOTS` rather than deleted by hand.**
  `write_generated_outputs` already `rmtree`s those roots, and `validate_generated_outputs` reports
  one that reappears — so the removal is enforced, not merely performed, matching the existing
  `platforms/portable` precedent.
- **`test_non_claude_plugins_do_not_load_the_claude_guard` was renamed**, not just trimmed. It now
  reads `test_the_codex_plugin_root_cannot_reach_the_claude_guard` and carries a comment recording
  why the deleted half proved nothing: a test whose name claims more than it checks is how the false
  `AGENTS.md` claim survived review.
