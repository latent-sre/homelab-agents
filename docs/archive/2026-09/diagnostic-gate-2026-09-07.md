# Diagnostic command gate correction, 2026-09-07

Candidate starts from main `68dfc4458a416fde73eab79ba6a5028b535a8924` on
`fix/homelab-diagnostic-gate`. The operator requested the diagnostic false-prompt repair and
confirmed a ten-minute timeout convention. This is separate from operating-flow PR #175.

## Reproduced behavior and correction

The live matcher searched later argument words for mutation verbs. Thus `docker inspect restart`
matched `docker restart`. Whole command groups also conflated reads with writes: `terraform state
list` and `kubectl rollout status` were gated, as was bare `mount`. Under `dontAsk`, these false
positives became denials, not extra prompts. The initial regression suite failed 90 assertions.

The correction recognizes narrowly listed diagnostic paths before the conservative matcher,
consuming known option values before locating the command. This covers Docker inspect/logs/ps and
Compose ps/logs/config, selected systemctl status commands, rollout status/history, state
list/show/pull, and bare mount or its listing-only label switch. Operands named `restart`, `up`,
or `stop` remain operands. Unknown option arity and unlisted command paths retain the conservative
matcher. No live roster entry, agent scope, permission mode, hook wiring, or exit code is removed.

An independent review found that existing normalization discarded assignment-shaped option values
and quoted redirection-shaped values. That could turn a real write into an apparent reader:
`docker --config cfg=prod restart inspect` or `docker --config '>cfg' restart inspect`.
Thirteen new assertions reproduced the failure before repair. Assignment stripping now applies
only at prefix positions. Diagnostic recognition is withheld for command text containing `<` or
`>` because the existing splitter does not retain the needed quotation provenance; the same
restriction follows SSH recursion. These ambiguous spellings can still prompt, deliberately.

The second review identified a compatibility interaction: retaining three assignment-shaped
Compose filenames pushed `up` outside the old matcher's scan window. Nine assertions reproduced
it. Diagnostic recognition now uses intact operands, while the live fallback separately retains
its legacy normalization. An independent comparison generated 200 live command spellings with
repeated options, unusual values, and sudo/env/SSH wrappers; all 176 that the baseline denied
remain denied. This is regression coverage, not a claim that the legacy matcher is exhaustive.

The probe's subprocess timeout changes from 900 to **600 seconds per invocation**. This does not
repair PROBE-006's separate loss of later checks when a timeout escapes the probe runner.

## Public command contract

Context7 supplied the documented read/write distinctions; GitHits supplied implementation evidence.
No target infrastructure command was executed to establish these distinctions.

