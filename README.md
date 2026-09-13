# SDE Agents

A Claude Code plugin for one person who runs a home lab and wants AI agents that behave like a
careful operator: inspect before changing, finish an explicitly delegated task within its scope,
keep recovery ready, and record the result. It ships agents for running the lab and for writing the
scripts and services that live on it, skills that carry the operating knowledge, and two hooks
that enforce their scoped read-only and live-command policies.

## Fleet

<!-- fleet-inventory:start -->
- **Agents (10):** `application-security-auditor`, `code-reviewer`, `homelab-engineer`, `multi-agent-architect`, `principal-engineer`, `prompt-engineer`, `repository-investigator`, `researcher`, `sde-fullstack`, `verification-engineer`
- **Skills (20):** `backend-craft`, `ci-actions`, `code-craft`, `eng-ladder`, `frontend-craft`, `host-onboard`, `lab-audit`, `lab-incident`, `observability`, `onboarding-map`, `postmortem`, `prompt-craft`, `restore-drill`, `root-cause`, `runbook`, `security-audit`, `self-improve-loop`, `service-onboard`, `sre-tool`, `upgrade-campaign`
<!-- fleet-inventory:end -->

## Install

```
/plugin marketplace add latent-sre/sde-agents
/plugin install sde-agents@latent-sre
```

That installs the agents, the skills, and the two hooks together. Nothing is copied into the
`~/.claude/agents` or `~/.claude/skills` discovery roots — Claude Code keeps its own cached copy of
the plugin, which a reinstall replaces, so the fleet you edit here is never the fleet a normal
session loads. Components are namespaced by the plugin: `sde-agents:homelab-engineer`,
`/sde-agents:lab-incident`, and so on.

To load the plugin from a checkout instead of the marketplace copy, run `claude --plugin-dir .`
from the repository root.

## What you get

**Running the lab.** `homelab-engineer` is the operator's agent: it classifies every change by
how reversible it is and states recovery before acting. A bounded live request covers execution
and recovery; it asks again for an expanded scope or a destructive consequence you have not
authorized, and respects every actual host gate. It works the operating skills: `lab-incident` when something is down,
`root-cause` when the fix keeps not sticking, `runbook`, `postmortem`, `restore-drill`,
`upgrade-campaign`, `observability`, and the `lab-audit` and `security-audit` checklists. Bringing
a new machine or a new service into the lab runs `host-onboard` and `service-onboard`.

**Writing what runs on it.** `sde-fullstack` builds scripts, services, and small tools, with
`code-craft` (Bash and PowerShell pitfalls included), `backend-craft`, `frontend-craft`, and
`ci-actions` as its reference shelf. `code-reviewer` reviews a diff read-only. `researcher` handles
dedicated external-source investigations; `principal-engineer` and `multi-agent-architect` can
also consult the web for design work.

**Design and meta.** `principal-engineer` thinks through a change
before it is built. `prompt-engineer`, `prompt-craft`, `multi-agent-architect`, and
`self-improve-loop` are for people editing agents and skills, this fleet's included.

Ask in plain language. The right agent or skill fires from its description; you can also name one
directly with its namespaced name.

## How it protects you

Two `PreToolUse` hooks ship with the plugin and register session-wide. Each scopes itself to the
agent making the call and does nothing for anyone else, so your own shell is never inspected.

- **The read-only guard.** `code-reviewer`, `principal-engineer`, and
  `repository-investigator` hold `Bash` for inspection only. The guard permits an enumerated set
  of read-only commands (`git diff`, `rg`, `cat`, and their kin) and denies everything else,
  including any interpreter. If the guard cannot run, those agents lose Bash rather than gaining
  it.
- **The optional live-effect gate.** Default `host` policy leaves decisions to the host's actual
  permissions. To retain the extra command-level prompt, the operator sets
  `SDE_AGENTS_LIVE_EFFECT_POLICY=prompt` in the environment launching Claude before the session.
  In that policy, listed live commands from `homelab-engineer` and unparseable forms ask, or deny
  when prompts are suppressed. Unset or `host` adds no decision; invalid values fail closed for
  that agent. This setting grants no task authority and agents must not change it to authorize
  their own work. Existing host prompts and denials always apply.

Both hooks run from the installed plugin copy, never from a repository under review. Neither is a
sandbox: a reviewer that can read files can read secrets, and the load-bearing control remains the
least privilege you give the session. The wiring, the reasoning, and the honest limits are in
`docs/fleet-development.md`.

## Project context convention

Use the target repository's existing project-instruction file and do not create a competing one.
For a new cross-host repository, prefer a portable root `AGENTS.md`.

