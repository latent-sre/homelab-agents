from __future__ import annotations

import unittest
import json
from pathlib import Path

from tests.validate_fleet_wiring_support import PluginWiringMixin, READONLY_BASH_AGENT, _add_guarded_name


class PluginWiringGuardTests(PluginWiringMixin, unittest.TestCase):
    def test_dangling_namespace_reference_is_reported(self) -> None:
        # The corpus carries hundreds of `sde-agents:<name>` cross-references and nothing at
        # runtime resolves one: a renamed or deleted member leaves pointers that pass every gate
        # while routing quietly degrades. Mutation, not a fixture, because the invariant is about
        # the real repo's densely linked graph.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\nEscalate fan-out design to `sde-agents:ghost-skill`.\n",
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("sde-agents:ghost-skill" in i for i in issues), issues)

    def test_malformed_namespace_reference_is_reported_as_the_complete_token(self) -> None:
        # A prefix-only regex used to accept code-reviewer_v2 as the live code-reviewer target and
        # skipped uppercase targets entirely. Each mutation introduces one malformed reference.
        for target in ("code-reviewer_v2", "Code-Reviewer", "code--reviewer"):
            with self.subTest(target=target):

                def mutate(repo: Path, target: str = target) -> None:
                    path = repo / "agents" / "researcher.md"
                    path.write_text(
                        path.read_text(encoding="utf-8")
                        + f"\nEscalate to `sde-agents:{target}`.\n",
                        encoding="utf-8",
                    )

                issues = self._issues_after(mutate)
                self.assertTrue(
                    any(
                        f"sde-agents:{target}" in issue
                        and "malformed namespaced reference" in issue
                        for issue in issues
                    ),
                    issues,
                )

    def test_slash_command_reference_must_target_a_skill(self) -> None:
        # code-reviewer is a real fleet member, but it is an agent and therefore cannot resolve
        # through slash-command syntax. Union membership must not certify the invocation.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\nRun `/sde-agents:code-reviewer` before continuing.\n",
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "/sde-agents:code-reviewer" in issue
                and "slash-command reference" in issue
                and "must target a skill" in issue
                for issue in issues
            ),
            issues,
        )

    def test_missing_hook_registration_is_reported(self) -> None:
        issues = self._issues_after(lambda r: (r / "hooks" / "hooks.json").unlink())
        self.assertTrue(any("ONLY place the read-only guard" in i for i in issues), issues)

    def test_hook_that_does_not_use_the_plugin_root_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "hooks" / "hooks.json"
            path.write_text(
                path.read_text(encoding="utf-8").replace("${CLAUDE_PLUGIN_ROOT}", "$HOME/.claude"),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("CLAUDE_PLUGIN_ROOT" in i for i in issues), issues)

    def test_guarded_agent_missing_from_the_hook_string_is_reported(self) -> None:
        # The hook filters on the agent name before it ever runs the guard, so the roster lives in
        # TWO places. Simulate adding another guarded agent to the guard alone: the hook's
        # fast-path would exit 0 for it, leaving it unguarded while every file claims otherwise.
        # `sde-fullstack` is a real agent, so this isolates the hook-sync rule from the
        # does-this-agent-exist rule above.
        def mutate(repo: Path) -> None:
            _add_guarded_name(repo, "sde-fullstack")

        issues = self._issues_after(mutate)
        self.assertTrue(any("never names 'sde-fullstack'" in i for i in issues), issues)

    def test_name_present_in_only_one_hook_roster_is_reported(self) -> None:
        # REGRESSION (review-reported, reproduced): the hook holds TWO rosters — the `case`
        # fast-path that decides whether the guard runs at all, and the no-interpreter fallback
        # that fails closed. Searching the whole command string passed when a name sat in one
        # block and was missing from the other, which is the silent-disarm this rule exists to
        # prevent. Each direction is pinned separately.
        def drop_from_fast_path(repo: Path) -> None:
            path = repo / "hooks" / "hooks.json"
            doc = json.loads(path.read_text(encoding="utf-8"))
            hook = doc["hooks"]["PreToolUse"][0]["hooks"][0]
            hook["command"] = hook["command"].replace("|*principal-engineer*", "", 1)
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

        issues = self._issues_after(drop_from_fast_path)
        self.assertTrue(
            any("fast-path filter" in i and "principal-engineer" in i for i in issues), issues
        )

        def drop_from_fallback(repo: Path) -> None:
            path = repo / "hooks" / "hooks.json"
            doc = json.loads(path.read_text(encoding="utf-8"))
            hook = doc["hooks"]["PreToolUse"][0]["hooks"][0]
            command = hook["command"]
            # Remove only the fallback's agent_type patterns for this agent, leaving the fast-path.
            for form in ("sde-agents:principal-engineer", "principal-engineer"):
                command = command.replace(f"""|*'"agent_type":"{form}"'*""", "")
                command = command.replace(f"""|*'"agent_type": "{form}"'*""", "")
            hook["command"] = command
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

        issues = self._issues_after(drop_from_fallback)
        self.assertTrue(
            any("no-interpreter fallback" in i and "principal-engineer" in i for i in issues), issues
        )

    def test_unrecognized_hook_shape_fails_rather_than_passing(self) -> None:
        # If the hook is ever restructured away from two `case` blocks, the roster cross-check
        # cannot verify it — and must say so instead of quietly reporting no issues.
        def mutate(repo: Path) -> None:
            path = repo / "hooks" / "hooks.json"
            doc = json.loads(path.read_text(encoding="utf-8"))
            hook = doc["hooks"]["PreToolUse"][0]["hooks"][0]
            hook["command"] = hook["command"].replace('case "$IN" in', "if false; then", 1)
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("does not recognize" in i for i in issues), issues)

    def test_plugin_name_mismatch_is_reported(self) -> None:
        # The guard matches a NAMESPACED agent_type. Rename the plugin and it matches nobody.
        def mutate(repo: Path) -> None:
            path = repo / ".claude-plugin" / "plugin.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["name"] = "renamed-fleet"
            path.write_text(json.dumps(manifest), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("silently guards nothing" in i for i in issues), issues)

    def test_missing_author_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / ".claude-plugin" / "plugin.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            del manifest["author"]
            path.write_text(json.dumps(manifest), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("--strict" in i for i in issues), issues)

    def test_unguarded_readonly_bash_agent_is_reported(self) -> None:
        # Add a new read-only agent that holds Bash and forget to register it with the guard --
        # the exact way a future agent would arrive unguarded while every test stayed green.
        issues = self._issues_after(
            lambda r: (r / "agents" / "auditor.md").write_text(READONLY_BASH_AGENT, encoding="utf-8")
        )
        self.assertTrue(
            any("'read-only' is a promise, not a control" in i for i in issues), issues
        )

    def test_guarding_an_agent_that_does_not_exist_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            _add_guarded_name(repo, "ghost")

        issues = self._issues_after(mutate)
        self.assertTrue(any("'ghost'" in i and "not an agent" in i for i in issues), issues)


