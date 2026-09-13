---
name: security-audit
description: An adversary-eyes security sweep of the running home lab — exposure, trust zones, authn on exposed services, management planes reachable from the wrong zone, default credentials, secrets posture, vulnerabilities triaged into sde-agents:upgrade-campaign priorities. Use for "security-audit my lab", "what could an attacker reach", "check my exposure", or after standing up anything internet-facing. Reports only; fixes go to sde-agents:homelab-engineer. For a diff, sde-agents:code-reviewer; a codebase threat model, sde-agents:application-security-auditor; hygiene, sde-agents:lab-audit.
argument-hint: [scope - a zone, a service, or the whole lab]
disallowed-tools: Write, Edit, NotebookEdit
---

Audit the lab the way an attacker reads it: not "is it well-kept" but "can someone get in, move,
or take." Every finding is evidence-cited and carries the path an attacker would actually walk —
`sde-agents:lab-audit` owns the hygiene sweep; this skill owns the adversary's question.

All checks are read-only. `disallowed-tools` removes Write and Edit while this skill is active,
but Bash can still mutate (redirects, `docker rm`), so the mandate is still yours: inspection
commands only — every fix routes to `sde-agents:homelab-engineer`, and vulnerability findings
feed `sde-agents:upgrade-campaign`'s priority order rather than becoming ad-hoc patches. The
read-only-ness here is cooperative, not enforced (the reviewer's Bash guard keys on guarded
*agent* identities, not skills). Fan the checks out in parallel (per zone or per check area)
rather than sweeping serially.

Two rules with no exceptions:

- **A finding carries an attack path or gets downgraded.** A pattern match with no reachable
  route from an attacker position is a P2/P3 note, not a P0 — say what position the attacker
  needs, what they cross, and what they reach, or lower the severity and say why.
- **Triage suspicion; escalate corroborated compromise.** An unfamiliar key, process, or container
  is a lead. Make a bounded, nonmutating provenance check against deployment records, key
  fingerprints and ownership, package/image identity, and relevant access logs. Select only
  needed fields and keep credentials out of output. An explained, authorized artifact lets the
  sweep continue. An unresolved lead retains its evidence and missing provenance in the report;
  uncertainty is not proof of a breach. Corroborated unauthorized access, execution, exfiltration,
  or tampering ends the ordinary sweep: preserve available evidence and hand the incident to the
  operator. Do not clean up, restart, rebuild, rotate credentials, or isolate hosts as an audit
  step. Containment and recovery use `sde-agents:lab-incident` under
  `sde-agents:homelab-engineer`'s authority and actual host controls.

## Checks (run what applies; name what you skipped in the denominator)

The seven checks — trust zones and reachability, authentication on exposed services, management
planes, credentials, secrets posture, vulnerability triage, personal-data paths — live with their
command-level detail in [`references/checks.md`](references/checks.md); read it before sweeping.
The secrets check has its own deep-dive at [`references/secrets.md`](references/secrets.md),
loaded when that row trips.

## Output

Open with the coverage denominator — zones and checks swept vs. skipped, with why — then findings
ranked `[P0]`–`[P3]`, each with its evidence (command + output — for secrets and credentials,
names and paths only, never values: a report that quotes a secret is itself a leak), its attack
path (position → crossing → reach), and the one-line fix class. Grade severity by the unauthorized
capability or data reached and the prerequisites; intended public content and permitted,
authenticated access are not findings by themselves. End with the top three things to fix this
weekend, then emit the findings-ledger rows in `sde-agents:lab-audit`'s table format for the
operator to append to the lab repo's ledger — this skill holds no write tools, so the emitted
block IS the ledger entry.
