from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.validate_fleet_wiring_support import (
    READONLY_BASH_AGENT,
    PluginWiringMixin,
    _add_guarded_name,
)


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
            lambda r: (r / "agents" / "auditor.md").write_text(
                READONLY_BASH_AGENT, encoding="utf-8"
            )
        )
        self.assertTrue(
            any("'read-only' is a promise, not a control" in i for i in issues), issues
        )

    def test_guarding_an_agent_that_does_not_exist_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            _add_guarded_name(repo, "ghost")

        issues = self._issues_after(mutate)
        self.assertTrue(any("'ghost'" in i and "not an agent" in i for i in issues), issues)


if __name__ == "__main__":
    unittest.main()
