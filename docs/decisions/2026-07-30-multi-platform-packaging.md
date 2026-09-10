# Multi-platform packaging and authority adapters

**Status:** Accepted and implemented on 2026-07-30; Codex import bridge amended 2026-08-02;
generated-lane support level and its field-contradiction reopen trigger amended 2026-08-10
(LANE-001); Copilot CLI lane and the Codex `/import` bridge retired 2026-08-18
**Date:** 2026-07-30

## Context

The fleet was authored as a Claude Code plugin. Codex, GitHub Copilot CLI, and VS Code Agent
Plugins can consume similar Markdown skills and agents, but their formats are not interchangeable:

- Claude agent definitions use Claude frontmatter, plugin namespaces, preloaded skills, and
  `${CLAUDE_PLUGIN_ROOT}`.
- Copilot and VS Code custom agents use `.agent.md` files and host tool aliases. Their
  `PreToolUse` payload does not identify the active custom agent.
- Codex custom agents are standalone TOML with a sandbox mode. Codex plugins package skills,
  hooks, apps, and MCP servers, but not custom-agent TOML.
- Codex and Copilot express explicit skill invocation differently.

Copying the Claude files unchanged would therefore preserve the appearance of controls while
silently dropping namespaces, tool restrictions, paths, or hooks.

