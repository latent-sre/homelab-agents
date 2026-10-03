"""Namespaced cross-reference records of the canonical fleet, read once and never judged.

The rules in `fleet/rules/` read these records; the judgments stay in the rules.

The inspected tree is DATA. Nothing under the caller-supplied root is imported or executed, so a
foreign checkout is safe to parse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fleet import fs
from fleet.frontmatter import parse_lines, span


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    """Parse the small YAML subset used by the fleet frontmatter."""

    lines = fs.read_text(path).splitlines()
    end = span(lines)
    return None if end is None else parse_lines(lines, end)


def definition_markdown_files(root: Path) -> list[Path]:
    """Every markdown file the fleet ships as behavior: agent bodies, SKILL.md files, and each
    skill's references/ and assets/ — the surface a cross-reference or platform-fact rule must
    cover, because all of it is loaded (or read by path) into real sessions."""
    files = sorted((root / "agents").glob("*.md")) if (root / "agents").is_dir() else []
    if (root / "skills").is_dir():
        files += sorted((root / "skills").rglob("*.md"))
    return files


def namespaced_reference_re(plugin_name: str) -> re.Pattern[str]:
    """The fleet's one namespaced-reference matcher.

    Captures uppercase and invalid punctuation deliberately so malformed syntax is REJECTED by the
    validator rather than skipped or truncated to a valid prefix -- a prefix matcher would certify
    `code-reviewer_v2` as `code-reviewer`, and nothing at runtime checks either.
    """
    return re.compile(
        rf"(?<![\w/.-])(?P<slash>/)?{re.escape(plugin_name)}:"
        r"(?P<target>[^\s`'\"<>()\[\]{},;!?]*)"
    )


@dataclass(frozen=True)
class Reference:
    """One namespaced cross-reference occurrence and where it was written."""

    target: str
    path: Path
    line: int  # 1-indexed
    is_slash_command: bool


def collect_references(
    root: Path, plugin_name: str, *, texts: dict[Path, str | None] | None = None
) -> tuple[Reference, ...]:
    """Every namespaced-reference occurrence across the fleet's markdown surface.

    Matching runs over RAW source lines, not over parsed field values. The validator's dangling-
    reference rule reads the same raw text, and a collector that scanned re-joined frontmatter
    instead would silently stop seeing references the validator still rejects.
    """
    if not plugin_name:
        return ()
    pattern = namespaced_reference_re(plugin_name)
    found: list[Reference] = []

    # `texts` lets a snapshot that already read every definition feed the collector the same
    # bytes its other rules judged; without it the collector reads the tree itself.
    paths = sorted(texts) if texts is not None else definition_markdown_files(root)
    for path in paths:
        text = texts[path] if texts is not None else fs.try_read_text(path)
        if text is None:
            continue
        for index, line_text in enumerate(text.splitlines()):
            for match in pattern.finditer(line_text):
                found.append(
                    Reference(
                        target=match.group("target").rstrip(".:"),
                        path=path,
                        line=index + 1,
                        is_slash_command=bool(match.group("slash")),
                    )
                )
    return tuple(found)
