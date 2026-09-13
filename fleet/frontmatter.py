"""The fleet's frontmatter DIALECT: the one reader, its strict companion, and its emitter.

This is deliberately not a YAML parser, and the reason is the design fact that governs every
line here: **the hosts that load these definitions are the oracle, and they are not conforming
YAML parsers either.** Claude Code's documented `argument-hint: [issue-number]` is a bare flow
sequence to a conforming parser and a string to the host. A file must therefore stay inside the
subset every host reads identically, and this module reads exactly that subset -- refusing,
never guessing, at anything outside it, because a misread frontmatter line silently changes what
a definition configures (a typo'd `tools Read, Write` would read as no tools authority at all,
and the file would validate).

Three pieces, kept together on purpose because they used to live in two files and drift:

* `span` / `parse_lines` -- the reader (moved verbatim from `scripts/fleet_records.py`).
* `flow_scalar_defect` -- the strict check a reader that reads to end of line cannot make on its
  own (moved verbatim from `scripts/validate_fleet.py`). It names why a quoted scalar the reader
  accepted would be refused by a conforming parser, or mangled by THIS one.
* `yaml_scalar` / `yaml_flow_list` -- the emitter. A JSON string is a valid YAML 1.2 double-quoted
  scalar, and a JSON list of strings a valid flow sequence; every generated host copy re-serializes
  through these two functions so the emitted subset is documented in one place.

The differential tripwire in `tests/test_fleet_frontmatter.py` runs a conforming parser beside
this one over every canonical definition and pins the exact class of divergence the dialect
allows, so a new divergence fails a test instead of shipping.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
LIST_ITEM_RE = re.compile(r"^\s*-\s+(\S.*?)\s*$")

_BLOCK_SCALAR_MARKERS = frozenset({">", ">-", "|", "|-"})


def span(lines: Sequence[str]) -> int | None:
    """The index of the closing `---` of a complete frontmatter block, or None.

    Claude Code reads frontmatter only when the opening `---` is the file's FIRST line; a file
    that opens anywhere else is treated as plain content, so it is treated as no frontmatter here.
    """
    if not lines or lines[0].strip() != "---":
        return None
    return next(
        (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
        None,
    )


def parse_lines(lines: Sequence[str], end: int) -> dict[str, str] | None:
    """Parse the dialect from an already-split source, or None when a line is outside it.

    Every value is returned as a string: a block sequence is joined with ", " so that `tools:`
    written inline and written as a list read identically downstream, and a folded or literal
    block scalar is joined with single spaces. Quotes surrounding a value are stripped and
    nothing inside them is unescaped -- which is exactly why `flow_scalar_defect` exists.
    """
    fields: dict[str, str] = {}
    i = 1
    while i < end:
        if not lines[i].strip() or lines[i].lstrip().startswith("#"):
            i += 1
            continue

        match = TOP_LEVEL_KEY_RE.match(lines[i])
        if not match:
            # Skipping an unparseable line loses whatever it configured without a word. Refuse
            # the block instead so the caller reports it.
            return None

        key, value = match.groups()
        if key in fields:
            # YAML keeps the last duplicate. A file carrying `model: opus` then `model: inherit`
            # would validate against a value its author never intended to be the live one.
            return None
        value = value.strip()
        if value in _BLOCK_SCALAR_MARKERS:
            parts: list[str] = []
            i += 1
            while i < end and not TOP_LEVEL_KEY_RE.match(lines[i]):
                parts.append(lines[i].strip())
                i += 1
            fields[key] = " ".join(part for part in parts if part).strip()
            continue

        if not value:
            # An empty inline value can mean a block sequence follows (`skills:` then indented
            # `- item` lines). Collect it so `skills:` doesn't silently become "" with nothing
            # downstream ever able to check it. Blank lines and comments inside the sequence are
            # skipped, mirroring the outer loop, so `skills:\n  # note\n  - item` doesn't leave
            # `- item` stranded where it fails TOP_LEVEL_KEY_RE and refuses the block.
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


def parse_text(text: str) -> dict[str, str] | None:
    """Parse a whole definition's frontmatter, or None when absent, unterminated, or refused."""
    lines = text.splitlines()
    end = span(lines)
    return None if end is None else parse_lines(lines, end)


