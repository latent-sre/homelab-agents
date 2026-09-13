"""One typed, read-once snapshot of the tree the validator judges.

Every rule used to open and parse its own files, so one definition was read up to four times per
run and two rules could disagree about the same file. `Fleet.load(root)` reads each definition,
the plugin manifest, and the hook file exactly once; rules are pure functions over the result.

This module records; it never judges (a malformed frontmatter is `fields is None`, not a
finding). The inspected tree is data: nothing under `root` is imported or executed. The one
script the validator must read facts FROM -- a hook's roster constants -- is read as an AST
(`read_rosters`), never run, so a hostile or broken hook cannot execute during validation. The
tests that need the hook's *behaviour* still load it as a module through the validator's
content-keyed loader; that path is theirs, not this snapshot's.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from fleet import frontmatter, fs

TOOL_ENTRY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\((.*)\))?$")


@dataclass(frozen=True)
class Definition:
    """One canonical agent (`agents/<name>.md`) or skill (`skills/<name>/SKILL.md`)."""

    kind: str  # "agent" | "skill"
    path: Path
    text: str | None  # None when the file is not valid UTF-8 or cannot be read
    lines: tuple[str, ...]
    span: int | None  # closing frontmatter marker index, or None
    fields: dict[str, str] | None  # None when absent, unterminated, or refused
    # A skill's bundle as loaded: every path under its references/, assets/, and scripts/ (files
    # and directories, so a link to either resolves) and the files alone, in walk order. The
    # bundle rules judge these records, not the disk, so one report never mixes two trees.
    bundle_paths: frozenset[Path] = field(default_factory=frozenset)
    bundle_files: tuple[Path, ...] = ()

    @property
    def stem(self) -> str:
        return self.path.stem if self.kind == "agent" else self.path.parent.name

    @property
    def directory(self) -> Path:
        """A skill's directory; an agent's `agents/` directory."""
        return self.path.parent

    @property
    def name(self) -> str:
        return (self.fields or {}).get("name", "") or self.stem

    @property
    def readable(self) -> bool:
        return self.text is not None

    def field(self, key: str) -> str:
        return (self.fields or {}).get(key, "")

    def tool_entries(self) -> list[str]:
        return frontmatter.split_tools(self.field("tools"))

    def tool_bases(self) -> set[str]:
        bases: set[str] = set()
        for entry in self.tool_entries():
            match = TOOL_ENTRY_RE.match(entry)
            if match:
                bases.add(match.group(1))
        return bases

    def preloaded_skills(self) -> list[str]:
        return [entry.strip() for entry in self.field("skills").split(",") if entry.strip()]


BUNDLE_DIRS = ("references", "assets", "scripts")


def _bundle_inventory(directory: Path) -> tuple[frozenset[Path], tuple[Path, ...]]:
    """Every path and every file under the bundle directories of `directory`, walked once."""
    paths: set[Path] = set()
    files: list[Path] = []
    for name in BUNDLE_DIRS:
        bundle_dir = directory / name
        if not bundle_dir.is_dir():
            continue
        paths.add(bundle_dir)
        for entry in sorted(bundle_dir.rglob("*")):
            paths.add(entry)
            if entry.is_file():
                files.append(entry)
    return frozenset(paths), tuple(files)


def _load_definition(kind: str, path: Path) -> Definition:
    bundle_paths, bundle_files = (
        _bundle_inventory(path.parent) if kind == "skill" else (frozenset(), ())
    )
    text = fs.try_read_text(path)
    if text is None:
        return Definition(kind, path, None, (), None, None, bundle_paths, bundle_files)
    lines = text.splitlines()
    span = frontmatter.span(lines)
    fields = None if span is None else frontmatter.parse_lines(lines, span)
    return Definition(kind, path, text, tuple(lines), span, fields, bundle_paths, bundle_files)


@dataclass(frozen=True)
class Fleet:
    """Everything the rules read, loaded once."""

    root: Path
    agents_dir_exists: bool
    skills_dir_exists: bool
    agents: tuple[Definition, ...]
    skills: tuple[Definition, ...]
    skill_dirs_without_skill_md: tuple[Path, ...]
    plugin_manifest_path: Path
    plugin_manifest: dict[str, object] | None
    plugin_manifest_error: str | None
    hooks_path: Path
    hook_commands: tuple[str, ...] = field(default=())
    # Whether the manifest existed when the tree was read: every plugin-gated rule gates on this
    # record, so a manifest created or removed afterwards changes nothing in this report.
    plugin_manifest_present: bool = False
    # The repository-level bundle directories a skill link may resolve to instead of its own.
    shared_bundle_paths: frozenset[Path] = field(default_factory=frozenset)
    # The two hook scripts and their rosters, read as data at load time. The plugin rules judge
    # these against the same agents and hook file the rest of the report describes; a script
    # rewritten after the snapshot changes nothing in this report.
    guard: HookScript = field(default_factory=lambda: HookScript(Path(GUARD_SCRIPT)))
    gate: HookScript = field(default_factory=lambda: HookScript(Path(GATE_SCRIPT)))
    # Every markdown file the fleet ships as behaviour (agent bodies, SKILL.md files, and each
    # skill's references/ and assets/), read once: the cross-reference and perishable-token rules
    # judge these bytes, the same bytes the agent and skill rules judged, so one report can never
    # describe two versions of a tree.
    markdown_texts: dict[Path, str | None] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path) -> Fleet:
        root = Path(root)
        agents_dir = root / "agents"
        skills_dir = root / "skills"
        agents = (
            tuple(_load_definition("agent", path) for path in sorted(agents_dir.glob("*.md")))
            if agents_dir.is_dir()
            else ()
        )
        skills: list[Definition] = []
        missing: list[Path] = []
        if skills_dir.is_dir():
            for directory in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
                skill_file = directory / "SKILL.md"
                if skill_file.is_file():
                    skills.append(_load_definition("skill", skill_file))
                else:
                    missing.append(directory)
        manifest_path = root / ".claude-plugin" / "plugin.json"
        manifest: dict[str, object] | None = None
        manifest_error: str | None = None
        if manifest_path.is_file():
            try:
                loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = loaded if isinstance(loaded, dict) else {}
            except (json.JSONDecodeError, OSError) as exc:
                manifest_error = str(exc)
        hooks_path = root / "hooks" / "hooks.json"
        guard = HookScript.load(root / GUARD_SCRIPT, GUARD_ROSTER)
        gate = HookScript.load(root / GATE_SCRIPT, GATE_ROSTER)
        # The definitions' bytes seed the map, so a core file is read exactly once; only the
        # bundled markdown (a skill's references/ and assets/) is read here.
        markdown_texts = {definition.path: definition.text for definition in (*agents, *skills)}
        for path in _definition_markdown_files(root):
            if path not in markdown_texts:
                markdown_texts[path] = fs.try_read_text(path)
        return cls(
            root=root,
            agents_dir_exists=agents_dir.is_dir(),
            skills_dir_exists=skills_dir.is_dir(),
            agents=agents,
            skills=tuple(skills),
            skill_dirs_without_skill_md=tuple(missing),
            plugin_manifest_path=manifest_path,
            plugin_manifest=manifest,
            plugin_manifest_error=manifest_error,
            plugin_manifest_present=manifest_path.is_file(),
            shared_bundle_paths=_bundle_inventory(root)[0],
            hooks_path=hooks_path,
            hook_commands=tuple(_hook_commands(hooks_path)),
            guard=guard,
            gate=gate,
            markdown_texts=markdown_texts,
        )

    # --- derived views -------------------------------------------------------------------

    @property
    def ships_as_plugin(self) -> bool:
        return self.plugin_manifest_present

    @property
    def plugin_name(self) -> str:
        return str((self.plugin_manifest or {}).get("name", "")).strip()

    @property
    def parsed_agents(self) -> tuple[Definition, ...]:
        return tuple(agent for agent in self.agents if agent.fields is not None)

    @property
    def parsed_skills(self) -> tuple[Definition, ...]:
        return tuple(skill for skill in self.skills if skill.fields is not None)

    @property
    def agent_names(self) -> list[str]:
        """Sorted names of every agent whose frontmatter parsed (the legacy `names` view)."""
        return sorted(agent.name for agent in self.parsed_agents)

    @property
    def skill_names(self) -> list[str]:
        return sorted(skill.name for skill in self.parsed_skills)

    @property
    def component_names(self) -> set[str]:
        return set(self.agent_names) | set(self.skill_names)

    def definitions(self) -> Iterator[Definition]:
        yield from self.agents
        yield from self.skills

    def skill(self, name: str) -> Definition | None:
        return next((s for s in self.skills if s.stem == name), None)

    def markdown_files(self) -> list[Path]:
        """The definition markdown paths, in the order the reference collector walks them."""
        return sorted(self.markdown_texts)

    def hook_command_for(self, script: str) -> str | None:
        """The PreToolUse/Bash command that runs `script`, found by name."""
        return next((command for command in self.hook_commands if script in command), None)


def _definition_markdown_files(root: Path) -> list[Path]:
    files = sorted((root / "agents").glob("*.md")) if (root / "agents").is_dir() else []
    if (root / "skills").is_dir():
        files += sorted((root / "skills").rglob("*.md"))
    return files


def _hook_commands(path: Path) -> list[str]:
    """Every PreToolUse/Bash command string in hooks/hooks.json, in file order."""
    if not path.is_file():
        return []
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    # A file that parses but has the wrong shape (a top-level list, a string where a table
    # belongs) is recorded as declaring no commands, so the plugin rules report the missing
    # hooks rather than the whole snapshot refusing to load an unrelated agent check.
    commands: list[str] = []
    hooks = config.get("hooks") if isinstance(config, dict) else None
    entries = hooks.get("PreToolUse") if isinstance(hooks, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, dict) and entry.get("matcher") == "Bash":
            hook_list = entry.get("hooks")
            for hook in hook_list if isinstance(hook_list, list) else []:
                if isinstance(hook, dict) and hook.get("type") == "command" and hook.get("command"):
                    commands.append(hook["command"])
    return commands


# --- hook rosters as data ----------------------------------------------------------------

# Where each Claude hook script lives and the roster constant naming the agents it scopes to.
# `hooks/hooks.json` resolves the scripts through ${CLAUDE_PLUGIN_ROOT}, so these are the only
# locations a plugin-shipped fleet can put them (`scripts/readonly-guard.py` docstring).
GUARD_SCRIPT = "scripts/readonly-guard.py"
GUARD_ROSTER = "GUARDED_AGENT_NAMES"
GATE_SCRIPT = "scripts/live-effect-gate.py"
GATE_ROSTER = "GATED_AGENT_NAMES"


class RosterError(ValueError):
    """A hook script's roster constants could not be read as data."""


