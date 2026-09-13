# Rebuild the fleet machinery on one kernel

- Date: 2026-09-13
- Status: **accepted** by the operator on 2026-09-13 ("approved for the code rewrite"), after
  phase 0 merged in PR #187 and both live preconditions were met (the unprivileged probe re-run
  and the native eval pilot, both in `docs/archive/2026-09/`). Phases 1–5 now carry
  implementation authority in the order the phase table states, one PR each.
- Owner of the live work item: `MACH-001` in `docs/fleet-roadmap.md`.
- Amends nothing yet. Accepting phase 4 amends `evals/README.md` and the routing-eval sentence
  in `AGENTS.md`; accepting phase 5 amends `docs/fleet-development.md`'s hook section.

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
| 4 | routing evals migrated to native cases; runner retired; `evals/README.md` amended | one paired run under both instruments on the same plugin bytes agrees on every case verdict |
| 5 | `hooks/hooks.json` generated from rosters | byte-identical hook file; `tests/test_hook_wiring.py` still executes the shell string |

The lint ratchet in `pyproject.toml` lists, per legacy module, exactly the rule codes it
violated on 2026-09-13; a module leaves the table in the phase that migrates it.

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
  known-key sets with a dated test. Fact 1 (native evals) needs a live run and stays MACH-001's
  first live action.

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
