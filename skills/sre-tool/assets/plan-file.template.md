<!-- Plan file — reuse an existing orchestrator plan; instantiate this only when the full pipeline
     needs one and none exists (default .agents/plan.md), before Phase 1. Omit inapplicable sections;
     preserve applicable authorization, gates, counters, and the safe resume point.
     ORCHESTRATOR-OWNED: builders write only their own progress shards. Keep current state clear;
     compact superseded narration into outcomes and accessible evidence references. Retain material
     decisions and reasons, authorization, failed attempts/results, unresolved risks, counters,
     and the next safe action. Compaction must not reset limits or erase a live decision. -->

# Plan — <tool name>

## Safe resume point

<!-- Keep current: next safe action, work in flight, possibly half-written files, and what to
     verify before continuing. A successor should not have to reconstruct the event log. -->

## Mission transaction

<!-- reference the exact transaction in the existing mission block — Phase 4 runs that transaction -->

## Cadence contract

- **Commit policy**: <!-- required: e.g. "commit at every green batch boundary"; without an explicit grant, never commit -->
- **Pause points / user gates**: <!-- user-requested or required by applicable phases/repository;
     routine design adds no approval pause; reuse decisions already made -->

## Gate status

| Gate | Status (open / approved / n-a) | Evidence |
|---|---|---|
<!-- one row per named gate; approval evidence is a pointer to the user's words, never inferred -->

## Counters (survive compaction — the caps reset silently otherwise)

| Builder / component | Relaunches used (cap 1) | Fix→re-review rounds (cap 2) |
|---|---|---|

## Parked suspicions — never shown to the reviewer

<!-- defects the orchestrator suspects, recorded BEFORE the review returns; reconcile after.
     A reviewer handed a hypothesis can only echo it. -->

## Batch & checkpoint log

<!-- Retain consequential checkpoints: builder, assigned/completed boundary, evidence and gaps.
     Summarize superseded status updates; keep failed attempts/results needed to avoid repetition. -->
