"""Rules that apply only to a repository which SHIPS AS A PLUGIN.

Every rule here is a tripwire for a failure that is SILENT at runtime. A plugin-shipped agent
cannot carry its own `hooks:`, so the read-only guard has exactly one place to live and exactly
one way to find its subject; get any link in that chain wrong and nothing errors, nothing logs,
and `code-reviewer` simply runs Bash unguarded against the repository it is reviewing. The
rosters are read from the hook scripts as DATA (`fleet.snapshot.HookScript`, captured once in
`Fleet.load`), never by running them. All rules return [] when there is no manifest, so a
synthetic fixture stays valid.
"""

from __future__ import annotations

from fleet.findings import Finding
from fleet.policy import POLICY
from fleet.rules import rule
from fleet.rules.references import plugin_reference_findings
from fleet.snapshot import GUARD_ROSTER, Fleet

GROUP = "plugin"


PLUGIN_RULE_IDS = (
    "plugin.rules",
    "plugin.manifest",
    "plugin.guard",
    "plugin.hooks.guard",
    "plugin.guard.roster",
    "plugin.references.description-namespace",
    "plugin.references.home-path",
    "plugin.references.namespaced",
)


@rule(
    "plugin.rules",
    group=GROUP,
    why="The manifest, the guard, and the hook file must agree on names and rosters in every "
    "direction, or a guarded agent silently runs unguarded.",
    emits=PLUGIN_RULE_IDS,
)
def plugin_rules(fleet: Fleet) -> list[Finding]:
    """One legacy pass, kept as one rule so its early returns keep their exact semantics: a
    guard that cannot be read short-circuits everything that would have cross-checked it. Each
    check emits its own id, all declared on the registration above."""
    return plugin_findings(fleet)


def plugin_findings(fleet: Fleet) -> list[Finding]:
    """Every plugin-wiring check over the snapshot."""
    if not fleet.ships_as_plugin:
        return []
    manifest_path = fleet.plugin_manifest_path
    if fleet.plugin_manifest_error is not None:
        return [
            Finding(
                "plugin.manifest",
                f"{manifest_path}: unreadable plugin manifest: {fleet.plugin_manifest_error}",
                manifest_path,
            )
        ]
    manifest = fleet.plugin_manifest or {}
    findings: list[Finding] = []
    plugin_name = fleet.plugin_name
    if not plugin_name:
        findings.append(
            Finding(
                "plugin.manifest",
                f"{manifest_path}: manifest is missing the required 'name'",
                manifest_path,
            )
        )
    if not manifest.get("author"):
        # `claude plugin validate --strict` treats a missing author as an error; say so here rather
        # than letting CI be the first to find out.
        findings.append(
            Finding(
                "plugin.manifest",
                f"{manifest_path}: missing 'author' — `claude plugin validate --strict` fails "
                f"without it",
                manifest_path,
            )
        )

    hooks_path = fleet.hooks_path
    guard_path = fleet.guard.path
    if not fleet.guard.exists:
        return findings + [
            Finding("plugin.guard", f"{guard_path}: missing the read-only guard", guard_path)
        ]
    guard = fleet.guard.rosters
    if guard is None:  # a guard whose rosters cannot even be read guards nothing
        return findings + [
            Finding(
                "plugin.guard", f"{guard_path}: cannot load guard: {fleet.guard.error}", guard_path
            )
        ]
    guarded = guard[GUARD_ROSTER]

    if plugin_name and guard.plugin_name != plugin_name:
        findings.append(
            Finding(
                "plugin.guard",
                f"{guard_path}: PLUGIN_NAME {guard.plugin_name!r} does not match the manifest name "
                f"{plugin_name!r}. The guard recognizes its subject by a NAMESPACED agent_type, "
                f"so a "
                f"mismatch means it matches nobody and silently guards nothing.",
                guard_path,
            )
        )

    agent_names = set(fleet.agent_names)

    command = fleet.hook_command_for("readonly-guard.py")
    # An empty GUARDED_AGENT_NAMES guards nobody by design and
    # renders no hook, so only a non-empty roster owes one.
    if command is None:
        if guarded:
            findings.append(
                Finding(
                    "plugin.hooks.guard",
                    f"{hooks_path}: no PreToolUse/Bash hook runs scripts/readonly-guard.py. "
                    f"A plugin-shipped agent cannot carry its own hooks, so this file is the ONLY "
                    f"place the "
                    f"read-only guard can be attached — without it, code-reviewer holds Bash "
                    f"unguarded.",
                    hooks_path,
                )
            )
    else:
        if "${CLAUDE_PLUGIN_ROOT}" not in command:
            findings.append(
                Finding(
                    "plugin.hooks.guard",
                    f"{hooks_path}: the PreToolUse/Bash hook must run the guard from "
                    f"${{CLAUDE_PLUGIN_ROOT}} — the plugin's own installed copy. Resolving it any "
                    f"other "
                    f"way risks executing a guard supplied by the repository under review.",
                    hooks_path,
                )
            )

    # The guard's subject list and the agent roster must agree, in both directions.
    for name in sorted(guarded - agent_names):
        findings.append(
            Finding(
                "plugin.guard.roster",
                f"{guard_path}: GUARDED_AGENT_NAMES lists {name!r}, which is not an agent in "
                f"agents/",
                guard_path,
            )
        )
    for agent in fleet.agents:
        tools = agent.tool_bases()
        if "Bash" in tools and not (tools & POLICY.write_tools) and agent.path.stem not in guarded:
            findings.append(
                Finding(
                    "plugin.guard.roster",
                    f"{agent.path}: agent {agent.path.stem!r} holds Bash and no write tool — a "
                    f"read-only agent whose "
                    f"only route to mutation is the shell — but it is absent from "
                    f"GUARDED_AGENT_NAMES in "
                    f"scripts/readonly-guard.py, so the guard ignores it and its 'read-only' is a "
                    f"promise, "
                    f"not a control.",
                    agent.path,
                )
            )

    findings.extend(plugin_reference_findings(fleet))
    return findings
