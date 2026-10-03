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

import re

from fleet.findings import Finding
from fleet.policy import POLICY
from fleet.rules import rule
from fleet.rules.references import plugin_reference_findings
from fleet.snapshot import GUARD_ROSTER, Fleet

# The hook reads its fast-path from "$IN" and its identity fallback from "$SQ", a
# whitespace-stripped copy, so JSON spacing cannot decide whether the fallback fires. Either
# variable opens a roster block, and the cross-check must recognise both.
CASE_BLOCK_RE = re.compile(r'case "\$(IN|SQ)" in')
# Every `case` opener and closer, so nesting depth can be tracked: only blocks opened at the
# outer level decide anything.
CASE_TOKEN_RE = re.compile(r"\bcase\s+\S+\s+in\b|\besac\b")
# The two blocks a roster must reach. Named, not counted: see `_select_roster_blocks`.
ROSTER_VARIABLES = ("IN", "SQ")
GROUP = "plugin"


def _roster_blocks(command: str) -> list[tuple[str, str]]:
    """Every roster-bearing `case` block at the OUTER level, with the variable that opened it.

    Depth is tracked rather than assumed. A `case "$SQ"` nested inside the fast path decides
    nothing -- the fast path already chose to run the interpreter by the time it is reached -- but
    a malformed hook can put a roster-shaped decoy there and leave the real fallback matching
    nobody. Taking the first block per variable would then check the decoy and pass (Copilot,
    PR #193). Only blocks opened at depth 0 are returned.
    """

    blocks: list[tuple[str, str]] = []
    depth = 0
    for token in CASE_TOKEN_RE.finditer(command):
        text = token.group(0)
        if text == "esac":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            variable = CASE_BLOCK_RE.match(text)
            if variable is not None:
                blocks.append((variable.group(1), command[token.end() :]))
        depth += 1
    return blocks


def _case_alternatives(block: str) -> set[str]:
    """The `case` alternatives the block actually matches on, as exact tokens.

    A SUBSTRING test does not prove a pattern is present: a rendered
    `*homelab-engineer*requires-extra*` contains `*homelab-engineer*`, satisfies the check, and
    still never matches an ordinary payload for that agent (Copilot, PR #193). The alternative
    list ends at the first unquoted `)`, which is where `case` itself ends it, and the roster
    tokens this fleet renders contain no `)`.
    """

    return {alternative.strip() for alternative in block.split(")", 1)[0].split("|")}


def _missing_patterns(variable: str, name: str, plugin_name: str, block: str) -> list[str]:
    """The roster patterns `name` must contribute to this block, and which of them are absent.

    A BARE-NAME substring search is not enough: a `$SQ` slice can run on into a denial reason
    whose English sentence names the agent, so the roster could be replaced with a name that
    matches nobody and the check would still find the agent, in prose (Copilot, PR #193).
    Matching the exact `case` alternation tokens closes that: prose does not contain them.

    Each token must be an ENTIRE alternative, not a substring of one: a pattern narrowed to
    `*name*something-else*` contains the expected text and matches nothing real.

    These tokens are spelled HERE rather than imported from `fleet.hooks`, deliberately. This is
    the independent check on what that renderer produced; building the expectation from the
    renderer's own helper would compare the file against a copy its author wrote, which is the
    one thing a diagnostic naming an external authority must not do (`AGENTS.md`). The roster
    names and the namespace still come from the hook script, which is the authority here.
    """

    if variable == "IN":
        # The fast path is a loose substring filter over the raw payload, by design: it only
        # decides whether the interpreter is launched.
        wanted = [f"*{name}*"]
    else:
        # The fallback matches the IDENTITY, in both spellings, against the whitespace-stripped
        # payload. Either spelling missing leaves that spelling unguarded.
        wanted = [
            f"""*'"agent_type":"{plugin_name}:{name}"'*""",
            f"""*'"agent_type":"{name}"'*""",
        ]
    present = _case_alternatives(block)
    return [pattern for pattern in wanted if pattern not in present]


def _select_roster_blocks(blocks: list[tuple[str, str]]) -> dict[str, str]:
    """The fast-path filter and the no-interpreter fallback, chosen by the variable each reads.

    Never by position: a hook may nest another `case` inside its fallback, so the last block need
    not be the one that decides, and checking a nested block reads as enforcement while checking
    prose. The first block each variable opens is the outer one, which is the one that decides.
    """

    found: dict[str, str] = {}
    for variable, block in blocks:
        found.setdefault(variable, block)
    return found


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


def plugin_findings(
    fleet: Fleet,
    agent_names: list[str] | None = None,
    skill_names: list[str] | None = None,
) -> list[Finding]:
    """The pass, with the roster a caller may supply (the legacy `validate_plugin` contract)."""
    if not fleet.ships_as_plugin:
        return []
    supplied_agent_names = fleet.agent_names if agent_names is None else agent_names
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

    agent_names = set(supplied_agent_names)

    command = fleet.hook_command_for("readonly-guard.py")
    # An empty GUARDED_AGENT_NAMES guards nobody by design and
    # renders no hook, so only a non-empty roster owes one.
    if command is None:
        if guarded:
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
        cases = _select_roster_blocks(blocks)
        if not set(ROSTER_VARIABLES) <= cases.keys():
            findings.append(
                Finding(
                    "plugin.hooks.guard",
                    f"{hooks_path}: expected the PreToolUse/Bash hook to contain a "
                    f'`case "$IN" in` fast-path filter and a `case "$SQ" in` no-interpreter '
                    f"fallback; found blocks on "
                    f"{[variable for variable, _ in blocks] or 'no roster variable'}. "
                    f"The roster cross-check below cannot verify a hook it does not recognize, "
                    f"so this fails rather than passing a hook it did not actually check.",
                    hooks_path,
                )
            )
        else:
            for label, variable in (
                ("fast-path filter", "IN"),
                ("no-interpreter fallback", "SQ"),
            ):
                block = cases[variable]
                for name in sorted(guarded):
                    missing = _missing_patterns(
                        variable, name, guard.plugin_name or plugin_name, block
                    )
                    if missing:
                        findings.append(
                            Finding(
                                "plugin.hooks.guard",
                                f"{hooks_path}: the hook's {label} is missing {missing} for "
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

    findings.extend(plugin_reference_findings(fleet, list(supplied_agent_names), skill_names))
    return findings
