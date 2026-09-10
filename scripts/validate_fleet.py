#!/usr/bin/env python3
"""Validate this repository's canonical agent and skill definitions.

The validator intentionally uses only the Python standard library. It checks
the local ``agents/`` and ``skills/`` layout instead of assuming a particular
runtime's generated directories.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# The generator owns the generated-root set. Its validator access is lazy, so importing it here is
# acyclic while letting both package imports and direct script execution resolve the same source.
if __package__:
    from . import generate_platform_adapters  # noqa: E402
else:
    import generate_platform_adapters  # noqa: E402

# The fleet's one parser lives in fleet_records; these names are re-exported here because
# generate_platform_adapters.py and the test suite reach them as attributes of this module. A
# second frontmatter or reference parser would let the graph and the validator disagree about the
# same tree with nothing to arbitrate them.
import fleet_records  # noqa: E402  (sibling module; scripts/ is not a package)
from fleet_records import (  # noqa: E402  (sibling module; scripts/ is not a package)
    LIST_ITEM_RE,
    NAME_RE,
    TOP_LEVEL_KEY_RE,
    definition_markdown_files,
    frontmatter_span,
    is_runtime_byproduct,
    parse_frontmatter,
    parse_frontmatter_lines,
    read_text,
    split_tools,
)

# The optional `./` is load-bearing. Without it the lookbehind rejected any link written
# `./references/foo.md`, so such a link matched nothing: the existence check never ran (a broken
# path shipped silently) and the orphan check counted the target as unlinked. The dot remains in
# the leading boundary: without it matching restarts inside `../references` or
# `foo.references`, incorrectly treating either as a local bundle path. Both consumers strip the
# allowed prefix before comparing, so the two valid spellings resolve to the same file.
BUNDLE_REF_RE = re.compile(
    r"(?<![\w./])(?:\./)?(?:references|assets|scripts)/[A-Za-z0-9._/-]*[A-Za-z0-9_-]"
)
# The two free-prose frontmatter fields — the only ones whose value is a sentence, so the only ones
# that can carry a colon-space into a plain YAML scalar. See validate_yaml_scalar_quoting.
PROSE_SCALAR_FIELDS = ("description", "argument-hint")
INVENTORY_RE = re.compile(
    r"<!-- fleet-inventory:start -->.*?<!-- fleet-inventory:end -->",
    re.DOTALL,
)
# Two different questions, two different errors: keep runtime schema ("is this a real Claude Code
# value?") separate from fleet policy ("do we permit it?"). Claude Code accepts these aliases AND any
# full model ID that `--model` takes, e.g.
# `claude-opus-4-8` (per code.claude.com/docs/en/sub-agents). This fleet deliberately allows only the
# aliases: a pinned ID goes stale silently while an alias follows the model upgrade. So a full ID is
# a POLICY failure (valid runtime value, banned here) and anything else is a SCHEMA failure (not a
# model at all) — never report them as the same thing.
ALIAS_MODELS = {"inherit", "haiku", "sonnet", "opus", "fable"}
FULL_MODEL_ID_RE = re.compile(r"^claude-[a-z0-9]+(?:-[a-z0-9]+)+$")
# Every frontmatter key Claude Code defines for a subagent (code.claude.com/docs/en/sub-agents).
# This exists to close a silent-disarm hole, not for tidiness: the validator used to check only the
# VALUES of keys it knew and never the KEY NAMESPACE, so a misspelled key was dropped on the floor.
# That matters because `hooks:` on code-reviewer is what installs the read-only guard on an agent
# holding Bash — misspell it `hook:` and (before this check) the validator passed, the hook-wiring
# test passed, and the guard was gone. Whether the runtime errors or silently ignores an unknown key
# is UNDOCUMENTED, so we refuse to depend on the answer: an unknown key fails here.
KNOWN_AGENT_FIELDS = {
    "name",
    "description",
    "tools",
    "disallowedTools",
    "model",
    "permissionMode",
    "maxTurns",
    "skills",
    "mcpServers",
    "hooks",
    "memory",
    "background",
    "effort",
    "isolation",
    "color",
    "initialPrompt",
}
# Every documented SKILL.md frontmatter field (code.claude.com/docs/en/skills, frontmatter table).
# Same rationale as KNOWN_AGENT_FIELDS: an unrecognized key is not guaranteed to fail loudly, so a
# typo silently drops what it configured — a `disable-model-invocaton` or `user-invokable` slip would
# quietly turn a side-effect skill model-invocable, or expose a background skill, with no error. The
# agent path had this check; the skill path did not (external-review gap). Kept in sync with the docs
# by hand; `claude plugin validate --strict` is the backstop for anything added upstream since.
KNOWN_SKILL_FIELDS = {
    "name",
    "description",
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "allowed-tools",
    "disallowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "background",
    "hooks",
    "paths",
    "shell",
}
# Claude Code SILENTLY IGNORES these three on a PLUGIN-SHIPPED agent: "For security reasons,
# `hooks`, `mcpServers`, and `permissionMode` are not supported for plugin-shipped agents"
# (code.claude.com/docs/en/plugins-reference). Probed on CLI 2.1.200: a plugin agent's frontmatter
# hook never fired, while a byte-identical hook on a project-scope agent did.
#
# This fleet SHIPS AS A PLUGIN, so any of them here is configuration that does not exist. `hooks:`
# is the dangerous one — it is how the read-only guard used to be attached to `code-reviewer`, and
# leaving it would read as armor while providing none. An agent that LOOKS guarded and isn't is
# strictly worse than one that is honestly unguarded, because nobody goes looking. The guard now
# lives in hooks/hooks.json (session-wide) and scopes itself on the payload's `agent_type`.
#
# This replaces the old `bypassPermissions` value check: banning `permissionMode` outright covers
# it, and the old error ("it would nullify the read-only guard") is no longer even true for a
# plugin agent — the field is ignored, so it nullifies nothing. Wrong reasons rot into wrong fixes.
PLUGIN_INERT_AGENT_FIELDS = {"hooks", "mcpServers", "permissionMode"}
# Tools that make an agent a WRITER. An agent holding Bash but none of these is a read-only agent
# whose only route to mutation is the shell — exactly what the guard exists to close.
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
# The `tools:` field IS the authority an agent is granted, so it gets the same runtime-schema vs
# fleet-policy split as `model`: RUNTIME_TOOLS answers "is this a real Claude Code tool?" and
# FLEET_TOOLS answers "do we grant it here?". A typo (`Wrte`) is a schema error; a real-but-unadopted
# tool (`PowerShell`) is a policy error you can lift deliberately. Collapsing the two would either
# let typos through or make the validator a mirror of the runtime with no opinion of its own.
#
# Canonical table: code.claude.com/docs/en/tools-reference. Note `BashOutput`, `KillShell`, and
# `SlashCommand` were previously allowed here and appear nowhere in it — they were accepted names
# that grant nothing.
RUNTIME_TOOLS = {
    # "Task" was renamed to "Agent" in 2.1.63 and survives only as a deprecated alias; we take the
    # canonical name so a legacy `Task` grant fails and gets rewritten. Do not "fix" Agent -> Task.
    "Agent", "Artifact", "AskUserQuestion", "Bash", "CronCreate", "CronDelete", "CronList", "Edit",
    "EnterPlanMode", "EnterWorktree", "ExitPlanMode", "ExitWorktree", "Glob", "Grep",
    "ListMcpResourcesTool", "LSP", "Monitor", "NotebookEdit", "PowerShell", "PushNotification",
    "Read", "ReadMcpResourceTool", "RemoteTrigger", "ReportFindings", "ScheduleWakeup", "SendMessage",
    "SendUserFile", "ShareOnboardingGuide", "Skill", "TaskCreate", "TaskGet", "TaskList", "TaskOutput",
    "TaskStop", "TaskUpdate", "TodoWrite", "ToolSearch", "WaitForMcpServers", "WebFetch", "WebSearch",
    "Workflow", "Write",
}
# What this fleet actually grants. Widen deliberately; every entry is authority.
FLEET_TOOLS = {
    "Agent", "Bash", "Edit", "Glob", "Grep", "NotebookEdit", "Read", "Skill", "TodoWrite",
    "ToolSearch", "WebFetch", "WebSearch", "Write",
}
# MCP tools share the `tools:` availability allowlist with built-ins, but their namespace is
# runtime-configured rather than a closed Claude Code table. Keep a separate exact allowlist so
# every external capability is an explicit fleet decision. Server-level grants (`mcp__server` or
# `mcp__server__*`) are valid runtime syntax but forbidden here: they silently acquire whatever a
# future server release adds. That is already unsafe for GitHits, whose read-only evidence tools
# sit beside `feedback`, an external write.
EVIDENCE_MCP_TOOLS = {
    "mcp__claude_ai_Context7__query-docs",
    "mcp__claude_ai_Context7__resolve-library-id",
    "mcp__plugin_context7_context7__query-docs",
    "mcp__plugin_context7_context7__resolve-library-id",
    "mcp__plugin_githits_githits__code_files",
    "mcp__plugin_githits_githits__code_grep",
    "mcp__plugin_githits_githits__code_read",
    "mcp__plugin_githits_githits__docs_list",
    "mcp__plugin_githits_githits__docs_read",
    "mcp__plugin_githits_githits__get_example",
    "mcp__plugin_githits_githits__pkg_changelog",
    "mcp__plugin_githits_githits__pkg_deps",
    "mcp__plugin_githits_githits__pkg_info",
    "mcp__plugin_githits_githits__pkg_upgrade_review",
    "mcp__plugin_githits_githits__pkg_vulns",
    "mcp__plugin_githits_githits__search",
    "mcp__plugin_githits_githits__search_language",
    "mcp__plugin_githits_githits__search_status",
}
FLEET_MCP_TOOLS = set(EVIDENCE_MCP_TOOLS)
LOCAL_REPOSITORY_TOOLS = {"Glob", "Grep", "Read"}
EXTERNAL_RESEARCH_TOOLS = {"ToolSearch", "WebFetch", "WebSearch", *EVIDENCE_MCP_TOOLS}
# Investigation roles are deliberately split at the tool layer. A role that holds private source
# and fetched external content can leak one into the other through prompt injection even when its
# prose says not to. Pin both required and forbidden authority so a one-line frontmatter edit cannot
# silently collapse that trust boundary.
#
# `repository-investigator` REQUIRES Bash — for git history and revision identity — and that grant
# is admissible only because the read-only guard covers it (Bash with no write tool compels roster
# membership, checked below) and the guard scopes the allowlist's one network family away from it:
# the `gh` readers are GitHub fetches, granted via NETWORK_AGENT_NAMES to the review/design roles and
# deliberately withheld from this role (PR #141 review finding). The
# application-security-auditor keeps Bash forbidden: its mandate is to be safe against a HOSTILE
# repository, and the guard's own docstring names the git-config ext-diff vector that a shell —
# even an allowlisted one — opens against a repo that arrives as a directory.
REQUIRED_AGENT_TOOLS = {
    "application-security-auditor": set(LOCAL_REPOSITORY_TOOLS),
    "repository-investigator": {*LOCAL_REPOSITORY_TOOLS, "Bash"},
    "researcher": set(EXTERNAL_RESEARCH_TOOLS),
}
FORBIDDEN_AGENT_TOOLS = {
    "application-security-auditor": {
        "Agent", "Bash", "Edit", "NotebookEdit", "ToolSearch", "WebFetch", "WebSearch", "Write",
        *EVIDENCE_MCP_TOOLS,
    },
    "repository-investigator": {
        "Agent", "Edit", "NotebookEdit", "ToolSearch", "WebFetch", "WebSearch", "Write",
        *EVIDENCE_MCP_TOOLS,
    },
    "researcher": {
        "Agent", "Bash", "Edit", "Glob", "Grep", "NotebookEdit", "Read", "Write",
    },
}
# Real tools that a SUBAGENT never receives, however they are listed, because they depend on the main
# conversation's UI or session state (code.claude.com/docs/en/sub-agents). Everything in agents/ is a
# subagent definition, so granting one of these is a no-op that reads like a capability.
SUBAGENT_UNAVAILABLE_TOOLS = {
    "AskUserQuestion",
    "EnterPlanMode",
    "ExitPlanMode",  # unless permissionMode is `plan`
    "ScheduleWakeup",
    "WaitForMcpServers",
}
# A tools entry: a bare name, or a name with a parenthesized scope, e.g. `Agent(worker, researcher)`.
TOOL_ENTRY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\((.*)\))?$")
# Exact MCP names use the runtime's `mcp__<server>__<tool>` convention. Hyphens are real in tool
# names (`query-docs`, `resolve-library-id`), so the built-in-name grammar above cannot parse them.
# Server names are normalized to one underscore-delimited segment; `__` remains the separator.
MCP_EXACT_TOOL_RE = re.compile(r"^mcp__[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+$")
MCP_SERVER_GRANT_RE = re.compile(r"^mcp__[A-Za-z0-9_.-]+(?:__\*)?$")


# Canonical evidence-label phrasing; agent files may extend a definition but
# must contain these exact stems so the triad cannot drift file by file.
EVIDENCE_LABEL_STEMS = (
    "**[verified]** (you ran or observed it",
    "**[sourced]** (cited to file:line, URL, or query)",
    "**[unverified]** (assumption or couldn't check)",
)
EVIDENCE_LABEL_RE = re.compile(r"\*\*\[(?:un)?(?:verified|sourced)\]\*\*")
# The workflow packet schemas carry the same evidence triad as the agents' prose packets, as a
# bare enum. If either side drifts, nothing errors at load time -- the mismatch surfaces as a
# schema-validation failure five retries deep inside a live workflow run, billed and late. Pin
# the enum to the canonical stems so the drift is a validation failure at commit time instead.
WORKFLOW_EVIDENCE_ENUM = tuple(
    stem.split("[", 1)[1].split("]", 1)[0] for stem in EVIDENCE_LABEL_STEMS
)  # ("verified", "sourced", "unverified"), derived so the triad has exactly one authoring point
WORKFLOW_EVIDENCE_ENUM_RE = re.compile(
    r"const\s+EVIDENCE\s*=\s*\[([^\]]*)\]"
)
PACKET_HEADING_RE = re.compile(
    r"^##\s.*\bpacket\b|^##\s+Output format\b", re.IGNORECASE | re.MULTILINE
)
# Perishable platform facts get exactly ONE home inside agents/ and skills/, so when the platform
# moves, the correction lands once instead of chasing prose copies. Keys are literal substrings
# searched in every definition markdown file; values are the only file (repo-relative POSIX path)
# allowed to carry them. The complete issue identifier below is the upstream
# disable-model-invocation-ignored-for-plugin-skills bug: it had already been copied into an agent
# body once, and a stale copy keeps teaching the old platform behavior with no runtime error after
# the issue closes. Pin the full identifier rather than its common numeric suffix so unrelated
# ports, record IDs, and metrics remain valid definition content.
PERISHABLE_TOKENS = {
    "anthropics/claude-code#22345": "skills/prompt-craft/references/claude-code-frontmatter.md",
}
# AGENTS.md drift tripwires. The guide paraphrases the validator and the repo layout, and prose has
# no runtime: Claude Code loads CLAUDE.md (not AGENTS.md), so a lost `@AGENTS.md` import orphans the
# guide without an error; a renamed script leaves it pointing at nothing; an alias change leaves it
# teaching a stale policy. Same doctrine as EVIDENCE_LABEL_STEMS — pin the paraphrase to its source
# and fail loudly when they part.
GUIDE_IMPORT = "@AGENTS.md"
# The program map exists specifically so the engineering program's documentation cannot go stale,
# which makes it the one document least entitled to stale paths of its own: it is held to the same
# path-drift tripwire as the guide. Self-gating — a repo that does not carry the map makes no
# map claims.
PROGRAM_DOC = "docs/engineering-program.md"
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
# A path-shaped token inside an inline code span. Deliberately excludes glob/placeholder characters
# (`*`, `<`, `>`, `$`, `{`) so illustrative forms like `agents/*.md` and `skills/<name>/SKILL.md`
# self-exclude and only concrete, resolvable paths are asserted.
GUIDE_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_./-]*")


def validate_name(name: str, kind: str, source: Path) -> list[str]:
    issues: list[str] = []
    if not name:
        return [f"{source}: missing {kind} name"]
    if len(name) > 64:
        issues.append(f"{source}: {kind} name exceeds 64 characters")
    if not NAME_RE.fullmatch(name):
        issues.append(f"{source}: invalid {kind} name {name!r}")
    return issues


def validate_description(fields: dict[str, str], kind: str, source: Path) -> list[str]:
    description = fields.get("description", "").strip()
    if not description:
        return [f"{source}: missing {kind} description"]
    if len(description) > 1024:
        return [f"{source}: {kind} description exceeds 1024 characters"]
    return []


def validate_agents(root: Path) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    names: list[str] = []
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return [f"{agents_dir}: missing agents directory"], names

    for path in sorted(agents_dir.glob("*.md")):
        fields = parse_frontmatter(path)
        if fields is None:
            issues.append(f"{path}: missing or malformed frontmatter")
            continue

        for key in fields:
            if key not in KNOWN_AGENT_FIELDS:
                issues.append(
                    f"{path}: unknown frontmatter key {key!r} is not a Claude Code agent field. "
                    f"An unrecognized key does not fail loudly at load time, so a typo here silently "
                    f"drops whatever it was meant to configure."
                )
            elif key in PLUGIN_INERT_AGENT_FIELDS:
                issues.append(
                    f"{path}: frontmatter key {key!r} is SILENTLY IGNORED for a plugin-shipped agent, "
                    f"and this fleet ships as a plugin. Declaring it configures nothing while reading "
                    f"as though it does. The read-only guard belongs in hooks/hooks.json, scoped on "
                    f"the payload's 'agent_type'."
                )

        name = fields.get("name", "")
        names.append(name or path.stem)
        issues.extend(validate_name(name, "agent", path))
        if name and name != path.stem:
            issues.append(f"{path}: agent name {name!r} must match filename {path.stem!r}")
        issues.extend(validate_description(fields, "agent", path))

        tools = fields.get("tools", "").strip()
        parsed_tools: list[str] = []
        if not tools:
            # Not a harmless omission: an absent `tools:` INHERITS EVERY TOOL rather than granting
            # none, so a reviewer meant to be read-only would silently receive Write and Edit.
            issues.append(f"{path}: missing explicit tools authority (omitting it inherits ALL tools)")
        else:
            parsed_tools = split_tools(tools)
            if len(parsed_tools) != len(set(parsed_tools)):
                issues.append(f"{path}: duplicate tool in tools authority")
            for tool in parsed_tools:
                if tool.startswith("mcp__"):
                    if MCP_EXACT_TOOL_RE.fullmatch(tool):
                        if tool not in FLEET_MCP_TOOLS:
                            issues.append(
                                f"{path}: MCP tool {tool!r} is structurally valid but is not adopted "
                                f"by this fleet; add it to FLEET_MCP_TOOLS deliberately if the agent "
                                f"needs it"
                            )
                    elif MCP_SERVER_GRANT_RE.fullmatch(tool):
                        issues.append(
                            f"{path}: server-wide MCP grant {tool!r} is real Claude Code syntax but "
                            f"is not adopted by this fleet. It silently acquires future tools from "
                            f"that server, so list each required exact tool in FLEET_MCP_TOOLS"
                        )
                    else:
                        issues.append(
                            f"{path}: malformed MCP tool entry {tool!r} in tools authority; expected "
                            f"an exact mcp__<server>__<tool> name"
                        )
                    continue

                entry = TOOL_ENTRY_RE.match(tool)
                if not entry:
                    issues.append(f"{path}: malformed tool entry {tool!r} in tools authority")
                    continue
                base, scope = entry.group(1), entry.group(2)

                if base not in RUNTIME_TOOLS:
                    issues.append(f"{path}: unknown tool {base!r} in tools authority is not a Claude Code tool")
                elif base in SUBAGENT_UNAVAILABLE_TOOLS:
                    issues.append(
                        f"{path}: tool {base!r} is never available to a subagent regardless of this "
                        f"grant (it needs the main conversation's UI or session state); granting it "
                        f"reads like a capability the agent does not have"
                    )
                elif base not in FLEET_TOOLS:
                    issues.append(
                        f"{path}: tool {base!r} is a real Claude Code tool but is not adopted by this "
                        f"fleet; add it to FLEET_TOOLS deliberately if the agent needs it"
                    )

                if scope is not None and base == "Agent":
                    # The trap: `Agent(worker)` restricts spawning ONLY for an agent running as the
                    # main thread (`claude --agent`). In a subagent definition the parenthesized type
                    # list is IGNORED, so this grants UNRESTRICTED spawn while reading like a limit.
                    issues.append(
                        f"{path}: scoped grant {tool!r} does not restrict anything here. The "
                        f"Agent(type) allowlist applies only to a main-thread agent (claude --agent); "
                        f"in a subagent definition the type list is ignored and spawning is "
                        f"unrestricted. Use a bare 'Agent' so the grant matches reality"
                    )
                elif scope is not None:
                    issues.append(
                        f"{path}: scoped grant {tool!r} uses permission-rule syntax that the "
                        f"frontmatter 'tools:' field SILENTLY IGNORES. Probed on CLI 2.1.200: an agent "
                        f"granted `Bash(git diff:*)` ran `git status` exactly like one granted a bare "
                        f"`Bash` — the specifier restricts nothing while reading as though it does. "
                        f"Specifiers work only in settings.json permission rules (session-wide) or a "
                        f"PreToolUse hook; narrow there, not here."
                    )

        required_tools = REQUIRED_AGENT_TOOLS.get(name, set())
        missing_required_tools = sorted(required_tools - set(parsed_tools))
        if missing_required_tools:
            issues.append(
                f"{path}: evidence role {name!r} is missing required tools "
                f"{missing_required_tools}. Its investigation method depends on this exact side of "
                f"the local-versus-external trust boundary, so removing authority silently makes "
                f"the method impossible"
            )
        forbidden_tools = sorted(FORBIDDEN_AGENT_TOOLS.get(name, set()) & set(parsed_tools))
        if forbidden_tools:
            issues.append(
                f"{path}: trust-separated role {name!r} holds forbidden tools {forbidden_tools}. "
                f"Local/private repository access and external fetched content must not coexist in "
                f"one subordinate role; prose cannot enforce that boundary"
            )

        # `skills:` is in KNOWN_AGENT_FIELDS, which only checks that the KEY is real -- it says
        # nothing about whether each listed VALUE resolves to anything. Two ways that silently
        # disarms preloading: a typo'd or dropped skill name (skills/<name>/SKILL.md doesn't exist),
        # and a skill that sets `disable-model-invocation: true` -- such a skill cannot be preloaded
        # ("preloading draws from the same set of skills Claude can invoke"), so listing it here is a
        # no-op that reads like a guarantee.
        for skill_name in (entry.strip() for entry in fields.get("skills", "").split(",")):
            if not skill_name:
                continue
            skill_file = root / "skills" / skill_name / "SKILL.md"
            if not skill_file.is_file():
                issues.append(
                    f"{path}: skills: entry {skill_name!r} does not resolve to "
                    f"skills/{skill_name}/SKILL.md -- preloading silently drops it"
                )
                continue
            skill_fields = parse_frontmatter(skill_file) or {}
            if skill_fields.get("disable-model-invocation", "").strip().lower() == "true":
                issues.append(
                    f"{path}: skills: entry {skill_name!r} names {skill_file}, which sets "
                    f"disable-model-invocation: true -- a skill so marked CANNOT be preloaded "
                    f"(preloading draws from the same set of skills Claude can invoke), so listing "
                    f"it here configures nothing"
                )

        model = fields.get("model", "").strip()
        aliases = ", ".join(sorted(ALIAS_MODELS))
        if not model:
            issues.append(f"{path}: missing model")
        elif model in ALIAS_MODELS:
            pass
        elif FULL_MODEL_ID_RE.match(model):
            issues.append(
                f"{path}: model {model!r} is a valid Claude Code model but is pinned; "
                f"this fleet requires an alias ({aliases}) so agents follow model upgrades "
                f"instead of rotting on a stale pin"
            )
        else:
            issues.append(f"{path}: unknown model {model!r} (expected one of: {aliases})")

        content = read_text(path)
        if EVIDENCE_LABEL_RE.search(content):
            for stem in EVIDENCE_LABEL_STEMS:
                if stem not in content:
                    issues.append(
                        f"{path}: evidence labels drifted from canonical phrasing; expected {stem!r}"
                    )
        if not PACKET_HEADING_RE.search(content):
            issues.append(
                f"{path}: missing end-of-task packet ('## ... packet' or '## Output format' section)"
            )

    if not names:
        issues.append(f"{agents_dir}: no agent definitions found")
    if len(names) != len(set(names)):
        issues.append(f"{agents_dir}: duplicate agent names")
    return issues, sorted(names)


def bundle_references(skill_file: Path) -> set[str]:
    """Every bundle path named in SKILL.md, normalized so `./references/x.md` and `references/x.md`
    are the same reference. Both direction checks read this, so they cannot disagree on spelling.
    """
    return {
        match.group(0).rstrip(".,;:)]}").removeprefix("./")
        for match in BUNDLE_REF_RE.finditer(read_text(skill_file))
    }


def validate_bundle_references(root: Path, skill_dir: Path, skill_file: Path) -> list[str]:
    issues: list[str] = []
    for reference in sorted(bundle_references(skill_file)):
        local_target = skill_dir / Path(reference)
        shared_target = root / Path(reference)
        if not local_target.exists() and not shared_target.exists():
            issues.append(f"{skill_file}: referenced file does not exist: {reference}")
    return issues


def validate_reference_orphans(skill_dir: Path, skill_file: Path) -> list[str]:
    """The other direction from validate_bundle_references: every file under references/ must be
    named by at least one link in SKILL.md.

    validate_bundle_references only ever asks "does the thing this link points at exist?" -- it never
    asks the reverse. So a references/*.md file with no routing-table row is invisible to it: the
    validator stays green, the tests stay green, and the probe only ever exercises the rows that DO
    have links. Dead knowledge that looks shipped.
    """
    issues: list[str] = []
    references_dir = skill_dir / "references"
    if not references_dir.is_dir():
        return issues
    linked = bundle_references(skill_file)
    for ref_file in sorted(references_dir.rglob("*")):
        if not ref_file.is_file():
            continue
        rel = ref_file.relative_to(skill_dir).as_posix()
        if rel not in linked:
            issues.append(
                f"{ref_file}: orphaned -- no skill-relative link to {rel!r} found in {skill_file}; a "
                f"reference file with no routing-table row is unreachable by any means. Routing-table "
                f"links must be written skill-relative (e.g. {rel!r}) -- a full path such as "
                f"'{skill_dir.name}/{rel}' will not be recognized by this check"
            )
    return issues


def validate_skills(root: Path) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    names: list[str] = []
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return [f"{skills_dir}: missing skills directory"], names

    for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            issues.append(f"{skill_dir}: missing SKILL.md")
            continue

        fields = parse_frontmatter(skill_file)
        if fields is None:
            issues.append(f"{skill_file}: missing or malformed frontmatter")
            continue

        for key in fields:
            if key not in KNOWN_SKILL_FIELDS:
                issues.append(
                    f"{skill_file}: unknown frontmatter key {key!r} is not a Claude Code skill field. "
                    f"An unrecognized key is not guaranteed to fail loudly, so a typo silently drops "
                    f"what it configured (e.g. 'disable-model-invocaton' would leave a side-effect "
                    f"skill model-invocable)."
                )

        name = fields.get("name", "")
        names.append(name or skill_dir.name)
        issues.extend(validate_name(name, "skill", skill_file))
        if name and name != skill_dir.name:
            issues.append(
                f"{skill_file}: skill name {name!r} must match directory {skill_dir.name!r}"
            )
        issues.extend(validate_description(fields, "skill", skill_file))
        issues.extend(validate_bundle_references(root, skill_dir, skill_file))
        issues.extend(validate_reference_orphans(skill_dir, skill_file))

    if not names:
        issues.append(f"{skills_dir}: no skill definitions found")
    if len(names) != len(set(names)):
        issues.append(f"{skills_dir}: duplicate skill names")
    return issues, sorted(names)


# YAML's complete double-quoted escape set (spec 1.2 §7.3.1): these single characters, plus
# `\x`/`\u`/`\U` with exactly 2/4/8 hex digits. Anything else is "found unknown escape character"
# and the parser refuses the document. Skipping backslash-plus-one unconditionally let
# `description: "Use C:\q"` through (review finding, PR #120) — a Windows path in a description is
# exactly how an author writes that by accident. Single-quoted scalars are deliberately absent from
# this map: YAML gives them no backslash escapes at all, so a backslash there is one literal
# character and validating it would invent a rule the parser does not have.
_DOUBLE_QUOTE_ESCAPES = frozenset('0abtnvfre"/\\N_LP \t')
_HEX_ESCAPE_WIDTHS = {"x": 2, "u": 4, "U": 8}
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
# A well-formed `\u`/`\U` escape can still name something that is not a character. YAML escapes
# denote scalar VALUES, and the surrogate block exists only to encode pairs inside UTF-16 — a lone
# one is not a code point a loader can produce, and nothing above U+10FFFF exists at all. Counting
# hex digits accepted both (review finding, PR #120), so a description could carry `\uD800` and
# still ship: this validator keeps the bytes, a strict loader refuses the document, and the
# component goes missing with no error. `\x` needs no range check — two hex digits cannot leave
# 0x00-0xFF.
_SURROGATE_RANGE = range(0xD800, 0xE000)
_MAX_CODE_POINT = 0x10FFFF


def _flow_scalar_defect(value: str) -> str | None:
    """Name why a quoted YAML flow scalar is unusable here, or return None when it is fine.

    YAML ends a flow scalar at the FIRST unescaped matching quote, so "does a quote appear later
    in the line" is not the question. Asking only that let `description: "ok"oops` through, and —
    worse, because it reads as ordinary prose — `description: 'Use the agent's output`, which
    closes at the apostrophe in "agent's" and leaves `s output` as trailing tokens.

    **One case is deliberately stricter than YAML**, and it is the only place in this rule that
    rejects a legal document. YAML drops a ` # comment` after a closing quote; `parse_frontmatter`
    above is not comment-aware — it takes the line and calls `.strip("'\\"")`, which removes the
    outer quote characters and nothing else. So `description: "Use when routing." # note` parses to
    `Use when routing." # note` and every generated host copy ships that string as the description
    (executed, PR #120). Accepting it because YAML would was the wrong call: the fleet's readers are
    this parser and the hosts downstream of it, not a conforming one.

    Escapes are honored in both directions — a doubled `''` inside a single-quoted scalar and the
    real escape set inside a double-quoted one — because a value that merely LOOKS malformed would
    be a false red on a legal file, and the caller's whole point is that only the strict parser can
    see the difference.
    """
    quote = value[0]
    index = 1
    while index < len(value):
        char = value[index]
        if quote == '"' and char == "\\":
            following = value[index + 1: index + 2]
            if not following:
                return (
                    "ends on a dangling backslash with nothing to escape, so the scalar never "
                    "closes"
                )
            width = _HEX_ESCAPE_WIDTHS.get(following)
            if width is not None:
                digits = value[index + 2: index + 2 + width]
                if len(digits) != width or not set(digits) <= _HEX_DIGITS:
                    return (
                        f"carries the malformed hex escape "
                        f"{value[index: index + 2 + width]!r}, which needs exactly {width} hex "
                        f"digits; a conforming YAML parser refuses the document over it"
                    )
                if following in "uU":
                    code_point = int(digits, 16)
                    if code_point in _SURROGATE_RANGE:
                        return (
                            f"escapes the lone surrogate U+{code_point:04X} "
                            f"({value[index: index + 2 + width]!r}); surrogates encode UTF-16 "
                            f"pairs and are not scalar values, so a strict loader refuses the "
                            f"document while this parser keeps the bytes"
                        )
                    if code_point > _MAX_CODE_POINT:
                        return (
                            f"escapes U+{code_point:04X} "
                            f"({value[index: index + 2 + width]!r}), above the Unicode maximum "
                            f"U+{_MAX_CODE_POINT:04X}; no such character exists, so a strict "
                            f"loader refuses the document while this parser keeps the bytes"
                        )
                index += 2 + width
                continue
            if following not in _DOUBLE_QUOTE_ESCAPES:
                return (
                    f"carries the invalid escape sequence {value[index: index + 2]!r}; a "
                    f"conforming YAML parser refuses the document with 'found unknown escape "
                    f"character', while this validator's parser keeps the backslash and every "
                    f"generated copy ships it"
                )
            index += 2
            continue
        if char == quote:
            if quote == "'" and value[index + 1: index + 2] == "'":
                index += 2
                continue
            tail = value[index + 1:].strip()
            if not tail:
                return None
            if tail.startswith("#"):
                return (
                    f"closes its {quote} quote and then carries the comment {tail!r}. YAML would "
                    f"drop that comment, but `parse_frontmatter` in this file is not "
                    f"comment-aware: it strips only the outer quote characters, so the value "
                    f"becomes {value.strip(chr(39) + chr(34))!r} and every generated host copy "
                    f"ships the comment as literal description text. This rule is deliberately "
                    f"stricter than YAML here"
                )
            return (
                f"closes its {quote} quote and then carries the trailing token(s) {tail!r}, which "
                f"a conforming YAML parser refuses"
            )
        index += 1
    return f"opens a {quote} quote that never closes on its line"


def validate_yaml_scalar_quoting(root: Path) -> list[str]:
    """Reject a frontmatter scalar that a conforming YAML parser refuses to read.

    Two ways to write one, and the rule owes both. A plain (unquoted) scalar may not contain `: `
    — a real parser reads it as a nested mapping key and raises "mapping values are not allowed
    here". A QUOTED scalar fails differently: it must close on its line, carry only escapes YAML
    defines *naming code points that exist*, and be followed by nothing — so `"ok"oops`,
    `'Use the agent's output`, `"Use C:\\q"`, and `"\\uD800"` are refused too
    (`_flow_scalar_defect` above names which). Nothing else in this repository can
    see any of them: `parse_frontmatter` above is a hand-rolled subset that reads to end of line,
    and every generated host copy re-serializes the value through `json.dumps`, so the offending
    bytes exist only in the canonical file and every check downstream of them passes. The failure
    lands on whichever host loads frontmatter with a strict parser — the component does not error,
    it does not load, and the fleet ships one skill silently absent.

    One case is stricter than YAML on purpose: a ` # comment` after the closing quote is legal YAML
    and is still rejected, because `parse_frontmatter` is not comment-aware and would ship the
    comment as literal description text on every host. The rule serves this repository's readers,
    not a conforming one. Quote the value, close the quote, and put nothing after it.
    """

    issues: list[str] = []
    paths = sorted((root / "agents").glob("*.md")) if (root / "agents").is_dir() else []
    if (root / "skills").is_dir():
        paths += sorted((root / "skills").glob("*/SKILL.md"))

    for path in paths:
        lines = read_text(path).splitlines()
        end = frontmatter_span(lines)
        if end is None:
            continue  # Absent or unterminated frontmatter is the agent/skill rules' report to make.

        for line in lines[1:end]:
            # TOP_LEVEL_KEY_RE is anchored at column zero, so the indented continuation lines of a
            # `description: >` block scalar never reach this check — and a colon-space is legal
            # inside one, which is why they must not.
            match = TOP_LEVEL_KEY_RE.match(line)
            if not match:
                continue
            key, value = match.groups()
            value = value.strip()
            if key not in PROSE_SCALAR_FIELDS or not value:
                continue
            # A quoted scalar may hold anything — but only once its quote CLOSES, closes with
            # nothing after it, and escapes nothing YAML does not define. Skipping on the opening
            # character alone left the rule's own failure mode reachable one typo over:
            # `description: "Use when routing: requests` is read to end of line by
            # `parse_frontmatter` above, re-serialized into valid generated copies, and passed
            # here, while a strict parser runs past the newline hunting the close quote and
            # refuses the file — the same silently absent component, arrived at differently
            # (review finding, PR #107). Each shape carries its own consequence in the message,
            # because they do not share one: most are files a conforming parser refuses, while the
            # trailing-comment case is legal YAML that only THIS repository's reader mangles.
            if value[0] in "\"'":
                defect = _flow_scalar_defect(value)
                if defect is None:
                    continue
                issues.append(
                    f"{path}: {key!r} frontmatter value {defect}. Nothing downstream can see it: "
                    f"this validator's parser takes the whole line and every generated copy "
                    f"re-serializes what it took, so the fleet validates while the host either "
                    f"drops the component with no error anyone sees or ships the wrong string. "
                    f"Close the quote, and put nothing after it."
                )
                continue
            # A flow collection (`argument-hint: [a path: here]`) parses too — badly, as a list of
            # one-pair mappings, but it PARSES, and this rule may only claim what it can prove:
            # that a strict parser refuses the file outright.
            if value[0] in "[{":
                continue
            if ": " in value:
                issues.append(
                    f"{path}: unquoted {key!r} frontmatter value contains ': ', which a "
                    f"conforming YAML parser rejects as a nested mapping key. This validator's "
                    f"own parser and every generated copy quote or re-serialize the value, so "
                    f"the whole fleet validates while a host that parses strict YAML drops the "
                    f"component without an error anyone sees. Wrap the value in double quotes."
                )

    return issues


