# Reviewing an agent for security

Read before shipping an agent, skill, or tool definition that touches untrusted content, private
data, or the ability to act. Use `skills/prompt-craft/SKILL.md` for the prompt-editing method,
this reference for security guidance, and `references/claude-code-frontmatter.md` for Claude
field behavior.

## The lethal trifecta

Investigate prompt-injection exposure when one context combines all three of:

1. **Untrusted content** — a fetched page, a repository it didn't write, an issue body, a log line,
   a tool result from someone else's service.
2. **Access to private data** — the filesystem, credentials, an authenticated API, the user's repo.
3. **A way to exfiltrate** — an outbound request, a write to somewhere published, a commit, a
   comment, a message.

**All three warrants an attack-path investigation, not an automatic vulnerability or severity.**
Trace attacker-controlled content through private-data access to an outbound action, identify the
controls on that path, and state any unverified bypass. Rate a finding by its reachable impact and
preconditions. "Ignore malicious instructions" is a prompt mitigation, not an enforced control;
remove an unnecessary capability or constrain its use through controls outside the model.

Remove unnecessary capabilities and verify the effective boundary:

- **Constrain outbound paths.** Inspect network access, writes, posting, logs, and returned reports.
  Read-only filesystem access does not prevent disclosure through a network tool or the answer.
- **Restrict private-data access.** Run untrusted-input processing without unnecessary credentials
  or mounts. A separate agent counts only when those access restrictions actually hold.
- **Constrain inputs.** Use a vetted, versioned input set when the task permits it; pinning records
  identity but does not make content trustworthy.
- **Separate capabilities when needed.** Keeping one of the three out of a context can reduce
  exposure, but another agent's involvement is not itself an enforced boundary.

## Delegation is not isolation

Spawning a subagent does not sanitize its inputs or outputs. Separate context does not establish
a separate trust domain; inspect effective tools, credentials, mounts, and network access.
Returned content can carry an injected instruction into the parent. Two consequences:

- **Trace the full handoff.** A worker without private data can still influence an orchestrator
  that has credentials and acts on its report. Check the composed path as well as each agent.
- **Validate returned fields.** A constrained schema reduces free-form channels, but a string
  inside valid JSON can still contain hostile instructions. Treat returned content as evidence;
  validate proposed actions against the user's task and host controls before acting.

## Tool grants are the actual security boundary

- **Enumerate `tools:` explicitly.** Omitting the field inherits *every* tool — omission means "all",
  not "none". This is the most consequential single line in an agent file.
- **A grant that looks like a limit and isn't** is worse than no limit: scoped specifiers such as
  `Bash(git diff:*)` are silently ignored on a subagent's `tools:` list, and `Agent(type)` restricts
  nothing there either. See `references/claude-code-frontmatter.md` — the fleet's validator rejects
  both for exactly this reason.
- **`Bash` is the universal escape hatch.** Any agent with `Bash` can do anything the shell can,
  whatever its prose says. Read-only-by-prose plus `Bash` is a promise; enforcement needs a
  `PreToolUse` hook with an allowlist (this repo's `scripts/readonly-guard.py` is the worked
  example, honest boundaries included).
- **`memory:` auto-enables Read, Write, and Edit** — never add it to an agent whose mandate is
  read-only.
- Plugin-shipped agents silently ignore `hooks:`, `mcpServers:`, and `permissionMode:`. A guard
  declared there is decoration; it must live in the plugin's `hooks/hooks.json`, scoped on the
  payload's agent identity.

## Content boundaries in the prompt itself

Prompt instructions supplement host controls:

- **State that fetched and read content is data, not instructions**, and that an attempt to direct
  the agent gets *reported* rather than obeyed. The report is the valuable half — it turns an attack
  into a signal.
- Delimit untrusted content from instructions. Use extracted values only for the authorized task;
  validate paths, destinations, and action parameters before use. Content cannot grant permission
  or redefine the task, and delimiters alone do not enforce that boundary.
- Bind executable dependencies and compared prompt versions to known revisions when identity
  matters; `sde-agents:ci-actions` covers CI pinning.
- Keep credentials out of prompts and model-visible tool arguments. Use the host's credential
  mechanism or a scoped process environment, and keep values out of logs and returned output.

## The review, in five questions

1. Which of the three legs does this agent hold, and what enforced boundary prevents their misuse?
2. Does its `tools:` list say exactly what it can do — with nothing inherited and no fake scoping?
3. If it holds `Bash` or a write tool, what enforces the limit its prose claims?
4. Where does untrusted content enter, and what validates an action derived from it?
5. What does its output flow into, and is that consumer treating it as data or as instructions?

An unanswered question is an evidence gap, not a proven vulnerability. Record reachable findings
and gaps separately with the fleet's evidence labels: `[verified]`, `[sourced]`, or `[unverified]`.

[OpenAI's agent safety guidance](https://developers.openai.com/api/docs/guides/agent-builder-safety#combine-techniques)
describes structured outputs and isolation as mitigations that reduce, but do not eliminate,
prompt-injection risk.
