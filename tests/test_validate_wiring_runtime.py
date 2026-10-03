from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.validate_fleet_wiring_support import PluginWiringMixin


class PluginWiringRuntimeTests(PluginWiringMixin, unittest.TestCase):
    def test_codex_interface_contract_cannot_silently_disappear(self) -> None:
        # Codex accepts the nested plugin only when its presentation contract is complete. A
        # malformed marketplace card otherwise fails at install time outside this repo's CI.
        def mutate(repo: Path) -> None:
            path = (
                repo
                / "plugins"
                / "sde-agents"
                / ".codex-plugin"
                / "plugin.json"
            )
            manifest = json.loads(path.read_text(encoding="utf-8"))
            del manifest["interface"]
            path.write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )

        issues = self._issues_after(mutate, check_adapters=True)
        self.assertTrue(
            any(
                "Codex manifest interface" in issue
                and "required presentation fields" in issue
                for issue in issues
            ),
            issues,
        )

    def test_codex_marketplace_policy_cannot_silently_disappear(self) -> None:
        # The repo-local marketplace is the Codex install entry point, not decorative metadata.
        # Its required policy and category must fail here instead of during a user's installation.
        def mutate(repo: Path) -> None:
            path = repo / ".agents" / "plugins" / "marketplace.json"
            marketplace = json.loads(path.read_text(encoding="utf-8"))
            del marketplace["plugins"][0]["policy"]
            path.write_text(
                json.dumps(marketplace, indent=2) + "\n",
                encoding="utf-8",
            )

        issues = self._issues_after(mutate, check_adapters=True)
        self.assertTrue(
            any(
                "Codex marketplace entry requires installation policy" in issue
                for issue in issues
            ),
            issues,
        )

    def test_evidence_agent_cannot_silently_lose_its_mcp_authority(self) -> None:
        # Both evidence agents used to promise Context7/GitHits while their tools allowlist removed
        # every MCP tool. Mutation is the right test because the invariant binds a real role's
        # method to its real frontmatter rather than defining a synthetic "researcher" fixture.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "  - mcp__plugin_githits_githits__pkg_info\n", ""
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "evidence role 'researcher' is missing required tools" in issue
                and "pkg_info" in issue
                for issue in issues
            ),
            issues,
        )

    def test_investigation_roles_cannot_collapse_the_local_external_boundary(self) -> None:
        mutations = (
            ("researcher", "  - Read\n"),
            ("repository-investigator", "  - WebFetch\n"),
            ("application-security-auditor", "  - WebSearch\n"),
        )
        for name, tool_line in mutations:
            with self.subTest(agent=name):

                def mutate(repo: Path, name: str = name, tool_line: str = tool_line) -> None:
                    path = repo / "agents" / f"{name}.md"
                    text = path.read_text(encoding="utf-8")
                    path.write_text(
                        text.replace("tools:\n", "tools:\n" + tool_line, 1),
                        encoding="utf-8",
                    )

                issues = self._issues_after(mutate)
                self.assertTrue(
                    any(
                        f"trust-separated role '{name}' holds forbidden tools" in issue
                        for issue in issues
                    ),
                    issues,
                )


if __name__ == "__main__":
    unittest.main()
