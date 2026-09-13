"""Cross-reference rules: bare skill names, perishable tokens, and (for a plugin) namespaced
references, description namespacing, and `~/.claude` paths."""

from __future__ import annotations

import re
from pathlib import Path

from fleet.findings import Finding
from fleet.frontmatter import NAME_RE
from fleet.policy import POLICY
from fleet.references import collect_references
from fleet.rules import rule
from fleet.snapshot import Fleet

INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")


@rule(
    "references.bare-skill",
    group="references",
    why="A bare backticked skill name asserts 'already in context'; without a preload the "
    "instruction cannot execute and nothing errors (observed: sde-fullstack and `code-craft`).",
)
def bare_skill_references(fleet: Fleet, skill_names: list[str] | None = None) -> list[Finding]:
    """`skill_names` is the roster a legacy caller may supply; the snapshot's own is the default.
    A test grades a synthetic body against names the tree under validation does not carry."""
    findings: list[Finding] = []
    known = set(fleet.skill_names if skill_names is None else skill_names)
    for agent in fleet.agents:
        preloaded = set(agent.preloaded_skills())
        for span in sorted(set(INLINE_CODE_RE.findall(agent.text or ""))):
            if span in known and span not in preloaded:
                findings.append(
                    Finding(
                        "references.bare-skill",
                        f"{agent.path}: bare backticked skill name `{span}` claims the skill is "
                        f"already in "
                        f"this agent's context, but it is not in the skills: preload — the "
                        f"reference "
                        f"is unreachable authority that reads as configured, and nothing errors at "
                        f"runtime. Preload it; use the namespaced form if routing is the intent; "
                        f"or "
                        f"give an explicit, resolvable "
                        f"${{CLAUDE_PLUGIN_ROOT}}/skills/{span}/SKILL.md path if the agent must "
                        f"read it.",
                        agent.path,
                    )
                )
    return findings


@rule(
    "references.perishable-token",
    group="references",
    why="A perishable platform fact copied outside its owner file keeps teaching stale behaviour "
    "with no runtime error after the platform moves.",
)
def perishable_tokens(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    for token, owner in POLICY.perishable_tokens.items():
        for path in fleet.markdown_files():
            if path.relative_to(fleet.root).as_posix() == owner:
                continue
            if token in (fleet.markdown_texts[path] or ""):
                findings.append(
                    Finding(
                        "references.perishable-token",
                        f"{path}: carries perishable platform token {token!r}, whose only allowed "
                        f"home "
                        f"is {owner}. A second copy stays behind when the platform moves and keeps "
                        f"teaching the stale behavior with no runtime error — state the role-local "
                        f"consequence here and point at the owner file for the fact.",
                        path,
                    )
                )
    return findings


def plugin_reference_findings(
    fleet: Fleet,
    agent_names: list[str] | None = None,
    skill_names: list[str] | None = None,
) -> list[Finding]:
    """The plugin-scoped reference rules the legacy `validate_plugin` ran last: description
    namespacing, `~/.claude` paths, and every namespaced reference's shape and resolution.

    `agent_names` / `skill_names` default to the snapshot's; the compatibility layer passes a
    caller's roster through, as the legacy signature promised."""
    findings: list[Finding] = []
    plugin_name = fleet.plugin_name
    agent_names = fleet.agent_names if agent_names is None else agent_names
    skill_names = fleet.skill_names if skill_names is None else skill_names
    fleet_members = set(agent_names) | set(skill_names)
    definitions = [(a.path, a.path.stem, a) for a in fleet.agents]
    definitions += [(s.path, s.directory.name, s) for s in fleet.skills]

    for path, own, definition in definitions:
        text = definition.text or ""
        description = definition.field("description")
        for other in sorted(fleet_members - {own}):
            if re.search(rf"(?<![\w:-]){re.escape(other)}(?![\w-])", description):
                findings.append(
                    Finding(
                        "plugin.references.description-namespace",
                        f"{path}: description names {other!r} without the plugin namespace. Every "
                        f"component a plugin ships is namespaced, so the real name is "
                        f"{plugin_name}:{other} — a bare reference points at nothing and degrades "
                        f"the routing this description exists to drive.",
                        path,
                    )
                )
        # `~/.claude/agents|skills/` does NOT contain this fleet once it ships as a plugin. The
        # `(?!\*)` spares the doc-reference form (`~/.claude/agents/*.md`) and catches only a path
        # being resolved to a specific file -- the thing that silently stops resolving.
        for match in re.finditer(r"~/\.claude/(agents|skills)/(?!\*)", text):
            kind = match.group(1)
            findings.append(
                Finding(
                    "plugin.references.home-path",
                    f"{path}: resolves a fleet file under '~/.claude/{kind}/', which will NOT "
                    f"contain this "
                    f"fleet once it ships as a plugin — those files live under "
                    f"${{CLAUDE_PLUGIN_ROOT}}. "
                    f"Use '${{CLAUDE_PLUGIN_ROOT}}/{kind}/...' instead.",
                    path,
                )
            )

    # Every namespaced cross-reference must be one complete, well-formed token that resolves to
    # the right kind of member: a prefix-only matcher can certify `code-reviewer_v2` as
    # `code-reviewer`, and union membership can certify a slash command naming an agent.
    if plugin_name:
        agents = set(agent_names)
        skills = set(skill_names)
        # One shared extraction (fleet.references). Deduping per file to (slash, target) keeps
        # one message per distinct reference however many times a file repeats it.
        by_path: dict[Path, set[tuple[bool, str]]] = {}
        for record in collect_references(fleet.root, plugin_name, texts=fleet.markdown_texts):
            by_path.setdefault(record.path, set()).add((record.is_slash_command, record.target))
        for path, references in by_path.items():
            for is_slash_command, target in sorted(references):
                reference = f"{'/' if is_slash_command else ''}{plugin_name}:{target}"
                if not NAME_RE.fullmatch(target):
                    findings.append(
                        Finding(
                            "plugin.references.namespaced",
                            f"{path}: malformed namespaced reference {reference!r}; the complete "
                            f"target "
                            f"must be a kebab-case fleet name. Prefix matching would silently "
                            f"certify "
                            f"a different live member while this token fails to resolve at "
                            f"runtime.",
                            path,
                        )
                    )
                    continue
                if is_slash_command and target not in skills:
                    target_kind = "an agent" if target in agents else "no shipped skill"
                    findings.append(
                        Finding(
                            "plugin.references.namespaced",
                            f"{path}: slash-command reference {reference!r} names {target_kind}; a "
                            f"slash-command reference must target a skill, or the invocation "
                            f"cannot "
                            f"resolve at runtime.",
                            path,
                        )
                    )
                    continue
                if target not in fleet_members:
                    findings.append(
                        Finding(
                            "plugin.references.namespaced",
                            f"{path}: references {reference}, which is not an agent or "
                            f"skill in this fleet. A dangling cross-reference fails nowhere at "
                            f"runtime — routing and handoffs just quietly stop resolving — so a "
                            f"rename or removal must update every referrer, and this rule is what "
                            f"makes the miss loud.",
                            path,
                        )
                    )
    return findings
