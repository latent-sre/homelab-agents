"""Shared test fixtures — only patterns with multiple real consumers live here.

This module deliberately stays small. A helper earns its place by replacing the same code in
two or more test modules (or a dozen repetitions in one); anything a single module needs stays
in that module, per the repository's proportionality rule. It is named so `unittest discover`
never collects it, and imported as `from tests.support import ...`, which holds under every
sanctioned invocation for the same reason the existing `from scripts import ...` imports do:
the suite runs from the repository root.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from collections.abc import Callable, Iterator
from pathlib import Path

from fleet import fs

REPO = Path(__file__).resolve().parents[1]

# The copy exclusions are the kernel's (fleet/fs.py), shared with the probe's plugin copy. They
# used to be two lists "kept in step by hand"; the reasons for each entry live beside the set.
_IGNORED_DIRS = fs.IGNORED_DIRS
_IGNORED_PATHS = fs.IGNORED_PATHS
_is_ignored = fs.is_ignored


def _copy_ignore(directory: str, names: list[str]) -> set[str]:
    """copytree callback bound to the module's REPO at call time, so tests may patch REPO."""
    return fs.copytree_ignore(REPO)(directory, names)


def create_directory_link(target: Path, link: Path) -> None:
    """Create the link primitive that can redirect directory traversal on this host.

    Windows junctions stand in where symlinks need privilege; POSIX gets a real symlink. Tests
    that exercise link handling use this so the same test covers both primitives across the CI
    matrix, skipping only where the host can create neither.
    """
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise unittest.SkipTest(
                f"cannot create a Windows junction for the regression test: {result.stderr}"
            )
    else:
        link.symlink_to(target, target_is_directory=True)


def remove_directory_link(link: Path) -> None:
    if link.is_symlink():
        link.unlink()
    elif link.exists():
        link.rmdir()


def _is_link(path: Path) -> bool:
    """True for symlinks AND Windows reparse points (junctions), which is_symlink() misses."""
    return fs.is_link_or_reparse(path)


def _remove_link(path: Path) -> None:
    """Remove a link entry itself, whatever it points at — including nothing.

    The dispatch must not follow the link: is_dir() on a DANGLING junction or symlink answers
    for the missing target, not the entry, and picks the wrong removal call (caught in review
    on #91). unlink-then-rmdir covers every link shape on both platforms without consulting
    the target: POSIX symlinks always unlink; Windows directory junctions refuse unlink and
    fall through to rmdir, which removes the junction without touching its target.
    """
    try:
        path.unlink()
    except OSError:
        os.rmdir(path)


def _walk_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if _is_ignored(path.relative_to(root)):
            continue
        if path.is_file():
            yield path


