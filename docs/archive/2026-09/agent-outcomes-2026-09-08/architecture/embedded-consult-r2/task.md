# Embedded design consult task

This is a synthetic fixture. The builder remains the owner of the PostgreSQL TLS migration;
you are being asked to resolve one design fork and return the answer through the caller.
No external research, implementation, deployment, or ownership transfer is authorized.

Our builder is moving three internal applications from encrypted PostgreSQL connections with
no server identity verification to sslmode=verify-full. Keep that target. There are four stable
database DNS names and six application hosts, all in one administrative region. We can issue
certificates with the DNS names clients actually use. None of the applications uses a client
certificate; this decision is about clients verifying the database server.

The open fork is to distribute explicit per-database self-signed server trust certificates to
each application host, or establish one small internal CA and distribute its public trust
certificate. There is no current CA, no existing automated issuer, and no team offering to run
a broad PKI platform. Two platform operators can own protected key storage and scheduled
maintenance; each application team owns its deployment configuration. Database admins own
server certificates. We can stage trust updates before certificate swaps, but applications
must keep connecting during routine rotation and we need a credible recovery path if a server
key, CA key, or the operators' management machine is lost or compromised.

Return a concise, bounded decision record for this trust fork, with the division of ownership
and enough rationale for the builder to continue the migration. Do not redesign the TLS
migration or write code, commands, config files, or an organization-wide PKI program.
