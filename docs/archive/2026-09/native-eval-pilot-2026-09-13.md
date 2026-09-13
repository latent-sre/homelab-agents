# Native `claude plugin eval` pilot: does `tool_used: Agent` see a namespaced spawn? 2026-09-13

Scope: the one live run the machinery-rewrite decision names as phase 4's precondition
(`docs/decisions/2026-09-13-machinery-rewrite.md`, "What retires") — a single native case with a
`tool_used` grader on `Agent` whose `input_match` accepts a plugin-namespaced `subagent_type`.
Nothing here migrates the routing suite or touches `scripts/eval_routing.py`. Tree under test:
`d288a52ae223` on `claude/machinery-rewrite-fresh-ar08n6`, plugin `sde-agents` 0.7.4.17 loaded
from the repository root.

## Answer

**Yes.** The native `tool_used: Agent` grader observes a plugin-namespaced subagent spawn. Across
two runs of three, the grader passed in five of six runs, and in the three runs whose traces were
preserved the observed input was `"subagent_type": "sde-agents:homelab-engineer"` every time —
never the bare name. The one failing run did not delegate at all (`Agent called 0x`), which is
the headless under-delegation `evals/README.md` already documents, not a grader miss.

## The case

`evals/native-pilot/routes-to-homelab-engineer/` — a directory that does not collide with the
existing `evals/{routing,baselines,conformance}` contents, pointed at with `--eval-dir`.

- `prompt.md` — the body is byte-identical to `pos-diagnose-idle-lab-failure` in
  `evals/routing/investigation.json` (checked by a script comparing the two strings). Frontmatter:
  `max_turns: 15`, `timeout_seconds: 300`, `allowed_tools: [Read, Glob, Grep, Skill, Agent]`.
- `graders/agent-homelab-engineer.md` — `type: tool_used`, `tool: Agent`,
  `input_match: '"subagent_type"\s*:\s*"(?:sde-agents:)?homelab-engineer"'`.
- `graders/no-agent-code-reviewer.md` — the same shape with `min: 0`, `max: 0`, `arm: both`, and
  the regex naming `code-reviewer`, a cluster sibling that must not fire.

**Deviation from the brief.** The brief asked for a positive case in `investigation.json` whose
`expect_fires` names an agent. There is none: both positives there name `root-cause`, which is a
skill, and no routing cluster carries an agent-only positive (26 were retired 2026-08-17,
`evals/README.md`). The chosen case is the one investigation positive that spawned an agent in
every stored headless run — `homelab-platform`, since renamed `homelab-engineer`, 3/3 in both the
before and after captures under `evals/baselines/2026-08-18-ctx-002/*/investigation/` (CLI
2.1.235, sonnet, clean room). Its `expected_output` names homelab-engineer's tiers as the
destination. The Agent grader therefore targets `homelab-engineer`, not the case's declared
`root-cause`.

## Exact command

Run from the repository root (the plugin root), CLI `2.1.270 (Claude Code)`, model pinned to
`sonnet` to match the routing runner's doctrine; every run reported `claude-sonnet-5` in its trace.

```bash
claude plugin eval . --eval-dir evals/native-pilot --ablation none --runs 3 -j 3 --no-publish --model sonnet --max-cost-usd 3 --json <path>.json
```

The second invocation added `--keep-temp` so the per-run traces survived long enough to read the
observed `subagent_type`; nothing else differed.

## Per-run grader verdicts, from the `--json` documents

| Attempt | Started (UTC) | Run | Turns | `agent-homelab-engineer` | `no-agent-code-reviewer` | Score |
|---|---|---|---|---|---|---|
| 1 | 17:39:54 | 1 | 14 | FAIL — `Agent called 0x (expected 1..∞)` | PASS — `Agent called 0x (expected 0..0)` | 0.5 |
| 1 | 17:39:54 | 2 | 3 | PASS — `Agent called 1x` | PASS | 1.0 |
| 1 | 17:39:54 | 3 | 1 | PASS — `Agent called 1x` | PASS | 1.0 |
| 2 | 17:41:40 | 1 | 2 | PASS — `Agent called 1x` | PASS | 1.0 |
| 2 | 17:41:40 | 2 | 2 | PASS — `Agent called 1x` | PASS | 1.0 |
| 2 | 17:41:40 | 3 | 4 | PASS — `Agent called 1x` | PASS | 1.0 |

