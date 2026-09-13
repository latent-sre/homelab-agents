# Lab-audit checks — command-level detail

Read from `SKILL.md`. Every command here is read-only; anything that would fix what it finds
routes to `sde-agents:homelab-engineer`. Substitute the lab's real hosts, paths, and domains, and
read the lab repo's own config first. Drift checks compare declared and running state; confirm
intended state against operator decisions and deployment history before choosing which side to
reconcile.

Per check: what to read, what a finding looks like, and the fix class (one line — the audit never
applies it).

## 1. Exposure

Hygiene depth only: listening sockets vs the proxy list. The adversary's version of this question —
what a specific attacker position reaches, and across which boundary — is
`sde-agents:security-audit`'s [`references/checks.md`](../../security-audit/references/checks.md)
row 1; a finding here that needs an attack path belongs there.

- Read: `ss -tlnp` per Linux host (`netstat -ano` on a Windows host); the reverse-proxy config
  from the lab repo; the router/firewall forward table where the repo exports it.
- Compare: listening sockets and WAN-reachable ports with the declared consumers, proxy/native
  exposure, and forward list. Check which routes require an identity boundary; an intentionally
  public read-only page does not require auth merely because it is reachable.
- Finding: unauthorized exposure of sensitive data or administrative capability; grade severity by
  reachable impact and prerequisites. An unexpected listener is a lead until its purpose and reach
  are established, not automatically P0/P1.
- Fix class: restore the intended access boundary, close an unintended port, or record an accepted
  exception with its scope and justification.

## 2. Host and container hygiene

- Read: the canonical host record and required native service/unit and timer status, including
  intended startup policy and the latest required job result. Compare with the applicable
  [`host-onboard` baseline](../../host-onboard/SKILL.md); use its criteria without running onboarding
  or applying repairs. A host without containers still receives its applicable host checks.
  Select status/policy fields rather than dumping unit environments or credential-bearing commands.
- Finding: a required native service is failed, its intended startup policy drifted, or a required
  timer/job missed its expected run. A deliberately disabled unit is not a fault merely because it
  is inactive. Merge a backup-job finding with check 4 rather than emitting it twice.
- Fix class: restore the intended native service/job policy through `sde-agents:homelab-engineer`;
  record unreadable status or missing intended state as an evidence gap, not a healthy host.

- Read: `docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'`; project only restart policy,
  health status/check presence, numeric resource limits, and privilege flags from container
  inspection. For example, `docker inspect --format '{{json .HostConfig.RestartPolicy}}' <name>`
  returns just restart policy. Read the corresponding declared fields from the repo configuration.
  Select fields before output reaches the transcript: do not print bare `docker inspect` or
  resolved `docker compose config`, environment values, labels, or healthcheck command bodies,
  which can contain credentials. Do not expand env files merely to inspect these settings.
- Finding: `:latest` or untagged images; restart behavior is undeclared; no useful health signal;
  exited or restart-looping containers; privileged or resource-contentious workloads have no
  isolation or limits.
- Fix class: pin the tag; declare restart behavior; add the smallest useful health signal; add
  isolation or limits where its predicate fires — Tier 1 edit, Tier 2 apply.

## 3. Certificates

- Read: `openssl x509 -in <cert> -noout -enddate -subject` for every cert path the proxy config
  names. Live-endpoint probes (`openssl s_client`, curl) are network calls — when the session
  can't run them, the row lands in the denominator, not in silence.
- Finding: `[P1]` expiry ≤30 days with no renewal evidence (timer, cron, recent renewal log); a
  service crossing a trust boundary still uses plain HTTP with nothing in front.
- Fix class: repair the renewal path, or move the service behind the proxy.

## 4. Backups

- Read: the backup tool's config and its last-run state or log; the irreplaceable-state set (every
  service whose data matters and cannot be recreated from a declared source); documented loss
  tolerances; runbook Recovery slots and Last-verified lines where those runbooks are required.
- Finding: `[P0]` irreplaceable state absent from the backup set; last success older than the
  service's cadence; required restore never tested — a backup that has never been restored is a
  hope, not a backup (the rehearsal routes to `sde-agents:restore-drill`). Recreatable or explicitly
  disposable state is not a backup finding when its loss tolerance is recorded.
- Fix class: add to the backup set; schedule the restore drill.

## 5. Monitoring gaps

