"""Agent definition rules: frontmatter namespace, identity, tools authority, preloads, model,
and the end-of-task packet. Each is one silent-failure tripwire; the why is on the rule."""

from __future__ import annotations

import re

from fleet.findings import Finding
from fleet.frontmatter import NAME_RE
from fleet.policy import POLICY
from fleet.rules import rule
from fleet.snapshot import TOOL_ENTRY_RE, Definition, Fleet

FULL_MODEL_ID_RE = re.compile(r"^claude-[a-z0-9]+(?:-[a-z0-9]+)+$")
# Exact MCP names use the runtime's `mcp__<server>__<tool>` convention. Hyphens are real in tool
# names (`query-docs`), so the built-in-name grammar cannot parse them.
MCP_EXACT_TOOL_RE = re.compile(r"^mcp__[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+$")
MCP_SERVER_GRANT_RE = re.compile(r"^mcp__[A-Za-z0-9_.-]+(?:__\*)?$")
EVIDENCE_LABEL_RE = re.compile(r"\*\*\[(?:un)?(?:verified|sourced)\]\*\*")
PACKET_HEADING_RE = re.compile(
    r"^##\s.*\bpacket\b|^##\s+Output format\b", re.IGNORECASE | re.MULTILINE
)

GROUP = "agents"


def name_findings(name: str, kind: str, definition: Definition, rule_id: str) -> list[Finding]:
    source = definition.path
    if not name:
        return [Finding(rule_id, f"{source}: missing {kind} name", source)]
    findings: list[Finding] = []
    if len(name) > 64:
        findings.append(Finding(rule_id, f"{source}: {kind} name exceeds 64 characters", source))
    if not NAME_RE.fullmatch(name):
        findings.append(Finding(rule_id, f"{source}: invalid {kind} name {name!r}", source))
    return findings


def description_findings(definition: Definition, kind: str, rule_id: str) -> list[Finding]:
    source = definition.path
    description = definition.field("description").strip()
    if not description:
        return [Finding(rule_id, f"{source}: missing {kind} description", source)]
    if len(description) > 1024:
        return [Finding(rule_id, f"{source}: {kind} description exceeds 1024 characters", source)]
    return []


@rule("agents.directory", group=GROUP, why="A repository with no agents/ ships nothing.")
def agents_directory(fleet: Fleet) -> list[Finding]:
    if fleet.agents_dir_exists:
        return []
    path = fleet.root / "agents"
    return [Finding("agents.directory", f"{path}: missing agents directory", path)]


@rule(
    "agent.frontmatter",
    group=GROUP,
    why="A refused frontmatter block would otherwise read as an agent with no configuration.",
)
def agent_frontmatter(fleet: Fleet) -> list[Finding]:
    if not fleet.agents_dir_exists:
        return []
    return [
        Finding("agent.frontmatter", f"{a.path}: missing or malformed frontmatter", a.path)
        for a in fleet.agents
        if a.fields is None
    ]


