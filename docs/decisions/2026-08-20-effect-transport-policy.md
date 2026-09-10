# Effect transport policy: retire the broker mandate, gate on the host's own control

- **Date**: 2026-08-20
- **Status**: accepted
- **Owner**: `agents/homelab-engineer.md` ("Executing an approved effect")
- **Supersedes**: the Tier 2/3 broker mandate introduced by SAFE-P1-005 (`f4741c7`, 2026-07-31)
  and elaborated by GATE-001 (`d02bd33`, `1c8845e0`, 2026-08-09)
- **Closes**: roadmap item GATE-005

## Context

> **Naming.** The 2026-08-20 incident below happened under the key `homelab-platform`; the
> agent was renamed to `homelab-engineer` on 2026-08-30 (PR #165). Dated narration keeps the
> key that was live when the events occurred, so the record stays reconstructable; the Owner
> line and the decisions below use the current key, because they govern now.

`homelab-platform` refused an explicitly approved, reversible Tier 2 build. The session held a
complete effect packet, a successful backup, the user's approval of that exact target and command,
a clean preflight, a stated rollback, and access to a host-native managed command-approval path.
It refused anyway, because the agent named exactly one sanctioned transport for agent-mediated
execution and that transport was not installed.

Three lines carried the mandate: Tier 2 bound "any agent-mediated execution ... through the broker
below"; Tier 3 called "the same effect-bound broker ... mandatory"; and the absence paragraph
defined one continuation — stop and hand the command to the operator.

## What the evidence said

The mandate was never argued on its own merits. `f4741c7` is a batch sweep landing nine controls at
once; the broker is one clause in a six-item bullet. Its rationale lives in
`docs/archive/2026-07/p0-p1-safety-controls-outcomes-2026-07-31.md:33` (SAFE-P1-005, retired to Git history), and the same
document records two limits that decide this question:

- `:134` — "No live home-lab effect was brokered. Broker tests use temporary helper executables,
  keys, and ledgers only." The control has never been exercised against a real effect.
- `:136` — "The broker uses an HMAC because public-key/operator-service infrastructure was out of
  scope. It is enforceable only when the signing key and replay ledger are genuinely outside agent
  identity." It was the mechanism that was cheap to build, not a considered choice among
  alternatives.

No mediator, key, or ledger was ever configured on the estate. The mandate had been refusing work
on behalf of a control that never existed.

GATE-001 did not re-litigate it. That round arrived *from* an estate audit where broker-absence
friction was already logged as recurrence 2 (ledger `lc_6b36cf5d`), and its response was to make
the refusal better-mannered — stated once per session, never a per-change security finding — rather
than to ask whether the mandate was right. The rule also reached
`docs/decisions/2026-07-31-ai-graph-engineering.md:358` as graph invariant 6, "Every effect routes
through the broker."

## Decision

Retire the broker from `homelab-engineer` entirely. An approved Tier 2 or Tier 3 effect executes
through **a trusted host-native managed gate** — a control that interposes a per-invocation human
decision on the exact argv, such as Claude Code's permission prompt or Codex's command-approval
path. With no such gate, the agent stops and gives the operator the exact command.

The boundary the broker defended is preserved by naming the property rather than the product: the
decision to execute is held by an identity the agent cannot forge. A managed gate satisfies that.
What the broker adds beyond it — executable digest, expiry, cryptographic one-shot replay binding —
defends against replay and substitution in unattended pipelines, which is not this estate.

Consequences:

- `scripts/effect_broker.py` and its tests remain. No agent names it, so it left
  `RUNTIME_CONTROL_WIRING` in `scripts/validate_fleet.py`; it keeps its own typed-evidence check
  through `RUNTIME_EVIDENCE_PRODUCERS`. Deleting it is a separate decision nobody has made.
- Graph invariant 6 in `docs/decisions/2026-07-31-ai-graph-engineering.md` is **not** updated here.
  That record describes a graph control plane that has no runtime, and editing an accepted decision
  record to match a later one is how provenance rots. GRAPH-004 owns the reconciliation.
- The `Instrument:` declaration slot becomes `Transport: <managed gate|operator handoff>`.
  `Instrument: fresh request required` asserted that a signed broker request must exist, which is
  meaningless with no broker — the state GATE-005 asked someone to define. `packet_lint.py` mirrors
  the new vocabulary and `tests/test_packet_lint.py` still fails on drift from the agent file.
- The gate-owner closed set replaces "plugin effect-broker transport" with "operator handoff".

## Controls deliberately preserved

Retiring the transport does not retire the gate. All of these are unchanged or restated:

- explicit user approval for the exact target and exact command;
- the user-visible effect ("What you will see"), blast radius, verification, and exact rollback;
- a fresh preflight before execution, and a **new** request when material drift is found between
  approval and run;
- no argument or scope change between approval and execution — an added flag is a new effect;
- Tier 3's proven backup or recovery path and out-of-band access, established before the approval
  is acted on, and never consolidating even for an identical retry;
- no unrestricted shell fallback, no wrapper shell, no pre-approved alias standing in for the
  approved argv, and no routing around a gate that is present;
- a gate the operator has bypassed session-wide, or a command already blanket-allowlisted, grants
  no decision and counts as absent.

## Verification

- `python3 scripts/validate_fleet.py` — green; 182 adapters regenerated byte-exact.
- `python3 scripts/run_tests.py` — 991/991.
- Vocabulary drift detector proven non-vacuous by mutation: changing `TRANSPORT_STATES` away from
  the agent's declaration fails `test_gate_vocabularies_match_their_canonical_agent_declaration`.
- Offline oracle proof: the pre-change refusal answer **fails**
  `gate-managed-gate-executes-once` on five assertions while the corrected answer passes, and
  `gate-no-transport-operator-handoff` still rejects an agent that executes with no gate present.
- **Not run**: the paid behavioral lane. The two new contracts are written and their oracles are
  proven to fire offline, but no model session has been bought against them. Buy it with
  `python3 scripts/eval_behavioral.py --case 'gate-*' --runs 3 --model sonnet --clean-room`.

## Amendment 2026-09-01

The consequence above called deleting the broker "a separate decision nobody has made." That
decision was made 2026-09-01: `scripts/effect_broker.py` and `tests/test_effect_broker.py` were
retired, since no agent had named the broker since this record shipped. The typed-evidence check
in `RUNTIME_EVIDENCE_PRODUCERS` now covers only `scripts/run_state.py` and
`scripts/verification_sandbox.py`.

A further correction the same day: `scripts/run_state.py` and `scripts/verification_sandbox.py`
were themselves retired 2026-09-01 (operator ruling: the audience is a single home-lab operator),
and `RUNTIME_EVIDENCE_PRODUCERS`/`RUNTIME_CONTROL_WIRING` were removed from `validate_fleet.py` in
the same change — the sentence above named a coverage set that survived less than a day. The
Verification section's `python3 scripts/run_tests.py` line stands as a dated record of what ran on
2026-08-20; the equivalent check today is `python3 -m unittest discover -s tests`
(`scripts/run_tests.py` was retired 2026-09-01).

A 2026-09-02 correction to the same section: the behavioral harness retired that day under the
single-operator audience decision. The "Not run: the paid behavioral lane" line above stands as a
dated record of what was still owed on 2026-08-20; that run will not be bought. The two contracts'
offline-proven oracles retired with `evals/behavioral/contracts.json`; the routing suite is the
remaining paid instrument for this decision's claims.