class _RepoPool:
    """One pristine template plus one reused working tree, built lazily on first use.

    Copying the whole repository per mutation test was measured at 60% of the owning module's
    wall-clock (93 copies × ~160-325ms). The pool replaces every copy after the first two with
    a restore that compares each file's CONTENT against a SHA-256 manifest of the template —
    never stat shortcuts, whose mtime granularity on some filesystems would miss a same-size
    rewrite — so every borrower still provably starts pristine. The pool is process-local and
    unittest runs tests sequentially, so no two borrowers overlap.
    """

    def __init__(self) -> None:
        # Held for the process lifetime; the TemporaryDirectory finalizer cleans up at exit.
        self._holder = tempfile.TemporaryDirectory()
        base = Path(self._holder.name)
        self.template = base / "template"
        shutil.copytree(REPO, self.template, ignore=_copy_ignore)
        self.work = base / "repo"
        shutil.copytree(self.template, self.work)
        self.manifest = {
            path.relative_to(self.template): hashlib.sha256(path.read_bytes()).digest()
            for path in _walk_files(self.template)
        }
        self.directories = {
            path.relative_to(self.template)
            for path in self.template.rglob("*")
            if path.is_dir() and not _is_ignored(path.relative_to(self.template))
        }

    def _remove_links_top_down(self, directory: Path) -> None:
        with os.scandir(directory) as entries:
            children = sorted(entries, key=lambda entry: entry.name)
        for entry in children:
            if _is_ignored(Path(entry.path).relative_to(self.work)):
                continue
            path = Path(entry.path)
            if _is_link(path):
                _remove_link(path)
            elif entry.is_dir(follow_symlinks=False):
                self._remove_links_top_down(path)

    def restore(self) -> None:
        """Return the working tree to exactly the manifest's content, whatever the last test did."""
        # Links first: the template is link-free by construction (copytree resolves links), so
        # any symlink OR Windows junction here is borrower residue — and hashing or copyfile
        # would follow it, letting a restore WRITE THROUGH the link to a target outside the
        # pool (caught in review on #91, junctions included: is_symlink() alone misses them).
        # Removing the link itself makes the content passes below see a plain missing entry
        # and restore it from the template. The walk is explicitly top-down, removing each
        # link BEFORE descending: a recursive enumeration like rglob would follow a junction
        # first — pathlib's symlink-skip does not cover directory reparse points — so a
        # junction to an ancestor would cycle until path-length exhaustion.
        self._remove_links_top_down(self.work)
        seen: set[Path] = set()
        for path in _walk_files(self.work):
            rel = path.relative_to(self.work)
            seen.add(rel)
            want = self.manifest.get(rel)
            # nlink > 1 means the borrower hard-linked this entry to another inode — pool files
            # are independent inodes by construction — and writing "through" it would corrupt
            # the other side, possibly outside the fixture (caught in review on #91). So a
            # shared or changed entry is REPLACED (unlink, then copy), never written in place,
            # and a hard link is broken even when its content matches the manifest.
            hardlinked = path.stat().st_nlink > 1
            if want is None:
                path.unlink()  # file the last borrower added
            elif hardlinked or hashlib.sha256(path.read_bytes()).digest() != want:
                path.unlink()
                shutil.copyfile(self.template / rel, path)  # file the last borrower changed
        for rel in self.manifest.keys() - seen:
            target = self.work / rel
            if target.is_dir():
                # A directory now shadows the manifest file's path (the borrower replaced the
                # file); its contents were already removed above as additions, but copyfile
                # onto the shell would raise and poison the pool for every later borrower.
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.template / rel, target)  # file the last borrower deleted
        # Directories the borrower ADDED are not invisible once their files are gone: an empty
        # skills/<name>/ shell reads to validate_skills() as a skill missing its SKILL.md, so a
        # leftover would hand later borrowers a tree the validator judges differently (caught in
        # review on #91). Shallowest-first, so one rmtree takes any nested additions with it.
        for rel in sorted(
            path.relative_to(self.work)
            for path in self.work.rglob("*")
            if path.is_dir() and not _is_ignored(path.relative_to(self.work))
        ):
            if rel not in self.directories:
                target = self.work / rel
                if target.is_dir():
                    shutil.rmtree(target)


_pool: _RepoPool | None = None


@contextlib.contextmanager
def repo_copy() -> Iterator[Path]:
    """A disposable copy of the real repository, for mutation tests.

    Wiring invariants are proven against a copy of the actual repo, not a synthetic fixture
    that could drift away from it. tests/ stays in the copy: AGENTS.md names `tests/fixtures/`,
    and the guide drift check resolves every multi-segment path it asserts. Exclusions are
    exactly `_IGNORED_DIRS` — see its comment for why each entry is not part of the tree under
    validation.

    Callers may mutate file contents, add files or symlinks, or delete anything under the
    yielded path, and must not touch it after the with-block: the tree is pooled, and the next
    borrower gets it restored by content (symlinks a borrower left behind are removed, never
    followed). Restoration is content-level only — a test that needs to mutate file metadata
    (permissions, timestamps) must build its own copy instead.
    """
    global _pool
    if _pool is None:
        _pool = _RepoPool()
    else:
        _pool.restore()
    yield _pool.work


class TempDirTestCase(unittest.TestCase):
    """Test case with a cleanup-safe temporary directory available as ``self.base``."""

    def setUp(self) -> None:
        super().setUp()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)


def run_main(main: Callable[[list[str]], int], *argv: str) -> tuple[int, str]:
    """Call a script's main(argv) in-process, returning (exit code, stdout).

    Stderr is swallowed rather than asserted on: the scripts' contract is exit code plus
    stdout, and pinning diagnostics would turn every reworded warning into a test failure.
    """
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


def git(root: Path, *args: str) -> None:
    """Run git against a test repo, capturing output and failing on a nonzero exit."""
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
