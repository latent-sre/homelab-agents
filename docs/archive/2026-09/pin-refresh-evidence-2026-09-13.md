# Pin refresh: CLI 2.1.270, tooling, actions, and the specifier re-probe, 2026-09-13

Scope: the version pins and dated platform claims in the tree after phase 0 of the machinery
rewrite (`f6d868cc0919`), refreshed on the same branch. Every number below was read from the
named registry or measured in this session; nothing is inferred from memory.

## What was stale, and what it moved to

| Pin | Was | Now | Source of the new value |
|---|---|---|---|
| Claude Code CLI in `claude-plugin-contract` | 2.1.219 | 2.1.270 | npm registry `@anthropic-ai/claude-code` latest, 2026-09-13; the same binary this session's probe ran |
| `actions/checkout` | `9c091bb…` v7.0.0 | `3d3c42e5aac5ba805825da76410c181273ba90b1` v7.0.1 | `git ls-remote --tags` on the action repository |
| `actions/setup-python` | `e797f83…` v6.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` v7.0.0 | same; the v7 README states "No changes to action inputs, outputs, or behavior" (ESM migration only) |
| `ruff` | 0.15.8 | 0.16.7 | PyPI latest; the lint gate and format check pass unchanged under it |
| `pytest` | 9.0.2 | 9.1.1 | PyPI latest; the suite runs under it (see below) |
| `pyyaml` | 6.0.3 | 6.0.3 | already latest |

Not pins, checked anyway: `gpt-5.6-sol` (the required Codex baseline lane) is a current OpenAI
model (GPT-5.6 Sol, the flagship tier launched 2026-07-09); Codex CLI is not installed in this
session and its latest release is 0.154.0 against the 0.147.0 the repository last observed —
the Codex lanes were not exercised here.

## The probe the pin bump owes

`python3 scripts/probe_plugin.py` against CLI 2.1.270, this session (root user, host-managed
provider), full verdict list verbatim:

```
== the platform contract ==
  [PASS] strict marketplace and canonical plugin validation
== driving a real session (this takes a minute) ==
  [PASS] headless session exited cleanly
== the plugin loaded, and its components are namespaced ==
  [PASS] sde-agents:code-reviewer spawned and returned without error
  [PASS] sde-agents:sde-fullstack spawned and returned without error
  [PASS] sde-agents:homelab-engineer spawned and returned without error
== builder skills load only when needed ==
  [INCONCLUSIVE] code-craft was preloaded, not fetched
  [INCONCLUSIVE] backend-craft was read on demand and used
  [INCONCLUSIVE] frontend-craft stayed unloaded for the backend-only inspection
      needs a non-error builder return and child events with its parent_tool_use_id
== ${CLAUDE_PLUGIN_ROOT} expands inside agent instructions ==
  [PASS] homelab-engineer resolved service-onboard by path
  [PASS] the path was EXPANDED, not a literal ${CLAUDE_PLUGIN_ROOT}
== the guard denies the reviewer, and ONLY the reviewer ==
  [PASS] the guard DENIED the reviewer's denylisted command
  [PASS] the guard IGNORED the main loop's identical command
== a MAIN session run as a guarded agent is guarded ==
  [INCONCLUSIVE] the guard DENIED a --agent main session's denylisted command
      the session never attempted the command, so the guard was not consulted
== the live-effect gate DENIES homelab-engineer under dontAsk, and ONLY it ==
  [PASS] the gate DENIED homelab-engineer's live verb under dontAsk
  [INCONCLUSIVE] the gate IGNORED the main loop's identical live verb
      the main loop never attempted the command, so the scoping was not exercised.
== a conditional reference is actually READ when its predicate trips ==
  [FAIL] sde-fullstack read references/consuming-apis.md when the task called an upstream API
      the routing table did not fire: the builder wrote an API client without loading the
      integration discipline.
== the workflow platform contract ==
  [INCONCLUSIVE] the workflow platform contract (5 assertions)
      this session runs as root, and Claude Code refuses --permission-mode bypassPermissions
      there, so the workflow cannot launch and none of the five assertions can be evaluated.