def validate_bare_skill_references(root: Path, skill_names: list[str]) -> list[str]:
    """A bare backticked skill name in an agent body asserts "already in context".

    AGENTS.md reserves the bare form for preloaded content; everything else must be namespaced.
    The failure this catches is silent by construction: an agent told to work `some-skill` with no
    preload, no Skill grant, and no path has an instruction that cannot execute — the model just
    proceeds without the skill's content, and nothing errors. Observed for real: sde-fullstack
    said "invoke `code-craft`" while holding no route to it, and the fleet's flagship pipeline
    forbade its callers from working around the gap.
    """
    issues: list[str] = []
    known = set(skill_names)
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return issues
    for path in sorted(agents_dir.glob("*.md")):
        fields = parse_frontmatter(path) or {}
        preloaded = {entry.strip() for entry in fields.get("skills", "").split(",") if entry.strip()}
        for span in sorted(set(INLINE_CODE_RE.findall(read_text(path)))):
            if span in known and span not in preloaded:
                issues.append(
                    f"{path}: bare backticked skill name `{span}` claims the skill is already in "
                    f"this agent's context, but it is not in the skills: preload — the reference "
                    f"is unreachable authority that reads as configured, and nothing errors at "
                    f"runtime. Preload it; use the namespaced form if routing is the intent; or "
                    f"give an explicit, resolvable "
                    f"${{CLAUDE_PLUGIN_ROOT}}/skills/{span}/SKILL.md path if the agent must read it."
                )
    return issues


