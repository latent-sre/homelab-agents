"""Filesystem primitives: link-safe inspection, UTF-8 reads, atomic writes, shared ignore rules.

Every rule here exists because a plain `pathlib` call once produced a wrong answer that looked
right. The comments name the incident; keep them when editing.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Iterable
from pathlib import Path

# Windows directory junctions are reparse points that `Path.is_symlink()` reports as plain
# directories, so a junction planted inside a generated tree, a fixture copy, or a provenance
# input redirects traversal without tripping the symlink check. Every kernel walk therefore asks
# about the reparse attribute too. The flag's value is fixed by the Win32 API; the fallback keeps
# the check MEANINGFUL on an interpreter that lacks the constant instead of silently disabling
# it (one of the three former copies defaulted to 0, which is exactly that silent disable).
REPARSE_POINT_FLAG = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def is_link_or_reparse(target: Path | os.stat_result) -> bool:
    """True for POSIX symlinks and every Windows reparse-point kind, including junctions.

    Accepts a path (stat'ed with `lstat`, so the entry itself is inspected, never what it points
    at) or a stat result a caller already holds (anything carrying `st_mode`). A path that cannot
    be stat'ed raises `OSError`: an unreadable entry is not evidence that it is safe.
    """
    file_stat = target if hasattr(target, "st_mode") else Path(target).lstat()
    return stat.S_ISLNK(file_stat.st_mode) or bool(
        getattr(file_stat, "st_file_attributes", 0) & REPARSE_POINT_FLAG
    )


def absolute_without_resolving(path: Path) -> Path:
    """An absolute lexical path. `Path.resolve()` is not used because it follows links, and the
    callers of this function are the ones deciding whether a link is acceptable at all."""
    return Path(os.path.abspath(os.fspath(Path(path).expanduser())))


def read_text(path: Path) -> str:
    """Read a UTF-8 text file; the encoding is explicit so Windows never decodes as cp1252."""
    return Path(path).read_text(encoding="utf-8")


def try_read_text(path: Path) -> str | None:
    """Read a UTF-8 text file, or None when it cannot be read or decoded.

    An inspected tree is arbitrary bytes. A definition containing invalid UTF-8 once raised
    `UnicodeDecodeError` mid-collection, so the CLI printed a traceback and the damaged file never
    reached the unreadable list it exists to name. Returning None lets the caller record the path
    and keep producing an explicitly incomplete artifact.
    """
    try:
        return read_text(path)
    except (UnicodeDecodeError, OSError):
        return None


def is_runtime_byproduct(path: Path) -> bool:
    """Whether a path is Python execution residue rather than distributable fleet source."""
    path = Path(path)
    return "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo"}


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Replace `path` with `content` so a reader never observes a partially written file.

    The bytes land in a sibling temporary file, are flushed and fsync'ed, then renamed over the
    target with `os.replace`, which is atomic on POSIX and on NTFS. A failure at any step removes
    the temporary file and leaves the previous content untouched.
    """
    import tempfile

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


# Directory entries no fleet copy of the repository may carry, by basename and by anchored path.
#
# `.probe-tmp` is the live-probe workspace (`scripts/probe_plugin.py`), created and removed inside
# the repository root; copying it races that removal, which invalidated a probe run when the suite
# and the probe ran concurrently. `.claude/worktrees` is the platform's nested-worktree home: a
# second full checkout another session writes concurrently, so copying it bloats every copy by
# that checkout's size and races the other writer exactly as `.probe-tmp` did. The worktree
# exclusion is anchored at the repository root and covers everything UNDER the path, never the bare
# basename: a basename ignore would silently omit any legitimate `worktrees/` directory a later
# skill or fixture ships, so the tree under validation would quietly stop matching the repository.
#
# Before this module the test pool and the probe each carried this list "kept in step by hand"
# (tests/support.py, scripts/probe_plugin.py). Now both read it from here.
# `node_modules` is a maintainer's local toolchain, never fleet source; the probe excluded it to
# keep its plugin copy small and the test pool now agrees.
IGNORED_DIRS: frozenset[str] = frozenset({".git", "__pycache__", ".probe-tmp", "node_modules"})
IGNORED_PATHS: frozenset[Path] = frozenset({Path(".claude") / "worktrees"})


def is_ignored(relative: Path) -> bool:
    """Whether a repository-relative path falls under the shared copy exclusions."""
    relative = Path(relative)
    return (
        relative in IGNORED_PATHS
        or any(parent in IGNORED_PATHS for parent in relative.parents)
        or any(part in IGNORED_DIRS for part in relative.parts)
    )


def copytree_ignore(root: Path):
    """A `shutil.copytree(ignore=...)` callback applying the shared exclusions under `root`.

    The callback drops only entries named in its return value -- a synthetic slash-joined name
    ignores nothing -- so an anchored path is excluded by ignoring its final component when the
    callback fires for its parent.
    """
    root = Path(root)

    def _ignore(directory: str, names: Iterable[str]) -> set[str]:
        ignored = set(names) & IGNORED_DIRS
        directory_path = Path(directory)
        for anchored in IGNORED_PATHS:
            if directory_path == root / anchored.parent:
                ignored.add(anchored.name)
        return ignored

    return _ignore


def safe_path_segment(value: str, *, what: str) -> str:
    """One path component, or a refusal naming what was wrong.

    A name that reaches a filesystem path has to be checked before it is joined, not after. Two
    ways it goes wrong, both found by review on a generated eval tree rather than by a test:

    - An **absolute** value silently discards the base it is joined to. `Path("/base") / "/tmp/x"`
      is `/tmp/x`, not `/base/tmp/x`, so a case id of `/tmp/x` writes outside the tree entirely.
    - A value containing `..` climbs out of it. `evals/generated/../../../victim` under a private
      snapshot root resolves to a sibling of that root — and the caller that then removes a stale
      directory would remove whatever is there.

    Refusing is the only safe answer: sanitising by stripping the offending parts silently renames
    what the caller asked for, and two different inputs would collide on one output.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{what} must be a non-empty string (got {value!r})")
    if value in (".", "..") or "/" in value or "\\" in value or os.sep in value:
        raise ValueError(
            f"{what} must be a single path component, with no separator and no '..': {value!r}"
        )
    if Path(value).is_absolute() or (os.altsep and os.altsep in value):
        raise ValueError(f"{what} must be relative, not an absolute path: {value!r}")
    return value


def contained_path(root: Path, relative: str, *, what: str) -> Path:
    """`root / relative`, proven to stay under `root`.

    The belt to `safe_path_segment`'s braces, for a multi-segment relative path that is assembled
    rather than supplied whole. Resolution is done WITHOUT following symlinks
    (`absolute_without_resolving`), because resolving first would accept a path whose containment
    depends on a link that a repository under evaluation could have planted.
    """
    base = absolute_without_resolving(root)
    candidate = absolute_without_resolving(root / relative)
    if base != candidate and base not in candidate.parents:
        raise ValueError(f"{what} escapes {base}: {relative!r} -> {candidate}")
    return candidate
