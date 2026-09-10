#!/usr/bin/env python3
"""Routing eval runner — measure whether the fleet routes a prompt to the right component.

WHY THIS EXISTS. `agents/prompt-engineer.md` mandates eval-first prompt changes (baseline,
repetitions, fresh contexts), but the fleet shipped none — it preached a practice it did not
follow. This is the practice: given a realistic prompt, does the intended agent/skill fire, and do
near-miss prompts that merely share vocabulary (write / fix / optimize / rewrite) route ELSEWHERE?

WHY A LOCAL RUNNER AND NOT `claude plugin eval`. The native harness is the right long-term home —
it does ablation baselines, repetitions, and LLM grading — but it is currently EARLY ACCESS and
does not run in every environment. The case files here follow the Agent Skills eval shape
(agentskills.io/skill-creation/evaluating-skills) so they migrate cleanly when it opens; this
runner exercises them TODAY, and retires when `claude plugin eval` is generally available.

HOW IT GRADES. Routing is a fact you can read straight off the transcript — which Skill was
invoked, which subagent was spawned — so grading needs no judge model and is deterministic and
free. A positive case passes when an expected cluster member fires; a negative passes only when
none of its FORBIDDEN set fires, and that set is the whole cluster unless the case narrows it with
`expect_not_fires` (a disambiguation case: "X must not fire here, but its sibling Y is the correct
destination"). Routing is probabilistic (a skill/agent fires perhaps half the time in practice), so
results are RATES over --runs, not booleans. The load-bearing signals are a positive whose rate
collapses after a description edit (regression) and a negative that fires at all (over-trigger) —
both visible in the delta between runs of this suite.

Pure standard library. Spawns headless `claude -p ... --plugin-dir <repo>` sessions, one per run,
each with a fresh cwd and conversation. A fresh session is NOT configuration isolation: it still
inherits everything under the user's CLAUDE_CONFIG_DIR (personal agents, skills, plugins, global
CLAUDE.md), and a junction deployment makes the fleet register twice — bare and namespaced — in
every run. `--clean-room` (scripts/eval_clean_room.py) is the isolation switch, and it is recorded
in `conditions` because two artifacts that differ on it are not comparable.

Every written artifact also carries `provenance`: hashes of the exact cluster bytes, canonical
selected cases, evaluator/grader sources, and runtime-relevant plugin content. Sessions execute a
private copy of the identified plugin bytes, closing source-checkout A -> B -> A drift and detecting
a private-snapshot mutation that remains at the endpoint. Same-user session code can transiently
mutate and restore that copy unless the host sandbox denies writes; endpoint hashing is not an
immutability boundary.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import fnmatch
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAUDE = shutil.which("claude")

# The fleet roster, derived from the repo so this never drifts from what actually ships.
FLEET_AGENTS = frozenset(p.stem for p in (REPO / "agents").glob("*.md"))
FLEET_SKILLS = frozenset(p.name for p in (REPO / "skills").iterdir() if p.is_dir()) if (REPO / "skills").is_dir() else frozenset()
FLEET = FLEET_AGENTS | FLEET_SKILLS
NAMESPACED_FLEET_AGENTS = frozenset(f"sde-agents:{name}" for name in FLEET_AGENTS)

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
_HARD_EXCLUDED_REFERENCE_ROOTS = frozenset({
    ".git", "evals", "tests", ".agents", ".claude", ".codex", ".codex-plugin",
    ".github", ".probe-tmp", ".superpowers", "platforms", "plugins",
})
_TRANSIENT_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache"})
_TRANSIENT_FILE_NAMES = frozenset({".DS_Store", "Thumbs.db", ".coverage"})
_PLUGIN_ROOT_REFERENCE = re.compile(
    rb"\$\{CLAUDE_PLUGIN_ROOT\}[\\/]+([A-Za-z0-9_.\\/\-]+)"
)
_BACKTICK_CONTENT = re.compile(rb"(?<!`)`([^`\r\n]+)`(?!`)")
_SAFE_RELATIVE_PART = re.compile(r"(?=.*[A-Za-z0-9_-])[A-Za-z0-9_.-]+\Z")


class ProvenanceError(RuntimeError):
    """The eval input cannot be identified without following an unsafe filesystem entry."""


class EvalAuthUnavailable(RuntimeError):
    """A model session could not authenticate, so the batch produced no valid benchmark."""


class EvalRegistrationUnavailable(RuntimeError):
    """The session did not prove that the namespaced fleet under test was registered."""


_CLEAN_ROOM_MODULE = None
_LOADED_EVALUATOR_SOURCES: dict[str, bytes] = {}
_EXECUTING_EVALUATOR_SOURCE = globals().get("_SDE_EVAL_EXECUTING_SOURCE")

# macOS mounts /var, /tmp, and /etc as symlinks to /private/* by OS design, so every
# tempfile-derived path fails the ancestor link-walk below on that platform alone — ten
# provenance tests red on the macOS CI job from the day the walk shipped, green everywhere
# else. Canonicalizing the temp ROOT once at import fixes every present and future
# tempfile call site in one place; the walk stays fully strict below the base, so a link
# planted inside the harness's own scratch tree still refuses. Process-global on purpose:
# any process that loads this provenance layer needs canonical scratch paths or its own
# temp dirs are unreadable to it.
tempfile.tempdir = os.path.realpath(tempfile.gettempdir())


def _is_link_or_reparse(file_stat) -> bool:
    """True for POSIX symlinks and every Windows reparse-point kind, including junctions."""
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(file_stat.st_mode) or bool(
        getattr(file_stat, "st_file_attributes", 0) & reparse_flag
    )


def _absolute_without_resolving(path: Path) -> Path:
    """Return an absolute lexical path; `resolve()` is forbidden because it follows links."""
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _checked_stat(path: Path):
    try:
        file_stat = path.lstat()
    except OSError as exc:
        raise ProvenanceError(f"cannot inspect provenance path {path}: {exc}") from exc
    if _is_link_or_reparse(file_stat):
        raise ProvenanceError(
            f"unsafe provenance path {path}: symlinks, junctions, and reparse points are refused"
        )
    return file_stat


def _check_existing_ancestors(path: Path) -> None:
    """Reject a link in any existing path component before opening the target."""
    absolute = _absolute_without_resolving(path)
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current /= part
        _checked_stat(current)


def _read_regular_file(path: Path, *, max_bytes: int | None = None) -> bytes:
    """Read bytes without links, special files, unbounded input, or mid-read changes."""
    path = _absolute_without_resolving(path)
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
    absolute = _absolute_without_resolving(path)
    try:
        return absolute.relative_to(_absolute_without_resolving(REPO)).as_posix() or "."
    except ValueError:
        return absolute.as_posix()


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def source_identity(paths: list[Path]) -> list[dict]:
    """SHA-256 records for exact eval-source bytes, sorted by portable path label."""
    records = [
        {"path": _portable_path_label(path), "sha256": _sha256(_read_regular_file(path))}
        for path in paths
    ]
    return sorted(records, key=lambda record: record["path"])


def _evaluator_source_key(path: Path) -> str:
    """Registry key for one evaluator path. normcase is load-bearing on Windows: the filesystem
    treats c:\\repo and C:\\repo as one file, but a case-preserving dict does not — a process whose
    cwd was spelled lowercase then registers and looks up different keys for the same bytes, and
    the provenance read silently falls back to re-reading the file it promised not to (#69)."""
    return os.path.normcase(os.fspath(_absolute_without_resolving(path)))


def register_loaded_evaluator_source(path: Path, content: bytes) -> None:
    """Bind one evaluator path to the exact source bytes compiled in this process."""
    absolute = _absolute_without_resolving(path)
    key = _evaluator_source_key(path)
    prior = _LOADED_EVALUATOR_SOURCES.get(key)
    if prior is not None and prior != content:
        raise ProvenanceError(
            f"evaluator source {absolute} was loaded from two different byte sequences"
        )
    _LOADED_EVALUATOR_SOURCES[key] = bytes(content)


def load_evaluator_module(name: str, path: Path):
    """Compile one evaluator module from the exact checked bytes registered for provenance.

    Import machinery compiles a source buffer before module code starts. Re-reading ``__file__``
    from inside that module can therefore observe disk B even though the process is executing A.
    Evaluator modules use this loader so compilation and provenance consume one byte buffer.
    """
    absolute = _absolute_without_resolving(path)
    source = _read_regular_file(absolute)
    spec = importlib.util.spec_from_file_location(name, absolute)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load evaluator module {name!r} from {absolute}")
    module = importlib.util.module_from_spec(spec)
    module.__dict__["_SDE_EVAL_EXECUTING_SOURCE"] = source
    exec(compile(source, str(absolute), "exec"), module.__dict__)
    register_loaded_evaluator_source(absolute, source)
    return module


def load_current_evaluator():
    """Return this runner compiled from and bound to one checked source buffer.

    The public helper is also the script's self-bootstrap. It lets tests and imported callers run
    the same exact-source path as ``python scripts/eval_routing.py`` instead of relying on a later
    disk read to guess which bytes Python originally compiled.
    """
    return load_evaluator_module("_sde_eval_routing_bound", Path(__file__))


if _EXECUTING_EVALUATOR_SOURCE is not None:
    register_loaded_evaluator_source(Path(__file__), _EXECUTING_EVALUATOR_SOURCE)


def routing_evaluator_paths() -> list[Path]:
    """Exact executable and imported classifier/grader sources for this runner."""
    runner = Path(__file__)
    return [runner, runner.with_name("eval_clean_room.py")]


def evaluator_identity(paths: list[Path]) -> dict:
    """Content identity for the code that turns transcripts into benchmark verdicts."""
    if not paths:
        raise ProvenanceError("evaluator provenance requires at least one source file")
    clean_room_path = _absolute_without_resolving(Path(__file__).with_name("eval_clean_room.py"))
    records: list[dict[str, str]] = []
    for path in paths:
        absolute = _absolute_without_resolving(path)
        # This module used to load lazily after the endpoint hash. Loading it here from one checked
        # byte buffer and hashing that same buffer closes the pre-first-load A -> B -> A race.
        if absolute == clean_room_path:
            _load_clean_room()
        content = _LOADED_EVALUATOR_SOURCES.get(_evaluator_source_key(absolute))
        if content is None:
            content = _read_regular_file(absolute)
        records.append({
            "path": _portable_path_label(absolute),
            "sha256": _sha256(content),
        })
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
        "runtime": {
            "implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
        },
    }


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
        raise ProvenanceError("cluster error: 'members' must be a non-empty list of component names")
    return list(raw)


