"""The projection from a routing cluster onto native eval case directories.

The generated graders are text the native harness compiles; nothing in this repository runs them.
So the pattern each grader carries is unquoted exactly as YAML would and matched here against real
tool-call JSON -- a pattern that never matches would pass every negative and fail every positive
while looking like a grader.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from fleet import nativecases
from scripts import eval_routing

SPEC = {"cluster": "demo", "members": ["prompt-craft", "prompt-engineer"], "cases": []}
POSITIVE = {
    "id": "pos-case",
    "prompt": "Fix my skill.",
    "polarity": "positive",
    "expect_fires": ["prompt-craft", "prompt-engineer"],
    "tags": ["fix-trigger"],
}
NEGATIVE = {"id": "neg-case", "prompt": "Optimize this SQL.", "polarity": "negative"}

AGENT_CALL = (
    '{"type":"tool_use","name":"Agent","input":{"subagent_type":"sde-agents:prompt-engineer"}}'
)
SKILL_CALL = '{"type":"tool_use","name":"Skill","input":{"skill": "prompt-craft"}}'


def grader(files: dict[str, str], case_id: str) -> dict[str, str]:
    """The grader's fields, with `pattern` unquoted the way a YAML parser reads it."""
    text = files[f"{case_id}/graders/routing.md"]
    fields = {}
    for line in text.split("---")[1].strip().splitlines():
        key, value = line.split(": ", 1)
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
        fields[key] = value
    return fields


class GraderTests(unittest.TestCase):
    def test_a_positive_grader_matches_either_tool_in_either_spelling(self) -> None:
        fields = grader(nativecases.case_files(SPEC, POSITIVE), "pos-case")
        self.assertEqual(
            ("regex", "trace", "contains"), (fields["type"], fields["target"], fields["match"])
        )
        pattern = re.compile(fields["pattern"])
        self.assertTrue(pattern.search(AGENT_CALL))
        self.assertTrue(pattern.search(SKILL_CALL))
        self.assertTrue(pattern.search('{"input":{"skill":"sde-agents:prompt-craft"}}'))

    def test_the_pattern_matches_no_longer_name_and_no_other_plugin(self) -> None:
        pattern = re.compile(nativecases.routing_pattern(["prompt-craft"]))
        for text in (
            '{"input":{"skill":"prompt-crafter"}}',
            '{"input":{"skill":"other-plugin:prompt-craft"}}',
            '{"input":{"description":"prompt-craft"}}',
        ):
            with self.subTest(text=text):
                self.assertIsNone(pattern.search(text))

    def test_a_negative_without_targets_forbids_the_whole_cluster(self) -> None:
        fields = grader(nativecases.case_files(SPEC, NEGATIVE), "neg-case")
        self.assertEqual("not_contains", fields["match"])
        self.assertEqual(nativecases.routing_pattern(SPEC["members"]), fields["pattern"])

    def test_the_pattern_is_valid_javascript_without_hyphen_escapes(self) -> None:
        # The harness compiles it as a JS RegExp, which rejects `\-` under the `u` flag.
        self.assertNotIn("\\-", nativecases.routing_pattern(SPEC["members"]))

    def test_a_name_outside_the_component_grammar_never_reaches_a_pattern(self) -> None:
        for bad in ("a|b", "x.*", "Upper"):
            with self.subTest(name=bad), self.assertRaises(ValueError):
                nativecases.routing_pattern([bad])


class CaseTreeTests(unittest.TestCase):
    def test_the_prompt_is_tagged_with_cluster_and_polarity(self) -> None:
        # The driver selects each polarity with `--tag`, so the tag is load-bearing.
        prompt = nativecases.case_files(SPEC, POSITIVE)["pos-case/prompt.md"]
        self.assertIn('tags: ["demo", "positive", "fix-trigger"]', prompt)
        self.assertTrue(prompt.rstrip().endswith("Fix my skill."))

    def test_ids_that_collide_ignoring_case_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            nativecases.cluster_files(SPEC, [POSITIVE, {**NEGATIVE, "id": "POS-CASE"}])

    def test_an_id_that_would_leave_the_tree_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            nativecases.case_files(SPEC, {**POSITIVE, "id": "../escape"})


class DriverTests(unittest.TestCase):
    def _dry_run(self, *extra: str) -> tuple[int, str, Path]:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        cluster = tmp / "demo.json"
        cluster.write_text(json.dumps({**SPEC, "cases": [POSITIVE, NEGATIVE]}), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = eval_routing.main([str(cluster), "--plugin-dir", str(tmp), "--dry-run", *extra])
        return code, out.getvalue(), tmp

    def test_a_dry_run_writes_the_cases_and_one_command_per_polarity(self) -> None:
        code, out, tmp = self._dry_run()
        self.assertEqual(0, code)
        self.assertTrue((tmp / "evals/generated/demo/pos-case/graders/routing.md").is_file())
        self.assertIn("--tag positive --threshold 0.5", out)
        self.assertIn("--tag negative --threshold 1.0", out)

    def test_a_case_filter_skips_the_polarity_it_excludes(self) -> None:
        code, out, _ = self._dry_run("--case", "pos-*")
        self.assertEqual(0, code)
        self.assertIn("--tag positive", out)
        self.assertNotIn("--tag negative", out)


if __name__ == "__main__":
    unittest.main()
