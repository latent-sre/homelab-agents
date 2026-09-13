from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import validate_fleet
from tests.support import REPO


FIXTURES = Path(__file__).parent / "fixtures"


VALID_AGENT = (
    "---\n"
    "name: builder\n"
    "description: Use when implementing a small feature.\n"
    "tools: Read, Write\n"
    "model: inherit\n"
    "---\n\n"
    "# Builder\n\n"
    "## Review packet\n\n"
    "- **Changed**: what changed.\n"
)


class FleetValidatorTests(unittest.TestCase):
    # Claude's per-session worktrees live INSIDE the repository root, so a `git add -A` sweeps
    # one in as a 160000 gitlink. That happened on three commits (fbb142e, 31f6334, 62629b9)
    # and stayed invisible until a release-tag dry-run surfaced it by hand: a gitlink with no
    # .gitmodules entry is unusable, so clean clones and archives get an empty directory where
    # a checkout should be, and nothing in the suite said a word.
    # A literal line-presence check misses the case where a later rule negates the pattern; use
    # `git check-ignore` to verify that the effective ignore decision is correct.
    @unittest.skipUnless(
        (REPO / ".git").exists() and shutil.which("git"),
        "not a git checkout or git binary absent -- cannot check effective ignore",
    )
    def test_claude_worktrees_are_gitignored(self) -> None:
        result = subprocess.run(
            ["git", "check-ignore", "-q", ".claude/worktrees/fake"],
            cwd=REPO,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            0,
            result.returncode,
            ".claude/worktrees/ is not effectively gitignored (check-ignore exit code != 0); "
            "a later rule may be negating the pattern",
        )

    # Deliberately generalized past the incident: this repository has no submodules, so ANY
    # tracked gitlink is the same defect. Scoped to `.claude/worktrees` it would go green the
    # first time a host puts its transient checkouts somewhere else.
    @unittest.skipUnless(
        (REPO / ".git").exists() and shutil.which("git"),
        "not a git checkout or git binary absent -- no index to inspect",
    )
    def test_no_gitlink_is_tracked_anywhere(self) -> None:
        staged = subprocess.run(
            ["git", "ls-files", "--stage"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, staged.returncode, staged.stderr)
        gitlinks = [line for line in staged.stdout.splitlines() if line.startswith("160000 ")]
        self.assertEqual([], gitlinks)

    def test_valid_fleet_and_generated_inventory(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(FIXTURES / "valid")
        self.assertEqual([], issues)

    def test_agent_requires_explicit_tools(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "missing-tools", check_inventory=False
        )
        self.assertTrue(any("missing explicit tools authority" in issue for issue in issues))

    def test_unknown_tool_is_reported(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "unknown-tool", check_inventory=False
        )
        self.assertTrue(any("unknown tool 'Bogus'" in issue for issue in issues))

    def test_unadopted_mcp_tool_is_reported(self) -> None:
        # The fixture uses GitHits' feedback tool: structurally real MCP authority, but an external
        # write that the fleet's evidence agents do not need. It must fail as a POLICY decision,
        # not be mislabeled as an unknown Claude Code tool.
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "unadopted-mcp-tool", check_inventory=False
        )
        feedback_issues = [issue for issue in issues if "feedback" in issue]
        self.assertTrue(any("not adopted by this fleet" in issue for issue in feedback_issues), issues)
        self.assertFalse(any("not a Claude Code tool" in issue for issue in feedback_issues), issues)

    def test_bare_skill_reference_without_preload_is_reported(self) -> None:
        # The fixture's agent says "work the `tuning` skill" with no skills: preload — an
        # instruction that cannot execute and errors nowhere, which is exactly how sde-fullstack's
        # `code-craft` reference shipped unreachable.
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "unreachable-bare-skill", check_inventory=False
        )
        self.assertTrue(any("unreachable authority" in issue and "tuning" in issue for issue in issues), issues)

    def test_perishable_token_outside_owner_is_reported(self) -> None:
        # The fixture's agent restates the complete upstream issue identifier while its skill uses
        # the same digits as an unrelated port. Only the platform-fact copy should be rejected.
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "perishable-token-copy", check_inventory=False
        )
        token_issues = [issue for issue in issues if "perishable platform token" in issue]
        self.assertEqual(1, len(token_issues), issues)
        self.assertIn("anthropics/claude-code#22345", token_issues[0])

    def test_unquoted_prose_scalar_with_colon_space_is_reported(self) -> None:
        """The fixture's skill writes both prose fields as plain scalars carrying ': '.

        A conforming YAML parser refuses such a file outright ("mapping values are not allowed
        here"), but nothing here could see it: `parse_frontmatter` reads to end of line and the
        generated copies re-serialize through `json.dumps`, so the bad bytes live only in the
        canonical file and every downstream check passes. The fixture's AGENT is the control --
        the same colon-space inside a quoted value is legal and must not be reported, or the rule
        would be a ban on colons rather than a YAML-validity check.
        """
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "unquoted-yaml-scalar", check_inventory=False
        )
        quoting_issues = [issue for issue in issues if "conforming YAML parser" in issue]
        self.assertEqual(2, len(quoting_issues), issues)
        self.assertTrue(all("skills" in issue for issue in quoting_issues), quoting_issues)
        self.assertEqual(
            {"'description'", "'argument-hint'"},
            {issue.split("unquoted ")[1].split(" frontmatter")[0] for issue in quoting_issues},
        )

    def test_unterminated_quoted_prose_scalar_is_reported(self) -> None:
        """The rule skipped on the OPENING quote, which left its own failure one typo away.

        The fixture's skill opens a double quote and never closes it. `parse_frontmatter` reads to
        end of line and returns a truncated but plausible value, the generated copies re-serialize
        exactly that, and every check passed -- while a strict parser hunts the close quote past
        the newline and refuses the file, dropping the component silently. The fixture's AGENT is
        the control: the same colon-space inside a CLOSED quote must stay unreported, or the
        repair would have traded one silent loss for a ban on quoted prose.
        """
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "unterminated-yaml-scalar", check_inventory=False
        )
        unterminated = [issue for issue in issues if "never closes on its line" in issue]
        self.assertEqual(1, len(unterminated), issues)
        self.assertIn("skills", unterminated[0])
        self.assertIn("'description'", unterminated[0])

    def test_quoted_prose_scalar_with_a_trailing_token_is_reported(self) -> None:
        """Closing somewhere on the line is not the bar; closing with nothing after it is.

        YAML ends a flow scalar at the FIRST unescaped matching quote, so a scan that returned
        True on finding one accepted two shapes a strict parser refuses (review finding, PR #120).
        The fixture carries both: `"...ok"oops` is visibly wrong, and
        `'Use the agent's output` reads as ordinary prose while closing at the apostrophe in
        "agent's" and leaving `s output` as trailing tokens -- the one an author would actually
        write, and the one no reader catches.
        """
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "trailing-token-yaml-scalar", check_inventory=False
        )
        trailing = [issue for issue in issues if "carries the trailing token" in issue]
        self.assertEqual(2, len(trailing), issues)
        self.assertEqual(
            {"'description'", "'argument-hint'"},
            {
                issue.split(" frontmatter value ")[0].rsplit(" ", 1)[1]
                for issue in trailing
            },
        )
        # Each finding must quote the token it found, not merely say one exists: the two shapes
        # need different repairs, and an author cannot tell which is theirs from a generic message.
        self.assertTrue(any("'oops'" in issue for issue in trailing), trailing)
        self.assertTrue(any("'s output'" in issue for issue in trailing), trailing)

    def test_trailing_comment_is_rejected_because_this_parser_keeps_it(self) -> None:
        """Deliberately stricter than YAML, and the reversal of an earlier ruling here.

        A ` # comment` after the closing quote is legal YAML, so this rule first ACCEPTED it. That
        was wrong for this repository: `parse_frontmatter` is not comment-aware and strips only the
        outer quote characters, so `description: "Use when routing." # note` parses to
        `Use when routing." # note` -- closing quote and comment intact -- and every generated host
        copy ships that as the description. The executed parse is the evidence, and it is asserted
        here so the rule cannot drift back to the YAML-shaped answer.
        """
        line = 'description: "Use when routing." # note'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "agents").mkdir()
            (root / "agents" / "builder.md").write_text(VALID_AGENT, encoding="utf-8")
            skill = root / "skills" / "craft"
            skill.mkdir(parents=True)
            path = skill / "SKILL.md"
            path.write_text(
                f"---\nname: craft\n{line}\nargument-hint: [the file to change]\n---\n\n# Craft\n",
                encoding="utf-8",
            )
            # What the generators would actually consume, read from the shipped parser.
            self.assertEqual(
                'Use when routing." # note',
                validate_fleet.parse_frontmatter(path)["description"],
            )
            issues = validate_fleet.validate_yaml_scalar_quoting(root)
            self.assertEqual(1, len(issues), issues)
            self.assertIn("carries the comment", issues[0])
            self.assertIn("deliberately stricter than YAML", issues[0])

    def test_invalid_double_quoted_escape_is_reported(self) -> None:
        """`\\q` is not a YAML escape, and skipping backslash-plus-one accepted every such typo.

        A Windows path in a description is how an author writes one by accident, and the parser
        here keeps the backslash while a conforming one refuses the document -- the same silent
        absence, through the escape set instead of the quote (review finding, PR #120).
        """
        for value, expected in (
            # The finding must quote the offending sequence: "invalid escape" alone leaves an
            # author hunting a backslash in a 900-character description.
            ('"Use C:\\q for the path."', repr("\\q")),
            ('"Use \\z here."', repr("\\z")),
            ('"Use \\x2 here."', "malformed hex escape"),
            # Syntactically complete and still not a character: counting hex digits accepted both.
            ('"Use \\uD800 here."', "lone surrogate U+D800"),
            # U+ notation is not zero-padded past four digits, so the escape's eight digits and
            # the code point's rendering deliberately differ.
            ('"Use \\U00110000 here."', "U+110000"),
            # No closing quote at all, so the backslash has nothing to escape. `"...\\"` is a
            # DIFFERENT shape -- there the backslash escapes the quote and the honest diagnosis is
            # "never closes", which the unterminated test already covers.
            ('"Ends on a backslash \\', "dangling backslash"),
        ):
            with self.subTest(value=value):
                defect = validate_fleet._flow_scalar_defect(value)
                self.assertIsNotNone(defect, value)
                self.assertIn(expected, defect)

    def test_single_quoted_scalars_have_no_backslash_escapes(self) -> None:
        """YAML gives single-quoted scalars no backslash escapes, so validating them would invent
        a rule the parser does not have -- and `'...C:\\q...'` is a legal, ordinary value."""
        self.assertIsNone(
            validate_fleet._flow_scalar_defect("'Use C:\\q for the path.'")
        )
        # The doubled-quote escape is the only one single-quoted YAML has, and it must still work.
        self.assertIsNone(
            validate_fleet._flow_scalar_defect("'Use the lab''s path.'")
        )

    def test_closed_quotes_and_their_escapes_are_not_reported(self) -> None:
        """The false-red direction, which is why the closing scan honors both escape forms.

        The escape rows are the precision controls the escape-set repair owes: `\\"`, `\\\\`, the
        named escapes, and a well-formed `\\x` hex escape are all legal and must survive, or the
        repair trades the silent loss for a ban on ordinary frontmatter. The last three sit on the
        code-point range check's own boundaries -- one below the surrogate block, one above it, and
        the maximum code point -- because an off-by-one there would reject legal text.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "agents").mkdir()
            (root / "agents" / "builder.md").write_text(VALID_AGENT, encoding="utf-8")
            skill = root / "skills" / "craft"
            skill.mkdir(parents=True)
            for description in (
                'description: "Use when applying conventions: the ordinary quoted form."',
                "description: 'Use when applying the lab''s conventions: a doubled quote.'",
                'description: "Use when the value quotes a \\"name: value\\" pair inline."',
                'description: "Use when applying conventions."   ',
                'description: "Use when a path needs a \\\\ backslash."',
                'description: "Use when a tab \\t or newline \\n is meant."',
                'description: "Use when the code point \\x41 is meant."',
                'description: "Use when \\uD7FF, just below the surrogate block, is meant."',
                'description: "Use when \\uE000, just above the surrogate block, is meant."',
                'description: "Use when \\U0010FFFF, the maximum code point, is meant."',
            ):
                with self.subTest(description=description):
                    skill.joinpath("SKILL.md").write_text(
                        f"---\nname: craft\n{description}\n"
                        "argument-hint: [the file to change]\n---\n\n# Craft\n",
                        encoding="utf-8",
                    )
                    self.assertEqual([], validate_fleet.validate_yaml_scalar_quoting(root))

    def test_flow_collection_argument_hint_is_not_reported(self) -> None:
        """Every fleet skill writes `argument-hint: [a hint]`, which YAML reads as a flow sequence.

        A colon-space inside one parses (as a one-pair mapping -- wrong, but not a parse error), so
        flagging it would make this rule claim a rejection that never happens.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "agents").mkdir()
            (root / "agents" / "builder.md").write_text(VALID_AGENT, encoding="utf-8")
            skill = root / "skills" / "craft"
            skill.mkdir(parents=True)
            skill.joinpath("SKILL.md").write_text(
                "---\nname: craft\ndescription: Use when applying conventions.\n"
                "argument-hint: [the file to change: a path]\n---\n\n# Craft\n",
                encoding="utf-8",
            )
            self.assertEqual([], validate_fleet.validate_yaml_scalar_quoting(root))

    def test_missing_bundled_reference_fails(self) -> None:
        """The fixture links `./references/missing.md` on purpose. Before BUNDLE_REF_RE accepted the
        `./` prefix the link matched nothing at all, so a broken path raised no issue whatsoever --
        this test is what fails if that lookbehind regresses.
        """
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "missing-reference", check_inventory=False
        )
        self.assertTrue(any("references/missing.md" in issue for issue in issues))

    def test_dot_slash_and_bare_bundle_paths_are_the_same_reference(self) -> None:
        """Both direction checks compare against this set, so the two spellings must collapse or the
        orphan check would call a linked file unreachable.
        """
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "SKILL.md"
            skill.write_text(
                "See ./references/a.md and references/b.md.\n", encoding="utf-8"
            )
            self.assertEqual(
                {"references/a.md", "references/b.md"},
                validate_fleet.bundle_references(skill),
            )

    def test_bundle_reference_does_not_restart_inside_other_paths(self) -> None:
        """The optional `./` must not let matching restart inside a parent or dotted token."""
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "SKILL.md"
            invalid_paths = (
                "../references/parent.md",
                ".references/hidden.md",
                "foo.references/embedded.md",
                "https://example.test/references/remote.md",
            )
            for invalid_path in invalid_paths:
                with self.subTest(invalid_path=invalid_path):
                    skill.write_text(f"Read {invalid_path}.\n", encoding="utf-8")
                    self.assertEqual(set(), validate_fleet.bundle_references(skill))

    def test_evidence_label_drift_is_reported(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "evidence-drift", check_inventory=False
        )
        self.assertTrue(any("evidence labels drifted" in issue for issue in issues))

    def test_missing_packet_is_reported(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "missing-packet", check_inventory=False
        )
        self.assertTrue(any("missing end-of-task packet" in issue for issue in issues))

    def test_inventory_drift_is_reported(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(FIXTURES / "inventory-drift")
        self.assertTrue(any("inventory drifted" in issue for issue in issues))

    def test_folded_description_is_supported(self) -> None:
        fields = validate_fleet.parse_frontmatter(FIXTURES / "folded" / "builder.md")
        self.assertIsNotNone(fields)
        self.assertEqual("Use when implementing a small feature.", fields["description"])

    def test_malformed_frontmatter_is_rejected(self) -> None:
        """An unparseable line used to be skipped silently, so a typo'd key configured nothing and
        still validated.
        """
        self.assertIsNone(
            validate_fleet.parse_frontmatter(FIXTURES / "folded" / "malformed.md")
        )

    def test_duplicate_frontmatter_key_is_rejected(self) -> None:
        """YAML keeps the last duplicate, so the file would validate against a value its author did
        not mean to be live.
        """
        self.assertIsNone(
            validate_fleet.parse_frontmatter(FIXTURES / "folded" / "duplicate-key.md")
        )

    def test_inventory_replacement_is_pure(self) -> None:
        content = (FIXTURES / "inventory-drift" / "README.md").read_text(encoding="utf-8")
        expected = validate_fleet.render_inventory(["builder"], ["craft"])
        updated = validate_fleet.replace_inventory(content, expected)
        self.assertIn(expected, updated)
        self.assertNotIn("stale", updated)

    def test_inventory_replacement_preserves_crlf(self) -> None:
        content = (
            (FIXTURES / "inventory-drift" / "README.md")
            .read_text(encoding="utf-8")
            .replace("\n", "\r\n")
        )
        expected = validate_fleet.render_inventory(["builder"], ["craft"])
        updated = validate_fleet.replace_inventory(content, expected)
        self.assertNotIn("\n", updated.replace("\r\n", ""))


    # --- main() exit-code contract (T1): CI's entire signal rests on this ---

    def test_main_returns_zero_on_valid_fleet(self) -> None:
        self.assertEqual(0, validate_fleet.main(["--root", str(FIXTURES / "valid")]))

    def test_main_returns_one_on_invalid_fleet(self) -> None:
        self.assertEqual(1, validate_fleet.main(["--root", str(FIXTURES / "missing-tools")]))

    # --- --write-inventory round-trip (T3): the operation the single-source design depends on ---

    def test_main_write_inventory_regenerates_readme_and_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "valid", dst)
            readme = dst / "README.md"
            drifted = validate_fleet.INVENTORY_RE.sub(
                "<!-- fleet-inventory:start -->\nstale\n<!-- fleet-inventory:end -->",
                readme.read_text(encoding="utf-8"),
                count=1,
            )
            readme.write_text(drifted, encoding="utf-8")
            # precondition: the drift makes plain validation fail
            self.assertEqual(1, validate_fleet.main(["--root", str(dst)]))
            # write mode repairs the README and exits clean
            self.assertEqual(
                0, validate_fleet.main(["--write-inventory", "--root", str(dst)])
            )
            repaired = readme.read_text(encoding="utf-8")
            self.assertNotIn("stale", repaired)
            self.assertIn("`builder`", repaired)
            self.assertIn("`craft`", repaired)
            # idempotent: a following read-only run stays green
            self.assertEqual(0, validate_fleet.main(["--root", str(dst)]))

    def test_replace_inventory_without_markers_raises(self) -> None:
        with self.assertRaises(ValueError):
            validate_fleet.replace_inventory("# no markers here\n", "whatever")

    # --- frontmatter parser edge cases (T6) ---

    def _parse(self, text: str) -> dict | None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.md"
            path.write_text(text, encoding="utf-8")
            return validate_fleet.parse_frontmatter(path)

    def test_parser_returns_none_without_opening_marker(self) -> None:
        self.assertIsNone(self._parse("name: builder\n---\n"))

    def test_parser_returns_none_when_frontmatter_is_unterminated(self) -> None:
        self.assertIsNone(self._parse("---\nname: builder\n\n# body but no closing marker\n"))

    def test_parser_strips_surrounding_quotes_from_values(self) -> None:
        fields = self._parse('---\nname: "builder"\ncolor: \'red\'\n---\n')
        self.assertEqual("builder", fields["name"])
        self.assertEqual("red", fields["color"])

    def test_parser_reads_literal_block_scalar(self) -> None:
        fields = self._parse("---\ndescription: |\n  line one\n  line two\n---\n")
        self.assertIn("line one", fields["description"])
        self.assertIn("line two", fields["description"])

    def test_parser_reads_yaml_block_sequence(self) -> None:
        # TOP_LEVEL_KEY_RE is anchored at column zero, so `  - item` lines under `skills:` never
        # matched it and `fields["skills"]` silently came back "" -- the root cause of P1-a.
        fields = self._parse(
            "---\nname: builder\nskills:\n  - backend-craft\n  - frontend-craft\nmodel: inherit\n---\n"
        )
        self.assertEqual("backend-craft, frontend-craft", fields["skills"])
        self.assertEqual("inherit", fields["model"])  # the key after the list is still parsed

    def test_parser_reads_block_sequence_with_interleaved_blanks_and_comments(self) -> None:
        # A blank line or `#` comment between `skills:` and the first `- item` used to leave the
        # list items stranded in the outer loop, which then returned None because `- item` lines
        # don't match TOP_LEVEL_KEY_RE.
        fields = self._parse(
            "---\nname: builder\nskills:\n  # note\n\n  - backend-craft\n  - frontend-craft\nmodel: inherit\n---\n"
        )
        self.assertIsNotNone(fields)
        self.assertEqual("backend-craft, frontend-craft", fields["skills"])
        self.assertEqual("inherit", fields["model"])

    # --- validator guardrail branches (T2) ---

    def _agent_issues(self, *files: tuple[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            agents = Path(tmp) / "agents"
            agents.mkdir()
            for filename, body in files:
                (agents / filename).write_text(body, encoding="utf-8")
            issues, _ = validate_fleet.validate_agents(Path(tmp))
            return issues

    def _skill_issues(self, name: str, frontmatter: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "skills" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\n{frontmatter}---\n\nBody.\n", encoding="utf-8"
            )
            issues, _ = validate_fleet.validate_skills(Path(tmp))
            return issues

    def test_unknown_skill_frontmatter_key_is_reported(self) -> None:
        # Symmetric with the agent check. Before this, the skill path validated name/description/
        # bundle refs but never the KEY namespace, so a `disable-model-invocaton` typo left a
        # side-effect skill model-invocable with no error (external-review gap).
        issues = self._skill_issues(
            "craft",
            "name: craft\ndescription: Use when building.\ndisable-model-invocaton: true\n",
        )
        self.assertTrue(
            any("unknown frontmatter key" in i and "disable-model-invocaton" in i for i in issues),
            issues,
        )

    def test_documented_skill_frontmatter_keys_are_accepted(self) -> None:
        # The full documented set must pass, or the allowlist is a false tripwire. "Full" is meant
        # literally: this asserts EVERY key in KNOWN_SKILL_FIELDS, because a typo'd allowlist entry
        # (`backgroud`) rejects the very field it was added to permit, and a test that exercised
        # only a hand-picked five would not notice.
        documented = sorted(validate_fleet.KNOWN_SKILL_FIELDS - {"name", "description"})
        extra = "".join(f"{key}: x\n" for key in documented)
        issues = self._skill_issues(
            "craft", "name: craft\ndescription: Use when building.\n" + extra
        )
        self.assertEqual([], [i for i in issues if "frontmatter key" in i])
        self.assertIn("background", documented)  # the field added 2026-07-24, now covered

    def test_agent_name_must_match_filename(self) -> None:
        body = VALID_AGENT.replace("name: builder", "name: other")
        self.assertTrue(any("must match filename" in i for i in self._agent_issues(("builder.md", body))))

    def test_unknown_model_is_reported(self) -> None:
        body = VALID_AGENT.replace("model: inherit", "model: gpt-4")
        self.assertTrue(any("unknown model" in i for i in self._agent_issues(("builder.md", body))))

    def test_fable_alias_is_accepted(self) -> None:
        # `fable` is a documented Claude Code alias (code.claude.com/docs/en/sub-agents);
        # rejecting it was a real bug, so pin the fix.
        body = VALID_AGENT.replace("model: inherit", "model: fable")
        self.assertEqual([], [i for i in self._agent_issues(("builder.md", body)) if "model" in i])

    def test_pinned_full_model_id_is_a_policy_error_not_a_schema_error(self) -> None:
        # Valid at runtime, banned by fleet policy — the message must say so, not claim it's unknown.
        body = VALID_AGENT.replace("model: inherit", "model: claude-opus-4-8")
        issues = [i for i in self._agent_issues(("builder.md", body)) if "model" in i]
        self.assertTrue(any("pinned" in i for i in issues), issues)
        self.assertFalse(any("unknown model" in i for i in issues), issues)

    def test_scoped_agent_grant_is_reported_as_a_false_restriction(self) -> None:
        # `Agent(code-reviewer)` restricts spawning only for a main-thread agent (`claude --agent`).
        # Everything in agents/ is a SUBAGENT definition, where the type list is ignored — so this
        # reads like a limit and grants unrestricted spawn. It must not pass silently.
        body = VALID_AGENT.replace("tools: Read", "tools: Read, Agent(code-reviewer)")
        issues = self._agent_issues(("builder.md", body))
        self.assertTrue(any("does not restrict anything here" in i for i in issues), issues)

    def test_scoped_bash_grant_is_reported_as_a_false_restriction(self) -> None:
        # The Agent(type) branch above had a test; this sibling branch — the one guarding the
        # `Bash(git diff:*)` footgun the read-only guard exists because of — had none, so a
        # refactor could have disarmed it silently.
        body = VALID_AGENT.replace("tools: Read", "tools: Read, Bash(git diff:*)")
        issues = self._agent_issues(("builder.md", body))
        self.assertTrue(any("SILENTLY IGNORES" in i for i in issues), issues)

    def test_scoped_grant_survives_the_comma_split(self) -> None:
        # A naive split(",") shreds `Agent(worker, researcher)` into `Agent(worker` and `researcher)`,
        # which would surface as two bogus "unknown tool" errors instead of the real problem.
        self.assertEqual(
            ["Read", "Agent(worker, researcher)", "Bash"],
            validate_fleet.split_tools("Read, Agent(worker, researcher), Bash"),
        )
        body = VALID_AGENT.replace("tools: Read", "tools: Read, Agent(worker, researcher)")
        issues = self._agent_issues(("builder.md", body))
        self.assertFalse(any("unknown tool" in i for i in issues), issues)

    def test_real_but_unadopted_tool_is_a_policy_error_not_a_schema_error(self) -> None:
        body = VALID_AGENT.replace("tools: Read", "tools: Read, PowerShell")
        issues = [i for i in self._agent_issues(("builder.md", body)) if "PowerShell" in i]
        self.assertTrue(any("not adopted by this fleet" in i for i in issues), issues)
        self.assertFalse(any("is not a Claude Code tool" in i for i in issues), issues)

    def test_adopted_exact_mcp_tool_is_accepted(self) -> None:
        body = VALID_AGENT.replace(
            "tools: Read",
            "tools: Read, ToolSearch, mcp__plugin_githits_githits__pkg_info",
        )
        issues = self._agent_issues(("builder.md", body))
        self.assertFalse(any("tool" in i.lower() and "authority" in i.lower() for i in issues), issues)

    def test_server_wide_mcp_grant_is_rejected_as_drifting_authority(self) -> None:
        # A server wildcard silently acquires every tool added in a future MCP release. GitHits
        # currently exposes a feedback write beside its read-only evidence tools, so broad grant
        # syntax defeats the fleet's "every tool is deliberate authority" policy.
        body = VALID_AGENT.replace(
            "tools: Read",
            "tools: Read, mcp__plugin_githits_githits__*",
        )
        issues = self._agent_issues(("builder.md", body))
        self.assertTrue(any("server-wide MCP grant" in i and "future tools" in i for i in issues), issues)

    def test_tool_unavailable_to_subagents_is_reported(self) -> None:
        body = VALID_AGENT.replace("tools: Read", "tools: Read, AskUserQuestion")
        issues = self._agent_issues(("builder.md", body))
        self.assertTrue(any("never available to a subagent" in i for i in issues), issues)

    def test_retired_tool_names_are_rejected(self) -> None:
        # BashOutput/KillShell/SlashCommand were allowed but appear nowhere in the canonical table.
        for retired in ("BashOutput", "KillShell", "SlashCommand"):
            body = VALID_AGENT.replace("tools: Read", f"tools: Read, {retired}")
            issues = self._agent_issues(("builder.md", body))
            self.assertTrue(any("is not a Claude Code tool" in i for i in issues), (retired, issues))

    def test_unknown_frontmatter_key_is_reported(self) -> None:
        # An unrecognized key is not guaranteed to fail loudly, so a typo silently drops whatever
        # it configured. The key namespace itself is the tripwire.
        body = VALID_AGENT.replace("model: inherit", "hook: PreToolUse\nmodel: inherit")
        issues = self._agent_issues(("builder.md", body))
        self.assertTrue(any("unknown frontmatter key" in i and "'hook'" in i for i in issues), issues)

    def test_known_optional_frontmatter_keys_are_accepted(self) -> None:
        # The documented fields must pass, or the allowlist becomes a false tripwire. `hooks`,
        # `mcpServers`, and `permissionMode` are deliberately NOT here — see the test below.
        extra = "skills: runbook\neffort: high\nisolation: worktree\nmaxTurns: 5\n"
        body = VALID_AGENT.replace("model: inherit", extra + "model: inherit")
        self.assertEqual([], [i for i in self._agent_issues(("builder.md", body)) if "frontmatter key" in i])

    def test_fields_that_a_plugin_silently_ignores_are_rejected(self) -> None:
        # THE bug this whole layout exists to prevent. Claude Code silently ignores `hooks`,
        # `mcpServers`, and `permissionMode` on a plugin-shipped agent. This fleet ships as a
        # plugin, so a `hooks:` block on code-reviewer would look exactly like a read-only guard
        # and be nothing at all — and no test, no load error, and no log would say so.
        for field in ("hooks", "mcpServers", "permissionMode"):
            with self.subTest(field=field):
                body = VALID_AGENT.replace("model: inherit", f"{field}: whatever\nmodel: inherit")
                issues = self._agent_issues(("builder.md", body))
                self.assertTrue(
                    any("SILENTLY IGNORED" in i and repr(field) in i for i in issues), issues
                )

    def test_invalid_agent_name_is_reported(self) -> None:
        # uppercase fails NAME_RE; filename Builder.md keeps name==stem so only the regex branch fires
        body = VALID_AGENT.replace("name: builder", "name: Builder")
        self.assertTrue(any("invalid agent name" in i for i in self._agent_issues(("Builder.md", body))))

    def test_duplicate_agent_names_are_reported(self) -> None:
        second = VALID_AGENT  # both files declare name: builder
        issues = self._agent_issues(("builder.md", VALID_AGENT), ("clone.md", second))
        self.assertTrue(any("duplicate agent names" in i for i in issues))

    def test_missing_agents_directory_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            issues, names = validate_fleet.validate_agents(Path(tmp))
            self.assertEqual([], names)
            self.assertTrue(any("missing agents directory" in i for i in issues))

    # --- skills: list validation (P1-a): `skills` passed KNOWN_AGENT_FIELDS' key-namespace check,
    # but nothing ever validated its VALUES -- a typo'd or dropped entry, or a skill that cannot be
    # preloaded at all, passed silently. ---

    def _agent_issues_with_skills(
        self, agent_file: tuple[str, str], skill_files: dict[str, str]
    ) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            agents = Path(tmp) / "agents"
            agents.mkdir()
            filename, body = agent_file
            (agents / filename).write_text(body, encoding="utf-8")
            for skill_name, skill_body in skill_files.items():
                skill_dir = Path(tmp) / "skills" / skill_name
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(skill_body, encoding="utf-8")
            issues, _ = validate_fleet.validate_agents(Path(tmp))
            return issues

    SKILL_BODY = (
        "---\nname: {name}\ndescription: Use when doing the thing.\n---\n\n# Skill\n"
    )
    DISABLED_SKILL_BODY = (
        "---\nname: {name}\ndescription: Use when doing the thing.\n"
        "disable-model-invocation: true\n---\n\n# Skill\n"
    )

    def test_skills_entry_that_does_not_resolve_is_reported(self) -> None:
        body = VALID_AGENT.replace("model: inherit", "skills:\n  - ghost-skill\nmodel: inherit")
        issues = self._agent_issues_with_skills(("builder.md", body), {})
        self.assertTrue(
            any("'ghost-skill'" in i and "does not resolve" in i for i in issues), issues
        )

    def test_skills_entry_naming_a_model_invocation_disabled_skill_is_reported(self) -> None:
        # A skill with `disable-model-invocation: true` cannot be preloaded ("preloading draws from
        # the same set of skills Claude can invoke") -- listing one under `skills:` is a silent no-op.
        body = VALID_AGENT.replace("model: inherit", "skills:\n  - disabled\nmodel: inherit")
        issues = self._agent_issues_with_skills(
            ("builder.md", body), {"disabled": self.DISABLED_SKILL_BODY.format(name="disabled")}
        )
        self.assertTrue(
            any("'disabled'" in i and "disable-model-invocation" in i for i in issues), issues
        )

    def test_skills_entry_that_resolves_to_a_preloadable_skill_is_accepted(self) -> None:
        body = VALID_AGENT.replace("model: inherit", "skills:\n  - ok\nmodel: inherit")
        issues = self._agent_issues_with_skills(
            ("builder.md", body), {"ok": self.SKILL_BODY.format(name="ok")}
        )
        self.assertEqual([], [i for i in issues if "skills:" in i], issues)


class DocumentedFrontmatterKeysTests(unittest.TestCase):
    """The known-key sets must cover every key the platform documents, as read on a stated date.

    Risk hypothesis: a key added upstream and used in a definition fails the namespace rule as
    "unknown" with no hint that the SET is stale rather than the file. Pinning the documented
    reading here makes a stale set a test failure with the date it was last checked in its name.
    """

    AGENT_KEYS_2026_09_13 = {
        "name", "description", "tools", "disallowedTools", "model", "permissionMode",
        "maxTurns", "skills", "mcpServers", "hooks", "memory", "background", "effort",
        "isolation", "color", "initialPrompt", "experimental",
    }
    SKILL_KEYS_2026_09_13 = {
        "name", "description", "when_to_use", "argument-hint", "arguments",
        "disable-model-invocation", "user-invocable", "allowed-tools", "disallowed-tools",
        "model", "effort", "context", "agent", "background", "hooks", "paths", "shell",
        "metadata", "license", "compatibility",
    }

    def test_known_fields_cover_the_keys_documented_on_2026_09_13(self) -> None:
        # code.claude.com/docs/en/sub-agents and /docs/en/skills, frontmatter tables, CLI 2.1.270.
        self.assertEqual(set(), self.AGENT_KEYS_2026_09_13 - validate_fleet.KNOWN_AGENT_FIELDS)
        self.assertEqual(set(), self.SKILL_KEYS_2026_09_13 - validate_fleet.KNOWN_SKILL_FIELDS)



if __name__ == "__main__":
    unittest.main()