- Mount's [listing condition](https://github.com/util-linux/util-linux/blob/c08bd2aa50aa306c6ad51e50f582acf686283deb/sys-utils/mount.c#L1027)
  and [operand dispatch](https://github.com/util-linux/util-linux/blob/c08bd2aa50aa306c6ad51e50f582acf686283deb/sys-utils/mount.c#L1077)
  distinguish listing from mounting; even a single target operand may mount from fstab.
- Docker's [global options](https://github.com/docker/cli/blob/d306b9d6007b0e9a0ec1c7a99646fceba4f5e20e/cli/flags/options.go#L119)
  and Compose's [project flags](https://github.com/docker/compose/blob/75331cd042747b69ac1d6c802ce3a5069fd3e7ed/cmd/compose/compose.go#L224)
  establish value-bearing options before command selection. Docker's snapshot was provisional
  while GitHits indexing completed; these facts are syntax evidence, not installed-version proof.
- Kubectl registers [distinct rollout commands](https://github.com/kubernetes/kubectl/blob/master/pkg/cmd/rollout/rollout.go#L67);
  [restart patches resources](https://github.com/kubernetes/kubectl/blob/master/pkg/cmd/rollout/rollout_restart.go#L195).
- Terraform [state pull](https://github.com/hashicorp/terraform/blob/main/internal/command/state_pull.go#L60)
  and OpenTofu [state pull](https://github.com/opentofu/opentofu/blob/80be292a94a61d99dfd9b1a090cea2e759b6209c/internal/command/state_pull.go#L71)
  export state to stdout; state mutation verbs retain the existing gate.

## Verification

All 38 gate tests pass after the normalization repairs. They exercise the real hook subprocess
exit-code/JSON contract: recognized reads get no gate decision in normal, suppressed, and absent
modes; neighboring writes retain ask/deny, including SSH and command chains. Three static review
rounds ended with both reported P1s corrected and no remaining material findings.

- `python -B -m unittest discover -s tests`: **468 tests, 80.689 seconds, OK, two skipped**.
  The command-local PATH included the installed Git `sh` for hook wiring tests.
- `python -B scripts/validate_fleet.py`: **11 agents / 20 skills**, adapter parity and inventory
  current. No canonical definition changed, so no adapter regeneration was needed.
- `claude plugin validate . --strict` and `git diff --check`: **passed**.
- Native Claude Code **2.1.263**, `homelab-engineer`, `dontAsk`: the exact Bash `mount` call ran
  and returned the Git Bash mount listing, with no gate denial.
- A separate native call attempted `docker compose -f <absolute missing fixture file> up -d probe`
  under the same agent and mode. The hook denied it with its own live-effect-gate reason. The
  absent Compose file made the check inert independently of the gate, and remained absent.

The broad probe passed registration, onboarding-path expansion, reviewer guard denial/main-loop
scoping, guarded `--agent` denial, and the main-loop live-verb exclusion. Its initial gated-agent
leg was inconclusive because the agent did not attempt that command; the separate native check
above exercised it. Main's preload oracle misread an async launch receipt as an answer, the
existing issue addressed in PR #175. The API-reference leg then reached the observed **600-second**
timeout, reproducing PROBE-006; the workflow arm did not run. This is not a full broad-probe pass.

A local capture wrapper persisted each invocation's output before scoring and kept partial output
on timeout, then re-raised the original exception. It did not change the shipped scorer or continue
later legs. The source hashes stayed unchanged during the run. Captures and red/green test logs are
under `C:\Users\hawkins\sde-agents\.worktrees\homelab-diagnostic-evidence-20260907` (local evidence,
not shipped fixtures). SHA-256 identities:

```text
scripts/live-effect-gate.py
7b95cc13daecda90ffcd90014339cd49d15c97886d7b6307e5bd48c35cd1b156
scripts/probe_plugin.py
bbd8bb7a1e6e7f0dc75198ace7996e1b9bce7b9d7a8dc3807cdd847eeed67990
native-reader.json
b9e4e83c67b00a0b87806733bff1a0aa6e1383c87ce3001d8f3b60c99b3ef733
native-live-verb.json
0c595f922d492d9f701710446f1e470a55f84fb1ad90cca279f78adda4aa660e
```

The doctor reports the working diff, the existing aggregate listing-budget warning (9,983
characters on this main-based tree), and installed Codex drift. No host installation occurred.
This change does not certify unusual CLI extensions or arbitrary wrappers as harmless.

Rollback restores the gate and timeout source together with their tests. It restores the earlier
false prompts and the 900-second timeout; no infrastructure operation is part of this change.

## PR #176 review correction

The diagnostic parser now recognizes explicit values on known Boolean switches, using the flag
name before `=`. Supported `docker-compose` and `k3s kubectl` frontends normalize only inside the
diagnostic recognizer; unmatched commands still reach the original live matcher unchanged.

The option syntax is documented in Docker's
[pflag reference](https://github.com/docker/cli/blob/master/vendor/github.com/spf13/pflag/README.md).
[K3s documents its embedded kubectl frontend](https://docs.k3s.io/cli). Both alias families already
had live entries in this gate; this correction gives their diagnostics the same treatment.

Nine additional diagnostic commands across five modes reproduced **45 false denials** before the
repair. Seven neighboring live, unknown-option, and compound commands retain ask/deny. The full
suite passed **470 tests in 85.442 seconds, two skipped**, with Git Bash available for hook tests.
Adapter parity, inventory, strict plugin validation, and whitespace checks passed. A bounded
independent static review found no new live-command exemption.

A fresh native Claude 2.1.263 session under `homelab-engineer` and `dontAsk` attempted exactly
`docker --tls=false inspect restart`. Docker returned a missing local daemon error, proving that
the diagnostic reached the CLI without a gate denial, not that Docker inspection succeeded.
The same session attempted `docker-compose -f <absolute absent fixture> up -d probe`; its correlated
tool result contained the gate's own `docker-compose up` denial. The fixture remained absent,
independently preventing deployment. Capture: `.worktrees/pr176-native-review.jsonl` in the local
parent checkout.

GATE-008 is removed from the live roadmap in this landing change, and this archive is indexed as
implementation evidence. It remains the record of verification limits; a merged tree must not send
the next session back to a completed diagnostic fix. PROBE-002 and PROBE-006 remain separate.

The correction also reran the broad probe. It was stopped after exceeding a ten-minute overall
budget; buffered stdout yielded no completed report. This attempt is **incomplete**, not a pass,
and does not replace the scoped tool-result evidence above or close the existing probe gaps.
