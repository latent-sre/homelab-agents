"""The projection from a routing cluster onto native eval case directories.

The generated graders are text that nothing in this repository executes, so the regexes are
compiled and matched here against real tool-call JSON. A grader whose `input_match` never matches
is not a weak tripwire -- it is a green light that means nothing, and it would pass every other
check in the tree.
"""

from __future__ import annotations

import json
import re
import unittest

from fleet import frontmatter, nativecases

AGENTS = frozenset({"homelab-engineer", "code-reviewer", "sde-fullstack"})
SPEC = {
    "cluster": "demo",
    "members": ["homelab-engineer", "code-reviewer", "runbook", "lab-audit"],
    "cases": [],
}


def grader_body(files: dict[str, str], name: str) -> dict[str, str]:
    for path, text in files.items():
        if path.endswith(f"/graders/{name}.md"):
            parsed = frontmatter.parse_text(text)
            assert parsed is not None, f"grader {name} has unreadable frontmatter"
            return parsed
    raise AssertionError(f"no grader named {name} in {sorted(files)}")


class ToolForTests(unittest.TestCase):
    def test_an_agent_dispatches_through_agent_and_a_skill_through_skill(self) -> None:
        self.assertEqual("Agent", nativecases.tool_for("homelab-engineer", AGENTS))
        self.assertEqual("Skill", nativecases.tool_for("runbook", AGENTS))


class NegativeCaseTests(unittest.TestCase):
    CASE = {
        "id": "neg-demo",
        "polarity": "negative",
        "prompt": "do something unrelated",
        "expect_not_fires": ["homelab-engineer", "runbook"],
    }

    def setUp(self) -> None:
        self.files = nativecases.case_files(SPEC, self.CASE, agents=AGENTS)

    def test_each_forbidden_target_gets_a_zero_bound_grader_on_its_own_tool(self) -> None:
        agent = grader_body(self.files, "no-homelab-engineer")
        self.assertEqual("Agent", agent["tool"])
        skill = grader_body(self.files, "no-runbook")
        self.assertEqual("Skill", skill["tool"])
        for body in (agent, skill):
            self.assertEqual("tool_used", body["type"])
            self.assertEqual("0", body["min"])
            self.assertEqual("0", body["max"])
            self.assertEqual("both", body["arm"], "a negative must hold in the no-plugin arm too")

    def test_a_target_outside_the_case_gets_no_grader(self) -> None:
        """The runner honoured `expect_not_fires`; a sibling firing is not an over-trigger."""
        self.assertNotIn("neg-demo/graders/no-code-reviewer.md", self.files)

    def test_a_broad_negative_forbids_every_cluster_member(self) -> None:
        broad = dict(self.CASE)
        del broad["expect_not_fires"]
        files = nativecases.case_files(SPEC, broad, agents=AGENTS)
        self.assertEqual(
            {f"neg-demo/graders/no-{m}.md" for m in SPEC["members"]},
            {p for p in files if "/graders/" in p},
        )


class GraderRegexTests(unittest.TestCase):
    """The generated `input_match` is matched against real tool-call JSON, not eyeballed."""

    def _pattern(self, component: str) -> re.Pattern[str]:
        """Compile the pattern AND prove the grader carries it byte-for-byte.

        The fleet's own frontmatter reader is lenient about quoting and cannot recover a
        single-quoted scalar's contents, so the emitted text is checked against the pattern
        directly rather than round-tripped through a parser that would silently mangle it.
        """
        tool = nativecases.tool_for(component, AGENTS)
        pattern = nativecases.forbidden_pattern(component, tool)
        case = {
            "id": "neg", "polarity": "negative", "prompt": "p",
            "expect_not_fires": [component],
        }
        files = nativecases.case_files(SPEC, case, agents=AGENTS)
        emitted = files[f"neg/graders/no-{component}.md"]
        self.assertIn(
            f"input_match: '{pattern}'\n", emitted,
            "the grader must carry the pattern in the single-quoted form, where a backslash is "
            "literal -- a double-quoted scalar needs the reader to decode it, and a mangled "
            "pattern matches nothing while a max:0 tripwire passes forever",
        )
        return re.compile(pattern)

    def test_an_agent_pattern_matches_both_spellings_and_nothing_else(self) -> None:
        pattern = self._pattern("homelab-engineer")
        for spelling in ("sde-agents:homelab-engineer", "homelab-engineer"):
            with self.subTest(spelling=spelling):
                self.assertRegex(json.dumps({"subagent_type": spelling}), pattern)
        self.assertNotRegex(json.dumps({"subagent_type": "code-reviewer"}), pattern)
        self.assertNotRegex(
            json.dumps({"subagent_type": "homelab-engineer-v2"}), pattern,
            "a longer name that merely starts with this one is a different component",
        )

    def test_a_skill_pattern_matches_the_keys_a_skill_call_uses(self) -> None:
        pattern = self._pattern("runbook")
        for key in ("command", "skill", "name"):
            with self.subTest(key=key):
                self.assertRegex(json.dumps({key: "sde-agents:runbook"}), pattern)
        self.assertNotRegex(json.dumps({"command": "lab-audit"}), pattern)

    def test_a_pattern_survives_the_json_whitespace_the_cli_may_emit(self) -> None:
        pattern = self._pattern("homelab-engineer")
        self.assertRegex('{"subagent_type" : "sde-agents:homelab-engineer"}', pattern)


