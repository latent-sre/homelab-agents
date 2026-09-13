"""Rules that apply only to a repository which SHIPS AS A PLUGIN.

Every rule here is a tripwire for a failure that is SILENT at runtime. A plugin-shipped agent
cannot carry its own `hooks:`, so the read-only guard has exactly one place to live and exactly
one way to find its subject; get any link in that chain wrong and nothing errors, nothing logs,
and `code-reviewer` simply runs Bash unguarded against the repository it is reviewing. The
rosters are read from the hook scripts as DATA (`fleet.snapshot.read_rosters`), never by running
them. All rules return [] when there is no manifest, so a synthetic fixture stays valid.
"""

from __future__ import annotations

import re

from fleet.findings import Finding
from fleet.policy import POLICY
from fleet.rules import rule
from fleet.rules.references import plugin_reference_findings
from fleet.snapshot import Fleet, RosterError, read_rosters

# The hook reads its fast-path from "$IN" and its identity fallback from "$SQ", a
# whitespace-stripped copy, so JSON spacing cannot decide whether the fallback fires. Either
# variable opens a roster block, and the cross-check must recognise both.
CASE_BLOCK_RE = re.compile(r'case "\$(?:IN|SQ)" in')
GROUP = "plugin"


def _roster_blocks(command: str) -> list[str]:
    return [segment.split("esac", 1)[0] for segment in CASE_BLOCK_RE.split(command)[1:]]