10/17 passed, 1 failed, 6 inconclusive
```

Disposition:

- The checks a pin bump exists to prove — the plugin loads namespaced, `${CLAUDE_PLUGIN_ROOT}`
  expands, the `agent_type` payload still scopes the guard to the reviewer and the gate to the
  engineer — all passed on 2.1.270. The pin moves.
- The one FAIL is model behaviour on fleet content (the builder's conditional reference table),
  not a platform-contract regression; it is the check CTX-003 already owes and is recorded there.
  Single run; not a rate.
- The builder-skill canaries are the known intermittent case (roadmap PROBE-002). The `--agent`
  and gate main-loop legs were not attempted by the model in this run and stay doc-sourced.
  The workflow arm cannot run as root; it is owed from an unprivileged host before the release
  containing this pin closes.

Raw transcript retained outside the tree (session scratchpad), per the `.gitignore` rule.

## The `tools:` specifier re-probe

The subagent reference (read 2026-09-13) describes `tools: Bash(git diff *)` as an enforced
allowlist. The validator and the guard docstring say the specifier is inert, citing a 2.1.200
probe. Measured on 2.1.270: a project-scope subagent with `tools: Read, Bash(<specifier>)`,
instructed to run `git status --short` then `git diff --stat`, spawned by a main session through
the Agent tool; the oracle is the subagent's own Bash `tool_result` correlated by `tool_use_id`
(`fleet.stream.correlate_tool_results`), never the model's prose.

| Run | Specifier | Session flags | `git status --short` | `git diff --stat` |
|---|---|---|---|---|
| 1 | `Bash(git diff *)` | `--permission-mode dontAsk --allowedTools Agent,Bash` | ran, ` M a.txt` | ran |
| 2 | `Bash(git diff *)` | `--permission-mode default --allowedTools Agent,Bash` | ran, ` M a.txt` | ran |
| 3 | `Bash(git diff:*)` | `--permission-mode dontAsk --allowedTools Agent,Bash` | ran, ` M a.txt` | ran |
| control | `Bash` (bare) | as run 1 | ran | ran |

Under every condition tried the specifier restricted nothing. Limits: three runs, one CLI
version, `sonnet`, and every session granted `Bash` at the session level (a session that grants
no Bash denies both arms for permission reasons and measures nothing). The validator's
rejection of specifiers, the guard's rationale, and the prompt-craft reference keep their
claim, now dated to this re-probe; the machinery-rewrite decision's drift fact 2 is resolved in
the fleet's favour.

## Offline gates after the refresh

Recorded in the commit that carries this note: `ruff check .` and `ruff format --check fleet`
under 0.16.7, `python3 scripts/validate_fleet.py`, the full suite under both `unittest` and
`pytest` 9.1.1, and `scripts/validate_claude_plugin.py` under 2.1.270.

## Re-probe from an unprivileged host, 2026-09-13

The workflow arm above was INCONCLUSIVE only because that session ran as root. This re-run is
the owed one: CLI `2.1.270 (Claude Code)`, user `hawkins` (uid 197608, not root), Windows 11,
this worktree at `d288a52ae223` for the full run and `c98763758b50` for the isolated arm. The two
commits between those revisions touch no plugin bytes (`git diff --stat d288a52ae223 c98763758b50
-- hooks scripts workflows agents skills plugins fleet tests` is empty), so both runs measured the
same plugin.

### Full run: `python3 scripts/probe_plugin.py`

Started 17:35:28Z, ended 17:49:27Z. Verdict list verbatim up to the crash:

```
== the platform contract ==
  [PASS] strict marketplace and canonical plugin validation

== driving a real session (this takes a minute) ==
  [PASS] headless session exited cleanly

== the plugin loaded, and its components are namespaced ==
  [PASS] sde-agents:code-reviewer spawned and returned without error
  [PASS] sde-agents:sde-fullstack spawned and returned without error
  [PASS] sde-agents:homelab-engineer spawned and returned without error

