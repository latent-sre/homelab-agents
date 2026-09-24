# Claude Code frontmatter — agents & skills

Read this before writing or editing the frontmatter of any agent or skill file. It is the fleet's
**single source of truth** for Claude Code frontmatter facts — the two prose copies it replaced (in
`prompt-craft`'s body and `agents/prompt-engineer.md`) drifted within one release, so platform facts
live here and only here. `validate_fleet.py` keeps the authoritative *field sets*
(`KNOWN_AGENT_FIELDS`, `KNOWN_SKILL_FIELDS`) checked against code; on any conflict with the live
docs (code.claude.com/docs/en/sub-agents, code.claude.com/docs/en/skills), the docs win — update
this file, re-verify after CLI upgrades.

## Agents

Locations: `agents/*.md` in a plugin; `.claude/agents/*.md` project-level; `~/.claude/agents/*.md`
user-level. A project-level definition shadows a user-level one of the same name.

Required: `name`, `description` (the trigger). Optional: `tools`, `disallowedTools`, `model`,
`permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`,
`omitClaudeMd`, `effort`, `isolation`, `color`, `initialPrompt`, `experimental`.

What a subagent starts with (doc-checked 2026-09-23, CLI 2.1.281): its body plus environment
details as the system prompt — **not** Claude Code's system prompt, so none of its built-in git
or safety guidance applies and a definition must state what its agent needs. It also loads every
CLAUDE.md level (user, project, local, and `AGENTS.md` imports) unless `omitClaudeMd` is set, and
always a git status snapshot. By default a subagent may spawn subagents of its own up to three
layers below the main conversation.

These fields affect authority where Claude honors them. Check scope and effective permissions;
plugin exceptions below can make a field inert.

| Field | Notes |
|---|---|
| `tools` | Availability allowlist for built-ins **and MCP tools**. **Omitting it inherits every tool** — omission is "all tools," not "none." Exact MCP names use `mcp__<server>__<tool>`; `mcp__<server>` and `mcp__<server>__*` are server-wide patterns. This fleet permits only exact entries in `FLEET_MCP_TOOLS`, because a server-wide pattern silently acquires tools added later. Include `ToolSearch` when approved MCP tools are deferred. **A permission-rule specifier here is inert**: `Bash(git diff:*)` on an agent's `tools:` list restricts nothing (probed on CLI 2.1.200 and re-probed 2026-09-13 on 2.1.270 with both spellings under `default` and `dontAsk` — the agent ran `git status` exactly like one granted a bare `Bash`, although the subagent reference now describes the specifier as an enforced allowlist), because specifiers work only in settings.json permission rules or a PreToolUse hook. It reads as a limit and is none, so the fleet's validator rejects the form outright. `Agent(worker)` scoping works only for a main-thread agent (`claude --agent`); a subagent silently ignores the type list, so it reads like a limit and isn't one. `AskUserQuestion`, `EnterPlanMode`, `ScheduleWakeup`, `WaitForMcpServers` are never available to a subagent, however listed; `ExitPlanMode` only under `permissionMode: plan`, which a plugin-shipped agent can't set. |
| `disallowedTools` | Denylist; applied before `tools` resolves. |
| `permissionMode` | `default \| acceptEdits \| auto \| dontAsk \| bypassPermissions \| plan \| manual`. Ignored for plugin-shipped agents, so this fleet (a plugin) rejects the field outright — `validate_fleet.py` flags it as configuration that does not exist. |
| `hooks` | Agent-scoped lifecycle hooks. Real at project/user scope, **inert in a plugin**. A plugin must instead ship `hooks/hooks.json`, which is session-wide, and scope the hook itself on the payload's `agent_type` — that is how this fleet guards `sde-agents:code-reviewer`'s `Bash`. |
| `skills` | Preloads full skill content at startup — prefer this over putting `Skill` in `tools`. Don't list a `disable-model-invocation: true` skill here — the fleet's validator rejects it as policy. (Documented behavior is that such skills can't be preloaded; since that flag is unreliable in a plugin — see the caveat under Skills below — the fleet enforces the rule rather than depending on the runtime honoring it.) |
| `model` | Aliases `haiku \| sonnet \| opus \| fable \| inherit`, or a full ID (`claude-opus-4-8`); defaults to `inherit`. Use an alias — this fleet rejects pins, which rot silently while an alias follows the upgrade. |
| `memory` | `user \| project \| local`. **Setting it auto-enables Read, Write, and Edit** — never add it to a read-only agent (it would silently widen `sde-agents:code-reviewer`'s mandate). |

Also: `maxTurns` (int), `background` (bool), `omitClaudeMd` (bool, CLI 2.1.271+; withholds the
user, project, and local CLAUDE.md files, not the git status snapshot — `sde-agents:researcher`
sets it), `effort` (`low|medium|high|xhigh|max`), `isolation` (`worktree`; the worktree branches
from the default branch, not the parent's `HEAD`, unless settings set `worktree.baseRef: "head"`),
`color`, `initialPrompt` (main-session only), `experimental` (`cacheTtl`).

Plugin-packaged agents **ignore** `hooks`, `mcpServers`, and `permissionMode`, and do not support
`initialPrompt` — a guard that works locally is silently absent once the agent ships in a plugin. Spell keys exactly: an unrecognized key
is not guaranteed to fail loudly, so a typo can silently drop what it configured
(`validate_fleet.py` rejects unknown keys for that reason).

## Skills

Locations: `skills/<name>/SKILL.md` in a plugin; `.claude/skills/<name>/SKILL.md` project-level.
Precedence for **same-named non-namespaced skills** is the **reverse** of agents: a personal
(user-level) skill overrides a project-level one — enterprise → personal → project → bundled. Plugin
skills are namespaced (`plugin:name`, e.g. `sde-agents:service-onboard`) and don't participate in
that chain — a same-named project skill does not shadow them.

Core fields: `name`, `description` (the trigger), `argument-hint`. Behavior switches:

- `disable-model-invocation: true` — intended for side-effect skills (deploy, send, commit):
  user-only via `/name`, description removed from the model's context, and not preloadable via an
  agent's `skills:` field. **Caveat — version-sensitive, not timeless.** On CLI 2.1.212 the flag
  was ignored outright for plugin-shipped skills (anthropics/claude-code#22345, verified
  2026-07-17). Probed again 2026-08-16 on CLI 2.1.233: the listing half now works — both of this
  plugin's flagged skills were absent from a live session's model-visible skill listing — but
  whether Skill-tool invocation is also blocked for a plugin skill remains unprobed, so keep
  making the skill's own content defer authority rather than treating the flag as an enforced
  boundary. Re-verify after CLI upgrades — `scripts/probe_plugin.py` is the capability test — and
  update this stamp. (Docs also state the flag stops scheduled-task firings that name the skill,
  as of v2.1.196 — doc-checked 2026-07-24 and again 2026-09-13, not probed.)
- `user-invocable: false` — background-knowledge skills, hidden from the `/` menu.
- `allowed-tools` **grants** (pre-approves, no permission prompt) while the skill is active — it
  does **not** restrict availability. Takes bare tool names or permission-rule specifiers
  (`Bash(git add *)`).
- `disallowed-tools` **removes** tools while the skill is active (clears on the next user message) —
  this is the restricting field.

Also available: `when_to_use`, `arguments`, `model`, `effort`, `context`, `agent`, `background`
(with `context: fork`; `false` waits for the forked result in the invoking turn), `hooks`, `paths`,
`shell` — not exhaustive; see code.claude.com/docs/en/skills for the current table
(`validate_fleet.py` keeps `KNOWN_SKILL_FIELDS` as the fleet's checked copy). Skill/subagent
frontmatter `hooks` are scoped to the component's lifecycle — registered when it activates,
cleaned up when it finishes; a subagent's `Stop` converts to `SubagentStop` (doc-checked
2026-07-30). Whether a **plugin-shipped skill's** `hooks` fire is unprobed — plugin *agents*
ignore the field outright (see above), so treat this as unenforced in a plugin until
`scripts/probe_plugin.py` proves otherwise.

## Platform environment facts (doc-checked 2026-07-30, CLI 2.1.220 era; the `${CLAUDE_PLUGIN_DATA}`, `/doctor`, and `/verify` bullets re-checked against the docs 2026-09-13 with CLI 2.1.270 current — unchanged)

- **`${CLAUDE_PLUGIN_DATA}`** — per-plugin persistent directory (`~/.claude/plugins/data/{id}/`),
  created on first reference, survives plugin updates; exported to hook processes. The place for
  installed dependencies, generated state, caches — never the plugin tree itself.
- **`CLAUDE_ENV_FILE`** — available to `SessionStart` hooks: append `export` lines there to
  persist environment variables for the session's later Bash commands (append, don't truncate —
  other hooks share it).
- **`/doctor`** — a bundled skill (was a built-in command before v2.1.205): diagnoses setup,
  flags unused skills/MCP servers/plugins against their context cost and slow hooks, trims
  checked-in `CLAUDE.md` of content derivable from the codebase, and migrates always-loaded
  guidance into on-demand skills — reports first, asks before changing. `claude doctor` from the
  terminal is the read-only form.
- **`/verify`** — a bundled skill (v2.1.145+): builds and runs the app to confirm a change does
  what it should. Since v2.1.215 it runs only when the user invokes it, never autonomously.

- **Skill-listing character budget** (probed 2026-08-16, CLI 2.1.233 — binary constants plus live
  headless sessions). The model-visible skill listing is budgeted at context-window tokens × 4
  chars/token × `skillListingBudgetFraction` (default 0.01) — exactly **8,000 characters on a
  200k-token model** — with each description also capped at `skillListingMaxDescChars` (1536).
  Over budget, entries are not dropped: plugin and user entries silently degrade to bare
  `- name` lines with **no description**, greedily by priority, while Anthropic-bundled skills
  are exempt and charge the budget first; the only signal is a debug-log warning. Live: a
  200k-window model rendered 18 of this fleet's 19 entries name-only, while larger-window models
  rendered all in full. Workflows list exactly like skills (`- plugin:name: meta description`)
  and spend the same budget. `scripts/fleet_doctor.py` estimates this fleet's Claude footprint
  (`repository.skill-listing-budget`) under those recorded assumptions; it does not measure the
  active host's context, settings, or complete catalog. Consuming repositories can raise
  `skillListingBudgetFraction` / `skillListingMaxDescChars` in settings, or override outright
  with the `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable.

**Codex uses a separate token budget.** Current
[configuration documentation](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml)
defines `skills.max_context_tokens`: by default 2% of the model context, with explicit values capped
at 10,000 tokens (source checked 2026-09-12). Do not apply Claude's character estimate or settings to
Codex. Establish the target host's model, settings, and listing before making a visibility claim.

Keep descriptions lean — they load into context every session, and past the listing budget above
a long description does not degrade gracefully: it disappears entirely on the hosts that
truncate, taking its routing with it.

## Fleet decisions on unused fields

Fields the fleet deliberately does not use — considered, not overlooked. Reopen only with a reason:

- **`when_to_use`** — trigger phrasings live in `description` so routing has one surface to tune
  (and one surface for the routing evals to measure). Both fields share the same 1,536-character
  listing cap, so splitting saves nothing.
- **`maxTurns`** — loop bounds are task-shaped prose rules (three-strikes, two-round review caps),
  which fail with a diagnosis. A capped agent returns partial output that the caller can resume
  (CLI 2.1.246+), so the cap is cheaper than it was, but no runaway loop has been observed to
  justify one. Revisit if one is.
- **`memory`** — agents are stateless by design; durable lab knowledge lives in the repo (runbooks,
  `CLAUDE.md`). And setting `memory` auto-enables Read/Write/Edit, so it must never be added to
  `sde-agents:code-reviewer`.

## Plain-scalar descriptions and the CLI's stricter parser

A plain (unquoted) `description:` containing `: ` followed by a colon-bearing token (e.g.
`skills: sde-agents:backend-craft`) parses in the runtime and in `scripts/validate_fleet.py` but
fails `claude plugin tag` with "Unexpected token", blocking the release path — observed 2026-08-02
on `code-craft` at CLI 2.1.220, while `claude plugin validate --strict` and sibling descriptions
with a simple `: ` passed.
Double-quote the whole scalar when a description contains a namespaced reference after a colon;
the rendered string is identical, so routing and evals are unaffected. Quoting works only while
the text needs no internal escapes: the adapter generator copies the raw value, so `\"` sequences
land literally in generated copies (observed same day) — a description that would need escaped
quotes gets a punctuation reword instead.
