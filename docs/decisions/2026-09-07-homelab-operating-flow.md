# Homelab operating flow for one operator

> **Authority update, 2026-09-11:** The accepted
> [bounded-campaign decision](2026-09-11-bounded-upgrade-campaign.md) supersedes this record's
> exact-command-only authorization, automatic fresh-Tier-3 decision, and prompt-only transport
> requirements. Its applicable host controls and unrelated decisions remain in force. The
> original rationale and evidence below are retained as history.

**Status:** Implemented and reviewed candidate on `refactor/homelab-operating-flow`.
The evidence below was captured during pre-publication review. No host installation is part of
this change; publication was authorized after the review completed.
The operator selected main-review items 1, 2, 3, 5, and 6 on 2026-09-07. This change starts from
main `68dfc4458a416fde73eab79ba6a5028b535a8924`; the roster-cut branch is not its source.

## Decision and boundaries

- Retire the mandatory Learning packet and routine retro preloads across the existing roster.
  Preserve useful discoveries in an existing owned artifact when authorized, otherwise return
  the evidence, destination, and owner. Keep `self-improve-loop` as explicit maintainer work.
- Replace the homelab/builder digest-and-receipt protocol with a task brief carrying the objective,
  evidence-backed decisions, constraints, acceptance, authority/recovery, and remaining work.
  Keep operational configuration and small glue with the homelab owner; application code still
  goes to the builder. Missing substantive facts or contradictions remain real stop conditions.
- Replace the runbook proposal's five-line grammar with factual gap reporting. Document supported
  procedures while stopping only unsupported steps. Preserve real owner/path identities, scoped
  applicability, no invented commands, and Last verified tied to executed procedures.
- Reference an existing exact Tier 2 decision instead of repeating its proposal. State each
  effect's tier beside its target. Preserve actual host transport, a fresh Tier 3 decision and
  recovery proof, preflight freshness, bounded retries, and reconciliation after unknown outcomes.
- Preload only `code-craft` for the builder. Read backend, frontend, debugging, and CI guidance
  before the corresponding work. The runtime probe now checks common preload plus conditional
  backend loading; its guard, gate, workflow, and onboarding-path arms remain intact.

The agent roster, audit split, onboarding-map, tool grants, and live-effect hook are unchanged.
The diagnostic false positives and adjacent operational recipe findings were not selected.

The operator's selection of these broader policy changes from refreshed main supersedes the
earlier CTX-005 contract-preserving diet and its no-policy-change constraint. CTX-005 closes as
superseded; its old candidate remains historical no-go evidence, not a donor or an accepted
experiment. LABFLOW-001 is the sole live owner of this scope. This is not a claim that CTX-005's
missing routing/behavioral acceptance passed; the new work's evidence and gaps are stated below.

## Alternatives and consumers

A homelab-only Learning exception would add a policy split to the validator; retire the universal
contract and its four wording tests together instead. A new handoff schema, acknowledgment store,
or approval broker has no necessary consumer in this task. The existing builder still consumes
the useful brief facts; the host still owns execution permission. Keep structural adapter and
permission checks, not formatting tests for a retired packet.

The revised transport rewrite rejects missing or duplicate canonical policy bullets. Otherwise a
second conflicting policy could survive generation while byte-parity validation reported success.
The existing generic preload-validity check prevents preloading the explicit-only retro skill.

## Compatibility and rollback

This is a prompt/adapter migration, with no operational database or on-disk record migration.
Existing `Work Order v1` packets remain readable as task briefs; their contents are evidence and
constraints, not authorization. The revised receiver does not require a digest or emit a receipt.
Producer and consumer ship together. Previously recorded learning evidence remains historical;
no automatic promotion, deletion, or replay occurs. ACK-001 and LEDGER-001 leave the live queue
because their routine-ledger consumers are retired; their history remains in the archive.

Rollback restores the prior canonical definitions, corresponding validator/probe changes, and
regenerated adapters together. It does not undo any lab effect, artifact written by an operator,
or in-flight task. Reconcile such a task and supply the old receiver's required brief before
resuming under reverted definitions. Restoring only one side of the handoff is unsupported.

## Acceptance and evidence

| Scenario | Required observation |
|---|---|
| Routine completion | Useful result, no empty Learning form or implicit retro; an actual gap retains evidence and owner |
| Complete legacy brief without digest | Implementation preserves constraints and verifies output; no formatting-only stop |
| Conflicting brief | The material conflict is resolved before the affected edit |
| Supported Health, unknown Recovery | Authorized Health update proceeds; Recovery stays visibly non-runnable with owner |
| Proposal with missing ownership | Factual missing evidence, no invented owner or executable advice |
| Existing Tier 2 decision | No new chat approval; the actual host control still carries each effect |
| Tier 3 or unproven transport | Fresh decision/recovery requirements remain; no silent live effect |
| Unknown apply result | Inspect state before retry; a completed effect is not repeated |
| Backend-only work, then a failure | Applicable guidance loads before work; no frontend/retro preload; diagnosis precedes the next fix |