def validate_perishable_tokens(root: Path) -> list[str]:
    """Each perishable platform fact may appear in exactly one declared owner file."""
    issues: list[str] = []
    for token, owner in PERISHABLE_TOKENS.items():
        for path in definition_markdown_files(root):
            if path.relative_to(root).as_posix() == owner:
                continue
            if token in read_text(path):
                issues.append(
                    f"{path}: carries perishable platform token {token!r}, whose only allowed home "
                    f"is {owner}. A second copy stays behind when the platform moves and keeps "
                    f"teaching the stale behavior with no runtime error — state the role-local "
                    f"consequence here and point at the owner file for the fact."
                )
    return issues


def render_inventory(agent_names: list[str], skill_names: list[str]) -> str:
    agents = ", ".join(f"`{name}`" for name in agent_names)
    skills = ", ".join(f"`{name}`" for name in skill_names)
    return "\n".join(
        [
            "<!-- fleet-inventory:start -->",
            f"- **Agents ({len(agent_names)}):** {agents}",
            f"- **Skills ({len(skill_names)}):** {skills}",
            "<!-- fleet-inventory:end -->",
        ]
    )


def replace_inventory(content: str, expected: str) -> str:
    if not INVENTORY_RE.search(content):
        raise ValueError("missing fleet inventory markers")
    newline = "\r\n" if "\r\n" in content else "\n"
    return INVENTORY_RE.sub(expected.replace("\n", newline), content, count=1)


