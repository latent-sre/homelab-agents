"""The host projections: counted rewrites, the TOML emitter, and the generator's `--diff`.

Risk hypothesis: with the per-host prose rewrites moved out of a hand-written `if name == …`
chain and into a table, the table can go stale exactly as the chain did — a canonical sentence
is reworded, a rewrite silently stops matching, and the regenerated adapter keeps a Claude-only
authority claim that the byte-drift check cannot see, because the committed copy was produced
with the same miss. These tests pin the count contract that closes that class, and the round-trip
that keeps a TOML escaping bug from shipping the same way.
"""

from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from fleet.hosts import toml as fleet_toml
from fleet.hosts.rewrites import (
    AT_LEAST_ONE,
    Ledger,
    Rewrite,
    RewriteError,
    apply_rewrites,
    check_table,
)
from fleet.hosts.table import ALL_REWRITES, TEXT_REWRITES
from fleet.references import namespaced_reference_re
from scripts import generate_platform_adapters as generator
from tests.support import REPO, repo_copy, run_main


class RewriteContractTests(unittest.TestCase):
    def test_the_table_is_judgeable(self) -> None:
        # A duplicate id would make two rewrites share one count, so neither could be judged.
        check_table(ALL_REWRITES)
        self.assertEqual(len(ALL_REWRITES), len({rewrite.id for rewrite in ALL_REWRITES}))
        for rewrite in ALL_REWRITES:
            with self.subTest(rewrite=rewrite.id):
                self.assertTrue(rewrite.why.strip(), "a rewrite must say why it exists")

    def test_a_zero_expectation_cannot_be_declared(self) -> None:
        # Zero is the dead rewrite the ledger exists to surface; declaring it would re-open the
        # silent-no-op class the count was added to close.
        with self.assertRaises(RewriteError):
            Rewrite(id="x", why="w", find="a", replace="b", expect=0)
        with self.assertRaises(RewriteError):
            Rewrite(id="x", why="w", find="a", replace="b", expect=-1)
        with self.assertRaises(RewriteError):
            Rewrite(id="x", why="", find="a", replace="b", expect=1)
        with self.assertRaises(RewriteError):
            Rewrite(id="x", why="w", find="a", replace="b", expect=1, hosts=("borg",))

    def test_duplicate_ids_are_refused(self) -> None:
        one = Rewrite(id="same", why="w", find="a", replace="b", expect=1)
        with self.assertRaises(RewriteError):
            check_table([one, one])

    def test_a_pattern_that_matches_nothing_is_reported_as_dead(self) -> None:
        dead = Rewrite(id="dead", why="w", find="never", replace="x", expect=AT_LEAST_ONE)
        ledger = Ledger()
        apply_rewrites("some text", [dead], host="codex", ledger=ledger)
        self.assertIn("matched nothing in the whole fleet", ledger.shortfalls([dead])[0])

    def test_a_mismatch_names_the_repair_its_direction_calls_for(self) -> None:
        # Guessing the direction costs a correction: too few means an anchor was lost, too many
        # usually means a legitimate new occurrence that should be reviewed and counted. A
        # message that said "unintended" either way would send half of them to undo the rewrite.
        rewrite = Rewrite(id="counted", why="the reason", find="a", replace="b", expect=2)
        short = Ledger()
        short.record(rewrite, 1)
        under = short.shortfalls([rewrite])[0]
        self.assertIn("Re-anchor the rewrite", under)
        self.assertNotIn("raise `expect`", under)

        long = Ledger()
        long.record(rewrite, 3)
        over = long.shortfalls([rewrite])[0]
        self.assertIn("raise `expect`", over)
        self.assertNotIn("Re-anchor the rewrite", over)
        for message in (under, over):
            self.assertIn("the reason", message)

    def test_rewrites_run_in_table_order(self) -> None:
        # Order is load-bearing: the fleet's own chain rewrites "its preloaded skills" before a
        # later regex that matches only the rewritten form.
        first = Rewrite(id="first", why="w", find="alpha", replace="beta", expect=1)
        second = Rewrite(id="second", why="w", find="beta", replace="gamma", expect=1)
        self.assertEqual("gamma", apply_rewrites("alpha", [first, second], host="codex"))
        self.assertEqual("beta", apply_rewrites("alpha", [second, first], host="codex"))

    def test_scoping_keeps_a_rewrite_off_other_hosts_and_agents(self) -> None:
        scoped = Rewrite(
            id="scoped",
            why="w",
            find="a",
            replace="b",
            expect=1,
            hosts=("codex",),
            agents=("researcher",),
        )
        self.assertEqual("b", apply_rewrites("a", [scoped], host="codex", agent="researcher"))
        self.assertEqual("a", apply_rewrites("a", [scoped], host="copilot", agent="researcher"))
        self.assertEqual("a", apply_rewrites("a", [scoped], host="codex", agent="code-reviewer"))
        # A skill carries no agent, so an agent-scoped rewrite must never reach it.
        self.assertEqual("a", apply_rewrites("a", [scoped], host="codex"))

    def test_a_host_without_an_honest_statement_is_refused(self) -> None:
        # A per-host replacement reaching a host it has no wording for must fail loudly rather
        # than fall back to the canonical Claude claim.
        partial = Rewrite(
            id="partial", why="w", find="a", replace={"codex": "b"}, expect=1
        )
        with self.assertRaises(RewriteError):
            apply_rewrites("a", [partial], host="copilot")

    def test_the_namespace_projection_uses_the_canonical_matcher(self) -> None:
        # One grammar for a namespaced reference (AGENTS.md, one parser per fact). A second,
        # looser one would rewrite the namespace inside a URL or path; a stricter one would
        # silently skip a malformed reference the validator is meant to reject.
        rewrite = next(r for r in TEXT_REWRITES if r.id == "text.namespace.reference")
        self.assertEqual(namespaced_reference_re("sde-agents").pattern, rewrite.find)
        body = (
            "Run /sde-agents:runbook, hand to sde-agents:code-reviewer, "
            "see https://example.test/sde-agents:code-reviewer"
        )
        codex = apply_rewrites(body, [rewrite], host="codex")
        self.assertIn("Run $runbook", codex)
        self.assertIn("hand to code-reviewer", codex)
        # The URL keeps its path segment: it is not an invocation to translate.
        self.assertIn("https://example.test/sde-agents:code-reviewer", codex)
        self.assertIn("Run /runbook", apply_rewrites(body, [rewrite], host="copilot"))

    def test_a_literal_replacement_is_never_read_as_a_group_reference(self) -> None:
        # Honest prose contains backslashes; a replacement passed to re.sub as a template would
        # corrupt them or raise.
        rewrite = Rewrite(
            id="literal", why="w", find=r"x+", replace=r"a\1b\\c", expect=1, regex=True
        )
        self.assertEqual(r"a\1b\\c", apply_rewrites("xxx", [rewrite], host="codex"))


