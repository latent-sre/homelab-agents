#!/usr/bin/env python3
"""Safely synchronize the generated Codex custom agents into another scope.

Codex plugins currently load skills, hooks, and MCP servers, but not custom-agent TOML. The
repository therefore keeps project-scoped agents under ``.codex/agents`` and provides this explicit
synchronizer for a user or alternate project scope.

The installer owns only files carrying ``INSTALL_MARKER``. It adopts an unmarked copy only when its
parsed contract matches the current generated source, refuses every behaviorally different name
collision, and prunes only stale managed files. The complete plan is checked for conflicts before
any write or removal occurs.
"""

from __future__ import annotations

import argparse
import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)  # `import fleet` when run as `python3 scripts/<name>.py`

from fleet import fs as _fs  # noqa: E402

try:
    from scripts import generate_platform_adapters
except ModuleNotFoundError:
    import generate_platform_adapters  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIRECTORY = REPO_ROOT / ".codex" / "agents"
INSTALL_MARKER = "# Managed by sde-agents scripts/install_codex_agents.py; do not edit."


@dataclass(frozen=True)
class SyncPlan:
    """A complete, preflighted set of exact file operations."""

    writes: tuple[tuple[Path, bytes], ...]
    removals: tuple[Path, ...]
    conflicts: tuple[Path, ...]

    @property
    def out_of_sync(self) -> bool:
        return bool(self.writes or self.removals or self.conflicts)


def _installed_bytes(source: bytes) -> bytes:
    return f"{INSTALL_MARKER}\n".encode() + source


def _is_managed(content: bytes) -> bool:
    first_line = content.splitlines()[0] if content else b""
    return first_line == INSTALL_MARKER.encode("utf-8")


def _normalized_contract(content: bytes) -> dict[str, object] | None:
    """Parse one agent while ignoring only importer's terminal-newline formatting."""

    try:
        contract = tomllib.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    instructions = contract.get("developer_instructions")
    if isinstance(instructions, str):
        if instructions.endswith("\r\n"):
            instructions = instructions[:-2]
        elif instructions.endswith(("\r", "\n")):
            instructions = instructions[:-1]
        contract["developer_instructions"] = instructions
    return contract


def _matches_generated_contract(current: bytes, source: bytes) -> bool:
    """Allow Codex importer formatting, but reject any field or authority difference."""

    current_contract = _normalized_contract(current)
    source_contract = _normalized_contract(source)
    return current_contract is not None and current_contract == source_contract


def build_sync_plan(source_directory: Path, target_directory: Path) -> SyncPlan:
    """Plan a safe synchronization without changing either directory."""

    sources = {
        source.name: source.read_bytes()
        for source in sorted(source_directory.glob("*.toml"))
        if source.is_file()
    }
    if not sources:
        raise ValueError(f"{source_directory}: no generated Codex agent TOML files found")

    writes: list[tuple[Path, bytes]] = []
    removals: list[Path] = []
    conflicts: list[Path] = []

    for name, source_content in sources.items():
        target = target_directory / name
        desired = _installed_bytes(source_content)
        if not target.exists():
            writes.append((target, desired))
            continue
        if not target.is_file():
            conflicts.append(target)
            continue

        current = target.read_bytes()
        if current == desired:
            continue
        if (
            _is_managed(current)
            or current == source_content
            or _matches_generated_contract(current, source_content)
        ):
            writes.append((target, desired))
        else:
            conflicts.append(target)

    if target_directory.is_dir():
        for target in sorted(target_directory.glob("*.toml")):
            if target.name in sources or not target.is_file():
                continue
            if _is_managed(target.read_bytes()):
                removals.append(target)

    return SyncPlan(tuple(writes), tuple(removals), tuple(conflicts))


def _atomic_write(path: Path, content: bytes) -> None:
    """Replace `path` atomically (kernel implementation: sibling temp file, fsync, `os.replace`)."""
    _fs.atomic_write_bytes(path, content)


def apply_sync_plan(plan: SyncPlan) -> None:
    """Apply a conflict-free plan; callers must not bypass the preflight."""

    if plan.conflicts:
        rendered = ", ".join(str(path) for path in plan.conflicts)
        raise ValueError(f"refusing to overwrite unmanaged Codex agent files: {rendered}")
    for path, content in plan.writes:
        _atomic_write(path, content)
    for path in plan.removals:
        path.unlink()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--user",
        action="store_true",
        help="synchronize into CODEX_HOME/agents (default: ~/.codex/agents)",
    )
    target.add_argument(
        "--target",
        type=Path,
        help="synchronize into an explicit Codex agents directory",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without writing or pruning files",
    )
    return parser


def _user_agents_directory() -> Path:
    """Resolve the user agent directory from the same home contract Codex uses."""

    configured_home = os.environ.get("CODEX_HOME")
    if configured_home:
        codex_home = Path(configured_home).expanduser().resolve()
        if not codex_home.is_dir():
            raise ValueError(
                f"CODEX_HOME does not exist or is not a directory: {codex_home}"
            )
    else:
        codex_home = (Path.home() / ".codex").resolve()
    return codex_home / "agents"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    adapter_issues = generate_platform_adapters.validate_generated_outputs(REPO_ROOT)
    if adapter_issues:
        for issue in adapter_issues:
            print(issue, file=sys.stderr)
        return 2

    try:
        target = (
            _user_agents_directory()
            if args.user
            else args.target.expanduser().resolve()
        )
        plan = build_sync_plan(SOURCE_DIRECTORY, target)
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2

    if plan.conflicts:
        for path in plan.conflicts:
            print(
                f"{path}: unmanaged file conflicts with a generated sde-agents role; "
                "move or rename it before retrying",
                file=sys.stderr,
            )
        return 2

    if args.check:
        if plan.out_of_sync:
            print(
                f"Codex agents are not synchronized: {len(plan.writes)} update(s), "
                f"{len(plan.removals)} stale managed file(s)."
            )
            return 1
        print("Codex agents are synchronized.")
        return 0

    try:
        apply_sync_plan(plan)
    except OSError as exc:
        print(f"Codex agent synchronization failed: {exc}", file=sys.stderr)
        return 2

    print(
        f"Synchronized {len(plan.writes)} Codex agent file(s) to {target}; "
        f"removed {len(plan.removals)} stale managed file(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
