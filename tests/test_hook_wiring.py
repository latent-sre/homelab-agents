"""End-to-end test of the read-only guard AS hooks/hooks.json DEFINES IT.

tests/test_readonly_guard.py tests the guard's decisions by invoking the script directly.
That is not the same thing as testing the hook: the hook is a shell command string in
hooks/hooks.json, and it is what Claude Code actually runs. These tests extract that string
and run it under `sh`, exactly as the runtime does.

Why the wiring moved here from the agent's frontmatter — the load-bearing fact:

    A plugin-shipped agent's `hooks:` frontmatter is SILENTLY IGNORED. ("For security reasons,
    `hooks`, `mcpServers`, and `permissionMode` are not supported for plugin-shipped agents" —
    code.claude.com/docs/en/plugins-reference.) Probed on CLI 2.1.200: a plugin agent's
    frontmatter hook never fired, while a byte-identical hook on a project-scope agent did.

This fleet ships as a plugin, so a guard on the agent would be armor that isn't there — the
reviewer would hold Bash with nothing watching it, and every test would still pass. The guard
therefore lives in hooks/hooks.json, which Claude Code registers SESSION-WIDE, and scopes itself
on the payload's `agent_type`. Two properties follow, and both are tested below because getting
either wrong is worse than having no guard at all:

  1. It must DENY state-changing Bash for the reviewer, and fail CLOSED when it cannot decide.
  2. It must NEVER touch anyone else — above all the user's own Bash in a plain main session,
     whose payload carries no `agent_type` key (an `--agent` session carries that agent's name;
     the scoping contract in scripts/readonly-guard.py's docstring is the owner).

The trust boundary also moved, and improved: the guard now runs from ${CLAUDE_PLUGIN_ROOT}, the
plugin's installed copy, which by construction is not inside the repository under review.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.support import REPO
HOOKS = REPO / "hooks" / "hooks.json"
AGENT = REPO / "agents" / "code-reviewer.md"
SH = shutil.which("sh")

REVIEWER = "sde-agents:code-reviewer"
PUSH = "git push --force origin main"
DIFF = "git diff HEAD~1"


def hook_command() -> str:
    """The PreToolUse command string, read from hooks/hooks.json itself.

    Walks the real `hooks -> PreToolUse -> matcher: Bash -> command` path rather than grepping
    for any `command` key. The structure IS the thing under test: a command string sitting at a
    path Claude Code never reads is not a wired hook, and that is precisely how the previous
    wiring died — the string was still in the agent file, perfectly valid, and completely inert.
    """
    config = json.loads(HOOKS.read_text(encoding="utf-8"))
    for entry in config["hooks"]["PreToolUse"]:
        if entry.get("matcher") == "Bash":
            for hook in entry["hooks"]:
                if hook.get("type") == "command" and hook.get("command"):
                    return hook["command"]
    raise RuntimeError(
        "hooks/hooks.json: no PreToolUse hook with matcher 'Bash' and a command. The read-only "
        "guard is wired through hooks->PreToolUse->matcher: Bash->command; a renamed or misnested "
        "key silently disarms it."
    )


def payload(command: str, agent_type: str | None = None) -> str:
    """A PreToolUse payload shaped like the real one (compact JSON, as observed on CLI 2.1.200).

    A plain main loop genuinely has NO `agent_type` key — it is not empty, it is absent — so
    `agent_type=None` omits it rather than sending a null. (An `--agent` session carries the
    agent's name; that lane is doc-sourced, PROBE-001.)
    """
    data: dict = {
        "hook_event_name": "PreToolUse",
        "session_id": "s-1",
        "cwd": str(REPO),
        "permission_mode": "default",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    if agent_type is not None:
        data["agent_id"] = "a-1"
        data["agent_type"] = agent_type
    return json.dumps(data)


def run_hook(
    pl: str,
    *,
    plugin_root: str = str(REPO),
    cwd: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run the hook exactly as Claude Code would: sh -c <command>, JSON on stdin."""
    # Inherit the real environment and override only what the hook resolves paths from.
    # (A stripped env breaks Windows: unset SystemDrive/SystemRoot make native calls
    # expand %SystemDrive% literally and scatter directories into the CWD.)
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=plugin_root)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [str(SH), "-c", hook_command()],
        input=pl,
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        timeout=60,
    )


def decision(stdout: str) -> str | None:
    if not stdout.strip():
        return None  # no decision -> Claude allows the command
    return json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]


def seed_target_guard(project: str) -> Path:
    """Plant a guard in the repository under review that leaves proof if it is ever executed."""
    marker = Path(project) / "target-guard-executed"
    target_guard = Path(project) / "scripts" / "readonly-guard.py"
    target_guard.parent.mkdir(parents=True)
    target_guard.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n",
        encoding="utf-8",
    )
    return marker


