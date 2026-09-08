# Principal-engineer final-source outcome trials

This packet evaluates the frozen canonical principal-engineer source captured from revision
`81fc08572b3eab529fb0b9f741c3f88330aab230`, SHA256
`e6f5ae1d78170340ae8dc36458f6976ac135e8366975f8ac43a356be94014b6f`.
It does not compare an earlier source or test native role selection.

Completed results: [summary.md](summary.md). Aggregate outcome is **no pass** because both
embedded consults have a material partial, although the four broader design decisions pass.

- [Cases](cases/): three synthetic, self-contained tasks; two independent runs each.
- [Rubric](rubric.md): criteria written and hashed before the first actor launch.
- [Conditions](conditions.json): available host/model/isolation information and explicit limits.
- [Runs](runs.json): source and input hashes, actor identifiers, timestamps, completion state.
- [Handoff template](actor-handoff-template.txt): exact actor wrapper; each run retains its rendered
  `handoff.txt`, `task.md`, full `answer.md`, and completion return when available.

Each actor is a fresh `default` actor with `fork_turns=none`, no model or reasoning override,
and no supplied grader criteria or other actor outputs. The wrapper permits one narrowly scoped
shell read to load its source and task; after that it permits only writing the answer artifact.
The actor's output directory is its isolated documentation home. This input transport is a
harness provision, not evidence that the source-host Bash guard ran. Generic host instructions
and tools may remain ambient. Tool/read/write limits are cooperative under inherited full access.

No actor receives memory or current repository files. No product files, definitions, installed
adapters, releases, or live systems are changed. A model's actual identity and sampling seed are
not reported by the spawning API and remain unknown. Timestamps record when the coordinator
registered launch/completion, not server-side model timing.

The architecture coordinator grades the full answers manually against the frozen rubric using
exact quotes. A material partial or failure prevents a case-level pass. Two runs measure only
observed variation on these three supplied tasks; they are too few for a reliability estimate.
No answer is edited after submission, and the case/rubric/source do not change in response to
results. Unexpected issues are recorded alongside the initial assertions.