def selection_identity(
    expression: str, cases: list[dict], limit: int | None = None,
    *, members: list[str] | None = None,
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
        "canonicalization": "JSON UTF-8, sorted object keys, compact separators, array order preserved",
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
    common = {"capture_output": True, "encoding": "utf-8", "errors": "replace",
              "timeout": 30, "env": quiet_env}
    try:
        head = subprocess.run(
            [git, "-C", str(root), "rev-parse", "--verify", "HEAD"], **common
        )
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
    root = _absolute_without_resolving(plugin_dir)
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
            if relative in instruction_files else ()
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
    root: Path, files: dict[str, bytes], included: set[str],
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
    source_paths: list[Path], cases: list[dict], expression: str, plugin_dir: Path,
    limit: int | None = None, *, evaluator_paths: list[Path],
    plugin_identity_value: dict | None = None, members: list[str] | None = None,
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
            plugin_identity(plugin_dir)
            if plugin_identity_value is None
            else plugin_identity_value
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


def strip_ns(name: str) -> str:
    """`sde-agents:prompt-craft` -> `prompt-craft`; a bare name is returned unchanged."""
    return name.split(":", 1)[1] if ":" in name else name


def _event_message_field(event: object, field: str):
    """Read `event["message"][field]`, tolerating a stream event that is not shaped that way.

    Not defensive decoration: `(event.get("message") or {}).get(...)` crashes on an event whose
    `message` is a plain string, and both readers below run on EVERY line of EVERY session. One such
    event raised AttributeError out of `components_fired`, past the behavioral runner's
    `EvalAuthUnavailable`-only handler, and took down the whole batch with no benchmark written —
    observed on a live `verifier-fails-honestly-no-product-edit` session, 2026-08-10. A transcript
    line the reader cannot interpret must be skipped, never fatal: the sessions are already paid
    for by the time it is parsed.
    """
    if not isinstance(event, dict):
        return None
    message = event.get("message")
    return message.get(field) if isinstance(message, dict) else None


def decode_stream(value: object) -> str:
    """Text for a captured stream, whatever the failure path handed us.

    Not a convenience wrapper: `subprocess.TimeoutExpired.stdout` is **bytes even when the call
    passed `encoding=`**, so an `isinstance(value, str)` test silently yields "" and throws away
    the partial transcript of a session that was already paid for. Every timed-out run then
    reports no tokens, no model, and no duration into a `conditions` block whose whole purpose is
    stating what was measured. Readers of both Claude-side runners route through here so the
    bytes/str asymmetry is answered in one place.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return ""


def components_fired(transcript: str) -> set[str]:
    """The set of fleet components (bare names) invoked anywhere in a run's transcript.

    Detects the two invocation paths: the Skill tool (a skill fired) and the Agent/Task tool (a
    subagent spawned). Rather than guess the exact input field name — which differs across the two
    and across CLI versions — it scans each relevant tool_use's input values for a known fleet name.
    A component named only in ASSISTANT PROSE (not a tool call) is intentionally NOT counted: the
    model mentioning 'prompt-craft' is not the same as prompt-craft firing. A tool_use whose matching
    tool_result is a GENUINE dispatch failure is likewise NOT counted — counting a truly failed
    spawn would produce false PASS results (see scripts/probe_plugin.py:174 for the same
    correlate-by-tool_use_id pattern).

    Crucially, `is_error` is NOT a reliable "the call failed" flag for the Skill tool. A skill that
    restricts tools (allowed-tools / disallowed-tools) is LAUNCHED via a tool_result the CLI marks
    `is_error: true` with content "Execute skill: <name>"; a skill WITHOUT restrictions reports
    "Launching skill: <name>" with is_error unset. Both mean the skill was invoked — the routing fact
    we grade. Treating the first as an error silently dropped every tool-restricting skill's
    invocation: `lab-audit` (which sets `disallowed-tools`) scored 0/N despite routing correctly on
    every run, and — worse — an over-trigger of `lab-audit` on a NEGATIVE case was invisible, a false
    PASS. So a skill-launch control signal is never treated as a failure; only a genuine hard error
    (real dispatch failure, different content) excludes the routing decision.
    """
    launch_signals = ("execute skill:", "launching skill:")
    candidates: dict[str, set[str]] = {}  # tool_use_id -> bare names named in this call
    errored: set[str] = set()  # tool_use_ids whose tool_result was a genuine dispatch failure
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = _event_message_field(event, "content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "tool_use" and block.get("name") in ("Skill", "Agent", "Task"):
                names = {strip_ns(v) for v in _string_values(block.get("input"))} & FLEET
                if names:
                    candidates[block.get("id", "")] = names
            elif btype == "tool_result" and block.get("is_error"):
                result_text = " ".join(_string_values(block.get("content"))).lower()
                if any(sig in result_text for sig in launch_signals):
                    continue  # skill-launch control signal, not a failure — the skill WAS invoked
                errored.add(block.get("tool_use_id", ""))
    fired: set[str] = set()
    for tid, names in candidates.items():
        if tid not in errored:
            fired |= names
    return fired


def _string_values(obj) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in _string_values(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in _string_values(v)]
    return []


def transcript_stats(stdout: str) -> dict:
    """Measurement conditions read off one stream-json transcript:
    {input_tokens, output_tokens, duration_ms, model, completed, result_error, init_observed,
    fleet_registered, registered_agents}.

    Shared by BOTH runners (EVAL-002): an artifact that cannot state what it measured is not a
    baseline, and two parsers would eventually disagree about one transcript — so this is the one
    read every benchmark writer uses. Token fields are None when the transcript carries no usage,
    never zero: a fabricated 0 reads as "this run was free" in any later cost comparison.
    """
    input_tokens = output_tokens = duration = model = None
    completed = False
    result_error = False
    init_observed = False
    registered_agents: set[str] = set()
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            init_observed = True
            agents = event.get("agents")
            if isinstance(agents, list):
                registered_agents.update(
                    strip_ns(name)
                    for name in agents
                    if isinstance(name, str) and name in NAMESPACED_FLEET_AGENTS
                )
        if event.get("type") == "result":
            usage = event.get("usage") or {}
            input_tokens = usage.get("input_tokens", input_tokens)
            output_tokens = usage.get("output_tokens", output_tokens)
            duration = event.get("duration_ms")
            # Only a non-error final result makes silence an observation. Reassign on every result
            # so the final structured result controls the classification.
            result_error = bool(event.get("is_error"))
            completed = not result_error
        # Record the model the session ACTUALLY ran on, read off the transcript rather than
        # assumed — routing behavior varies by tier, so an artifact that omits it cannot be validly
        # diffed against another. Deliberately independent of any REQUESTED model: reusing the
        # request for this once made the read conditional on --model being absent, so
        # `models_observed` echoed the requested alias for exactly the pinned runs the conditions
        # block exists to describe.
        if model is None:
            candidate = (
                (event.get("model") if isinstance(event, dict) else None)
                or _event_message_field(event, "model")
            )
            if isinstance(candidate, str) and candidate:
                model = candidate
    return {"input_tokens": input_tokens, "output_tokens": output_tokens,
            "duration_ms": duration, "model": model, "completed": completed,
            "result_error": result_error, "init_observed": init_observed,
            "fleet_registered": bool(registered_agents),
            "registered_agents": sorted(registered_agents)}


def run_once(prompt: str, plugin_dir: Path, timeout: int = 180, model: str | None = None,
             env: dict | None = None,
             required_agents: set[str] | frozenset[str] | None = None) -> dict:
    """One headless run in a fresh temp cwd. Returns {fired, tokens, duration_ms, model, error, note}.

    Ordinary runner trouble never raises: this drives a flaky, sometimes long-running subprocess,
    and a routing eval only needs the FIRST routing decision, not a completed session. Authentication
    failure and missing namespaced fleet registration are exceptions because either invalidates the
    whole batch rather than describing routing variance.
    A timeout is expected rather than exceptional — the transcript captured up to that point almost
    always already contains the Skill or Agent call we grade on. So: parse whatever stdout exists
    whether the run exits, times out, or errors, and set `error` only when the transcript cannot
    support a routing verdict (see the usability comment below). `note` keeps the trouble visible
    even for runs that were graded anyway, so an artifact can still say a rate came from cut or
    non-zero sessions.
    """
    stdout, stderr, note = "", "", None
    returncode: int | None = None
    try:
        with tempfile.TemporaryDirectory() as cwd:
            proc = subprocess.run(
                [
                    CLAUDE, "-p", prompt,
                    "--plugin-dir", str(plugin_dir),
                    "--output-format", "stream-json", "--verbose",
                    *(("--model", model) if model else ()),
                ],
                capture_output=True, encoding="utf-8", errors="replace", cwd=cwd, timeout=timeout,
                env=env,
            )
            stdout, stderr = proc.stdout or "", proc.stderr or ""
            returncode = proc.returncode
            if proc.returncode != 0:
                note = f"exit {proc.returncode}: {stderr[:150]}"
    except subprocess.TimeoutExpired as exc:
        stdout = decode_stream(exc.stdout)
        stderr = decode_stream(exc.stderr)
        returncode = 1
        note = f"timed out after {timeout}s (partial transcript graded)"
    except Exception as exc:  # a broken spawn must not crash the suite
        note = f"run failed: {exc}"

    if returncode is not None:
        raise_for_auth_failure(stdout, stderr)

    stats = transcript_stats(stdout)
    tokens = ((stats["input_tokens"] or 0) + (stats["output_tokens"] or 0)) or None
    duration, observed_model = stats["duration_ms"], stats["model"]
    session_completed = stats["completed"]

    if stats["result_error"]:
        result_note = "structured result reported an error"
        note = f"{note}; {result_note}" if note else result_note

    fired = sorted(components_fired(stdout))
    registered_agents = set(stats["registered_agents"])
    registered = bool(registered_agents)
    missing_agents = set(required_agents or ()) - registered_agents
    init_observed = stats["init_observed"]
    # Usability, not emptiness, decides whether a troubled run is a measurement. A session that
    # reached its non-error `result` event routed somewhere — possibly off the fleet entirely, which
    # is a real negative sample and a real positive miss — even if the CLI then exited non-zero;
    # discarding it
    # because no FLEET component fired drops exactly the wrong-route evidence, and dropping misses
    # from a positive's denominator can turn mostly-wrong routing into a PASS. A run cut by the
    # TIMEOUT is different: its silence is not a decision, only an unfinished one, so it still counts
    # as a measurement failure unless something already fired. The same narrow partial-evidence
    # rule applies to an error result: a component call observed before the error is real, but the
    # error result's silence can never green a negative.
    usable = bool(fired) or session_completed
    if (not registered or missing_agents) and (init_observed or usable):
        if missing_agents:
            detail = (
                "system/init omitted selected namespaced agent(s) "
                f"{sorted(missing_agents)}; --plugin-dir did not register every agent "
                "measured by this cluster"
            )
        else:
            detail = (
                "system/init did not register a known namespaced sde-agents agent; "
                "--plugin-dir did not load the fleet under test"
            )
        raise EvalRegistrationUnavailable(detail)
    # Exit status cannot turn silence into evidence: a clean process with no firing or completed
    # result is still an unusable sample and must not green a negative case.
    error = None if usable else (note or "no usable transcript")
    return {"fired": fired, "tokens": tokens, "duration_ms": duration, "model": observed_model,
            "error": error, "note": note}


def _load_clean_room():
    """Load scripts/eval_clean_room.py by path. A plain import spells differently in this file's
    two runtime contexts (script vs `from scripts import eval_routing`); path loading works in both,
    and it happens lazily so only `--clean-room` runs pay for or depend on it."""
    global _CLEAN_ROOM_MODULE
    if _CLEAN_ROOM_MODULE is not None:
        return _CLEAN_ROOM_MODULE
    path = Path(__file__).resolve().parent / "eval_clean_room.py"
    try:
        module = load_evaluator_module("eval_clean_room", path)
    except ImportError as exc:
        raise ImportError(
            f"cannot load the clean-room module from {path}; without it --clean-room cannot "
            "isolate the run, so refusing rather than measuring a dirty room"
        ) from exc
    # Every worker reuses this already-loaded module. Otherwise an A -> B -> A source edit during
    # a concurrent batch could make different sessions use different auth classifiers while the
    # endpoint provenance hashes still match.
    _CLEAN_ROOM_MODULE = module
    return _CLEAN_ROOM_MODULE


def raise_for_auth_failure(transcript: str, stderr: str = "") -> None:
    """Translate the shared clean-room classifier into a runner-stable batch exception."""
    clean_room = _load_clean_room()
    try:
        clean_room.raise_if_auth_failed(transcript, stderr)
    except clean_room.AuthUnavailable as exc:
        raise EvalAuthUnavailable(str(exc)) from exc


def auth_provider_mode(env: dict | None, *, clean_room_enabled: bool) -> dict:
    """Return non-secret auth/provider measurement metadata from the shared classifier."""
    clean_room = _load_clean_room()
    return clean_room.auth_provider_mode(env, clean_room=clean_room_enabled)


def cli_version() -> str | None:
    """The Claude Code version this measurement ran against, or None if it cannot be read."""
    if CLAUDE is None:
        return None
    try:
        proc = subprocess.run([CLAUDE, "--version"], capture_output=True, encoding="utf-8", timeout=30)
        return (proc.stdout or "").strip() or None
    except Exception:
        return None


def plugin_dir_label(plugin_dir: Path) -> str:
    """The plugin_dir as recorded in a benchmark's conditions.

    Recorded verbatim, the default (this repo, absolute) bakes the operator's local filesystem
    layout — a home-directory username on Windows — into a committed artifact, where it is identity
    noise rather than a measurement condition and makes identical runs from two machines diff. So a
    plugin_dir inside the repo is recorded repo-relative ("." for the repo itself). An external
    plugin_dir still changes the measured plugin identity through the separately recorded plugin hash,
    so the committed conditions use a stable placeholder instead of leaking workstation paths.
    """
    try:
        return str(plugin_dir.resolve().relative_to(REPO))
    except ValueError:
        return "<external-plugin-dir>"


def _validated_threshold(threshold: float) -> float:
    """Return a usable positive-case threshold or reject a false-green configuration."""
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < threshold <= 1
    ):
        raise ValueError(f"threshold must be > 0 and <= 1 (got {threshold!r})")
    return float(threshold)


def _scoring_targets(case: dict, members: set[str]) -> tuple[str, set[str]]:
    """Validate the polarity-specific contract and return the set used by the scorer."""
    case_id = case.get("id", "<missing id>") if isinstance(case, dict) else "<invalid case>"
    if not isinstance(case, dict):
        raise ValueError(f"case {case_id!r} must be an object")
    if not members or any(
        not isinstance(member, str) or not member.strip() for member in members
    ):
        raise ValueError("cluster members must be a non-empty set of component names")

    polarity = case.get("polarity")
    if polarity not in ("positive", "negative"):
        raise ValueError(
            f"case {case_id!r} polarity must be exactly 'positive' or 'negative' "
            f"(got {polarity!r})"
        )

    if polarity == "positive":
        field = "expect_fires"
        raw_targets = case.get(field)
    elif "expect_not_fires" in case:
        field = "expect_not_fires"
        raw_targets = case[field]
    else:
        # Omission is the documented broad negative: no member of the cluster may fire.
        return polarity, set(members)

    if not isinstance(raw_targets, list) or not raw_targets:
        raise ValueError(f"case {case_id!r} {field} must be a non-empty list")
    invalid = [
        target
        for target in raw_targets
        if not isinstance(target, str) or not target.strip() or target not in members
    ]
    if invalid:
        raise ValueError(
            f"case {case_id!r} {field} contains invalid cluster member(s): {invalid!r}"
        )
    return polarity, set(raw_targets)


def score_case(case: dict, runs: list[dict], members: set[str], threshold: float) -> dict:
    """Aggregate a case's runs into rates and a pass/fail verdict.

    Runs carrying an `error` are EXCLUDED from the rates. `run_once` sets that only when a session
    produced no usable transcript (a timeout that captured no routing decision, or a failed spawn),
    and its comment already said why such a run must not count -- "otherwise negatives would pass
    vacuously on empty transcripts" -- but nothing implemented the exclusion, so an invalid sample
    was scored as a confident "did not route". That mattered as soon as a slower model was pinned:
    sessions began timing out BEFORE their first tool call, and the resulting empty transcripts read
    as routing failures. A measurement failure and a routing failure are different facts.

    If every run of a case is invalid, the case is INCONCLUSIVE and never counts as passed -- an
    unmeasured case must not be reported as a result in either direction.
    """
    threshold = _validated_threshold(threshold)
    polarity, scoring_targets = _scoring_targets(case, members)
    valid = [r for r in runs if not r.get("error")]
    excluded = len(runs) - len(valid)
    n = len(valid)
    inconclusive = n == 0
    member_hits = [bool(set(r["fired"]) & members) for r in valid]
    fire_rate = sum(member_hits) / n if n else 0.0
    suffix = f" [{excluded} run(s) excluded: no usable transcript]" if excluded else ""

    if polarity == "positive":
        expected = scoring_targets
        correct = [bool(set(r["fired"]) & expected) for r in valid]
        correct_rate = sum(correct) / n if n else 0.0
        passed = (not inconclusive) and correct_rate >= threshold
        detail = f"expected {sorted(expected)} fired in {sum(correct)}/{n} runs{suffix}"
    else:
        # HONOR the case's own `expect_not_fires`. Every negative declares it, and this used to grade
        # against the whole member list regardless — so a DISAMBIGUATION case (X must not fire here,
        # but its sibling Y legitimately should) failed for its sibling doing the right thing. That
        # is the code ignoring what the data declares, and it produced a wrong verdict:
        # neg-resolved-not-incident forbids the mitigation skills on an already-resolved outage while
        # `postmortem` — a cluster member, and the correct destination — is expected to fire.
        # Defaults to every member, so a plain near-miss case behaves exactly as before.
        forbidden = scoring_targets
        hits = [bool(set(r["fired"]) & forbidden) for r in valid]
        correct_rate = sum(not h for h in hits) / n if n else 0.0  # rate of NOT firing
        # A negative fails if a forbidden component fires even once -- but an INCONCLUSIVE negative
        # must not pass, which is the vacuous pass the excluded-run comment above warns about.
        passed = (not inconclusive) and not any(hits)
        scope = "cluster" if forbidden == members else f"{sorted(forbidden)}"
        detail = f"{scope} fired in {sum(hits)}/{n} runs (want 0){suffix}"

    if inconclusive:
        detail = f"INCONCLUSIVE — no run produced a usable transcript ({excluded} attempted)"

    # What else fired — diagnostic, e.g. a negative correctly landing on backend-craft/sde-fullstack.
    other = sorted({c for r in valid for c in r["fired"]} - members)
    return {
        "id": case["id"],
        "polarity": polarity,
        "tags": case.get("tags", []),
        "passed": passed,
        "inconclusive": inconclusive,
        "runs_excluded": excluded,
        "cluster_fire_rate": round(fire_rate, 3),
        "correct_rate": round(correct_rate, 3),
        "detail": detail,
        "also_fired": other,
        # Per-run firing sets, so a surprising verdict can be audited from the artifact instead of
        # re-run to find out what happened. (Needed exactly once already: a negative reported
        # "fired 1/3" and the stored aggregate could not say which component it was.)
        "fired_per_run": [r["fired"] for r in runs],
        "errors": [r["error"] for r in runs if r["error"]],
        # Trouble on runs that were still GRADED (a non-zero exit whose session completed, a timeout
        # that captured a firing). Without this the artifact cannot say a rate came from cut or
        # failed sessions, only that no run was excluded.
        "notes": [r["note"] for r in runs if r.get("note") and not r["error"]],
    }


def main(argv: list[str] | None = None) -> int:
    if _EXECUTING_EVALUATOR_SOURCE is None:
        # The ordinary Python loader does not expose the exact source buffer it compiled. Delegate
        # before any eval input is read or session is started, so all grading and provenance run
        # from one checked buffer registered by ``load_current_evaluator``.
        return load_current_evaluator().main(argv)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cluster", nargs="?", default=str(REPO / "evals" / "routing" / "prompt-tooling.json"),
                        help="path to a cluster JSON file")
    parser.add_argument("--runs", type=int, default=3, help="runs per case (default 3)")
    parser.add_argument("--plugin-dir", type=Path, default=REPO, help="plugin to load (default this repo)")
    parser.add_argument("--case", default="*", help="glob over case ids (default all)")
    parser.add_argument("--limit", type=int, default=0, help="cap number of cases (0 = all) — for cheap demo runs")
    parser.add_argument("--concurrency", type=int, default=4, help="parallel runs (default 4)")
    parser.add_argument("--timeout", type=int, default=180,
                        help="per-run seconds before the session is cut and its partial transcript graded (default 180)")
    parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="positive passes at this fire rate; must be > 0 and <= 1 (default 0.5)",
    )
    parser.add_argument("--output-dir", type=Path, default=None, help="write benchmark.json here")
    # Without this the subprocesses take whatever model the CLI defaults to, which is NOT the model
    # of the session that launched them: a `/model` change in an interactive session does not
    # propagate to `claude -p` children. That silently invalidated a comparison here — two runs
    # believed to differ by model tier were both sonnet, which the new conditions block exposed.
    # Pin it explicitly for any run whose numbers are meant to be compared to another's.
    parser.add_argument("--model", default=None,
                        help="model for the eval sessions (alias or id). Default: the CLI's own "
                             "default, which is NOT inherited from the launching session")
    parser.add_argument("--clean-room", action="store_true",
                        help="relocate CLAUDE_CONFIG_DIR to a temp dir holding only credentials for "
                             "every session, so personal components and a junction-deployed fleet "
                             "cannot enter the routing surface (see scripts/eval_clean_room.py). "
                             "Recorded in conditions: artifacts differing on it are not comparable")
    args = parser.parse_args(argv)

    if args.runs < 1:
        print(f"--runs must be >= 1 (got {args.runs}); 0 would make every negative pass vacuously", file=sys.stderr)
        return 2
    try:
        args.threshold = _validated_threshold(args.threshold)
    except ValueError as exc:
        print(f"--{exc}", file=sys.stderr)
        return 2
    if CLAUDE is None:
        print("claude CLI not found on PATH", file=sys.stderr)
        return 2

    cluster_path = Path(args.cluster)
    try:
        spec = json.loads(_read_regular_file(cluster_path).decode("utf-8"))
    except (ProvenanceError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"cluster error: {exc}", file=sys.stderr)
        return 2
    if not isinstance(spec, dict):
        print("cluster error: top-level JSON value must be an object", file=sys.stderr)
        return 2
    if not isinstance(spec.get("cluster"), str) or not spec["cluster"].strip():
        print("cluster error: 'cluster' must be a non-empty string", file=sys.stderr)
        return 2
    try:
        raw_members = validated_members(spec.get("members"))
    except ProvenanceError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    raw_cases = spec.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        print("cluster error: 'cases' must be a non-empty list", file=sys.stderr)
        return 2

    members = set(raw_members)
    cases = []
    for index, case in enumerate(raw_cases, start=1):
        if not isinstance(case, dict):
            print(f"cluster error: case #{index} must be an object", file=sys.stderr)
            return 2
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            print(f"cluster error: case #{index} must have a non-empty 'id'", file=sys.stderr)
            return 2
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            print(f"cluster error: case {case_id!r} must have a non-empty 'prompt'", file=sys.stderr)
            return 2
        try:
            _scoring_targets(case, members)
        except ValueError as exc:
            print(f"cluster error: {exc}", file=sys.stderr)
            return 2
        if fnmatch.fnmatch(case_id, args.case):
            cases.append(case)
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        print("no cases matched", file=sys.stderr)
        return 2
    required_agents = members & FLEET_AGENTS

    provenance = None
    if args.output_dir:
        try:
            provenance = benchmark_provenance(
                [cluster_path], cases, args.case, args.plugin_dir, args.limit,
                evaluator_paths=routing_evaluator_paths(), members=raw_members,
            )
        except ProvenanceError as exc:
            print(f"provenance error: {exc}", file=sys.stderr)
            return 2

    # Flatten to (case, run_index) work items so all runs across all cases share the pool.
    work = [(c, i) for c in cases for i in range(args.runs)]
    print(f"cluster '{spec['cluster']}': {len(cases)} cases x {args.runs} runs = {len(work)} sessions "
          f"(members: {sorted(members)}, concurrency {args.concurrency})\n")

    results_by_case: dict[str, list[tuple[int, dict]]] = {c["id"]: [] for c in cases}
    # One room for the whole batch: the sessions only read the relocated config, and per-session
    # rooms would copy credentials once per run for no added isolation. The room must outlive the
    # pool, so the ExitStack closes after the last future resolves.
    auth_mode = None
    with contextlib.ExitStack() as stack:
        try:
            execution_plugin_dir, execution_plugin_identity = stack.enter_context(
                frozen_plugin(args.plugin_dir)
            )
        except ProvenanceError as exc:
            print(f"provenance error: {exc}", file=sys.stderr)
            return 2
        if provenance is not None and (
            provenance["plugin"]["sha256"] != execution_plugin_identity["sha256"]
        ):
            print(
                "provenance error: plugin content changed before its execution snapshot was "
                "created; benchmark.json was not written",
                file=sys.stderr,
            )
            return 2
        session_env = None
        if args.clean_room:
            clean_room = _load_clean_room()
            try:
                session_env = stack.enter_context(clean_room.clean_env())
            except clean_room.AuthUnavailable as exc:
                # A refusal here is the module doing its job: an unauthenticated batch would
                # produce 24 vacuously-passing negatives, not 24 measurements.
                print(f"clean room refused to run: {exc}", file=sys.stderr)
                return 2
        auth_mode = auth_provider_mode(
            session_env, clean_room_enabled=bool(args.clean_room)
        )
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency)
        futures = {
            pool.submit(run_once, c["prompt"], execution_plugin_dir, args.timeout, args.model,
                        session_env, required_agents): (c["id"], i)
            for c, i in work
        }
        done = 0
        fatal_measurement_failure: EvalAuthUnavailable | EvalRegistrationUnavailable | None = None
        try:
            for future in concurrent.futures.as_completed(futures):
                case_id, run_index = futures[future]
                try:
                    result = future.result()
                except (EvalAuthUnavailable, EvalRegistrationUnavailable) as exc:
                    fatal_measurement_failure = exc
                    for pending in futures:
                        pending.cancel()
                    break
                results_by_case[case_id].append((run_index, result))
                done += 1
                print(f"  [{done}/{len(work)}] runs complete", end="\r")
        finally:
            # subprocess.run cannot interrupt work already started; pending sessions can still be
            # cancelled, limiting the outage to at most the configured concurrency.
            pool.shutdown(wait=True, cancel_futures=fatal_measurement_failure is not None)
        try:
            verify_frozen_plugin(execution_plugin_dir, execution_plugin_identity)
        except ProvenanceError as exc:
            print(f"provenance error after sessions: {exc}", file=sys.stderr)
            return 2
        if fatal_measurement_failure is not None:
            print(
                f"\neval aborted: {fatal_measurement_failure}; benchmark.json was not written",
                file=sys.stderr,
            )
            return 2
    print()

    # Sort back into submission order. Sessions finish in whatever order they finish, and the
    # per-run arrays in the artifact would otherwise permute between two identical measurements —
    # the documented baseline workflow diffs the whole `.cases` array, so that noise reads as a
    # change and can bury a real one.
    runs_by_case = {cid: [r for _, r in sorted(pairs, key=lambda p: p[0])]
                    for cid, pairs in results_by_case.items()}

    scored = [score_case(c, runs_by_case[c["id"]], members, args.threshold) for c in cases]

    print("\n{:<28} {:<9} {:>6} {:<40}".format("case", "verdict", "rate", "detail"))
    print("-" * 90)
    for s in scored:
        rate = s["correct_rate"]
        mark = "INCONC" if s.get("inconclusive") else ("PASS" if s["passed"] else "FAIL")
        also = f"  [also fired: {', '.join(s['also_fired'])}]" if s["also_fired"] else ""
        print("{:<28} {:<9} {:>6.0%} {}{}".format(s["id"], mark, rate, s["detail"], also))
        for err in s["errors"]:
            print(f"    ! run error: {err}")
        for note in s.get("notes", []):
            print(f"    ~ graded despite: {note}")

    passed = sum(s["passed"] for s in scored)
    pos = [s for s in scored if s["polarity"] == "positive"]
    neg = [s for s in scored if s["polarity"] == "negative"]
    inconc = [s for s in scored if s.get("inconclusive")]
    print("-" * 90)
    print(f"{passed}/{len(scored)} passed  "
          f"(positives: {sum(s['passed'] for s in pos)}/{len(pos)} routed correctly, "
          f"negatives: {sum(s['passed'] for s in neg)}/{len(neg)} correctly did NOT fire)")
    if inconc:
        # Loud, because an unmeasured case silently counted as a failure is how a measurement
        # problem gets mistaken for a routing problem — which happened here with a slower model.
        print(f"! {len(inconc)} case(s) INCONCLUSIVE (no usable transcript): "
              f"{', '.join(s['id'] for s in inconc)}")
        print("  Raise --timeout or re-run those; they are not evidence in either direction.")
    excluded_total = sum(s.get("runs_excluded", 0) for s in scored)
    if excluded_total:
        print(f"! {excluded_total} individual run(s) excluded from rates for the same reason.")

    # The conditions the measurement was taken under. A benchmark without them is not a baseline:
    # routing behavior varies by model tier, so diffing two runs that silently used different models
    # reads a model difference as a routing regression. `models_observed` is read off the transcripts
    # (what actually ran), and more than one entry means the run itself was not uniform.
    models = sorted({r["model"] for runs in runs_by_case.values() for r in runs if r.get("model")})
    conditions = {
        "cli_version": cli_version(),
        "model_requested": args.model,      # None means "whatever the CLI defaulted to"
        "models_observed": models,          # what actually ran, per the transcripts
        "plugin_dir": plugin_dir_label(args.plugin_dir),
        "threshold": args.threshold,
        # The timeout is a measurement decision, not a convenience: a shorter one excludes more runs
        # and therefore moves every rate in the artifact. Two benchmarks taken at different timeouts
        # are not comparable, and without this recorded they look identical in their conditions.
        "timeout_s": args.timeout,
        "concurrency": args.concurrency,
        "auth_provider": auth_mode,
        # Whether the sessions saw only this plugin (clean room) or the operator's whole
        # configuration surface. Two artifacts differing here measured different competitions
        # for every routing decision — diffing them reads contamination as a description change.
        "clean_room": bool(args.clean_room),
    }
    if len(models) > 1:
        print(f"\n! WARNING: runs did not use one model ({', '.join(models)}) — this benchmark mixes "
              f"conditions and should not be diffed as a single baseline")

    benchmark = {
        "cluster": spec["cluster"],
        "runs_per_case": args.runs,
        "members": sorted(members),
        "conditions": conditions,
        "provenance": provenance,
        "summary": {"passed": passed, "total": len(scored)},
        "cases": scored,
    }
    if args.output_dir:
        try:
            latest_spec = json.loads(_read_regular_file(cluster_path).decode("utf-8"))
            latest_cases = [
                case for case in latest_spec["cases"] if fnmatch.fnmatch(case["id"], args.case)
            ]
            if args.limit:
                latest_cases = latest_cases[:args.limit]
            latest_members = validated_members(latest_spec.get("members"))
            # The targets need the same revalidation as the membership, and for the same reason:
            # `_graded_definition` canonicalizes them with `set()`, so an unhashable target in a
            # cluster edited mid-batch raises TypeError straight past the `except ProvenanceError`
            # below. The membership half of this was fixed one round before the target half, which
            # is exactly how the resolver's copy of the rule went wrong too (PR #145 review).
            for latest_case in latest_cases:
                try:
                    _scoring_targets(latest_case, set(latest_members))
                except ValueError as exc:
                    raise ProvenanceError(f"cluster error after sessions: {exc}") from exc
            latest_provenance = benchmark_provenance(
                [cluster_path], latest_cases, args.case, args.plugin_dir, args.limit,
                evaluator_paths=routing_evaluator_paths(),
                members=latest_members,
            )
        except ProvenanceError as exc:
            print(f"provenance error after sessions: {exc}", file=sys.stderr)
            return 2
        if not _content_provenance_matches(provenance, latest_provenance):
            print(
                "provenance error: eval source, selected cases, evaluator, or plugin content "
                "changed while the batch was running; benchmark.json was not written",
                file=sys.stderr,
            )
            return 2
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "benchmark.json").write_text(json.dumps(benchmark, indent=2), encoding="utf-8")
        print(f"\nwrote {args.output_dir / 'benchmark.json'}")

    # Distinct exits, because the two non-zero outcomes ask for different responses: 1 is a routing
    # verdict to investigate, 3 is a measurement that did not happen and wants --timeout and a
    # re-run. Collapsing them sent a caller auditing descriptions over a clock problem. A real
    # failure outranks an inconclusive: it is the actionable one. (2 stays usage errors.)
    if passed != len(scored) - len(inconc):
        return 1
    return 3 if inconc else 0


def _main_entry() -> int:
    """Run the command from one captured source buffer, including the main runner itself."""
    if _EXECUTING_EVALUATOR_SOURCE is None:
        return load_current_evaluator().main()
    return main()


if __name__ == "__main__":
    raise SystemExit(_main_entry())
