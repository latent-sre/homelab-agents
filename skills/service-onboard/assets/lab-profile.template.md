<!--
Template for a LAB PROFILE — the standing facts about a specific home lab.

This file does NOT belong in the sde-agents plugin. Copy it into the lab's own repository as its
project context (CLAUDE.md, or an AGENTS.md bridged by a CLAUDE.md containing `@AGENTS.md` — see the
plugin README's "Project context convention"). The plugin ships portable method; a lab's hostnames,
paths, and conventions are local facts that change without any plugin release, and a fleet skill that
hard-coded them would be wrong for every other lab and stale for this one.

Fill every slot or delete it. A half-filled profile that looks authoritative is worse than none,
because an agent will act on it.
-->

# Lab profile — <lab name>

## Stack (what this lab actually runs)

- **Container runtime**: <Docker Compose / Podman / k3s — and the version>
- **Compose/stack files live in**: <repo path, and how they map to hosts>
- **Reverse proxy**: <Caddy / Traefik / nginx> — config at <path>, TLS via <ACME method>
- **DNS**: <resolver, where records are edited, the fallback resolver>
- **Storage**: <ZFS/btrfs/ext4; pools, mounts, what is redundant and what is not>
- **Backups**: <tool, schedule, destination, retention> — restore path documented in <runbook>
- **Monitoring**: <Prometheus/Grafana/Loki endpoints; where rules and dashboards live in the repo>
- **Secrets**: <how they reach services — env files, a secret store — and where they are NOT>

## Hosts

| Host | Role | OS | Notable constraints |
|---|---|---|---|
| <nuc-01> | <app services> | <Debian 12> | <8 GB RAM — no memory-hungry additions> |

## Conventions this lab expects

- Image tags are **pinned**; `:latest` is a finding.
- Every service has: pinned source configuration, deliberate restart behavior, one useful health
  signal, rollback, and an end-to-end check. Backup/restore, proxy/TLS/auth, alert/runbook, and
  isolation/limits follow the service-onboard applicability predicates. Its canonical inventory or
  runbook records all four predicate outcomes and the facts that support them.
- Config is in the repo and applied from there — never edited live and left undocumented.
- <naming convention for containers, volumes, networks>
- <how a change reaches the lab: git push then pull, or applied by hand>

## Stay in lane

Agents working on this lab: **do not propose a platform change** — no migration to Kubernetes, no
new orchestrator, no swapping the proxy or the storage layer — as part of an ordinary service or
troubleshooting task. Those are lab-shaping decisions that go up the ladder
(`sde-agents:principal-engineer`, including multi-year
commitments), and they arrive as a proposal for the operator, never as part of a fix. Work within
the stack above, or hand the decision up and say why.

## Known quirks

- <the thing that always trips people up: a service that must start after another, a host with a
  flaky NIC, a container that needs a manual step after a reboot>

## Change tiers in this lab

`sde-agents:homelab-engineer` owns change authority. Local specifics it needs:

- **Console/out-of-band access**: <how you reach a host if the network change locks you out>
- **The management path that must survive every change**: <gateway, switch, AP addresses>
- **What is never touched without the operator present**: <the NAS, the router, the ISP handoff>
