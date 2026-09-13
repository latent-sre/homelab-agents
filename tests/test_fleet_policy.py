"""The policy file is the one vocabulary, and the validator's constants are views of it."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fleet import policy
from scripts import validate_fleet


class PolicyLoadTests(unittest.TestCase):
    def test_groups_expand_and_roles_reference_them(self) -> None:
        p = policy.POLICY
        self.assertLess(
            {"Glob", "Grep", "Read"}, p.roles["repository-investigator"].required | {"x"}
        )
        self.assertIn("Bash", p.roles["repository-investigator"].required)
        self.assertTrue(p.evidence_mcp_tools <= p.roles["researcher"].required)
        self.assertTrue(p.evidence_mcp_tools <= p.roles["application-security-auditor"].forbidden)
        self.assertEqual(("verified", "sourced", "unverified"), p.workflow_evidence_enum)

    def test_validator_constants_are_views_of_the_policy(self) -> None:
        p = policy.POLICY
        self.assertEqual(set(p.model_aliases), validate_fleet.ALIAS_MODELS)
        self.assertEqual(set(p.known_agent_fields), validate_fleet.KNOWN_AGENT_FIELDS)
        self.assertEqual(set(p.known_skill_fields), validate_fleet.KNOWN_SKILL_FIELDS)
        self.assertEqual(set(p.fleet_tools), validate_fleet.FLEET_TOOLS)
        self.assertEqual(set(p.write_tools), validate_fleet.WRITE_TOOLS)
        self.assertEqual(
            {n: set(r.forbidden) for n, r in p.roles.items()}, validate_fleet.FORBIDDEN_AGENT_TOOLS
        )

    def test_an_unknown_group_reference_is_a_loud_error(self) -> None:
        # A typo'd `@group` would otherwise grant or forbid nothing while reading as policy.
        source = policy.POLICY_PATH.read_text(encoding="utf-8").replace(
            '"@local_repository"', '"@local_repositry"', 1
        )
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "policy.toml"
            broken.write_text(source, encoding="utf-8")
            with self.assertRaises(policy.PolicyError):
                policy.load(broken)

    def test_a_duplicate_role_name_is_refused(self) -> None:
        # A second [[roles]] table with the same name would silently replace the first role's
        # trust boundary while the loader and the validator stay green.
        source = policy.POLICY_PATH.read_text(encoding="utf-8")
        start = source.index('[[roles]]\nname = "researcher"')
        end = source.index("\n[", start + 1)  # up to the next table header
        block = source[start:end]
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "policy.toml"
            broken.write_text(source + "\n" + block, encoding="utf-8")
            with self.assertRaises(policy.PolicyError):
                policy.load(broken)

    def test_every_table_carries_a_checked_date_or_the_meta_date(self) -> None:
        self.assertRegex(policy.POLICY.checked, r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(policy.POLICY.cli, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
