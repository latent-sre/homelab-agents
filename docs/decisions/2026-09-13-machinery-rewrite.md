# Rebuild the fleet machinery on one kernel

- Date: 2026-09-13
- Status: **accepted** by the operator on 2026-09-13 ("approved for the code rewrite"), after
  phase 0 merged in PR #187 and both live preconditions were met (the unprivileged probe re-run
  and the native eval pilot, both in `docs/archive/2026-09/`). Phases 1–5 now carry
  implementation authority in the order the phase table states, one PR each.
- **Closed 2026-09-14.** All five phases merged (PRs #187, #188, #189, #190, #191, #193) and
  the lint ratchet reached its amended acceptance, so `MACH-001` left `docs/fleet-roadmap.md`
  under that file's rule that it carries only unfinished work. This record is now the owner of
  what that item held; the two facts it alone carried are preserved below.
- Amendments discharged: phase 4 amended `evals/README.md` and the routing-eval sentence in
  `AGENTS.md` (PR #191); phase 5 amended `docs/fleet-development.md`'s hook section and the
  generated-output and hook playbooks in `AGENTS.md`.

## Context

The machinery is fourteen scripts (9,897 lines) and 513 tests (9,482 lines), all standard
library, grown one incident at a time between 2026-07 and 2026-09. Three audits of the whole
tree on 2026-09-13 (validator, generator and installer, runtime instruments) found the same
shape everywhere: correct policy, carried by primitives that each script re-implemented.

**Duplicated primitives, each with a live divergence.**

| Primitive | Copies | Divergence found |
|---|---|---|
| symlink / reparse-point check | 3 (`eval_routing`, `generate_platform_adapters`, `tests/support`) | one copy defaulted the Windows reparse flag to `0`, which silently disables the junction half on an interpreter lacking the constant |
| subprocess runner | 4 (`probe_plugin`, `probe_hosts`, `fleet_doctor`, `eval_routing` inline) | `probe_hosts` rendered a timed-out stream as the literal text `b'...'` by calling `str()` on the bytes `TimeoutExpired` returns; `eval_routing` had already fixed that case in its own copy |
| stream-json decoder | 4 (`stream_events` plus private loops in `eval_routing` ×2 and `probe_plugin` ×4) | the "content is a string or a list of text parts" flattening was written four times with three different join separators |
| SHA-256 convention | 2 (`eval_routing` canonical JSON with `ensure_ascii=False`; `probe_hosts` with the default) | two identities for one manifest that nothing can arbitrate |
| frontmatter reading | 1 reader in `fleet_records`, its strict companion in `validate_fleet`, its emitter in `generate_platform_adapters` | a fix to one could not be seen from the others |
| copy-exclusion list | 2 (`tests/support`, `probe_plugin`), each saying "kept in step by hand" | they already differed (`__pycache__` vs `node_modules`) |
| `try: from scripts import X / except: import X` | 3 | packaging workaround repeated per file |
| exit-code meaning | 3 | `fleet_doctor` 2 = inconclusive; `eval_routing` 3 = inconclusive and 2 = usage; `probe_hosts` maps `probe_plugin`'s 2 onto its own verdicts |

**Policy compiled into code.** Tool vocabularies, per-role required and forbidden tools, known
frontmatter keys, model aliases, evidence stems, perishable tokens and the two hook rosters are
module constants; the generator's per-host prose rewrites are a 394-line `if name == …` chain
over ten agent names, and only three of its roughly twenty substitutions count their matches.
The rest are silent no-ops when the canonical sentence they target is reworded — and byte-drift
validation cannot see that, because the committed adapter was produced with the same miss
(PR #141 finding, recorded at `generate_platform_adapters.py` beside the one anchored rewrite).

**Messages as API.** Every validator rule returns free-form strings and the tests assert
substrings of them, so a reworded diagnostic is a test failure and no consumer can filter by
rule, path, or severity. Files are parsed up to four times per run because no rule shares a
loaded snapshot.

**Contract drift against the platform, found while checking the design.** All four facts were
`[sourced]` from code.claude.com on 2026-09-13; facts 2 and 4 were then `[verified]` the same
day and the pins moved ([pin refresh evidence](../archive/2026-09/pin-refresh-evidence-2026-09-13.md)):

1. `claude plugin eval` shipped in Claude Code 2.1.269 (2026-09-11) and its documentation now
   lists the grader set, an isolated per-run configuration, `tool_used` graders with
   `input_match` over the tool's JSON input (so an `Agent` spawn naming `subagent_type` is
   gradable), `min: 0` / `max: 0` for a must-not-fire case, `--json` with `schemaVersion: 1`,
   documented exit codes, and `--trust-plugin` for CI. `scripts/eval_routing.py`'s own
   docstring says it "retires when `claude plugin eval` is generally available".
2. The subagent reference now documents `tools: Bash(git diff *)` as an enforced allowlist
   ("This allows only `git diff` and `git log` commands via Bash"). The validator rejects those
   specifiers citing a 2.1.200 probe in which they did nothing, and the guard docstring rests on
   the same probe. Re-probed on 2.1.270 (three runs, both spellings, two permission modes): the
   specifier still restricts nothing. The validator's claim stands; the documentation's does not
   hold under a session that grants Bash.
3. The agent frontmatter reference lists `effort`, `maxTurns`, `memory`, `background`,
   `isolation`, `initialPrompt`, `experimental`, and `disallowedTools`; the skill reference
   lists `when_to_use`, `arguments`, `user-invocable`, `disallowed-tools`, `paths`, `shell`,
   `context`, `agent`, `effort`, `hooks`, `metadata`, `license`, `compatibility`. The validator's
   known-key sets carry no record of which documentation revision they were checked against.
4. `claude plugin validate --json` exists since 2.1.268 and the wrapper still parses console
   text. CI pinned 2.1.219; it now pins 2.1.270, the version that passed both the marketplace and
   the canonical plugin copy under `--strict` and the runtime probe's contract checks.

## Decision

Rebuild the machinery as **one kernel package plus thin instruments**, migrated in phases that
each keep the existing tests green and the generated adapters byte-identical, and **retire the
instrument the platform now owns** rather than rewrite it.

### The kernel: `fleet/`

A top-level, standard-library-only package. Its rules (binding, stated in `fleet/__init__.py`):
records never judgments; the inspected tree is data; skip-never-crash on paid transcripts and
refuse-never-guess on definitions; no dependency, because the hooks that share `scripts/` must
stay importable under `python -I -S` and a kernel with dependencies is a temptation to import
from one.

| Module | Owns | Replaces |
|---|---|---|
| `fleet/fs.py` | link/reparse detection with a non-zero flag fallback; UTF-8 reads that refuse to guess; atomic writes; the shared copy exclusions | the three link checks, two read policies, the installer's atomic write, the two exclusion lists |
| `fleet/proc.py` | one runner: explicit UTF-8, required timeout, timed-out streams decoded, missing binaries as results | four runners |
| `fleet/stream.py` | stream-json readers; `block_text` with a named separator; `correlate_tool_results` — the `tool_use_id` oracle with every result kept; the skill-launch signal | four decoders and five correlation loops |
| `fleet/digest.py` | `sha256_hex`, `sha256_file`, length-framed multi-part digests | two conventions |
| `fleet/diagnostics.py` | the exit ladder 0 / 1 fail / 2 not computed / 3 warn, ordered by how definite the answer is | three ladders |
| `fleet/frontmatter.py` | the dialect: reader, strict scalar check, emitter, in one file | reader in `fleet_records`, check in `validate_fleet`, emitter in the generator |

Phase 1 adds `fleet/records.py` (typed `Agent`, `Skill`, `Plugin`, `Hook` loaded once),
`fleet/policy.toml` read by `tomllib` (the vocabularies and rosters, each stamped with the
documentation revision it was checked against), `fleet/findings.py` (a `Finding` with rule id,
severity, path, line, message, and the "why it would fail silently" text; renderers for human,
JSON, and GitHub annotations), and `fleet/cli.py` (one `argparse` with subcommands and shared
`--root` / `--json` / `--output` flags). Phase 2 adds `fleet/hosts/` with a declarative rewrite
table where every rewrite states its expected match count and the generator fails on a
mismatch — closing the silent-no-op class wholesale instead of anchoring one rewrite at a time.

### The dialect stays hand-written, with a conforming parser as its tripwire

Running PyYAML beside the dialect over all 80 definitions and adapters found one systematic
divergence and no other: every skill's bare `argument-hint: [..]` is a string to the dialect and
a flow sequence to a conforming parser. Claude Code's own skill reference writes that field
unquoted, so the hosts are the oracle and they are not conforming parsers either. Therefore:
the reader stays the dialect; `pyyaml` enters the **dev** group only; and
`tests/test_fleet_frontmatter.py` pins the one allowed divergence class so a second one fails a
test rather than shipping a component a host silently drops. The generated host copies already
re-serialize every scalar through the emitter, so no host ever sees the bare form.

### Dependency policy

- **Plugin hooks:** none, ever (`AGENTS.md`, hard rules). The hooks do not import `fleet/`.
- **Kernel:** standard library only, for the reason above.
- **Tooling (dev group in `pyproject.toml`, pinned):** `ruff` (lint gate, format gate on
  `fleet/`), `pytest` (runs the unittest suite unchanged, adds `-k` and `--durations` on every
  supported Python), `pyyaml` (tripwire only). `tomli-w` is added in phase 2 when the Codex TOML
  emitter has a consumer; `hypothesis` in phase 3 for property tests over the guard's tokenizer
  and the dialect, where hostile-input fuzzing has the highest value.
- **Not adopted, with the reason:** `pydantic` / `typer` / `rich` (no consumer; the
  proportionality rule), a third-party GitHub Action for `uv` (a required-job action must be
  pinned to a full SHA the operator verifies; CI installs the pins with `pip` instead).

### What retires

`scripts/eval_routing.py` and `scripts/eval_clean_room.py` (1,682 lines, 80 tests) retire in
phase 4 in favour of native `claude plugin eval` cases: one directory per routing case with a
`prompt.md` and `tool_used` graders on `Skill` and `Agent` with `input_match`, negatives as
`min: 0, max: 0, arm: both`. Isolation, runs, concurrency, cost caps, JSON results and exit
codes become the platform's. What the fleet keeps as its own thin layer: a one-shot converter
from `evals/routing/*.json`, a recorder that stores the native `--json` result beside the plugin
digest so the paired before/after discipline survives, and the README's statistical caveats.
Preconditions: the CI pin moves to ≥ 2.1.269 with the probe re-run that every pin bump owes;
one live run confirms `tool_used: Agent` matches a plugin-namespaced `subagent_type`; the
native results directory is git-ignored. Until then the runner stays untouched — deliberately
not even wired onto the kernel, because its evaluator identity hashes only its own two files and
a kernel import would open a provenance hole.

`scripts/readonly-guard.py` and `scripts/live-effect-gate.py` are **not rewritten**. They are
the fleet's security boundary, single-file by contract, and the most-reviewed code in the tree;
the validator will read their rosters through `ast` rather than executing them (phase 1), and
phase 5 generates `hooks/hooks.json` from a template plus those rosters so the two hand-copied
roster blocks the validator currently cross-checks become one source, byte-checked like the
adapters.

## Phases

Each phase is one PR, validator-green at its head, with the oracle that proves it changed
nothing it did not mean to.

| Phase | Lands | Oracle |
|---|---|---|
| **0** (this branch) | `pyproject.toml`; the six kernel modules with 36 tests; every instrument except the retiring runner wired onto them; lint gate with a per-file ratchet for legacy findings; the CI lint step | 549 tests green; adapters byte-identical under `--check`; the divergent probe_hosts timeout path now has a test |
| 1 | `records`, `policy.toml`, `findings`, `cli`; validator rules become small pure functions over one snapshot, registered with an id and a "why"; tests migrate from message substrings to rule ids; hook rosters read by `ast` | every fixture under `tests/fixtures/` and every mutation test keeps its verdict; the message register is preserved |
| 2 | `fleet/hosts/` projections; count-checked rewrite table; `tomli-w` TOML emitter; `--diff` on generate | committed adapters byte-identical; the tests' forbidden-phrase assertions pass |
| 3 | probes and doctor as verbs over `proc`/`stream`/`findings`; `hypothesis` property tests for the guard tokenizer and the dialect; PROBE-006 closed by the runner's timeout result | `probe_plugin --help` still spends nothing; the INCONCLUSIVE oracles keep their polarity tests |
| 4 | routing evals migrated to native cases; runner reduced to a thin layer; `evals/README.md` amended | both instruments grade one live batch's identical traces and agree on every case verdict (see the phase-4 amendment) |
| 5 | `hooks/hooks.json` generated from rosters | byte-identical hook file; `tests/test_hook_wiring.py` still executes the shell string |

The lint ratchet in `pyproject.toml` lists, per legacy module, exactly the rule codes it
violated on 2026-09-13; a module leaves the table in the phase that migrates it.

## Phase 4 as implemented, and where it departs from the plan above

Three things were settled by measurement during implementation and changed the design. Each is
recorded here because the paragraph above states the opposite.

**The native graders are a tripwire, not the verdict.** The plan handed grading to `tool_used`
graders. Measured on 2026-09-14, `tool_used` counts a call whose input matches its regex whether
or not the spawn SUCCEEDED, so on a positive case a routing regression can hide behind a dispatch
that never landed — the retiring runner deliberately excluded those. And a positive passes when
ANY of its expected destinations fires; all 18 multi-target positives in this repository name both
an agent and a skill, so the disjunction spans two tools and no combination of `tool_used` graders
states it. `fleet/routing.py` therefore keeps the runner's reading and applies it to the harness's
own traces, which `--keep-temp` preserves. Evidence:
`docs/archive/2026-09/native-grader-errored-spawn-2026-09-14.md`.

**`scripts/eval_clean_room.py` does not retire, but `--clean-room` no longer claims isolation.**
A first reading of the child session's `init` event concluded it inherits the operator's whole
component surface, and that was wrong: a controlled comparison the same day showed the surface is
byte-identical with and without the flag, and that the operator's own config-dir skills appear in
neither. The harness sets its own config directory and overrides the variable the flag moves.
What the child does see is sixteen of the CLI's **bundled** skills — `code-review`, `debug`,
`verify` and others — which no config relocation removes.

So the condition is now observed rather than asserted: every benchmark records
`components_observed`, read off each session's own `init` event, and the flag is recorded as
`clean_room_requested`. A flag stored as a condition it does not deliver is the same silent
failure as an untested guard — it reads as isolation to every later comparison while providing
none.

**The evaluator self-binding is dropped.** The runner re-executed itself from checked bytes and
hashed those, which it could do as one file that both ran sessions and graded them. Phase 4 splits
those jobs across imported kernel modules, so binding only the entry script would cover a
shrinking fraction of the code that decides a verdict while still reading like the old guarantee.
`evaluator_identity` now hashes the named files on disk and claims exactly that. The window it no
longer closes — an evaluator source edited between import and record, by the operator running the
measurement — is narrower than the one `frozen_plugin` still closes for the plugin under test,
which is a different party's bytes.

**The oracle is restated.** "One paired run under both instruments" cannot mean two live batches:
routing is stochastic, so two batches disagree case by case from variance alone and the comparison
would measure run-to-run spread rather than the migration. Both instruments instead grade the SAME
runs — one live batch, the retiring runner's reader and scorer applied to identical traces. All 12
`prompt-tooling` case verdicts agreed, on the pass flag, the inconclusive flag, the excluded-run
count and the per-run firing sets. What that oracle cannot exercise, and why, is recorded with it:
`docs/archive/2026-09/routing-migration-oracle-2026-09-14.md`.

### The thirteen runner tests, dispositioned

`fleet/provenance.py` took the retiring runner's identity machinery and 21 of its tests. Thirteen
more drove that machinery through the runner's `main` and could not run until the thin replacement
existed; a fourteenth (the drive-letter test) was deferred separately and belongs with them. Phase
4 did not merge until each was re-homed or deleted with its reason, and this is that disposition —
recorded here because the roadmap item that held it has closed. Two counts in the original were
wrong and are corrected: an early draft claimed all were re-homed (false for four), and gave the
total as thirteen where the groups below enumerate fourteen.

- **Re-homed to `FrozenPluginTest` in `tests/test_fleet_provenance.py`**, driven directly rather
  than through a runner: `test_routing_executes_frozen_plugin_when_source_changes_and_restores`,
  `test_routing_refuses_frozen_plugin_mutated_by_a_session`,
  `test_transient_private_snapshot_mutation_is_a_host_sandbox_boundary`.
- **Re-homed to `MainIntegrationTest` in `tests/test_eval_routing.py`**, which drives `main` with
  the native harness mocked and mutation-proves both guards:
  `test_routing_benchmark_writes_complete_provenance`,
  `test_routing_benchmark_refuses_plugin_content_changed_during_run`,
  `test_a_cluster_edited_mid_batch_into_a_bad_target_exits_two`.
- **Deleted with the machinery the phase-4 amendment drops** (evaluator self-binding):
  `test_clean_room_classifier_is_loaded_once_per_evaluator_process`,
  `test_clean_room_identity_hashes_the_exact_compiled_source_buffer`,
  `test_standalone_runner_is_bound_to_its_actual_compiled_source_buffer`,
  `test_loaded_a_disk_b_identity_records_the_executing_routing_buffer`,
  `test_registry_survives_drive_letter_case_drift`.
- **Deleted because the MECHANISM they drove is now the platform's, not because the checks are
  gone**: `test_routing_batch_aborts_auth_failure_without_writing_benchmark`,
  `test_routing_batch_requires_every_selected_agent_to_be_registered`,
  `test_routing_batch_cancels_queued_runs_after_registration_failure`. An earlier draft said the
  fleet "can no longer observe a failed registration", which is wrong and was caught in review:
  the shipped runner reconstructs the registered surface from each trace and aborts the batch
  through `RegistrationIncomplete` at exit 2, and the authentication abort is likewise retained —
  both exercised by
  `CodexTenthRoundTest.test_an_unregistered_component_aborts_the_batch_rather_than_one_run`,
  `CodexSecondRoundTest.test_an_authentication_failure_aborts_the_batch`, and the
  missing-registration tests in `CodexReviewFindingsTest`, `CodexSecondRoundTest`,
  `CodexFourthRoundTest` and `CodexEighthRoundTest`. What genuinely moved is **queue
  cancellation**: the fleet no longer spawns the sessions, so it has no queue of its own to
  cancel. Its remaining obligation — never writing a benchmark for a measurement that did not
  happen — is covered by
  `test_an_unreadable_native_result_is_a_measurement_failure_not_a_verdict`.

## Rejected alternatives

- **Rewrite everything in one PR.** The suite is the only complete statement of the machinery's
  contract, and a 10,000-line replacement cannot be reviewed against it inside the three-round
  review cap `AGENTS.md` sets. Strangling one primitive at a time keeps every commit
  bisectable.
- **Adopt PyYAML as the reader.** Refuted by measurement: it reads twenty canonical files
  differently from the hosts.
- **Keep per-script copies and add a drift test between them.** A drift test between three
  copies is the parser-per-fact problem restated; one copy is the fix.
- **Fold the hooks into the kernel.** Breaks the `python -I -S` contract and widens the
  security review surface for no control gained.
- **Rewrite the routing runner on the kernel.** The platform now owns the whole job; the
  fleet would be maintaining a second harness with worse isolation than the native one.

## Consequences

- Contributors need the dev group (`uv sync` or the pinned `pip` line in CI) for the lint gate
  and the tripwire; the T0 validator and the full unittest suite still run on a bare
  interpreter — the tripwire skips with a named reason where PyYAML is absent, and CI installs
  it so the skip never hides there.
- `import fleet` must resolve when a script runs as `python3 scripts/<name>.py`; each consumer
  inserts the repository root ahead of its kernel import (one idiom, replacing the three-way
  import dance). Phase 1's `cli.py` makes `python3 -m fleet <verb>` the primary entry and
  reduces the scripts to shims.
- Two behaviours changed on purpose in phase 0 and are tested: a timed-out `probe_hosts`
  command now carries its partial transcript as text, and the test pool now excludes
  `node_modules` exactly as the probe's plugin copy always did.
- Drift facts 2 and 4 were resolved by measurement the same day; fact 3 by refreshing the
  known-key sets with a dated test. Fact 1 (native evals) needed a live run, which phase 4 took on
  2026-09-14 — see the oracle in
  [`routing-migration-oracle-2026-09-14.md`](../archive/2026-09/routing-migration-oracle-2026-09-14.md)
  (link intentionally over the wrap target; a split path would not resolve).

## Reopen triggers

- A host is found to read a frontmatter form differently from the dialect that the tripwire did
  not catch — the dialect's subset is wrong, not the tripwire.
- The kernel acquires a runtime dependency, or a hook imports it.
- A phase lands whose oracle needed a message or byte change that was not recorded in its PR.
- `claude plugin eval` loses the `tool_used` grader over `Agent` input, or its isolation stops
  matching the clean-room guarantees the retired runner gave — phase 4 is then reversed, not
  patched.

## Amendment, 2026-09-13 — phase 1 landed

Phase 1 is implemented on `claude/machinery-rewrite-fresh-ar08n6` after acceptance, with two
naming departures from the plan above, both because the planned name was already taken:
the typed snapshot is `fleet/snapshot.py` (the member and cross-reference records moved into
`fleet/references.py`, and `scripts/fleet_records.py` re-exports both), and the finding type is
`fleet/findings.py` as planned. What landed: `fleet/policy.toml` with every vocabulary and roster
stamped with its source and check date; `fleet/rules/` with 24 registered rules in eleven groups
run in the legacy `validate_repo` order, each declaring its scope (`fleet` or `definition`) and
every id it emits, with the runner sequencing definition-scoped findings definition-major as the
legacy per-definition loops did; `fleet/cli.py` with `validate` (`--json`, `--github`,
`--write-inventory`, `--no-adapters`) and `rules`; hook rosters read through `ast` in
`fleet.snapshot.read_rosters` and captured once per load as `HookScript` records, alongside
the manifest's presence and each skill's bundle inventory, so the validator neither executes a
hook script nor re-reads any input after the snapshot; the group vocabulary is closed (an
unknown group is refused at registration and at selection) and the policy's mappings are
read-only views;
`fleet/modules.py` as the one content-keyed script loader. `scripts/validate_fleet.py` shrank to
a compatibility layer whose `validate_*` functions and constants are views of the rules and the
policy, and whose roster-taking wrappers honour the caller's roster.

Oracle met: a scratch harness ran the pre-phase validator and the rule-based validator over the
repository, all fourteen fixtures, and eleven fresh mutations of a repository copy (a dropped
guard roster entry, a pinned model plus a scoped tool, a hook roster drift, a stale guide path, a
non-member routing entry, a workflow with a statement ahead of `meta`, an orphaned reference
file, a manifest without an author, all of those combined, three failing agents plus four failing
skills at once for the definition-major order, and unadopted tool grants plus alias drift) and
found identical message lists, order included, on every tree. Four diagnostics are the only
text deltas, mapped explicitly in the harness: the three tool-adoption messages and the guide's
alias message now name their `fleet/policy.toml` table instead of `FLEET_TOOLS`,
`FLEET_MCP_TOOLS`, and `ALIAS_MODELS`, which no longer govern anything. The suite grew from 550
to 596 tests, the new ones pinning rule ids per fixture, the registry's uniqueness, group
coverage, run order, and scope set, policy loading, snapshot reads (definition bytes and hook
rosters judged as loaded, never re-read), the roster reader's refusal to execute, the finding
renderers, and the CLI. Three Codex review rounds (seven, five, and seven findings) and one Copilot review (seven
findings, four still open on the head it reviewed) drove the
order, the snapshot-captured rosters, manifest presence, and bundle inventories, the declared
ids, the closed group vocabulary, the honoured rosters, the read-only policy views, the
source line on reference findings, the tolerant hook reader, the policy-pointing diagnostics,
the preload check judged against the captured roster, one snapshot per CLI run, and a load that
opens no file twice; one finding was declined, with the reason in `fleet/policy.py`'s docstring.

## Amendment, 2026-09-13 — phase 2 landed

Phase 2 is implemented on `claude/machinery-rewrite-fresh-ar08n6`, restarted from `main` after
phase 1 merged (PR #188). What landed: `fleet/hosts/rewrites.py` (a `Rewrite` with a stable id, a
`why`, its host and agent scope, and the count it must land; a `Ledger` that tallies a run and
names every rewrite that missed), `fleet/hosts/table.py` (every projection the generator applies,
in the order the hand-written chains ran, because each rewrite's output is the next one's input),
and `fleet/hosts/toml.py` (the Codex emitter). `scripts/generate_platform_adapters.py` lost its
394-line `if name == …` chain and its 30-replacement text chain; `expected_outputs` now owns one
ledger for the run and refuses to return bytes whose rewrites did not land their counts. The
generator left the lint ratchet in the same change, as the phase table requires.

Oracle met: all 181 generated files byte-identical, `--check` clean, and the forbidden-phrase
assertions unchanged and passing. The count contract was then exercised by mutation — rewording a
canonical sentence fails generation naming the rewrite, its landed count, and its `why`.

**The phase found the class it was built to close.** Twelve of the sixty-three ported rewrites
matched nothing anywhere in the fleet: the canonical sentences they anchored on had been reworded
or deleted (`the preloaded craft skills' rules` is now `the applicable craft skills' rules`;
`A container, VM, or Claude Code sandbox counts only …` is now `A separate agent counts only …`;
the three "already in your context" preload claims and the `${CLAUDE_PLUGIN_ROOT}/scripts/` path
form are gone entirely). None of them was correcting anything, and each was read by every
maintainer as a live control. They are deleted rather than pinned at zero — a rewrite that
translates nothing is dead, not cautious, so the table has no zero-expectation form. The
forbidden-phrase assertions in `tests/test_platform_adapters.py` independently cover the same
classes, so a canonical sentence that brings one of those forms back fails a test rather than
shipping.

Two deliberate departures from the plan above:

- **`tomli-w` is not adopted at all.** The plan added it "when the Codex TOML emitter has a
  consumer". Making it the emitter would put a dependency in the path that `--check` runs, and
  the T0 validator must keep working on a bare interpreter (Consequences, above), so
  `fleet/hosts/toml.py` emits and then parses its own document back with the standard library's
  `tomllib`, comparing it to the mapping it was asked to write — an always-on check that needs no
  install. It was then added as a differential tripwire beside that check, on the PyYAML
  precedent, and review showed the analogy does not hold: PyYAML is an independent *parser* of a
  dialect the fleet reads itself, while the fleet has no TOML reader — `tomllib` is the oracle
  here and in every consumer, so a third-party *writer* compared through that same parser cannot
  fail for any defect the round-trip already catches. It was removed as a check that re-proves an
  existing fact, and the dev group and CI install lines go back to what they were.
- **`expected_outputs(root, verify_rewrites=False)` exists for synthetic trees.** The counts
  describe *this fleet's* canonical corpus, so a two-file fixture would report every rewrite as
  missing and say nothing true. Every path that generates the real fleet — the CLI's `--write`,
  `--check`, and `--diff`, and the validator's adapter rule — keeps the default.

The four tests that asserted an anchor miss at the render-call level now assert it over a full
generation run, because the count a rewrite must land is a statement about the corpus rather than
about one render. The guarantee is strictly wider than before: it holds for all fifty-four
rewrites, where four were anchored by hand.

Review found three gaps in the first push, all fixed on the same branch. The three substitutions
in `_portable_readonly_body` had stayed outside the table, so the claim that every projection is
counted was false where it mattered most — a skill body crediting `disallowed-tools` with
removing Write and Edit names a deny the portable frontmatter drops. They are `skill.readonly.*`
in the table now. `--diff` also rendered two real changes as nothing: a difference only in line
endings or the final newline (which `splitlines()` discards, so the preview exited 0 on a tree
`--write` would still rewrite) and the retired roots `--write` deletes outright, which appear in
no expected-output map. Both are reported explicitly.

A second review round retired the `tomli-w` tripwire for the reason recorded above, and split the
count-mismatch diagnostic by direction: too few means an anchor was lost and must be re-anchored;
too many usually means a legitimate new occurrence to review and count. One message calling both
"unintended" would have sent half the failures to undo a correction that was working.

A third round caught the two remaining holes. The table had carried its own namespaced-reference
regexes — a second grammar for a fact `fleet/references.py` already owns, loose enough to rewrite
the namespace inside a URL and strict enough to skip a malformed reference the validator rejects.
The projection now compiles the canonical matcher, and the adapters stayed byte-identical, which
is the evidence the two grammars had not yet diverged in this corpus. And the TOML emitter's
"parsed does not equal intended" branch had no firing test: the escaping mutation exits through
the parse error instead, so the equality check was an untested guard reading as enforcement. A
mutation that emits valid TOML with a changed value now fires it.

A fourth round found the two remaining gaps, both places where a guard held only for the inputs
it happened to see. The read-only projections were applied only to a skill whose frontmatter
carried `disallowed-tools`, so a skill that acquired the claim WITHOUT the field skipped the
table entirely while the ledger's count stayed satisfied by the skills that do carry it — the
false deny shipped to both hosts. They now judge every skill body, and `had_tool_deny` keeps only
its own job, the adapter note about the dropped field. And `--diff` reported a retired root that
is a regular file as a zero-file removal, because `rglob` finds nothing in one, while `--write`
then aborted on that same path with `NotADirectoryError`: the preview promised what the operation
could not do. The preview now names the obstruction and the write clears a root whatever shape it
has, since a declared retired root is an obsolete artifact either way.

A fifth round closed the same two classes at their remaining edges, plus one new one. The
read-only projections judged only `SKILL.md` bodies, so the claim in a bundled `references/` file
still shipped untranslated with the ledger satisfied by the bodies — they now judge bundled
resources too. `--diff` disclosed a retired root that is a file but not an *active* generated root
that is one, which `--write` also unlinks before recreating the directory; both are reported now.
And nothing called `check_table` outside its unit test, so two rewrites sharing an id would share
one ledger entry and a lost anchor could hide behind its twin's count: the table refuses to load
that way at import, and the generator re-checks at the point of judgement so a table patched at
runtime fails too.

A sixth round found the one class the count contract structurally cannot hold, and in doing so
falsified a claim this record and the pull request had both made. Twelve rewrites were deleted
during the port because their canonical anchors were gone, and the justification offered was that
the forbidden-phrase assertions independently reject the same forms. Codex demonstrated that false
for `agent.codex.project-instruction-record`: reintroducing its sentence into a canonical agent
generated successfully and preserved the `CLAUDE.md` instruction verbatim in the Codex profile.
Checking the other eleven the same way — rather than accepting the single finding — showed the
claim failed for **ten of the twelve** on at least one surface, and for six on both; only the two
`${CLAUDE_PLUGIN_ROOT}` forms were genuinely covered.

The gap is structural, not an oversight in any one deletion. A rewrite's count is a *writer* check:
it holds prose that exists today to a projection. Deleting a rewrite deletes that check with it,
and the module deliberately refuses a zero expectation, so nothing can be left behind to watch for
the sentence's return. `RETIRED_CLAUDE_ONLY_FORMS` in `tests/test_platform_adapters.py` is the
reader check that now stands where those rewrites stood, asserted over every generated file in
every generated root. Verified end to end rather than by inspection: each of the twelve anchors was
injected into a canonical agent and a canonical skill, regenerated, and confirmed to be rejected —
which is the instrument that should have produced the original claim instead of a reading of the
assertion lists.

A seventh round found the read-only projections missing a third surface: skill *descriptions*.
Frontmatter values and the Codex explicit-only policy were adapted with the shared text rewrites
only, so the claim in a description reached both generated `SKILL.md` files and — when placed
early enough to survive the policy's 100-character truncation — the generated
`agents/openai.yaml` as well, with the ledger's count satisfied by the bodies throughout.

That is the same defect for the third round running (body in round 4, bundled resource in round 5,
description in round 7), which makes the pattern itself the finding: each fix closed the surface it
was shown while the next one stayed open, because **a corpus-wide count is a total, not a coverage
proof**. It cannot distinguish "every surface is projected" from "enough surfaces are projected to
reach the declared number", and nothing else was asserting the difference. The fix is therefore
structural rather than another patched call site: `adapt_skill_text` is the single entry point for
every piece of skill prose — frontmatter values, the body, bundled resources, and the policy
description — so there is no longer a fourth surface to route separately and forget. Adapters stay
byte-identical, which is the evidence that consolidating the four paths changed no output.

This is the limit of what the count contract can be asked to do. It is an excellent instrument for
a *rewrite that stopped matching*, which is the failure it was built for, and a poor one for a
*surface that was never wired*. The second failure needs one code path, not a better number.

An eighth round found the same defect on the agent side: descriptions ran only the shared text
rewrites while `AGENT_REWRITES` reached the body alone, so an authority sentence in an agent
description shipped to both host adapters untouched, with the ledger satisfied by the bodies. This
one is a miss in round 7's own fix rather than a new discovery — `adapt_skill_text` closed the
class for skill prose while the identical shape sat two functions above it, visible in the same
survey that produced it. `adapt_agent_text` is its twin, and both renderers now route description
and body through it.

Four surfaces across five rounds is enough evidence to stop relying on noticing the next one.
`test_every_prose_surface_goes_through_one_entry_point` parses the generator and asserts that
`adapt_text` is reachable only through those two composers, so a newly added surface that routes
itself separately fails a test naming the function that bypassed them. That is the structural
invariant the count cannot express: a corpus-wide total says how many times a rewrite landed, never
that every surface was offered to it. The two instruments are now complementary rather than one
overloaded — the count catches a rewrite whose anchor moved, the retired-form tuple catches a form
whose rewrite is gone, and this catches a surface the tables never saw.

**Operator ruling, 2026-09-13.** Eight broad review rounds ran against the three-round cap in
`AGENTS.md` ("Another broad round beyond the cap requires an explicit operator ruling"). The
operator ruled: address the round in flight, and accept no further broad rounds on this PR.
Rounds 1–8 are recorded above; the ninth is the last, and this PR merges on its disposition plus
green CI rather than on a round returning clean. Bounded corrections to demonstrated in-scope
defects remain permitted after it, as the cap has always allowed — what ends is the broad-review
loop, not the obligation to fix a defect someone shows us.

## Amendment, 2026-09-13 — phase 3 landed

Phase 3 delivered its three rows, and the property tests changed what the phase was worth.

**PROBE-006 is closed.** `probe_plugin.run` is `fleet.proc.run`, so a leg that gets no answer
returns the partial transcript instead of raising out of the run. Two primitives carry the
verdict: `unanswered_cause` names why a command produced no verdict — a timeout or a binary that
never started, both environment rather than fleet defect, which is why both are INCONCLUSIVE —
and `Probe.reading` declares which session the following checks read and how complete it is.
`reading` clears as well as sets, and that half is load-bearing: each leg drives its own session,
so a timeout in one must not silence the next. A truncated transcript downgrades a later FAIL to
INCONCLUSIVE, which is PROBE-002's distinction applied to a session — evidence that simply stops
cannot tell "the canary is absent" from "the oracle saw nothing".

Wiring it reproduced PROBE-006 in a new form inside the fix: two early returns added for
unanswered legs sat in `main()` rather than in a leg function, and would have skipped the workflow
contract entirely. The test asserting a timed-out main session still reaches that leg is what
surfaced it, which is the argument for writing the behavioural test before believing the fix.

**The doctor holds the kernel's result.** It kept its own three-field `CommandResult` and
downgraded into it, collapsing a timeout and a missing binary into one `returncode=127`. Those
call for different operator actions, and telling the operator which thing to fix is the doctor's
whole job. The checks now read `result.ok` rather than `result.returncode`, because a timed-out
result carries `returncode=None` and the old expression would have called that a success.

**The property tests found a live guard bypass on their first run.** `shlex(punctuation_chars=
True)` emits a run of adjacent operator characters as ONE token, so `ls;(rm -rf /)` lexed as
`['ls', ';(', 'rm', '-rf', '/', ')']`. `;(` matched no separator, the line never split, and the
segment's command word was the allowed reader `ls` with the denied command as its arguments —
ALLOWED, while both halves are denied alone. 33 variants confirmed. Any operator token that is
not exactly a recognised separator is now denied, on the same rule the unbalanced quote used;
a quoted `(` in a search pattern is denied with it, which is the guard's standing trade of a loud
false positive over a silent allow. The forms are in the DENIED corpus as well as the property
test, because that test skips without the dev group and a security regression must not be
skippable.

This is the case for the dependency, and it is worth stating plainly: the hand-written corpus had
every separator with a space and none without. A corpus encodes the shapes its author thought of.

Two dialect findings came from the same run. `yaml_scalar` emitted NEL, LINE SEPARATOR and
PARAGRAPH SEPARATOR literally while `str.splitlines()` breaks on all three, so a description
carrying one would be written whole and read back torn, its tail parsed as a frontmatter key —
fixed by escaping them, with every generated adapter byte-identical. The second is recorded as
DIALECT-001 rather than fixed: the reader strips quote characters instead of parsing the scalar,
so it never decodes the escapes the hosts do decode, and it eats a trailing apostrophe. It is
latent — nothing compares a description read back from a generated file against its canonical
source — and the fix changes what every rule sees for every quoted value, which is a phase of its
own rather than a change smuggled into this one.

**The hook probe was run, and the gate is discharged.** `python3 scripts/probe_plugin.py` against
CLI 2.1.270 — the pinned version — passed every guard and gate assertion: the guard denied the
reviewer and a `--agent` main session, ignored the main loop, the live-effect gate denied
homelab-engineer's live verb under `dontAsk` and ignored the main loop's identical one, and
`${CLAUDE_PLUGIN_ROOT}` expanded. So the pinned CLI still supplies the scoped `agent_type` the
guard's contract rests on, after the tokenizer change. Two failures and one inconclusive are
recorded with their dispositions in
[guard bypass probe evidence](../archive/2026-09/guard-bypass-probe-2026-09-13.md): both failures
reproduce prior results on this same pin in code this phase does not touch, and the inconclusive
is PROBE-003's root-session verdict observed live — one line with its own cause rather than five
cascading FAILs, which is the polarity contract working.

I had earlier reported this gate as impossible to discharge here, on the grounds that the
environment had no `claude` CLI. That was wrong, and wrong in the way this whole phase is about: I
asserted it without running `which claude`. The CLI was present at the pinned version the whole
time, and the claim reached the pull request body before anyone checked it.

A fourth round then found three more presence-based verdicts the truncation logic would silence
(`code_status`, the literal-plugin-root read, and a completed gate arm discarded when its peer
timed out). Enumerating them by hand had now failed three times, so the default moved instead of
the list growing: `check()` downgrades only when the caller passes `absence=True`. An unclassified
verdict is REPORTED. Forgetting now costs a noisy FAIL on partial evidence rather than a silent
pass, which is the only safe direction for a security instrument. The absence side is the safe one
to enumerate, because a mark that drifts there is visible as noise rather than as silence.

Copilot separately observed that the property test never *pins* NEL, LINE SEPARATOR and PARAGRAPH
SEPARATOR: a few hundred generated strings may include none of them, so reverting
`_escape_line_breakers` could pass wherever the example database is absent. A property is not a
regression pin, and `LineBreakerEscapingTests` now covers all three deterministically.

## Amendment, 2026-09-14 — phase 5 landed

Phase 5 delivered its one row, and the amendment this record promised: `docs/fleet-development.md`'s
hook section now says the hook file is generated and that a roster changes in the script.

**The hook file is rendered, not written.** `fleet/hooks.py` holds each hook's shell text verbatim
as a template with exactly two computed spans — the `case "$IN"` fast-path alternation and the
`case "$SQ"` identity alternation — and renders them from `GUARDED_AGENT_NAMES` and
`GATED_AGENT_NAMES`, read as AST data by `fleet.snapshot` (phase 1's reader; the generator's own
roster lookup, which used to *import* the guard, moved onto it in the same change). Substitution is
by explicit `@@PLACEHOLDER@@` rather than `str.format`, because both templates legitimately contain
`${CLAUDE_PLUGIN_ROOT}` and JSON braces, and an escaping mistake here is a silently disarmed hook.
Each hook renders with its own script's `PLUGIN_NAME`: the two must agree with the manifest, and
rendering both from one value would hide a disagreement behind a file that looks consistent.

**It is a generated file, not a generated root.** `--write` replaces a generated root wholesale,
which is right for a directory whose every entry the generator produces. `hooks/` is not that
directory — it is the plugin's own hook directory, and clearing it to regenerate one file would
take anything a future hook adds with it. So the generator gained `GENERATED_FILES` beside
`GENERATED_ROOTS`: byte-checked by `--check`, previewed by `--diff`, written by `--write`, and
subject to the same link/reparse refusal the roots carry, with no directory handed to the writer.
Its drift diagnostic is its own, because "Copilot would get host-dependent behavior" is not what a
stale hook costs.

**The check it replaces was reading prose as a roster.** The validator cross-checks each roster
against the hook file in both of the file's blocks. It selected them by position — first and last
— and the gate nests a `case "$IN"` inside its no-interpreter fallback to separate a suppressed
session from an interactive one. That nested block is last, and it names `homelab-engineer` only
inside an English denial reason. Measured while building this phase: replacing the gate's real
`case "$SQ"` roster with a name that gates nobody left `validate_fleet.py` at exit 0 and
`tests.test_fleet_rules` green. `tests/test_hook_wiring.py`, which executes the shell string, was
the only instrument that caught it (11 failures). The blocks are now selected by the variable that
opened them, and the mutation is pinned. The shipped hook was never wrong — the enforcement was
checking something else, which is the exact class this repository treats as worse than no check.

The cross-check stays alongside byte-drift validation rather than being retired by it. Byte drift
proves the file equals what the renderer produces; the cross-check proves the file names each
roster member in both deciding blocks. A wrong renderer satisfies the first and fails the second.

Oracle, as the phase table states it: the committed `hooks/hooks.json` is byte-identical to the
rendering (3,035 bytes, unchanged), and `tests/test_hook_wiring.py` still extracts the command and
runs it under `sh`. Nothing in this phase changes a shipped byte of shell.

**The lint ratchet, and what "a module leaves the table in the phase that migrates it" turned out
to mean.** The table held 27 file entries suppressing 147 findings. Three passes cleared 24 of
them: the classes that describe defects rather than formatting (`B023`, `B905`, `B007`, `F401`,
`F841`), the import and modernization classes (`I001`, `UP012`, `UP017`, `UP035`, `UP037`), and
line length in sixteen modules. What is left is three `E501` entries that no migration can clear,
and the operator ruled on 2026-09-14 that all three are permanent, amending MACH-001's acceptance
from "the table is empty" to "every entry states why it is exempt".

`scripts/probe_plugin.py` holds the probe's live-model stimulus (a prompt and a workflow
source) in triple-quoted constants. A physical line inside a triple-quoted string cannot carry a `noqa`,
and rewrapping it changes what the probe measures, so the recorded probe evidence would stop
describing the same measurement; reflowing an instrument's stimulus to satisfy a formatter is the
wrong trade. The two hook scripts' long lines are comments and code rather than emitted bytes, so
they are reflowable with no behavior change — but editing either is a hook change under
`AGENTS.md`'s hook playbook and owes a probe run, and spending a live probe to rewrap comments in
the fleet's security boundary is the same trade `[tool.ruff.format]` already declined when it
excluded them.

The distinction that matters for the next maintainer: a suppression dated to when the gate was
introduced is debt, and a suppression that states a reason is a decision. The table now holds only
the second kind, and the rule against widening an entry is unchanged.

**The probe was not run for this phase, and that is a ruling rather than an omission.**
`AGENTS.md`'s hook playbook owes a `scripts/probe_plugin.py` run for a hook change, and the
shipped `hooks/hooks.json` did not change a byte — it is identical at 3,035 bytes to the file the
last probe ran against, and absent from `git diff` on every head of the phase-5 PR. A run would
therefore have re-proved an existing fact, which proportionality forbids, and byte-identity is
the stronger evidence for a change of PROVENANCE than a live session would be. **The next probe —
owed at the next CLI pin bump — is the first to exercise a machine-produced hook file, and is the
run to read carefully.** Weighing against this ruling, and recorded because it belongs beside it:
review found three separate ways the renderer could have emitted bytes other than expected, so
the argument rests on the committed bytes being unchanged, not on the renderer being obviously
right.

## Amendment, 2026-09-15 — the consolidation audit, and two leftovers it removed

An operator asked the question this record could not answer from its own text: did the rewrite
actually remove the machinery it replaced? Audited across the rewrite's 81 commits.

**What the audit confirmed.** The retired generated roots are gone from disk and still declared,
so `--write` keeps deleting them. The session-launching half really did move to
`claude plugin eval` — no thread pool, process pool, or async gather survives anywhere under
`scripts/`, and `eval_routing.py` retains only the converter, scorer and recorder this record said
to keep. The guard's tokenizer exists once, in the hook that cannot import the kernel. The
conformance schema is loaded by the validator rule rather than copied. `probe_plugin.run` is a
three-line delegation to `fleet.proc.run`, not a fork. No file was deleted in the whole rewrite,
which is correct: it rewired internals rather than dropping files.

**Two leftovers were found and removed in the same change as this amendment.**

- `scripts/validate_fleet.py`'s `agent_tool_bases` re-implemented `fleet/snapshot.py`'s
  `Definition.tool_bases()` line for line — the same `TOOL_ENTRY_RE` over the same `split_tools`
  — with no caller anywhere in the tree. A second implementation of one fact is the exact defect
  the one-parser rule names, and it survived the change that existed to eliminate it, because
  nothing referenced it loudly enough to notice. Its orphaned `TOOL_ENTRY_RE` import went with it;
  `parse_frontmatter` and `split_tools` stay, because `tests/test_platform_adapters.py` consumes
  them as `validate_fleet` exports.
- `fleet/routing.py`'s `bare_names` was a namespace-stripping helper whose own docstring said it
  existed so callers would not re-derive the rule. It had no callers, and nothing re-derived it
  either. A mechanism with no task consuming it is what the proportionality rule forbids, and a
  docstring asserting a consumer that never arrived is how the surplus stayed invisible.

Neither deletion changed a test count (886, unchanged), which is itself the evidence that nothing
pinned them.

**Two findings were left open, deliberately, and are recorded here rather than acted on.**

- `scripts/validate_fleet.py` carries a block of pre-rewrite API names as delegating shims
  (`# --- rule groups under their legacy names ---`). They cannot disagree with the kernel, since
  they delegate, but at least `validate_agent_guide` and `validate_perishable_tokens` have no
  consumer in this repository. Whether that surface is owed to a consumer outside it is an
  operator call, not a fact readable from the tree.
- `scripts/eval_routing.py` calls `subprocess.run` directly rather than `fleet.proc.run`, and
  that is very likely correct: `fleet/proc.py` is deliberately absent from `EVALUATOR_PATHS`, so
  routing through it would put unhashed code in the measurement path. The reasoning appears
  nowhere at the call site, and **this record's own stated reason for it is now false** — "the
  runner stays untouched, deliberately not even wired onto the kernel" under *What retires* has
  not been true since phase 4, which wired it onto the kernel in two places and hashed five kernel
  modules into the evaluator identity. The comment is owed; the behaviour is not a defect.

**The limit of the audit, stated so the next reader does not over-trust it.** It was name-based,
so it produced false positives on every `fleet/rules/` function — those register through `@rule`
and never appear at a call site — and those were excluded by inspection rather than by the scan.
Dynamic access was checked for and none reaches these symbols, and there is no `__all__` export
contract. A consumer outside this repository would be invisible to it.