class AgentMustNotCarryAnInertHookTest(unittest.TestCase):
    def test_code_reviewer_has_no_frontmatter_hooks_key(self) -> None:
        # A `hooks:` block here is IGNORED for a plugin-shipped agent. Leaving one would read as
        # protection and provide none — the single most dangerous thing this file guards against.
        frontmatter = AGENT.read_text(encoding="utf-8").split("---", 2)[1]
        self.assertNotRegex(
            frontmatter,
            r"(?m)^hooks:",
            "agents/code-reviewer.md declares frontmatter 'hooks:', which Claude Code SILENTLY "
            "IGNORES for a plugin-shipped agent. The guard belongs in hooks/hooks.json.",
        )


@unittest.skipIf(SH is None, "POSIX sh unavailable")
class HookWiringTest(unittest.TestCase):
    def _run(self, pl: str, **kwargs) -> str:
        # A crashing hook prints nothing on stdout, and empty stdout is silently treated as
        # ALLOW -- exactly the failure mode this file exists to catch. Fail loudly instead.
        result = run_hook(pl, **kwargs)
        self.assertEqual(
            result.returncode, 0,
            f"hook exited {result.returncode}; stderr:\n{result.stderr}",
        )
        return result.stdout

    # --- the guarded agent -------------------------------------------------------------
    def test_denies_state_change_for_the_reviewer(self) -> None:
        self.assertEqual(decision(self._run(payload(PUSH, REVIEWER))), "deny")

    def test_allows_read_only_command_for_the_reviewer(self) -> None:
        self.assertIsNone(decision(self._run(payload(DIFF, REVIEWER))))

    def test_guards_the_bare_agent_name_too(self) -> None:
        # Project/user-scope installs report a bare `agent_type` (the --plugin-dir dev loop
        # reports the NAMESPACED form). The guard must not be sidestepped by hand-installing the
        # agent at a different scope.
        self.assertEqual(decision(self._run(payload(PUSH, "code-reviewer"))), "deny")

    # --- everyone else, above all the user ---------------------------------------------
    def test_main_loop_is_never_guarded(self) -> None:
        # A plain main loop carries NO agent_type. This is the property that makes a
        # session-wide hook safe to ship: get it wrong and the user cannot run git in their own
        # ordinary session. (An --agent session carries the agent's name — deliberate scoping,
        # owned by the guard docstring.)
        self.assertIsNone(decision(self._run(payload(PUSH))))

    def test_other_subagents_are_never_guarded(self) -> None:
        self.assertIsNone(decision(self._run(payload(PUSH, "sde-agents:sde-fullstack"))))

    def test_main_loop_command_that_merely_names_the_reviewer_is_allowed(self) -> None:
        # `tool_input.command` is user-controlled text. Scanning it for the agent's name would deny
        # an ordinary commit -- and this is the exact command someone editing this guard would run.
        self.assertIsNone(
            decision(self._run(payload('git commit -m "fix sde-agents:code-reviewer"')))
        )

    # --- malformed input: fail closed for the guarded, inert for everyone else (GOV-001) --
    def test_malformed_guarded_payload_fails_closed(self) -> None:
        # End to end: the guard cannot parse this, so it must answer with NEITHER sentinel; the
        # hook then reaches its raw agent_type match and denies. Before the fix the guard said
        # EXIT_ALLOW and the hook stopped listening one line earlier — the fallback that exists
        # for exactly this payload never ran.
        truncated = payload(PUSH, REVIEWER)[:-1]  # drop only the brace: identity survives intact
        self.assertIn(f'"agent_type": "{REVIEWER}"', truncated)
        self.assertEqual(decision(self._run(truncated)), "deny")

    def test_malformed_unguarded_payload_is_a_no_op(self) -> None:
        # The complementary half: malformed input whose agent_type names no guarded agent must
        # not brick unrelated work — even when a guarded NAME rides in user-controlled command
        # text, which is what gets it past the hook's cheap pre-filter in the first place.
        truncated = payload('echo "ask code-reviewer later"', "sde-agents:sde-fullstack")[:-1]
        self.assertIsNone(decision(self._run(truncated)))

    # --- failing closed, but only for the reviewer ---------------------------------------
    def test_fails_closed_for_the_reviewer_when_the_guard_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            out = self._run(payload(DIFF, REVIEWER), plugin_root=empty)
            self.assertEqual(decision(out), "deny")
            self.assertIn("guard unavailable", out)

    def test_missing_guard_does_not_break_the_main_session(self) -> None:
        # Fail-closed must never escalate into "the user cannot use Bash". A broken plugin install
        # degrades the reviewer; it must not brick the session.
        with tempfile.TemporaryDirectory() as empty:
            self.assertIsNone(decision(self._run(payload(PUSH), plugin_root=empty)))

    def test_broken_guard_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "scripts").mkdir()
            (Path(root) / "scripts" / "readonly-guard.py").write_text(
                "raise RuntimeError('broken guard')\n", encoding="utf-8"
            )
            out = self._run(payload(DIFF, REVIEWER), plugin_root=root)
            self.assertEqual(decision(out), "deny")

    # --- trust boundary: never execute code from the repository under review --------------
    def test_never_executes_a_guard_from_the_repository_under_review(self) -> None:
        with tempfile.TemporaryDirectory() as project:
            marker = seed_target_guard(project)
            out = self._run(payload(DIFF, REVIEWER), cwd=project)
            self.assertIsNone(decision(out))
            self.assertFalse(marker.exists(), "the target repository's guard was executed")

    def test_target_guard_is_not_used_even_when_the_plugin_copy_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as empty:
            marker = seed_target_guard(project)
            out = self._run(payload(DIFF, REVIEWER), plugin_root=empty, cwd=project)
            self.assertEqual(decision(out), "deny")
            self.assertFalse(marker.exists(), "the target repository's guard was executed")

    def test_poisoned_interpreter_cannot_disarm_the_guard(self) -> None:
        """A PATH-planted `python3` that exits 0 with empty stdout must not read as ALLOW.

        This is why the guard asserts its verdict with distinctive exit codes (EXIT_ALLOW /
        EXIT_DENY) instead of relying on "exit 0 + empty stdout". A stand-in interpreter cannot
        forge those, so the hook rejects it and moves on to a real Python.

        Honest boundary: the plugin has no install step, so no absolute interpreter can be pinned
        ahead of time and the shim IS executed once while the hook looks for a working Python.
        Whoever can write to PATH already has code execution; what must not happen -- and does not
        -- is that they thereby turn the guard off. `-I` additionally neutralizes PYTHONPATH and
        PYTHONHOME.
        """
        with tempfile.TemporaryDirectory() as project:
            poison_bin = Path(project) / "poison-bin"
            poison_bin.mkdir()
            shim = poison_bin / "python3"
            shim.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            shim.chmod(0o755)

            poison_imports = Path(project) / "poison-imports"
            poison_imports.mkdir()
            (poison_imports / "json.py").write_text("raise SystemExit(0)\n", encoding="utf-8")

            out = self._run(
                payload(PUSH, REVIEWER),
                cwd=project,
                extra_env={
                    "PATH": str(poison_bin) + os.pathsep + os.environ.get("PATH", ""),
                    "PYTHONHOME": str(poison_imports),
                    "PYTHONPATH": str(poison_imports),
                },
            )
            self.assertEqual(decision(out), "deny")


