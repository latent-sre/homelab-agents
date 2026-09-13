#!/usr/bin/env python3
"""Typed, read-only records of what the canonical fleet declares.

This module is the instruments' import path for the fleet's ONE set of readers: the frontmatter
dialect (`fleet/frontmatter.py`), the filesystem primitives (`fleet/fs.py`), and the member and
cross-reference records (`fleet/references.py`). Every name is re-exported here unchanged so
`validate_fleet.py`, `fleet_doctor.py`, the generator, and the tests keep reaching them as
`fleet_records.<name>`; the implementations live in the kernel, once.

It records; it never judges. Every policy question -- is this tool adopted, is this description too
long, is this reference resolvable -- stays with the rules in `fleet/rules/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `import fleet` must resolve both under the test suite (repository root on sys.path via the cwd)
# and when a script is run as `python3 scripts/<name>.py`, where only `scripts/` is on the path.
_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fleet import frontmatter as _frontmatter  # noqa: E402
from fleet import fs as _fs  # noqa: E402
from fleet.references import (  # noqa: E402
    FleetRecords,
    Member,
    Reference,
    collect,
    collect_references,
    core_definition_paths,
    definition_markdown_files,
    namespaced_reference_re,
    parse_frontmatter,
)

NAME_RE = _frontmatter.NAME_RE
TOP_LEVEL_KEY_RE = _frontmatter.TOP_LEVEL_KEY_RE
LIST_ITEM_RE = _frontmatter.LIST_ITEM_RE

read_text = _fs.read_text
try_read_text = _fs.try_read_text
is_runtime_byproduct = _fs.is_runtime_byproduct
split_tools = _frontmatter.split_tools
frontmatter_span = _frontmatter.span
parse_frontmatter_lines = _frontmatter.parse_lines

__all__ = [
    "FleetRecords", "Member", "Reference", "collect", "collect_references",
    "core_definition_paths", "definition_markdown_files", "namespaced_reference_re",
    "parse_frontmatter", "NAME_RE", "TOP_LEVEL_KEY_RE", "LIST_ITEM_RE", "read_text",
    "try_read_text", "is_runtime_byproduct", "split_tools", "frontmatter_span",
    "parse_frontmatter_lines",
]
