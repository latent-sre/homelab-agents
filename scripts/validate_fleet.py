#!/usr/bin/env python3
"""Validate the canonical fleet: the checks for failures Claude Code ignores silently.

Every check guards something that breaks without an error at runtime -- an unknown tool or
frontmatter key, a `skills:` preload that resolves to nothing, an unguarded read-only Bash agent,
a cross-reference to a renamed component, a stale generated adapter. Platform schema is
`claude plugin validate`'s job (`scripts/validate_claude_plugin.py`); this script holds only
what that cannot see.

Exit 0 on a clean tree, 1 with one line per problem. `--write-inventory` rewrites the README
inventory first. Standard library only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

_SCRIPTS = str(Path(__file__).resolve().parent)
_REPO_ROOT = str(Path(__file__).resolve().parents[1])
for _path in (_SCRIPTS, _REPO_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)  # `import fleet` and the sibling generator as a plain script

from fleet import fs  # noqa: E402
from fleet.frontmatter import NAME_RE, parse_lines, span, split_tools  # noqa: E402
from fleet.references import collect_references, parse_frontmatter  # noqa: E402,F401
from fleet.roster import GUARD_ROSTER, GUARD_SCRIPT, WRITE_TOOLS, HookScript  # noqa: E402

# --- vocabularies: every entry is authority, so widen deliberately ------------------------------
# Aliases follow model upgrades; a pinned model ID goes stale silently.
MODEL_ALIASES = frozenset({"inherit", "haiku", "sonnet", "opus", "fable"})
# Every documented subagent frontmatter key (code.claude.com/docs/en/sub-agents). An unknown key
# does not error at load time, so a typo silently drops whatever it configured.
AGENT_FIELDS = frozenset({
    "name", "description", "tools", "disallowedTools", "model", "permissionMode", "maxTurns",
    "skills", "mcpServers", "hooks", "memory", "background", "omitClaudeMd", "effort",
    "isolation", "color", "initialPrompt", "experimental",
})
# Claude Code silently ignores these on a plugin-shipped agent; `hooks:` once carried the guard.
PLUGIN_INERT_AGENT_FIELDS = frozenset({"hooks", "mcpServers", "permissionMode", "initialPrompt"})
# Every documented SKILL.md key (code.claude.com/docs/en/skills).
SKILL_FIELDS = frozenset({
    "name", "description", "when_to_use", "argument-hint", "arguments",
    "disable-model-invocation", "user-invocable", "allowed-tools", "disallowed-tools", "model",
    "effort", "context", "agent", "background", "hooks", "paths", "shell", "metadata", "license",
    "compatibility",
})
# Real Claude Code tools (code.claude.com/docs/en/tools-reference).
RUNTIME_TOOLS = frozenset({
    "Agent", "Artifact", "AskUserQuestion", "Bash", "CronCreate", "CronDelete", "CronList", "Edit",
    "EnterPlanMode", "EnterWorktree", "ExitPlanMode", "ExitWorktree", "Glob", "Grep",
    "ListMcpResourcesTool", "LSP", "Monitor", "NotebookEdit", "PowerShell", "PushNotification",
    "Read", "ReadMcpResourceTool", "RemoteTrigger", "ReportFindings", "ScheduleWakeup",
    "SendMessage", "SendUserFile", "ShareOnboardingGuide", "Skill", "TaskCreate", "TaskGet",
    "TaskList", "TaskOutput", "TaskStop", "TaskUpdate", "TodoWrite", "ToolSearch",
    "WaitForMcpServers", "WebFetch", "WebSearch", "Workflow", "Write",
})
# What this fleet grants.
FLEET_TOOLS = frozenset({
    "Agent", "Bash", "Edit", "Glob", "Grep", "NotebookEdit", "Read", "Skill", "TodoWrite",
    "ToolSearch", "WebFetch", "WebSearch", "Write",
})
# Tools a subagent never receives however they are listed.
SUBAGENT_UNAVAILABLE_TOOLS = frozenset({
    "AskUserQuestion", "EnterPlanMode", "ExitPlanMode", "ScheduleWakeup", "WaitForMcpServers",
})
# MCP tools are listed exactly: a server-wide grant silently acquires whatever the server adds.
EVIDENCE_MCP = frozenset({
    "mcp__claude_ai_Context7__query-docs",
    "mcp__claude_ai_Context7__resolve-library-id",
    "mcp__plugin_context7_context7__query-docs",
    "mcp__plugin_context7_context7__resolve-library-id",
    "mcp__plugin_githits_githits__get_example",
    "mcp__plugin_githits_githits__grep",
    "mcp__plugin_githits_githits__list",
    "mcp__plugin_githits_githits__pkg_changelog",
    "mcp__plugin_githits_githits__pkg_deps",
    "mcp__plugin_githits_githits__pkg_info",
    "mcp__plugin_githits_githits__pkg_upgrade_review",
    "mcp__plugin_githits_githits__pkg_vulns",
    "mcp__plugin_githits_githits__quick_start",
    "mcp__plugin_githits_githits__read",
    "mcp__plugin_githits_githits__search",
    "mcp__plugin_githits_githits__search_status",
})
LOCAL_REPOSITORY = frozenset({"Glob", "Grep", "Read"})
EXTERNAL_RESEARCH = frozenset({"ToolSearch", "WebFetch", "WebSearch"}) | EVIDENCE_MCP
# Investigation roles are split at the tool layer: a role holding private source AND fetched
# external content can leak one into the other through prompt injection whatever its prose says.
# (required, forbidden) for each role the split binds.
ROLES = {
    "application-security-auditor": (
        LOCAL_REPOSITORY,
        frozenset({"Agent", "Bash", "Edit", "NotebookEdit", "Write"}) | EXTERNAL_RESEARCH,
    ),
    "repository-investigator": (
        LOCAL_REPOSITORY | {"Bash"},
        frozenset({"Agent", "Edit", "NotebookEdit", "Write"}) | EXTERNAL_RESEARCH,
    ),
    "researcher": (
        EXTERNAL_RESEARCH,
        frozenset({"Agent", "Bash", "Edit", "Glob", "Grep", "NotebookEdit", "Read", "Write"}),
    ),
}
GUIDE_IMPORT = "@AGENTS.md"
PROGRAM_DOC = "docs/engineering-program.md"

TOOL_ENTRY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\((.*)\))?$")
MCP_EXACT_TOOL_RE = re.compile(r"^mcp__[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+$")
FULL_MODEL_ID_RE = re.compile(r"^claude-[a-z0-9]+(?:-[a-z0-9]+)+$")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
# The optional `./` is load-bearing: without it a `./references/x.md` link matched nothing, so a
# broken path shipped silently and the file counted as unlinked.
BUNDLE_REF_RE = re.compile(
    r"(?<![\w./])(?:\./)?(?:references|assets|scripts)/[A-Za-z0-9._/-]*[A-Za-z0-9_-]"
)
# A path-shaped token in an inline code span; glob and placeholder characters self-exclude.
GUIDE_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_./-]*")
INVENTORY_RE = re.compile(
    r"<!-- fleet-inventory:start -->.*?<!-- fleet-inventory:end -->", re.DOTALL
)


class Definition(NamedTuple):
    path: Path
    text: str | None
    fields: dict[str, str] | None

    def field(self, key: str) -> str:
        return (self.fields or {}).get(key, "")

    def tools(self) -> list[str]:
        return split_tools(self.field("tools"))

    def tool_bases(self) -> set[str]:
        return {m.group(1) for m in map(TOOL_ENTRY_RE.match, self.tools()) if m}

    def preloaded_skills(self) -> list[str]:
        return [entry.strip() for entry in self.field("skills").split(",") if entry.strip()]


def load_definition(path: Path) -> Definition:
    text = fs.try_read_text(path)
    if text is None:
        return Definition(path, None, None)
    lines = text.splitlines()
    end = span(lines)
    return Definition(path, text, None if end is None else parse_lines(lines, end))


def _identity(definition: Definition, kind: str, expected: str) -> list[str]:
    path, name = definition.path, definition.field("name")
    issues = []
    if not name or len(name) > 64 or not NAME_RE.fullmatch(name):
        issues.append(f"{path}: invalid or missing {kind} name {name!r}")
    elif name != expected:
        issues.append(f"{path}: {kind} name {name!r} must match {expected!r}")
    description = definition.field("description").strip()
    if not description:
        issues.append(f"{path}: missing {kind} description")
    elif len(description) > 1024:
        issues.append(f"{path}: {kind} description exceeds 1024 characters")
    return issues


def _tool_issues(agent: Definition) -> list[str]:
    path = agent.path
    if not agent.field("tools").strip():
        return [f"{path}: missing explicit tools: -- omitting it INHERITS EVERY TOOL"]
    tools = agent.tools()
    issues = []
    if len(tools) != len(set(tools)):
        issues.append(f"{path}: duplicate tool in tools:")
    for tool in tools:
        if tool.startswith("mcp__"):
            if not MCP_EXACT_TOOL_RE.fullmatch(tool) or tool not in EVIDENCE_MCP:
                issues.append(
                    f"{path}: MCP tool {tool!r} is not an exact adopted name; list each tool "
                    f"in EVIDENCE_MCP deliberately (a server-wide grant silently gains new tools)"
                )
            continue
        entry = TOOL_ENTRY_RE.match(tool)
        if not entry:
            issues.append(f"{path}: malformed tool entry {tool!r}")
            continue
        base, scope = entry.groups()
        if base not in RUNTIME_TOOLS:
            issues.append(f"{path}: unknown tool {base!r} is not a Claude Code tool")
        elif base in SUBAGENT_UNAVAILABLE_TOOLS:
            issues.append(f"{path}: tool {base!r} is never available to a subagent")
        elif base not in FLEET_TOOLS:
            issues.append(
                f"{path}: tool {base!r} is real but not adopted by this fleet; add it to "
                f"FLEET_TOOLS deliberately"
            )
        if scope is not None:
            issues.append(
                f"{path}: scoped grant {tool!r} restricts nothing -- a subagent's tools: field "
                f"ignores the parenthesized part, so it grants the bare tool while reading as "
                f"a limit"
            )
    return issues


def check_agents(root: Path, skills: dict[str, Definition]) -> tuple[list[str], list[str]]:
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return [f"{agents_dir}: missing agents directory"], []
    issues: list[str] = []
    names: list[str] = []
    for path in sorted(agents_dir.glob("*.md")):
        agent = load_definition(path)
        if agent.fields is None:
            issues.append(f"{path}: missing or malformed frontmatter")
            continue
        names.append(agent.field("name"))
        for key in agent.fields:
            if key not in AGENT_FIELDS:
                issues.append(f"{path}: unknown frontmatter key {key!r} -- it is ignored silently")
            elif key in PLUGIN_INERT_AGENT_FIELDS:
                issues.append(
                    f"{path}: frontmatter key {key!r} is SILENTLY IGNORED on a plugin-shipped "
                    f"agent; the read-only guard belongs in hooks/hooks.json"
                )
        issues += _identity(agent, "agent", path.stem)
        issues += _tool_issues(agent)
        role = ROLES.get(agent.field("name"))
        if role:
            held = set(agent.tools())
            if missing := sorted(role[0] - held):
                issues.append(f"{path}: trust-separated role is missing required tools {missing}")
            if forbidden := sorted(role[1] & held):
                issues.append(
                    f"{path}: trust-separated role holds forbidden tools {forbidden} -- local "
                    f"source and external content must not meet in one subordinate role"
                )
        for skill_name in agent.preloaded_skills():
            skill = skills.get(skill_name)
            if skill is None:
                issues.append(f"{path}: skills: entry {skill_name!r} does not resolve to a skill")
            elif skill.field("disable-model-invocation").strip().lower() == "true":
                issues.append(
                    f"{path}: skills: entry {skill_name!r} is model-invocation-disabled and "
                    f"cannot be preloaded, so listing it configures nothing"
                )
        model = agent.field("model").strip()
        if model not in MODEL_ALIASES:
            kind = "a pinned model ID" if FULL_MODEL_ID_RE.match(model) else "not a model alias"
            issues.append(f"{path}: model {model!r} is {kind}; use one of {sorted(MODEL_ALIASES)}")
        # A bare backticked skill name claims the skill is already in context.
        preloaded = set(agent.preloaded_skills())
        for name in sorted(set(INLINE_CODE_RE.findall(agent.text or ""))):
            if name in skills and name not in preloaded:
                issues.append(
                    f"{path}: bare backticked skill name `{name}` is not in skills: -- the "
                    f"instruction cannot execute; preload it or use the namespaced form"
                )
    if not names:
        issues.append(f"{agents_dir}: no agent definitions found")
    elif len(names) != len(set(names)):
        issues.append(f"{agents_dir}: duplicate agent names")
    return issues, names


def load_skills(root: Path) -> tuple[dict[str, Definition], list[str]]:
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return {}, [f"{skills_dir}: missing skills directory"]
    skills: dict[str, Definition] = {}
    issues: list[str] = []
    for directory in sorted(d for d in skills_dir.iterdir() if d.is_dir()):
        skill_md = directory / "SKILL.md"
        if not skill_md.is_file():
            issues.append(f"{directory}: missing SKILL.md")
            continue
        skill = load_definition(skill_md)
        if skill.fields is None:
            issues.append(f"{skill_md}: missing or malformed frontmatter")
            continue
        if directory.name in skills:
            issues.append(f"{skills_dir}: duplicate skill names")
        skills[directory.name] = skill
    if not skills and not issues:
        issues.append(f"{skills_dir}: no skill definitions found")
    return skills, issues


def bundle_references(text: str) -> set[str]:
    return {
        match.group(0).rstrip(".,;:)]}").removeprefix("./")
        for match in BUNDLE_REF_RE.finditer(text)
    }


def _bundle_target_exists(base: Path, reference: str) -> bool:
    """Whether `reference` names an existing file inside the bundle folder it starts with.

    `references/../../x` normalizes out of the bundle, so existence alone would accept a file the
    generated adapters never package -- a link that resolves only on this machine.
    """
    folder = Path(os.path.normpath(base / reference.split("/", 1)[0]))
    target = Path(os.path.normpath(base / reference))
    return target != folder and target.is_relative_to(folder) and target.exists()


def check_skills(root: Path, skills: dict[str, Definition]) -> list[str]:
    issues: list[str] = []
    for name, skill in skills.items():
        path, directory = skill.path, skill.path.parent
        for key in skill.fields or {}:
            if key not in SKILL_FIELDS:
                issues.append(f"{path}: unknown frontmatter key {key!r} -- it is ignored silently")
        issues += _identity(skill, "skill", name)
        linked = bundle_references(skill.text or "")
        for reference in sorted(linked):
            if not any(_bundle_target_exists(base, reference) for base in (directory, root)):
                issues.append(f"{path}: referenced file does not exist: {reference}")
        references_dir = directory / "references"
        for file in sorted(p for p in references_dir.rglob("*") if p.is_file()):
            rel = file.relative_to(directory).as_posix()
            if rel not in linked:
                issues.append(
                    f"{file}: orphaned -- {path.name} has no skill-relative link to {rel!r}, "
                    f"so nothing can reach it"
                )
    return issues


def check_plugin(root: Path, agent_names: list[str], skills: dict[str, Definition]) -> list[str]:
    """The guard roster and every namespaced cross-reference, for a fleet that ships as a plugin."""
    manifest = root / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        return []
    try:
        plugin_name = str(json.loads(fs.read_text(manifest)).get("name", "")).strip()
    except (ValueError, AttributeError) as exc:
        return [f"{manifest}: unreadable plugin manifest: {exc}"]
    issues: list[str] = []
    guard = HookScript.load(root / GUARD_SCRIPT, GUARD_ROSTER)
    if guard.rosters is None:
        issues.append(f"{guard.path}: cannot read the guard roster: {guard.error}")
    else:
        if guard.rosters.plugin_name != plugin_name:
            issues.append(
                f"{guard.path}: PLUGIN_NAME {guard.rosters.plugin_name!r} does not match the "
                f"manifest name {plugin_name!r}, so the guard matches nobody"
            )
        guarded = guard.rosters[GUARD_ROSTER]
        for name in sorted(guarded - set(agent_names)):
            issues.append(f"{guard.path}: GUARDED_AGENT_NAMES lists {name!r}, not an agent")
        for path in sorted((root / "agents").glob("*.md")):
            tools = load_definition(path).tool_bases()
            if "Bash" in tools and not tools & WRITE_TOOLS and path.stem not in guarded:
                issues.append(
                    f"{path}: holds Bash and no write tool but is not in GUARDED_AGENT_NAMES, "
                    f"so its 'read-only' is a promise, not a control"
                )
    members = set(agent_names) | set(skills)
    seen: set[tuple[Path, bool, str]] = set()
    for record in collect_references(root, plugin_name):
        key = (record.path, record.is_slash_command, record.target)
        if key in seen:
            continue
        seen.add(key)
        where = f"{record.path}:{record.line}"
        reference = f"{'/' if record.is_slash_command else ''}{plugin_name}:{record.target}"
        if not NAME_RE.fullmatch(record.target):
            issues.append(f"{where}: malformed namespaced reference {reference!r}")
        elif record.is_slash_command and record.target not in skills:
            issues.append(f"{where}: slash-command reference {reference!r} must name a skill")
        elif record.target not in members:
            issues.append(
                f"{where}: {reference} is not an agent or skill in this fleet -- a dangling "
                f"reference fails nowhere at runtime"
            )
    return issues


def _stale_paths(root: Path, doc: Path) -> list[str]:
    issues = []
    for code in INLINE_CODE_RE.findall(fs.read_text(doc)):
        for token in GUIDE_PATH_TOKEN_RE.findall(code):
            token = token.rstrip(".,;:")
            # Only a multi-segment path asserts a location worth checking.
            if len([part for part in token.split("/") if part]) >= 2 and not (
                root / token.rstrip("/")
            ).exists():
                issues.append(
                    f"{doc}: names '{token}', which does not exist in this repository -- a "
                    f"stale path misleads every session that reads it"
                )
    return issues


def check_guide(root: Path) -> list[str]:
    """Claude Code loads CLAUDE.md, not AGENTS.md, so a lost import orphans the guide silently."""
    guide, bridge, program = root / "AGENTS.md", root / "CLAUDE.md", root / PROGRAM_DOC
    issues = _stale_paths(root, program) if program.is_file() else []
    imports = bridge.is_file() and GUIDE_IMPORT in fs.read_text(bridge).splitlines()
    if not guide.is_file():
        if imports:
            issues.append(f"{bridge}: imports {GUIDE_IMPORT} but AGENTS.md does not exist")
        return issues
    if not imports:
        issues.append(f"{guide}: {bridge.name} lacks the line {GUIDE_IMPORT!r}, so it never loads")
    return issues + _stale_paths(root, guide)


def check_adapters(root: Path) -> list[str]:
    """The generated host adapters and hook file must be byte-current."""
    if not (root / ".claude-plugin" / "plugin.json").is_file():
        return []
    # The generator comes from the tree being validated, not this script's own checkout: with
    # `--root` pointing elsewhere, the executing copy would judge bytes it did not produce.
    source = root / "scripts" / "generate_platform_adapters.py"
    if not source.is_file():
        return [f"{source}: missing platform adapter generator"]
    try:
        spec = importlib.util.spec_from_file_location("validated_tree_generator", source)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        return list(generator.validate_platform_support(root))
    except Exception as exc:  # a broken checker must fail loudly, not certify stale copies
        return [f"{root}: platform adapter validation crashed: {exc}"]


def render_inventory(agent_names: list[str], skill_names: list[str]) -> str:
    return "\n".join([
        "<!-- fleet-inventory:start -->",
        f"- **Agents ({len(agent_names)}):** " + ", ".join(f"`{n}`" for n in agent_names),
        f"- **Skills ({len(skill_names)}):** " + ", ".join(f"`{n}`" for n in skill_names),
        "<!-- fleet-inventory:end -->",
    ])


def replace_inventory(content: str, expected: str) -> str:
    if not INVENTORY_RE.search(content):
        raise ValueError("missing fleet inventory markers")
    newline = "\r\n" if "\r\n" in content else "\n"
    return INVENTORY_RE.sub(expected.replace("\n", newline), content, count=1)


def check_inventory(root: Path, expected: str) -> list[str]:
    readme = root / "README.md"
    if not readme.is_file():
        return [f"{readme}: missing README.md"]
    match = INVENTORY_RE.search(fs.read_text(readme))
    if not match:
        return [f"{readme}: missing fleet inventory markers"]
    if match.group(0) != expected:
        return [f"{readme}: fleet inventory drifted; run with --write-inventory"]
    return []


def validate(
    root: Path, *, adapters: bool = True, write_inventory: bool = False
) -> tuple[list[str], list[str], list[str]]:
    """Every check over `root`: (problems, agent names, skill names)."""
    skills, issues = load_skills(root)
    agent_issues, agent_names = check_agents(root, skills)
    issues += agent_issues + check_skills(root, skills)
    issues += check_plugin(root, agent_names, skills) + check_guide(root)
    if adapters:
        issues += check_adapters(root)
    skill_names = list(skills)
    if not issues:
        expected = render_inventory(agent_names, skill_names)
        readme = root / "README.md"
        if write_inventory and readme.is_file():
            try:
                content = readme.read_bytes().decode("utf-8")
                readme.write_bytes(replace_inventory(content, expected).encode("utf-8"))
            except ValueError as exc:
                issues.append(f"{readme}: {exc}")
        issues += check_inventory(root, expected)
    return issues, agent_names, skill_names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(_REPO_ROOT), help="repository root")
    parser.add_argument(
        "--write-inventory", action="store_true", help="rewrite the README inventory first"
    )
    args = parser.parse_args(argv)
    issues, agent_names, skill_names = validate(
        args.root.resolve(), write_inventory=args.write_inventory
    )
    if issues:
        print("Fleet validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print(
        f"Validated {len(agent_names)} agents and {len(skill_names)} skills; "
        "inventory is current."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
