"""The README's generated fleet inventory must match the definitions on disk."""

from __future__ import annotations

import re
from pathlib import Path

from fleet import fs
from fleet.findings import Finding
from fleet.rules import rule
from fleet.snapshot import Fleet

INVENTORY_RE = re.compile(
    r"<!-- fleet-inventory:start -->.*?<!-- fleet-inventory:end -->",
    re.DOTALL,
)


def render_inventory(agent_names: list[str], skill_names: list[str]) -> str:
    agents = ", ".join(f"`{name}`" for name in agent_names)
    skills = ", ".join(f"`{name}`" for name in skill_names)
    return "\n".join(
        [
            "<!-- fleet-inventory:start -->",
            f"- **Agents ({len(agent_names)}):** {agents}",
            f"- **Skills ({len(skill_names)}):** {skills}",
            "<!-- fleet-inventory:end -->",
        ]
    )


def replace_inventory(content: str, expected: str) -> str:
    if not INVENTORY_RE.search(content):
        raise ValueError("missing fleet inventory markers")
    newline = "\r\n" if "\r\n" in content else "\n"
    return INVENTORY_RE.sub(expected.replace("\n", newline), content, count=1)


def write_inventory(readme: Path, expected: str) -> None:
    if not readme.is_file():
        raise ValueError(f"{readme}: missing README.md")
    content = readme.read_bytes().decode("utf-8")
    try:
        updated = replace_inventory(content, expected)
    except ValueError as exc:
        raise ValueError(f"{readme}: {exc}") from exc
    readme.write_bytes(updated.encode("utf-8"))


def inventory_findings(root: Path, expected: str) -> list[Finding]:
    readme = root / "README.md"
    if not readme.is_file():
        return [Finding("inventory", f"{readme}: missing README.md", readme)]
    match = INVENTORY_RE.search(fs.read_text(readme))
    if not match:
        return [Finding("inventory", f"{readme}: missing fleet inventory markers", readme)]
    if match.group(0) != expected:
        return [
            Finding(
                "inventory",
                f"{readme}: fleet inventory drifted; run "
                "`python scripts/validate_fleet.py --write-inventory`",
                readme,
            )
        ]
    return []


@rule(
    "inventory",
    group="inventory",
    why="The README inventory is generated; a stale one advertises a fleet that does not ship.",
)
def inventory(fleet: Fleet) -> list[Finding]:
    return inventory_findings(fleet.root, render_inventory(fleet.agent_names, fleet.skill_names))