### Executed fixture outcomes, 2026-09-07

Fresh source-following actors read frozen main or candidate definitions. Builder and runbook pairs
received identical fixture tasks, with the scoring criteria withheld. The authority comparison
used identical case facts; an earlier candidate response to an abbreviated prompt was excluded.
These are small diagnostic samples, not population rates, latency measurements, or host-control
proof. No operational command was executed in the simulated authority cases.

| Fixture | Main | Candidate | What the result establishes |
|---|---|---|---|
| Complete legacy brief without ID/digest, two actors per side | Both stopped solely for the missing identity/digest; no implementation | Both implemented and passed 16 independent input checks each | Removing the formatting stop restored completion on this task |
| Supported Health update, unknown required Recovery, two actors per side | Both updated correctly; 423 and 478 words | Both updated correctly; 160 and 148 words | Same observed core behavior with less filler; a whole-document block was not reproduced on main |
| Previously approved exact Tier 2 restart | Continued through the managed gate; included the full packet and empty Learning line | Continued through the managed gate; no new chat approval or empty Learning line | The shorter reporting path preserved execution interposition |
| Tier 3 firewall command that auto-allows | Operator handoff for a fresh decision | Operator handoff for a fresh decision | General maintenance approval did not authorize the access-path change |
| Restart lost its exit status | Read-only reconciliation before another live effect | Read-only reconciliation before another live effect | Neither inferred failure or blindly repeated the restart |

The builder task accepted positive integers and decimal strings; it rejected booleans, floats,
zero/negative values, invalid strings, and unsupported types with `ValueError`. The independent
check covered `1`, `"30"`, `"0003"`, `999`, `True`, `False`, `1.5`, `2.0`, `"1.5"`, `"x"`, `0`,
`-1`, `""`, `None`, `[]`, and `{}`. Both candidate actors also exercised red/green verification.

The runbook task corrected `/healthz` to `/health` from an operator's HTTP 200 observation on
`nuc-01`. All four artifacts kept required Recovery visibly incomplete, named Alex Hawkins as its
owner, and limited Last verified to Health. No restart or recovery was claimed as executed.
The candidate artifact mean was 154 words versus 450.5 on main, a 66% reduction for this fixture.

Conflicting briefs, unresolved document ownership, secrets handling, and conditional guidance
failure were checked in source review; they were not separately exercised by paired actors.
The simulated authority responses establish the ordered decision boundaries only: one candidate
used the label `verified in simulation`, which is not evidence of a real observed lab result.

Frozen inputs and outputs remain locally under
`C:\Users\hawkins\sde-agents\.worktrees\homelab-behavior-pairs-20260907`; the independent builder
results are in `fixture-verification.json`. This local scratch location is not a shipped fixture.
The three candidate definition bodies used in these comparisons were unchanged by review fixes.

### Source size and identity

Measured on the same Windows host with Python whitespace splitting; characters use decoded UTF-8
with normalized newlines. These are source sizes, not tokenizer counts or performance evidence.

| Canonical source | Main words | Candidate words | Main characters | Candidate characters |
|---|---:|---:|---:|---:|
| `agents/homelab-engineer.md` | 3,873 | 2,830 | 26,021 | 18,816 |
| `agents/sde-fullstack.md` | 3,211 | 2,812 | 20,573 | 17,778 |
| `skills/runbook/SKILL.md` | 1,510 | 841 | 10,283 | 5,885 |

Candidate normalized UTF-8 SHA-256 fingerprints, in that order:

```text
9c4a9254605234673a0ca5d889d5748b284185107fb9583b4a0368bab0bca25b
8891105293ae20a90a31d2b5fcf49bc98576a6bbef912fdbd3e77968d8b7630b
e567e0a5559db4c67d0a678f786541e73ff2b9261547727275a95ca39dc7f4d2
```

### Offline and live verification

- `python -B scripts/generate_platform_adapters.py --write`: 181 adapters regenerated.
- `python -B scripts/validate_fleet.py`: 11 agents / 20 skills, inventory current.
- `python -B -m unittest discover -s tests`: 485 tests, 73.194 seconds, OK with two skips.
  The command-local PATH included the already installed Git `sh` for hook wiring tests.
  The suite includes 50 probe-canary tests, covering cross-actor contamination, missing child
  provenance, and asynchronous launch-versus-completion attribution.
- The duplicate-transport test was independently exercised against a mutation that accepted the
  first match only: both policy bullets on both generated hosts stopped failing under that mutation.
  The candidate rejects all four duplicate cases; adapter byte parity alone would not catch them.
- The first static review found an automatic retro call remaining in postmortem and a probe that
  could borrow another actor's backend Read. Both were corrected. The paraphrase sweep also fixed
  service-onboard's retired proposal grammar and the layer skills' stale preload claims.
- The second and final independent static review found no remaining material findings. It reopened
  the corrected call sites, checked authority and adapter boundaries, and independently matched
  the saved runtime capture and the three definition fingerprints to this record. This verdict
  covers the inspected working diff, not an unseen later revision or installation.

