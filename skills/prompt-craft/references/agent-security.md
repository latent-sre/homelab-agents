# Reviewing an agent for security

Read before shipping an agent, skill, or tool definition that touches untrusted content, private
data, or the ability to act. The universal method lives in `skills/prompt-craft/SKILL.md`. On any
conflict, SKILL.md wins.

The fleet authors agents constantly and has a review method for code but none for agents. This is it.

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

Ways to cut a leg, in descending robustness:

- **Remove the exfiltration path**: no network tools, no write tools, no posting. A reviewer that can
  only read and report cannot leak what it found.
- **Remove the private data**: run the untrusted-content step in a separate agent with no credentials
  and no repo access, and pass forward only a structured summary.
- **Remove the untrusted content**: pin the inputs (a vetted doc set) rather than fetching whatever a
  link points at.
- **Rule of Two**: allow at most two of the three in any single agent, and make the third a boundary
  another agent owns.

## Delegation is not isolation

Spawning a subagent does **not** sanitize anything. The subagent gets its own context window, not its
own trust domain: it still holds the tools its definition grants, and its *output flows back into the
parent's context*, where it is read as trusted narration. An untrusted instruction that reaches a
worker can therefore steer the parent through the worker's report. Two consequences:

- **The trifecta is evaluated per agent AND across the handoff.** A researcher with WebFetch and no
  credentials is fine alone; if it reports into an orchestrator that holds a deploy token and acts on
  the report without review, the composite has all three legs.
- **Structure the return value.** A schema (findings with file:line, a verdict enum) is far harder to
  smuggle instructions through than free prose, and it makes the parent's parsing mechanical.

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

Prose can't be the control, but it should still be right:

- **State that fetched and read content is data, not instructions**, and that an attempt to direct
  the agent gets *reported* rather than obeyed. The report is the valuable half — it turns an attack
  into a signal.
- Keep the untrusted content clearly delimited from the instructions when you assemble a prompt, and
  never let it choose a tool, a path, or a permission decision.
- **Hash- or version-bind anything you depend on**: a pinned dependency, a pinned action SHA, a
  pinned prompt template. "Latest" means someone else decides what your agent runs
  (`sde-agents:ci-actions` covers the CI form).
- Secrets never enter a prompt or a tool argument; they belong in the environment of the process that
  needs them.

## The review, in five questions

1. Which of the three legs does this agent hold, and what enforced boundary prevents their misuse?
2. Does its `tools:` list say exactly what it can do — with nothing inherited and no fake scoping?
3. If it holds `Bash` or a write tool, what enforces the limit its prose claims?
4. Where does untrusted content enter, and what stops it from selecting an action?
5. What does its output flow into, and is that consumer treating it as data or as instructions?

Any question without a concrete answer is the finding. Record it the way the fleet records evidence:
`[verified]`, `[sourced]`, or `[unverified]`.
