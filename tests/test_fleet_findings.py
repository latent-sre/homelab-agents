"""Findings keep the legacy text and add the handles a consumer filters by."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from fleet import diagnostics
from fleet.findings import Finding, Report


class FindingTests(unittest.TestCase):
    def test_a_finding_needs_a_rule_and_a_known_severity(self) -> None:
        with self.assertRaises(ValueError):
            Finding("", "text")
        with self.assertRaises(ValueError):
            Finding("r", "text", severity="fatal")

    def test_report_renders_every_form_and_exits_by_the_ladder(self) -> None:
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
                    "workflow.meta-contract",
                    "/repo/workflows/x.js:7: body references meta",
                    Path("/repo/workflows/x.js"),
                    7,
                ),
                Finding("doctor.note", "advisory", None, severity="warning"),
            ],
        )
        self.assertEqual(diagnostics.EXIT_FAIL, report.exit_status())
        self.assertEqual(
            [
                "/repo/agents/a.md: missing explicit tools authority",
                "/repo/workflows/x.js:7: body references meta",
                "advisory",
            ],
            report.texts,
        )
        human = report.render_human()
        self.assertTrue(human.startswith("Fleet validation failed:\n- /repo/agents/a.md"))
        document = json.loads(report.render_json())
        self.assertEqual(1, document["schema_version"])
        self.assertEqual({"error": 2, "warning": 1}, document["summary"])
        self.assertEqual("agents/a.md", document["findings"][0]["path"])
        self.assertEqual(7, document["findings"][1]["line"])
        github = report.render_github().splitlines()
        self.assertEqual(
            "::error file=agents/a.md,title=agent.tools::"
            "/repo/agents/a.md: missing explicit tools authority",
            github[0],
        )
        self.assertIn("line=7", github[1])
        self.assertTrue(github[2].startswith("::warning title=doctor.note::"))

    def test_warnings_alone_exit_warn_and_nothing_exits_ok(self) -> None:
        self.assertEqual(
            diagnostics.EXIT_WARN,
            Report(Path("."), [Finding("r", "t", severity="warning")]).exit_status(),
        )
        self.assertEqual(diagnostics.EXIT_OK, Report(Path("."), []).exit_status())
        self.assertEqual("", Report(Path("."), []).render_human())


if __name__ == "__main__":
    unittest.main()
