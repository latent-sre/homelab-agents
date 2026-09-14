"""Shared member metadata and source-attributed reference records."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import fleet_records
from tests.support import REPO

PLUGIN = json.loads(
    (REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
)["name"]


def _tree() -> TemporaryDirectory:
    """A minimal tree carrying one agent and one skill."""
    handle = TemporaryDirectory()
    root = Path(handle.name)
    (root / "agents").mkdir()
    (root / "skills" / "demo-skill").mkdir(parents=True)
    (root / "agents" / "demo-agent.md").write_text(
        "---\n"
        "name: demo-agent\n"
        f"description: Routes to {PLUGIN}:demo-skill when asked.\n"
        "tools: Read, Grep\n"
        "skills:\n"
        "  - demo-skill\n"
        "---\n\n"
        f"Body mentions /{PLUGIN}:demo-skill once.\n",
        encoding="utf-8",
    )
    (root / "skills" / "demo-skill" / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: A demo skill.\n---\n\nBody.\n",
        encoding="utf-8",
    )
    return handle


class ReferenceRecordTests(unittest.TestCase):
    def test_surface_and_line_are_recorded_per_occurrence(self):
        handle = _tree()
        with handle:
            references = fleet_records.collect_references(Path(handle.name), PLUGIN)
        surfaces = {r.surface for r in references}
        self.assertEqual(surfaces, {"description", "body"})
        for reference in references:
            self.assertEqual(reference.source, "demo-agent")
            self.assertEqual(reference.target, "demo-skill")
            self.assertGreater(reference.line, 0)
        body = next(r for r in references if r.surface == "body")
        self.assertTrue(body.is_slash_command)
        self.assertEqual(body.raw, f"/{PLUGIN}:demo-skill")

    def test_reference_lines_point_at_the_real_source_line(self):
        handle = _tree()
        with handle:
            root = Path(handle.name)
            references = fleet_records.collect_references(root, PLUGIN)
            lines = (root / "agents" / "demo-agent.md").read_text(encoding="utf-8").splitlines()
            for reference in references:
                self.assertIn(reference.raw, lines[reference.line - 1])

    def test_a_reference_in_another_frontmatter_field_gets_its_own_surface(self):
        """The third surface value, which previously had no firing test at all. Folding it into
        description or body would count a reference where no reader sees one."""
        handle = _tree()
        with handle:
            root = Path(handle.name)
            skill = root / "skills" / "demo-skill" / "SKILL.md"
            skill.write_text(
                "---\nname: demo-skill\ndescription: A demo skill.\n"
                f"argument-hint: pass {PLUGIN}:demo-agent\n---\n\nBody.\n",
                encoding="utf-8",
            )
            references = fleet_records.collect_references(root, PLUGIN)
        surfaces = {r.surface for r in references if r.path == skill}
        self.assertEqual(surfaces, {"frontmatter"})

    def test_bundled_reference_files_are_attributed_to_their_skill(self):
        handle = _tree()
        with handle:
            root = Path(handle.name)
            bundle = root / "skills" / "demo-skill" / "references"
            bundle.mkdir()
            (bundle / "detail.md").write_text(f"See {PLUGIN}:demo-agent.\n", encoding="utf-8")
            references = fleet_records.collect_references(root, PLUGIN)
        bundled = [r for r in references if r.path.name == "detail.md"]
        self.assertEqual(len(bundled), 1)
        self.assertEqual(bundled[0].source, "demo-skill")
        self.assertFalse(bundled[0].in_core_definition)


class MemberRecordTests(unittest.TestCase):
    def test_block_sequence_and_inline_tools_both_parse(self):
        """An inline-only reader scores block-sequence agents zero and still totals a plausible
        number -- measured as 58 against a true 85 while reproducing the decision's snapshot."""
        inline = fleet_records.parse_frontmatter(REPO / "agents" / "code-reviewer.md")
        block = fleet_records.parse_frontmatter(REPO / "agents" / "researcher.md")
        self.assertGreater(len(fleet_records.split_tools(inline["tools"])), 0)
        self.assertGreater(len(fleet_records.split_tools(block["tools"])), 3)

    def test_member_fields_preserve_absent_and_empty_tools(self):
        """Missing and explicitly empty authority must remain different parsed records."""
        handle = _tree()
        with handle:
            root = Path(handle.name)
            agent = root / "agents" / "demo-agent.md"
            agent.write_text(
                agent.read_text(encoding="utf-8").replace("tools: Read, Grep", "tools: ''"),
                encoding="utf-8",
            )
            members = {member.name: member for member in fleet_records.collect(root).members}
        self.assertEqual("", members["demo-agent"].fields["tools"])
        self.assertNotIn("tools", members["demo-skill"].fields)


if __name__ == "__main__":
    unittest.main()