Claude Code natively loads `CLAUDE.md` (project, user, and managed levels) and passes it to
subagents automatically; it does **not** read a bare `AGENTS.md`
([memory docs](https://code.claude.com/docs/en/memory): "Claude Code reads `CLAUDE.md`, not
`AGENTS.md`"). A repository using portable `AGENTS.md` therefore needs a root `CLAUDE.md` containing
a single `@AGENTS.md` import — on Windows the docs recommend the import over a symlink — or Claude
Code never sees it. Codex consumes `AGENTS.md` directly. GitHub's
[support matrix](https://docs.github.com/en/copilot/reference/custom-instructions-support)
(checked 2026-09-10) distinguishes Copilot surfaces:

- The cloud agent and CLI support `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` agent instructions.
- GitHub.com code review supports `AGENTS.md`, repository-wide, and path-specific instructions.
- VS Code Chat supports `AGENTS.md`, repository-wide, and path-specific instructions; VS Code
  code review lists only `.github/copilot-instructions.md`.

The matrix does not list `REVIEW.md`; use its per-surface entries for other hosts and features.
Copilot reading `CLAUDE.md` does not make a `CLAUDE.md` bridge portable: whether any non-Claude
host expands the `@file` import is unverified, so a bridge file is one line of nothing to a host
that does not. Record the environment card and mission block in the file the current host actually
loads.

This repository follows its own convention: guidance for working on the fleet lives in a portable
root `AGENTS.md`, bridged by a `CLAUDE.md` containing that single import.

Long-running work should use the progress file declared by that project context. When none is
declared, use `.agents/PROGRESS.md` — and in a parallel batch, one shard per builder
(`.agents/progress/<component>.md`), one writer per file, with the orchestrator's plan file
(`.agents/plan.md`) owned by the orchestrator alone. Progress files are coordination state, not a
substitute for the final review packet or committed documentation.

## Other hosts

Claude Code is the primary host. Generated adapters for VS Code and Codex are kept current by the
validator, with the authority each host can actually enforce; the details are in
`docs/fleet-development.md`.

**VS Code.** Open the repository as a workspace folder. The generated `.github/agents/*.agent.md`
profiles and `.github/skills/` are discovered with no install step. Do **not** install the
repository as a VS Code plugin: that path loads the canonical Claude fleet unadapted, including a
hook VS Code cannot scope.

**Codex.**

```bash
codex plugin marketplace add latent-sre/sde-agents
codex plugin add sde-agents@latent-sre
python3 scripts/install_codex_agents.py --user
```

The plugin carries the skills; the installer syncs the agent profiles into `~/.codex/agents` and
is the update path for them. On Codex, the onboarding skills are reached by name
(`$service-onboard`), and agents are reached by explicit request rather than routed from their
descriptions.

## Upgrade campaigns

Name the hosts/services and maintenance window. The campaign reuses existing inventory, patching
procedures, release guidance, and applicable restore evidence; it verifies each deployment and
recovers failures within the delegated scope. A major version alone does not require a new session.
After recovery, independent authorized upgrades can continue; unresolved shared failures stop
related work. The [bounded-campaign decision](docs/decisions/2026-09-11-bounded-upgrade-campaign.md)
records the behavior and host limits.

Claude's shipped live-effect hook still prompts for listed commands and denies them when prompts
are suppressed; unbound/unparseable forms also ask/deny. The hook is a partial filter: only when
it returns no decision does execution proceed under the host's own permission flow. Skills cooperatively route Claude live work to the engineer; that routing does
not remove main-loop tools. Direct Copilot skills also hand live commands to the operator.
Codex uses its effective permissions without a fleet-invented prompt; required native prompts
and denials still apply. The Copilot profile has no execution tool and hands live commands to
the operator. Changing prose
neither removes a host gate nor supplies a missing tool.

## Working on the fleet

`AGENTS.md` is the rulebook every editing session loads: what to validate before pushing, the
change playbooks, and the hard rules. `CONTRIBUTING.md` owns the pull-request procedure: branch
naming, the template, and supported reviewer triggers, with operator handoff when the host cannot
request a pass. `docs/fleet-development.md` holds the long-form material: which file owns which
convention, how the hooks are wired and why, how the fleet is validated and probed, and how to
import from another fleet. `docs/fleet-roadmap.md` is the only task tracker. After any agent or
skill edit, regenerate the host adapters; after adding, renaming, or removing a component, refresh
the inventory above:

```bash
python3 scripts/generate_platform_adapters.py --write
python3 scripts/validate_fleet.py --write-inventory
```