def write_inventory(readme: Path, expected: str) -> None:
    if not readme.is_file():
        raise ValueError(f"{readme}: missing README.md")
    content = readme.read_bytes().decode("utf-8")
    try:
        updated = replace_inventory(content, expected)
    except ValueError as exc:
        raise ValueError(f"{readme}: {exc}") from exc
    readme.write_bytes(updated.encode("utf-8"))


def validate_inventory(root: Path, expected: str) -> list[str]:
    readme = root / "README.md"
    if not readme.is_file():
        return [f"{readme}: missing README.md"]
    match = INVENTORY_RE.search(read_text(readme))
    if not match:
        return [f"{readme}: missing fleet inventory markers"]
    if match.group(0) != expected:
        return [
            f"{readme}: fleet inventory drifted; run "
            "`python scripts/validate_fleet.py --write-inventory`"
        ]
    return []


def validate_agent_guide(root: Path) -> list[str]:
    """Drift tripwires for the repo's own agent guide (AGENTS.md plus the CLAUDE.md bridge) and,
    when present, the engineering-program map (PROGRAM_DOC), which shares the guide's stale-path
    rule.

    Self-gating: a repo with no AGENTS.md (the synthetic fixtures under tests/) is not making any
    guide claims, so there is nothing to check and this returns []. Same for the program map.
    """
    issues: list[str] = []
    guide = root / "AGENTS.md"
    bridge = root / "CLAUDE.md"

    def has_import(path: Path) -> bool:
        return path.is_file() and any(
            line.strip() == GUIDE_IMPORT for line in read_text(path).splitlines()
        )

    def stale_path_issues(doc: Path) -> list[str]:
        found: list[str] = []
        for span in INLINE_CODE_RE.findall(read_text(doc)):
            for token in GUIDE_PATH_TOKEN_RE.findall(span):
                token = token.rstrip(".,;:")
                # Bare filenames and lone directory mentions (`references/`) are prose, not
                # resolvable claims; only a multi-segment path asserts a location worth checking.
                if len([part for part in token.split("/") if part]) < 2:
                    continue
                if not (root / token.rstrip("/")).exists():
                    found.append(
                        f"{doc}: names '{token}', which does not exist in this repository. A "
                        f"stale path here fails nowhere at runtime — it just misleads every "
                        f"future session that reads it."
                    )
        return found

    # The program map is checked BEFORE the guide's early return, never behind it. Its own header
    # advertises this tripwire ("the fleet validator resolves every path named here"), and a check
    # that a missing UNRELATED file disarms is enforcement prose with no guard behind it — the
    # exact defect class this validator exists to catch (PR #133 finding).
    program = root / PROGRAM_DOC
    if program.is_file():
        issues += stale_path_issues(program)

    if not guide.is_file():
        if has_import(bridge):
            issues.append(
                f"{bridge}: imports {GUIDE_IMPORT} but AGENTS.md does not exist — the import "
                f"resolves to nothing and the project context silently loads empty."
            )
        return issues

    if not has_import(bridge):
        issues.append(
            f"{guide}: exists but {root / 'CLAUDE.md'} does not carry a line reading "
            f"{GUIDE_IMPORT!r}. Claude Code reads CLAUDE.md, not AGENTS.md (the README's own "
            f"bridge convention), so without the import this guide is never loaded by the tool "
            f"it is written for."
        )

    issues += stale_path_issues(guide)

    text = read_text(guide)
    for alias in sorted(ALIAS_MODELS):
        if f"`{alias}`" not in text:
            issues.append(
                f"{guide}: the model-alias paraphrase omits `{alias}`; ALIAS_MODELS in "
                f"scripts/validate_fleet.py is the source of truth — fix the paraphrase, never "
                f"the source."
            )
    return issues


