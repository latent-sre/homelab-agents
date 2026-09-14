"""The Claude hook file, rendered from the guard and gate rosters.

`hooks/hooks.json` is the only place a plugin-shipped fleet can arm the read-only guard and the
live-effect gate: a plugin agent's own `hooks:` frontmatter is silently ignored, so a guard
declared there is armor that is not. `tests/test_hook_wiring.py` owns that fact and executes the
shell string these templates produce.

Each hook names its roster TWICE -- once in the `case "$IN"` fast path, which decides whether the
interpreter runs at all, and once in the `case "$SQ"` identity fallback, which fails closed when
no interpreter answers. Both copies were maintained by hand against the rosters declared in the
hook scripts, and a name reaching only one of them satisfies a substring check while the other
block silently lets the agent through. Phase 5 of the machinery rewrite makes the scripts' own
`GUARDED_AGENT_NAMES` and `GATED_AGENT_NAMES` the single source and renders both copies from it;
the committed file is byte-checked exactly like the host adapters
(`docs/decisions/2026-09-13-machinery-rewrite.md`).

The shell text is a TEMPLATE, not a builder. It is the fleet's security boundary and the
most-reviewed code in the tree, so it stays readable verbatim in one place and only the two
roster expansions are computed. Substitution is by explicit placeholder rather than `str.format`,
because the templates legitimately contain `${CLAUDE_PLUGIN_ROOT}` and JSON braces a format call
would have to escape -- and an escaping mistake here is a silently disarmed hook.

This module renders; it never reads a roster itself. `fleet.snapshot` already reads the hook
scripts as data, and a second reader here would be the duplicate-parser failure the kernel exists
to end (`AGENTS.md`, "One parser per fact").
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import NamedTuple


class Roster(NamedTuple):
    """One hook script's subjects and the namespace it spells them under.

    Both fields come from that script's own module constants, read as data by
    `fleet.snapshot.read_rosters`; this module never opens a hook script itself.
    """

    names: frozenset[str]
    plugin_name: str


# The placeholders the two templates carry. Deliberately not `{}`-style: see the module docstring.
FAST_PATH = "@@FAST_PATH@@"
IDENTITY = "@@IDENTITY@@"

# Rendered from the committed hook file with the two roster expansions replaced by placeholders.
# Changing the shell semantics is a hook change and owes the probe, not only the tests
# (`AGENTS.md`, "Touching a Claude hook"). Each is ONE line and stays that way: the hook
# file holds the command as a single JSON string, and a wrapped source line would render
# bytes the committed file does not have. Hence the width waiver rather than a reflow.
GUARD_TEMPLATE = 'IN=$(cat); SQ=$(printf %s "$IN" | tr -d " \\t\\n\\r"); case "$IN" in @@FAST_PATH@@) ;; *) exit 0 ;; esac; G="${CLAUDE_PLUGIN_ROOT}/scripts/readonly-guard.py"; for C in python3 python py; do command -v "$C" >/dev/null 2>&1 || continue; OUT=$(printf \'%s\' "$IN" | "$C" -I -S "$G" 2>/dev/null); RC=$?; if [ "$RC" -eq 42 ]; then exit 0; fi; if [ "$RC" -eq 43 ]; then printf \'%s\' "$OUT"; exit 0; fi; done; case "$SQ" in @@IDENTITY@@) printf \'%s\' \'{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Read-only guard unavailable or failed: no interpreter answered with the guard\'"\'"\'s own exit code (tried python3, python, py), so the guard is missing, broken, or not really Python. Bash is denied for this read-only agent by default. Install Python 3, or reinstall the sde-agents plugin."}}\' ;; esac; exit 0'  # noqa: E501

GATE_TEMPLATE = 'IN=$(cat); SQ=$(printf %s "$IN" | tr -d " \\t\\n\\r"); case "$IN" in @@FAST_PATH@@) ;; *) exit 0 ;; esac; case "${SDE_AGENTS_LIVE_EFFECT_POLICY-host}" in host) exit 0 ;; esac; G="${CLAUDE_PLUGIN_ROOT}/scripts/live-effect-gate.py"; for C in python3 python py; do command -v "$C" >/dev/null 2>&1 || continue; OUT=$(printf \'%s\' "$IN" | "$C" -I -S "$G" 2>/dev/null); RC=$?; if [ "$RC" -eq 42 ]; then exit 0; fi; if [ "$RC" -eq 43 ] || [ "$RC" -eq 45 ]; then printf \'%s\' "$OUT"; exit 0; fi; done; case "$SQ" in @@IDENTITY@@) case "$IN" in *bypassPermissions*|*dontAsk*|*\'"permission_mode":"auto"\'*|*\'"permission_mode": "auto"\'*) printf \'%s\' \'{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"sde-agents live-effect gate unavailable or failed, and this session suppresses prompts: no interpreter answered with the gate\'"\'"\'s own exit codes (tried python3, python, py). Hand the exact command to the operator until Python 3 or the plugin is repaired."}}\' ;; *) printf \'%s\' \'{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"sde-agents live-effect gate unavailable or failed: no interpreter answered with the gate\'"\'"\'s own exit codes (tried python3, python, py). Every Bash call from homelab-engineer asks until Python 3 or the plugin is repaired."}}\' ;; esac ;; esac; exit 0'  # noqa: E501


def fast_path_pattern(names: Iterable[str]) -> str:
    """The `case "$IN"` alternation: a cheap substring filter over the raw payload.

    Bare names only. This block decides whether the interpreter is launched at all, so it is
    deliberately LOOSER than the identity fallback -- a payload naming the agent in any spelling
    reaches the script, which then makes the real decision from `agent_type`.
    """
    return "|".join(f"*{name}*" for name in sorted(names))


def identity_pattern(names: Iterable[str], plugin_name: str) -> str:
    """The `case "$SQ"` alternation: the exact `agent_type` spellings, namespaced and bare.

    This is what fails closed when no interpreter answered, so it matches the identity rather
    than any mention of it -- a main-session command that merely names a guarded agent must not
    be denied. `$SQ` is the whitespace-stripped payload, so JSON spacing cannot decide whether
    the fallback fires.
    """
    return "|".join(
        f"""*'"agent_type":"{plugin_name}:{name}"'*|*'"agent_type":"{name}"'*"""
        for name in sorted(names)
    )


def render(template: str, names: Iterable[str], plugin_name: str) -> str:
    """One hook command, with both roster copies rendered from the same set of names."""
    names = list(names)
    if not names:
        # An empty roster would render `case "$IN" in ) ;;` -- a shell syntax error that the
        # runtime swallows, leaving the hook exiting non-zero on every Bash call. Refusing is the
        # only answer that cannot be mistaken for an armed hook.
        raise ValueError("a hook roster cannot be empty; the rendered `case` would not parse")
    return template.replace(FAST_PATH, fast_path_pattern(names), 1).replace(
        IDENTITY, identity_pattern(names, plugin_name), 1
    )


def hooks_document(guard: Roster, gate: Roster) -> dict[str, object]:
    """The whole `hooks.json` document: both hooks on one `PreToolUse`/`Bash` matcher.

    One matcher with two entries, not two matchers: the guard and the gate scope to disjoint
    rosters and each exits 0 for everyone else, so they compose on the same Bash event.

    Each hook is rendered with ITS OWN script's `PLUGIN_NAME`, not one shared value. The two must
    agree with the manifest -- `plugin.guard` and `plugin.gate` say so -- but the namespaced
    `agent_type` a hook matches is the one its own script builds, so rendering the gate's
    identity block from the guard's namespace would be a silent disagreement this file cannot
    show.
    """
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": render(GUARD_TEMPLATE, guard.names, guard.plugin_name),
                        },
                        {
                            "type": "command",
                            "command": render(GATE_TEMPLATE, gate.names, gate.plugin_name),
                        },
                    ],
                }
            ]
        }
    }


def hooks_json(guard: Roster, gate: Roster) -> bytes:
    """The document as the committed file's exact bytes: `indent=2` and a trailing newline."""
    return (json.dumps(hooks_document(guard, gate), indent=2) + "\n").encode("utf-8")
