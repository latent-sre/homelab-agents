"""`python -m fleet validate` is the legacy validator's run with structured output."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fleet import cli
from tests.support import run_main

FIXTURES = Path(__file__).parent / "fixtures"


class CliTests(unittest.TestCase):
    def test_valid_fixture_exits_zero_and_reports_counts(self) -> None:
        code, out = run_main(cli.main, "validate", "--root", str(FIXTURES / "valid"))
        self.assertEqual(0, code)
        self.assertIn("Validated 1 agents and 1 skills", out)

    def test_invalid_fixture_exits_one_and_json_names_the_rule(self) -> None:
        code, out = run_main(
            cli.main, "validate", "--root", str(FIXTURES / "missing-tools"), "--json"
        )
        self.assertEqual(1, code)
        document = json.loads(out)
        self.assertIn("agent.tools", [f["rule"] for f in document["findings"]])
        self.assertEqual("agents/builder.md", document["findings"][0]["path"])

    def test_github_annotations_render_one_line_per_finding(self) -> None:
        code, out = run_main(
            cli.main, "validate", "--root", str(FIXTURES / "unknown-tool"), "--github"
        )
        self.assertEqual(1, code)
        self.assertTrue(out.startswith("::error file=agents/builder.md"))

    def test_write_inventory_repairs_then_validates_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "valid", dst)
            readme = dst / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace("`builder`", "`stale`"), encoding="utf-8"
            )
            self.assertEqual(1, run_main(cli.main, "validate", "--root", str(dst))[0])
            self.assertEqual(
                0, run_main(cli.main, "validate", "--root", str(dst), "--write-inventory")[0]
            )
            self.assertEqual(0, run_main(cli.main, "validate", "--root", str(dst))[0])

    def test_validate_loads_the_tree_once(self) -> None:
        # The rules, the inventory check, and the success counts all read one snapshot; a second
        # load would let a definition changed between reads be counted without being validated.
        from unittest import mock

        from fleet.snapshot import Fleet

        with mock.patch.object(Fleet, "load", wraps=Fleet.load) as load:
            code, out = run_main(cli.main, "validate", "--root", str(FIXTURES / "valid"))
        self.assertEqual(0, code, out)
        self.assertEqual(1, load.call_count)

    def test_rules_verb_lists_every_registered_rule(self) -> None:
        from fleet import rules

        code, out = run_main(cli.main, "rules")
        self.assertEqual(0, code)
        for entry in rules.rules():
            self.assertIn(entry.id, out)


if __name__ == "__main__":
    unittest.main()
