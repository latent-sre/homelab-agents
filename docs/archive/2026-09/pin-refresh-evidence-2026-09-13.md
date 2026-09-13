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
