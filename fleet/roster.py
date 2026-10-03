"""The read-only guard's roster, read from the hook script as DATA, never by running it.

`hooks/hooks.json` resolves the guard through ${CLAUDE_PLUGIN_ROOT}, so `scripts/readonly-guard.py`
is the only place a plugin-shipped fleet can put it. The generator renders the hook from this
roster and the validator cross-checks it against the agents; executing the script to learn either
would run whatever the tree under validation supplies, so both read its AST.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

GUARD_SCRIPT = "scripts/readonly-guard.py"
GUARD_ROSTER = "GUARDED_AGENT_NAMES"
# Tools that make an agent a WRITER. An agent holding Bash but none of these is a read-only agent
# whose only route to mutation is the shell -- exactly what the guard exists to close.
WRITE_TOOLS = frozenset({"Write", "Edit", "NotebookEdit"})


class RosterError(ValueError):
    """A hook script's roster constants could not be read as data."""


@dataclass(frozen=True)
class Rosters:
    """The module-level constants a hook declares, read from its AST."""

    path: Path
    plugin_name: str
    names: dict[str, frozenset[str]]

    def __getitem__(self, constant: str) -> frozenset[str]:
        return self.names[constant]


@dataclass(frozen=True)
class HookScript:
    """One hook script: present or not, and its rosters or the reason they could not be read."""

    path: Path
    exists: bool = False
    rosters: Rosters | None = None
    error: str | None = None

    @classmethod
    def load(cls, path: Path, *constants: str) -> HookScript:
        exists = path.is_file()
        try:
            return cls(path, exists, read_rosters(path, *constants))
        except RosterError as exc:
            return cls(path, exists, None, str(exc))


def _string_set(node: ast.AST, constant: str, path: Path) -> frozenset[str]:
    """Evaluate `frozenset({...})`, `{...}`, or a list/tuple of string literals."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"frozenset", "set"}
        and len(node.args) <= 1
        and not node.keywords
    ):
        if not node.args:
            # `frozenset()` is the obvious way to write "this hook covers nobody", a valid
            # configuration rather than an unreadable one.
            return frozenset()
        node = node.args[0]
    if not isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        raise RosterError(f"{path}: {constant} is not a literal set of names")
    values: set[str] = set()
    for element in node.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            raise RosterError(f"{path}: {constant} contains a non-literal member")
        values.add(element.value)
    return frozenset(values)


def read_rosters(path: Path, *names: str) -> Rosters:
    """Read `PLUGIN_NAME` and the named roster constants from a hook script without running it."""
    path = Path(path)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise RosterError(f"{path}: cannot read hook rosters: {exc}") from exc
    wanted = {"PLUGIN_NAME", *names}
    found: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in wanted:
                found[target.id] = node.value
    missing = sorted(wanted - found.keys())
    if missing:
        raise RosterError(f"{path}: missing module constant(s) {missing}")
    plugin = found["PLUGIN_NAME"]
    if not isinstance(plugin, ast.Constant) or not isinstance(plugin.value, str):
        raise RosterError(f"{path}: PLUGIN_NAME is not a string literal")
    return Rosters(
        path,
        plugin.value,
        {name: _string_set(found[name], name, path) for name in names},
    )