class FleetRewriteCountTests(unittest.TestCase):
    def test_every_rewrite_lands_the_count_the_table_declares(self) -> None:
        # The live invariant: generation over the real fleet must match the table exactly. A
        # failure here names the canonical sentence that moved.
        generator.expected_outputs(REPO)

    def test_a_reworded_canonical_sentence_fails_generation(self) -> None:
        # The whole point of the phase. Without the count, this mutation regenerates a
        # clean-looking adapter that still names Claude's Agent tool to a host that has none.
        anchor = next(r for r in TEXT_REWRITES if r.id == "text.agent-tool.spawn")
        with repo_copy() as dst:
            carriers = [
                path
                for path in sorted((dst / "agents").glob("*.md"))
                if anchor.find in path.read_text(encoding="utf-8")
            ]
            self.assertTrue(carriers, "the anchor must exist somewhere to be worth counting")
            for path in carriers:
                path.write_text(
                    path.read_text(encoding="utf-8").replace(
                        anchor.find, "Use the subagent mechanism to spawn"
                    ),
                    encoding="utf-8",
                )
            with self.assertRaises(RewriteError) as caught:
                generator.expected_outputs(dst)
        message = str(caught.exception)
        self.assertIn("text.agent-tool.spawn", message)
        self.assertIn("landed 0 time(s)", message)
        self.assertIn(anchor.why, message)


    def test_a_reworded_read_only_skill_claim_fails_generation(self) -> None:
        # A skill body that credits `disallowed-tools` with removing Write and Edit names a deny
        # the portable frontmatter drops, so the projection is as load-bearing as any agent's —
        # and so is its count.
        anchor = "All checks are read-only. `disallowed-tools` removes Write and Edit"
        with repo_copy() as dst:
            carriers = [
                path
                for path in sorted((dst / "skills").rglob("SKILL.md"))
                if anchor in path.read_text(encoding="utf-8")
            ]
            self.assertTrue(carriers, "the anchor must exist somewhere to be worth counting")
            for path in carriers:
                path.write_text(
                    path.read_text(encoding="utf-8").replace(
                        anchor, "All checks are read-only. The deny list removes Write and Edit"
                    ),
                    encoding="utf-8",
                )
            with self.assertRaises(RewriteError) as caught:
                generator.expected_outputs(dst)
        self.assertIn("skill.readonly.disallowed-tools-claim", str(caught.exception))


    def test_a_read_only_claim_outside_the_deny_frontmatter_still_fails_generation(self) -> None:
        # Gating the projection on `disallowed-tools` let a skill that acquired the claim
        # without the field skip the table entirely: the ledger's count stayed satisfied by the
        # skills that do carry it, and both adapters shipped the false deny unchanged.
        claim = (
            "All checks are read-only. `disallowed-tools` removes Write and Edit while this "
            "skill is active,\nbut Bash can still mutate things.\n"
        )
        with repo_copy() as dst:
            target = dst / "skills" / "backend-craft" / "SKILL.md"
            self.assertNotIn(
                "disallowed-tools", target.read_text(encoding="utf-8"),
                "the fixture skill must not carry the frontmatter field",
            )
            target.write_text(
                target.read_text(encoding="utf-8") + "\n\n" + claim, encoding="utf-8"
            )
            with self.assertRaises(RewriteError) as caught:
                generator.expected_outputs(dst)
        message = str(caught.exception)
        self.assertIn("skill.readonly.disallowed-tools-claim", message)
        self.assertIn("landed 6 time(s)", message)