@rule(
    "plugin.rules",
    group=GROUP,
    why="The manifest, the guard, the gate, and the hook file must agree on names and rosters "
    "in every direction, or a guarded agent silently runs unguarded.",
)
def plugin_rules(fleet: Fleet) -> list[Finding]:
    """One legacy pass, kept as one rule so its early returns keep their exact semantics: a
    guard that cannot be read short-circuits everything that would have cross-checked it."""
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

    root = fleet.root
    hooks_path = fleet.hooks_path
    guard_path = root / "scripts" / "readonly-guard.py"
    if not guard_path.is_file():
        return findings + [
            Finding("plugin.guard", f"{guard_path}: missing the read-only guard", guard_path)
        ]
    try:
        guard = read_rosters(guard_path, "GUARDED_AGENT_NAMES")
    except RosterError as exc:  # a guard whose rosters cannot even be read guards nothing
        return findings + [
            Finding("plugin.guard", f"{guard_path}: cannot load guard: {exc}", guard_path)
        ]
    guarded = guard["GUARDED_AGENT_NAMES"]

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

    # The live-effect gate is the guard's mirror image for a Bash-and-Write agent; it has the
    # same single place to live and the same silent failure modes, so the same links are held.
    agent_names = set(fleet.agent_names)
    gate_path = root / "scripts" / "live-effect-gate.py"
    try:
        gate = read_rosters(gate_path, "GATED_AGENT_NAMES")
    except RosterError as exc:  # a gate that cannot be read gates nothing
        findings.append(
            Finding("plugin.gate", f"{gate_path}: cannot load live-effect gate: {exc}", gate_path)
        )
        gate = None
    if gate is not None:
        gated = gate["GATED_AGENT_NAMES"]
        if plugin_name and gate.plugin_name != plugin_name:
            findings.append(
                Finding(
                    "plugin.gate",
                    f"{gate_path}: PLUGIN_NAME {gate.plugin_name!r} does not match the manifest "
                    f"name "
                    f"{plugin_name!r}. The gate recognizes its subject by a NAMESPACED "
                    f"agent_type, so a "
                    f"mismatch means it matches nobody and silently gates nothing.",
                    gate_path,
                )
            )
        for name in sorted(gated):
            agent = next((a for a in fleet.agents if a.path.stem == name), None)
            if name not in agent_names:
                findings.append(
                    Finding(
                        "plugin.gate",
                        f"{gate_path}: GATED_AGENT_NAMES names {name!r}, which is not an agent in "
                        f"agents/ — a typo here gates nobody.",
                        gate_path,
                    )
                )
                continue
            if agent is None or "Bash" not in agent.tool_bases():
                findings.append(
                    Finding(
                        "plugin.gate",
                        f"{gate_path}: gated agent {name!r} holds no Bash, so the gate can never "
                        f"fire "
                        f"for it",
                        gate_path,
                    )
                )
            if name in guarded:
                findings.append(
                    Finding(
                        "plugin.gate",
                        f"{gate_path}: {name!r} is in both GATED_AGENT_NAMES and the guard's "
                        f"GUARDED_AGENT_NAMES; a read-only agent gets the guard, a live-effect "
                        f"agent "
                        f"gets the gate, never both (the guard would deny every live verb before "
                        f"the "
                        f"gate asked)",
                        gate_path,
                    )
                )
        gate_command = fleet.hook_command_for("live-effect-gate.py")
        if gate_command is None:
            findings.append(
                Finding(
                    "plugin.hooks.gate",
                    f"{hooks_path}: no PreToolUse/Bash hook runs "
                    f"scripts/live-effect-gate.py. A plugin-shipped agent cannot carry its own "
                    f"hooks, "
                    f"so this file is the ONLY place the live-effect gate can be attached — "
                    f"without "
                    f"it, homelab-engineer's managed gate is prose.",
                    hooks_path,
                )
            )
        elif "${CLAUDE_PLUGIN_ROOT}/scripts/live-effect-gate.py" not in gate_command:
            findings.append(
                Finding(
                    "plugin.hooks.gate",
                    f"{hooks_path}: the live-effect-gate.py hook must run the gate "
                    f"from ${{CLAUDE_PLUGIN_ROOT}} — the plugin's own installed copy — never a "
                    f"relative path a repository under operation could supply.",
                    hooks_path,
                )
            )
        if gate_command is not None:
            # The gate hook carries two rosters, and each disarms it alone: the `case` fast-path
            # decides whether the gate runs at all, and the no-interpreter fallback is what
            # decides when no Python answers. A name added to GATED_AGENT_NAMES after an incident
            # would gate NOTHING while every check stays green without this (review-reported).
            gate_blocks = _roster_blocks(gate_command)
            if len(gate_blocks) < 2:
                findings.append(
                    Finding(
                        "plugin.hooks.gate",
                        f"{hooks_path}: expected the live-effect-gate hook to "
                        f'contain two `case "$IN" in` blocks (the fast-path filter and the '
                        f"no-interpreter fallback), found {len(gate_blocks)}. The roster "
                        f"cross-check "
                        f"cannot verify a hook it does not recognize, so this fails rather than "
                        f"passing a hook it did not actually check.",
                        hooks_path,
                    )
                )
            else:
                for label, block in (
                    ("fast-path filter", gate_blocks[0]),
                    ("no-interpreter fallback", gate_blocks[-1]),
                ):
                    for name in sorted(gated):
                        if name not in block:
                            findings.append(
                                Finding(
                                    "plugin.hooks.gate",
                                    f"{hooks_path}: the live-effect-gate hook's "
                                    f"{label} never names {name!r}, but "
                                    f"scripts/live-effect-gate.py "
                                    f"lists it in GATED_AGENT_NAMES. The fast-path decides "
                                    f"whether the "
                                    f"gate runs at all and the fallback is what decides when no "
                                    f"interpreter answers, so a name missing from EITHER leaves "
                                    f"that "
                                    f"agent's live effects ungated — silently, because the hook "
                                    f"still "
                                    f"exits 0.",
                                    hooks_path,
                                )
                            )

    command = fleet.hook_command_for("readonly-guard.py")
    if command is None:
        findings.append(
            Finding(
                "plugin.hooks.guard",
                f"{hooks_path}: no PreToolUse hook with matcher 'Bash' and a command. "
                f"A plugin-shipped agent cannot carry its own hooks, so this file is the ONLY "
                f"place the "
                f"read-only guard can be attached — without it, code-reviewer holds Bash "
                f"unguarded.",
                hooks_path,
            )
        )
    else:
        if "readonly-guard.py" not in command:
            findings.append(
                Finding(
                    "plugin.hooks.guard",
                    f"{hooks_path}: the PreToolUse/Bash hook does not run "
                    f"scripts/readonly-guard.py",
                    hooks_path,
                )
            )
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
        # The hook string carries TWO independent copies of the roster, and each one can disarm
        # the guard on its own; a name present in only one block satisfies a substring check while
        # the other block silently lets the agent through (caught in review of this very rule).
        blocks = _roster_blocks(command)
        if len(blocks) < 2:
            findings.append(
                Finding(
                    "plugin.hooks.guard",
                    f"{hooks_path}: expected the PreToolUse/Bash hook to contain two "
                    f'`case "$IN" in` blocks (the fast-path filter and the no-interpreter '
                    f"fallback), "
                    f"found {len(blocks)}. The roster cross-check below cannot verify a hook it "
                    f"does not "
                    f"recognize, so this fails rather than passing a hook it did not actually "
                    f"check.",
                    hooks_path,
                )
            )
        else:
            for label, block in (
                ("fast-path filter", blocks[0]),
                ("no-interpreter fallback", blocks[-1]),
            ):
                for name in sorted(guarded):
                    if name not in block:
                        findings.append(
                            Finding(
                                "plugin.hooks.guard",
                                f"{hooks_path}: the hook's {label} never names "
                                f"{name!r}, but scripts/readonly-guard.py lists it in "
                                f"GUARDED_AGENT_NAMES. The fast-path decides whether the guard "
                                f"runs at "
                                f"all and the fallback is what fails closed when no interpreter "
                                f"answers, so a name missing from EITHER leaves that agent's "
                                f"'read-only' "
                                f"a promise with no control behind it — silently, because the hook "
                                f"still exits 0.",
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