class PositiveCaseTests(unittest.TestCase):
    CASE = {
        "id": "pos-demo",
        "polarity": "positive",
        "prompt": "diagnose the failure",
        "expect_fires": ["homelab-engineer", "runbook"],
        "expected_output": "either destination is correct",
    }

    def test_a_positive_gets_one_openly_vacuous_grader_and_no_lower_bound(self) -> None:
        """A positive's disjunction spans two tools, so no `tool_used` grader can state it.

        The harness rejects a case with no graders, so the placeholder exists; what matters is
        that it never claims a lower bound, which would fail whenever the OTHER correct
        destination fired.
        """
        files = nativecases.case_files(SPEC, self.CASE, agents=AGENTS)
        graders = [p for p in files if "/graders/" in p]
        self.assertEqual(["pos-demo/graders/verdict-is-fleet-side.md"], graders)
        body = grader_body(files, "verdict-is-fleet-side")
        self.assertEqual("0", body["min"])
        self.assertNotIn("max", body)
        self.assertNotIn("input_match", body)


class PromptFileTests(unittest.TestCase):
    CASE = {
        "id": "pos-demo",
        "polarity": "positive",
        "prompt": "diagnose: the thing # broke",
        "expect_fires": ["runbook"],
        "expected_output": "runbook is correct",
        "tags": ["disambiguation"],
    }

    def setUp(self) -> None:
        self.text = nativecases.case_files(SPEC, self.CASE, agents=AGENTS)["pos-demo/prompt.md"]
        parsed = frontmatter.parse_text(self.text)
        assert parsed is not None
        self.front = parsed

    def test_the_prompt_body_is_the_cluster_prompt_verbatim(self) -> None:
        self.assertTrue(self.text.endswith("diagnose: the thing # broke\n"))

    def test_a_prompt_with_yaml_punctuation_round_trips_rather_than_tearing(self) -> None:
        """`: ` and `#` in a value are why the emitter quotes; this proves it reads back whole."""
        self.assertEqual("runbook is correct", self.front["expected_outcome"])

    def test_the_cluster_and_polarity_are_carried_as_tags(self) -> None:
        self.assertEqual(
            ["demo", "positive", "disambiguation"], json.loads(self.front["tags"])
        )

    def test_the_measurement_levers_are_written_where_the_harness_reads_them(self) -> None:
        files = nativecases.case_files(
            SPEC, self.CASE, agents=AGENTS, max_turns=9, timeout_seconds=42,
            allowed_tools=("Read", "Skill"),
        )
        front = frontmatter.parse_text(files["pos-demo/prompt.md"])
        assert front is not None
        self.assertEqual("9", front["max_turns"])
        self.assertEqual("42", front["timeout_seconds"])
        self.assertEqual(["Read", "Skill"], json.loads(front["allowed_tools"]))


class ClusterTests(unittest.TestCase):
    def test_two_cases_sharing_an_id_are_refused_rather_than_silently_merged(self) -> None:
        """The directory is keyed by id, so the second would replace the first and every count
        would still look right."""
        case = {"id": "dup", "polarity": "positive", "prompt": "p", "expect_fires": ["runbook"]}
        with self.assertRaisesRegex(ValueError, "two cases with id"):
            nativecases.cluster_files(SPEC, [case, dict(case)], agents=AGENTS)

    def test_every_real_cluster_projects_and_every_grader_frontmatter_parses(self) -> None:
        """A live-wiring check: the projection runs over this repository's own clusters."""
        import pathlib

        agents = {p.stem for p in pathlib.Path("agents").glob("*.md")}
        clusters = sorted(pathlib.Path("evals/routing").glob("*.json"))
        self.assertTrue(clusters, "no routing clusters found to project")
        for path in clusters:
            with self.subTest(cluster=path.stem):
                spec = json.loads(path.read_text(encoding="utf-8"))
                files = nativecases.cluster_files(spec, spec["cases"], agents=agents)
                self.assertEqual(
                    len(spec["cases"]),
                    sum(1 for p in files if p.endswith("/prompt.md")),
                    "every case must project to exactly one prompt",
                )
                for rel, text in files.items():
                    self.assertIsNotNone(
                        frontmatter.parse_text(text),
                        f"{path.stem}/{rel} has unreadable frontmatter",
                    )


if __name__ == "__main__":
    unittest.main()
