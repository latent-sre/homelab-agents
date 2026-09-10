# Fleet role expansion and home-lab SRE identity

**Status:** Accepted (2026-07-29) — the application-security auditor (ROLE-002) and the
home-lab SRE identity with `host-onboard` (ROLE-001) are accepted as proposed; the
verification-execution authority question (ROLE-003) was accepted later the same day as the
test-authoring verifier contract recorded below
**Date:** 2026-07-28
**Reviewed revision:** `be2af4c87a3ecd53286fbcda84863d507ee47ac4`
**Compared design:** [`2026-07-27 roster expansion`](../archive/2026-07/roster-expansion-design.md)
**Implementation status:** Implemented in full — ROLE-001, ROLE-002, and LABSEC-001 landed
2026-07-29 (PRs #37–#42), and ROLE-003's accepted contract with ROLE-004's
`verification-engineer` landed the same day (PR #43). This record holds no open work; anything
still tracked lives in [`fleet-roadmap.md`](../fleet-roadmap.md).

## Acceptance record

**LABSEC-001 accepted as proposed, 2026-07-29** (the reconciled running-lab security decision this
record carried alongside the two roles): the adversary sweep exists as its own read-only
`security-audit` skill rather than being folded into `lab-audit`, with the boundary this record
named — hygiene stays with `lab-audit`, fixes stay with `homelab-engineer`, vulnerability output
feeds `upgrade-campaign`, and evidence of active compromise stops the sweep. Implemented the same
day; `LABSEC-002` (the guard-enforced inspector that could run either checklist under
enforcement) was blocked on `DEPLOY-001` at the time of this record, since a guard-enforced agent
must not ship into a deployment where the guard never runs. That prerequisite has since been
satisfied — the roadmap owns its current status.

2026-07-29, fresh-look session, operator answered directly: **accept both** decidable roles as
proposed — ROLE-001 (visible rebrand to Home-Lab SRE / Platform Engineer with the
`homelab-platform` key unchanged, Linux-host trigger vocabulary, explicit-only `host-onboard`)
and ROLE-002 (`application-security-auditor`, static-first tools, no Bash, non-PR remit).
ROLE-003 was deliberately not decided: it parks trigger-bound and reopens on the first real
independent-verification task, which also keeps ROLE-004 blocked. LABSEC-001 remains sequenced
behind ROUND1-001's lab-audit split, unchanged.

> **Superseded in part, 2026-08-30.** ROLE-001 kept the `homelab-platform` key while rebranding
> the visible role to "Home-Lab SRE / Platform Engineer", and this record's rejected
> alternatives argued for keeping that key. The key was renamed to **`homelab-engineer`** on
> 2026-08-30 (PR #165), on the ground that the body had carried the "SRE / Platform Engineer"
> heading and the engineering remit all along while the key advertised only the medium. The
> 2026-07-29 ruling above is preserved verbatim: it says what was decided then, and this note
> is what changed it. Live files use the new key; this record and the other frozen artefacts
> keep the old one.

**ROLE-003 accepted, 2026-07-29 (later the same session).** The operator reopened the question
directly rather than waiting for a trigger task and chose the **test-authoring verifier** model
with a local-containers-free effects gate. The authority contract, answering the six forks this
record posed:

- it may create and edit tests — the earlier `test-engineer` authoring contract folds in here;
- product-code edits are always prohibited, as a cooperative limit the definition states honestly
  (no tool layer distinguishes test paths from product paths);
- it verifies in a disposable worktree by default, and evidence binds to the exact revision and
  environment actually tested;
- hermetic checks run freely, and so do throwaway local containers — with mandatory teardown and
  packet-reported residue, because container side effects outlive the worktree — while live-lab
  services, external network calls, shared databases, and external systems require approval named
  in the task;
- a check whose gated effect lacks approval is reported **inconclusive**, never silently skipped
  and never counted passed; and
- the `tools:` list is the only enforced limit; path scoping and effects gating are cooperative,
  and the definition states which is which.

Write and Edit are held for the real purpose of test authoring, which keeps the agent out of the
read-only classification; an execute-only design was rejected because it would either be blocked
by the guard's no-interpreters rule or require weakening that rule. This acceptance unblocks
ROLE-004; the roadmap and the 2026-07-29 verification-round documents own implementation status.

## Decision question

Does the fleet need dedicated QA, Linux, SRE, and security agents, and should
`homelab-platform` be renamed or rebranded as an SRE role?

## Proposed decision

| Capability | Proposal |
|---|---|
| Independent QA | Add `verification-engineer` only after a test-execution authority model is accepted |
| Linux operations | Do not add an agent; add action-shaped host lifecycle coverage |
| General SRE | Do not add an agent; the existing home-lab operator already owns that outcome |
| Application security | Add `application-security-auditor` with a static-first, non-PR remit |
| Running-lab security | Decide separately on a `security-audit` skill and an optional guard-enforced `lab-inspector` |
| Home-lab identity | Present the role as **Home-Lab SRE / Platform Engineer** while keeping the `homelab-platform` key |

The resulting shape is two narrowly bounded agents, one Linux-host skill, and one visible rebrand
— not four generic agents. The optional lab inspector is a separate enforcement decision, not part
of that immediate role count.

## How the proposal was reached

Three read-only reviewers received non-overlapping surfaces and no access to `docs/`, `README.md`,
repository history, or earlier review conclusions:

1. Agent topology: `agents/*.md` and the plugin manifest.
2. Skill topology: `skills/**`, including linked references and assets.
3. Governance and evidence: `scripts/`, `hooks/`, `tests/`, `evals/`, CI, and plugin wiring.

Their conclusions were frozen before comparison with the historical documents. The later document
comparison affected naming, sequencing, and safeguards; it did not choose the gaps.

### Reconciliation with the earlier roster design

The earlier roster design was produced independently on `claude/roster-design` and proposed more
implementation-shaped components. Merging that branch changes neither document's evidence; it
does make their relationship explicit:

| Earlier proposal | Current treatment |
|---|---|
| `test-engineer` authors missing tests without changing product code | Fold into ROLE-003's authority decision as one possible verification mode; do not create a second testing agent before that boundary is settled |
| `security-audit` surveys the running lab from an adversary's perspective | Preserve as a distinct decision because application-source auditing and live-lab exposure have different inputs, authority, and fixes |
| `lab-inspector` enforces read-only evidence gathering for lab checklists | Preserve as an optional blocked agent; GOV-001 and command-by-command guard validation must land first |
| Home-lab SRE trigger vocabulary without renaming the key | Adopted by this proposal's visible rebrand and stable-key recommendation |
| No generic Linux or generic SRE agent | Confirmed independently |
| `release` and `porting-method` skills | Outside this role decision; retained as deferred roadmap items |

The old design's exact descriptions, eval seeds, guard command candidates, and rejected alternatives
remain in the archive as implementation evidence. They do not bypass the current decision gates.

## Context

### Independent verification is not currently owned

[`sde-fullstack`](../../agents/sde-fullstack.md) implements and verifies its own work.
[`code-reviewer`](../../agents/code-reviewer.md) independently reviews a diff but deliberately
cannot run repository tests or scripts. No role independently reproduces behavior, exercises the
actual runtime, compares it with acceptance criteria, and returns a release-readiness verdict.

### Whole-repository application security is not currently owned

`code-reviewer` has a strong security pass, but its public remit is a PR, commit, branch, or diff.
`researcher` can investigate external advisories and vendor evidence. Neither owns a repository or
subsystem threat model, source-to-sink audit, attack-path validation, or severity calibration.

### Adversary-focused running-lab security is a separate surface

`lab-audit` owns operational hygiene. The proposed application-security auditor owns source and
threat analysis. `homelab-engineer` owns every live fix. None of those contracts, by itself, owns
an intent-driven sweep of trust zones, exposed services, management planes, credentials, secrets,
and personal-data paths in the running lab.

The earlier design's `security-audit` skill fits that content boundary. Its optional
`lab-inspector` fits a different enforcement boundary: executing either lab checklist with no
write tools and no web, SSH, or curl channel. These are preserved as LABSEC-001 and LABSEC-002
rather than being conflated with application security.

### The home-lab operator already performs SRE work

[`homelab-engineer`](../../agents/homelab-engineer.md) owns VMs, containers, networking, storage,
monitoring, backups, change classification, rollback, access preservation, and operating
documentation. The operating skills form a service lifecycle: onboarding, observability, audits,
incidents, runbooks, postmortems, restore drills, and upgrade campaigns.

Linux is the substrate of that outcome. A generic Linux agent would overlap the authority owner
while routing on a technology name rather than a user outcome.

## Role contract: `application-security-auditor`

### Owns

- repository- or subsystem-wide application-security audits;
- threat models, trust boundaries, assets, actors, and entry points;
- source-to-sink and attack-path analysis;
- validation and severity calibration of suspected findings; and
- source-backed reports without implementing remediation.

### Does not own

- PR, commit, or branch review — `code-reviewer`;
- external CVE/vendor research alone — `researcher`;
- remediation implementation — `sde-fullstack`;
- home-lab exposure and operational hardening — `homelab-engineer` / `lab-audit`; or
- multi-system security architecture — `principal-engineer`.

### Initial authority

Start with `Read, Grep, Glob, WebSearch, WebFetch`. Static source analysis and authoritative
external evidence do not require Bash. Add history or execution authority only after a
demonstrated need and after the malformed-input guard defect is fixed.

**Departure as shipped (recorded 2026-08-17):** `agents/application-security-auditor.md` holds
`Read, Grep, Glob` only — the auditor is local-only and static-first, and its description now
routes external CVE and vendor research to `sde-agents:researcher`. No decision record captured
that narrowing when it happened; the shipped tool list governs, and this note is the audit trail.
Authority narrower than the accepted decision is the safe direction, but it should not have gone
unrecorded — a later reader comparing the two would otherwise read the omission as drift to repair.

### Required output

- scope and threat model;
- assets, actors, entry points, and trust boundaries;
- candidate attack paths;
- validated findings with source-to-sink evidence;
- exploit preconditions, impact, severity, and confidence;
- remediation direction; and
- rejected candidates and residual unknowns.

The proposed name deliberately uses **auditor**, not `security-reviewer`, because “reviewer” would
collide with the fleet's most routing-sensitive existing role.

## Role contract: `verification-engineer`

### Owns

- independently reproducing reported behavior;
- executing acceptance, regression, and failure-path checks;
- exercising runtime integration;
- comparing observed behavior with explicit acceptance criteria; and
- returning traceable evidence and a pass/fail/inconclusive release verdict.

### Does not own

- implementing the feature or fix — `sde-fullstack`;
- static PR/diff review — `code-reviewer`;
- diagnosing an unknown failure — `root-cause`;
- changing live home-lab infrastructure — `homelab-engineer`; or
- inventing a cross-component test architecture — `principal-engineer` when that design is
  material or hard to reverse.

### Authority prerequisite

The current policy treats Bash plus no write tools as a read-only agent, while the read-only guard
deliberately rejects Python, pytest, npm, make, and other test runners. Granting Write merely to
escape that classification would make the definition look safer without creating a real boundary.

Before authoring this agent, decide:

- whether it may create or edit tests;
- whether product-code edits are always prohibited;
- how `isolation: worktree` is used;
- how network, database, container, and external-system effects are gated;
- which integration or live-environment checks require approval; and
- which limits are enforced versus cooperative.

Claude Code documents custom subagents as separate contexts with selectable tools:
<https://code.claude.com/docs/en/sub-agents>. It documents `isolation: worktree` as temporary
file-change isolation: <https://code.claude.com/docs/en/worktrees>. A worktree is not a sandbox for
external effects.

### Required output

- target, environment, and exact revision;
- acceptance criteria;
- tests and checks executed;
- expected versus observed behavior;
- failure-path coverage;
- evidence and reproducible commands;
- pass/fail/inconclusive verdict; and
- skipped checks and remaining risk.

## Home-lab SRE identity and Linux boundary

Keep the stable component key:

```yaml
name: homelab-platform
```

Proposed visible heading:

```markdown
# Home-Lab SRE / Platform Engineer
```

Proposed description opener:

> Home-lab site reliability and platform operations for Linux hosts, VMs, container stacks,
> networking, storage, observability, backups, and self-hosted services.

Add trigger vocabulary for systemd and services, packages and patching, users/permissions/SSH,
disks/filesystems/mounts, host networking/firewalls, and host telemetry.

The first Linux addition should be explicit-only `host-onboard`, covering:

- OS and patch baseline;
- users, groups, sudo, SSH, and access recovery;
- package sources and update policy;
- host firewall and management exposure;
- systemd health and restart policy;
- disks, filesystems, mounts, and capacity;
- time synchronization and DNS;
- metrics/log enrollment;
- backup enrollment and restore ownership; and
- configuration tracking, validation, and rollback.

Because onboarding changes a live host, `host-onboard` should set
`disable-model-invocation: true`; `homelab-engineer` retains the change authority.

## Governance prerequisites discovered during the review — both since fixed

**Both defects below landed fixes in PR #40 (GOV-001 and EVAL-001) and are recorded here as the
reason those items existed, not as live defects.** The reproductions describe the reviewed
revision `be2af4c8`, not current behavior.

### Malformed guarded input returned ALLOW (fixed)

At the reviewed revision, [`readonly-guard.py`](../../scripts/readonly-guard.py) caught JSON
decoding failure and returned the exit-42 allow sentinel, and
[`hooks.json`](../../hooks/hooks.json) treated 42 as authoritative, exiting before the raw
guarded-agent fallback.

Reproduction at that revision:

| Input | Result then |
|---|---|
| Valid guarded payload with a state-changing Git command | Denied, exit 43 |
| Same guarded payload truncated into malformed JSON | Allowed, exit 42 |
| Malformed unscoped payload | Allowed, exit 42 |

**Resolution:** GOV-001 (PR #40) gave the guard a distinct `EXIT_INDETERMINATE = 44` answer, so
unparseable input can no longer be laundered into an authoritative allow. The guard's own docstring
owns the current exit-code contract.

### A routing case could pass outside its declared cluster (fixed)

At the reviewed revision, `evals/routing/craft-vs-fullstack.json` accepted `code-reviewer` for
`pos-ci-actions-harden`, although `code-reviewer` was not a declared member, so the scorer could
pass the case while reporting zero cluster fire rate.

**Resolution:** EVAL-001 (PR #40) landed cluster-membership schema enforcement.

### Current baselines are not one comparable anchor

Some clusters have no current baseline, membership and case counts have changed, and known-invalid
artifacts lack comparable conditions. Negative near-misses and measured regressions remain the
strongest routing signals. The full re-baseline stays deferred as `EVAL-003` until the active
Round 1 measurement path is healthy.

## Alternatives rejected

### Add a generic Linux agent

Rejected because it duplicates `homelab-engineer`'s authority and routes on a substrate. Reopen
only if repeated Linux work has a distinct output and authority boundary that does not belong to
the home-lab operator.

### Add a generic SRE agent

Rejected because the current home-lab hub and operating skills already provide SRE outcomes.
Reopen if the plugin intentionally expands to non-home-lab production operations and can state a
clean “not for home labs” boundary.

### Add a generic QA or test-strategy skill

Rejected because testing method already exists in the craft and implementation skills. It would
not solve the missing independent executable verdict. Extract a reusable verification skill only
after a second consumer demonstrates one.

The earlier `test-engineer` agent is not silently discarded: its test-authoring-only contract is
one candidate answer to ROLE-003. The current recommendation starts with verification outcomes
because pass/fail/inconclusive evidence is the missing fleet contract. Add a separate independent
test author only if observed work proves that authoring and verification need different contexts.

### Put security into another `reviewer`

Rejected because `code-reviewer` owns diffs and PRs. Whole-system security gets a separate output
and an auditor name; remediation remains with the builder.

### Rename the canonical home-lab key

Rejected because `homelab-engineer` is a useful routing discriminator and is referenced throughout
the skills, evals, inventory, and user-facing conventions. Rebrand the presentation without
breaking the component identity.

## Reopen triggers

Revisit this proposal when:

- an operator accepts, revises, or rejects the role boundaries;
- a real verification task demonstrates a safer execution-authority model;
- repeated Linux work falls outside both host onboarding and home-lab operations;
- the plugin expands to enterprise/non-home-lab production systems;
- static security assessment proves insufficient without Git history or execution;
- a running-lab security task proves the hygiene checklist lacks adversary-focused depth; or
- routing measurements show the proposed names or boundaries collide.

## Verification at review time

At the reviewed revision:

- fleet validator: 8 agents and 17 skills, inventory current;
- unit suite: 138 passed, 12 POSIX-shell hook tests skipped on Windows;
- strict plugin validation: passed.

No live routing run or role implementation was performed. The skipped hook tests are why the
guard defect is not treated as covered by the otherwise-green Windows suite.
