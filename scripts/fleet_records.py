#!/usr/bin/env python3
"""Typed, read-only records of what the canonical fleet declares.

This module owns the fleet's ONE parser for frontmatter, `tools:` values, and namespaced
cross-references. `validate_fleet.py` and `fleet_doctor.py` use these shared readers so their
interpretations of a definition cannot drift through separate parsers.

It records; it never judges. Every policy question -- is this tool adopted, is this description too
long, is this reference resolvable -- stays in `validate_fleet.py`.

The inspected tree is DATA. Nothing under the caller-supplied root is imported or executed, so a
foreign checkout or a frozen baseline is safe to parse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
LIST_ITEM_RE = re.compile(r"^\s*-\s+(\S.*?)\s*$")


# --------------------------------------------------------------------------------------
# Parsing primitives (moved verbatim from validate_fleet.py, which re-exports them)
# --------------------------------------------------------------------------------------


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def try_read_text(path: Path) -> str | None:
    """Read a file, or return None when it cannot be decoded.

    An inspected tree is arbitrary bytes: a definition containing invalid UTF-8 raised
    UnicodeDecodeError mid-collection, so the CLI printed a traceback and the damaged file never
    reached the unreadable list it exists to name. Returning None lets the caller record the path
    and keep producing an explicitly incomplete artifact.
    """
    try:
        return read_text(path)
    except (UnicodeDecodeError, OSError):
        return None


def is_runtime_byproduct(path: Path) -> bool:
    """Return whether a path is Python execution residue, not distributable fleet source."""

    return "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo"}


def split_tools(raw: str) -> list[str]:
    """Split a `tools:` value on top-level commas only.

    A naive ``raw.split(",")`` shreds a scoped grant: `Agent(worker, researcher)` becomes
    `Agent(worker` and `researcher)`. Splitting at paren depth 0 keeps the scope intact so it can be
    judged rather than mangled into two bogus tool names.
    """
    entries: list[str] = []
    depth = 0
    current: list[str] = []
    for char in raw:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            entries.append("".join(current))
            current = []
            continue
        current.append(char)
    entries.append("".join(current))
    return [entry.strip(" []'\"") for entry in entries if entry.strip(" []'\"")]


def frontmatter_span(lines: list[str]) -> int | None:
    """Return the closing marker index for a complete frontmatter block."""

    if not lines or lines[0].strip() != "---":
        return None
    return next(
        (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
        None,
    )


def parse_frontmatter_lines(lines: list[str], end: int) -> dict[str, str] | None:
    """Parse the fleet's YAML subset from one already-decoded source snapshot."""

    fields: dict[str, str] = {}
    i = 1
    while i < end:
        if not lines[i].strip() or lines[i].lstrip().startswith("#"):
            i += 1
            continue

        match = TOP_LEVEL_KEY_RE.match(lines[i])
        if not match:
            # Skipping an unparseable line loses whatever it configured without a word: a typo'd
            # `tools Read, Write` would read as no tools authority at all, and the file would
            # validate. Refuse the block instead so the caller reports it.
            return None

        key, value = match.groups()
        if key in fields:
            # YAML keeps the last duplicate. A file carrying `model: opus` then `model: inherit`
            # would validate against a value its author never intended to be the live one.
            return None
        value = value.strip()
        if value in {">", ">-", "|", "|-"}:
            parts: list[str] = []
            i += 1
            while i < end and not TOP_LEVEL_KEY_RE.match(lines[i]):
                parts.append(lines[i].strip())
                i += 1
            fields[key] = " ".join(part for part in parts if part).strip()
            continue

        if not value:
            # An empty inline value can mean a YAML block sequence follows (`skills:` then indented
            # `- item` lines). Collect it so a value like `skills:` doesn't silently become "" with
            # nothing downstream ever able to check it -- see LIST_ITEM_RE.
            # Skip blank lines and comments within the sequence, mirroring the outer loop, so that
            # `skills:\n  # note\n  - item` doesn't leave `- item` stranded in the outer loop
            # where it fails TOP_LEVEL_KEY_RE and returns None.
            items: list[str] = []
            j = i + 1
            while j < end:
                line = lines[j]
                if not line.strip() or line.lstrip().startswith("#"):
                    j += 1
                    continue
                item_match = LIST_ITEM_RE.match(line)
                if not item_match:
                    break
                items.append(item_match.group(1).strip("'\""))
                j += 1
            if items:
                fields[key] = ", ".join(items)
                i = j
                continue

        fields[key] = value.strip("'\"")
        i += 1

    return fields


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
