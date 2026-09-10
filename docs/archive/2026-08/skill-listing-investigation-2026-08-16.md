# Skill-listing budget investigation — 2026-08-16

**Status:** dated evidence record for roadmap items CTX-002, CTX-003, and CTX-004. This archive
captures the mechanism, the live probes, the mitigation calibration, and the preload/body
footprint so the remediation passes start from committed evidence rather than a session's
memory. It adds no work of its own.

**Conditions.** Claude Code CLI 2.1.233 (native binary, string-extracted constants), plugin
loaded from the working tree via `--plugin-dir .`, remote container (claude.ai/code environment
with its bundled-skill set), 2026-08-16. Live sessions were one-shot headless `claude -p` runs;
models named per probe. Trim and settings experiments ran in a scratch copy of the checkout,
never the working tree.

## Mechanism [verified — binary constants + live behavior]

The model-visible skill listing is budgeted in characters:

- budget = context-window tokens × 4 chars/token × `skillListingBudgetFraction` (default 0.01) —
  **exactly 8,000 chars on a 200k-token model**; per-description cap
  `skillListingMaxDescChars` = 1536; env override `SLASH_COMMAND_TOOL_CHAR_BUDGET`.
- Over budget, entries are **not dropped**: plugin and user entries degrade to bare `- name`
  lines with no description, greedily by priority. **Anthropic-bundled skills are exempt and
  charge the budget first.** The only signal is a debug-log warning.
- Workflows list exactly like skills (`- plugin:name: <meta description>`) and spend the same
  budget. `disable-model-invocation: true` plugin skills are absent from the listing on this CLI
  (both of this fleet's flagged skills unlisted — the 2.1.212-era "flag ignored for plugin
  skills" caveat is half-stale; invocability remains unprobed).
- OpenAI Codex documents the same default: its skills list gets min(2% of context, 8,000 chars
  when the window is unknown); it shortens descriptions first, then omits entries [sourced —
  developers.openai.com/codex/skills via search snippets; domain egress-blocked here].

## Live listing state by model [verified]

Fleet footprint at the time of measurement: ~11.9k chars across 19 entries (18 non-DMI skills +
the `deep-review` workflow), per `scripts/fleet_doctor.py repository.skill-listing-budget`.

| Session model | Listing state |
|---|---|
| Haiku 4.5 (200k window) | **18 of 19 entries bare names**; only `deep-review` kept its description |
| Sonnet 5, Fable 5 (larger windows) | all 19 entries full |

This also resolves the LADDER-002 investigation's unexplained observation (full description
visible at CLI 2.1.231 despite ~11k listing volume): that probe ran on a large-window model,
where the same fraction buys a larger character budget.

## Routing consequence [verified — behavioral A/B, demonstration scale]