_MODULES_BY_SOURCE: dict[tuple[str, bytes], object] = {}


def load_module_by_content(source: Path, name: str):
    """Import a script by path, reusing the module when the exact bytes were already imported.

    Validation imports the tree-under-validation's own scripts, and the mutation suite validates
    ~a hundred copies of this repository in one process — nearly all byte-identical, each
    previously paying compile+exec again. Keying the cache on content (the convention
    eval_routing uses for its evaluator) keeps the reuse honest: mutated code hashes differently
    and gets a fresh import, so the cache can never certify code it did not load.

    The key covers every sibling `*.py` next to the script, not just the script itself: these
    scripts import each other by paths derived from their own `__file__` at import time, so a
    module cached on its own bytes alone could be served for a tree whose DEPENDENCIES were
    mutated — a false pass caught in review. Hashing the whole sibling set costs ~1ms; a
    directory-wide miss on any mutation is the price of never validating one tree with another
    tree's code.

    The cache is ONLY for scripts whose import binds no repository content beyond scripts/.
    A script whose import chain globs repository content into a module-level constant — for
    example a roster built by globbing agents/ at import time — captures fleet state the byte
    key can't see, so it must be imported fresh per tree instead of through this cache: no
    affordable byte key can cover everything such an import might read.

    Returns None when no import spec can be built (the caller owns that message); a module
    whose exec raises is never cached, so a broken script fails on every call, not just the first.
    """
    digest = hashlib.sha256()
    source_bytes: bytes | None = None
    for sibling in sorted(source.parent.glob("*.py")):
        data = sibling.read_bytes()
        # Length-framed, not bare concatenation: without the frame, moving bytes across a file
        # boundary (append a deleted sibling's name+contents to the file sorted before it)
        # yields the same stream and a false cache hit (caught in review on #91).
        digest.update(f"{sibling.name}\x00{len(data)}\x00".encode("utf-8"))
        digest.update(data)
        if sibling == source:
            source_bytes = data
    if source_bytes is None:
        return None
    key = (source.name, digest.digest())
    module = _MODULES_BY_SOURCE.get(key)
    if module is None:
        module = _execute_source(source, name, source_bytes)
        if module is None:
            return None
        _MODULES_BY_SOURCE[key] = module
    return module


def _execute_source(source: Path, name: str, data: bytes | None = None):
    """Build a module by compiling the given bytes, bypassing bytecode caches.

    SourceFileLoader.exec_module trusts a __pycache__ entry validated only by (mtime, size), so
    a same-size rewrite inside one timestamp tick would execute the PREVIOUS contents while a
    content digest describes the new ones (caught in review on #91). Compiling the buffer
    directly is eval_routing's checked-buffer convention: what was hashed is exactly what runs
    — which is also why callers that hashed pass the SAME bytes rather than letting this
    function re-read a file that may have changed in between.
    """
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    exec(compile(data if data is not None else source.read_bytes(), str(source), "exec"),
         module.__dict__)
    return module


def load_guard(root: Path):
    """Import scripts/readonly-guard.py by path — the hyphen makes it un-importable by name."""
    source = root / "scripts" / "readonly-guard.py"
    module = load_module_by_content(source, "readonly_guard")
    if module is None:
        raise ImportError(f"cannot load {source}")
    return module


# The hook reads its fast-path from "$IN" and its identity fallback from "$SQ", a
# whitespace-stripped copy, so JSON spacing cannot decide whether the fallback fires. Either
# variable opens a roster block, and the cross-check below must recognise both.
_CASE_BLOCK_RE = re.compile(r'case "\$(?:IN|SQ)" in')


def load_gate(root: Path):
    """Import scripts/live-effect-gate.py by path — the hyphen makes it un-importable by name."""
    source = root / "scripts" / "live-effect-gate.py"
    module = load_module_by_content(source, "live_effect_gate")
    if module is None:
        raise ImportError(f"cannot load {source}")
    return module


def hook_commands(root: Path) -> list[str]:
    """Every PreToolUse/Bash command string in hooks/hooks.json, in file order."""
    path = root / "hooks" / "hooks.json"
    if not path.is_file():
        return []
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    commands: list[str] = []
    for entry in config.get("hooks", {}).get("PreToolUse", []):
        if entry.get("matcher") == "Bash":
            for hook in entry.get("hooks", []):
                if hook.get("type") == "command" and hook.get("command"):
                    commands.append(hook["command"])
    return commands


def hook_command_for(root: Path, script: str) -> str | None:
    """The PreToolUse/Bash command that runs `script`, found by name — two hooks share the matcher."""
    return next((command for command in hook_commands(root) if script in command), None)


def hook_command(root: Path) -> str | None:
    """The read-only guard's PreToolUse/Bash command string (its callers keep this name)."""
    return hook_command_for(root, "readonly-guard.py")


def agent_tool_bases(path: Path) -> set[str]:
    fields = parse_frontmatter(path) or {}
    bases: set[str] = set()
    for entry in split_tools(fields.get("tools", "")):
        match = TOOL_ENTRY_RE.match(entry)
        if match:
            bases.add(match.group(1))
    return bases


