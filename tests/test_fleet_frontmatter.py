"""The frontmatter dialect: refuse what it cannot read, and stay inside what every host reads.

The differential tripwire at the bottom is the load-bearing test. It runs a conforming YAML
parser beside the dialect over every canonical definition and pins the ONE class of divergence
the fleet has decided to live with, so a second class fails here instead of shipping.
"""

from __future__ import annotations

import unittest

from fleet import frontmatter as fm
from tests.support import HAS_HYPOTHESIS, HYPOTHESIS_REQUIRED, REPO, given, settings, st

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

    def test_a_single_quoted_scalar_carries_a_backslash_literally(self) -> None:
        """The form a regex must be emitted in: only `''` is an escape, so `\\s` stays `\\s`."""
        self.assertEqual(fm.yaml_single_quoted(r'"a"\s*:\s*"b"'), r"""'"a"\s*:\s*"b"'""")
        self.assertEqual(fm.yaml_single_quoted("it's"), "'it''s'")

    def test_a_value_with_a_line_break_is_refused_rather_than_emitted_torn(self) -> None:
        """A single-quoted scalar cannot carry one, and this dialect reads line by line, so the
        tail would be parsed as a frontmatter key of its own."""
        for value in ("a\nb", "a\rb", "a\u2028b"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "cannot carry a line break"):
                    fm.yaml_single_quoted(value)

    @unittest.skipIf(yaml is None, "PyYAML (dev dependency group) is required for the tripwire")
    def test_a_single_quoted_regex_round_trips_through_a_conforming_parser(self) -> None:
        """The claim the generated graders rest on: what the reader gets back IS the pattern.

        If this were false a `max: 0` tripwire would match nothing, count zero calls, and pass
        forever while enforcing nothing -- with no test in the tree able to tell.
        """
        for pattern in (
            r'"subagent_type"\s*:\s*"(?:sde-agents:)?homelab-engineer"',
            r'"(?:command|skill|name)"\s*:\s*"(?:sde-agents:)?runbook"',
        ):
            with self.subTest(pattern=pattern):
                self.assertEqual(
                    yaml.safe_load(f"k: {fm.yaml_single_quoted(pattern)}")["k"], pattern
                )


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


class LineBreakerEscapingTests(unittest.TestCase):
    """Deterministic pins for the three characters that motivated `_escape_line_breakers`.

    The property test next door found this defect, but a property is not a regression pin: a
    fresh Hypothesis run draws a few hundred strings and may never produce NEL, LINE SEPARATOR
    or PARAGRAPH SEPARATOR, so reverting the fix could pass wherever the local example database
    is absent -- CI included (Copilot, PR #190). These cases always run, and they run without
    the dev group.
    """

    # `str.splitlines()` breaks on all three; `json.dumps(ensure_ascii=False)` escapes none of
    # them, because none is a JSON control character. That disagreement is the whole defect.
    LINE_BREAKERS = {"NEL": "\x85", "LINE SEPARATOR": "\u2028", "PARAGRAPH SEPARATOR": "\u2029"}

    def test_each_line_breaker_is_escaped_rather_than_emitted_raw(self) -> None:
        for name, character in self.LINE_BREAKERS.items():
            with self.subTest(character=name):
                rendered = fm.yaml_scalar(f"before{character}after")
                self.assertNotIn(character, rendered, f"{name} was emitted raw")
                self.assertEqual(1, len(rendered.splitlines()), f"{name} still splits the line")

    def test_a_description_carrying_one_does_not_tear_the_frontmatter(self) -> None:
        for name, character in self.LINE_BREAKERS.items():
            with self.subTest(character=name):
                value = f"Routes work{character}to the right altitude"
                document = (
                    f"---\nname: demo\ndescription: {fm.yaml_scalar(value)}\n---\n\nBody.\n"
                )
                parsed = fm.parse_text(document)
                self.assertIsNotNone(parsed, f"{name} ended the frontmatter block early")
                self.assertEqual({"name", "description"}, set(parsed))
                self.assertEqual("demo", parsed["name"])

    def test_the_flow_list_emitter_escapes_them_too(self) -> None:
        for name, character in self.LINE_BREAKERS.items():
            with self.subTest(character=name):
                rendered = fm.yaml_flow_list([f"a{character}b"])
                self.assertNotIn(character, rendered, f"{name} was emitted raw in a flow list")


