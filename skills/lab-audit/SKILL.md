---
name: lab-audit
description: A read-only home-lab health and hygiene sweep that reports severity-ranked, evidence-cited findings. Use for a periodic audit, when asked "what's wrong with my lab" or "audit my setup", or after a long gap in maintenance. Surveys and reports; for the fixes themselves, use sde-agents:homelab-engineer.
argument-hint: [scope - a host, a stack, or the whole lab]
disallowed-tools: Write, Edit, NotebookEdit
---

Audit the lab against its own standards and report like a code review of the infrastructure: severity-ranked, evidence-cited, no finding without the command output that proves it.

## Checks (run what's applicable; list what you couldn't run and why)

All checks are read-only. `disallowed-tools` removes Write and Edit while this skill is active, but Bash can still mutate (redirects, `docker rm`), so the mandate is still yours: inspection commands only — fixes route to `sde-agents:homelab-engineer`. Whether you were invoked directly from the main session or under `homelab-engineer`, the reviewer's Bash guard does not cover this skill (that hook keys on guarded *agent* identities, and the main loop carries none at all) — the read-only-ness here is cooperative, not enforced. `NotebookEdit` is in `disallowed-tools` for the same reason as Write and Edit: it is a write tool, and a denylist that names only the obvious two leaves the third. Fan the checks out in parallel (per host or per area) rather than sweeping serially.

The eight checks — exposure, container hygiene, certificates, backups, monitoring gaps, drift,
capacity, updates — live with their command-level detail in
[`references/checks.md`](references/checks.md); read it before sweeping. Run what applies, and
name what you skipped in the denominator.

This is the hygiene sweep: is the lab well-kept. The adversary's sweep — what an attacker in a
given position can reach, move through, or take (trust zones, authn, management planes,
credentials, secrets, reachable vulnerabilities, family data) — is
`sde-agents:security-audit`. Same read-only posture, same ledger format, different question.

## Output

Open with the coverage denominator — hosts covered and checks run vs. skipped, with why (e.g. "3/4 hosts; 6/8 checks — backups and drift skipped: no repo access") — findings without a denominator overstate the sweep. Then `[P0]`–`[P3]` findings, each with the evidence (command + output) and the one-line fix. Grade exposure by unauthorized capability or data reached, not the absence of auth on intended public content; irreplaceable state without backup is graded against its declared loss tolerance. End with the top three things to fix this weekend — not a list of thirty. After the top three, emit the findings-ledger rows (format at the end of
[`references/checks.md`](references/checks.md)) for the operator to append to the lab repo's
ledger — this skill holds no write tools, so the emitted block IS the ledger entry.
