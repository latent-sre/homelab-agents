"""Content identity for a routing measurement: what was measured, by what, against which bytes.

Moved here whole from `scripts/eval_routing.py` when phase 4 retired that runner. It is the part
of the runner that does NOT become the platform's: `claude plugin eval` owns isolation, runs,
concurrency and cost caps, but nothing in it identifies the plugin bytes a result was taken
against, and without that the paired before/after discipline `AGENTS.md` requires at T3 is not a
comparison -- it is two numbers side by side.

Every digest is length-framed before hashing, so concatenation cannot make two different trees
collide at the serialization layer. Only digests and scope metadata are returned; repository
content never is.

One behaviour survives the move unchanged because it is the reason `frozen_plugin` exists:
endpoint hashing alone cannot detect an A -> B -> A edit made while sessions are loading a source
checkout, so a measurement executes bytes collected for one content identity out of a private
copy, and re-checks the endpoint afterwards.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

from fleet import fs

# The repository this kernel ships in. Only used to shorten a path for display, so that a label in
# a stored artifact does not carry the operator's home directory into a shared record.
REPO = Path(__file__).resolve().parents[1]

# v4 (2026-08-17): the identity narrowed to what the scorer reads. `selection.definitions` now
# hashes only the graded case fields (GRADED_CASE_FIELDS) instead of whole case dicts, and the
# reusability check no longer compares `eval_sources`, which hashed each cluster file whole and so
# invalidated captures on comment-only edits. Both changes remove invalidations that protected
# nothing. The version moves because a v3 selection hash was computed over different bytes and
# cannot be compared with a v4 one — reporting that as "selection diverged" would misattribute a
# schema change to a routing change.
#
# Two later hashing changes in the same PR deliberately did NOT take a v5, and the reason is the
# rule for the next one: the version exists so a STORED capture computed under older rules is
# reported as a schema difference rather than a routing one. Every stored capture is v3 (8) or
# unversioned (17) — no v4 capture has ever been written — and `provenance_divergences` returns on a
# schema mismatch before it compares `selection`, so those captures can never reach the changed
# hashing at all. A v5 would therefore rename something no reader can observe. Bump when a capture
# exists that the change would misreport; not merely because the hash moved.
PROVENANCE_SCHEMA = "sde-agents/eval-provenance/v4"


# `claude --plugin-dir` discovers these authored/runtime surfaces. The allowlist is deliberate:
# test fixtures, eval outputs, repository docs, generated host adapters, and operator scratch state
# are not inputs to the Claude plugin being measured, so hashing the whole checkout would make a
# benchmark identity move for irrelevant reasons. Runtime text may name additional files through
# ${CLAUDE_PLUGIN_ROOT} or a safe backticked repository-relative path; those exact references are
# discovered and included below (the fleet's read-only guard and learning ledger are examples).
PLUGIN_RUNTIME_DIRS = (".claude-plugin", "agents", "commands", "hooks", "skills", "workflows")


PLUGIN_RUNTIME_FILES = (".mcp.json",)


PLUGIN_HASH_EXCLUSIONS = (
    ".git/**",
    "evals/**",
    "unreferenced docs/**",
    "tests/**",
    ".agents/**",
    ".claude/**",
    ".codex/**",
    ".codex-plugin/**",
    ".github/**",
    ".probe-tmp/**",
    ".superpowers/**",
    "platforms/**",
    "plugins/**",
    "unreferenced repository-only root documents",
    "all other top-level entries outside the runtime allowlist",
    "**/__pycache__/**, **/*.pyc, editor and OS transient files",
)


_HARD_EXCLUDED_REFERENCE_ROOTS = frozenset(
    {
        ".git",
        "evals",
        "tests",
        ".agents",
        ".claude",
        ".codex",
        ".codex-plugin",
        ".github",
        ".probe-tmp",
        ".superpowers",
        "platforms",
        "plugins",
    }
)


_TRANSIENT_DIR_NAMES = frozenset(
    {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache"}
)


_TRANSIENT_FILE_NAMES = frozenset({".DS_Store", "Thumbs.db", ".coverage"})


_PLUGIN_ROOT_REFERENCE = re.compile(rb"\$\{CLAUDE_PLUGIN_ROOT\}[\\/]+([A-Za-z0-9_.\\/\-]+)")


_BACKTICK_CONTENT = re.compile(rb"(?<!`)`([^`\r\n]+)`(?!`)")


_SAFE_RELATIVE_PART = re.compile(r"(?=.*[A-Za-z0-9_-])[A-Za-z0-9_.-]+\Z")


class ProvenanceError(RuntimeError):
    """The eval input cannot be identified without following an unsafe filesystem entry."""


def canonicalize_tempdir() -> None:
    """Point the process's temp root at its real path, so the ancestor walk can accept it.

    macOS mounts /var, /tmp, and /etc as symlinks to /private/* by OS design, so every
    tempfile-derived path fails `_check_existing_ancestors` on that platform alone -- ten
    provenance tests red on the macOS CI job from the day the walk shipped, green everywhere
    else. Canonicalizing the temp ROOT once fixes every present and future tempfile call site
    in one place; the walk stays fully strict below the base, so a link planted inside the
    harness's own scratch tree still refuses. Process-global on purpose: any process that loads
    this provenance layer needs canonical scratch paths or its own temp dirs are unreadable to
    it. Dropped during the move out of the runner and restored after review caught it; the
    three-OS matrix at T2 would have found it only after merge.
    """
    tempfile.tempdir = os.path.realpath(tempfile.gettempdir())


canonicalize_tempdir()


def _checked_stat(path: Path):
    try:
        file_stat = path.lstat()
    except OSError as exc:
        raise ProvenanceError(f"cannot inspect provenance path {path}: {exc}") from exc
    if fs.is_link_or_reparse(file_stat):
        raise ProvenanceError(
            f"unsafe provenance path {path}: symlinks, junctions, and reparse points are refused"
        )
    return file_stat


def _check_existing_ancestors(path: Path) -> None:
    """Reject a link in any existing path component before opening the target."""
    absolute = fs.absolute_without_resolving(path)
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current /= part
        _checked_stat(current)


def _read_regular_file(path: Path, *, max_bytes: int | None = None) -> bytes:
    """Read bytes without links, special files, unbounded input, or mid-read changes."""
    path = fs.absolute_without_resolving(path)
    _check_existing_ancestors(path)
    before = _checked_stat(path)
    if not stat.S_ISREG(before.st_mode):
        raise ProvenanceError(f"provenance input is not a regular file: {path}")
    if max_bytes is not None and before.st_size > max_bytes:
        raise ProvenanceError(f"provenance input exceeds {max_bytes} bytes: {path}")
    try:
        if max_bytes is None:
            content = path.read_bytes()
        else:
            with path.open("rb") as stream:
                content = stream.read(max_bytes + 1)
    except OSError as exc:
        raise ProvenanceError(f"cannot read provenance input {path}: {exc}") from exc
    if max_bytes is not None and len(content) > max_bytes:
        raise ProvenanceError(f"provenance input exceeds {max_bytes} bytes: {path}")
    after = _checked_stat(path)
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity:
        raise ProvenanceError(f"provenance input changed while it was being read: {path}")
    return content


def _portable_path_label(path: Path) -> str:
    absolute = fs.absolute_without_resolving(path)
    try:
        return absolute.relative_to(fs.absolute_without_resolving(REPO)).as_posix() or "."
    except ValueError:
        return absolute.as_posix()


def evaluator_identity(paths: list[Path]) -> dict:
    """Content identity for the code that turns transcripts into benchmark verdicts.

    The retiring runner bound this to the exact source buffer it had compiled: it was one file
    that both ran the sessions and graded them, so it could re-execute itself from checked bytes
    and hash those. Phase 4 splits those jobs -- the platform runs, `fleet.routing` and
    `fleet.nativecases` grade -- and the graders are ordinary imported modules, so binding only
    the entry script would give a guarantee over a shrinking fraction of the code that decides a
    verdict. That is worse than a plain one, because it reads like the old guarantee.

    So this hashes the files as they are on disk when a measurement is recorded, and claims
    exactly that. The window it no longer closes -- an evaluator source edited between import and
    record, by the operator running the measurement -- is narrower than the one `frozen_plugin`
    closes for the plugin under test, which is a different party's bytes.
    """
    if not paths:
        raise ProvenanceError("evaluator provenance requires at least one source file")
    records: list[dict[str, str]] = []
    for path in paths:
        absolute = fs.absolute_without_resolving(path)
        records.append(
            {
                "path": _portable_path_label(absolute),
                "sha256": _sha256(_read_regular_file(absolute)),
            }
        )
    records.sort(key=lambda record: record["path"])
    labels = [record["path"] for record in records]
    if len(labels) != len(set(labels)):
        raise ProvenanceError("evaluator provenance contains the same source file more than once")
    canonical = json.dumps(
        records, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return {
        "sha256": _sha256(canonical),
        "files": records,
        # The interpreter is part of the evaluator: two Pythons can disagree about, for example,
        # what `str.splitlines()` treats as a line break in a transcript.
        "runtime": {
            "implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
        },
    }


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def source_identity(paths: list[Path]) -> list[dict]:
    """SHA-256 records for exact eval-source bytes, sorted by portable path label."""
    records = [
        {"path": _portable_path_label(path), "sha256": _sha256(_read_regular_file(path))}
        for path in paths
    ]
    return sorted(records, key=lambda record: record["path"])


GRADED_CASE_FIELDS = ("id", "polarity", "prompt", "expect_fires", "expect_not_fires")


# Graded as SETS by `_scoring_targets`, so their array order and any duplicate are invisible
# to every verdict and must be invisible to the identity too.
_UNORDERED_TARGET_FIELDS = frozenset({"expect_fires", "expect_not_fires"})


def _graded_definition(case: dict) -> dict:
    """The fields of a case the scorer actually reads.

    `expected_output` and `tags` are documentation of intent: `score_case` never reads either, so
    hashing them made a comment edit invalidate a stored baseline that measured byte-identical
    routing. Narrowing the identity to the graded fields removes invalidations that protect
    nothing — it does not weaken the identity, because a field the grader cannot see cannot change
    a rate. Add a field here in the same change that makes the scorer read it.

    A case-level `threshold` was listed here and is not: `score_case` takes the threshold as an
    ARGUMENT and `main` passes `args.threshold`, so nothing reads `case["threshold"]` and a
    per-case value grades identically to its absence. Listing it meant an inert field could stale
    every stored baseline for a cluster whose grading had not moved — the exact re-buy this
    narrowing exists to stop, reintroduced by the narrowing itself. If per-case thresholds are ever
    implemented, this entry returns in that same change (PR #145 review).
    """
    return {
        # `expect_fires` / `expect_not_fires` are hashed as sorted unique values because
        # `_scoring_targets` returns `set(raw_targets)` — order and duplicates are both discarded
        # before anything is graded, so preserving array order here made a pure reorder read as a
        # routing change and demanded a fresh paid capture. Same reason `members` is sorted above
        # (PR #145 review). Every other graded field keeps its literal value: `prompt` and `id` are
        # compared as written, and `polarity` is a scalar.
        field: sorted(set(case[field])) if field in _UNORDERED_TARGET_FIELDS else case[field]
        for field in GRADED_CASE_FIELDS
        if field in case
    }


def validated_members(raw: object) -> list[str]:
    """The ONE place the `members` rule lives, because three paths hash that value.

    A cluster's members reach `sorted(set(...))` in `selection_identity`, so a malformed list
    (`["prompt-craft", 1]`) raises an uncaught TypeError wherever it is hashed. The rule was stated
    inline in `main()`, restated in a second validator this repo has since retired, and absent from
    the post-session reread — so the reread crashed on a cluster edited mid-run while the other two
    refused it cleanly. Three copies of a rule is how a path ends up without it (PR #145 review).
    """
    if (
        not isinstance(raw, list)
        or not raw
        or any(not isinstance(member, str) or not member.strip() for member in raw)
    ):
        raise ProvenanceError(
            "cluster error: 'members' must be a non-empty list of component names"
        )
    return list(raw)


def selection_identity(
    expression: str,
    cases: list[dict],
    limit: int | None = None,
    *,
    members: list[str] | None = None,
) -> dict:
    """Hash selected definitions, the cluster's members, and the exact selection operation.

    `members` is a grading input, not context: a negative with no `expect_not_fires` is graded
    against the WHOLE member list (`_scoring_targets`), and `required_agents` is derived from it, so
    a membership change moves what the same case bytes assert. It is hashed here because narrowing
    the identity to graded case fields would otherwise let a membership change pass unnoticed —
    `eval_sources` used to catch it only as a side effect of hashing the whole cluster file.
    """
    case_ids = [case["id"] for case in cases]
    selected = {
        "expression": expression,
        "limit": limit,
        "case_ids": case_ids,
        # sorted UNIQUE, for the same reason the target lists are: routing does `set(raw_members)`
        # before grading, required-agent calculation, and serialization, so a repeated member
        # changes no measurement — and preserving the duplicate here staled a capture for an edit
        # no verdict could see. `members` was sorted one round before the target lists and did not
        # get the dedupe half of the same fact (PR #145 review).
        "members": sorted(set(members)) if members is not None else None,
        "definitions": [_graded_definition(case) for case in cases],
    }
    canonical = json.dumps(
        selected, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return {
        "expression": expression,
        "limit": limit,
        "case_ids": case_ids,
        "members": sorted(set(members)) if members is not None else None,
        "canonicalization": (
            "JSON UTF-8, sorted object keys, compact separators, array order preserved"
        ),
        "sha256": _sha256(canonical),
    }


def _is_transient(path: Path) -> bool:
    return (
        path.name in _TRANSIENT_DIR_NAMES
        or path.name in _TRANSIENT_FILE_NAMES
        or path.suffix in {".pyc", ".pyo", ".tmp", ".swp"}
        or path.name.endswith("~")
    )


def _collect_runtime_path(root: Path, path: Path, files: dict[str, bytes]) -> None:
    file_stat = _checked_stat(path)
    if _is_transient(path):
        return
    if stat.S_ISREG(file_stat.st_mode):
        relative = path.relative_to(root).as_posix()
        files[relative] = _read_regular_file(path)
        return
    if not stat.S_ISDIR(file_stat.st_mode):
        raise ProvenanceError(f"unsafe non-file entry in plugin provenance scope: {path}")
    try:
        children = sorted(path.iterdir(), key=lambda child: child.name.replace("\\", "/"))
    except OSError as exc:
        raise ProvenanceError(f"cannot traverse plugin provenance path {path}: {exc}") from exc
    for child in children:
        _collect_runtime_path(root, child, files)


def _reference_parts(raw: bytes, source: str) -> tuple[str, ...]:
    referenced = raw.decode("ascii").replace("\\", "/").rstrip("/")
    parts = tuple(part for part in referenced.split("/") if part not in ("", "."))
    if not parts or ".." in parts:
        raise ProvenanceError(f"unsafe repository-relative reference in {source}: {referenced!r}")
    return parts


def _backticked_repo_paths(content: bytes, source: str) -> list[tuple[str, ...]]:
    """Extract bounded, safe relative-path tokens from inline-code spans.

    Runtime instructions conventionally backtick paths. Restricting discovery to those spans and
    existing regular files lets an explicitly directed dependency affect identity without turning
    every prose word—or the whole repository—into plugin content.
    """
    paths: set[tuple[str, ...]] = set()
    for span_match in _BACKTICK_CONTENT.finditer(content):
        for raw_token in re.split(rb"\s+", span_match.group(1)):
            token = raw_token.strip(b"'\"(),;[]{}")
            if token.startswith(b"./") or token.startswith(b".\\"):
                token = token[2:]
            if not token or token.startswith((b"/", b"\\")):
                continue
            try:
                normalized = token.decode("ascii").replace("\\", "/").rstrip("/")
            except UnicodeDecodeError:
                continue
            # A plain component name is usually an agent, skill, command, or flag rather than a
            # path. A dotted root file such as README.md remains eligible.
            if "/" not in normalized:
                if normalized in (".", "..", "...") or "." not in normalized:
                    continue
            parts = tuple(normalized.split("/"))
            if ".." in parts:
                raise ProvenanceError(
                    f"unsafe repository-relative reference in {source}: {normalized!r}"
                )
            if any(not _SAFE_RELATIVE_PART.fullmatch(part) for part in parts):
                continue
            if parts[0] in _HARD_EXCLUDED_REFERENCE_ROOTS:
                continue
            if any(part in _TRANSIENT_DIR_NAMES or part in _TRANSIENT_FILE_NAMES for part in parts):
                continue
            paths.add(parts)
    return sorted(paths)


def _git_identity(root: Path) -> tuple[str | None, bool | None]:
    git = shutil.which("git")
    if git is None:
        return None, None
    quiet_env = dict(os.environ)
    quiet_env["GIT_OPTIONAL_LOCKS"] = "0"
    common = {
        "capture_output": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": 30,
        "env": quiet_env,
    }
    try:
        head = subprocess.run([git, "-C", str(root), "rev-parse", "--verify", "HEAD"], **common)
        status_result = subprocess.run(
            [git, "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"],
            **common,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None
    if head.returncode != 0 or status_result.returncode != 0:
        return None, None
    return head.stdout.strip() or None, bool(status_result.stdout)


def _plugin_runtime_files(plugin_dir: Path) -> tuple[Path, dict[str, bytes], set[str]]:
    """Read one complete, link-safe snapshot of every runtime-relevant plugin file."""
    root = fs.absolute_without_resolving(plugin_dir)
    _check_existing_ancestors(root)
    root_stat = _checked_stat(root)
    if not stat.S_ISDIR(root_stat.st_mode):
        raise ProvenanceError(f"plugin directory is not a directory: {root}")

    files: dict[str, bytes] = {}
    included: set[str] = set()
    for name in (*PLUGIN_RUNTIME_DIRS, *PLUGIN_RUNTIME_FILES):
        path = root / name
        try:
            path.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ProvenanceError(f"cannot inspect plugin provenance path {path}: {exc}") from exc
        _collect_runtime_path(root, path, files)
        included.add(name)

    # Runtime text can name supporting files outside the conventional plugin directories. Include
    # exact plugin-root references and existing safe paths in inline-code spans recursively, without
    # interpreting or executing content. A missing backticked path may be a worked example; it is
    # ignored. `${CLAUDE_PLUGIN_ROOT}` is authoritative, so its missing target fails closed.
    instruction_files = set(files)
    scanned: set[str] = set()
    while pending := sorted(set(files) - scanned):
        relative = pending[0]
        scanned.add(relative)
        for match in _PLUGIN_ROOT_REFERENCE.finditer(files[relative]):
            parts = _reference_parts(match.group(1), relative)
            if parts[0] in _HARD_EXCLUDED_REFERENCE_ROOTS:
                continue
            target = root.joinpath(*parts)
            try:
                target.lstat()
            except OSError as exc:
                raise ProvenanceError(
                    f"runtime dependency named by {relative} cannot be inspected: {target}: {exc}"
                ) from exc
            _collect_runtime_path(root, target, files)
            included.add("/".join(parts))
        for parts in (
            _backticked_repo_paths(files[relative], relative)
            if relative in instruction_files
            else ()
        ):
            target = root.joinpath(*parts)
            try:
                target.lstat()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise ProvenanceError(
                    f"repo-relative dependency named by {relative} cannot be inspected: "
                    f"{target}: {exc}"
                ) from exc
            target_stat = _checked_stat(target)
            if not stat.S_ISREG(target_stat.st_mode):
                continue
            files[target.relative_to(root).as_posix()] = _read_regular_file(target)
            included.add("/".join(parts))

    if not files:
        raise ProvenanceError(
            f"no plugin runtime files found under {root}; refusing an identity for an empty scope"
        )
    return root, files, included


def _plugin_identity_from_files(
    root: Path,
    files: dict[str, bytes],
    included: set[str],
) -> dict:
    """Identify the exact in-memory snapshot returned by `_plugin_runtime_files`."""
    digest = hashlib.sha256()
    digest.update(b"sde-agents-plugin-content-v1\0")
    for relative in sorted(files):
        name_bytes = relative.encode("utf-8")
        content = files[relative]
        digest.update(len(name_bytes).to_bytes(8, "big"))
        digest.update(name_bytes)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)

    git_head, git_dirty = _git_identity(root)
    return {
        "sha256": digest.hexdigest(),
        "files_hashed": len(files),
        "scope": {
            "strategy": "runtime allowlist plus referenced repository-local dependencies",
            "included": sorted(included),
            "excluded": list(PLUGIN_HASH_EXCLUSIONS),
        },
        "git_head": git_head,
        "git_dirty": git_dirty,
        "git_scope": "containing worktree" if git_head is not None else None,
    }


def plugin_identity(plugin_dir: Path) -> dict:
    """Content-derived identity for the plugin surfaces a Claude eval can load.

    Paths and bytes are length-framed before hashing, so concatenation cannot make two different
    trees collide at the serialization layer. Only digests and scope metadata enter benchmark.json;
    raw repository content never does.
    """
    root, files, included = _plugin_runtime_files(plugin_dir)
    return _plugin_identity_from_files(root, files, included)


@contextlib.contextmanager
def frozen_plugin(plugin_dir: Path):
    """Yield a private execution copy whose bytes cannot follow edits to the source checkout.

    Endpoint hashing alone cannot detect A -> B -> A edits made while concurrent sessions are
    loading a source checkout. The eval therefore executes the exact bytes collected for one
    content identity from an unadvertised temporary directory. A final identity check detects a
    session-side mutation left in place. It cannot detect a same-user session mutating and restoring
    the snapshot between checks; preventing that is a host-sandbox boundary, not a hash claim.
    """
    source_root, files, included = _plugin_runtime_files(plugin_dir)
    source_identity = _plugin_identity_from_files(source_root, files, included)
    with tempfile.TemporaryDirectory(prefix="sde-agents-eval-plugin-") as temp_dir:
        frozen_root = Path(temp_dir) / "plugin"
        frozen_root.mkdir()
        for relative, content in files.items():
            target = frozen_root / Path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            # Carry the EXECUTABLE bit across. `write_bytes` creates with the process umask, so a
            # plugin that runs one of its own files -- a hook command under
            # `${CLAUDE_PLUGIN_ROOT}` -- met `Permission denied` inside the snapshot while the
            # byte-only identity still matched, and the benchmark then measured behaviour the
            # supplied plugin does not have. Only the execute bits are copied: identity stays
            # byte-derived on purpose (a mode is not content), so this restores fidelity without
            # widening what a hash claims.
            try:
                source_mode = (source_root / Path(relative)).stat().st_mode
            except OSError:
                continue
            executable = source_mode & 0o111
            if executable:
                target.chmod((target.stat().st_mode | executable) & 0o7777)
        frozen_identity = plugin_identity(frozen_root)
        if source_identity["sha256"] != frozen_identity["sha256"]:
            raise ProvenanceError(
                "frozen plugin snapshot does not match the source bytes collected for execution"
            )
        yield frozen_root, source_identity


def verify_frozen_plugin(plugin_dir: Path, expected_identity: dict) -> None:
    """Fail when a private-snapshot mutation remains observable at the endpoint."""
    actual = plugin_identity(plugin_dir)
    if actual["sha256"] != expected_identity["sha256"]:
        raise ProvenanceError("frozen plugin content changed while the batch was running")


def benchmark_provenance(
    source_paths: list[Path],
    cases: list[dict],
    expression: str,
    plugin_dir: Path,
    limit: int | None = None,
    *,
    evaluator_paths: list[Path],
    plugin_identity_value: dict | None = None,
    members: list[str] | None = None,
) -> dict:
    return {
        "schema": PROVENANCE_SCHEMA,
        "eval_sources": source_identity(source_paths),
        "selection": selection_identity(expression, cases, limit, members=members),
        # This is deliberately separate from the plugin under test. A copied or external plugin
        # directory does not identify the local runner and deterministic graders that interpreted
        # its transcripts.
        "evaluator": evaluator_identity(evaluator_paths),
        # Claude evaluates plugin runtime bytes; another runtime may execute a narrower captured
        # projection. A precomputed identity binds provenance to those already-captured bytes while
        # retaining one schema without conflating scopes.
        "plugin": (
            plugin_identity(plugin_dir) if plugin_identity_value is None else plugin_identity_value
        ),
    }


def _content_provenance_matches(before: dict, after: dict) -> bool:
    """Git dirtiness may move for excluded files; measurement inputs and evaluator may not."""
    return (
        before["eval_sources"] == after["eval_sources"]
        and before["selection"] == after["selection"]
        and before["evaluator"] == after["evaluator"]
        and before["plugin"]["sha256"] == after["plugin"]["sha256"]
    )