@unittest.skipUnless(HAS_HYPOTHESIS, HYPOTHESIS_REQUIRED)
class DialectPropertyTests(unittest.TestCase):
    """Properties over arbitrary text, where a hand-picked corpus stops being convincing.

    The dialect is a deliberate subset reader, so its interesting failures are inputs nobody
    would think to write down: a character Python calls a line break and YAML does not, a value
    whose rendering the fleet's own validator would then reject. Both of the findings recorded
    below came from these, not from a defect report.
    """

    @given(st.text(max_size=200))
    @settings(max_examples=400, deadline=None)
    def test_the_reader_never_raises_on_arbitrary_text(self, text: str) -> None:
        # The reader runs against files a contributor is editing, so a crash is a broken gate
        # rather than a refusal. Refusing is the dialect's job; raising is not.
        result = fm.parse_text(text)
        self.assertTrue(result is None or isinstance(result, dict))

    @given(st.text(max_size=200))
    @settings(max_examples=400, deadline=None)
    def test_the_writer_never_emits_a_scalar_its_own_validator_rejects(self, value: str) -> None:
        # `frontmatter.scalar` fails the build for a scalar a strict host would drop. If the
        # fleet's own writer could produce one, generation would author a file the validator
        # then refuses -- a gate that cannot be satisfied by any canonical edit.
        self.assertIsNone(fm.flow_scalar_defect(fm.yaml_scalar(value)))

    @given(st.text(max_size=200))
    @settings(max_examples=400, deadline=None)
    def test_an_emitted_scalar_never_breaks_the_frontmatter_it_is_written_into(
        self, value: str
    ) -> None:
        """No emitted value may end the frontmatter block early.

        This is what found the NEL fix. `str.splitlines()` breaks on \\x85, \\u2028 and \\u2029;
        `json.dumps(ensure_ascii=False)` emitted all three literally, because they are not JSON
        control characters. A description carrying one -- pasted from a word processor, say --
        was written whole and read back torn, with its tail parsed as a frontmatter key.
        """
        document = f"---\nname: demo\ndescription: {fm.yaml_scalar(value)}\n---\n\nBody.\n"
        parsed = fm.parse_text(document)
        self.assertIsNotNone(parsed, f"{value!r} ended the frontmatter block early")
        self.assertEqual("demo", parsed["name"])
        self.assertEqual({"name", "description"}, set(parsed))

    @given(
        st.text(
            # Everything that needs no escaping and no stripping: the control and separator
            # categories are what `json.dumps` escapes, and the three quote characters are what
            # the reader strips. The excluded set IS the boundary this test exists to pin.
            alphabet=st.characters(
                exclude_categories=("Cc", "Cs", "Zl", "Zp"),
                exclude_characters="\"\\'",
            ),
            max_size=200,
        )
    )
    @settings(max_examples=400, deadline=None)
    def test_a_value_carrying_no_quote_or_escape_round_trips_exactly(self, value: str) -> None:
        """The round trip holds exactly as far as quoting, and no further.

        The dialect reads a quoted scalar with `value.strip("\'\\"")` -- a crude strip of quote
        characters from both ends, not a scalar parser. Two consequences, one root cause, both
        found by this property rather than by a defect report:

        * it does not decode YAML's double-quoted escapes, while the hosts that load the
          definitions do, so `yaml_scalar('say "hi"')` reads back here as `say \\"hi\\"` and on a
          host as `say "hi"`;
        * it strips ANY quote character repeatedly, so the emitted `"say \'hi\'"` reads back as
          `say \'hi` -- a trailing apostrophe in a description is simply lost.

        Both are latent today: nothing compares a description read back from a generated file
        against its canonical source. They are recorded together as DIALECT-001 in
        `docs/fleet-roadmap.md`, not fixed here, because the fix is a real double-quoted scalar
        reader and that changes what every rule sees for every quoted value. This test pins the
        boundary so the "latent" claim stays checkable: everything short of a quote or an escape
        round-trips exactly.
        """
        rendered = fm.yaml_scalar(value)
        parsed = fm.parse_text(f"---\nname: {rendered}\n---\n")
        self.assertIsNotNone(parsed)
        self.assertEqual(value, parsed["name"])


if __name__ == "__main__":
    unittest.main()
