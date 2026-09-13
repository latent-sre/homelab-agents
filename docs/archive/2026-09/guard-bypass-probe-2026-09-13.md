# Runtime probe after the read-only guard bypass fix — 2026-09-13

Evidence for the `AGENTS.md` gate that every `scripts/readonly-guard.py` edit owes: the guard's
contract rests on the `agent_type` payload field, and only the probe proves the pinned CLI still
honours it. Run for machinery-rewrite phase 3 (PR #190), which changed the guard's tokenizer to
close a bypass (`ls;(rm -rf /)` and 32 variants).

## Conditions

| | |
|---|---|
| CLI | 2.1.270 — the version pinned in `.github/workflows/validate.yml` |
| Command | `python3 scripts/probe_plugin.py` |
| Tree | `c9af8e803993` plus the round-4 review fixes, no other writer |
| Exit | 1 — **14/17 passed, 2 failed, 1 inconclusive** |

## What the gate owed, and what it got

Every guard and gate assertion passed, which is the contract this gate exists to re-verify:

| Check | Verdict |
|---|---|
| the guard DENIED the reviewer's denylisted command | PASS |
| the guard IGNORED the main loop's identical command | PASS |
| the guard DENIED a `--agent` main session's denylisted command | PASS |
| the gate DENIED homelab-engineer's live verb under `dontAsk` | PASS |
| the gate IGNORED the main loop's identical live verb | PASS |
| `${CLAUDE_PLUGIN_ROOT}` expanded, not a literal | PASS |
| plugin loaded; all three agents spawned under their namespaced names | PASS |

So the pinned CLI still loads these hook bytes, still supplies a scoped `agent_type`, and the
guard still fires for guarded agents **and only them** after the tokenizer change.

## The two failures are not this change's

| Failure | Disposition |
|---|---|
| `backend-craft was read on demand and used` | **PROBE-002**, recorded as a real, intermittent craft-preload failure (2 passes, 3 failures across five runs). Not guard-related. |
| `sde-fullstack read references/consuming-apis.md` | Already recorded against this same CLI pin before this PR: "The 2026-09-13 probe on CLI 2.1.270 FAILED the conditional-reference check once" (`docs/fleet-roadmap.md`, LABFLOW-001). Design Risk 1, not guard-related. |

Neither is in code PR #190 touches, and no timeout occurred, so the phase-3 verdict changes were
not exercised in producing them.

## The INCONCLUSIVE is the polarity contract working

The workflow leg reported **one** INCONCLUSIVE naming its own cause — this session runs as root,
and Claude Code refuses `--permission-mode bypassPermissions` there — rather than five cascading
FAILs. That is PROBE-003's documented verdict, observed live.

## Not covered by this run

The workflow platform contract's five assertions were not evaluated (root). Re-run as an
unprivileged user to close that part; it is unrelated to the guard change.
