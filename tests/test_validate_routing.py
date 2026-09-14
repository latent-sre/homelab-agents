from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import validate_fleet
from tests.support import repo_copy


class RoutingClusterTests(unittest.TestCase):
    """Schema integrity for evals/routing/*.json (EVAL-001).

    The scorer grades a positive on its own expect_fires but reports the CLUSTER's fire rate — so
    a positive naming a component outside the declared members can pass while the reported rate
    reads zero (observed live: pos-ci-actions-harden accepting code-reviewer). And both target
    lists match components BY NAME, so a typo'd member or target forbids or expects nothing and
    passes vacuously. The runner has no error to raise at grade time; only a validator sees it.
    """

    BASE = {"cluster": "demo", "members": ["craft", "builder"], "cases": []}

    def _issues_with_cluster(self, doc) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            routing = dst / "evals" / "routing"
            routing.mkdir(parents=True)
            payload = doc if isinstance(doc, str) else json.dumps(doc)
            (routing / "cluster.json").write_text(payload, encoding="utf-8")
            return validate_fleet.validate_routing_clusters(dst, ["builder"], ["craft"])

    def test_well_formed_cluster_passes(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "pos-a", "prompt": "p", "polarity": "positive", "expect_fires": ["craft"]},
            {"id": "neg-a", "prompt": "p", "polarity": "negative",
             "expect_not_fires": ["craft", "builder"]},
            {"id": "neg-default", "prompt": "p", "polarity": "negative"},
        ])
        self.assertEqual([], self._issues_with_cluster(doc))

    def test_typoed_polarity_is_reported(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "bad", "prompt": "p", "polarity": "positve", "expect_fires": ["craft"]},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(
            any("polarity" in i and "positive or negative" in i for i in issues), issues
        )

    def test_empty_positive_expectation_is_reported(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "bad", "prompt": "p", "polarity": "positive", "expect_fires": []},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("expect_fires" in i and "non-empty list" in i for i in issues), issues)

    def test_empty_explicit_negative_forbidden_set_is_reported(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "bad", "prompt": "p", "polarity": "negative", "expect_not_fires": []},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(
            any("expect_not_fires" in i and "non-empty list" in i for i in issues), issues
        )

    def test_expectation_fields_reject_wrong_types(self) -> None:
        cases = [
            {"id": "bad-pos", "prompt": "p", "polarity": "positive", "expect_fires": "craft"},
            {"id": "bad-neg", "prompt": "p", "polarity": "negative",
             "expect_not_fires": "craft"},
        ]
        issues = self._issues_with_cluster(dict(self.BASE, cases=cases))
        self.assertTrue(any("bad-pos" in i and "expect_fires" in i for i in issues), issues)
        self.assertTrue(any("bad-neg" in i and "expect_not_fires" in i for i in issues), issues)

    def test_required_case_fields_are_reported(self) -> None:
        cases = [
            {"prompt": "p", "polarity": "negative"},
            {"id": "missing-prompt", "polarity": "negative"},
            {"id": "missing-polarity", "prompt": "p"},
            {"id": "missing-positive-targets", "prompt": "p", "polarity": "positive"},
        ]
        issues = self._issues_with_cluster(dict(self.BASE, cases=cases))
        self.assertTrue(any("non-empty 'id'" in i for i in issues), issues)
        self.assertTrue(
            any("missing-prompt" in i and "non-empty 'prompt'" in i for i in issues), issues
        )
        self.assertTrue(any("missing-polarity" in i and "polarity" in i for i in issues), issues)
        self.assertTrue(
            any("missing-positive-targets" in i and "expect_fires" in i for i in issues),
            issues,
        )

    def test_cases_must_be_a_non_empty_list(self) -> None:
        for cases in (None, {}, []):
            with self.subTest(cases=cases):
                issues = self._issues_with_cluster(dict(self.BASE, cases=cases))
                self.assertTrue(any("non-empty 'cases' list" in i for i in issues), issues)

    def test_cluster_name_is_required(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "neg-a", "prompt": "p", "polarity": "negative"},
        ])
        del doc["cluster"]
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("non-empty 'cluster' string" in i for i in issues), issues)

    def test_member_names_reject_wrong_types(self) -> None:
        doc = dict(self.BASE, members=["craft", {"not": "a name"}], cases=[
            {"id": "pos-a", "prompt": "p", "polarity": "positive", "expect_fires": ["craft"]},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("member #2" in i and "component name" in i for i in issues), issues)

    def test_each_case_must_be_an_object(self) -> None:
        issues = self._issues_with_cluster(dict(self.BASE, cases=["not-an-object"]))
        self.assertTrue(any("case #1 is not an object" in i for i in issues), issues)

    def test_unresolvable_member_is_reported(self) -> None:
        issues = self._issues_with_cluster(dict(self.BASE, members=["craft", "no-such-component"]))
        self.assertTrue(any("not a fleet component" in i for i in issues), issues)

    def test_duplicate_case_ids_are_reported(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "pos-a", "prompt": "p", "polarity": "positive", "expect_fires": ["craft"]},
            {"id": "pos-a", "prompt": "q", "polarity": "positive", "expect_fires": ["craft"]},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("duplicate case id" in i for i in issues), issues)

    def test_nonmember_forbidden_target_is_reported(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "neg-a", "prompt": "p", "polarity": "negative",
             "expect_not_fires": ["no-such-component"]},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("forbids" in i for i in issues), issues)

    def test_unparseable_cluster_file_is_reported(self) -> None:
        issues = self._issues_with_cluster("not json {")
        self.assertTrue(any("unreadable cluster file" in i for i in issues), issues)

    def test_reintroducing_the_observed_inconsistency_is_reported(self) -> None:
        # The exact defect EVAL-001 was opened on, proven against a COPY of the real repository
        # rather than a synthetic shape that could drift away from the actual cluster file.
        with repo_copy() as dst:
            path = dst / "evals" / "routing" / "craft-vs-fullstack.json"
            doc = json.loads(path.read_text(encoding="utf-8"))
            case = next(c for c in doc["cases"] if c["id"] == "pos-ci-actions-harden")
            case["expect_fires"].append("code-reviewer")
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertTrue(
            any("pos-ci-actions-harden" in i and "outside the cluster's members" in i
                for i in issues),
            issues,
        )

class AdapterCheckTierTests(unittest.TestCase):
    """The T0/T1 tier boundary for adapter byte-drift.

    check_adapters=False exists so the wiring mutation tests stop re-generating and
    byte-comparing every host adapter to check one unrelated breakage. These two tests pin the
    flag's semantics: True still reports drift (so retiring the recipe's separate
    `generate --check` step loses nothing), and False genuinely skips it (so the speedup is
    real, and a future adapter test that forgets to pass True fails loudly — its expected issue
    never appears — instead of passing vacuously)."""

    def _drift_adapter(self, dst: Path) -> None:
        adapter = sorted((dst / ".github" / "agents").glob("*.md"))[0]
        adapter.write_text(
            adapter.read_text(encoding="utf-8") + "\nhand edit\n", encoding="utf-8"
        )

    def test_flag_on_reports_hand_edited_adapter(self) -> None:
        with repo_copy() as dst:
            self._drift_adapter(dst)
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=True
            )
        self.assertTrue(issues, "hand-edited adapter must be reported when the check runs")

    def test_flag_off_skips_only_the_adapter_check(self) -> None:
        with repo_copy() as dst:
            self._drift_adapter(dst)
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertEqual(
            [],
            issues,
            "the only defect is adapter drift; skipping the adapter check must leave a clean "
            "report",
        )


if __name__ == "__main__":
    unittest.main()
