from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from scripts import fleet_doctor
from tests import support
from tests.support import REPO


class CodexInstallMarkerIsIgnored(support.TempDirTestCase):
    """A Codex marketplace snapshot must not read as a permanently dirty worktree.

    `codex plugin add` writes `.codex-marketplace-install.json` into the snapshot it installs from.
    On a host whose only copy of the fleet IS that snapshot, an unignored marker makes
    `repository.worktree` warn on every run, and a warning is a non-zero doctor exit — so the
    health check would be non-zero forever, which teaches an operator to ignore it. That is the
    same silence the exit code was changed to break, so this reads the repository's REAL
    `.gitignore` rather than a synthetic copy of the rule: a fixture could drift away from the file
    that actually ships.
    """

    MARKER = ".codex-marketplace-install.json"
    RULE = "/.codex-marketplace-install.json"

    def _snapshot(self, gitignore: str | None = None) -> Path:
        """A committed git repo carrying the shipped .gitignore, as a snapshot checkout does."""
        root = self.base / "snapshot"
        root.mkdir()
        support.git(root, "init", "-q")
        # `git status` here reads the invoking developer's global config, so two settings decide
        # this fixture's verdict before the repository rule gets a vote. Both are pinned locally,
        # and both were review findings on this PR -- the second reproduced at exit 1 with three
        # failures under `GIT_CONFIG_GLOBAL` alone.
        #   core.excludesFile          -- an operator who ignored the marker globally would make
        #                                 the strip-the-rule proof below pass whether or not the
        #                                 repository rule existed: a green reporting their config.
        #   status.showUntrackedFiles  -- set to `no`, every untracked marker is suppressed and the
        #                                 warn-expecting cases fail on their machine and nowhere
        #                                 else. `all` also survives `normal`'s directory collapsing.
        empty = self.base / "empty-global-excludes"
        empty.write_text("", encoding="utf-8")
        support.git(root, "config", "core.excludesFile", str(empty))
        support.git(root, "config", "status.showUntrackedFiles", "all")
        text = (REPO / ".gitignore").read_text(encoding="utf-8")
        (root / ".gitignore").write_text(
            text if gitignore is None else gitignore, encoding="utf-8", newline="\n"
        )
        (root / "tests" / "fixtures").mkdir(parents=True)
        (root / "tests" / "fixtures" / "kept.txt").write_text("tracked\n", encoding="utf-8")
        support.git(root, "add", "-A")
        support.git(
            root, "-c", "user.email=t@example.invalid", "-c", "user.name=t",
            "commit", "-qm", "seed",
        )
        return root

    def _worktree_status(self, root: Path) -> fleet_doctor.Check:
        checks = fleet_doctor._git_checks(root, fleet_doctor._run_read_only)
        return {check.check_id: check for check in checks}["repository.worktree"]

    def test_the_marker_alone_leaves_the_worktree_clean(self) -> None:
        root = self._snapshot()
        (root / self.MARKER).write_text('{"plugin": "sde-agents"}', encoding="utf-8")

        check = self._worktree_status(root)

        self.assertEqual("pass", check.status, check.details)

    def test_without_the_rule_the_same_tree_would_warn(self) -> None:
        # Non-vacuity, proven in-test rather than by hand: strip only this rule and the identical
        # tree warns, so the new .gitignore entry -- not some pre-existing rule, and not the
        # check's own behavior -- is what keeps a snapshot host at exit 0. The filter matches the
        # rule LINE exactly rather than any line mentioning the marker, so a later comment naming
        # the file cannot silently widen what this proof removes (review finding, PR #130).
        shipped = (REPO / ".gitignore").read_text(encoding="utf-8")
        stripped = "\n".join(
            line for line in shipped.splitlines() if line.strip() != self.RULE
        )
        self.assertNotEqual(shipped, stripped, "the rule under test is missing from .gitignore")
        root = self._snapshot(gitignore=stripped + "\n")
        (root / self.MARKER).write_text('{"plugin": "sde-agents"}', encoding="utf-8")

        check = self._worktree_status(root)

        self.assertEqual("warn", check.status)
        self.assertIn(self.MARKER, " ".join(check.details["entries"]))

    def test_a_nested_marker_is_somebody_s_real_file_and_still_warns(self) -> None:
        # The rule is anchored to the snapshot root because Codex writes it only there. A slashless
        # pattern would match the basename at every depth and hide a genuine local addition; this
        # is the test that keeps the anchor from being dropped (review finding, PR #130).
        root = self._snapshot()
        nested = root / "tests" / "fixtures" / self.MARKER
        nested.write_text('{"plugin": "sde-agents"}', encoding="utf-8")

        check = self._worktree_status(root)

        self.assertEqual("warn", check.status, check.details)
        self.assertIn("tests/fixtures/" + self.MARKER, " ".join(check.details["entries"]))

    def test_a_real_local_edit_still_warns(self) -> None:
        # The rule must ignore exactly one host-generated marker, never soften the check itself.
        root = self._snapshot()
        (root / "README.md").write_text("an actual local change", encoding="utf-8")

        self.assertEqual("warn", self._worktree_status(root).status)


