# Decision: one small internal CA for database server identity

**Status:** proposed decision for the builder to apply within the existing migration.
The builder retains ownership; `sslmode=verify-full` remains the target.

**Context [sourced]:** The task specifies three applications, six application hosts, four
stable database DNS names, no client certificates, and no existing issuer. Two platform
operators can maintain protected keys; application teams own deployment configuration and
database admins own server certificates. Trust updates can precede certificate swaps.
Source: supplied `task.md`, paragraphs 2–3. This record uses those fixture facts; no runtime
behavior or certificate tooling was inspected.

**Decision:** Establish one dedicated, offline CA that signs only database server certificates
for this migration. Distribute its public trust certificate through application teams' existing
deployment process. Use a separate server private key for each independently operated server
identity, and certificates containing the DNS names those clients actually use. Do not add an
online issuer, intermediate hierarchy, or client authentication.

| Option | Trade-off and position |
|---|---|
| Keep the present trust behavior | **[sourced]** Conflicts with the required identity-verification target; rejected. |
| Explicit self-signed server certificates | **[unverified — design expectation]** Limits each trusted signing key to its server certificate, but couples replacement certificates to coordinated trust deployment on the relevant application hosts. Feasible at this size; preferred fallback if protected CA custody is not achievable. |
| One dedicated offline CA | **[unverified — design expectation]** Lets routine leaf replacement retain the same application trust anchor. Adds signing-key custody and a shared trust failure across all applications accepting that CA. Chosen because rotation continuity is a recurring requirement and named operators can own maintenance. |

The CA is justified by the rotation workflow, not by an assumed need to grow a PKI platform.
**[Unverified]** Actual drivers must demonstrate both CA-chain and hostname verification;
the expected behavior above is not evidence that these applications already support it.

**Ownership and operating contract**

- **Platform operators:** hold the CA key in a protected signing environment, separate from
  the ordinary management machine. Keep an encrypted recovery copy in a separate location,
  with recovery access available to both operators. Own the issuance inventory, calendar,
  expiry alerts, public CA certificate provenance, and a demonstrated recovery procedure.
  Signing is a scheduled manual operation; no always-on issuer is proposed.
- **Database admins:** generate and retain server keys at the server's protection boundary;
  submit certificate requests, check returned identities, and install server certificates.
  Send only public requests to the signer. Own server expiry and reload failures.
- **Application teams:** install the designated public trust material, preserve hostname
  verification, and prove every deployed instance has loaded a trust change. Own connection
  errors and any necessary application reload. A successful deployment alone is insufficient.
- **Builder:** integrate this decision into the migration and coordinate acceptance evidence
  through the caller. Implementation remains with `sde-agents:sde-fullstack`.

Proposed initial maintenance policy: one-year server certificates, renewal starting 90 days
before expiry, and a five-year CA with replacement staging beginning one year before expiry.
These are operating choices, not measured capacity claims. Platform operators review the
inventory monthly; existing monitoring routes approaching expiry and overdue renewal to them.
Application and database alerts retain their existing team owners. **[Unverified]** Existing
monitoring and deployment mechanisms can carry these duties; confirm that before issuance.

**Rotation, failures, and recovery**

**Routine rotation [unverified — expected behavior]:** With the same trusted CA, install a new
server key and certificate without changing application trust. Before calling this ready, the
builder must demonstrate rotation with established sessions and fresh connections from every
distinct application driver, including its real certificate-loading behavior. Certificate
reload or existing failover must preserve the required continuity; that is not assumed here.
For planned CA replacement, first load both public anchors everywhere, prove fresh connections
to the new chain, then replace server certificates and remove the old anchor. Retain the old
valid certificate for routine rollback only while its key remains trusted.

| Failure | Required response and detection |
|---|---|
| Server key lost | Database admins issue a new key and leaf from the existing CA. A healthy existing instance or existing failover carries service while replaced; without either, recovery can require an outage. Detect through key availability and reload checks. |
| Server key compromised | Database admins replace the key; platform operators contain the compromised host and access path. **[Unverified]** No client-enforced revocation capability is established. A new leaf does not invalidate the stolen one. If containment cannot exclude impersonation, replace the CA trust across affected applications and reissue its leaves, removing the old anchor. Do not wait for expiry or claim a routine zero-outage rollback is safe. |
| CA key lost | Platform operators restore from the independently held recovery copy in a trusted environment. **[Unverified — expected behavior]** Existing valid server certificates remain usable without an online signer. If restoration fails, stage a new CA before existing certificates expire; do not bypass verification. |
| CA key compromised | Treat every identity accepted under that CA as suspect. Platform operators establish a new CA on clean equipment; database admins reissue leaves and application teams remove the compromised anchor. Overlap is a temporary exposure, not restored security. Coordinate isolation or a maintenance outage if prompt distrust cannot preserve connectivity. |
| Management machine lost or compromised | Restore ordinary management access separately from CA custody. On compromise, suspend its deployment/signing access, rebuild from trusted material, and inspect application trust and server changes against independently held records. Rotate accessible credentials and keys; use the CA-compromise path if CA-key exposure cannot be excluded. Offline storage alone does not prove safety. |

Platform operators own signing and trust-change records; unexpected issuance or trust deployment
requires investigation. **[Unverified]** Key theft may leave no signal: these records aid detection
and recovery but do not guarantee discovery of compromise.

**Acceptance and reversibility:** The first reversible step is an isolated rehearsal covering
valid names, wrong names, unknown issuers, leaf rotation, overlapping-anchor rollover, old-anchor
rejection, and recovery with the management machine unavailable. Record results for actual driver
versions. If custody or continuity fails, return this fork to the builder before production trust
installation. Choosing a CA is a two-way door while keys are trustworthy: self-signed trust can be
staged before replacement server certificates. Removing trust after a compromise is intentionally
not reversible to the compromised key.

**Design packet**

- **Decisions:** Use one offline database-only CA; assign custody to platform, server keys to
  database admins, and trust deployment to application teams. Return implementation to the caller.
- **Assumptions:** The supplied ownership capacity is available; deployed drivers support the
  required verification and overlapping trust; recovery material survives management-machine loss.
- **Weakest point:** The protected signing and recovery procedure is unproven. A nominally offline
  key routinely unlocked on the same management machine would undermine the decision.
- **Accepted trade-off / revisit:** Accept a shared trust failure to reduce recurring trust
  deployments. Prefer explicit self-signed trust if independent CA custody cannot be demonstrated;
  revisit the design if manual renewals miss their window or the trust domain gains independent
  administrative owners. No organization-wide PKI scope is authorized.

Learning: none — no reusable signal.