def validate_plugin(root: Path, agent_names: list[str], skill_names: list[str]) -> list[str]:
    """Checks that only apply to a repo which SHIPS AS A PLUGIN.

    Returns [] when there is no manifest, so the synthetic fixtures under tests/ — bare agents/ and
    skills/ trees that are not plugins — stay valid.

    Every rule here is a tripwire for a failure that is SILENT at runtime. A plugin-shipped agent
    cannot carry its own `hooks:`, so the read-only guard has exactly one place to live and exactly
    one way to find its subject; get any link in that chain wrong and nothing errors, nothing logs,
    and `code-reviewer` simply runs Bash unguarded against the repository it is reviewing.
    """
    manifest_path = root / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return []

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [f"{manifest_path}: unreadable plugin manifest: {exc}"]

    issues: list[str] = []
    plugin_name = str(manifest.get("name", "")).strip()
    if not plugin_name:
        issues.append(f"{manifest_path}: manifest is missing the required 'name'")
    if not manifest.get("author"):
        # `claude plugin validate --strict` treats a missing author as an error; say so here rather
        # than letting CI be the first to find out.
        issues.append(
            f"{manifest_path}: missing 'author' — `claude plugin validate --strict` fails without it"
        )

    guard_path = root / "scripts" / "readonly-guard.py"
    if not guard_path.is_file():
        return issues + [f"{guard_path}: missing the read-only guard"]
    try:
        guard = load_guard(root)
    except Exception as exc:  # a guard that cannot even import guards nothing
        return issues + [f"{guard_path}: cannot load guard: {exc}"]

    if plugin_name and guard.PLUGIN_NAME != plugin_name:
        issues.append(
            f"{guard_path}: PLUGIN_NAME {guard.PLUGIN_NAME!r} does not match the manifest name "
            f"{plugin_name!r}. The guard recognizes its subject by a NAMESPACED agent_type, so a "
            f"mismatch means it matches nobody and silently guards nothing."
        )

    # The live-effect gate is the guard's mirror image for a Bash-and-Write agent: where the
    # guard enumerates readers and denies the rest, the gate names live verbs and makes a human
    # decide. It has the same single place to live and the same silent failure modes, so the
    # same links are held: it must load, name the plugin, name real Bash-holding agents that
    # are not also guarded, and be wired from ${CLAUDE_PLUGIN_ROOT}.
    gate_path = root / "scripts" / "live-effect-gate.py"
    try:
        gate = load_gate(root)
    except Exception as exc:  # a gate that cannot import gates nothing
        issues.append(f"{gate_path}: cannot load live-effect gate: {exc}")
        gate = None
    if gate is not None:
        if plugin_name and gate.PLUGIN_NAME != plugin_name:
            issues.append(
                f"{gate_path}: PLUGIN_NAME {gate.PLUGIN_NAME!r} does not match the manifest name "
                f"{plugin_name!r}. The gate recognizes its subject by a NAMESPACED agent_type, so a "
                f"mismatch means it matches nobody and silently gates nothing."
            )
        for name in sorted(gate.GATED_AGENT_NAMES):
            agent_path = root / "agents" / f"{name}.md"
            if name not in agent_names:
                issues.append(
                    f"{gate_path}: GATED_AGENT_NAMES names {name!r}, which is not an agent in "
                    f"agents/ — a typo here gates nobody."
                )
                continue
            if "Bash" not in agent_tool_bases(agent_path):
                issues.append(
                    f"{gate_path}: gated agent {name!r} holds no Bash, so the gate can never fire "
                    f"for it"
                )
            if name in guard.GUARDED_AGENT_NAMES:
                issues.append(
                    f"{gate_path}: {name!r} is in both GATED_AGENT_NAMES and the guard's "
                    f"GUARDED_AGENT_NAMES; a read-only agent gets the guard, a live-effect agent "
                    f"gets the gate, never both (the guard would deny every live verb before the "
                    f"gate asked)"
                )
        gate_command = hook_command_for(root, "live-effect-gate.py")
        if gate_command is None:
            issues.append(
                f"{root / 'hooks' / 'hooks.json'}: no PreToolUse/Bash hook runs "
                f"scripts/live-effect-gate.py. A plugin-shipped agent cannot carry its own hooks, "
                f"so this file is the ONLY place the live-effect gate can be attached — without "
                f"it, homelab-engineer's managed gate is prose."
            )
        elif "${CLAUDE_PLUGIN_ROOT}/scripts/live-effect-gate.py" not in gate_command:
            issues.append(
                f"{root / 'hooks' / 'hooks.json'}: the live-effect-gate.py hook must run the gate "
                f"from ${{CLAUDE_PLUGIN_ROOT}} — the plugin's own installed copy — never a "
                f"relative path a repository under operation could supply."
            )
        if gate_command is not None:
            # The gate hook carries the same two rosters the guard's does, and each disarms it
            # alone: the `case` fast-path decides whether the gate runs at all, and the
            # no-interpreter fallback is what decides when no Python answers. The gate's own
            # documented growth path is "the roster grows by recurrence" — someone adds a name to
            # GATED_AGENT_NAMES after an incident — and without this check that addition gates
            # NOTHING while every check stays green, because the fast-path still exits for the
            # unlisted name (review-reported, reproduced).
            gate_blocks = [segment.split("esac", 1)[0]
                           for segment in _CASE_BLOCK_RE.split(gate_command)[1:]]
            if len(gate_blocks) < 2:
                issues.append(
                    f"{root / 'hooks' / 'hooks.json'}: expected the live-effect-gate hook to "
                    f"contain two `case \"$IN\" in` blocks (the fast-path filter and the "
                    f"no-interpreter fallback), found {len(gate_blocks)}. The roster cross-check "
                    f"cannot verify a hook it does not recognize, so this fails rather than "
                    f"passing a hook it did not actually check."
                )
            else:
                for label, block in (("fast-path filter", gate_blocks[0]),
                                     ("no-interpreter fallback", gate_blocks[-1])):
                    for name in sorted(gate.GATED_AGENT_NAMES):
                        if name not in block:
                            issues.append(
                                f"{root / 'hooks' / 'hooks.json'}: the live-effect-gate hook's "
                                f"{label} never names {name!r}, but scripts/live-effect-gate.py "
                                f"lists it in GATED_AGENT_NAMES. The fast-path decides whether the "
                                f"gate runs at all and the fallback is what decides when no "
                                f"interpreter answers, so a name missing from EITHER leaves that "
                                f"agent's live effects ungated — silently, because the hook still "
                                f"exits 0."
                            )

    command = hook_command(root)
    if command is None:
        issues.append(
            f"{root / 'hooks' / 'hooks.json'}: no PreToolUse hook with matcher 'Bash' and a command. "
            f"A plugin-shipped agent cannot carry its own hooks, so this file is the ONLY place the "
            f"read-only guard can be attached — without it, code-reviewer holds Bash unguarded."
        )
    else:
        if "readonly-guard.py" not in command:
            issues.append(
                f"{root / 'hooks' / 'hooks.json'}: the PreToolUse/Bash hook does not run "
                f"scripts/readonly-guard.py"
            )
        if "${CLAUDE_PLUGIN_ROOT}" not in command:
            issues.append(
                f"{root / 'hooks' / 'hooks.json'}: the PreToolUse/Bash hook must run the guard from "
                f"${{CLAUDE_PLUGIN_ROOT}} — the plugin's own installed copy. Resolving it any other "
                f"way risks executing a guard supplied by the repository under review."
            )
        # The hook string carries TWO independent copies of the roster, and each one can disarm the
        # guard on its own:
        #   1. the `case` FAST-PATH, which exits 0 for any payload not naming a guarded agent --
        #      a name missing here means the guard is never even invoked for that agent;
        #   2. the no-interpreter FALLBACK deny patterns, which are what fails closed when no
        #      Python answers -- a name missing there means that agent gets an open Bash exactly
        #      when the guard is broken or absent.
        # Searching the whole command string cannot tell them apart: a name present in only one
        # block satisfies a substring check while the other block silently lets the agent through
        # (caught in review of this very rule). So each block is located and asserted separately.
        blocks = [segment.split("esac", 1)[0] for segment in _CASE_BLOCK_RE.split(command)[1:]]
        if len(blocks) < 2:
            issues.append(
                f"{root / 'hooks' / 'hooks.json'}: expected the PreToolUse/Bash hook to contain two "
                f"`case \"$IN\" in` blocks (the fast-path filter and the no-interpreter fallback), "
                f"found {len(blocks)}. The roster cross-check below cannot verify a hook it does not "
                f"recognize, so this fails rather than passing a hook it did not actually check."
            )
        else:
            for label, block in (("fast-path filter", blocks[0]), ("no-interpreter fallback", blocks[-1])):
                for name in sorted(guard.GUARDED_AGENT_NAMES):
                    if name not in block:
                        issues.append(
                            f"{root / 'hooks' / 'hooks.json'}: the hook's {label} never names "
                            f"{name!r}, but scripts/readonly-guard.py lists it in "
                            f"GUARDED_AGENT_NAMES. The fast-path decides whether the guard runs at "
                            f"all and the fallback is what fails closed when no interpreter "
                            f"answers, so a name missing from EITHER leaves that agent's 'read-only' "
                            f"a promise with no control behind it — silently, because the hook "
                            f"still exits 0."
                        )

    # The guard's subject list and the agent roster must agree, in both directions.
    guarded = set(guard.GUARDED_AGENT_NAMES)
    for name in sorted(guarded - set(agent_names)):
        issues.append(
            f"{guard_path}: GUARDED_AGENT_NAMES lists {name!r}, which is not an agent in agents/"
        )
    for path in sorted((root / "agents").glob("*.md")):
        tools = agent_tool_bases(path)
        if "Bash" in tools and not (tools & WRITE_TOOLS) and path.stem not in guarded:
            issues.append(
                f"{path}: agent {path.stem!r} holds Bash and no write tool — a read-only agent whose "
                f"only route to mutation is the shell — but it is absent from GUARDED_AGENT_NAMES in "
                f"scripts/readonly-guard.py, so the guard ignores it and its 'read-only' is a promise, "
                f"not a control."
            )

    # Cross-references and paths, across every agent and skill definition.
    fleet = set(agent_names) | set(skill_names)
    definitions = [(path, path.stem) for path in sorted((root / "agents").glob("*.md"))]
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        definitions += [
            (directory / "SKILL.md", directory.name)
            for directory in sorted(p for p in skills_dir.iterdir() if p.is_dir())
            if (directory / "SKILL.md").is_file()
        ]

    for path, own in definitions:
        text = read_text(path)
        description = (parse_frontmatter(path) or {}).get("description", "")
        for other in sorted(fleet - {own}):
            if re.search(rf"(?<![\w:-]){re.escape(other)}(?![\w-])", description):
                issues.append(
                    f"{path}: description names {other!r} without the plugin namespace. Every "
                    f"component a plugin ships is namespaced, so the real name is "
                    f"{plugin_name}:{other} — a bare reference points at nothing and degrades "
                    f"the routing this description exists to drive."
                )
        # `~/.claude/agents|skills/` does NOT contain this fleet once it ships as a plugin; its files
        # live under ${CLAUDE_PLUGIN_ROOT}. The `(?!\*)` spares the doc-reference form
        # (`~/.claude/agents/*.md`, which correctly describes where USER-level agents live) and
        # catches only a path being resolved to a specific file — the thing that silently stops
        # resolving, taking `service-onboard` (unreachable any other way) down with it.
        for match in re.finditer(r"~/\.claude/(agents|skills)/(?!\*)", text):
            kind = match.group(1)
            issues.append(
                f"{path}: resolves a fleet file under '~/.claude/{kind}/', which will NOT contain this "
                f"fleet once it ships as a plugin — those files live under ${{CLAUDE_PLUGIN_ROOT}}. "
                f"Use '${{CLAUDE_PLUGIN_ROOT}}/{kind}/...' instead."
            )

    # Every namespaced cross-reference must be one complete, well-formed token that resolves to
    # the right kind of fleet member. The corpus is a densely linked graph (hundreds of
    # `<plugin>:<name>` references) and NOTHING at runtime checks one: a prefix-only matcher can
    # certify `code-reviewer_v2` as `code-reviewer`, while union membership can certify a slash
    # command that names an agent even though slash commands invoke skills. Both failures are
    # silent. The token matcher therefore captures uppercase and invalid punctuation too, so
    # syntax is rejected explicitly instead of being skipped or truncated to a valid prefix.
    if plugin_name:
        agents = set(agent_names)
        skills = set(skill_names)
        # One shared extraction. Deduping per file to
        # (slash, target) keeps one message per distinct reference however many times a file
        # repeats it; the records retain each occurrence's source location.
        by_path: dict[Path, set[tuple[bool, str]]] = {}
        for record in fleet_records.collect_references(root, plugin_name):
            by_path.setdefault(record.path, set()).add((record.is_slash_command, record.target))
        for path, references in by_path.items():
            for is_slash_command, target in sorted(references):
                reference = f"{'/' if is_slash_command else ''}{plugin_name}:{target}"
                if not NAME_RE.fullmatch(target):
                    issues.append(
                        f"{path}: malformed namespaced reference {reference!r}; the complete target "
                        f"must be a kebab-case fleet name. Prefix matching would silently certify "
                        f"a different live member while this token fails to resolve at runtime."
                    )
                    continue
                if is_slash_command and target not in skills:
                    target_kind = "an agent" if target in agents else "no shipped skill"
                    issues.append(
                        f"{path}: slash-command reference {reference!r} names {target_kind}; a "
                        f"slash-command reference must target a skill, or the invocation cannot "
                        f"resolve at runtime."
                    )
                    continue
                if target not in fleet:
                    issues.append(
                        f"{path}: references {reference}, which is not an agent or "
                        f"skill in this fleet. A dangling cross-reference fails nowhere at "
                        f"runtime — routing and handoffs just quietly stop resolving — so a "
                        f"rename or removal must update every referrer, and this rule is what "
                        f"makes the miss loud."
                    )

    return issues


def load_platform_adapter_generator(root: Path):
    """Load the adapter generator shipped by the tree under validation."""
    source = root / "scripts" / "generate_platform_adapters.py"
    module = load_module_by_content(source, "platform_adapters")
    if module is None:
        raise ImportError(f"cannot load {source}")
    return module


def validate_platform_adapters(root: Path) -> list[str]:
    """Load the repository's adapter generator and verify every non-Claude install surface.

    Synthetic fixtures do not ship a Claude manifest and skip this rule. A real plugin must carry
    the generator: otherwise generated copies can drift while the canonical fleet remains green.
    """

    if not (root / ".claude-plugin" / "plugin.json").is_file():
        return []

    source = root / "scripts" / "generate_platform_adapters.py"
    if not source.is_file():
        return [
            f"{source}: missing platform adapter generator. The Copilot, VS Code, and Codex "
            f"copies would have no mechanical link to the canonical Claude definitions."
        ]

    try:
        module = load_platform_adapter_generator(root)
        return module.validate_platform_support(root)
    except Exception as exc:
        return [
            f"{source}: platform adapter validation crashed: {exc}. A broken checker must fail "
            f"loudly rather than certifying stale host copies."
        ]