class SkillListingBudgetCheck(support.TempDirTestCase):
    """The listing-budget tripwire warns before a host silently strips plugin descriptions.

    On a 200k-context model the skill listing is capped at 8,000 characters and over-budget
    plugin entries degrade to bare names (probed on CLI 2.1.233), so the failure this check
    watches for is invisible at runtime: routing quietly stops and nothing says so. Each test
    here makes one branch of the computation fire — over/under, the workflow entries, and the
    disable-model-invocation exclusion — because a sum that silently skipped a component would
    report headroom the model does not have.
    """

    def _tree(
        self,
        *,
        skills: dict[str, str],
        dmi: dict[str, str] | None = None,
        workflow_description: str | None = None,
        label: str = "fleet",
    ) -> Path:
        root = self.base / label
        (root / ".claude-plugin").mkdir(parents=True)
        (root / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "sde-agents", "version": "0.0.0"}\n', encoding="utf-8"
        )
        for name, description in {**skills, **(dmi or {})}.items():
            directory = root / "skills" / name
            directory.mkdir(parents=True)
            flag = "disable-model-invocation: true\n" if dmi and name in dmi else ""
            (directory / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {description}\n{flag}---\n\nBody.\n",
                encoding="utf-8",
            )
        if workflow_description is not None:
            (root / "workflows").mkdir()
            (root / "workflows" / "wf.js").write_text(
                "export const meta = {\n"
                "  name: 'wf',\n"
                f"  description: '{workflow_description}',\n"
                "}\n",
                encoding="utf-8",
            )
        return root

    def _check(self, root: Path) -> fleet_doctor.Check:
        check = fleet_doctor._skill_listing_budget_check(root)
        self.assertEqual("repository.skill-listing-budget", check.check_id)
        return check

    def test_a_listing_over_budget_warns_with_the_consequence(self) -> None:
        check = self._check(self._tree(skills={f"skill-{i}": "d" * 900 for i in range(10)}))
        self.assertEqual("warn", check.status)
        self.assertIn("bare names", check.summary)
        self.assertGreater(check.details["total_chars"], check.details["budget_chars"])

    def test_listing_estimate_states_its_host_assumptions_in_both_verdicts(self) -> None:
        for count in (1, 10):
            with self.subTest(count=count):
                check = self._check(self._tree(
                    skills={f"skill-{i}": "d" * 900 for i in range(count)},
                    label=f"host-assumptions-{count}",
                ))
                self.assertEqual("claude", check.details["host"])
                self.assertEqual(200000, check.details["assumed_context_window_tokens"])
                self.assertFalse(check.details["observed_host_listing"])
                self.assertIn("Claude", check.summary)
                self.assertIn("not measured", check.summary)

    def test_a_listing_within_budget_passes_and_states_headroom(self) -> None:
        check = self._check(self._tree(skills={"one": "short description"}))
        self.assertEqual("pass", check.status)
        self.assertIn("headroom", check.summary)

    def test_workflow_meta_descriptions_count_toward_the_budget(self) -> None:
        # Skills alone fit; the workflow's entry tips the sum. If workflow parsing silently
        # broke, this tree would report headroom the model does not have — exactly the
        # under-report the docstring names.
        skills = {f"skill-{i}": "d" * 900 for i in range(8)}
        without = self._check(self._tree(skills=skills))
        self.assertEqual("pass", without.status)
        with_workflow = self._check(
            self._tree(skills=skills, workflow_description="w" * 900, label="with-workflow")
        )
        self.assertEqual("warn", with_workflow.status)
        self.assertEqual(9, with_workflow.details["entries"])

    def test_disable_model_invocation_entries_cost_nothing_but_are_reported(self) -> None:
        # The DMI skill's description would tip the budget if counted; its absence from the
        # model's listing was verified live on CLI 2.1.233, so counting it would overstate
        # the fleet's footprint and demand trims the listing does not need. But 2.1.212-era
        # CLIs listed flagged plugin skills anyway, so the excluded cost must be visible —
        # a pass on those hosts is only honest if its headroom covers the DMI entries too.
        skills = {f"skill-{i}": "d" * 900 for i in range(8)}
        check = self._check(self._tree(skills=skills, dmi={"ceremony": "d" * 500}))
        self.assertEqual("pass", check.status)
        self.assertEqual(8, check.details["entries"])
        self.assertGreater(check.details["dmi_excluded_chars"], 500)
        self.assertIn("disable-model-invocation entries", check.summary)

    def test_an_unreadable_tree_is_inconclusive_not_a_verdict(self) -> None:
        check = self._check(self.base / "missing")
        self.assertEqual("inconclusive", check.status)

    def test_a_non_string_plugin_name_is_inconclusive_not_a_traceback(self) -> None:
        # `re.escape(7)` five frames down would print a traceback exactly when the manifest is
        # damaged — the moment the documented inconclusive path exists for.
        root = self._tree(skills={"one": "short"}, label="bad-name")
        (root / ".claude-plugin" / "plugin.json").write_text(
            '{"name": 7}\n', encoding="utf-8"
        )
        check = self._check(root)
        self.assertEqual("inconclusive", check.status)

    def test_a_non_object_manifest_root_is_inconclusive_not_a_traceback(self) -> None:
        # json.loads happily returns a list, and `manifest["name"]` on one raises TypeError —
        # outside the except clause — so a damaged manifest crashed the doctor instead of
        # taking the documented inconclusive path (DOCTOR-001).
        root = self._tree(skills={"one": "short"}, label="list-manifest")
        (root / ".claude-plugin" / "plugin.json").write_text("[]\n", encoding="utf-8")
        check = self._check(root)
        self.assertEqual("inconclusive", check.status)

    def test_a_workflow_name_colliding_with_a_skill_counts_both_entries(self) -> None:
        # Keyed into one dict by name, the collision silently overwrote the skill's entry — an
        # undercount toward a false pass with no inconclusive verdict (DOCTOR-004). The model's
        # listing shows both entries, so the sum must count both.
        root = self._tree(skills={"twin": "d" * 400}, label="name-collision")
        (root / "workflows").mkdir()
        (root / "workflows" / "wf.js").write_text(
            "export const meta = {\n"
            "  name: 'twin',\n"
            f"  description: '{'D' * 400}',\n"
            "}\n",
            encoding="utf-8",
        )
        check = self._check(root)
        self.assertEqual(2, check.details["entries"])
        self.assertGreater(check.details["total_chars"], 800)

    def test_an_unparseable_skill_definition_blocks_the_verdict(self) -> None:
        # The unparseable file is omitted from the sum, so a verdict over the remainder would
        # report headroom the model does not have — fictitious-pass, the review finding's exact
        # scenario: eight parseable skills under budget plus one unreadable large one.
        root = self._tree(
            skills={f"skill-{i}": "d" * 900 for i in range(8)}, label="broken-skill"
        )
        broken = root / "skills" / "broken" / "SKILL.md"
        broken.parent.mkdir(parents=True)
        broken.write_text("no frontmatter at all\n", encoding="utf-8")
        check = self._check(root)
        self.assertEqual("inconclusive", check.status)
        self.assertIn("skills/broken/SKILL.md", str(check.details["unreadable"]))

    def test_workflow_extraction_takes_the_top_level_description_not_a_nested_decoy(self) -> None:
        # An unscoped regex would take the first `description:` in the file — here a tiny nested
        # one inside phases — and undercount the listing by the whole real entry.
        root = self._tree(skills={"one": "short"}, label="nested-meta")
        (root / "workflows").mkdir()
        (root / "workflows" / "wf.js").write_text(
            "export const meta = {\n"
            "  name: 'wf',\n"
            "  phases: [{ title: 'Scan', description: 'tiny' }],\n"
            f"  description: '{'D' * 900}',\n"
            "}\n",
            encoding="utf-8",
        )
        check = self._check(root)
        self.assertEqual(2, check.details["entries"])
        # The 900-char top-level description dominates the total; the 4-char decoy cannot.
        self.assertGreater(check.details["total_chars"], 900)

    def test_a_workflow_with_only_a_nested_description_blocks_the_verdict(self) -> None:
        # The nested value is not the listing field; treating it as one would report a
        # near-empty entry for a workflow whose real listing cost is unknown.
        root = self._tree(skills={"one": "short"}, label="nested-only-meta")
        (root / "workflows").mkdir()
        (root / "workflows" / "wf.js").write_text(
            "export const meta = {\n"
            "  name: 'wf',\n"
            "  phases: [{ title: 'Scan', description: 'tiny' }],\n"
            "}\n",
            encoding="utf-8",
        )
        check = self._check(root)
        self.assertEqual("inconclusive", check.status)

    def test_legacy_dmi_cost_exceeding_headroom_is_named_in_the_pass(self) -> None:
        # A pass whose headroom is smaller than the excluded DMI cost does not hold on
        # pre-2.1.233 hosts, and the message must say so rather than leaving it to arithmetic.
        skills = {f"skill-{i}": "d" * 900 for i in range(8)}  # ~7.5k of 8k: little headroom
        check = self._check(
            self._tree(skills=skills, dmi={"ceremony": "d" * 800}, label="legacy-over")
        )
        self.assertEqual("pass", check.status)
        self.assertTrue(check.details["legacy_dmi_over_headroom"])
        self.assertIn("over budget despite this pass", check.summary)

    def test_a_workflow_without_an_extractable_description_blocks_the_verdict(self) -> None:
        # workflows/ is auto-discovered, so a meta this extractor cannot read is a real listing
        # entry with an unknown cost — silently skipping it shrinks the sum toward a false pass.
        root = self._tree(skills={"one": "short"}, label="broken-workflow")
        (root / "workflows").mkdir()
        (root / "workflows" / "wf.js").write_text(
            "export const meta = {\n  name: 'wf',\n}\n", encoding="utf-8"
        )
        check = self._check(root)
        self.assertEqual("inconclusive", check.status)
        self.assertIn("workflows/wf.js", str(check.details["unreadable"]))

    def test_the_real_repository_computes_a_verdict(self) -> None:
        # Not pinned to warn or pass: the description diet this check exists to motivate will
        # legitimately flip it. What must hold is that the real tree computes — a real-repo
        # regression to inconclusive would mean the tripwire disarmed itself silently.
        check = self._check(REPO)
        self.assertIn(check.status, {"pass", "warn"})
        self.assertGreater(check.details["entries"], 0)