@dataclass(frozen=True)
class HookScript:
    """One hook script as the snapshot saw it: present or not, and its rosters or the reason
    they could not be read. A script the plugin rules cannot read guards nothing, and the rule
    says so from this record rather than re-reading the disk."""

    path: Path
    exists: bool = False
    rosters: Rosters | None = None
    error: str | None = None

    @classmethod
    def load(cls, path: Path, *constants: str) -> HookScript:
        # An absent script is read anyway so its error carries the reader's own wording: the
        # gate rule reports an absent gate exactly as it reports an unreadable one.
        exists = path.is_file()
        try:
            return cls(path, exists, read_rosters(path, *constants))
        except RosterError as exc:
            return cls(path, exists, None, str(exc))


@dataclass(frozen=True)
class Rosters:
    """The module-level constants a hook declares, read from its AST."""

    path: Path
    plugin_name: str
    names: dict[str, frozenset[str]]

    def __getitem__(self, constant: str) -> frozenset[str]:
        return self.names[constant]


def _string_set(node: ast.AST, constant: str, path: Path) -> frozenset[str]:
    """Evaluate `frozenset({...})`, `{...}`, or a list/tuple of string literals."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"frozenset", "set"}
        and len(node.args) == 1
        and not node.keywords
    ):
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
    """Read `PLUGIN_NAME` and the named roster constants from a hook script without running it.

    The validator cross-checks these against the agents and the hook file. Executing the script
    to read them would run whatever the tree under validation supplies; the AST is data.
    """
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
