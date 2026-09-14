"""Offline tests for scripts/eval_routing.py — the thin layer over `claude plugin eval`.

The measurement's live arm belongs to the platform now. What is testable offline, and must be,
is everything the fleet still decides: which runs count as measurements, what the stored artifact
says, the native flags the measurement depends on, and the cluster files themselves.

The grading semantics moved with the reader into `tests/test_fleet_routing.py`, and the identity
rules into `tests/test_fleet_provenance.py`.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fleet import fs as fs_module
from scripts import eval_routing
from tests.support import REPO


def trace(*events: dict) -> str:
    return "\n".join(json.dumps(event) for event in events)


def call(name: str, tool_id: str, **inputs) -> dict:
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tool_id, "name": name, "input": inputs}]}}


def result_event(is_error: bool = False, model: str = "claude-sonnet-5") -> dict:
    return {"type": "result", "is_error": is_error, "model": model, "duration_ms": 5}


class FiredPerRunTest(unittest.TestCase):
    """Which runs count as measurements — the rule that decides whether a rate means anything.

    A measurement failure and a routing failure are different facts. Scoring the first as the
    second greens negatives vacuously (no transcript is not evidence that nothing fired) and drops
    misses out of a positive's denominator, turning mostly-wrong routing into a PASS.
    """

    ROSTER = frozenset({"root-cause", "lab-audit", "code-reviewer"})

    def _run(self, text: str, error: str | None = None) -> dict:
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        handle.write(text)
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return {"tracePath": handle.name, "error": error}

    def test_a_completed_session_that_routed_nowhere_is_a_measurement(self) -> None:
        """Silence from a session that FINISHED is a real observation: a genuine miss on a
        positive, a genuine pass on a negative."""
        fired, notes, _, _ = eval_routing.fired_per_run(
            [self._run(trace(result_event()))], self.ROSTER
        )
        self.assertEqual([frozenset()], fired)
        self.assertEqual([], notes)

    def test_a_run_cut_at_its_turn_limit_is_still_graded_when_it_routed(self) -> None:
        """The harness reports a turn-limit cut as an error, but that trace carries the decision.

        Treating every harness error as an invalid run made the first end-to-end measurement
        report INCONCLUSIVE on a case whose trace was perfectly readable.
        """
        fired, notes, _, _ = eval_routing.fired_per_run(
            [self._run(
                trace(call("Skill", "s1", command="sde-agents:root-cause")),
                error="exit 1: Reached maximum number of turns (6)",
            )],
            self.ROSTER,
        )
        self.assertEqual([frozenset({"root-cause"})], fired)
        self.assertIn("graded despite", notes[0], "trouble on a graded run must stay visible")

    def test_an_unfinished_session_that_routed_nowhere_is_not_a_measurement(self) -> None:
        """Its silence is not a decision, only an unfinished one."""
        fired, notes, _, _ = eval_routing.fired_per_run(
            [self._run(trace(call("Read", "r1", file_path="x")), error="timed out")], self.ROSTER
        )
        self.assertEqual([None], fired)
        self.assertIn("no usable transcript", notes[0])

    def test_an_error_result_cannot_green_a_negative(self) -> None:
        """A session that ended in an error decided nothing, whatever its exit status."""
        fired, _notes, _, _ = eval_routing.fired_per_run(
            [self._run(trace(result_event(is_error=True)))], self.ROSTER
        )
        self.assertEqual([None], fired)

    def test_a_firing_before_an_error_result_is_still_evidence(self) -> None:
        """The component call was observed; only the silence afterwards is uninterpretable."""
        fired, _notes, _, _ = eval_routing.fired_per_run(
            [self._run(trace(
                call("Agent", "a1", subagent_type="sde-agents:code-reviewer"),
                result_event(is_error=True),
            ))],
            self.ROSTER,
        )
        self.assertEqual([frozenset({"code-reviewer"})], fired)

    def test_an_unreadable_trace_is_an_invalid_run_whatever_the_harness_said(self) -> None:
        """There is nothing left to grade, so it cannot be scored in either direction."""
        fired, notes, _, _ = eval_routing.fired_per_run(
            [{"tracePath": "/nonexistent/trace.jsonl", "error": None}], self.ROSTER
        )
        self.assertEqual([None], fired)
        self.assertIn("trace unreadable", notes[0])

    def test_the_model_is_read_off_the_transcript_not_the_request(self) -> None:
        """An artifact that records what was ASKED for cannot be validly diffed against another:
        the runs a conditions block exists to describe are the pinned ones, where the two agree."""
        _fired, _notes, models, _surfaces = eval_routing.fired_per_run(
            [self._run(trace({"type": "assistant", "message": {"model": "claude-opus-5",
                                                               "content": []}}, result_event()))],
            self.ROSTER,
        )
        self.assertEqual(["claude-opus-5"], models)


class ScoredArtifactTest(unittest.TestCase):
    """A surprising verdict must be explicable from the stored artifact, not by re-running."""

    MEMBERS = ["root-cause", "lab-audit"]
    ROSTER = frozenset({"root-cause", "lab-audit", "backend-craft"})

    def _init(self, *names: str) -> dict:
        """A session `init` event registering these components, namespaced as the CLI lists them.

        Every fixture trace carries one: a run whose session never registered the graded
        components cannot evidence that they did not fire, so `_scored` now excludes it. Without
        an init event these fixtures would exercise that exclusion instead of the scoring they are
        written for.
        """
        return {"type": "system", "subtype": "init",
                "agents": [], "skills": [f"sde-agents:{n}" for n in names]}

    def _scored(self, case: dict, *traces: str | None, threshold: float = 0.5) -> dict:
        runs = []
        for text in traces:
            if text is None:
                runs.append({"tracePath": "/nonexistent", "error": "run failed"})
                continue
            handle = tempfile.NamedTemporaryFile(
                "w", suffix=".jsonl", delete=False, encoding="utf-8"
            )
            handle.write(text)
            handle.close()
            self.addCleanup(Path(handle.name).unlink, missing_ok=True)
            runs.append({"tracePath": handle.name, "error": None})
        return eval_routing._scored(case, self.MEMBERS, runs, self.ROSTER, threshold)

    def test_per_run_firings_are_recorded_for_audit(self) -> None:
        case = {"id": "n", "polarity": "negative", "expect_not_fires": list(self.MEMBERS)}
        entry = self._scored(
            case,
            trace(self._init(*self.MEMBERS), result_event()),
            trace(self._init(*self.MEMBERS),
                  call("Skill", "s1", command="root-cause"), result_event()),
        )
        self.assertEqual([[], ["root-cause"]], entry["fired_per_run"])
        self.assertFalse(entry["passed"], "one over-trigger fails a negative")

    def test_a_component_outside_the_cluster_is_reported_as_a_diagnostic(self) -> None:
        """A negative correctly landing elsewhere is the useful half of the result."""
        case = {"id": "n", "polarity": "negative", "expect_not_fires": list(self.MEMBERS)}
        entry = self._scored(
            case, trace(self._init(*self.MEMBERS, "backend-craft"),
                        call("Skill", "s1", command="backend-craft"), result_event())
        )
        self.assertTrue(entry["passed"])
        self.assertEqual(["backend-craft"], entry["also_fired"])

    def test_an_excluded_run_is_named_in_the_detail_and_not_in_the_rate(self) -> None:
        case = {"id": "p", "polarity": "positive", "expect_fires": ["root-cause"]}
        entry = self._scored(
            case,
            trace(self._init(*self.MEMBERS),
                  call("Skill", "s1", command="root-cause"), result_event()),
            None,
        )
        self.assertTrue(entry["passed"], entry["detail"])  # 1/1 valid, not 1/2
        self.assertEqual(1, entry["runs_excluded"])
        self.assertIn("excluded", entry["detail"])

    def test_a_case_with_no_valid_run_says_INCONCLUSIVE_and_does_not_pass(self) -> None:
        for polarity, extra in (("positive", {"expect_fires": ["root-cause"]}),
                                ("negative", {"expect_not_fires": ["root-cause"]})):
            with self.subTest(polarity=polarity):
                entry = self._scored({"id": "c", "polarity": polarity, **extra}, None, None)
                self.assertTrue(entry["inconclusive"])
                self.assertFalse(entry["passed"])
                self.assertIn("INCONCLUSIVE", entry["detail"])

    def test_a_negative_detail_names_what_was_actually_forbidden(self) -> None:
        """A narrowed negative graded against the whole cluster once failed for a sibling doing
        the right thing; the detail has to say which set the verdict used."""
        entry = self._scored(
            {"id": "n", "polarity": "negative", "expect_not_fires": ["lab-audit"]},
            trace(self._init(*self.MEMBERS),
                  call("Skill", "s1", command="root-cause"), result_event()),
        )
        self.assertTrue(entry["passed"])
        self.assertIn("lab-audit", entry["detail"])
        entry = self._scored(
            {"id": "n", "polarity": "negative"}, trace(self._init(*self.MEMBERS), result_event())
        )
        self.assertIn("cluster", entry["detail"], "a broad negative says so")


class NativeCommandTest(unittest.TestCase):
    """The native flags this measurement depends on, rather than whatever the defaults become."""

    def _command(self, **overrides) -> list[str]:
        args = eval_routing._parser().parse_args([])
        for key, value in overrides.items():
            setattr(args, key, value)
        return eval_routing.native_command(
            Path("/plugin"), "evals/generated/c", Path("/r.json"), args
        )

    def test_keep_temp_is_always_passed(self) -> None:
        """Load-bearing, not a debugging convenience: without it the trace is deleted before the
        result document that names it can be read, and there is nothing to grade."""
        self.assertIn("--keep-temp", self._command())

    def test_the_native_threshold_is_zero_so_the_exit_code_is_ours(self) -> None:
        """The native score comes from tripwire graders that are not the verdict; letting it decide
        the exit would report a routing result this measurement never computed."""
        command = self._command()
        self.assertEqual("0", command[command.index("--threshold") + 1])

    def test_the_baseline_arm_is_off(self) -> None:
        """A no-plugin arm cannot route to a fleet component by construction."""
        command = self._command()
        self.assertEqual("none", command[command.index("--ablation") + 1])

    def test_a_requested_model_is_passed_through_and_absent_otherwise(self) -> None:
        self.assertNotIn("--model", self._command())
        command = self._command(model="opus")
        self.assertEqual("opus", command[command.index("--model") + 1])

    def test_a_cost_ceiling_is_passed_through_only_when_set(self) -> None:
        self.assertNotIn("--max-cost-usd", self._command())
        self.assertIn("--max-cost-usd", self._command(max_cost_usd=5))


class WriteCasesTest(unittest.TestCase):
    def test_a_stale_case_directory_is_replaced_rather_than_merged(self) -> None:
        """A case removed from the cluster must disappear from the measurement. Merging would
        leave it on disk to be run and scored as if the cluster still declared it."""
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = Path(tmp) / "generated"
            spec = {"cluster": "demo"}
            eval_routing.write_cases(eval_dir, {"old-case/prompt.md": "old"}, spec)
            self.assertTrue((eval_dir / "old-case" / "prompt.md").exists())
            eval_routing.write_cases(eval_dir, {"new-case/prompt.md": "new"}, spec)
            self.assertFalse((eval_dir / "old-case" / "prompt.md").exists())
            self.assertTrue((eval_dir / "new-case" / "prompt.md").exists())

    def test_the_generated_tree_says_what_produced_it(self) -> None:
        """It is git-ignored and disposable, so whoever finds one needs it to say so before they
        trust or edit it."""
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = Path(tmp) / "generated"
            eval_routing.write_cases(eval_dir, {"c/prompt.md": "x"}, {"cluster": "demo"})
            manifest = json.loads((eval_dir / "GENERATED.json").read_text(encoding="utf-8"))
            self.assertEqual("demo", manifest["cluster"])
            self.assertIn("never this directory", manifest["warning"])


class RemoveKeptTempDirsTest(unittest.TestCase):
    def test_only_the_harness_own_directories_are_removed(self) -> None:
        """`--keep-temp` leaves a directory the harness says it could not seal, holding a copy of
        the plugin under test. Leaving it is a disclosure; removing the wrong one is worse."""
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "claude-eval-abc123" / "out"
            harness.mkdir(parents=True)
            (harness / "trace.jsonl").write_text("{}", encoding="utf-8")
            other = Path(tmp) / "someone-elses-dir" / "out"
            other.mkdir(parents=True)
            (other / "trace.jsonl").write_text("{}", encoding="utf-8")
            eval_routing._remove_kept_temp_dirs({
                "a": [{"tracePath": str(harness / "trace.jsonl")}],
                "b": [{"tracePath": str(other / "trace.jsonl")}],
            })
            self.assertFalse(harness.parent.exists())
            self.assertTrue(other.parent.exists(), "a path outside the harness's own naming")


class CliValidationTest(unittest.TestCase):
    def test_cli_rejects_zero_threshold_before_reading_or_running(self) -> None:
        self._assert_invalid_threshold("0")

    def test_cli_rejects_threshold_above_one_before_reading_or_running(self) -> None:
        self._assert_invalid_threshold("1.01")

    def _assert_invalid_threshold(self, threshold: str) -> None:
        stderr = io.StringIO()
        with (
            mock.patch.object(eval_routing, "CLAUDE", "claude"),
            mock.patch.object(
                eval_routing.provenance,
                "_read_regular_file",
                side_effect=AssertionError("invalid threshold reached cluster loading"),
            ),
            contextlib.redirect_stderr(stderr),
        ):
            code = eval_routing.main(["--threshold", threshold])
        self.assertEqual(2, code)
        self.assertIn("--threshold must be > 0 and <= 1", stderr.getvalue())


class ConditionsTest(unittest.TestCase):
    def test_plugin_dir_inside_repo_is_recorded_repo_relative(self) -> None:
        # Recorded verbatim, the default plugin_dir (this repo, absolute) commits the operator's
        # local filesystem layout into a baseline artifact — identity noise that makes identical
        # measurements from two machines diff.
        self.assertEqual(".", eval_routing.plugin_dir_label(REPO))
        self.assertEqual("agents", eval_routing.plugin_dir_label(REPO / "agents"))

    def test_external_plugin_dir_is_redacted_to_a_stable_label(self) -> None:
        # The measured plugin identity is already hashed separately, so keeping a workstation path
        # here only leaks local layout into committed artifacts without adding provenance.
        outside = Path(REPO.anchor) / "somewhere-else"
        self.assertEqual("<external-plugin-dir>", eval_routing.plugin_dir_label(outside))


class CaseFileTest(unittest.TestCase):
    def test_seed_cluster_is_well_formed(self) -> None:
        path = REPO / "evals" / "routing" / "prompt-tooling.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        members = set(spec["members"])
        self.assertTrue(
            members <= eval_routing.FLEET, "cluster members must be real fleet components"
        )
        ids = [c["id"] for c in spec["cases"]]
        self.assertEqual(len(ids), len(set(ids)), "case ids must be unique")
        for case in spec["cases"]:
            self.assertIn(case["polarity"], ("positive", "negative"), case["id"])
            if case["polarity"] == "positive":
                self.assertTrue(set(case["expect_fires"]) <= members, case["id"])

    def test_every_negative_forbids_only_cluster_members(self) -> None:
        # A negative is graded against its own `expect_not_fires`, so a name that is not a cluster
        # member forbids nothing and the case passes vacuously — silently, and across every cluster.
        import json
        for path in sorted((REPO / "evals" / "routing").glob("*.json")):
            spec = json.loads(path.read_text(encoding="utf-8"))
            members = set(spec["members"])
            for case in spec["cases"]:
                if case["polarity"] != "negative":
                    continue
                forbidden = set(case.get("expect_not_fires", members))
                self.assertTrue(forbidden <= members,
                                f"{path.name}:{case['id']} forbids non-members "
                                f"{sorted(forbidden - members)} — they can never fire, so the case "
                                f"would pass without measuring anything")
                self.assertTrue(forbidden, f"{path.name}:{case['id']} forbids nothing")

    # A prompt that points at something must carry it. Every run executes in a fresh empty working
    # directory, so "here are the findings" with no findings makes the CORRECT behavior — asking for
    # the missing artifact — score as a routing miss.
    _DEICTIC = re.compile(
        r"\b(?:here (?:are|is) (?:the|my|one)|this (?:change|diff|branch|PR|patch)\b"
        r"|the attached|below\b)",
        re.IGNORECASE,
    )
    # What "carrying the referent" looks like: enough prose to BE the artifact, or a structural
    # marker that one is inlined.
    _CARRIES = ("```", "diff --git", "@@", "PR #", "DRAFT", "FINDINGS")

    # Words that mark a case reference as historical. A note may name a retired case — explaining
    # what stopped being covered is better than deleting the sentence — but it has to SAY so.
    _RETIREMENT_WORDS = re.compile(
        r"retir\w*|remov\w*|deleted|no longer|uncovered|historical|past tense|used to|"
        r"was asserted|cut on|left with",
        re.IGNORECASE,
    )
    _CASE_REF = re.compile(r"\b((?:pos|neg)-[a-z0-9]+(?:-[a-z0-9]+)*)(-\*)?\b")

    def test_cluster_prose_does_not_present_a_deleted_case_as_live_coverage(self) -> None:
        """Risk: a retirement deletes the cases and leaves the prose vouching for them.

        `craft-vs-fullstack` said its load-bearing assertion was that cross-layer work routes to
        sde-fullstack "(pos-fullstack-*)" — cases this PR retired. `ladder` said
        `pos-builder-scoped`
        guards an over-trigger it no longer guards. A later description review reading either note
        would treat that reachability as covered and skip measuring it, which is the same silent
        failure as a doc that still lists landed work as pending.

        A note MAY name a retired case; it may not imply the case is live. So a reference to an id
        that no longer exists must sit within the same sentence as a retirement word.
        """
        clusters = sorted((REPO / "evals" / "routing").glob("*.json"))
        existing = {
            case["id"]
            for path in clusters
            for case in json.loads(path.read_text(encoding="utf-8"))["cases"]
        }
        stale = []
        for path in clusters:
            spec = json.loads(path.read_text(encoding="utf-8"))
            prose = [value for value in spec.values() if isinstance(value, str)]
            prose += [case.get("expected_output", "") or "" for case in spec["cases"]]
            for text in prose:
                for sentence in re.split(r"(?<=[.;])\s+", text):
                    if self._RETIREMENT_WORDS.search(sentence):
                        continue
                    for stem, glob_suffix in self._CASE_REF.findall(sentence):
                        # `pos-foo-*` is satisfied by any surviving id under that stem.
                        alive = (
                            any(name.startswith(stem) for name in existing)
                            if glob_suffix else stem in existing
                        )
                        if not alive:
                            stale.append(f"{path.name}: {stem}{glob_suffix} in {sentence[:70]!r}")
        self.assertEqual(
            [], stale,
            "cluster prose names a case that no longer exists without saying it retired; a future "
            "description review will read that as live coverage and skip measuring it",
        )

    def test_no_prompt_points_at_an_artifact_it_does_not_carry(self) -> None:
        """Risk: a case measures the harness's empty cwd instead of the description.

        `evals/README.md` claims this class is empty. It was not, twice: PR #145 retired seven such
        cases and inlined two, then ADDED `pos-engladder-growth-feedback` saying "here are the last
        six months of pull requests" with none attached — and the sweep that found it also turned up
        `pos-iterate-draft`, which predates the branch. A claim of emptiness in prose is worth what
        the last person's grep was worth; this makes it worth what the tree says.
        """
        bare = []
        for path in sorted((REPO / "evals" / "routing").glob("*.json")):
            for case in json.loads(path.read_text(encoding="utf-8"))["cases"]:
                prompt = case["prompt"]
                match = self._DEICTIC.search(prompt)
                if match and len(prompt) <= 500 and not any(m in prompt for m in self._CARRIES):
                    bare.append(f"{path.name}:{case['id']} ({match.group(0)!r})")
        self.assertEqual(
            [], bare,
            "prompt(s) refer to an artifact they do not supply; every run starts in an empty "
            "directory, so the correct 'send me the artifact' answer scores as a routing miss — "
            "inline a representative artifact the way pos-engladder-assess does",
        )

    def test_readme_inventory_figures_match_the_shipped_suites(self) -> None:
        """Risk: a case lands or leaves and the prose that sizes the suite quietly stops being true.

        These are not decorative numbers — an operator reads them to decide whether a paid sweep is
        affordable, and a future session reads the narrowing fraction to judge how much over-trigger
        coverage the suite still has. Both were wrong at once in PR #145: three far-miss retirements
        left the narrowing denominator at 65 against an actual 62, and a merge took the behavioral
        count to 70 while the prose still said 69 and "64 of the 69" (wrong on both halves). Two
        review rounds were spent correcting figures by hand; this is the check that makes the third
        unnecessary.

        Each row asserts its regex MATCHED as well as what it captured, so rewording the sentence
        fails loudly instead of silently skipping the assertion.
        """
        readme = (REPO / "evals" / "README.md").read_text(encoding="utf-8")
        clusters = sorted((REPO / "evals" / "routing").glob("*.json"))
        positives = negatives = narrowed = 0
        for path in clusters:
            spec = json.loads(path.read_text(encoding="utf-8"))
            members = set(spec["members"])
            for case in spec["cases"]:
                if case["polarity"] == "positive":
                    positives += 1
                    continue
                negatives += 1
                if case.get("expect_not_fires") and set(case["expect_not_fires"]) != members:
                    narrowed += 1
        # The baselines inventory is quoted in the same file and drifted the same way — it was
        # written once after the retirement commits and not recomputed after the later ones, so it
        # claimed 9,262 lines across 20 directories against an actual 9,378 across 13. An operator
        # reads these to judge whether the cleanup did what it says (PR #145 review).
        baselines = REPO / "evals" / "baselines"
        # NEWLINE counts, matching `wc -l`, over every file in the directory. The first version of
        # this check used `splitlines()`, which adds one for a file with no trailing newline, so it
        # agreed with itself and disagreed with the tree by 16 lines — a check bound to a
        # computation no reader would run is not a check (PR #145 round 16). The README states the
        # exact command beside the figure for the same reason.
        def newline_count(paths) -> int:
            return sum(path.read_bytes().count(b"\n") for path in paths if path.is_file())

        # Count what git ships, not what this machine holds: the README's reproduce command is
        # `git ls-files ... | wc -l`, and a raw rglob also counts gitignored artifacts (the
        # behavioral runner's failing-run-evidence.json sidecars live beside committed benchmarks
        # by design), so a local run overstated the figure by 2,244 lines and shipped it in a
        # commit CI then failed (PR #156). --others --exclude-standard keeps pre-commit runs
        # honest about files that are about to be committed.
        tracked = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z",
             "evals/baselines"],
            capture_output=True, check=True, cwd=REPO,
        ).stdout.decode("utf-8")
        shipped = [REPO / name for name in tracked.split("\0") if name]
        baseline_lines = newline_count(shipped)
        baseline_dirs = len([path for path in baselines.iterdir() if path.is_dir()])
        # Every file under history/, not just Markdown: the restored tool-event evidence is part of
        # the distilled record it sits beside.
        history = baselines / "history"
        summary_lines = newline_count(p for p in shipped if history in p.parents)

        rows = (
            (r"\*\*(\d+)\*\* of (\d+) negatives narrow", (narrowed, negatives)),
            (r"(\d+) routing cases across the ten clusters \((\d+) positives, (\d+)",
             (positives + negatives, positives, negatives)),
            (r"is \*\*(\d+) sessions\*\*", ((positives + negatives) * 3,)),
            (r"\*\*([\d,]+) lines across (\d+) top-level directories\*\*",
             (f"{baseline_lines:,}", baseline_dirs)),
            (r"What remains: ([\d,]+) lines of distilled record", (f"{summary_lines:,}",)),
        )
        for pattern, expected in rows:
            found = re.search(pattern, readme)
            with self.subTest(pattern=pattern):
                self.assertIsNotNone(
                    found,
                    "evals/README.md no longer states this figure in the shape this test reads; "
                    "reword the test with the prose, do not delete the assertion",
                )
                self.assertEqual(
                    tuple(str(value) for value in expected), found.groups(),
                    "evals/README.md figure is stale against the shipped suites",
                )

    def test_coverage_table_lists_every_cluster_file(self) -> None:
        readme = (REPO / "evals" / "README.md").read_text(encoding="utf-8")
        missing = [
            path.name
            for path in sorted((REPO / "evals" / "routing").glob("*.json"))
            if f"`{path.name}`" not in readme
        ]
        self.assertEqual(
            [],
            missing,
            "evals/README.md omits routing clusters, so operators can silently skip shipped evals",
        )

if __name__ == "__main__":
    unittest.main()


class MainIntegrationTest(unittest.TestCase):
    """`main` end to end with the native harness mocked out.

    The pieces are covered individually elsewhere; what is only testable here is the WIRING --
    that the benchmark is written with complete provenance, and that the two guards which refuse
    to write one actually fire. A guard nothing exercises reads as enforcement while enforcing
    nothing, which is the failure this repository keeps finding.
    """

    PROMPT = "Tighten this tool description so it only fires for PDF form extraction."

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.cluster = self.tmp / "demo.json"
        self._write_cluster(["prompt-craft"])
        # Recorded so a test can assert a session was never launched, and so a per-run trace list
        # can stand in for a batch whose runs differed (a mixed-model batch, say).
        self.launched: list[list[str]] = []
        self.trace = self.tmp / "trace.jsonl"
        # The init event is part of the fixture because the conditions block reads the routing
        # competition off it; without one the components_observed assertion below would pass on
        # an empty dict and prove nothing.
        self.trace.write_text(trace(
            {"type": "system", "subtype": "init",
             "agents": ["sde-agents:prompt-engineer", "general-purpose"],
             "skills": ["sde-agents:prompt-craft", "code-review"]},
            call("Skill", "s1", command="sde-agents:prompt-craft"),
            result_event(),
        ), encoding="utf-8")
        self.traces = [self.trace]
        self.out = self.tmp / "out"

    def _write_cluster(self, expect_fires: list) -> None:
        self.cluster.write_text(json.dumps({
            "cluster": "demo",
            "members": ["prompt-craft", "prompt-engineer"],
            "cases": [{"id": "pos-demo", "polarity": "positive", "prompt": self.PROMPT,
                       "expect_fires": expect_fires}],
        }), encoding="utf-8")

    def _fake_native(self, on_run=None):
        """Stand in for `claude plugin eval`: write the result document it would have written.

        Patching `run` reaches the whole `subprocess` module, which provenance also uses for its
        `git` calls, so anything that is not the eval invocation is delegated to the real one
        rather than silently answered with a stub.
        """
        real_run = subprocess.run

        def run(argv, **kwargs):
            if "--json" not in argv:
                return real_run(argv, **kwargs)
            self.launched.append(list(argv))
            result_path = Path(argv[argv.index("--json") + 1])
            result_path.write_text(json.dumps({
                "claudeVersion": "2.1.270", "costUsd": 0.5, "partial": False,
                "cases": [{"name": "pos-demo", "arms": {"with": [
                    {"error": None, "tracePath": str(path)} for path in self.traces]}}],
            }), encoding="utf-8")
            if on_run is not None:
                on_run()
            return subprocess.CompletedProcess(argv, 0)
        return run

    def _main(self, on_run=None, argv_extra=(), runs: int = 1) -> tuple[int, str]:
        stderr = io.StringIO()
        with (
            mock.patch.object(eval_routing, "CLAUDE", "claude"),
            mock.patch.object(
                eval_routing.subprocess, "run", side_effect=self._fake_native(on_run)
            ),
            mock.patch.object(eval_routing, "cli_version", return_value="2.1.270 (Claude Code)"),
            contextlib.redirect_stderr(stderr),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = eval_routing.main(
                [str(self.cluster), "--runs", str(runs), "--output-dir", str(self.out),
                 *argv_extra]
            )
        return code, stderr.getvalue()

    def test_a_clean_run_writes_a_benchmark_with_complete_provenance(self) -> None:
        code, _stderr = self._main()
        self.assertEqual(0, code)
        benchmark = json.loads((self.out / "benchmark.json").read_text(encoding="utf-8"))
        self.assertEqual("demo", benchmark["cluster"])
        self.assertEqual({"passed": 1, "total": 1}, benchmark["summary"])
        self.assertEqual([["prompt-craft"]], benchmark["cases"][0]["fired_per_run"])
        for key in ("eval_sources", "selection", "evaluator", "plugin"):
            self.assertIn(key, benchmark["provenance"], f"provenance lost its {key}")
        conditions = benchmark["conditions"]
        # Read off the trace, not the request: an artifact recording what was ASKED for cannot be
        # validly diffed, because on the pinned runs it exists to describe the two agree.
        self.assertEqual(["claude-sonnet-5"], conditions["models_observed"])
        self.assertEqual("claude plugin eval", conditions["harness"])
        self.assertFalse(conditions["clean_room_requested"])
        # The competition, observed rather than asserted: a flag records what the caller wanted,
        # and `--clean-room` was measured to deliver none of it under the native harness.
        self.assertEqual(
            {"agents": ["general-purpose", "sde-agents:prompt-engineer"],
             "skills": ["code-review", "sde-agents:prompt-craft"]},
            conditions["components_observed"],
            "the competition must be read off the session's own init event",
        )

    def test_a_cluster_edited_mid_batch_into_a_bad_target_exits_two(self) -> None:
        """The sessions are already paid for; the benchmark must not describe a different cluster
        than the one that was measured."""
        code, stderr = self._main(on_run=lambda: self._write_cluster(["not-a-member"]))
        self.assertEqual(2, code)
        self.assertIn("cluster error after sessions", stderr)
        self.assertFalse((self.out / "benchmark.json").exists())

    def test_a_cluster_edited_mid_batch_into_a_different_selection_writes_nothing(self) -> None:
        def widen() -> None:
            spec = json.loads(self.cluster.read_text(encoding="utf-8"))
            spec["cases"].append({"id": "pos-added", "polarity": "positive",
                                  "prompt": "another", "expect_fires": ["prompt-craft"]})
            self.cluster.write_text(json.dumps(spec), encoding="utf-8")
        code, stderr = self._main(on_run=widen)
        self.assertEqual(2, code)
        self.assertIn("changed while the batch was running", stderr)
        self.assertFalse((self.out / "benchmark.json").exists())

    def test_a_traversing_cluster_name_is_refused_before_any_session_runs(self) -> None:
        """P1, at the wiring rather than the primitive: `write_cases` REMOVES a stale directory,
        so a cluster named `../../../victim` made an eval run delete an arbitrary one.

        Testing `safe_path_segment` alone left this branch vacuous -- removing the call from `main`
        kept every test green. This drives `main` and asserts the harness is never even launched.
        """
        spec = json.loads(self.cluster.read_text(encoding="utf-8"))
        spec["cluster"] = "../../../victim"
        self.cluster.write_text(json.dumps(spec), encoding="utf-8")
        stderr = io.StringIO()
        with (
            mock.patch.object(eval_routing, "CLAUDE", "claude"),
            mock.patch.object(
                eval_routing.subprocess, "run", side_effect=self._fake_native(),
            ),
            mock.patch.object(eval_routing, "cli_version", return_value="2.1.270"),
            contextlib.redirect_stderr(stderr),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = eval_routing.main([str(self.cluster), "--runs", "1"])
        self.assertEqual(2, code)
        self.assertIn("single path component", stderr.getvalue())
        self.assertFalse(
            self.out.exists(),
            "no benchmark may be written for a cluster whose name escapes the eval root",
        )

    def test_an_unreadable_native_result_is_a_measurement_failure_not_a_verdict(self) -> None:
        """Exit 3 asks for a re-run; exit 1 would send someone auditing descriptions over a
        harness that never produced a result."""
        stderr = io.StringIO()
        with (
            mock.patch.object(eval_routing, "CLAUDE", "claude"),
            mock.patch.object(
                eval_routing.subprocess, "run",
                return_value=subprocess.CompletedProcess([], 1),
            ),
            contextlib.redirect_stderr(stderr),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = eval_routing.main([str(self.cluster), "--runs", "1"])
        self.assertEqual(3, code)
        self.assertIn("no readable result", stderr.getvalue())


class CodexReviewFindingsTest(unittest.TestCase):
    """Guards restored or added after the Codex review of PR #191. All eleven findings were real.

    Each test drives the branch the finding named. They live together because they share one
    lesson: five of these were guards the retiring runner HAD, dropped in the rewrite because the
    code they protected had moved. A dropped guard leaves no failing test behind — that is what
    makes it the expensive kind of mistake.
    """

    def test_a_case_id_that_escapes_the_eval_root_is_refused(self) -> None:
        """P1: `Path("/base") / "/tmp/x"` is `/tmp/x`, so an absolute id wrote outside the tree."""
        from fleet import nativecases
        spec = {"cluster": "demo", "members": ["runbook"], "cases": []}
        for bad in ("/tmp/owned", "../../escape", "a/b"):
            with self.subTest(case_id=bad):
                case = {"id": bad, "polarity": "positive", "prompt": "p",
                        "expect_fires": ["runbook"]}
                with self.assertRaisesRegex(ValueError, "case id"):
                    nativecases.case_files(spec, case, agents=frozenset())

    def test_a_cluster_name_that_escapes_the_frozen_root_is_refused(self) -> None:
        """P1: `write_cases` REMOVES a stale directory, so a traversing name deleted an arbitrary
        one. The check has to run before the removal, which is what `write_cases` asserts."""
        from fleet import fs
        with self.assertRaisesRegex(ValueError, "cluster"):
            fs.safe_path_segment("../../../victim", what="cluster")

    def test_write_cases_refuses_an_escaping_target_before_deleting_anything(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            victim = root / "victim"
            victim.mkdir()
            (victim / "keep.txt").write_text("important", encoding="utf-8")
            with self.assertRaises(ValueError):
                eval_routing.write_cases(
                    root / "generated" / ".." / ".." / "victim", {"c/p.md": "x"}, {"cluster": "d"}
                )
            self.assertTrue(
                (victim / "keep.txt").exists(), "the refusal must precede the tree removal"
            )

    def test_a_run_that_never_registered_the_graded_components_is_not_evidence(self) -> None:
        """P1: a completed trace with no dispatch used to pass a negative whose forbidden
        destination was never loaded, so it could not possibly have fired."""
        case = {"id": "n", "polarity": "negative", "expect_not_fires": ["root-cause"]}
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        handle.write(trace(
            {"type": "system", "subtype": "init", "agents": [], "skills": ["sde-agents:runbook"]},
            result_event(),
        ))
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        entry = eval_routing._scored(
            case, ["root-cause"], [{"tracePath": handle.name, "error": None}],
            frozenset({"root-cause", "runbook"}), 0.5,
        )
        self.assertTrue(entry["inconclusive"], "an unloaded component cannot be measured")
        self.assertFalse(entry["passed"])
        self.assertIn("not registered", entry["notes"][0])

    def test_a_case_the_harness_stopped_short_of_is_not_scored_at_full_confidence(self) -> None:
        """P1: `--max-cost-usd` returns fewer records than requested; grading them as-is computed
        a 1/1 rate while the artifact still claimed three runs."""
        registered = {"type": "system", "subtype": "init", "agents": [],
                      "skills": ["sde-agents:root-cause"]}
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        handle.write(trace(registered, call("Skill", "s1", command="root-cause"), result_event()))
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        case = {"id": "p", "polarity": "positive", "prompt": "x", "expect_fires": ["root-cause"]}
        full = eval_routing._scored(
            case, ["root-cause"], [{"tracePath": handle.name, "error": None}],
            frozenset({"root-cause"}), 0.5,
        )
        self.assertEqual(0, full["runs_excluded"], "one requested, one delivered")
        # The padding happens in main; assert the shape it relies on rather than re-running main.
        padded = eval_routing._scored(
            case, ["root-cause"],
            [{"tracePath": handle.name, "error": None},
             {"tracePath": None, "error": "run never launched (harness stopped early)"},
             {"tracePath": None, "error": "run never launched (harness stopped early)"}],
            frozenset({"root-cause"}), 0.5,
        )
        self.assertEqual(2, padded["runs_excluded"])
        self.assertIn("excluded", padded["detail"])

    def test_the_frontmatter_emitter_is_part_of_the_evaluator_identity(self) -> None:
        """P2: it emits the prompts, tool permissions and grader regexes, so a change there alters
        the generated inputs while every other evaluator path stays byte-identical."""
        self.assertIn(
            REPO / "fleet" / "frontmatter.py", eval_routing.EVALUATOR_PATHS
        )

    def test_a_non_uniform_component_surface_is_recorded_as_such(self) -> None:
        """P2: the union cannot tell "every run saw this" from "one run saw an extra component"."""
        paths = []
        for extra in ([], ["sde-agents:extra"]):
            handle = tempfile.NamedTemporaryFile(
                "w", suffix=".jsonl", delete=False, encoding="utf-8"
            )
            handle.write(trace(
                {"type": "system", "subtype": "init", "agents": [],
                 "skills": ["sde-agents:root-cause", *extra]},
                call("Skill", "s1", command="root-cause"), result_event(),
            ))
            handle.close()
            self.addCleanup(Path(handle.name).unlink, missing_ok=True)
            paths.append(handle.name)
        case = {"id": "p", "polarity": "positive", "prompt": "x", "expect_fires": ["root-cause"]}
        same = eval_routing._scored(
            case, ["root-cause"], [{"tracePath": paths[0], "error": None}] * 2,
            frozenset({"root-cause"}), 0.5,
        )
        self.assertTrue(same["components_uniform"])
        mixed = eval_routing._scored(
            case, ["root-cause"],
            [{"tracePath": paths[0], "error": None}, {"tracePath": paths[1], "error": None}],
            frozenset({"root-cause"}), 0.5,
        )
        self.assertFalse(mixed["components_uniform"], "an intermittent surface must be visible")


class RestoredConditionGuardsTest(MainIntegrationTest):
    """The remaining Codex findings, driven through `main` rather than asserted about.

    Inherits `MainIntegrationTest`'s fixture so these exercise the real entry point with only the
    native harness replaced.
    """

    def test_a_mutation_inside_the_frozen_copy_is_detected(self) -> None:
        """P1: this verified `--plugin-dir` -- the untouched source -- so a session mutating the
        snapshot it actually ran from was invisible, and the benchmark kept the original identity.
        """
        def mutate_the_snapshot() -> None:
            # argv is `claude plugin eval <frozen> …`; the harness ran from that copy.
            frozen = Path(self.launched[-1][3])
            target = next(frozen.glob("agents/*.md"), None) or next(frozen.glob("skills/*/*.md"))
            target.write_text(target.read_text(encoding="utf-8") + "\nmutated\n", encoding="utf-8")

        code, stderr = self._main(on_run=mutate_the_snapshot)
        self.assertEqual(2, code)
        self.assertIn("changed while the batch was running", stderr)
        self.assertFalse((self.out / "benchmark.json").exists())

    def test_a_default_run_still_records_its_authentication_conditions(self) -> None:
        """P2: `auth_provider` was null unless `--clean-room`, so two benchmarks taken against
        different providers looked identical in their conditions."""
        code, _stderr = self._main()
        self.assertEqual(0, code)
        conditions = json.loads((self.out / "benchmark.json").read_text())["conditions"]
        self.assertIsNotNone(
            conditions["auth_provider"], "an ordinary run must classify its provider too"
        )
        self.assertIn("provider", conditions["auth_provider"])

    def test_a_batch_that_mixed_models_says_so(self) -> None:
        """P2: the runner collected the names but never checked the count, so it could write and
        exit 0 on a benchmark its own comment says must not be diffed as one baseline."""
        second = self.tmp / "trace2.jsonl"
        second.write_text(
            self.trace.read_text(encoding="utf-8").replace("claude-sonnet-5", "claude-opus-5"),
            encoding="utf-8",
        )
        self.traces = [self.trace, second]
        code, stderr = self._main(runs=2)
        self.assertEqual(0, code)
        self.assertIn("did not use one model", stderr)
        self.assertIn("must not be diffed as a single baseline", stderr)

    def test_a_malformed_prompt_is_refused_before_a_session_is_paid_for(self) -> None:
        """P2: `scoring_targets` never looks at the prompt, so `None` became the literal string
        "None" and bought a real session plus a recorded verdict."""
        for prompt in (None, "", "   ", 42):
            with self.subTest(prompt=prompt):
                spec = json.loads(self.cluster.read_text(encoding="utf-8"))
                spec["cases"][0]["prompt"] = prompt
                self.cluster.write_text(json.dumps(spec), encoding="utf-8")
                self.launched.clear()
                code, stderr = self._main()
                self.assertEqual(2, code)
                self.assertIn("prompt must be a non-empty string", stderr)
                self.assertFalse(
                    [a for a in self.launched if "--json" in a], "no session may be launched"
                )

    def test_an_unusable_clean_room_exits_two_rather_than_raising(self) -> None:
        """P2: `clean_env()` raises on ENTER, not on construction, so the documented exit-2 path
        was an uncaught traceback for anyone without credentials."""
        module = eval_routing.sys.modules.get(
            "scripts.eval_clean_room"
        ) or eval_routing.sys.modules["eval_clean_room"]
        with mock.patch.object(
            module, "clean_env", side_effect=module.AuthUnavailable("no credentials")
        ):
            code, stderr = self._main(argv_extra=("--clean-room",))
        self.assertEqual(2, code)
        self.assertIn("clean room unavailable", stderr)


class CodexSecondRoundTest(MainIntegrationTest):
    """The eight findings from the Codex review of `142674b`. All eight were real too.

    Three were guards the first round restored too narrowly, which is its own lesson: fixing a
    finding is not the same as covering the invariant behind it.
    """

    def test_a_plugin_that_changed_before_the_freeze_is_refused(self) -> None:
        """P1: the snapshot is taken after the identity is recorded, so the sessions could run
        bytes the benchmark never names -- invisible if the source changed back afterwards."""
        real_frozen = eval_routing.provenance.frozen_plugin

        @contextlib.contextmanager
        def drifted(plugin_dir):
            with real_frozen(plugin_dir) as (frozen, identity):
                yield frozen, {**identity, "sha256": "0" * 64}

        stderr = io.StringIO()
        with (
            mock.patch.object(eval_routing, "CLAUDE", "claude"),
            mock.patch.object(
                eval_routing.subprocess, "run", side_effect=self._fake_native()
            ),
            mock.patch.object(eval_routing.provenance, "frozen_plugin", drifted),
            contextlib.redirect_stderr(stderr),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = eval_routing.main(
                [str(self.cluster), "--runs", "1", "--output-dir", str(self.out)]
            )
        self.assertEqual(2, code)
        self.assertIn("changed between recording its identity and freezing", stderr.getvalue())
        self.assertFalse((self.out / "benchmark.json").exists())

    def test_an_authentication_failure_aborts_the_batch(self) -> None:
        """P1: excluding only the affected runs let the earlier valid ones pass every case and
        write a benchmark at exit 0, which is a measurement outage reported as a result."""
        self.trace.write_text(trace(
            {"type": "system", "subtype": "init", "agents": [],
             "skills": ["sde-agents:prompt-craft"]},
            {"type": "result", "is_error": True,
             "result": "Failed to authenticate: OAuth session expired"},
        ), encoding="utf-8")
        code, stderr = self._main()
        self.assertEqual(3, code, "a measurement that did not happen is exit 3, not a verdict")
        self.assertIn("eval aborted", stderr)
        self.assertFalse((self.out / "benchmark.json").exists())

    def test_a_malformed_cases_array_exits_two_rather_than_raising(self) -> None:
        """P2: the filter called `.get()` on each entry before anything validated the array."""
        for cases in (None, 42, [42], [], ["a"]):
            with self.subTest(cases=cases):
                spec = json.loads(self.cluster.read_text(encoding="utf-8"))
                spec["cases"] = cases
                self.cluster.write_text(json.dumps(spec), encoding="utf-8")
                code, stderr = self._main()
                self.assertEqual(2, code)
                self.assertIn("non-empty list of objects", stderr)

    def test_an_absent_agent_member_invalidates_a_run_even_when_not_graded(self) -> None:
        """P2: the first fix checked only the graded targets, so a narrowed negative forbidding a
        skill stayed valid while an agent member of the cluster was missing entirely."""
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        handle.write(trace(
            {"type": "system", "subtype": "init", "agents": [],
             "skills": ["sde-agents:prompt-craft"]},
            result_event(),
        ))
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        # `prompt-engineer` is a real fleet AGENT and a cluster member here, but unregistered.
        entry = eval_routing._scored(
            {"id": "n", "polarity": "negative", "expect_not_fires": ["prompt-craft"]},
            ["prompt-craft", "prompt-engineer"],
            [{"tracePath": handle.name, "error": None}],
            eval_routing.FLEET, 0.5,
        )
        self.assertTrue(entry["inconclusive"])
        self.assertIn("prompt-engineer", entry["notes"][0])

    def test_uniformity_is_judged_across_the_batch_not_within_each_case(self) -> None:
        """P2: every run of case A seeing X and every run of case B seeing Y left each case-level
        flag true, which is exactly the changing competition the field rules out."""
        def entry(skills: list[str]) -> dict:
            return {"components_observed": {"agents": [], "skills": skills},
                    "components_uniform": True, "inconclusive": False}
        same = [entry(["a"]), entry(["a"])]
        differing = [entry(["a"]), entry(["a", "b"])]
        self.assertTrue(eval_routing._batch_components_uniform(same))
        self.assertFalse(eval_routing._batch_components_uniform(differing))

    def test_a_failed_cleanup_of_a_kept_directory_is_reported(self) -> None:
        """P2: `ignore_errors=True` hid a leftover plugin copy and session traces."""
        stderr = io.StringIO()
        with (
            mock.patch.object(
                eval_routing.shutil, "rmtree",
                side_effect=lambda root, onerror=None: onerror(None, str(root), None),
            ),
            contextlib.redirect_stderr(stderr),
        ):
            eval_routing._remove_kept_temp_dirs(
                {"a": [{"tracePath": "/tmp/claude-eval-abc/out/trace.jsonl"}]}
            )
        self.assertIn("could not remove kept eval directories", stderr.getvalue())
        self.assertIn("claude-eval-abc", stderr.getvalue())

    def test_the_module_docstring_does_not_carry_the_disproven_clean_room_premise(self) -> None:
        """P2: the correction reached `evals/README.md`, `AGENTS.md` and the decision record, but
        not the script's own docstring -- the drift I claimed to have fixed."""
        doc = eval_routing.__doc__ or ""
        # Asserted as what the docstring must SAY, not as a phrase it must avoid: prose that
        # quotes a disproven claim in order to refute it is correct, and a bare absence check
        # fails it. These three are the measured contract.
        self.assertIn("refuted", doc)
        self.assertIn("byte-identical with and without", doc)
        self.assertIn("components_observed", doc)
        self.assertIn("clean_room_requested", doc)
        self.assertNotIn("`--clean-room` therefore\nsurvives", doc)

    def test_provenance_uses_the_kernel_filesystem_primitives(self) -> None:
        """P1: it reimplemented `is_link_or_reparse` and `absolute_without_resolving`, which is
        two kernel answers for one filesystem safety fact -- an explicit AGENTS.md hard rule."""
        import fleet.provenance as prov
        self.assertFalse(hasattr(prov, "_is_link_or_reparse"))
        self.assertFalse(hasattr(prov, "_absolute_without_resolving"))
        self.assertIs(prov.fs.is_link_or_reparse, fs_module.is_link_or_reparse)