class FleetDoctorTests(unittest.TestCase):
    def test_command_allowlist_rejects_mutating_or_model_commands(self) -> None:
        fleet_doctor._assert_read_only_command(
            ("git", "--no-optional-locks", "-C", str(REPO), "status", "--short")
        )
        fleet_doctor._assert_read_only_command(("claude", "plugin", "list"))
        for command in (
            ("git", "--no-optional-locks", "-C", str(REPO), "fetch"),
            ("git", "-C", str(REPO), "status", "--short"),
            ("claude", "plugin", "install", "sde-agents"),
            ("codex", "exec", "inspect this repo"),
            ("python", "scripts/generate_platform_adapters.py", "--write"),
        ):
            with self.subTest(command=command):
                with self.assertRaisesRegex(ValueError, "read-only allowlist"):
                    fleet_doctor._assert_read_only_command(command)

    def test_report_uses_only_read_only_commands_and_does_not_touch_home(self) -> None:
        calls: list[tuple[str, ...]] = []

        def run(argv: tuple[str, ...]) -> fleet_doctor.CommandResult:
            calls.append(tuple(argv))
            fleet_doctor._assert_read_only_command(argv)
            if tuple(argv[-2:]) == ("rev-parse", "HEAD"):
                return fleet_doctor.CommandResult(tuple(argv), 0, "a" * 40 + "\n", "")
            if tuple(argv[-2:]) == ("status", "--short"):
                return fleet_doctor.CommandResult(tuple(argv), 0, "", "")
            if tuple(argv[-2:]) == ("plugin", "list"):
                return fleet_doctor.CommandResult(tuple(argv), 0, "sde-agents 1.4.0\n", "")
            return fleet_doctor.CommandResult(tuple(argv), 0, "test-cli 1.0\n", "")

        def which(command: str) -> str:
            return str(Path("C:/tools") / f"{command}.exe")

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            codex_home = Path(temporary) / "codex"
            home.mkdir()
            sentinel = home / "sentinel.txt"
            sentinel.write_text("unchanged\n", encoding="utf-8")
            before = {
                path.relative_to(home): path.read_bytes()
                for path in home.rglob("*")
                if path.is_file()
            }

            with mock.patch.object(
                fleet_doctor,
                "_repository_checks",
                return_value=[
                    fleet_doctor.Check(
                        "repository.generated-adapters",
                        "pass",
                        "fixture repository is current",
                    )
                ],
            ):
                report = fleet_doctor.collect_report(
                    REPO,
                    home=home,
                    codex_home=codex_home,
                    run=run,
                    which=which,
                    now=datetime(2026, 7, 31, tzinfo=UTC),
                )

            after = {
                path.relative_to(home): path.read_bytes()
                for path in home.rglob("*")
                if path.is_file()
            }

        self.assertEqual(before, after)
        self.assertTrue(calls)
        for argv in calls:
            fleet_doctor._assert_read_only_command(argv)
            self.assertFalse({"install", "update", "fetch", "prune", "exec"} & set(argv))
            if Path(argv[0]).stem.lower() == "git":
                self.assertIn("--no-optional-locks", argv)
        self.assertEqual(1, report["schema_version"])
        self.assertEqual("2026-07-31T00:00:00Z", report["generated_at"])
        self.assertGreaterEqual(report["summary"]["pass"], 1)

    def test_junction_mode_without_plugin_reports_dormant_guard(self) -> None:
        def run(argv: tuple[str, ...]) -> fleet_doctor.CommandResult:
            if tuple(argv[-2:]) == ("plugin", "list"):
                return fleet_doctor.CommandResult(tuple(argv), 0, "other-plugin\n", "")
            return fleet_doctor.CommandResult(tuple(argv), 0, "test-cli 1.0\n", "")

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            codex_home = base / "codex"
            with mock.patch.object(fleet_doctor, "_same_location", return_value=True):
                checks = fleet_doctor._installation_checks(
                    REPO,
                    base,
                    {"claude": "claude"},
                    run,
                    codex_home=codex_home,
                )

        by_id = {check.check_id: check for check in checks}
        self.assertEqual("warn", by_id["host.claude.deployment"].status)
        self.assertEqual("warn", by_id["host.claude.readonly-guard"].status)
        self.assertIn("dormant", by_id["host.claude.readonly-guard"].summary)

    def test_main_exits_one_only_for_failing_checks(self) -> None:
        report = {
            "schema_version": 1,
            "generated_at": "2026-07-31T00:00:00Z",
            "root": str(REPO),
            "summary": {
                "pass": 0,
                "warn": 0,
                "fail": 1,
                "skip": 0,
                "inconclusive": 0,
            },
            "checks": [
                {
                    "check_id": "fixture.failure",
                    "status": "fail",
                    "summary": "fixture failed",
                    "details": {},
                }
            ],
        }
        output = io.StringIO()
        with mock.patch.object(fleet_doctor, "collect_report", return_value=report):
            with redirect_stdout(output):
                exit_code = fleet_doctor.main(["--json"])
        self.assertEqual(1, exit_code)
        self.assertIn('"fixture.failure"', output.getvalue())

    def _exit_code_for(self, **counts: int) -> int:
        report = {
            "schema_version": 1,
            "generated_at": "2026-08-13T00:00:00Z",
            "root": str(REPO),
            "summary": {status: counts.get(status, 0) for status in fleet_doctor.STATUSES},
            "checks": [],
        }
        with mock.patch.object(fleet_doctor, "collect_report", return_value=report):
            with redirect_stdout(io.StringIO()):
                return fleet_doctor.main(["--json"])

    def test_a_warning_alone_is_not_a_clean_exit(self) -> None:
        # REGRESSION (issue #126): host.codex.custom-agents warned that a stale standalone Codex
        # profile was shadowing the shipped one, and the doctor exited 0 anyway -- so every caller
        # that reads a status saw a healthy fleet. Without this the drift check is advisory prose.
        self.assertEqual(3, self._exit_code_for(warn=1, **{"pass": 12}))

    def test_a_failure_outranks_a_warning(self) -> None:
        self.assertEqual(1, self._exit_code_for(fail=1, warn=2))

    def test_only_a_clean_report_exits_zero(self) -> None:
        # A skip is a known non-answer, not an attention state: an absent host cannot be drift.
        self.assertEqual(0, self._exit_code_for(**{"pass": 9, "skip": 2}))

    def test_a_check_that_could_not_be_computed_is_not_a_clean_exit(self) -> None:
        """DOCTOR-002: `inconclusive` reached no exit status, so it exited 0.

        This test previously asserted that, on the reading that skip and inconclusive are both
        non-attention states. They are not the same thing. A skip is a known, expected non-answer
        — the host CLI is not installed. An inconclusive check is one the doctor tried to compute
        and could not, so exiting 0 means agreeing the fleet is healthy on the strength of an
        answer it never obtained. That is the same defect the warnings exit fixed, one level down.
        """
        self.assertEqual(2, self._exit_code_for(**{"pass": 9, "skip": 2, "inconclusive": 1}))

    def test_the_exit_ladder_is_ordered_by_how_definite_the_answer_is(self) -> None:
        """A definite negative outranks an unobtained answer, which outranks a computed warning."""
        self.assertEqual(1, self._exit_code_for(fail=1, inconclusive=1, warn=1))
        self.assertEqual(2, self._exit_code_for(inconclusive=1, warn=1))
        self.assertEqual(3, self._exit_code_for(warn=1))


