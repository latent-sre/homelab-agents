# Decision: the fleet ships to one home-lab operator

**Status:** Accepted 2026-09-02 (operator ruling).

## What was decided

`sde-agents` is a tooling kit for one person who runs a home lab and uses AI coding agents to
help. It is packaged well enough to hand to strangers who run the same kind of lab, but it is not a
platform for a team, and machinery that serves someone developing this repository does not ship
to that operator.

The ruling answers the question the 2026-09-01 scope review left open
(`../archive/2026-08/agent-skill-full-audit-findings-2026-08-30.md`, retired to Git history, is the complementary defect
audit; the scope review's evidence is the operator's artifact of that date and the harness cuts
that followed it in PRs #168, #169, and #170).

## What it closes, and why

Each of these left `fleet-roadmap.md` on 2026-09-02 on this ruling, not on acceptance evidence.
Their full history is in `../archive/2026-09/roadmap-history-2026-09-01.md`.

- **CTX-002 — met by construction.** The roster the ruling implies (5 agents, 16 model-visible
  skills) measures 6,946 characters of skill descriptions against the 8,000-character host budget,
  with no description edited. The trim the item planned is unnecessary; the doctor's headroom
  check is the closing evidence and runs in the roster change.
- **LEARN-002 — won't-do.** Its thirteen behavioral contracts measure `self-improve-loop`, a
  maintainer skill that leaves the shipped fleet. Paid batches against a skill no operator loads
  are not evidence about the product.
- **HANDOFF-001 — won't-do.** The digest-bound Work Order between `homelab-engineer` and
  `sde-fullstack` had one consumer, its own eval fixture. For one operator, onboarding happens in
  place or is handed to the builder with the plan file. The recurrence that motivated it (issue #60,
  a builder losing onboarding context three times) is answered by not splitting the work across
  two contexts.
- **LADDER-002 — won't-do.** `eng-ladder` routes work between three seniority rungs that one
  operator occupies alone; the roster cut deletes it, so neither repair option is bought and the
  `ladder` routing cluster retires with the skill.

## What lost

Keeping the fleet general enough for a team, with typed handoffs, a learning ledger, and a
seniority ladder, lost to the reader who actually exists. The mechanisms were built well; they had
no consumer.

## What would reopen this

A second regular operator of the same installation, or a measured routing or behavior regression
in the surviving fleet that the removed mechanism demonstrably prevented. Reopening restores the
mechanism from git history with its tests; nothing here is one-way.

## Amendment 2026-09-02

A direct consequence of this ruling, decided the same day: the behavioral evaluation harness
(`scripts/eval_behavioral.py`, `scripts/packet_lint.py`, `evals/behavioral/contracts.json`)
retired. The hooks (`scripts/readonly-guard.py`, `scripts/live-effect-gate.py`) enforce what
matters at runtime; the grader produced most of this year's false-red churn and no shipped role
ran it. EVAL-011 and ORACLE-019 closed won't-do with it — both were entirely about the retired
runner's grading. Every other roadmap item, decision, and doc that promised or cited a behavioral
contract run was amended in the same pass to note the retirement and fall back to routing evals
and the probe.