- Read: scrape/probe target lists and alert rules from the monitoring config in the repo; the
  receiver/route config those alerts point at. Live API queries land in the denominator when the
  session can't make them; config-vs-config answers most of this check.
- Finding: no useful health signal for an operated service; a service classified household-critical
  under [`service-onboard`'s predicates](../../service-onboard/SKILL.md) has no
  actionable alert; an alert routes to a receiver that no longer exists; a rule targets a service
  that's gone. Missing per-service metrics or a dashboard is not itself a finding without a named
  question they were supposed to answer.
- Fix class: add the smallest signal or fix the route — `sde-agents:observability` designs it,
  `sde-agents:homelab-engineer` applies it.

## 6. Drift

- Read: selected image, mount, and port fields from declared configuration and runtime inspection;
  apply check 2's output selection before emitting either side. Read env-file paths from source,
  not resolved environment values; runtime inspection does not retain their source filenames.
  If comparing a setting needs a private substitution, compare within its authorized environment
  and emit only the field name and match/mismatch. Also read `git -C <lab-repo> status --short`
  plus recent log for the config dirs.
- For native hosts, also compare required persistent mounts, time synchronization, timezone,
  resolver configuration and observed DNS health with the canonical host baseline. Select only
  task-relevant status/settings; unavailable runtime observations remain unverified. Reuse the
  host record rather than creating another inventory.
- Finding: a running container that differs from the repo's rendering; console changes never
  reconciled back to code; required native-host settings or observed function differ from the
  established baseline. Intended state that cannot be established remains a decision gap.
- Fix class: establish intended state, then reconcile the incorrect side. If runtime is correct,
  update the repo (Tier 1); apply through `sde-agents:homelab-engineer` only when runtime must
  change, with the applicable tier precautions. Verify agreement afterward. Unresolved intended
  state is a decision gap, not permission to re-apply.

## 7. Capacity

- Read: `df -h` (flag >80%); `du -sh` on the known growers (media, logs, backups);
  `docker system df`; growth rate = compare against the previous audit's ledger row.
- Where this host controls physical disks, inspect existing disk-health/SMART and storage-health
  evidence using the documented read-only status path. Guests reuse hypervisor coverage; missing
  access is a coverage gap. Do not start self-tests or storage repairs during this audit.
- Finding: >80% and growing; a log or volume growing with no rotation (no logrotate conf, no
  logging-driver max-size); unhealthy disks or absent required physical-disk health coverage.
- Fix class: rotation or retention policy, or a storage plan — never a mid-audit prune.

## 8. Updates

- Read: pinned versions from the repo, prioritizing the security-relevant surface — the proxy,
  VPN, and anything check 1 shows exposed. Upstream-latest intel is a web lookup; when the
  session can't fetch it, say so in the denominator (the caller or `sde-agents:researcher`
  supplies it).
- For native hosts, compare OS release, patch/package-source state and intended update policy
  with the host record. Establish support status from current vendor evidence via the caller or
  `sde-agents:researcher`; unavailable evidence leaves support status unverified. Do not install
  updates or refresh package indexes during the read-only audit.
- Finding: an exposed service far behind upstream, or a pinned image with a known-exploited CVE
  when version intel is available; an unsupported OS or a confirmed departure from the host's
  package/update policy. Bare `:latest` belongs to check 2, not here.
- Fix class: a planned bump — one service via `sde-agents:homelab-engineer`; a batch via
  `sde-agents:upgrade-campaign`.

## Findings ledger (output convention)

The audit's final block, emitted after the top-three. One row per finding, append-ready for the
lab repo's audit ledger (e.g. `audits/ledger.md` — the operator's location wins). This skill runs
without write tools, so **emitting the block is how the ledger gets written** — by the operator or
the agent they hand it to.

| date | check | sev | finding (one line) | evidence (cmd) | status |
|---|---|---|---|---|---|
| 2026-07-27 | backups | P0 | wiki-db volume not in backup set | `restic snapshots` empty for path | open |

`status` is `open` when emitted; the ledger's keeper flips it to `fixed` or `accepted`. An
`accepted` row carries or points at its written justification — the exception check 1 asks for in
writing — because the reader of that row is the next audit session, which otherwise cannot tell a
considered exception from a silence. A finding re-observed next audit updates its existing row
rather than adding a twin — the ledger reads as current state; git history is the history.