class DoctorUsesTheKernelResult(unittest.TestCase):
    """One result type, and the two failures it must keep apart.

    The doctor used to keep its own three-field `CommandResult` and downgrade the kernel's into
    it, turning both a timeout and a missing binary into `returncode=127` with the error text in
    stderr. Those call for different operator actions -- wait or retry versus install the CLI --
    and the doctor's whole job is telling the operator which thing to go fix.
    """

    def test_the_doctor_result_is_the_kernel_result(self) -> None:
        self.assertIs(fleet_doctor._proc.CommandResult, fleet_doctor.CommandResult)

    def test_a_timeout_and_a_missing_binary_stay_distinguishable(self) -> None:
        timed_out = fleet_doctor.CommandResult(
            ("claude", "--version"), None, "", "", timed_out=True, error="timed out"
        )
        missing = fleet_doctor.CommandResult(
            ("claude", "--version"), 127, "", "", failed_to_start=True, error="No such file"
        )
        self.assertTrue(timed_out.timed_out)
        self.assertFalse(timed_out.failed_to_start)
        self.assertTrue(missing.failed_to_start)
        self.assertFalse(missing.timed_out)
        # Both are failures; the next test pins why `ok` is the read and returncode is not.
        for result in (timed_out, missing):
            with self.subTest(result=result):
                self.assertFalse(result.ok)

    def test_the_two_failures_produce_different_diagnostics(self) -> None:
        """Holding the richer result is pointless if the report throws the distinction away.

        Both failures leave `stderr` empty and put the cause in `error`, so a details dict of
        `{"stderr": ...}` rendered them identically -- the operator saw one blank line either
        way and could not choose between retrying and repairing the installation.
        """
        timed_out = fleet_doctor.CommandResult(
            ("claude", "--version"), None, "", "", timed_out=True, error="timed out after 30s"
        )
        missing = fleet_doctor.CommandResult(
            ("claude", "--version"), 127, "", "", failed_to_start=True, error="No such file"
        )
        timeout_details = fleet_doctor._failure_details(timed_out)
        missing_details = fleet_doctor._failure_details(missing)

        self.assertNotEqual(timeout_details, missing_details)
        self.assertTrue(timeout_details["timed_out"])
        self.assertNotIn("timed_out", missing_details)
        self.assertTrue(missing_details["failed_to_start"])
        self.assertNotIn("failed_to_start", timeout_details)
        for details in (timeout_details, missing_details):
            with self.subTest(details=details):
                self.assertTrue(details["error"], "the only field carrying the cause is empty")

    def test_a_successful_result_carries_no_failure_flags(self) -> None:
        details = fleet_doctor._failure_details(
            fleet_doctor.CommandResult(("git",), 0, "out", "warn\n")
        )
        self.assertEqual({"stderr": "warn"}, details)

    def test_every_command_failure_branch_carries_the_cause(self) -> None:
        """All FOUR production branches, driven through their own functions.

        An earlier version of this test was named "every" while driving only the two
        `_git_checks` branches, so the CLI and plugin-list branches could have gone back to a
        bare `stderr` diagnostic with the suite green (Codex, #190). A test that asserts on the
        helper alone proves nothing about a branch that never calls it, and a name that overstates
        its coverage is worse than no test, because it stops anyone looking.
        """
        timed_out = fleet_doctor.CommandResult(
            ("cmd",), None, "", "", timed_out=True, error="timed out after 30s"
        )
        ok_head = fleet_doctor.CommandResult(("git",), 0, "a" * 40 + "\n", "")

        def assert_cause(check: fleet_doctor.Check, where: str) -> None:
            self.assertEqual("inconclusive", check.status, where)
            self.assertEqual("timed out after 30s", check.details.get("error"), where)
            self.assertTrue(check.details.get("timed_out"), where)

        # 1. repository.git -- the first command fails.
        checks = fleet_doctor._git_checks(Path("/repo"), lambda argv: timed_out)
        assert_cause(next(c for c in checks if c.check_id == "repository.git"), "repository.git")

        # 2. repository.worktree -- the revision reads, the status command does not.
        checks = fleet_doctor._git_checks(
            Path("/repo"), lambda argv: ok_head if "rev-parse" in argv else timed_out
        )
        assert_cause(
            next(c for c in checks if c.check_id == "repository.worktree"), "repository.worktree"
        )

        # 3. host.<name>.cli -- the executable is found but its version never comes back.
        cli_checks, _ = fleet_doctor._cli_checks(
            lambda command: f"/usr/bin/{command}", lambda argv: timed_out
        )
        version_checks = [c for c in cli_checks if c.check_id.endswith(".cli")]
        self.assertTrue(version_checks, "no CLI version check was produced")
        for check in version_checks:
            assert_cause(check, check.check_id)

        # 4. host.<name>.plugin -- the plugin inventory never comes back.
        listing_check, healthy = fleet_doctor._plugin_listing_check(
            "claude", "/usr/bin/claude", lambda argv: timed_out
        )
        assert_cause(listing_check, "host.claude.plugin")
        self.assertFalse(healthy, "a failed listing must not report the inventory as readable")

    def test_a_timed_out_command_is_not_read_as_a_passing_check(self) -> None:
        """The trap the migration had to avoid, pinned as behaviour rather than as a comment."""
        timed_out = fleet_doctor.CommandResult(
            ("git",), None, "", "", timed_out=True, error="timed out"
        )
        # This is the expression the checks used before the migration.
        self.assertFalse(bool(timed_out.returncode), "returncode None is falsy")
        # And this is the one they use now.
        self.assertFalse(timed_out.ok)


if __name__ == "__main__":
    unittest.main()
