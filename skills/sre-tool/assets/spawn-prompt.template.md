<!-- Spawn-prompt guide for Phase 2/3. Supply the objective, owned scope, acceptance criteria and
     return boundary; include material exclusions and authority limits. Reuse accessible current
     references and omit inapplicable fields without placeholders. Missing decision-changing facts
     are gaps, not inapplicable fields. Do not rely on implicit conversation inheritance or infer
     authority beyond the user's task and the agent's actual tool/host controls. -->

**Objective**: <!-- required: one sentence — what done looks like, not how -->

**Scope in**: <!-- required: the components/files this agent owns (disjoint from every parallel builder) -->

**Scope out / non-goals**: <!-- include material exclusions or constraints when they exist -->

**Acceptance criteria**: <!-- required: checkable statements the agent self-verifies before returning -->

**Boundary**: <!-- required: run to here, then return once — never mid-batch status; return early only on a material fork -->

**Inputs**:
- Environment card / mission block: <!-- required: path (usually the repo's CLAUDE.md) -->
- Contract artifact: <!-- multi-component only: path + version being built against -->
- Focus files / prior packets: <!-- reviewer spawns: "Check first" entries and nothing more — never your diagnosis or fix -->

**Leash**: reversible decisions are yours — make them and log them in your packet. A material fork
(changes what gets built and isn't inferable) comes back as the question plus your recommended
default. <!-- add lab-work tier constraints or other authority notes here, citing the approval, not restating it -->

**Return contract**: end with your agent file's packet. Name partial work explicitly — partial never
reads as complete. If you built against a contract version that changed while you ran, say so; the
result is stale until reconciled.
