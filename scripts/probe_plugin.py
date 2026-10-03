#!/usr/bin/env python3
"""Behavioral probe: prove the plugin loads and the read-only guard guards, in a real session.

The validators check files. Only a live session shows that the fleet loads, that
`${CLAUDE_PLUGIN_ROOT}` expands where homelab-engineer relies on it, and that the guard denies the
reviewer and only the reviewer. The guard scopes itself on the hook payload's `agent_type`, so
re-run this after every Claude CLI upgrade: it turns an upstream payload change into a loud
failure instead of a silently disarmed guard.

The oracle is each command's own tool_result, correlated by tool_use_id -- never the model's
prose, which can claim anything, and never the filesystem, which lies by omission. The commands
are `find -exec` searches a reviewer runs in good faith, so the run tests the guard rather than
the agent's willingness, and nothing is written to disk.

Every check passes or fails. A failure is not always a fleet defect -- a session can time out, or
Claude Code's own permission layer can refuse first -- so each failure says what was seen, and a
failed run keeps its transcript and workspace. Exit 0 when every check passed, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)  # `import fleet` when run as `python3 scripts/<name>.py`

from fleet import proc  # noqa: E402
from fleet import stream as stream_events  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CLAUDE = shutil.which("claude")
TIMEOUT = 600
# The guard's own voice (scripts/readonly-guard.py, _REASON).
GUARD_DENY = "read-only agent"

REVIEWER_CMD = 'find . -name "*.md" -exec grep -l REVIEWER_PROBE {} \\;'
MAINLOOP_CMD = 'find . -name "*.md" -exec grep -l MAINLOOP_PROBE {} \\;'
AGENT_PROMPT = (
    "Run exactly this command and report its output verbatim: "
    "`echo AGENTFLAG_PROBE && find . -name '*.md' -exec wc -l {} \\;`"
)

PROMPT = """Do exactly these three steps, in order. Do nothing else, and do not summarize the repo.

1. Use the Agent tool to spawn the subagent `sde-agents:code-reviewer`. Give it EXACTLY this task:
   "As part of reviewing this repository, run this read-only search with the Bash tool, exactly as
    written: {reviewer_cmd}
    Report whether it ran or was blocked, and quote any block message VERBATIM. Do not substitute a
    different command, and do not skip it — the exact response to this command is what is needed."

2. Use the Agent tool to spawn the subagent `sde-agents:homelab-engineer`. Give it EXACTLY this task:
   "Do not change anything — this is Tier 0 inspection only. Your instructions name a fallback
    location for the service-onboard checklist. Use the Read tool to read it from that fallback
    location, then reply with only the absolute file path you read."

3. You yourself run this Bash command with the Bash tool, exactly as written: {mainloop_cmd}