GATE_LIVE = "/usr/bin/docker compose -f /srv/media/docker-compose.yml up -d jellyfin"
GATE_READ = "docker compose -f /srv/media/docker-compose.yml ps"
HOMELAB = "sde-agents:homelab-engineer"


def gate_hook_command() -> str:
    """The live-effect gate's PreToolUse command string, found by the script it runs."""
    config = json.loads(HOOKS.read_text(encoding="utf-8"))
    for entry in config["hooks"]["PreToolUse"]:
        if entry.get("matcher") == "Bash":
            for hook in entry["hooks"]:
                if hook.get("type") == "command" and "live-effect-gate.py" in hook.get("command", ""):
                    return hook["command"]
    raise RuntimeError("hooks/hooks.json: no PreToolUse/Bash hook runs scripts/live-effect-gate.py")


def gate_payload(command: str, agent_type: str | None = HOMELAB, mode: str | None = "default") -> str:
    data: dict = {
        "hook_event_name": "PreToolUse",
        "session_id": "s-1",
        "cwd": str(REPO),
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    if mode is not None:
        data["permission_mode"] = mode
    if agent_type is not None:
        data["agent_id"] = "a-1"
        data["agent_type"] = agent_type
    return json.dumps(data)


class LiveEffectGateWiringTests(unittest.TestCase):
    """The gate AS hooks/hooks.json DEFINES IT, run under sh like the runtime does."""

    def _run(self, pl: str, **kwargs) -> str:
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=kwargs.pop("plugin_root", str(REPO)))
        policy = kwargs.pop("policy", "prompt")
        env.pop("SDE_AGENTS_LIVE_EFFECT_POLICY", None)
        if policy is not None:
            env["SDE_AGENTS_LIVE_EFFECT_POLICY"] = policy
        env.update(kwargs.pop("extra_env", {}) or {})
        return subprocess.run(
            [str(SH), "-c", gate_hook_command()], input=pl, capture_output=True, text=True,
            env=env, timeout=60,
        ).stdout

    def test_guard_and_gate_are_two_entries_on_the_same_matcher(self) -> None:
        self.assertNotEqual(hook_command(), gate_hook_command())
        self.assertIn("readonly-guard.py", hook_command())
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/scripts/live-effect-gate.py", gate_hook_command())

    def test_asks_for_a_live_verb_from_the_gated_agent(self) -> None:
        self.assertEqual("ask", decision(self._run(gate_payload(GATE_LIVE))))

    def test_host_policy_needs_no_gate_interpreter_or_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            for policy in (None, "host"):
                for mode in ("default", "dontAsk"):
                    with self.subTest(policy=policy, mode=mode):
                        self.assertEqual("", self._run(
                            gate_payload(GATE_LIVE, mode=mode), plugin_root=empty, policy=policy,
                        ))

    def test_invalid_policy_does_not_silently_allow_a_live_effect(self) -> None:
        self.assertEqual("deny", decision(self._run(gate_payload(GATE_LIVE), policy="promtp")))

    def test_invalid_policy_with_missing_gate_preserves_the_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            for policy in ("promtp", ""):
                for mode, expected in (("default", "ask"), ("dontAsk", "deny")):
                    with self.subTest(policy=policy, mode=mode):
                        self.assertEqual(expected, decision(self._run(
                            gate_payload(GATE_LIVE, mode=mode), policy=policy, plugin_root=empty,
                        )))

    def test_no_decision_for_a_reader_from_the_gated_agent(self) -> None:
        self.assertIsNone(decision(self._run(gate_payload(GATE_READ))))

    def test_main_loop_is_never_gated(self) -> None:
        self.assertIsNone(decision(self._run(gate_payload(GATE_LIVE, agent_type=None))))

    def test_other_subagents_are_never_gated(self) -> None:
        self.assertIsNone(decision(self._run(gate_payload(GATE_LIVE, "sde-agents:sde-fullstack"))))

    def test_main_loop_command_that_merely_names_the_agent_is_ignored(self) -> None:
        # The raw prefilter matches any payload mentioning homelab-engineer; the interpreter then
        # reads agent_type properly. A user editing agents/homelab-engineer.md must never be gated.
        pl = gate_payload("sed -n 1,5p agents/homelab-engineer.md && docker compose up -d", agent_type=None)
        self.assertIsNone(decision(self._run(pl)))

    def test_suppressed_mode_denies_with_the_gate_voice(self) -> None:
        out = self._run(gate_payload(GATE_LIVE, mode="bypassPermissions"))
        self.assertEqual("deny", decision(out))
        self.assertIn("live-effect gate", out)

    def test_gate_missing_asks_for_the_gated_agent_only(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            out = self._run(gate_payload(GATE_LIVE), plugin_root=empty)
            self.assertEqual("ask", decision(out))
            self.assertIn("gate unavailable", out)
            self.assertIsNone(decision(self._run(gate_payload(GATE_LIVE, agent_type=None), plugin_root=empty)))

    def test_gate_missing_denies_under_a_suppressed_mode(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            out = self._run(gate_payload(GATE_LIVE, mode="dontAsk"), plugin_root=empty)
            self.assertEqual("deny", decision(out))

    def test_gate_fallback_identity_survives_json_whitespace(self) -> None:
        # The fallback recognised only the compact and one-space serialisations, so a payload
        # Claude formatted with two spaces or a newline after the colon looked like an unrelated
        # caller and exited 0 — allowing the live command under dontAsk, which is precisely what
        # the fail-closed fallback exists to prevent. Insignificant JSON whitespace must not
        # decide whether the gate fires.
        with tempfile.TemporaryDirectory() as empty:
            compact = gate_payload(GATE_LIVE, mode="dontAsk")
            for spacing in ('"agent_type":  "', '"agent_type":\n    "', '"agent_type" : "'):
                spaced = compact.replace('"agent_type": "', spacing)
                self.assertNotEqual(compact, spaced, "the payload shape changed; fix the test")
                with self.subTest(spacing=spacing):
                    out = self._run(spaced, plugin_root=empty)
                    self.assertEqual("deny", decision(out), out)

    def test_broken_gate_falls_back_the_same_way(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "scripts").mkdir()
            (Path(root) / "scripts" / "live-effect-gate.py").write_text(
                "raise RuntimeError('broken gate')\n", encoding="utf-8"
            )
            self.assertEqual("ask", decision(self._run(gate_payload(GATE_LIVE), plugin_root=root)))

    def test_malformed_gated_payload_falls_back_to_ask(self) -> None:
        self.assertEqual("ask", decision(self._run(gate_payload(GATE_LIVE)[:-1])))

    def test_homelab_platform_has_no_frontmatter_hooks_key(self) -> None:
        text = (REPO / "agents" / "homelab-engineer.md").read_text(encoding="utf-8")
        self.assertNotIn("\nhooks:", text.split("\n---", 2)[1])


if __name__ == "__main__":
    unittest.main()
