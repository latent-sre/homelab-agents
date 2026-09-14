from __future__ import annotations

import unittest
from pathlib import Path

from tests.validate_fleet_wiring_support import PluginWiringMixin


class PluginWiringDocsTests(PluginWiringMixin, unittest.TestCase):
    def test_bare_cross_reference_in_a_description_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "code-reviewer.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "use sde-agents:lab-audit", "use lab-audit"
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("without the plugin namespace" in i for i in issues), issues)

    def test_bare_cross_reference_in_a_folded_description_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "code-reviewer.md"
            text = path.read_text(encoding="utf-8")
            start = text.index("description:")
            end = text.index("\ntools:", start)
            path.write_text(
                text[:start]
                + "description: >\n  Use lab-audit for a whole home-lab.\n"
                + text[end + 1:],
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("without the plugin namespace" in i for i in issues), issues)

    def test_home_claude_skill_path_is_reported(self) -> None:
        # The fleet-breaker: ~/.claude/skills does NOT hold this fleet once it ships as a plugin,
        # and `service-onboard` (model-invocation-disabled) is reachable ONLY by path -- so a stale
        # path here silently removes a capability rather than erroring.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "homelab-engineer.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "${CLAUDE_PLUGIN_ROOT}/skills/service-onboard/SKILL.md",
                    "~/.claude/skills/service-onboard/SKILL.md",
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("will NOT contain this fleet" in i for i in issues), issues)

    def test_orphaned_reference_file_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            (repo / "skills" / "backend-craft" / "references" / "caching.md").write_text(
                "# Caching\n\nNever linked from SKILL.md.\n", encoding="utf-8"
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any("orphaned" in i and "caching.md" in i for i in issues), issues
        )

    def test_claude_md_without_the_import_is_reported(self) -> None:
        # Claude Code reads CLAUDE.md, not AGENTS.md. Lose the one-line import and the guide is
        # orphaned -- still in the repo, never in any session, and nothing errors.
        def mutate(repo: Path) -> None:
            (repo / "CLAUDE.md").write_text("# project notes, no import\n", encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("never loaded" in i for i in issues), issues)

    def test_missing_claude_md_bridge_is_reported(self) -> None:
        issues = self._issues_after(lambda r: (r / "CLAUDE.md").unlink())
        self.assertTrue(any("never loaded" in i for i in issues), issues)

    def test_dangling_import_without_agents_md_is_reported(self) -> None:
        issues = self._issues_after(lambda r: (r / "AGENTS.md").unlink())
        self.assertTrue(any("resolves to nothing" in i for i in issues), issues)

    def test_stale_path_in_the_guide_is_reported(self) -> None:
        # The rename-a-script case: the guide keeps naming the old path, and only a reader who
        # tries the command ever finds out.
        def mutate(repo: Path) -> None:
            path = repo / "AGENTS.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "scripts/probe_plugin.py", "scripts/probe_plugins.py"
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("'scripts/probe_plugins.py'" in i for i in issues), issues)

    def test_stale_path_in_the_program_doc_is_reported(self) -> None:
        # The program map exists so the engineering program's documentation cannot go stale, which
        # makes it the one document least entitled to stale paths of its own — same
        # rename-a-script failure as the guide, same tripwire.
        def mutate(repo: Path) -> None:
            path = repo / "docs" / "engineering-program.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "scripts/live-effect-gate.py", "scripts/live-effect-gates.py"
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("'scripts/live-effect-gates.py'" in i for i in issues), issues)

    def test_program_doc_is_validated_without_the_guide(self) -> None:
        # PR #133 P2: the map's own header advertises this tripwire, so a check that deleting an
        # UNRELATED file disarms is enforcement prose with no guard behind it -- the exact defect
        # class the validator exists to catch. The no-guide early return must not swallow the
        # program map's stale paths.
        def mutate(repo: Path) -> None:
            (repo / "AGENTS.md").unlink()
            (repo / "CLAUDE.md").unlink()
            path = repo / "docs" / "engineering-program.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "scripts/live-effect-gate.py", "scripts/live-effect-gates.py"
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("'scripts/live-effect-gates.py'" in i for i in issues), issues)

    def test_repo_without_the_program_doc_is_valid(self) -> None:
        # Self-gating, like the guide: a repo that carries no program map makes no map claims.
        # AGENTS.md names the map as a path, so that mention leaves with it — otherwise the
        # guide's own stale-path check correctly fires on the dangling reference.
        def mutate(repo: Path) -> None:
            (repo / "docs" / "engineering-program.md").unlink()
            guide = repo / "AGENTS.md"
            guide.write_text(
                guide.read_text(encoding="utf-8").replace(
                    "docs/engineering-program.md", "docs"
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertEqual([], issues)

    def test_alias_drift_in_the_guide_is_reported(self) -> None:
        # Add an alias to ALIAS_MODELS (or drop one) and the guide's paraphrase must follow.
        def mutate(repo: Path) -> None:
            path = repo / "AGENTS.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace("`fable`", "`fable-classic`"),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("omits `fable`" in i for i in issues), issues)

    def test_repo_with_no_guide_at_all_is_valid(self) -> None:
        # The check is self-gating: a repo that makes no guide claims has nothing to drift.
        def mutate(repo: Path) -> None:
            (repo / "AGENTS.md").unlink()
            (repo / "CLAUDE.md").unlink()

        issues = self._issues_after(mutate)
        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
