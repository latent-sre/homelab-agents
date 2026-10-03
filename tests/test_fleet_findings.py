"""Findings keep the legacy text and add the handles a consumer filters by."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from fleet.findings import Finding, Report


class FindingTests(unittest.TestCase):
    def test_a_finding_needs_a_rule(self) -> None:
        with self.assertRaises(ValueError):
            Finding("", "text")

    def test_report_renders_every_form_and_exits_one(self) -> None:
        root = Path("/repo")
        report = Report(
            root,
            [
                Finding(
                    "agent.tools",
                    "/repo/agents/a.md: missing explicit tools authority",
                    Path("/repo/agents/a.md"),
                ),
                Finding(
                    "skill.bundle",
                    "/repo/skills/x/SKILL.md:7: links a missing file",
                    Path("/repo/skills/x/SKILL.md"),
                    7,
                ),
            ],
        )
        self.assertEqual(1, report.exit_status())
        self.assertEqual(
            [
                "/repo/agents/a.md: missing explicit tools authority",
                "/repo/skills/x/SKILL.md:7: links a missing file",
            ],
            report.texts,
        )
        human = report.render_human()
        self.assertTrue(human.startswith("Fleet validation failed:\n- /repo/agents/a.md"))
        document = json.loads(report.render_json())
        self.assertEqual({"error": 2}, document["summary"])
        self.assertEqual("agents/a.md", document["findings"][0]["path"])
        self.assertEqual(7, document["findings"][1]["line"])

    def test_a_clean_report_exits_zero_and_prints_nothing(self) -> None:
        self.assertEqual(0, Report(Path("."), []).exit_status())
        self.assertEqual("", Report(Path("."), []).render_human())


if __name__ == "__main__":
    unittest.main()