class TomlEmitterTests(unittest.TestCase):
    def test_a_document_reads_back_as_written(self) -> None:
        text = fleet_toml.render_document(
            [
                ("name", 'quotes " and \\ backslash'),
                ("description", "em dash — kept as itself"),
                ("developer_instructions", fleet_toml.Multiline("line one\nline two\n")),
            ],
            comment="generated",
        )
        self.assertTrue(text.startswith("# generated\n"))
        self.assertEqual(
            {
                "name": 'quotes " and \\ backslash',
                "description": "em dash — kept as itself",
                "developer_instructions": "line one\nline two\n",
            },
            tomllib.loads(text),
        )

    def test_a_value_the_delimiter_cannot_hold_is_refused(self) -> None:
        for value in ("has ''' inside", "ends with a quote'", "carriage\rreturn", "bell\x07"):
            with self.subTest(value=value):
                with self.assertRaises(fleet_toml.TomlEmitError):
                    fleet_toml.render_document([("k", fleet_toml.Multiline(value))])

    def test_a_duplicate_or_unquotable_key_is_refused(self) -> None:
        with self.assertRaises(fleet_toml.TomlEmitError):
            fleet_toml.render_document([("k", "a"), ("k", "b")])
        with self.assertRaises(fleet_toml.TomlEmitError):
            fleet_toml.render_document([("has space", "a")])

    def test_the_round_trip_catches_an_escaping_bug(self) -> None:
        # Mutation: an emitter that forgot to escape a quote still produces plausible TOML, so
        # the parse-back is the only thing standing between that bug and a shipped adapter.
        original = fleet_toml.basic_string
        try:
            fleet_toml.basic_string = lambda value: f'"{value}"'
            with self.assertRaises(fleet_toml.TomlEmitError):
                fleet_toml.render_document([("name", 'a " quote')])
        finally:
            fleet_toml.basic_string = original

    def test_a_valid_but_semantically_wrong_document_is_rejected(self) -> None:
        # The escaping mutation above exits through the parse error, so without this the
        # equality branch is an untested guard: it would read as enforcement while enforcing
        # nothing, which is the exact failure the round-trip exists to prevent.
        original = fleet_toml.basic_string
        try:
            # Valid TOML, wrong value — the only thing that reaches the comparison.
            fleet_toml.basic_string = lambda value: json.dumps(value + " (mangled)")
            with self.assertRaises(fleet_toml.TomlEmitError) as caught:
                fleet_toml.render_document([("name", "code-reviewer")])
        finally:
            fleet_toml.basic_string = original
        self.assertIn("did not read back as written", str(caught.exception))
        self.assertIn("name", str(caught.exception))

    def test_the_committed_codex_adapters_parse(self) -> None:
        agents = sorted((REPO / ".codex" / "agents").glob("*.toml"))
        self.assertTrue(agents)
        for path in agents:
            with self.subTest(path=path.name):
                parsed = tomllib.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(path.stem, parsed["name"])
                self.assertIn(parsed["sandbox_mode"], {"read-only", "workspace-write"})
                self.assertTrue(parsed["developer_instructions"].endswith("\n"))


