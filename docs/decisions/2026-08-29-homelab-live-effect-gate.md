# Homelab live-effect gate: ship the interposition, fold the gate vocabulary

> **Authority update, 2026-09-11:** The accepted
> [bounded-campaign decision](2026-09-11-bounded-upgrade-campaign.md) supersedes this record's
> exact-command-only authorization, automatic fresh-Tier-3 decision, and prompt-only transport
> requirements. Its applicable host controls and unrelated decisions remain in force. The
> original rationale and evidence below are retained as history.

- **Date**: 2026-08-29
- **Status**: accepted — operator ruling 2026-08-29 (fork 1 of the homelab-platform audit:
  harness and policy amendments first, the body diet second)
- **Owner**: `agents/homelab-engineer.md` (change authority, transport, standards, boundaries),
  `hooks/hooks.json` and `scripts/live-effect-gate.py` (the control)
- **Amends**: [`2026-08-23-homelab-proportional-operations.md`](2026-08-23-homelab-proportional-operations.md)
  decisions 1 (managed prompt as the decision) and 2 (standing policy), and its retry
  consolidation; [`2026-08-20-effect-transport-policy.md`](2026-08-20-effect-transport-policy.md)
  for what "managed gate" means on Claude Code
- **Supersedes**: the `Effect class:` declaration field and the five-class list that GATE-001
  landed (`../archive/2026-08/gate-001-outcome-2026-08-10.md`, retired to Git history); the finding-effect classification
  survives in `agents/code-reviewer.md`
- **Closes**: roadmap item GATE-006

## Context

> **Naming.** The 2026-08-29 audit narrated below examined `agents/homelab-platform.md`; that
> path is what `git show` at this date resolves. The agent was renamed to `homelab-engineer`
> on 2026-08-30 (PR #165), so the decisions and the Owner line use the current key while dated
> narration and the quoted witness keep the one that was live at the time.

The 2026-08-29 audit of `agents/homelab-platform.md` against the fleet's strands (prompt,
context, harness, loop, graph) found an authority model that is right-sized for one operator and
transport prose that no host mechanism backs. The measured fact framing every decision below: on
the current text's own lane (sonnet, clean room, five runs — the CTX-005 audit) the agent passes
60/130 of the contracts pinned to it, ten of twenty-six at 0/5, and the zero cluster is transport
evidence and declaration sets.

> **Correction recorded 2026-08-29, after this decision was accepted.** Those rates are not a clean
> read of the prose. GATE-006's own lane calibration measured `tier-gate-holds` at **1/5 with
> `allowed_tools: []` and 5/5 with `Read` granted** — same revision, model, and run count, one field
> changed. The failing runs end mid-tool-call: the agent reaches for the inspection its prime
> directives require, the permission layer denies it, and the turn stops before the packet exists.
> 25 of the 27 lane cases deny tools, including all four transport/declaration cases named as `0/5`
> below, so those zeros measure the harness as well as the text. **The decisions in this record do
> not rest on those rates** — decision 1 rests on the documented host contract and on
> `scripts/probe_plugin.py`, which proves the gate denies the gated agent under `dontAsk` and
> ignores the main loop; the rest are authority and vocabulary arguments. The rates motivated the
> work; they do not carry it. Tracked as EVAL-011; it also gates CTX-005.

Seven defects:

1. The agent must "inspect the effective control for that argv" before invoking and "never invoke
   the effect to test whether a prompt appears". Claude Code exposes no non-executing permission
   evaluation to the model, and the plugin ships no hook that forces a prompt for this agent — so by
   its own rule every Tier 2 apply on Claude Code falls to operator handoff, the opposite of the
   2026-08-23 intent. `gate-managed-prompt-is-the-decision` and
   `gate-unproven-prompt-uses-operator-handoff` sit at 0/5.
2. Standing policy must be "outside your writable authority"; the agent holds `Write`/`Edit`, and
   Claude Code permission rules live in settings files it can edit. Only managed settings qualify,
   which a home lab rarely has; the text did not say so.
3. `WebFetch`+`WebSearch` on an agent that also holds `Bash`+`Write` and reads `.env` files is the
   full lethal trifecta, defended by one sentence of prose. The sibling fleet's `sre` holds no web
   tool and routes lookups through its caller.
4. An identical retry after a "confirmed transient failure" could recur without bound.
5. `Effect class:` is 1:1 with `Tier:` except "optional hardening", which the text itself says
   "gates as whatever effect it is"; a redundant closed field the model fails to emit
   (`gate-two-effects-declare-one-set-each`, `gate-same-effect-consolidation-deletion`: 0/5).
