"""Member and cross-reference records of the canonical fleet, read once and never judged.

Moved verbatim from `scripts/fleet_records.py`, which re-exports every name here so the
instruments and tests keep their import paths. The rules in `fleet/rules/` and the doctor read
these records; the judgments stay in the rules.

The inspected tree is DATA. Nothing under the caller-supplied root is imported or executed, so a
foreign checkout or a frozen baseline is safe to parse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fleet import fs
from fleet.frontmatter import TOP_LEVEL_KEY_RE, parse_lines, span

read_text = fs.read_text
try_read_text = fs.try_read_text
frontmatter_span = span
parse_frontmatter_lines = parse_lines


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    """Parse the small YAML subset used by the fleet frontmatter."""

    lines = read_text(path).splitlines()
    end = frontmatter_span(lines)
    return None if end is None else parse_frontmatter_lines(lines, end)


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


# --------------------------------------------------------------------------------------
# Typed records
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Member:
    """One canonical fleet member: an agent or a skill."""

    name: str
    kind: str  # "agent" | "skill"
    fields: dict[str, str]

    @property
    def description(self) -> str:
        return self.fields.get("description", "")


@dataclass(frozen=True)
class Reference:
    """One namespaced cross-reference occurrence with its source location and context."""

    source: str  # owning member; a skill's references/ file is attributed to that skill
    target: str
    path: Path
    line: int  # 1-indexed
    # "description" | "body" | "frontmatter". The third is a reference in some OTHER frontmatter
    # field: rare, but it must not be folded into either of the first two, because a consumer
    # counting description-vs-body surfaces would then count something a reader never sees there.
    surface: str
    in_core_definition: bool  # agents/*.md or skills/*/SKILL.md, vs a bundled references/ file
    is_slash_command: bool
    raw: str  # exact reference form as written


@dataclass(frozen=True)
class FleetRecords:
    """Parsed member metadata and definitions whose metadata could not be read."""

    members: tuple[Member, ...] = ()
    # Definitions whose frontmatter the parser refused. These are NOT members -- they carry no
    # usable identity. The doctor needs their paths to avoid reporting a misleading listing total.
    unparseable: tuple[Path, ...] = ()


# --------------------------------------------------------------------------------------
# Collection
# --------------------------------------------------------------------------------------


def _member_for_path(path: Path, root: Path) -> str:
    """The member a definition file belongs to.

    A skill's references/ and assets/ files are not members; they are that skill's surface, so
    their references are attributed to the owning skill rather than dropped.
    """
    rel = path.relative_to(root)
    if rel.parts[0] == "agents":
        return path.stem
    return rel.parts[1]


def _surface_of_line(index: int, end: int | None, description_lines: set[int]) -> str:
    """Classify one 0-indexed source line as description, other frontmatter, or body."""
    if end is None or index > end:
        return "body"
    if index in description_lines:
        return "description"
    # A namespaced reference in some OTHER frontmatter field is neither routing text nor prose.
    # It gets its own label rather than being folded into either series, because silently counting
    # it as one of them is how a surface metric starts disagreeing with what a reader sees.
    return "frontmatter"


def _description_line_span(lines: list[str], end: int) -> set[int]:
    """0-indexed lines carrying the description value, including YAML continuations."""
    span: set[int] = set()
    capturing = False
    for index in range(1, end):
        line = lines[index]
        match = TOP_LEVEL_KEY_RE.match(line)
        if match:
            capturing = match.group(1) == "description"
            if capturing:
                span.add(index)
            continue
        if capturing and line.strip():
            span.add(index)
    return span


def collect_references(root: Path, plugin_name: str) -> tuple[Reference, ...]:
    """Every namespaced-reference occurrence across the fleet's markdown surface.

    Matching runs over RAW source lines, not over parsed field values. The validator's dangling-
    reference rule reads the same raw text, and a collector that scanned re-joined frontmatter
    instead would silently stop seeing references the validator still rejects -- two views of one
    tree that disagree, which is exactly what this module exists to prevent.

    Preserve each occurrence's line and surface before consumers deduplicate references.
    """
    if not plugin_name:
        return ()
    pattern = namespaced_reference_re(plugin_name)
    core = core_definition_paths(root)
    found: list[Reference] = []

    for path in definition_markdown_files(root):
        text = try_read_text(path)
        if text is None:
            continue  # recorded as unreadable by collect(); no references can be read from it
        lines = text.splitlines()
        end = frontmatter_span(lines)
        description_lines = _description_line_span(lines, end) if end is not None else set()
        source = _member_for_path(path, root)
        in_core = path in core
        for index, line_text in enumerate(lines):
            for match in pattern.finditer(line_text):
                found.append(
                    Reference(
                        source=source,
                        target=match.group("target").rstrip(".:"),
                        path=path,
                        line=index + 1,
                        surface=_surface_of_line(index, end, description_lines),
                        in_core_definition=in_core,
                        is_slash_command=bool(match.group("slash")),
                        raw=match.group(0),
                    )
                )
    return tuple(found)


def core_definition_paths(root: Path) -> set[Path]:
    """The files a member's own identity is declared in: agents/*.md and skills/*/SKILL.md.

    Reference records distinguish these declarations from bundled reference and asset files.
    """
    paths = set((root / "agents").glob("*.md")) if (root / "agents").is_dir() else set()
    if (root / "skills").is_dir():
        paths |= set((root / "skills").glob("*/SKILL.md"))
    return paths


def collect(root: Path) -> FleetRecords:
    """Collect canonical member metadata without scanning unrelated guards or routing files."""

    members: list[Member] = []
    unparseable: list[Path] = []

    for kind, paths in (
        ("agent", sorted((root / "agents").glob("*.md"))),
        ("skill", sorted((root / "skills").glob("*/SKILL.md"))),
    ):
        for path in paths:
            text = try_read_text(path)
            if text is None:
                unparseable.append(path)
                continue
            lines = text.splitlines()
            end = frontmatter_span(lines)
            fields = None if end is None else parse_frontmatter_lines(lines, end)
            if fields is None:
                unparseable.append(path)
                continue
            fallback = path.stem if kind == "agent" else path.parent.name
            members.append(Member(fields.get("name", fallback), kind, dict(fields)))

    return FleetRecords(members=tuple(members), unparseable=tuple(unparseable))
