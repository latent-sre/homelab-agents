---
name: prompt-craft
description: The lightweight inline method for prompt work — success criteria, baseline, minimal change, fresh retest. Use when creating or fixing anything an LLM consumes — prompts, agent definitions, skills, tool descriptions — including requests like "write me an agent for X", "my skill never triggers", "the model keeps ignoring this instruction". First stop for prompt work; escalate to sde-agents:prompt-engineer only when the fix needs fresh-context reps, before/after evals, or spans a prompt suite; for multi-agent systems, sde-agents:multi-agent-architect.
argument-hint: [what to create or fix]
---

For quick jobs, apply this method inline. For iterative testing or a full agent/skill suite,
spawn `sde-agents:prompt-engineer` with the target file, task mode, success criteria, and the
applicable requirements, established defect, or tuning hypothesis plus available baseline evidence.
Include the remaining review-round limit, stopping conditions, and prior attempts and results;
delegation does not reset the repair budget.

## Method

When capturing a live workflow, extract its tools, step order, and corrections from the
conversation. Ask about gaps only when they would change the reusable procedure.

1. **Define success.** State the required behavior, output, and constraints before editing.
   Use observable criteria: required fields, allowed actions, or how to handle missing evidence.
2. **Match the evidence to the task.** A new draft starts from requirements and representative
   inputs; no previous failure is required. A repair starts from observed behavior or a verified
   source contradiction: check loaded instructions, context, tool errors and runtime limits
   before blaming prose. Measured tuning starts from a captured configuration and metric.
3. **Make the smallest useful change.** Draft the required behavior, fix the established defect,
   or test one tuning hypothesis; preserve unrelated working instructions.
4. **Check the result at the appropriate depth.** Exercise a draft on a representative input;
   retest a repair's failure and a nearby valid case. Use fresh context when prior instructions
   could contaminate the result. Report checks actually performed; an unexecuted draft is
   "written but not behavior-tested." Measured tuning uses paired cases and repeated fresh runs
   under matching conditions, through `sde-agents:prompt-engineer` when that loop is needed.
   When editing this fleet's descriptions, follow the repository's before/after routing-eval
   playbook. Firing rates measure routing, not output quality; any new forbidden near-miss firing
   is a defect. Reuse existing evidence only under the repository's equivalence rules.

For iterative repairs, use the project's or caller's review-round limit; if none exists, state a
finite limit before iterating. Compare each unsuccessful fix with the previous attempt. Stop
editing when the same failure persists without new evidence, or when the limit is reached. Return
the unresolved issue, attempts and results, and what would justify another attempt to the caller.
The caller can extend its own limit only within the project's cap. Crossing that cap requires the
authority and extension size the project specifies; delegation cannot supply an operator ruling.
Without a project cap, the caller may authorize another round.

## Write instructions the model can apply

**Describe capability and triggers.** Use words a user would say; keep the procedure in the body.
For routing failures, check registration, visibility, and actual invocation before editing the
description. Test realistic requests and adjacent near-misses: "extracts form fields from PDFs"
gives a clearer action boundary than "helps with documents".

**Match the form to the observed failure.** These are starting points to test, not guarantees.

| Observed failure | Candidate change |
|---|---|
| Breaks a required rule under pressure | State the boundary and permitted alternative; add a counterexample if useful. Enforce authority outside the prompt. |
| Produces the wrong output shape | Specify the required parts and order; use a schema or compact example when useful. |
| Omits a required element | Add a required slot and define how to report missing evidence without inventing a value. |
| Behavior should depend on a condition | Conditional keyed to an observable predicate |
| Follows an earlier conflicting instruction | Correct the conflicting instruction at its source; adding another rule leaves both active. |

Use plain imperatives and observable conditions. Replace vague exceptions such as "unless it
matters" with the condition that changes the action; retain necessary exceptions. Explain why
only when it prevents a likely mistake. Emphasis and repeated prohibitions do not establish
compliance. Separate instructions, input data, and examples with clear headings or delimiters.

## Simplify without losing the contract

Remove repetition, generic workflow narration, and obsolete advice. Keep decision-changing
constraints, output contracts, reference triggers, and known failure points that still apply.
Put substantial conditional detail in references; do not split a short, self-contained procedure
merely to make its entrypoint shorter. Preserve security, privacy, authorization, and
destructive-action boundaries; `references/agent-security.md` owns the security guidance.

Treat simplification on a new model as an experiment. Compare recorded prompt versions on the
same cases, holding the model, tools, context, and grading fixed. Keep the change only when required
behavior is preserved. A shorter file proves only text reduction; claim better reliability,
latency, or token use only for what was measured.

Keep compact examples that demonstrate required behavior and agree with the instructions.
Test example changes on distinct cases; one model or benchmark does not establish a universal
rule. [Anthropic's context guidance](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
supports representative examples and sufficient, focused context.

## Load the reference for what you're working on

Read the relevant reference before writing; name the references used in the handoff.

| If the work involves… | Read first |
|---|---|
| an agent that touches untrusted content, private data, or the ability to act | [`references/agent-security.md`](references/agent-security.md) |
| choosing an agent's tools, or designing tools for a model to call | [`references/tools.md`](references/tools.md) |
| what an agent knows, when it loads it, or degradation over a long run | [`references/context.md`](references/context.md) |

## Host configuration

Use the target host's current configuration and permission controls. Frontmatter fields only
work where that host honors them. For canonical Claude definitions, read
[`references/claude-code-frontmatter.md`](references/claude-code-frontmatter.md); it owns the field
facts and plugin exceptions. Fix drift there instead of copying platform facts into each prompt.