Prompt: `pos-learning-repeated-failure` from `evals/routing/continuous-improvement.json`,
verbatim — a self-improve-loop positive that never names the skill. Haiku 4.5, two runs per
condition, firing = a `Skill` tool call targeting `sde-agents:self-improve-loop` in the stream
(text mentions do not count, per the routing suite's own rule).

| Condition | Fires |
|---|---|
| Default budget (entry is a bare name) | **0/2** |
| `skillListingBudgetFraction: 0.05` (entry fully described) | **2/2** |

n=2 per condition is a demonstration of the mechanism, not a routing benchmark; CTX-002's
acceptance still owes the paired cluster runs.

## Mitigation calibration [verified]

Project-scope `.claude/settings.json` in the consuming checkout, haiku 4.5, untrimmed listing:

| `skillListingBudgetFraction` | Result in this container |
|---|---|
| 0.01 (default → 8,000 chars) | 1 of 19 described |
| 0.02 (16,000 chars) | 16 of 19 described (`security-audit`, `self-improve-loop`, `upgrade-campaign` bare) |
| 0.05 (40,000 chars) | **all 19 described** |

The `--settings <file>` flag path was not separately confirmed; the project-settings path is the
proven transport and matches how a consuming lab repo would apply it.

## Trim simulation [verified — and the load-bearing surprise]

Mechanical first-sentence trim of every skill and workflow description in a scratch copy
(~3.0k chars of descriptions, ~3.9k listing total — well under the fleet's own 8,000 worst
case), default budget, haiku 4.5: **only 10 of 18 entries kept descriptions**.

The remainder of the 8,000 is consumed by this environment's bundled-skill entries, which are
protected and charged first; the measured bundled share here is roughly 5.5–6k chars, and the
fleet cannot control or predict that share across environments. Consequence for CTX-002:

- Trimming is still correct — it monotonically increases how many entries survive everywhere and
  is the only lever that also fixes Codex (its 8,000 budget is fleet-plus-nothing: bundled-skill
  protection is a Claude-side behavior).
- Trimming alone cannot guarantee full survival on 200k-window Claude hosts with rich bundled
  sets. Full survival there needs the settings fraction, calibrated by a live listing probe
  (0.05 verified in this container; 0.02 measured partial).
- The honest CTX-002 outcome is therefore both levers: the trim for every host, plus a
  documented, probe-verified settings line for consuming repositories.

## Agent listing: no comparable cliff [verified — negative result]

The Agent tool's subagent listing (~6.9k chars across 11 fleet agent descriptions) was checked
for the same truncation class and cleared: no budget constant surfaced in the CLI binary, and a
live 200k-window session rendered all 11 fleet agent descriptions in full. The
`evals/README.md` "agent positives under-fire in headless mode" observation therefore keeps its
existing explanation (one-shot sessions prefer doing work inline over delegating) — it is not a
listing-budget effect. Recorded so the check is not re-run from scratch.

## Preload and body footprint [verified — byte counts on this tree]

The listing budget is the *always-loaded* layer; the second cost center is per-spawn preloading:
an agent's `skills:` field loads each named skill's **full SKILL.md body** at spawn (references
stay on-demand — this repository's probe passed "sde-fullstack read `references/consuming-apis.md`
when the task called an upstream API" the same day, so the claim in some doc paraphrases that
references preload too is contradicted by executed evidence).

- `sde-fullstack` preloads `backend-craft`, `frontend-craft`, `code-craft`, `root-cause`,
  `self-improve-loop`: **48,317 bytes (~12.1k tokens) of skill bodies** on top of its own
  19,540-byte (~4.9k-token) body — roughly 17k tokens before the task arrives.
- `self-improve-loop` is the largest skill body (18.1k bytes, 272 lines, ~4.5k tokens — at the
  Agent Skills spec's "<5,000 tokens recommended" line) and is preloaded by **three** agents
  (`sde-fullstack`, `prompt-engineer`, `verification-engineer`), each of which already carries
  the Learning closeout stanza inline in its own Output format.
- All 20 skill bodies are within the published <500-line guidance (largest 272); the reference
  trees already practice progressive disclosure (`code-craft`: 2.8k body over 51k of on-demand
  references).
- **Constraint for any body diet:** `scripts/probe_plugin.py` asserts craft-skill *canary
  content is preloaded* (canary quoted from the body). Moving body content into references
  either keeps the canaries in the body or moves them deliberately with a probe update — a
  silent move would fail the probe or, worse, hollow out what "preloaded" proves.
- Adjacent hard cap, same family: GitHub's `.agent.md` body limit is 30,000 characters
  [sourced — github/docs `custom-agents-configuration.md`]; the generated
  `homelab-platform.agent.md` is at **24,631 (82%)** and that agent's canonical body has been
  the fleet's fastest-growing. Nothing warns before the cliff today.

## Artifacts

Probe transcripts and the scratch copy were session-local and are deliberately not committed;
every number above states its measurement conditions inline. The re-runnable instruments are
`scripts/fleet_doctor.py` (footprint), a live listing diagnostic (one-shot headless session
asking for the listing state), and the routing A/B recipe above.