class GeneratorDiffTests(unittest.TestCase):
    def test_diff_reports_nothing_on_a_current_tree(self) -> None:
        self.assertEqual([], generator.diff_generated_outputs(REPO))
        code, out = run_main(generator.main, "--diff", "--root", str(REPO))
        self.assertEqual(0, code, out)
        self.assertIn("match the canonical fleet", out)

    def test_diff_shows_the_projected_change_and_writes_nothing(self) -> None:
        with repo_copy() as dst:
            agent = dst / "agents" / "researcher.md"
            before = (dst / ".codex" / "agents" / "researcher.toml").read_bytes()
            agent.write_text(
                agent.read_text(encoding="utf-8").replace(
                    "External-source investigator", "External-source sleuth", 1
                ),
                encoding="utf-8",
            )
            report = generator.diff_generated_outputs(dst)
            code, out = run_main(generator.main, "--diff", "--root", str(dst))
            self.assertEqual(
                before, (dst / ".codex" / "agents" / "researcher.toml").read_bytes()
            )
        self.assertEqual(1, code, out)
        joined = "\n".join(report)
        self.assertIn(".codex/agents/researcher.toml", joined)
        self.assertIn("+description", joined)
        self.assertIn("External-source sleuth", joined)


    def test_diff_reports_a_change_that_has_no_visible_lines(self) -> None:
        # A stripped final newline and a CRLF rewrite both leave every line's content equal, so
        # a line-based diff renders nothing; reporting nothing would let `--diff` exit 0 on a
        # tree `--write` would still rewrite.
        target = Path(".github") / "agents" / "researcher.agent.md"
        for label, mutate in (
            ("final newline", lambda data: data.rstrip(b"\n")),
            ("CRLF", lambda data: data.replace(b"\n", b"\r\n")),
        ):
            with self.subTest(change=label), repo_copy() as dst:
                path = dst / target
                path.write_bytes(mutate(path.read_bytes()))
                report = generator.diff_generated_outputs(dst)
                code, out = run_main(generator.main, "--diff", "--root", str(dst))
            self.assertEqual(1, code, out)
            self.assertTrue(report, f"a {label} difference must not render as nothing")
            self.assertIn("same lines, different bytes", report[0])
            self.assertIn(target.as_posix(), report[0])

    def test_diff_reports_a_retired_root_that_write_would_delete(self) -> None:
        # Deleting the retired trees is the only destructive part of `--write`, and they appear
        # in no expected-output map, so the preview has to name them itself.
        with repo_copy() as dst:
            retired = dst / "platforms" / "portable"
            retired.mkdir(parents=True)
            (retired / "stale.md").write_text("x", encoding="utf-8")
            report = generator.diff_generated_outputs(dst)
            code, _ = run_main(generator.main, "--diff", "--root", str(dst))
            self.assertTrue((retired / "stale.md").is_file(), "--diff must not write")
        self.assertEqual(1, code)
        self.assertIn("retired generated root", "\n".join(report))
        self.assertIn("platforms/portable/stale.md", "\n".join(report))


    def test_a_retired_root_that_is_a_file_previews_and_removes_cleanly(self) -> None:
        # `rglob` finds nothing in a regular file, so the preview promised a zero-file removal
        # while `--write` aborted on the same path with NotADirectoryError.
        with repo_copy() as dst:
            retired = dst / "platforms" / "portable"
            retired.parent.mkdir(parents=True, exist_ok=True)
            retired.write_text("not a directory", encoding="utf-8")
            report = generator.diff_generated_outputs(dst)
            self.assertIn(
                "--- platforms/portable: retired generated root is a file, "
                "would be removed by --write",
                report,
            )
            self.assertTrue(retired.exists(), "--diff must not write")
            generator.write_generated_outputs(dst)
            self.assertFalse(retired.exists(), "--write must clear the retired root it promised")


class GeneratedTreeTests(unittest.TestCase):
    def test_no_generated_adapter_carries_a_claude_only_path(self) -> None:
        # The rewrites translate these forms; this is the reader check that holds whether or not
        # a given translation is still in the table.
        roots = (
            REPO / ".github" / "agents",
            REPO / ".codex" / "agents",
            REPO / ".github" / "skills",
            REPO / "plugins" / "sde-agents" / "skills",
        )
        reference = Path("prompt-craft/references/claude-code-frontmatter.md")
        for root in roots:
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.suffix not in {".md", ".toml"}:
                    continue
                if path.as_posix().endswith(reference.as_posix()):
                    continue  # copied verbatim on purpose: it documents Claude's own contract
                with self.subTest(path=path.relative_to(REPO)):
                    self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
