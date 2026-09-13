"""Emit the Codex host's TOML, and verify every emission by parsing it back.

Codex custom agents are standalone TOML. The fleet writes that file rather than a library,
because the hooks' dependency-free contract keeps the kernel standard-library only -- so the
escaping is the fleet's to get right, and an escaping bug here is silent in the worst way: the
file still looks like TOML, the validator still byte-compares it against a copy produced with the
same bug, and Codex reads a truncated instruction set or refuses the profile at load time.

The answer is not care, it is a check. Every document this module emits is parsed straight back
with `tomllib` and compared to the mapping it was asked to write. A wrong escape, a delimiter
inside a value, or a stray control character therefore fails at generation time, on a bare
interpreter, with no dependency to install. `tomli-w` is the third-party tripwire over the same
data in `tests/test_fleet_hosts.py`, the way PyYAML is the tripwire for the frontmatter dialect:
useful as an independent opinion, never in the path that writes the file.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


class TomlEmitError(ValueError):
    """A value cannot be written as TOML, or the emitted document did not read back equal."""


@dataclass(frozen=True)
class Multiline:
    """A value to emit as a multiline literal block rather than a quoted basic string.

    TOML trims the newline that follows the opening delimiter, so a value ending in a newline
    round-trips exactly; that is how an instruction body keeps its final line break.
    """

    value: str


def basic_string(value: str) -> str:
    """One quoted TOML basic string.

    TOML's basic-string escapes are a superset of JSON's for the characters `json` emits, and
    `ensure_ascii=False` keeps real text (an em dash, a non-Latin name) as itself rather than as
    an escape nobody can read in a diff. The round-trip in `render_document` is what makes that
    reasoning checkable rather than asserted.
    """
    return json.dumps(value, ensure_ascii=False)


def multiline_literal(value: str) -> str:
    """One `'''`-delimited literal block, refusing anything the delimiter cannot hold.

    A literal block applies no escaping at all, which is exactly why it suits an instruction body
    full of backslashes and quotes -- and exactly why the three refusals below matter: each would
    otherwise end the block early or start a fourth quote, truncating the instructions into a
    file that still parses.
    """
    if "'''" in value:
        raise TomlEmitError("value contains the TOML multiline-literal delimiter \"'''\"")
    if value.endswith("'"):
        raise TomlEmitError("value ends with a quote, which would extend the closing delimiter")
    if "\r" in value:
        raise TomlEmitError("value contains a carriage return, which TOML normalises on read")
    for character in value:
        if character != "\n" and character != "\t" and character < " ":
            raise TomlEmitError(f"value contains control character {character!r}")
    # The newline after the opening delimiter is trimmed on read, so it is formatting, not data.
    return f"'''\n{value}'''"


def render_document(
    entries: Sequence[tuple[str, str | Multiline]], *, comment: str | None = None
) -> str:
    """Render a flat table of string values, then prove it reads back as what was asked for."""

    lines: list[str] = []
    if comment is not None:
        if "\n" in comment:
            raise TomlEmitError("a document comment must be one line")
        lines.append(f"# {comment}")
    intended: dict[str, str] = {}
    for key, value in entries:
        if key in intended:
            raise TomlEmitError(f"duplicate key {key!r}")
        if not key.replace("_", "").replace("-", "").isalnum():
            # A bare key outside this set would need quoting; nothing in the fleet needs one, so
            # refusing is better than emitting a form no test covers.
            raise TomlEmitError(f"key {key!r} is not a bare TOML key")
        if isinstance(value, Multiline):
            lines.append(f"{key} = {multiline_literal(value.value)}")
            intended[key] = value.value
        else:
            lines.append(f"{key} = {basic_string(value)}")
            intended[key] = value
    text = "\n".join(lines) + "\n"

    try:
        parsed: Mapping[str, object] = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:  # an escaping bug, caught where it was made
        raise TomlEmitError(f"emitted document is not valid TOML: {exc}") from exc
    if parsed != intended:
        differing = sorted(
            key for key in {*parsed, *intended} if parsed.get(key) != intended.get(key)
        )
        raise TomlEmitError(
            f"emitted document did not read back as written; keys that differ: {differing}"
        )
    return text