def validate_routing_clusters(root: Path, agent_names: list[str], skill_names: list[str]) -> list[str]:
    """Schema integrity for evals/routing/*.json — the rules that keep the scorer honest.

    Every rule here is a tripwire for a measurement that would silently lie. The scorer grades a
    positive against its own expect_fires but reports the CLUSTER's fire rate, so a positive
    naming a component outside the declared members can pass while the reported rate reads zero
    (observed live in pos-ci-actions-harden, which accepted code-reviewer). Both target lists
    match components BY NAME, so a typo'd member or target expects or forbids nothing and passes
    vacuously. A misspelled polarity used to fall through to the negative branch, and an empty
    explicit forbidden set therefore passed every run. Case ids are also the keys a before/after
    diff aligns on, so a duplicate makes two measurements read as one.
    """
    issues: list[str] = []
    routing = root / "evals" / "routing"
    if not routing.is_dir():
        return issues
    components = set(agent_names) | set(skill_names)
    for path in sorted(routing.glob("*.json")):
        rel = path.relative_to(root).as_posix()
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            issues.append(
                f"{rel}: unreadable cluster file ({exc}) — the runner would fail loudly, but a "
                f"cluster nobody can run measures nothing while still looking like coverage."
            )
            continue
        if not isinstance(doc, dict):
            issues.append(
                f"{rel}: top-level JSON value is not an object — the runner needs named cluster, "
                f"members, and cases fields, so this file cannot describe a measurement."
            )
            continue
        cluster = doc.get("cluster")
        if not isinstance(cluster, str) or not cluster.strip():
            issues.append(
                f"{rel}: missing non-empty 'cluster' string — benchmark artifacts need a stable "
                f"cluster identity or results cannot be aligned."
            )
        members = doc.get("members")
        if not isinstance(members, list) or not members:
            issues.append(
                f"{rel}: no non-empty 'members' list — every routing assertion grades against the "
                f"member set, so without one the file asserts nothing."
            )
            continue
        member_set: set[str] = set()
        for index, member in enumerate(members, start=1):
            if not isinstance(member, str) or not member.strip():
                issues.append(
                    f"{rel}: member #{index} is not a non-empty component name — target matching "
                    f"is string-based, so a malformed member can never fire."
                )
                continue
            member_set.add(member)
            if member not in components:
                issues.append(
                    f"{rel}: member {member!r} is not a fleet component — a name that resolves to "
                    f"nothing can be expected or forbidden and never match, passing vacuously."
                )

        cases = doc.get("cases")
        if not isinstance(cases, list) or not cases:
            issues.append(
                f"{rel}: no non-empty 'cases' list — a cluster without runnable assertions can "
                f"look like coverage while measuring nothing."
            )
            continue
        seen_ids: set[str] = set()
        for index, case in enumerate(cases, start=1):
            if not isinstance(case, dict):
                issues.append(
                    f"{rel}: case #{index} is not an object — the runner cannot read its identity, "
                    f"prompt, polarity, or expectations."
                )
                continue
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id.strip():
                issues.append(
                    f"{rel}: case #{index} has no non-empty 'id' — results without a stable key "
                    f"cannot be aligned across benchmark runs."
                )
                case_label = f"#{index}"
            else:
                case_label = repr(case_id)
                if case_id in seen_ids:
                    issues.append(
                        f"{rel}: duplicate case id {case_id!r} — ids are what a before/after diff "
                        f"aligns on, so a duplicate makes two measurements read as one."
                    )
                seen_ids.add(case_id)

            prompt = case.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                issues.append(
                    f"{rel}: case {case_label} has no non-empty 'prompt' — a case with no runnable "
                    f"input cannot produce routing evidence."
                )

            polarity = case.get("polarity")
            if polarity not in ("positive", "negative"):
                issues.append(
                    f"{rel}: case {case_label} polarity must be exactly positive or negative "
                    f"(got {polarity!r}) — any other value used to fall through as a negative and "
                    f"could pass without testing the intended route."
                )
                continue

            if polarity == "positive":
                field = "expect_fires"
            elif "expect_not_fires" in case:
                field = "expect_not_fires"
            else:
                # Omission deliberately means the whole cluster; only an explicitly empty list is
                # invalid because it overrides that useful default with a vacuous prohibition.
                continue

            targets = case.get(field)
            if not isinstance(targets, list) or not targets:
                issues.append(
                    f"{rel}: case {case_label} {field} must be a non-empty list — an empty or "
                    f"wrongly typed target set can make the assertion vacuous."
                )
                continue
            for target in targets:
                if not isinstance(target, str) or not target.strip():
                    issues.append(
                        f"{rel}: case {case_label} {field} contains {target!r}, not a non-empty "
                        f"component name — malformed targets can never match a firing."
                    )
                    continue
                if target not in member_set:
                    if field == "expect_fires":
                        issues.append(
                            f"{rel}: case {case_label} expects {target!r}, outside the cluster's "
                            f"members — the scorer would pass the case on a fire the cluster rate "
                            f"does not count, so the case can pass while the reported rate reads zero."
                        )
                    else:
                        issues.append(
                            f"{rel}: case {case_label} forbids {target!r}, outside the cluster's "
                            f"members — a non-member can never fire as this cluster, so the "
                            f"prohibition matches nothing and the negative passes vacuously."
                        )
    return issues


def validate_host_conformance_manifest(root: Path) -> list[str]:
    """Apply repository coverage policy after the shared manifest schema validates."""

    if not (root / ".claude-plugin" / "plugin.json").is_file():
        return []
    path = root / "evals" / "conformance" / "hosts.json"
    schema = root / "scripts" / "host_conformance_schema.py"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        module = load_module_by_content(schema, "host_conformance_schema")
        if module is None:
            raise ImportError(f"cannot load {schema}")
        module.validate_manifest(document)
    except Exception as exc:
        return [
            f"{path}: host conformance manifest is missing, unreadable, or invalid ({exc}). "
            f"Without one authoritative schema, malformed lanes can silently disappear from the "
            f"cross-host baseline."
        ]
    lanes = document["lanes"]
    issues: list[str] = []
    static_hosts = {
        lane.get("host")
        for lane in lanes
        if isinstance(lane, dict) and lane.get("kind") == "static"
    }
    missing_hosts = sorted({"claude", "codex", "vscode"} - static_hosts)
    if missing_hosts:
        issues.append(
            f"{path}: static conformance lanes are missing hosts {missing_hosts}. A generated host "
            f"surface could drift while the cross-host report still looks complete."
        )
    sol_lane = next(
        lane
        for lane in lanes
        if lane.get("kind") == "model-baseline" and lane.get("model") == "gpt-5.6-sol"
    )
    if not sol_lane["required"]:
        issues.append(
            f"{path}: gpt-5.6-sol baseline is not required. The operator selected Sol as a "
            f"separately reported baseline; making it optional silently changes what was measured."
        )
    return issues


def validate_workflow_evidence_enums(root: Path) -> list[str]:
    """Every workflow script that declares an EVIDENCE enum must match the canonical triad."""
    issues: list[str] = []
    workflows_dir = root / "workflows"
    if not workflows_dir.is_dir():
        return issues
    for path in sorted(workflows_dir.glob("*.js")):
        text = read_text(path)
        matches = WORKFLOW_EVIDENCE_ENUM_RE.findall(text)
        if "evidence" in text and not matches:
            issues.append(
                f"{path}: declares an evidence field without a parseable `const EVIDENCE = [...]` "
                f"enum, so the canonical triad cannot be pinned and drift would be invisible "
                f"until a live run fails schema validation."
            )
        for group in matches:
            values = tuple(v.strip().strip("'\"") for v in group.split(",") if v.strip())
            if values != WORKFLOW_EVIDENCE_ENUM:
                issues.append(
                    f"{path}: workflow evidence enum {values!r} does not match the canonical "
                    f"triad {WORKFLOW_EVIDENCE_ENUM!r} from EVIDENCE_LABEL_STEMS; a drifted enum "
                    f"ships a packet contract that fails five retries deep with no load-time error."
                )
    return issues


def validate_workflow_line_endings(root: Path) -> list[str]:
    """No workflow script may contain a carriage return in the bytes actually on disk, and
    `.gitattributes` must carry the `*.js text eol=lf` rule that prevents Windows checkout
    translation from re-introducing them.

    The Workflow tool rejects any script containing \\r ("control characters that would be
    hidden in the approval dialog") BEFORE execution, so a CRLF workflow ships as configured
    and fails on first invocation with no load-time error -- proven on installed 1.6.10, where
    Windows checkout translation made the fleet's only workflow unrunnable (#75) while the
    probe passed against its own LF-written fixture. Checking only checkout bytes misses the
    configuration regression: a fresh Windows clone after the rule is removed would get CRLF
    and fail silently, and the byte check would pass on any machine where the file was already
    LF. Both conditions must hold -- no \\r bytes AND the pin must be present.
    """
    issues: list[str] = []
    workflows_dir = root / "workflows"
    if not workflows_dir.is_dir():
        return issues

    # Check that the eol pin is present in .gitattributes -- the byte check below passes on
    # any machine where files were already checked out as LF, so removing the rule would not
    # be caught by bytes alone. A fresh Windows clone after the rule is removed gets CRLF and
    # fails on first workflow invocation, exactly the silent failure class this rule closes.
    gitattributes = root / ".gitattributes"
    content = (
        gitattributes.read_text(encoding="utf-8", errors="replace")
        if gitattributes.is_file()
        else ""
    )
    if "*.js text eol=lf" not in content:
        issues.append(
            f"{gitattributes}: missing `*.js text eol=lf` rule; without it, Windows "
            f"checkout translation will convert workflows/*.js to CRLF and the Workflow "
            f"tool will refuse to run them -- the byte check alone cannot catch this "
            f"because it passes on any machine where the files are already LF on disk."
        )

    for path in sorted(workflows_dir.glob("*.js")):
        if b"\r" in path.read_bytes():
            issues.append(
                f"{path}: contains carriage returns; the Workflow tool refuses \\r-bearing "
                f"scripts before execution, so this workflow would install everywhere and run "
                f"nowhere -- check the `*.js text eol=lf` line in .gitattributes."
            )
    return issues


def _blank_js_strings_and_comments(source: str) -> str:
    """Overwrite the contents of '...', \"...\", and `...` literals -- and the whole of `//` and
    `/* */` comments -- with spaces, so structural scans (first-statement detection, brace
    matching, identifier detection) cannot be fooled by braces or identifier-shaped text that is
    only prose. Comments must blank the same way strings do: a leading licence or rationale block
    scanned as code reads as a statement ahead of `meta` and fails a workflow the runtime loads
    fine.

    Length and newlines are preserved, so an offset found in the blanked text indexes the same
    character of the raw source -- the checks that must see original bytes (a template literal's
    backticks inside meta) slice the identical span."""
    out = list(source)
    length = len(source)
    index = 0
    while index < length:
        ch = source[index]
        if ch in "'\"`":
            quote = ch
            index += 1
            while index < length:
                current = source[index]
                if current == "\\":
                    # Blank the escape and whatever it escapes together, so an escaped closing
                    # quote cannot end the literal early and leak the rest of the file into a
                    # scan as if it were code.
                    out[index] = " "
                    if index + 1 < length and source[index + 1] != "\n":
                        out[index + 1] = " "
                    index += 2
                    continue
                if current == quote:
                    index += 1
                    break
                if current != "\n":
                    out[index] = " "
                index += 1
            continue
        if ch == "/" and index + 1 < length and source[index + 1] == "/":
            while index < length and source[index] != "\n":
                out[index] = " "
                index += 1
            continue
        if ch == "/" and index + 1 < length and source[index + 1] == "*":
            out[index] = out[index + 1] = " "
            index += 2
            while index < length:
                if source[index] == "*" and index + 1 < length and source[index + 1] == "/":
                    out[index] = out[index + 1] = " "
                    index += 2
                    break
                if source[index] != "\n":
                    out[index] = " "
                index += 1
            continue
        index += 1
    return "".join(out)


# Identifier-shaped tokens that are legal literal values inside a pure-literal object.
_META_LITERAL_KEYWORDS = {"true", "false", "null", "undefined"}
# The declaration must be matched whole: `export const metadata = {...}` shares this prefix, and
# accepting it would let a workflow with no `meta` export at all validate clean while the runtime
# cannot load it. Requiring the opening brace here also means a non-object meta
# (`export const meta = null`) is a reported finding rather than a brace-search traceback.
_META_DECLARATION_RE = re.compile(r"export\s+const\s+meta\s*=\s*\{")
_META_IDENTIFIER_RE = re.compile(r"[A-Za-z_$][\w$]*")