Attempt 1: case score 0.833, pass rate 2/3, exit 1 (default `--threshold 1.0`), 56 s,
`costUsd` 0.638, `partial: false`. Attempt 2: case score 1.0, 3/3, exit 0, 74 s, `costUsd` 0.606,
`partial: false`. Every run had `error: null`.

Observed `Agent` inputs in attempt 2's traces (`out/trace.jsonl`, read before the kept temp
directories were removed):

| Run | `Agent` calls in order | Result |
|---|---|---|
| 1 | `sde-agents:homelab-engineer` | launched |
| 2 | `sde-agents:root-cause`, then `sde-agents:homelab-engineer` | first errored (see below), second launched |
| 3 | `sde-agents:homelab-engineer` | launched |

Runs 1 and 2 also invoked `Skill` with `sde-agents:root-cause`; run 2 tried it as an agent first.
Attempt 1's traces were not preserved (no `--keep-temp`), so what its non-delegating run did for
14 turns is unrecorded.

## Surprises worth carrying into phase 4

- **The error text is itself evidence of namespacing.** The failed `Agent(sde-agents:root-cause)`
  call returned `Agent type 'sde-agents:root-cause' not found. Available agents: claude, Explore,
  general-purpose, Plan, sde-agents:application-security-auditor, sde-agents:code-reviewer,
  sde-agents:homelab-engineer, sde-agents:multi-agent-architect, …` — the fleet registers under
  the prefix only, so a migrated grader can use `(?:sde-agents:)?` for tolerance but should never
  expect the bare form to appear.
- **`tool_used` counts calls, not successful spawns.** The errored call above is an ordinary
  `tool_use` block in the trace. It did not match this case's regex, so the pilot did not observe
  whether an errored spawn that *does* match would count — the docs describe the grader as counting
  calls whose input matches, with no success condition. A migrated suite that grades a spawn should
  treat this as unverified until one run shows it either way.
- **No trust prompt fired**, with or without `--trust-plugin`: this worktree path already carried
  `hasTrustDialogAccepted: true` in `~/.claude.json` from the interactive session that opened it.
  Under `--json` an untrusted directory is refused with exit 1 rather than prompted, so a CI or
  fresh-checkout run needs `--trust-plugin`.
- **Results land inside the eval directory**, at `evals/native-pilot/results/<timestamp>/` with
  `aggregate-result.json` and `report.html`, even when `--json <path>` writes the same document
  elsewhere. That directory is now in `.gitignore`. The report was kept local (`--no-publish`).
- **Neither grader was excluded.** Under `--ablation none` both `tool_used: Agent` graders
  were `scored: true` in every run; the `arm: both` on the negative is therefore inert here and
  matters only under `with-without`, where a `tool_used: Skill` grader would otherwise become an
  indicator.
- **`--keep-temp` on Windows cannot seal the kept directories** — the CLI warns that directory
  modes do not restrict access, tells you to read only `out/`, and prints the removal command. The
  three directories were read for `out/trace.jsonl` and removed in this session.
- **Cost and wall clock:** about $0.20 per run at sonnet, roughly a minute for three runs at
  `-j 3`; the $3 ceiling was never approached.

## What this does not settle

- Whether the native runner's delegation rate is higher than the stopgap runner's on the same
  prompts: 5/6 here against 6/6 in the two stored captures is one case, one model, and the
  stopgap's captures ran clean-room on a different CLI; no paired comparison was made.
- The converter and recorder the decision record keeps as the fleet's thin layer; neither exists
  yet.
