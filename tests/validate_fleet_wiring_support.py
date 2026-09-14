from __future__ import annotations

import unittest
from pathlib import Path

from scripts import validate_fleet
from tests.support import repo_copy


def _add_guarded_name(repo: Path, name: str) -> None:
    """Add one name to a repo COPY's GUARDED_AGENT_NAMES, whatever formatting the literal uses.

    The mutation tests below used to string-match the whole single-line frozenset, so extending the
    real roster broke them by silently mutating nothing — a green test that no longer tested
    anything. Anchoring on the first member instead survives reformatting.
    """
    path = repo / "scripts" / "readonly-guard.py"
    source = path.read_text(encoding="utf-8")
    anchor = '"code-reviewer"'
    assert anchor in source, "GUARDED_AGENT_NAMES no longer contains the expected anchor"
    path.write_text(source.replace(anchor, f'{anchor}, "{name}"', 1), encoding="utf-8")

READONLY_BASH_AGENT = (
    "---\n"
    "name: auditor\n"
    "description: Use when auditing something read-only.\n"
    "tools: Read, Grep, Bash\n"
    "model: inherit\n"
    "---\n\n"
    "# Auditor\n\n"
    "## Review packet\n\n"
    "- **Changed**: nothing.\n"
)


class PluginWiringMixin:
    """Shared copy-and-validate fixture for independently scheduled wiring-test shards."""

    def _issues_after(
        self: unittest.TestCase, mutate, *, check_adapters: bool = False
    ) -> list[str]:
        with repo_copy() as dst:
            mutate(dst)
            # Each test checks one deliberate breakage. Only adapter mutations pay for the
            # generated-byte comparison; AdapterCheckTierTests pins both sides of this tier.
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=check_adapters
            )
            return issues