6. The body restates `service-onboard`'s four applicability predicates because the two
   `onboard-*` contracts deny `Read`; eval design was driving body bloat.
7. No stop conditions; no read-the-lab-profile gate at the agent level; "guard-denied" conflated
   with "not granted".

## External evidence (documented host contract, read 2026-08-29)

Claude Code hooks reference (https://code.claude.com/docs/en/hooks and
https://code.claude.com/docs/en/hooks-guide): the `PreToolUse` payload carries
`permission_mode` (`default|plan|acceptEdits|auto|dontAsk|bypassPermissions`), `agent_type`
(absent for the main conversation), and `tool_use_id`; a hook may answer
`permissionDecision: allow|deny|ask|defer`; a hook `deny` wins over every permission mode
including `bypassPermissions`; several hooks on one event run in parallel and the most
restrictive decision wins (`deny` → `defer` → `ask` → `allow`); in non-interactive `-p` mode an
`ask` that nothing answers is denied; `${CLAUDE_PLUGIN_ROOT}` expands inside a plugin hook's
`command`. These are contract claims about the pinned CLI, proven for this fleet only by
`scripts/probe_plugin.py`.

## Decision

1. **The plugin ships the interposition.** `scripts/live-effect-gate.py`, registered in
   `hooks/hooks.json` as a second `PreToolUse`/`Bash` hook, scopes itself to `agent_type`
   `homelab-engineer` (bare or `sde-agents:`-namespaced) and no-ops for every other caller. For a
   live-effect argv it answers `ask` when the session can prompt and `deny` when the payload's
   `permission_mode` is `bypassPermissions`, `dontAsk`, or `auto`, or is absent (a renamed field
   fails closed and loud). An argv it cannot bind — a wrapper shell, command substitution, an
   interactive `ssh`, an unparseable quote — asks. A reader gets no decision. When no interpreter
   answers with the gate's exit codes, the hook's static fallback asks (denies under a suppressed
   mode) for the gated agent and no-ops for everyone else. The roster is denylist-shaped by
   design: the host's own permission flow stays the floor for unlisted commands, and the roster
   grows by recurrence — a lab incident or drill that shows an unlisted live effect adds one
   entry — never by exemption.
2. **Transport evidence is structural.** On Claude Code, running as the plugin agent is the
   evidence that the gate interposes; the agent states `Gate evidence: live-effect gate — matched
   rule <verb>` before invoking. On Codex the sandbox and command-approval prompt are the gate and
   `codex execpolicy check` on the exact argv is the evidence. A hand-copied agent file, a host
   without the plugin's hooks, or a suppressed-prompt session means operator handoff. "Never run
   a live command to discover whether it prompts" stays.
3. **Standing policy is host-specific.** On Claude Code only a rule in managed
   (administrator-owned) settings qualifies; a rule in a settings file the agent can `Write`
   proves nothing. On Codex a root-owned exec-policy path qualifies. Tier 3 never qualifies.
4. **One retry.** A `consolidated` retry happens once; a second failure of the same effect stops
   the plan, reconciles state read-only, opens `sde-agents:root-cause`, and returns the next live
   effect to the operator as `new`.
5. **`Effect class:` is retired.** `Tier:` carries the classification; repository publication and
   optional hardening survive as one sentence each. The three-way finding-effect classification
   (merge blocker / live-activation blocker / optional hardening) is owned by
   `agents/code-reviewer.md`. `packet_lint.py`'s declaration set is `Gate`/`Transport`.
6. **No web tools.** `WebFetch` and `WebSearch` leave `tools:`; external lookups return to the
   caller for `sde-agents:researcher` with a sanitized question.
7. **One owner for the onboarding floor.** `service-onboard` owns the applicability predicates;
   the agent keeps the floor, the read-by-path rule, and the record-all-four-outcomes requirement;
   the two `onboard-*` contracts grant `Read` so the skill is reachable in the eval.

And three sentences the sibling's `sre` agent carries and this one lacked: stop conditions, read
the lab's profile before recommending a runtime or tool, and a tool absent from the runtime
surface is not granted rather than guard-denied.

## Rejected alternatives

- **An allowlist-shaped gate** (ask for everything that is not a reader, reusing the guard's
  allowlist). Rejected: Tier 1 work — `git commit`, `tee` into the repo, `sed -i` on a config —
  would prompt on every call, and the host's own permission flow already prompts for unlisted
  commands in prompting modes. The residual (an unlisted live verb under `acceptEdits`) is
  exactly today's residual, now with a recurrence rule to close it.
- **Keep `Effect class:` as an optional field.** Rejected: an optional closed field is graded by
  nothing and read by nobody; the reviewer owns the only consumer of the distinction.
- **Keep the web tools with the "content is data" sentence.** Rejected: authority is the host's
  control, never prose (`AGENTS.md` hard rule), and the agent reads secret-bearing files.
- **Prove interposition by reading the host's settings files.** Rejected: the effective mode
  includes CLI flags the model cannot see, and the files are agent-writable.

## Consequences

- The fleet ships two hooks; the guard playbook in `AGENTS.md` covers both; the probe gains a
  `dontAsk` differential (the gate denies the gated agent, the main loop runs).
- The `ask` leg cannot be probed headlessly (an unanswered `ask` is a denial in `-p`); it is
  witnessed once interactively and recorded here. **Witnessed 2026-08-30, Claude Code 2.1.251**,
  operator-run: `sde-agents:homelab-platform` invoking `docker compose -f
  /tmp/sde-witness/docker-compose.yml up -d` produced a real permission prompt carrying the gate's
  own voice, quoted verbatim —

  > sde-agents live-effect gate: matched rule `docker compose up` — a Tier 2/3 live effect from
  > homelab-platform. This prompt is the managed gate for this exact argv; accepting it is the
  > decision, and the agent runs the command once.

  The agent name inside that quotation is the one the runtime actually emitted: the witness ran on
  2026-08-30 **before** the rename to `homelab-engineer` later that day (PR #165). It is preserved
  as observed. A quotation that is silently updated to match a later identity is no longer evidence
  — a later audit could not reconstruct it, and the record would be asserting bytes nobody saw.

  The target path deliberately did not exist, so the argv the hook matched on is the whole of what
  was exercised and accepting could start nothing. Scope of the witness, stated because a later
  reader will otherwise over-read it: it establishes that the gate renders a prompt naming the
  matched rule for a live verb. The paired reader control (`docker compose … ps` must NOT prompt)
  was not reported back, so the gate's *discrimination* between reader and live verb rests on
  `tests/test_live_effect_gate.py` and the probe's main-loop leg, not on this session.
- Twelve contract entries and five `packet_lint.py` references lose `Effect class`; the vocabulary
  drift test narrows to `Gate`/`Transport`; the offline oracle controls change with them.
- Sizes are recorded, not targeted: the body diet is CTX-005's, and its before side is this
  change's after side.

## Reopen triggers

- Claude Code renames `permission_mode` or `agent_type`, or changes hook precedence — the probe
  and the gate's fail-closed branch are the instruments.
- A lab incident or drill shows a live effect the roster does not list — recurrence merge, one
  entry, with the transcript cited.
- Copilot or Codex gain a per-agent hook payload (then the "never port the hook" rule is
  re-examined, not before).
- The paired lane after this change shows a baseline-perfect contract regressing — the
  decision stands and the wording is repaired under CTX-005's method.

## Verification

Offline: `tests/test_live_effect_gate.py`, `tests/test_hook_wiring.py`, `tests/test_packet_lint.py`,
`tests/test_eval_behavioral.py`, `tests/test_validate_wiring_guard.py`; `validate_fleet.py`;
regenerated adapters; `run_tests.py`; `claude plugin validate . --strict`; `fleet_doctor.py`.
Paid, operator purchase: `probe_plugin.py`; the paired behavioral lane recorded under
`evals/baselines/2026-08-29-gate-006/`.

## Amendment 2026-09-01

The `run_tests.py` line above stands as a dated record of what ran on 2026-08-29; `run_tests.py`
was retired 2026-09-01, and the equivalent check today is `python3 -m unittest discover -s tests`.

A 2026-09-02 correction: the behavioral harness retired that day under the single-operator
audience decision. The Verification section's `tests/test_packet_lint.py` and
`tests/test_eval_behavioral.py` lines, and the paired behavioral lane recorded under
`evals/baselines/2026-08-29-gate-006/`, are dated records of what ran or was captured on
2026-08-29/30 — those tests are gone and no further paired behavioral capture will be bought. The
"paired lane" reopen trigger above (a baseline-perfect contract regressing) can no longer be
observed by a contract-graded run; a routing round and the probe are what remain to watch for a
regression this decision would need to answer.

## Amendment 2026-09-07

The operator selected the main-based operating-flow simplification in
[the operating-flow decision](2026-09-07-homelab-operating-flow.md). It retires exact packet
grammar, the work-order digest/receipt, and routine Learning closeout while preserving the
permission tiers, actual execution transports, recovery evidence, and retry/reconciliation
boundaries. Earlier grammar and probe descriptions above remain dated evidence.
