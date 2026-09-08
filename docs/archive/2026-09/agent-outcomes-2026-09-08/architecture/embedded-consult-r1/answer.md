# Decision record: PostgreSQL server trust

**Decision:** Use one small internal CA dedicated to these database server identities. Have it
sign server certificates directly; distribute only its public trust certificate to application
hosts. Keep the signing key offline between scheduled issuance sessions. Do not introduce an
online issuer, client certificates, or a broader PKI service. **[unverified]** This is a proposed
design, with no runtime verification performed.

**Context:** **[sourced]** The migration retains `sslmode=verify-full`. Its scope is three
applications, four stable database DNS names, and six application hosts; matching DNS
certificates can be issued. Two platform operators can maintain protected keys, application
teams own deployment configuration, and database admins own server certificates
(`task.md:7–20`). The problem to solve here is maintaining server trust through rotation and
recovery; the builder retains ownership of the migration (`task.md:3–5`).

**Options and trade-off:** **[unverified]** These are design judgments, not measured costs.

| Option | Benefit | Cost and decision |
|---|---|---|
| Keep the current trust behavior | No trust-distribution work | Does not meet the required identity-verification target; reject. |
| Explicit self-signed trust per database | Limits each trust credential to the identities on that certificate; no CA signing key | Feasible at this size, but every server certificate replacement requires coordinated trust staging on its consumers. Prefer this if protected CA custody cannot be sustained. |
| Small dedicated CA | Routine server renewal keeps the application trust anchor stable | Adds signing-key custody and a shared compromise domain covering all four database identities. Choose this, accepting that emergency CA replacement requires fleet coordination. |

**Boundary and ownership:** **[unverified]** Proposed responsibilities:

- Platform operators jointly own CA custody, independently stored encrypted recovery copies,
  recovery access, the issuance/expiry record, and scheduled signing. A normal management
  machine must not be the only location for either the signing key or its recovery material.
  One operator must be able to recover without the other's machine.
- Database admins generate and protect separate server keys, request only their assigned DNS
  identities, and own installation and server rollback. Platform operators validate requested
  names against the four approved database identities before signing.
- Application teams own authenticated distribution of the public trust bundle to every actual
  application trust store, including packaged copies, and own reload behavior and connection
  validation. A host file update alone is not evidence that its applications consumed it.
- The builder coordinates ordering and acceptance evidence through the caller. Implementation
  remains with `sde-agents:sde-fullstack`; this consult transfers no ownership or authority.

**Routine rotation and rollback:** **[unverified]** Proposed operating contract: issue a new
server key and certificate under the existing CA early enough to retain a recovery window.
Database admins stage the replacement; application teams prove fresh connections through each
application using the real DNS names. Existing pooled sessions do not establish that the new
certificate works. Confirm the chosen server reload mechanism preserves connection availability
before relying on it. Retain the previous, still-valid server material temporarily for rollback;
it is usable only if it is not suspected compromised.

For planned CA replacement, application teams first install a bundle trusting both old and new
CAs and prove adoption. Database admins then replace server certificates; application teams
prove fresh connections under the new CA before removing old trust. Before removal, rollback
can use the old server material. After removal, rollback requires another coordinated trust
update. This is a two-way door with coordination cost, not an instantaneous revert.

**Recovery and the missing failure mode:** **[unverified]** Proposed recovery requirements:

| Event | Required response |
|---|---|
| Server key lost | Database admins generate a replacement and request issuance; restore protected server material only if its confidentiality remains credible. |
| Server key compromised | Replace the key immediately. Do not count replacement as proof that clients reject the stolen credential. Unless all three applications demonstrate an effective revocation path, use emergency CA replacement and remove the old CA from every consumer's trust. This deliberately accepts a fleet-wide recovery for one stolen server key. |
| CA key lost | Platform operators recover from an independent copy and verify it against the recorded public CA identity. If recovery fails, stage a replacement CA while existing certificates remain usable; insufficient validity headroom becomes an availability incident. |
| CA key compromised | Create a replacement in a clean environment, replace server certificates, and remove the compromised trust anchor everywhere. Overlapping trust keeps accepting the compromised authority; it is a temporary exposure, not completed recovery. |
| Management machine lost or compromised | Loss must be recoverable from independent material. On compromise, platform operators assess every accessible signing key, server key, and deployment credential; uncertain CA exposure invokes CA-compromise recovery. Rebuilding the machine alone does not restore trust. |

**[unverified]** Routine rotation is intended to preserve connections. Compromise recovery cannot
promise both uninterrupted connectivity and immediate rejection of compromised trust when some
consumers cannot update promptly. The incident owner must choose containment, including an outage
where necessary, rather than silently retaining unsafe trust. No client revocation capability is
assumed in this decision.

**Acceptance and operational cost:** **[unverified]** Before committing to CA custody, have the
two operators demonstrate recovery from an independent copy without the normal management
machine. The builder should obtain evidence of a routine server rotation, a staged CA transition,
rejection of wrong DNS identities, and rejection of retired trust using fresh connections from
each application. Teams must measure the emergency trust-removal time; an unacceptably long time
falsifies this recommendation. Platform operators own CA expiry and issuance reminders, database
admins own server expiry alerts, and application teams own connection-failure alerts. Thresholds
must leave time for distribution, verification, and rollback. Exact effort and recovery time
remain unknown; no new monitoring platform is proposed.

**Design packet**

- **Decisions:** Dedicated offline CA, direct server issuance, staged routine rotation, and a
  coordinated trust replacement fallback for compromise; builder retains migration ownership.
- **Assumptions:** **[sourced]** Named identities, staging ability, and operator ownership are
  supplied by `task.md:9–20`. **[unverified]** Independent key recovery, application trust reloads,
  and sufficiently fast emergency distribution still need demonstration.
- **Weakest point:** **[unverified]** Emergency replacement touches every consumer. If that is too
  slow or protected CA custody proves unsustainable, revisit per-database self-signed trust before
  adoption; if a tested revocation mechanism becomes available, revisit the fleet-wide fallback.

Learning: none — no reusable signal
