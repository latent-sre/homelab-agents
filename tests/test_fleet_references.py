"""Namespaced reference records: where each occurrence was written, read off raw source lines."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fleet.references import collect_references
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
    def test_each_occurrence_carries_its_real_source_line(self) -> None:
        handle = _tree()
        with handle:
            root = Path(handle.name)
            references = collect_references(root, PLUGIN)
            lines = (root / "agents" / "demo-agent.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual(2, len(references))
        for reference in references:
            self.assertEqual("demo-skill", reference.target)
            self.assertIn(f"{PLUGIN}:demo-skill", lines[reference.line - 1])
        self.assertEqual(
            [False, True], [reference.is_slash_command for reference in references]
        )

    def test_a_skills_bundled_reference_file_is_scanned(self) -> None:
        handle = _tree()
        with handle:
            root = Path(handle.name)
            bundle = root / "skills" / "demo-skill" / "references"
            bundle.mkdir()
            (bundle / "detail.md").write_text(f"See {PLUGIN}:demo-agent.\n", encoding="utf-8")
            references = collect_references(root, PLUGIN)
        self.assertEqual(1, len([r for r in references if r.path.name == "detail.md"]))


if __name__ == "__main__":
    unittest.main()