@rule(
    "agent.frontmatter.keys",
    group=GROUP,
    why="An unknown key does not fail loudly at load time, so a typo silently drops what it "
    "configured; a plugin-inert key reads as armor and is none.",
)
def agent_frontmatter_keys(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    for agent in fleet.parsed_agents:
        path = agent.path
        for key in agent.fields or {}:
            if key not in POLICY.known_agent_fields:
                findings.append(
                    Finding(
                        "agent.frontmatter.keys",
                        f"{path}: unknown frontmatter key {key!r} is not a Claude Code agent "
                        f"field. "
                        f"An unrecognized key does not fail loudly at load time, so a typo here "
                        f"silently "
                        f"drops whatever it was meant to configure.",
                        path,
                    )
                )
            elif key in POLICY.plugin_inert_agent_fields:
                findings.append(
                    Finding(
                        "agent.frontmatter.keys",
                        f"{path}: frontmatter key {key!r} is SILENTLY IGNORED for a "
                        f"plugin-shipped agent, "
                        f"and this fleet ships as a plugin. Declaring it configures nothing while "
                        f"reading "
                        f"as though it does. The read-only guard belongs in hooks/hooks.json, "
                        f"scoped on "
                        f"the payload's 'agent_type'.",
                        path,
                    )
                )
    return findings


@rule(
    "agent.identity",
    group=GROUP,
    why="The name is the routing and namespacing key; it must be valid and match the file.",
)
def agent_identity(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    for agent in fleet.parsed_agents:
        name = agent.field("name")
        findings.extend(name_findings(name, "agent", agent, "agent.identity"))
        if name and name != agent.path.stem:
            findings.append(
                Finding(
                    "agent.identity",
                    f"{agent.path}: agent name {name!r} must match filename {agent.path.stem!r}",
                    agent.path,
                )
            )
        findings.extend(description_findings(agent, "agent", "agent.identity"))
    return findings


@rule(
    "agent.tools",
    group=GROUP,
    why="An absent tools: INHERITS EVERY TOOL; an unknown, unadopted, unavailable, or scoped "
    "entry reads as authority or as a limit while being neither.",
)
def agent_tools(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    rid = "agent.tools"
    for agent in fleet.parsed_agents:
        path = agent.path
        tools = agent.field("tools").strip()
        if not tools:
            # Not a harmless omission: an absent `tools:` INHERITS EVERY TOOL rather than granting
            # none, so a reviewer meant to be read-only would silently receive Write and Edit.
            findings.append(
                Finding(
                    rid,
                    f"{path}: missing explicit tools authority (omitting it inherits ALL tools)",
                    path,
                )
            )
            continue
        parsed_tools = agent.tool_entries()
        if len(parsed_tools) != len(set(parsed_tools)):
            findings.append(Finding(rid, f"{path}: duplicate tool in tools authority", path))
        for tool in parsed_tools:
            if tool.startswith("mcp__"):
                if MCP_EXACT_TOOL_RE.fullmatch(tool):
                    if tool not in POLICY.fleet_mcp_tools:
                        findings.append(
                            Finding(
                                rid,
                                f"{path}: MCP tool {tool!r} is structurally valid but is not "
                                f"adopted "
                                f"by this fleet; add it to FLEET_MCP_TOOLS deliberately if the "
                                f"agent "
                                f"needs it",
                                path,
                            )
                        )
                elif MCP_SERVER_GRANT_RE.fullmatch(tool):
                    findings.append(
                        Finding(
                            rid,
                            f"{path}: server-wide MCP grant {tool!r} is real Claude Code syntax "
                            f"but "
                            f"is not adopted by this fleet. It silently acquires future tools from "
                            f"that server, so list each required exact tool in FLEET_MCP_TOOLS",
                            path,
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            rid,
                            f"{path}: malformed MCP tool entry {tool!r} in tools authority; "
                            f"expected "
                            f"an exact mcp__<server>__<tool> name",
                            path,
                        )
                    )
                continue

            entry = TOOL_ENTRY_RE.match(tool)
            if not entry:
                findings.append(
                    Finding(rid, f"{path}: malformed tool entry {tool!r} in tools authority", path)
                )
                continue
            base, scope = entry.group(1), entry.group(2)

            if base not in POLICY.runtime_tools:
                findings.append(
                    Finding(
                        rid,
                        f"{path}: unknown tool {base!r} in tools authority is not a Claude Code "
                        f"tool",
                        path,
                    )
                )
            elif base in POLICY.subagent_unavailable_tools:
                findings.append(
                    Finding(
                        rid,
                        f"{path}: tool {base!r} is never available to a subagent regardless of "
                        f"this "
                        f"grant (it needs the main conversation's UI or session state); granting "
                        f"it "
                        f"reads like a capability the agent does not have",
                        path,
                    )
                )
            elif base not in POLICY.fleet_tools:
                findings.append(
                    Finding(
                        rid,
                        f"{path}: tool {base!r} is a real Claude Code tool but is not adopted by "
                        f"this "
                        f"fleet; add it to FLEET_TOOLS deliberately if the agent needs it",
                        path,
                    )
                )

            if scope is not None and base == "Agent":
                # `Agent(worker)` restricts spawning ONLY for an agent running as the main thread
                # (`claude --agent`). In a subagent definition the parenthesized type list is
                # IGNORED, so this grants UNRESTRICTED spawn while reading like a limit.
                findings.append(
                    Finding(
                        rid,
                        f"{path}: scoped grant {tool!r} does not restrict anything here. The "
                        f"Agent(type) allowlist applies only to a main-thread agent (claude "
                        f"--agent); "
                        f"in a subagent definition the type list is ignored and spawning is "
                        f"unrestricted. Use a bare 'Agent' so the grant matches reality",
                        path,
                    )
                )
            elif scope is not None:
                findings.append(
                    Finding(
                        rid,
                        f"{path}: scoped grant {tool!r} uses permission-rule syntax that the "
                        f"frontmatter 'tools:' field SILENTLY IGNORES. Probed on CLI 2.1.200 and "
                        f"again "
                        f"on 2.1.270 (2026-09-13, both `Bash(git diff:*)` and `Bash(git diff *)`, "
                        f"under "
                        f"default and dontAsk): an agent granted either ran `git status` exactly "
                        f"like "
                        f"one granted a bare `Bash` — the specifier restricts nothing while "
                        f"reading as "
                        f"though it does, whatever the subagent reference currently says. "
                        f"Specifiers work only in settings.json permission rules (session-wide) "
                        f"or a "
                        f"PreToolUse hook; narrow there, not here.",
                        path,
                    )
                )
    return findings


@rule(
    "agent.tools.trust-boundary",
    group=GROUP,
    why="Investigation roles are split at the tool layer; a one-line frontmatter edit must not "
    "silently collapse the local-versus-external trust boundary.",
)
def agent_trust_boundary(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    rid = "agent.tools.trust-boundary"
    for agent in fleet.parsed_agents:
        path = agent.path
        name = agent.field("name")
        role = POLICY.roles.get(name)
        if role is None:
            continue
        parsed_tools = agent.tool_entries() if agent.field("tools").strip() else []
        missing_required_tools = sorted(role.required - set(parsed_tools))
        if missing_required_tools:
            findings.append(
                Finding(
                    rid,
                    f"{path}: evidence role {name!r} is missing required tools "
                    f"{missing_required_tools}. Its investigation method depends on this exact "
                    f"side of "
                    f"the local-versus-external trust boundary, so removing authority silently "
                    f"makes "
                    f"the method impossible",
                    path,
                )
            )
        forbidden_tools = sorted(role.forbidden & set(parsed_tools))
        if forbidden_tools:
            findings.append(
                Finding(
                    rid,
                    f"{path}: trust-separated role {name!r} holds forbidden tools "
                    f"{forbidden_tools}. "
                    f"Local/private repository access and external fetched content must not "
                    f"coexist in "
                    f"one subordinate role; prose cannot enforce that boundary",
                    path,
                )
            )
    return findings


@rule(
    "agent.skills",
    group=GROUP,
    why="A skills: entry that does not resolve, or names an explicit-only skill, configures "
    "nothing while reading like a guarantee.",
)
def agent_skills(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    rid = "agent.skills"
    for agent in fleet.parsed_agents:
        path = agent.path
        for skill_name in agent.preloaded_skills():
            skill_file = fleet.root / "skills" / skill_name / "SKILL.md"
            if not skill_file.is_file():
                findings.append(
                    Finding(
                        rid,
                        f"{path}: skills: entry {skill_name!r} does not resolve to "
                        f"skills/{skill_name}/SKILL.md -- preloading silently drops it",
                        path,
                    )
                )
                continue
            skill = fleet.skill(skill_name)
            skill_fields = (skill.fields if skill else None) or {}
            if skill_fields.get("disable-model-invocation", "").strip().lower() == "true":
                findings.append(
                    Finding(
                        rid,
                        f"{path}: skills: entry {skill_name!r} names {skill_file}, which sets "
                        f"disable-model-invocation: true -- a skill so marked CANNOT be preloaded "
                        f"(preloading draws from the same set of skills Claude can invoke), so "
                        f"listing "
                        f"it here configures nothing",
                        path,
                    )
                )
    return findings


@rule(
    "agent.model",
    group=GROUP,
    why="A pinned model ID goes stale silently while an alias follows the model upgrade.",
)
def agent_model(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    aliases = ", ".join(sorted(POLICY.model_aliases))
    for agent in fleet.parsed_agents:
        path = agent.path
        model = agent.field("model").strip()
        if not model:
            findings.append(Finding("agent.model", f"{path}: missing model", path))
        elif model in POLICY.model_aliases:
            pass
        elif FULL_MODEL_ID_RE.match(model):
            findings.append(
                Finding(
                    "agent.model",
                    f"{path}: model {model!r} is a valid Claude Code model but is pinned; "
                    f"this fleet requires an alias ({aliases}) so agents follow model upgrades "
                    f"instead of rotting on a stale pin",
                    path,
                )
            )
        else:
            findings.append(
                Finding(
                    "agent.model",
                    f"{path}: unknown model {model!r} (expected one of: {aliases})",
                    path,
                )
            )
    return findings


@rule(
    "agent.packet",
    group=GROUP,
    why="Evidence labels and the end-of-task packet are the handoff contract; drift is silent.",
)
def agent_packet(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    for agent in fleet.parsed_agents:
        path = agent.path
        content = agent.text or ""
        if EVIDENCE_LABEL_RE.search(content):
            for stem in POLICY.evidence_label_stems:
                if stem not in content:
                    findings.append(
                        Finding(
                            "agent.packet",
                            f"{path}: evidence labels drifted from canonical phrasing; expected "
                            f"{stem!r}",
                            path,
                        )
                    )
        if not PACKET_HEADING_RE.search(content):
            findings.append(
                Finding(
                    "agent.packet",
                    f"{path}: missing end-of-task packet ('## ... packet' or '## Output format' "
                    f"section)",
                    path,
                )
            )
    return findings


@rule("agents.roster", group=GROUP, why="No agents, or two with one name, ships a broken fleet.")
def agents_roster(fleet: Fleet) -> list[Finding]:
    if not fleet.agents_dir_exists:
        return []
    agents_dir = fleet.root / "agents"
    names = [a.name for a in fleet.parsed_agents]
    findings: list[Finding] = []
    if not names:
        findings.append(
            Finding("agents.roster", f"{agents_dir}: no agent definitions found", agents_dir)
        )
    if len(names) != len(set(names)):
        findings.append(
            Finding("agents.roster", f"{agents_dir}: duplicate agent names", agents_dir)
        )
    return findings