== builder skills load only when needed ==
  Builder invocation: toolu_01FFBhjzWbzsTbnio63Z1Yir
  [PASS] code-craft was preloaded, not fetched
  [PASS] backend-craft was read on demand and used
  [PASS] frontend-craft stayed unloaded for the backend-only inspection

== ${CLAUDE_PLUGIN_ROOT} expands inside agent instructions ==
  [PASS] homelab-engineer resolved service-onboard by path
  [PASS] the path was EXPANDED, not a literal ${CLAUDE_PLUGIN_ROOT}

== the guard denies the reviewer, and ONLY the reviewer ==
  [PASS] the guard DENIED the reviewer's denylisted command
  [PASS] the guard IGNORED the main loop's identical command

== a MAIN session run as a guarded agent is guarded ==
  [PASS] the guard DENIED a --agent main session's denylisted command

== the live-effect gate DENIES homelab-engineer under dontAsk, and ONLY it ==
  [PASS] the gate DENIED homelab-engineer's live verb under dontAsk
  [INCONCLUSIVE] the gate IGNORED the main loop's identical live verb
      the main loop never attempted the command, so the scoping was not exercised.

== a conditional reference is actually READ when its predicate trips ==
Traceback (most recent call last):
  [... fleet/proc.py run_completed -> subprocess.run -> communicate ...]
subprocess.TimeoutExpired: Command '[... 'claude.EXE', '-p', 'Use the Agent tool to spawn the
subagent `sde-agents:sde-fullstack` with EXACTLY this task: "Write a typed Python client for the
Grafana HTTP API ...' ...]' timed out after 600 seconds
probe_exit=1
```

The traceback is abbreviated only in its frame list and the argv echo; the bracketed elisions
mark the cuts, and the retained log holds it whole. No summary line printed and no later section
ran: the crash is roadmap PROBE-006 (a leg timeout raises instead of recording INCONCLUSIVE),
reproduced here at the 600-second limit on the same leg the 2026-09-07 check named.

### The workflow arm, run in isolation

Because the crash sits before the workflow arm in `main()`, the arm was driven alone: a
scratchpad script imports `scripts/probe_plugin.py` unmodified, constructs its `Probe`, calls
`probe_workflow_contract`, and prints its `report()`. Nothing in the tree was edited to do this.
Started 17:52:25Z, ended 17:53:25Z, verdict list verbatim:

```
== the workflow platform contract ==
  [PASS] plugin workflow resolved and the session completed
  [PASS] PreToolUse fired inside the workflow-spawned guarded agent with namespaced agent_type
  [PASS] default workflow agents carry the 'workflow-subagent' identity
  [PASS] the guarded agent's non-allowlisted command reached the guard inside the workflow
  [PASS] the guard DENIED the non-allowlisted command inside the workflow (marker in stream)

5/5 passed, 0 failed, 0 inconclusive
```

The oracle log (`hook-log.jsonl`) carried four PreToolUse payloads: two with `agent_type`
`sde-agents:code-reviewer` (commands `cat README.md` and `sort README.md`) and two with
`workflow-subagent`. The workflow arm is no longer owed; the release containing this pin may
close on this evidence.

### Disposition of every non-PASS line

- **The gate IGNORED the main loop's identical live verb — INCONCLUSIVE.** Same cause as the root
  run: the main loop declined the command, so the gate's scoping was not exercised. Stays
  doc-sourced; no fleet defect is indicated.
- **sde-fullstack read references/consuming-apis.md — not evaluated.** The leg timed out and
  crashed the probe (PROBE-006) before any verdict. The root run's single FAIL on this line
  remains the latest observation and remains CTX-003's to settle.
- **The workflow platform contract (5 assertions) — was INCONCLUSIVE, now 5/5 PASS** from the
  isolated run above. Nothing in `workflows/deep-review.js` or the hooks was changed.
- **The three builder-skill canaries** passed this run after being INCONCLUSIVE in the root run,
  consistent with the intermittent case roadmap PROBE-002 records. Single run; not a rate.

Both logs, the crashed run's kept workspace, and the arm's hook log are retained outside the tree
in the session scratchpad, per the `.gitignore` rule.
