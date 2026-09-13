"""The frontmatter dialect: refuse what it cannot read, and stay inside what every host reads.

The differential tripwire at the bottom is the load-bearing test. It runs a conforming YAML
parser beside the dialect over every canonical definition and pins the ONE class of divergence
the fleet has decided to live with, so a second class fails here instead of shipping.
"""

from __future__ import annotations

import unittest

from fleet import frontmatter as fm
from tests.support import REPO

try:  # The dev dependency group installs it; a bare interpreter skips the tripwire loudly below.
    import yaml
except ImportError:  # pragma: no cover - exercised only on hosts without the dev group
    yaml = None


def _parse(text: str) -> dict[str, str] | None:
    return fm.parse_text(text)


class ReaderTests(unittest.TestCase):
    def test_reads_inline_block_sequence_and_folded_values(self) -> None:
        parsed = _parse(
            "---\n"
            "name: demo\n"
            "description: >\n"
            "  Folded over\n"
            "  two lines.\n"
            "tools: Read, Agent(worker, researcher), Bash\n"
            "skills:\n"
            "  # a comment inside the sequence\n"
            "  - one\n"
            "\n"
            "  - 'two'\n"
            'model: "inherit"\n'
            "---\n"
            "body\n"
        )
        self.assertEqual(
            parsed,
            {
                "name": "demo",
                "description": "Folded over two lines.",
                "tools": "Read, Agent(worker, researcher), Bash",
                "skills": "one, two",
                "model": "inherit",
            },
        )
        self.assertEqual(
            fm.split_tools(parsed["tools"]), ["Read", "Agent(worker, researcher)", "Bash"]
        )

    def test_refuses_rather_than_guesses(self) -> None:
        self.assertIsNone(_parse("name: no opener\n---\n"))
        self.assertIsNone(_parse("---\nname: unterminated\n"))
        self.assertIsNone(
            _parse("---\ntools Read, Write\n---\n"), "a typo'd key must not read as no authority"
        )
        self.assertIsNone(
            _parse("---\nmodel: opus\nmodel: inherit\n---\n"), "YAML keeps the last duplicate"
        )
        self.assertIsNone(
            _parse("\n---\nname: late opener\n---\n"),
            "Claude Code reads frontmatter only on line 1",
        )

    def test_span_returns_the_closing_marker_index(self) -> None:
        self.assertEqual(fm.span(["---", "a: b", "---", "body"]), 2)
        self.assertIsNone(fm.span(["---", "a: b"]))
        self.assertIsNone(fm.span([]))


class FlowScalarDefectTests(unittest.TestCase):
    def test_clean_scalars_pass(self) -> None:
        for value in (
            '"fine"',
            "'it''s fine'",
            '"tab\\tand\\u00e9"',
            '"\\x41"',
            "'single # not comment'",
        ):
            with self.subTest(value=value):
                self.assertIsNone(fm.flow_scalar_defect(value))

    def test_each_defect_class_is_named(self) -> None:
        cases = {
            '"never closes': "never closes on its line",
            '"ok"oops': "carries the trailing token",
            "'Use the agent's output": "carries the trailing token",
            '"ok" # note': "deliberately stricter than YAML",
            '"Use C:\\q"': "invalid escape sequence",
            '"bad \\u12"': "malformed hex escape",
            '"\\uD800"': "lone surrogate U+D800",
            '"\\U00110000"': "U+110000",
            '"dangling\\': "dangling backslash",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                defect = fm.flow_scalar_defect(value)
                self.assertIsNotNone(defect)
                self.assertIn(expected, defect)


class EmitterTests(unittest.TestCase):
    def test_emitted_scalars_are_json_and_therefore_yaml(self) -> None:
        self.assertEqual(
            fm.yaml_scalar('a "quoted" [list-looking] value: here'),
            '"a \\"quoted\\" [list-looking] value: here"',
        )
        self.assertEqual(fm.yaml_flow_list(["read", "search"]), '["read", "search"]')

    @unittest.skipIf(yaml is None, "PyYAML (dev dependency group) is required for the tripwire")
    def test_emitted_values_round_trip_through_a_conforming_parser(self) -> None:
        for value in ['[what to upgrade, or "everything"]', "a: b", "# not a comment", "plain"]:
            with self.subTest(value=value):
                self.assertEqual(yaml.safe_load(f"k: {fm.yaml_scalar(value)}")["k"], value)
        self.assertEqual(yaml.safe_load(f"k: {fm.yaml_flow_list(['a b', 'c'])}")["k"], ["a b", "c"])


class DialectDifferentialTripwire(unittest.TestCase):
    """Every canonical definition must read the same under the dialect and a conforming parser,
    except for exactly one declared divergence: a bare `argument-hint: [...]`, which Claude Code's
    own documentation writes unquoted and treats as a string while YAML reads a flow sequence.
    That divergence is tolerated because the generated host copies re-serialize the value through
    `yaml_scalar`, so no host ever sees the bare form. Any OTHER divergence means a definition
    has drifted outside the subset every host reads identically, and fails here."""

    ALLOWED_DIVERGENT_KEYS = frozenset({"argument-hint"})

    @unittest.skipIf(yaml is None, "PyYAML (dev dependency group) is required for the tripwire")
    def test_dialect_agrees_with_a_conforming_parser_on_every_canonical_definition(self) -> None:
        files = sorted((REPO / "agents").glob("*.md")) + sorted(
            (REPO / "skills").glob("*/SKILL.md")
        )
        self.assertGreater(len(files), 0)
        divergences: list[str] = []
        for path in files:
            lines = path.read_text(encoding="utf-8").splitlines()
            end = fm.span(lines)
            self.assertIsNotNone(end, path)
            dialect = fm.parse_lines(lines, end)
            self.assertIsNotNone(dialect, path)
            conforming = yaml.safe_load("\n".join(lines[1:end]))
            self.assertEqual(set(conforming), set(dialect), path)
            for key, value in conforming.items():
                if isinstance(value, list):
                    if key in self.ALLOWED_DIVERGENT_KEYS and dialect[key].startswith("["):
                        continue  # the one declared divergence
                    flattened = ", ".join(str(item) for item in value)
                elif isinstance(value, bool):
                    flattened = str(value).lower()
                else:
                    flattened = str(value)
                if dialect[key].strip() != flattened.strip():
                    divergences.append(
                        f"{path.relative_to(REPO)}: {key}: dialect {dialect[key]!r} "
                        f"vs conforming {value!r}"
                    )
        self.assertEqual([], divergences, "\n".join(divergences))


if __name__ == "__main__":
    unittest.main()
