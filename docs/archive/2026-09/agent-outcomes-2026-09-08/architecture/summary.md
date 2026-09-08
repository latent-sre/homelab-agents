# Principal-engineer outcome results

**Aggregate: no pass.** Six unchanged final-source trials completed. Both system-design and both
strategic-direction answers met every material criterion. Each embedded consult had a different
material partial: management-access recovery in r1 and CA-rollover ordering in r2. Overall,
38 of 40 criterion judgments passed and two were partial; this is bounded case evidence, not a
reliability estimate or a pre/post improvement result.

| Case / repetition | Material result | Criterion judgments | Characters | Whitespace words |
|---|---|---:|---:|---:|
| [System r1](system-design-r1/answer.md) | Pass | 7 pass | 23,203 | 3,328 |
| [System r2](system-design-r2/answer.md) | Pass | 7 pass | 26,234 | 3,669 |
| [Strategic r1](strategic-direction-r1/answer.md) | Pass | 7 pass | 21,737 | 2,952 |
| [Strategic r2](strategic-direction-r2/answer.md) | Pass | 7 pass | 21,453 | 2,914 |
| [Consult r1](embedded-consult-r1/answer.md) | Material partial | 5 pass, C5 partial | 7,618 | 1,045 |
| [Consult r2](embedded-consult-r2/answer.md) | Material partial | 5 pass, C4 partial | 8,566 | 1,182 |

System responses preserved the settled platform, separated v1 analytics from split fulfillment,
retained effect identity and legacy keys, staged ownership before incompatible admission, and
quarantined unresolved carrier effects beyond the seven-day guarantee. They stated the real
cost: uncertain orders may remain held despite the 30-day replay capability, and rollback cannot
undo accepted shipments or erase outstanding split plans.

Strategic responses chose standardizing current contracts and recovery first, with managed
transport as a conditional later challenger. Both considered OSS operating duties, the
two-operator limit, six-team ownership, shared failures, region-bound data, byte/retention/replay
costs, measured headroom, falsifiers and reversible evidence-producing phases. They invented no
vendor prices, SLAs or capacities.

## Material partials and bounded repair direction

**Consult r1 — C5, management-machine compromise recovery.** Answer line 61 requires operators
to `assess every accessible signing key, server key, and deployment credential` and says
`Rebuilding the machine alone does not restore trust.` It does not require removing exposed
deployment write authority or re-establishing a trusted replacement distribution path before
repairing client trust. If a compromised credential can rewrite trust, replacing the CA and
machine does not settle that risk. The fixture does not establish that such credentials are
present: the finding is an incomplete recovery decision, not a deployed vulnerability.

Countervailing context is retained: r1 assigns authenticated distribution to application teams
(lines 33–35), generates a replacement CA in a clean environment (line 60), and permits
containment/outage instead of unsafe trust (lines 64–67). Those provisions do not finish the
credential recovery path. A bounded repair to the consult would contain the compromised host,
revoke/rotate exposed management and deployment access, restore trusted distribution from
independent clean material, then repair and verify trust/certificates; uncertain exposure remains
contained. [Full C5 judgment and context](embedded-consult-r1/grade.json).

**Consult r2 — C4, planned CA rollover ordering.** Lines 59–60 say:

> For planned CA replacement, first load both public anchors everywhere, prove fresh connections
> to the new chain, then replace server certificates and remove the old anchor.

This validates before replacing the server certificates and supplies no post-replacement gate
before removing old trust. A preflight/canary can establish new-chain support, but cannot prove
that every actual endpoint completed its replacement; premature old-anchor removal can strand
a lagging server. The answer's general driver verification (lines 55–57) and isolated rehearsal
(lines 75–79) are useful but do not correct that explicit dependency order. A bounded repair
would stage and verify both anchors, replace leaf certificates, prove fresh connections to the
new chain and correct names on affected endpoints/drivers, and only then remove old trust.
[Full C4 judgment and context](embedded-consult-r2/grade.json).

The parent independently reopened both consult answers and agreed these two partials after
considering the countervailing provisions. No actor was rerun, no answer was edited, and no
source fix is authorized or implied by these recommendations.

## Other limitations and retained issues

[Nonmaterial observations](nonmaterial-observations.md) preserve the extra Learning lines in
strategic r1 and both consults, a causal inference initially labeled sourced in strategic r2,
and consult r2's paragraph-style source citation. A material pass is not flawless source
following. System and strategic answers approach 3,000–3,700 words; there was no frozen length
threshold, runtime token usage, cost measurement, or before/after efficiency comparison.

All actors were fresh `default` actors, `fork_turns=none`, with no model/effort override and no
other actors' outputs or grader rubric supplied. Actual model identity and sampling seed remain
unknown. The first two system actors overlapped; thereafter only one architecture actor ran at
a time to preserve a slot for the parent's independent verifier. This is direct frozen-source
injection under ambient host instructions, not native activation/routing or installed-adapter
proof. Tool restrictions were cooperative under inherited full access, with one explicit input
bootstrap read and answer-only writing permitted. These observations do not prove host guards.

The coordinator authored the cases and rubric before actors ran and manually graded all full
answers with exact quotes. The parent independently checked the two material partials; the
remaining grades have no second independent review recorded. No real bus, carrier, vendor,
PostgreSQL driver, certificate rotation, or compromised host was exercised.

## Integrity and retained artifacts

Source: `agents/principal-engineer.md` at
`81fc08572b3eab529fb0b9f741c3f88330aab230`, SHA256
`e6f5ae1d78170340ae8dc36458f6976ac135e8366975f8ac43a356be94014b6f`.

The [evidence check](evidence-check.json) confirms unchanged source and pre-run rubric hashes,
all six task and answer hashes, all 40 criterion quotes, and all eight alternate-context quotes.
[runs.json](runs.json) records actor IDs and registration timestamps;
[summary.json](summary.json) records per-answer/input/handoff/grade hashes and measured sizes.
Each run retains its full `task.md`, exact `handoff.txt`, unchanged `answer.md`, actor
`completion.json`, and criterion-level `grade.json`. [conditions.json](conditions.json) retains
the scope and runtime limits; [rubric.md](rubric.md) is the unchanged grading contract.

Discovery disposition: both material gaps and the nonmaterial observations are filed in this
evidence packet and handed to the parent/maintainer. Their causes are not attributed to a
particular source sentence, and this task makes no fleet, release, install, or memory change.