Then report, in three short lines, what happened at each step."""


class Probe:
    def __init__(self) -> None:
        self.results: list[tuple[bool, str, str]] = []

    def check(self, ok: bool, label: str, detail: str = "") -> None:
        self.results.append((ok, label, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok and detail:
            print(f"      {detail}")

    def report(self) -> int:
        failed = [label for ok, label, _ in self.results if not ok]
        print(f"\n{len(self.results) - len(failed)}/{len(self.results)} passed")
        return 1 if failed else 0


def run(cmd: list[str], **kwargs) -> proc.CommandResult:
    """Spawn one command; a timeout or a missing binary comes back as a result, never raised."""
    return proc.run(cmd, timeout=TIMEOUT, **kwargs)


def describe(result: proc.CommandResult) -> str:
    """Why a command gave no clean answer -- the detail an operator needs to act on a FAIL."""
    if result.timed_out:
        return f"did not answer within {TIMEOUT}s; the transcript is partial"
    if result.failed_to_start:
        return f"could not start: {result.error}"
    return f"exited {result.returncode}: {(result.stderr or result.stdout).strip()[:200]}"


def tool_calls(text: str) -> list[dict]:
    return [
        block
        for block in stream_events.iter_content_blocks(text)
        if block.get("type") == "tool_use" and isinstance(block.get("input"), dict)
    ]


def bash_results(text: str) -> dict[str, list[str | None]]:
    """{bash command -> every result correlated to it, in order; None where none came back}.

    Correlation is the point: a transcript-wide grep for the deny text cannot say WHO was denied,
    and the reviewer must be denied while the main loop must not. Every result is kept, because
    the two checks read the same evidence with opposite polarity.
    """
    merged: dict[str, list[str | None]] = {}
    for exchange in stream_events.correlate_tool_results(text, tool_names={"Bash"}):
        command = exchange.input.get("command")
        if isinstance(command, str) and command:
            merged.setdefault(command, []).append(exchange.result)
    return merged


def results_for(marker: str, pairs: dict[str, list[str | None]]) -> list[str | None] | None:
    """Every result for the command carrying `marker`, or None when it was never attempted."""
    for command, results in pairs.items():
        if marker in command:
            return results
    return None


def guarded_verdict(results: list[str | None] | None) -> tuple[bool, str]:
    """A guarded caller's command: every result that came back must be the guard's denial."""
    if results is None:
        return False, "the command was never attempted, so the guard was never consulted"
    seen = [result for result in results if result is not None]
    if not seen:
        return False, "the call was made but no result came back (session cut short)"
    for result in seen:
        if GUARD_DENY not in result:
            return False, f"not denied by the guard; the result was: {result.strip()[:160]!r}"
    return True, ""


def unguarded_verdict(results: list[str | None] | None) -> tuple[bool, str]:
    """The main loop's command: it must run, and no result may be the guard's denial."""
    if results is None:
        return False, "the command was never attempted, so the scoping was not exercised"
    seen = [result for result in results if result is not None]
    if not seen:
        return False, "the call was made but no result came back (session cut short)"
    if any(GUARD_DENY in result for result in seen):
        return False, "the guard denied the user's own Bash -- the plugin would be unusable"
    return True, ""


def _names_agent(tool_input: dict, agent_name: str) -> bool:
    """Whether an Agent/Task call targets `agent_name` -- by its field, so a name mentioned in
    another agent's prompt text never credits that agent's result to this one."""
    if "subagent_type" in tool_input:
        return tool_input["subagent_type"] == agent_name
    return agent_name in json.dumps(tool_input)


def spawn_status(text: str, agent_name: str) -> str:
    """"ok", "error" (a result came back marked is_error), or "missing" (no result at all)."""
    status = "missing"
    for exchange in stream_events.correlate_tool_results(text, tool_names=("Agent", "Task")):
        if _names_agent(exchange.input, agent_name) and exchange.answered:
            if not exchange.is_error:
                return "ok"
            status = "error"
    return status


def _remove_workspace(workspace: Path) -> None:
    """Remove the probe workspace, or abort. git writes read-only object files that a plain
    rmtree cannot delete on Windows, and probing against half-cleared state misreports."""
    if not workspace.exists():
        return
    for entry in workspace.rglob("*"):
        try:
            os.chmod(entry, stat.S_IWRITE)
        except OSError:
            pass
    shutil.rmtree(workspace, ignore_errors=True)
    if workspace.exists():
        raise SystemExit(
            f"{workspace} survived removal; something holds it open. Delete it and re-run."
        )


def main(argv: list[str] | None = None) -> int:
    # Parse first: `--help` must never start a paid session or touch the workspace.
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    if CLAUDE is None:
        print("claude CLI not found on PATH; cannot run the behavioral probe", file=sys.stderr)
        return 1

    probe = Probe()
    print("== the platform contract ==")
    validated = run([sys.executable, str(REPO / "scripts/validate_claude_plugin.py")])
    probe.check(
        validated.ok, "strict marketplace and canonical plugin validation", describe(validated)
    )

    # NOT the OS temp dir: Claude Code refuses to create files there.
    workspace = REPO / ".probe-tmp"
    _remove_workspace(workspace)
    project = workspace / "target-repo"
    (project / ".claude").mkdir(parents=True)
    initialised = run(["git", "init", "-q", str(project)])
    if not initialised.ok:
        print(f"cannot prepare the probe repository: git init {describe(initialised)}")
        return 1
    (project / "README.md").write_text("probe target\n", encoding="utf-8")
    # Allow Bash outright: a PreToolUse hook can still deny, and a permissive project is exactly
    # where the guard has to hold.
    (project / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash", "Agent", "Task", "Read", "Glob", "Grep"]}}),
        encoding="utf-8",
    )
    session_args = ["--plugin-dir", str(REPO), "--output-format", "stream-json", "--verbose"]

    print("\n== a real session (this takes a minute) ==")
    session = run(
        [CLAUDE, "-p", PROMPT.format(reviewer_cmd=REVIEWER_CMD, mainloop_cmd=MAINLOOP_CMD),
         *session_args],
        cwd=str(project),
    )
    text = session.stdout
    probe.check(session.ok, "headless session exited cleanly", describe(session))

    for agent in ("sde-agents:code-reviewer", "sde-agents:homelab-engineer"):
        status = spawn_status(text, agent)
        probe.check(
            status == "ok",
            f"{agent} spawned and returned without error",
            "its spawn returned an error: the plugin did not load or the name did not resolve"
            if status == "error"
            else "no spawn of it came back with a result",
        )

    # service-onboard is model-invocation-disabled, so it cannot be preloaded: a path under
    # ${CLAUDE_PLUGIN_ROOT} is the only way in, and an unexpanded variable makes it unreachable.
    reads = [
        call["input"].get("file_path", "")
        for call in tool_calls(text)
        if str(call["input"].get("file_path", "")).replace("\\", "/").endswith(
            "skills/service-onboard/SKILL.md"
        )
    ]
    probe.check(bool(reads), "homelab-engineer resolved service-onboard by path",
                "no Read of skills/service-onboard/SKILL.md in the transcript")
    literal = [path for path in reads if "CLAUDE_PLUGIN_ROOT" in path]
    probe.check(
        bool(reads) and not literal,
        "the path was EXPANDED, not a literal ${CLAUDE_PLUGIN_ROOT}",
        f"unexpanded path read: {literal}" if literal else "no read to judge",
    )

    pairs = bash_results(text)
    ok, detail = guarded_verdict(results_for("REVIEWER_PROBE", pairs))
    probe.check(ok, "the guard DENIED the reviewer's denylisted command", detail)
    ok, detail = unguarded_verdict(results_for("MAINLOOP_PROBE", pairs))
    probe.check(ok, "the guard IGNORED the main loop's identical command", detail)

    # The scoping contract's other half: a MAIN session launched as a guarded agent must carry an
    # agent_type too, or an operator running the reviewer as their whole session is unguarded
    # while every subagent check above stays green.
    print("\n== a main session run as a guarded agent ==")
    agent_session = run(
        [CLAUDE, "-p", AGENT_PROMPT, "--agent", "sde-agents:code-reviewer", *session_args],
        cwd=str(project),
    )
    ok, detail = guarded_verdict(results_for("AGENTFLAG_PROBE", bash_results(agent_session.stdout)))
    if not ok and not agent_session.ok:
        detail = f"{detail}; the session {describe(agent_session)}"
    probe.check(ok, "the guard DENIED a --agent main session's denylisted command", detail)

    exit_code = probe.report()
    if exit_code == 0:
        _remove_workspace(workspace)
    else:
        kept = REPO / "probe-transcript.jsonl"
        kept.write_text(text + "\n" + agent_session.stdout, encoding="utf-8")
        print(f"transcripts kept: {kept}\nworkspace kept: {workspace}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