def validate_workflow_meta_contract(root: Path) -> list[str]:
    """`export const meta` must be each workflow's first statement, the meta object must be a
    pure literal, and the body must not reference `meta`.

    The Workflow runtime extracts `meta` statically before execution: a statement ahead of it,
    or an identifier reference inside it, parses as valid JavaScript and reads as configured in
    review, then fails at workflow load with no install-time error. Proven live: a review-fix
    commit moved the lane-model constants above `meta` and referenced them from
    `meta.phases[*].model`, shipping the fleet's only workflow in a shape the runtime cannot
    load -- the validator passed, the tests passed, and nothing would have said so before the
    first billed invocation.

    The body ban is the same failure from the other side, and its proof is the 1.7.0 acceptance
    run: the repair derived the constants FROM meta (`const SCOPE_MODEL = meta.phases[0].model`),
    which this validator blessed -- but the runtime evaluates the body with the meta export
    isolated, so `meta` is not in scope at execution and every invocation died at load with
    "meta is not defined" (2026-08-09, CLI 2.1.226, run wf_c1db8dfb-b9f, zero agents spawned).
    Both directions of sharing one value between meta and the body are therefore banned; the
    only loadable shape is a repeated literal held equal by a deterministic check."""
    issues: list[str] = []
    workflows_dir = root / "workflows"
    if not workflows_dir.is_dir():
        return issues
    for path in sorted(workflows_dir.glob("*.js")):
        text = read_text(path)
        blanked = _blank_js_strings_and_comments(text)
        first = re.search(r"\S", blanked)
        if first is None:
            issues.append(
                f"{path}: workflow file has no statements; it exports no `meta` and cannot load."
            )
            continue
        start = first.start()
        line_end = blanked.find("\n", start)
        found = text[start : line_end if line_end != -1 else len(text)].strip()
        declaration = _META_DECLARATION_RE.match(blanked, start)
        if declaration is None:
            issues.append(
                f"{path}: `export const meta = {{` is not the file's first statement (found "
                f"{found[:60]!r} first); the Workflow runtime requires an object-literal meta to "
                f"lead the file, so this workflow would install everywhere and fail to load "
                f"with no install-time error."
            )
            continue
        open_index = declaration.end() - 1
        depth = 0
        close_index = None
        for index in range(open_index, len(blanked)):
            if blanked[index] == "{":
                depth += 1
            elif blanked[index] == "}":
                depth -= 1
                if depth == 0:
                    close_index = index
                    break
        if close_index is None:
            issues.append(
                f"{path}: could not brace-match the meta object literal; an unparseable meta "
                f"fails at workflow load with no install-time error."
            )
            continue
        if "`" in text[open_index : close_index + 1]:
            # A template literal is not a pure literal the moment it interpolates, and the
            # interpolated identifier lives inside the blanked span where no scan can see it --
            # so the construct itself is the finding rather than its contents.
            issues.append(
                f"{path}: meta contains a template literal; the runtime requires meta to be a "
                f"pure literal, and an interpolated `${{...}}` reads as configured while failing "
                f"at workflow load -- use a plain quoted string."
            )
        meta_block = blanked[open_index : close_index + 1]
        for match in _META_IDENTIFIER_RE.finditer(meta_block):
            token = match.group(0)
            if token in _META_LITERAL_KEYWORDS:
                continue
            after = meta_block[match.end() :].lstrip()
            if after[:1] == ":":
                # A property key, not a value.
                continue
            issues.append(
                f"{path}: meta contains the identifier reference {token!r}; the "
                f"runtime requires meta to be a pure literal, so a variable here parses as "
                f"valid JavaScript, reads as configured, and fails at workflow load with no "
                f"install-time error -- repeat the value as a literal on both sides and let a "
                f"deterministic check hold the copies equal (the body cannot read meta either)."
            )
        body_offset = close_index + 1
        for match in _META_IDENTIFIER_RE.finditer(blanked, body_offset):
            if match.group(0) != "meta":
                continue
            preceding = blanked[: match.start()].rstrip()
            if preceding.endswith(".") and not preceding.endswith(".."):
                # `something.meta` is a property of another object, not the export. Spread
                # (`...meta`) must NOT take this exit: it references the export and dies at
                # load exactly like a bare reference (review finding on the first version of
                # this scan, which read the third spread dot as member access).
                continue
            if (
                blanked[match.end() :].lstrip()[:1] == ":"
                and preceding[-1:] in {"{", ","}
            ):
                # `{ meta: ... }` in a body-local object is a key, not a reference -- but only
                # in key position (after `{` or `,`). A colon alone also follows a ternary
                # consequent (`flag ? meta : x`), which IS a live reference that dies at load;
                # the first version of this exemption swallowed it (review finding).
                continue
            line_number = blanked.count("\n", 0, match.start()) + 1
            issues.append(
                f"{path}:{line_number}: the workflow body references `meta`; the runtime "
                f"evaluates the body with the meta export isolated, so `meta` is not in scope "
                f"at execution -- the script validates, installs everywhere, then fails every "
                f"invocation at load with 'meta is not defined'. Repeat the value as a literal "
                f"and let a deterministic check hold the copies equal. A body-local `meta` "
                f"declaration is banned by this same scan -- rename it."
            )
            break
        # The meta-side template ban above has a body-side twin: blanking erases backtick
        # contents, so a `${meta...}` interpolation is invisible to the identifier scan while
        # the runtime executes it at body load and dies the same way. Surviving backticks in
        # the blanked text are exactly the real template delimiters (quoted and commented
        # backticks were blanked), so pair them and scan the RAW spans for interpolated `meta`.
        # Nesting a template or extra braces inside an interpolation stays out of this flat
        # scan's reach -- a missed exotic nesting is a silent non-fire, the right failure
        # direction for a tripwire.
        tick_positions = [
            i for i in range(body_offset, len(blanked)) if blanked[i] == "`"
        ]
        for open_tick, close_tick in zip(tick_positions[0::2], tick_positions[1::2]):
            raw_span = text[open_tick : close_tick + 1]
            # Blank quoted strings inside each interpolation before searching: `${flag ? 'meta'
            # : ''}` interpolates a STRING named meta, not the export, and the raw scan
            # false-fired on it (review finding) -- failing a workflow the runtime loads fine.
            interpolated = any(
                re.search(
                    r"(?<![.\w$])meta\b(?!\s*:)",
                    re.sub(r"'[^'\n]*'|\"[^\"\n]*\"", " ", interp.group(1)),
                )
                for interp in re.finditer(r"\$\{([^}]*)\}", raw_span)
            )
            if interpolated:
                line_number = text.count("\n", 0, open_tick) + 1
                issues.append(
                    f"{path}:{line_number}: a body template literal interpolates `meta`; the "
                    f"runtime evaluates the body with the meta export isolated, so the "
                    f"interpolation throws at load with 'meta is not defined' -- and the "
                    f"identifier scan cannot see it because string contents are blanked. "
                    f"Interpolate a repeated literal constant instead."
                )
                break
    return issues


# Workflows are Claude-only: the other hosts have no workflow runtime, so a generated adapter
# that mentions one teaches an instruction that cannot execute there -- it reads as configured
# and fails silently, the exact failure class the bare-skill-reference rule already catches for
# skills. Match both the invocation form and the directory form. Generated skill resources may
# use any extension, so scan bytes rather than maintaining a text-suffix allowlist that lets the
# same unusable instruction bypass the rule when it moves from Markdown into a shell asset.
def validate_workflow_host_boundary(root: Path) -> list[str]:
    """No generated non-Claude adapter may reference a plugin workflow."""
    issues: list[str] = []
    workflow_names = set()
    workflows_dir = root / "workflows"
    if workflows_dir.is_dir():
        workflow_names = {p.stem for p in workflows_dir.glob("*.js")}
    if not workflow_names:
        return issues

    generated_roots = generate_platform_adapters.GENERATED_ROOTS
    if (root / ".claude-plugin" / "plugin.json").is_file():
        try:
            # Read authority from the checkout being validated. The content-keyed loader returns
            # the same module used by adapter byte validation, so a target-only tree cannot fall
            # outside this scan while its generated bytes still ship to a host.
            generated_roots = load_platform_adapter_generator(root).GENERATED_ROOTS
        except Exception:
            # validate_platform_adapters owns the precise load/crash diagnostic. Repeating it here
            # would turn one broken generator into two findings without adding evidence.
            return issues

    for tree in generated_roots:
        base = root / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(base)
            # The generator consumes this same predicate and never distributes these paths. A
            # local Python import therefore cannot make this scan inspect bytes no recipient gets.
            if is_runtime_byproduct(relative):
                continue
            content = path.read_bytes()
            for name in sorted(workflow_names):
                invocation = f"/sde-agents:{name}".encode("ascii")
                directory_reference = f"workflows/{name}".encode("ascii")
                if invocation in content or directory_reference in content:
                    issues.append(
                        f"{path}: generated non-Claude adapter references the Claude-only "
                        f"workflow {name!r}; that host has no workflow runtime, so the "
                        f"instruction reads as available and fails silently at use time."
                    )
    return issues


def validate_repo(
    root: Path, *, check_inventory: bool = True, check_adapters: bool = True
) -> tuple[list[str], list[str], list[str]]:
    agent_issues, agent_names = validate_agents(root)
    skill_issues, skill_names = validate_skills(root)
    issues = agent_issues + skill_issues
    issues.extend(validate_yaml_scalar_quoting(root))
    issues.extend(validate_plugin(root, agent_names, skill_names))
    # The adapter byte-compare is 59% of a validation run (profiled 2026-08-08) and independent
    # of every other rule, so a caller validating a deliberate non-adapter mutation may skip it.
    # The command line never does: `main` always runs the full set, which is why the recipe's
    # separate `generate --check` step could be retired without losing the gate.
    if check_adapters:
        issues.extend(validate_platform_adapters(root))
    issues.extend(validate_agent_guide(root))
    issues.extend(validate_routing_clusters(root, agent_names, skill_names))
    issues.extend(validate_host_conformance_manifest(root))
    issues.extend(validate_bare_skill_references(root, skill_names))
    issues.extend(validate_perishable_tokens(root))
    issues.extend(validate_workflow_evidence_enums(root))
    issues.extend(validate_workflow_line_endings(root))
    issues.extend(validate_workflow_meta_contract(root))
    issues.extend(validate_workflow_host_boundary(root))
    if check_inventory:
        issues.extend(validate_inventory(root, render_inventory(agent_names, skill_names)))
    return issues, agent_names, skill_names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the validator's parent repository)",
    )
    parser.add_argument(
        "--write-inventory",
        action="store_true",
        help="rewrite the generated README inventory before validating",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    issues, agent_names, skill_names = validate_repo(root, check_inventory=False)
    if args.write_inventory and not issues:
        try:
            write_inventory(root / "README.md", render_inventory(agent_names, skill_names))
        except ValueError as exc:
            issues.append(str(exc))

    if not issues:
        issues.extend(validate_inventory(root, render_inventory(agent_names, skill_names)))

    if issues:
        print("Fleet validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print(f"Validated {len(agent_names)} agents and {len(skill_names)} skills; inventory is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