The format comparison uses the current official
[VS Code Agent Plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins),
[Copilot CLI plugin](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference),
[Codex plugin](https://developers.openai.com/plugins/build/plugins), and
[Codex custom-agent](https://learn.chatgpt.com/docs/agent-configuration/subagents.md)
contracts. Runtime behavior still belongs to each installed host version.

## Decision

### One authored fleet

`agents/` and `skills/` remain the only authored definitions. Claude Code loads them directly.
`scripts/generate_platform_adapters.py` derives every other host artifact and the fleet validator
compares the tracked output byte for byte.

Generated artifacts are:

| Host | Agent artifact | Skill artifact | Package entry point |
|---|---|---|---|
| Claude Code | `agents/*.md` | `skills/*` | `.claude-plugin/plugin.json` |
| Copilot CLI / VS Code | `.github/agents/*.agent.md` | `platforms/copilot/skills/*` | `plugin.json` |
| Codex | `.codex/agents/*.toml` | `plugins/sde-agents/skills/*` | `.agents/plugins/marketplace.json` → nested `.codex-plugin/plugin.json` |

Codex's official one-time `/import` route additionally consumes generated
`.claude/agents/*.md`. Those files are an import bridge, not another authored fleet; the generator
derives them from the same canonical `agents/*.md` sources and the validator checks their currency.

The Codex plugin is nested deliberately. Its plugin root has no `hooks/hooks.json`, so default
component discovery cannot load Claude's session hook.

### Translate authority, not just syntax

Claude retains its session-wide allowlist hook for roles whose Bash contract is read-only.
Copilot and VS Code do not expose the active agent identity in `PreToolUse`, so those guarded roles
receive no `execute` tool. Codex profiles with no canonical write tool request
`sandbox_mode = "read-only"`; canonical writers request `workspace-write`. Those values are agent
defaults rather than immutable boundaries: parent live permission changes and full-access mode
override them and are reapplied to child agents. Codex custom-agent TOML also has no per-agent
tool allowlist, so inherited shell and subagent capabilities remain available unless an outer
boundary removes them.

The adapters therefore state Codex no-write, no-shell, and no-spawn mandates as cooperative when
parent authority remains broader. Document-only authority, approval requirements, and live-effect
limits likewise remain cooperative unless the host provides a stronger outer control.

Claude `skills:` preloads become explicit required-skill instructions because neither generated
agent format packages that frontmatter contract. Agent bodies and prompt-authoring references also
replace Claude-only hook, tool-name, and context-inheritance claims with the target host's actual
boundary.

### Keep host-specific skill policy

Both generated skill copies remove Claude namespaces and installed-root paths and serialize
frontmatter as valid YAML. Copilot retains `disable-model-invocation: true`. Codex removes that
unsupported value and generates `agents/openai.yaml` with
`policy.allow_implicit_invocation: false`.

### Distribute Codex agents honestly

Codex plugins currently do not package custom-agent TOML. The repository keeps `.codex/agents/`
for project-scoped use and provides `scripts/install_codex_agents.py` for an explicit user or
alternate project sync. The installer owns only marked files, adopts unmarked files only when their
parsed contract matches the current generated agent, preflights every behaviorally different
conflict before mutation, and prunes only stale managed files. This permits official importer
formatting without treating changed instructions or extra authority as generated. User-scope sync
uses `$CODEX_HOME/agents` when configured and otherwise defaults to `~/.codex/agents`.

## Rejected alternatives

- **Load the Claude files unchanged everywhere.** Rejected because syntax that looks plausible but
  is ignored is worse than an explicit adapter.
- **Reuse the Claude hook on every host.** Rejected because its scope depends on an active-agent
  payload field that Copilot, VS Code, and Codex do not provide on `PreToolUse`.
- **Use one shared "portable" skill copy.** Rejected because Copilot and Codex encode
  explicit-invocation policy differently.
- **Keep the Codex manifest at repository root.** Rejected because Codex default discovery would
  see Claude's incompatible `hooks/hooks.json`.
- **Maintain four authored fleets.** Rejected because fixes and authority changes would drift
  independently with no reliable owner.
- **Use symlinks for generated components.** Rejected because installed plugin archives and
  Windows checkouts do not preserve a dependable cross-host symlink contract.

## Consequences

- Any canonical agent or skill edit owes adapter regeneration.
- Generation rejects symlinks, junctions, and reparse points in canonical resources and generated
  roots so a local indirection cannot redirect reads or recursive replacement.
- Untracked Python cache residue is ignored only when Git proves it is untracked; archives and
  other non-worktree copies validate cache-shaped files strictly.
- An added host contract becomes a generator and validator change, not another hand-maintained
  corpus.
- Claude routing measurements remain measurements of the canonical descriptions. Generated-only
  wording does not trigger a second routing-eval gate.
- Generated lanes are therefore **supported but limited** (amended 2026-08-10): they carry the same
  content and host-appropriate authority, but not the same measurement, so a discovery or
  delegation behavior specific to one host is found in the field rather than in CI. The sanctioned
  repair is a cheap host-neutral change that the Claude harness can still measure — LANE-001's
  `onboarding-map`, a model-visible, side-effect-free pointer, is the worked example. A per-host
  routing harness stays out of scope; a lane limit that cannot be repaired that way is documented
  where users of that lane see it, in the README's install section for the host.
- Copilot/VS Code and Codex runtime smoke tests remain version-specific manual checks; offline CI
  proves structure, parity, generated currency, and the authority mapping.
- A change to the Codex import bridge or adoption rule owes a disposable live `/import` run; a
  Codex CLI upgrade is the freshness trigger for repeating that check.

## Reopen triggers

- A host gains a reliable active-agent identity in `PreToolUse`.
- Codex plugins gain first-class custom-agent packaging.
- A real workload on a generated lane contradicts a consequence of this record. The 2026-08-02
  Codex onboarding-discoverability field report (issue #61) is the first: the routing sentence
  shipped in the generated agent, yet plain-language intent had no model-reachable path to it, so
  "Claude routing measurements remain measurements of the canonical descriptions" was hiding a real
  behavioral gap rather than merely scoping a gate.
- A host adds an enforceable skill-level tool deny that can replace a cooperative boundary.
- A manifest or frontmatter version changes the discovery or invocation contract.

## Amendment, 2026-08-18 — three lanes retired

Reopen trigger hit: *"a manifest or frontmatter version changes the discovery or invocation
contract."* Reading VS Code 1.133.0's shipped bundles showed this record's host table described a
discovery contract that does not hold. Evidence:
`docs/archive/2026-08/vscode-discovery-investigation-2026-08-18.md` (retired to Git history).

**Retired:**

- **The Codex `/import` staging lane.** `.claude/agents/` was generated as migration input, but it is
  also Claude Code's own project-agent path *and* a VS Code agent-discovery path. Both hosts loaded
  the staging copies as a second fleet — measured at 22 agents for 11 roles. `/import` was never an
  update mechanism (it skips existing destinations), and `.codex/agents` already satisfies project
  scope, so the bridge bought nothing that `install_codex_agents.py` does not.
- **The Copilot CLI lane.** Dropped as a target. The root `plugin.json` it required is rejected by VS
  Code for lacking a valid `$schema`, so it served no other host.
- **A stray empty `.codex-plugin/`** at the repository root, which would have made the root a Codex
  plugin root had a manifest ever landed in it.

**Corrected:** this record and `AGENTS.md` both held that `hooks/copilot-hooks.json`, a deliberately
empty override, kept Copilot *and VS Code* from loading the Claude guard. It did not. VS Code reads
component overrides from the format's own manifest — `.claude-plugin/plugin.json` — never from the
root manifest that referenced the override, so it fell back to format 1's `hookConfigPath`,
`hooks/hooks.json`: the guard itself. A green test asserted the override's contents and therefore
proved nothing about the host it was named for. **Keeping a non-Claude host away from the guard is
structural — no file at that host's own hook-config path — never a declared manifest field.**

**Superseded in the host table:** the Copilot CLI / VS Code row. VS Code is now served by workspace
discovery of `.github/agents` only. Installing this repository as a VS Code plugin loads the
canonical Claude fleet and is unsupported; it cannot be prevented from inside the repository,
because VS Code treats any directory holding `.claude-plugin/plugin.json` as an installable plugin
and Claude Code requires that file at the root. Skills are not yet on a VS-Code-discovered path.

**Not revisited:** the one-authored-fleet decision, authority translation, host-specific skill
policy, and the nested Codex plugin root all stand unchanged. The nesting rationale is in fact
strengthened: the same reasoning that kept Claude's hook out of `plugins/sde-agents/` is what the
repository root could not offer VS Code.

## Amendment, 2026-08-24 — VS Code skills moved onto a discovered path

The generated VS Code skill tree moves from the retired Copilot CLI location
`platforms/copilot/skills/` to `.github/skills/`, a default VS Code workspace discovery path. The
generator owns the relocation and retains the old path as a retired root so regeneration removes
stale copies instead of leaving two plausible skill fleets. HOST-010 and HOST-011 close together:
the same move makes the adapted skills reachable and eliminates the orphaned output tree.

Evidence: the current official
[Agent Skills documentation](https://github.com/microsoft/vscode-docs/blob/main/docs/agent-customization/agent-skills.md)
lists `.github/skills/` as a default project location. VS Code's source declares the same workspace
root in
[`promptFileLocations.ts`](https://github.com/microsoft/vscode/blob/40f27cc166304afa356ab59fea79468e23113fce/src/vs/workbench/contrib/chat/common/promptSyntax/config/promptFileLocations.ts#L169),
and its end-to-end discovery suite exercises a skill at that path in
[`customizationDiscoverySuite.ts`](https://github.com/microsoft/vscode/blob/40f27cc166304afa356ab59fea79468e23113fce/src/vs/platform/agentHost/test/node/e2e/suites/customizationDiscoverySuite.ts#L95).
