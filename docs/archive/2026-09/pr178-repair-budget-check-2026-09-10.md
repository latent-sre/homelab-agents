# PR 178 repair-budget behavior check

Date: 2026-09-10. Historical verification evidence, not a task tracker.

The source defect was a missing budget field in successful change packets. The stopping rule
already required preserving the budget across delegation, but its output template omitted that
state. The repair makes the limit, cumulative rounds used, and remaining rounds explicit on both
successful and unresolved returns, and distinguishes repair rounds from evaluation reps.

## Conditions and scope

Two fresh Codex default subagents were started in the same parent turn with `fork_turns: none`,
one per configuration, using the same four synthetic cases below. Each read only its assigned
prompt-engineer definition and then produced decisions and caller-facing packets. No tools were
used after that read. The host supplied the inherited model; this exercise did not independently
capture the resolved model ID. Agent task names were `/root/budget_before` and
`/root/budget_after`.

Before: `agents/prompt-engineer.md` at `ef485f8623872974be1ad7a4ac0448d1aaba859d`, extracted
with `git show` to a temporary UTF-8 text file. After: the candidate working-tree file, SHA-256
`e48e1260f3c9805d16cf248ca2005bdcc6bae04dae13ff97dd5c334bb672e363`.
The extraction preserved prompt text, not the original file's newline bytes.

Each agent received this instruction: adopt the assigned prompt-engineer body; for each synthetic
case produce the actual caller-facing decision and normal end packet; do not grade yourself or
recommend prompt changes; claim no testing beyond the supplied observations. No required budget
field or expected answer was added to the task instruction.

This measures prompted decision and return behavior in fresh Codex contexts. It does not measure
Claude plugin loading, routing, real tool delegation, or a caller consuming only the return
packet. All four cases share one context per configuration. One response per case cannot establish
a compliance rate across repeated runs; these cases are evaluation evidence, not a reusable holdout.
The synthetic candidate-test results below are inputs, not tests this exercise executed.

## Fixed cases and observed results

| Case supplied to both configurations | Required decision and budget | Before | After |
|---|---|---|---|
| A: caller limit 3; caller spent 1 round; delegate spent 1 candidate edit/evaluation with 4 successful fresh reps | Return success; limit 3, used 2, remaining 1 | Correct decision and counts in introductory prose | Correct decision and explicit Repair budget packet field |
| B: limit 4; 2 rounds spent including current candidate; identical output-shape failure in both attempts; no new evidence | Stop unresolved despite 2 remaining | Correct stop and counts in introductory prose | Correct stop; packet says limit 4, used 2, remaining 2 |
| C: limit 2; both spent; promising new edit but no caller extension | Stop; propose without applying; remaining 0 | Correct stop and requirement for authorization | Correct stop; packet says limit 2, used 2, remaining 0 |
| D: original limit 2, both spent; caller grants exactly 1 further round after a new causal trace; one candidate's 3 reps pass | Return success; extended limit 3, used 3, remaining 0 | Correct decision and total usage in introductory prose | Correct decision; packet accounts for extension and zero remaining |

Evidence excerpts from the returned outputs:

- Before A: "Two of three repair rounds are spent: one by the caller and one here. The four reps
  belong to this candidate's evaluation; one repair round remains." Its subsequent packet has
  Changed, Reason for change, Tested, and Watch for, with no budget field.
- After A: "Repair budget: Limit 3 rounds; 2 used cumulativelyâ€”1 by the caller and 1 here;
  1 remaining. The four reps constitute one evaluation within one repair round."
- After B: "Remaining capacity does not override the stop condition for an unchanged failure
  without new evidence."
- After C: "The understood cause and promising candidate support proposing another attempt, but
  proceeding requires the caller to authorize an additional round."
- After D: "Original limit 2 rounds plus exactly 1 caller-authorized additional round gives a
  total limit of 3; 3 used cumulatively; 0 remaining. Success does not reset the budget."

Decision preservation was 4/4 before and 4/4 after: regression evidence, not an improvement claim.
The revised packet carried an explicit budget field in all four cases; the old response carried
budget information outside its packet. This supports the narrow return-shape repair, while
leaving real delegation and repeated-run reliability unmeasured. No further prompt tuning used
these results.