The full runtime probe on Claude Code 2.1.263 passed strict plugin validation, plugin agent
registration, the homelab onboarding fallback/path expansion, reviewer guard denial and main-loop
scope, the guarded `--agent` invocation, and the live-effect gate's suppressed-prompt denial.
Its gate/main-loop comparison was inconclusive because the main loop did not attempt the command.
The later Grafana conditional-reference arm timed out after 900 seconds, reproducing existing
PROBE-006; the subsequent workflow arm did not run. This is not a full runtime-probe pass.

The first builder-loading score mistook an asynchronous launch receipt for completion. The revised
oracle requires the matching builder's completion and child tool provenance. Replaying its saved
launch/completion established the answer shape but remained inconclusive without child provenance.

A fresh, focused capture then ran only the existing builder inspection prompt through Claude's
native Agent tool, with the same plugin path and `stream-json --verbose`. It exited 0 on
`claude-fable-5-1`. The final oracle passed all three checks: code-craft's canary came from preload,
backend-craft was read and its canary used, and frontend-craft stayed unloaded. The stream contained
one builder spawn, one backend Read, and three child events carrying the builder's parent tool ID.
This proves the inspected path on this host/run, not that every future task loads its guidance.
The focused capture, including partial output on timeout, was saved before scoring; no broad probe
rerun was needed.

Local capture: `.probe-tmp/conditional-loading-final.jsonl`, 43,992 bytes, SHA-256:

```text
cc2478874ca970f03adb7d9012871ea3c06a901fec9d6ca01f5f0311b9a485c7
```

Host installation is outside this change. The doctor reports the working diff, the existing
aggregate skill-listing budget warning, and installed Codex agent drift. Source/adapter validation
does not certify those installed copies. Descriptions were unchanged in the initial candidate;
the PR review correction below aligns the explicit-only retro's description. No routing-rate
improvement is claimed. The retro's automatic positive cases were retired, leaving 103 routing
cases (41 positive, 62 negative); their negative boundaries remain.

## PR #175 review corrections

The four review findings on `28c6487` are corrected in one follow-up batch:

- Portable builder instructions resolve actual catalog paths and provide checked repository-local
  fallbacks for all four conditional skills. Both generated hosts are regenerated; neither names
  a nonexistent Claude Read tool or treats a descriptive label as a file path. Native portable-host
  discovery was not exercised; the emitted routes and all eight fallback files were checked.
- The canonical retro description and generated picker text now lead with explicitly requested
  maintainer retros, matching disabled implicit invocation.
- Outer builder spawn, answer, async launch, and completion evidence requires explicit root
  attribution. Thirteen previously passing foreign/missing/sidechain cases failed before repair;
  all 51 canary tests now pass. The genuine saved native capture above replays three passes under
  the corrected oracle; this is a replay, not a new live session.
- CTX-005 is superseded as stated in the decision above, preserving its failed history and leaving
  LABFLOW-001 as the sole live owner of the selected operating-flow work.

The final full suite ran **488 tests in 77.184 seconds, OK with two skips**. All 32 adapter tests
passed, including red-first checks for unusable paths and missing/duplicate route rewrites. A
focused independent review of this correction found no remaining material findings.

Paired routing used unchanged cases and evaluator bytes, three runs per case, requested `sonnet`
(observed `claude-sonnet-5`), Claude 2.1.263, clean-room mode, threshold 0.5, concurrency two, and
**600-second** per-run timeouts. `retro-boundary` passed 5/5 cases before and after: postmortem 3/3
on the positive, zero forbidden invocations on all four negatives. `continuous-improvement`
passed 6/6 before and after, with zero self-improve-loop invocations in all 18 negative trials on
each side. Every case's correct-rate delta is zero; no errors, inconclusive cases, or excluded runs
were reported. These checks preserve routing boundaries; they do not prove picker usability.

The plugin locator differs (`.` before, `<external-plugin-dir>` after) because the before source
was frozen at `28c6487` in a separate checkout. Both sides ran identified private plugin copies;
all other recorded conditions and the case/evaluator provenance match. Local artifacts are under
`C:\Users\hawkins\sde-agents\.worktrees\pr175-review-evidence`, including the four benchmark files
and `routing-comparison.json`. Benchmark SHA-256 identities:

```text
retro-before  1e1b3816038520cc3725f7a2c8edd1b663ee4ac34d4ef4e14844fa7b64e92d23
retro-after   e1a28318b3486ace884b46af923b5e87374b5c20d3bd69ec43f5ec8126ae529c
improvement-before  1ba772e706442c396d7cd7e15a304fb48718d45cfc1b566db8adf78e325a3069
improvement-after   1c06ff152eb9b31a335f4c75ffac2fd8d86edbd8518f96a75f974decc85fda30
```

## Reopen triggers

A brief loses a decision the receiver needs; an ordinary task starts a retro; required guidance
is skipped; or a transcript shows an extra approval or a lost permission/recovery boundary.
Investigate the concrete case before adding another mechanism.