def split_tools(raw: str) -> list[str]:
    """Split a `tools:` value on top-level commas only.

    A naive `raw.split(",")` shreds a scoped grant: `Agent(worker, researcher)` becomes
    `Agent(worker` and `researcher)`. Splitting at paren depth 0 keeps the scope intact so it can
    be judged rather than mangled into two bogus tool names.
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


# YAML's complete double-quoted escape set (spec 1.2 s7.3.1): these single characters, plus
# `\x`/`\u`/`\U` with exactly 2/4/8 hex digits. Anything else is "found unknown escape character"
# and the parser refuses the document. Skipping backslash-plus-one unconditionally let
# `description: "Use C:\q"` through (review finding, PR #120) -- a Windows path in a description
# is exactly how an author writes that by accident. Single-quoted scalars are deliberately absent
# from this map: YAML gives them no backslash escapes at all, so a backslash there is one literal
# character and validating it would invent a rule the parser does not have.
_DOUBLE_QUOTE_ESCAPES = frozenset('0abtnvfre"/\\N_LP \t')
_HEX_ESCAPE_WIDTHS = {"x": 2, "u": 4, "U": 8}
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
# A well-formed `\u`/`\U` escape can still name something that is not a character. YAML escapes
# denote scalar VALUES, and the surrogate block exists only to encode pairs inside UTF-16 -- a
# lone one is not a code point a loader can produce, and nothing above U+10FFFF exists at all.
# Counting hex digits accepted both (review finding, PR #120), so a description could carry
# `\uD800` and still ship: this reader keeps the bytes, a strict loader refuses the document, and
# the component goes missing with no error. `\x` needs no range check -- two hex digits cannot
# leave 0x00-0xFF.
_SURROGATE_RANGE = range(0xD800, 0xE000)
_MAX_CODE_POINT = 0x10FFFF


def flow_scalar_defect(value: str) -> str | None:
    """Name why a quoted flow scalar is unusable here, or return None when it is fine.

    YAML ends a flow scalar at the FIRST unescaped matching quote, so "does a quote appear later
    in the line" is not the question. Asking only that let `description: "ok"oops` through, and --
    worse, because it reads as ordinary prose -- `description: 'Use the agent's output`, which
    closes at the apostrophe in "agent's" and leaves `s output` as trailing tokens.

    **One case is deliberately stricter than YAML**, and it is the only place in this rule that
    rejects a legal document. YAML drops a ` # comment` after a closing quote; `parse_lines`
    above is not comment-aware -- it takes the line and calls `.strip("'\\"")`, which removes the
    outer quote characters and nothing else. So `description: "Use when routing." # note` parses
    to `Use when routing." # note` and every generated host copy ships that string as the
    description (executed, PR #120). Accepting it because YAML would was the wrong call: the
    fleet's readers are this dialect and the hosts downstream of it, not a conforming parser.

    Escapes are honored in both directions -- a doubled `''` inside a single-quoted scalar and the
    real escape set inside a double-quoted one -- because a value that merely LOOKS malformed would
    be a false red on a legal file, and the caller's whole point is that only the strict check can
    see the difference.
    """
    quote = value[0]
    index = 1
    while index < len(value):
        char = value[index]
        if quote == '"' and char == "\\":
            following = value[index + 1 : index + 2]
            if not following:
                return (
                    "ends on a dangling backslash with nothing to escape, so the scalar never "
                    "closes"
                )
            width = _HEX_ESCAPE_WIDTHS.get(following)
            if width is not None:
                digits = value[index + 2 : index + 2 + width]
                if len(digits) != width or not set(digits) <= _HEX_DIGITS:
                    return (
                        f"carries the malformed hex escape "
                        f"{value[index : index + 2 + width]!r}, which needs exactly {width} hex "
                        f"digits; a conforming YAML parser refuses the document over it"
                    )
                if following in "uU":
                    code_point = int(digits, 16)
                    if code_point in _SURROGATE_RANGE:
                        return (
                            f"escapes the lone surrogate U+{code_point:04X} "
                            f"({value[index : index + 2 + width]!r}); surrogates encode UTF-16 "
                            f"pairs and are not scalar values, so a strict loader refuses the "
                            f"document while this parser keeps the bytes"
                        )
                    if code_point > _MAX_CODE_POINT:
                        return (
                            f"escapes U+{code_point:04X} "
                            f"({value[index : index + 2 + width]!r}), above the Unicode maximum "
                            f"U+{_MAX_CODE_POINT:04X}; no such character exists, so a strict "
                            f"loader refuses the document while this parser keeps the bytes"
                        )
                index += 2 + width
                continue
            if following not in _DOUBLE_QUOTE_ESCAPES:
                return (
                    f"carries the invalid escape sequence {value[index : index + 2]!r}; a "
                    f"conforming YAML parser refuses the document with 'found unknown escape "
                    f"character', while this validator's parser keeps the backslash and every "
                    f"generated copy ships it"
                )
            index += 2
            continue
        if char == quote:
            if quote == "'" and value[index + 1 : index + 2] == "'":
                index += 2
                continue
            tail = value[index + 1 :].strip()
            if not tail:
                return None
            if tail.startswith("#"):
                return (
                    f"closes its {quote} quote and then carries the comment {tail!r}. YAML would "
                    f"drop that comment, but the fleet's frontmatter reader is not "
                    f"comment-aware: it strips only the outer quote characters, so the value "
                    f"becomes {value.strip(chr(39) + chr(34))!r} and every generated host copy "
                    f"ships the comment as literal description text. This rule is deliberately "
                    f"stricter than YAML here"
                )
            return (
                f"closes its {quote} quote and then carries the trailing token(s) {tail!r}, which "
                f"a conforming YAML parser refuses"
            )
        index += 1
    return f"opens a {quote} quote that never closes on its line"


def yaml_scalar(value: str) -> str:
    """Emit a string as a double-quoted YAML scalar.

    A JSON string literal is a valid YAML 1.2 double-quoted scalar (JSON is a YAML subset), and
    it round-trips through every host's reader as the same string -- which a bare value with a
    leading `[`, a `: `, or a `#` does not. Non-ASCII text is emitted as UTF-8 rather than
    `\\uXXXX` escapes so a generated description stays readable in its host's listing. This is
    the one place that fact is relied on.
    """
    return json.dumps(value, ensure_ascii=False)


def yaml_flow_list(values: Iterable[str]) -> str:
    """Emit strings as a YAML flow sequence of double-quoted scalars, by the same argument."""
    return json.dumps(list(values), ensure_ascii=False)