class PluginWiringGateTests(PluginWiringMixin, unittest.TestCase):
    """The live-effect gate has exactly one place to live, like the guard; drift is silent."""

    def _hooks(self, repo: Path) -> dict:
        return json.loads((repo / "hooks" / "hooks.json").read_text(encoding="utf-8"))

    def test_missing_gate_entry_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            config = self._hooks(repo)
            for entry in config["hooks"]["PreToolUse"]:
                entry["hooks"] = [h for h in entry["hooks"] if "live-effect-gate.py" not in h.get("command", "")]
            (repo / "hooks" / "hooks.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("live-effect-gate.py" in i for i in issues), issues)

    def test_gated_name_missing_from_the_hook_rosters_is_reported(self) -> None:
        # REGRESSION (review-reported, reproduced): the gate's documented growth path is "the
        # roster grows by recurrence" -- an incident adds one name to GATED_AGENT_NAMES. Doing
        # exactly that left the validator GREEN while the hook's `*homelab-engineer*` prefilter
        # exited before the gate ran for the new name, so the addition gated nothing, silently.
        # The guard already cross-checks both of its roster blocks; the gate did not check either.
        def add_unwired_name(repo: Path) -> None:
            path = repo / "scripts" / "live-effect-gate.py"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace('GATED_AGENT_NAMES = frozenset({"homelab-engineer"})',
                             'GATED_AGENT_NAMES = frozenset({"homelab-engineer", "sde-fullstack"})'),
                encoding="utf-8", newline="\n")

        issues = self._issues_after(add_unwired_name)
        self.assertTrue(
            any("sde-fullstack" in i and "fast-path" in i for i in issues), issues
        )
        self.assertTrue(
            any("sde-fullstack" in i and "fallback" in i for i in issues), issues
        )

    def test_gate_not_resolved_through_plugin_root_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            config = self._hooks(repo)
            for entry in config["hooks"]["PreToolUse"]:
                for hook in entry["hooks"]:
                    if "live-effect-gate.py" in hook.get("command", ""):
                        hook["command"] = hook["command"].replace("${CLAUDE_PLUGIN_ROOT}/", "./")
            (repo / "hooks" / "hooks.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("live-effect-gate.py" in i and "CLAUDE_PLUGIN_ROOT" in i for i in issues), issues)

    def test_gated_agent_must_exist_and_hold_bash(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "scripts" / "live-effect-gate.py"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    'GATED_AGENT_NAMES = frozenset({"homelab-engineer"})',
                    'GATED_AGENT_NAMES = frozenset({"homelab-engineer", "ghost-agent"})',
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("ghost-agent" in i for i in issues), issues)

    def test_gate_plugin_name_must_match_the_manifest(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "scripts" / "live-effect-gate.py"
            path.write_text(
                path.read_text(encoding="utf-8").replace('PLUGIN_NAME = "sde-agents"', 'PLUGIN_NAME = "sde-agent"'),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("live-effect-gate.py" in i and "PLUGIN_NAME" in i for i in issues), issues)

    def test_guarded_and_gated_rosters_must_be_disjoint(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "scripts" / "live-effect-gate.py"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    'GATED_AGENT_NAMES = frozenset({"homelab-engineer"})',
                    'GATED_AGENT_NAMES = frozenset({"homelab-engineer", "code-reviewer"})',
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("code-reviewer" in i and "both" in i for i in issues), issues)


if __name__ == "__main__":
    unittest.main()
