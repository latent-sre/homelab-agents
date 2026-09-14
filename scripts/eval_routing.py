#!/usr/bin/env python3
"""Routing evals: `claude plugin eval` runs them, the fleet grades them.

This replaces a 1,450-line runner that also drove the sessions. The platform now owns isolation,
per-case runs, concurrency, cost ceilings, timeouts, the JSON result document and the HTML report,
and it owns them better than a fleet-local copy could. What stays here is everything the platform
does not do:

**The verdict.** Measured, not assumed
(`docs/archive/2026-09/native-grader-errored-spawn-2026-09-14.md`): a native `tool_used` grader
counts a call whose input matches its regex whether or not the spawn SUCCEEDED, so on a positive
case a routing regression can hide behind a dispatch that never landed. And a positive passes when
ANY of its expected destinations fires -- a disjunction that spans the Agent and Skill tools in
every multi-target positive this repository has, which no combination of `tool_used` graders can
state. So `fleet.routing` reads the harness's own traces and applies the retiring runner's
semantics, proved equal to it by differential on 12,400 transcripts and 8,004 grading combinations.

**The routing competition, observed rather than requested.** A first reading of an eval child
session's `init` event concluded that personal components reach the session; a controlled
comparison the same day refuted it. The surface is byte-identical with and without
`--clean-room` -- the harness sets its own config directory and overrides the variable that flag
moves -- and the operator's own config-dir components appear in neither. What the child does see
is sixteen of the CLI's BUNDLED skills (`code-review`, `debug`, `verify`, ...), which no config
relocation removes. So every benchmark records `components_observed`, read off each session's own
`init` event, and the flag is recorded as `clean_room_requested`, which is all it is.

**Provenance and conditions.** `fleet.provenance` identifies the plugin bytes, the case selection
and the evaluator; the conditions block records what the rates are comparable to. Nothing in the
native result document says either.

The native graders are kept as a cheap tripwire and deliberately cannot cry wolf: see
`fleet/nativecases.py`. Their score is not read here.
"""

from __future__ import annotations

import argparse
import contextlib
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)  # `import fleet` when run as `python3 scripts/<name>.py`

from fleet import fs, nativecases, provenance, routing, stream  # noqa: E402

try:  # the auth/clean-room classifier, imported at module level so main() and _run_batch() share it
    from scripts import eval_clean_room  # noqa: E402
except ImportError:  # running as a bare script rather than a package
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import eval_clean_room  # type: ignore[no-redef]  # noqa: E402

REPO = Path(_REPO_ROOT)
CLAUDE = shutil.which("claude")

DEFAULT_PLUGIN_NAMESPACE = "sde-agents"


def plugin_roster(plugin_dir: Path) -> tuple[frozenset[str], frozenset[str], str]:
    """The agents, skills and namespace of the plugin BEING EVALUATED.

    Read from `plugin_dir`, never from this checkout. `--plugin-dir` can name another revision or
    another plugin entirely, and a roster fixed at import graded those runs against the wrong
    component list and the wrong namespace -- producing a confident verdict about a plugin that
    was never measured. Falls back to this repository's own namespace when the target has no
    readable manifest name, because a missing name is not evidence of a different one.
    """
    agents = frozenset(p.stem for p in (plugin_dir / "agents").glob("*.md"))
    skills_dir = plugin_dir / "skills"
    skills = frozenset(
        p.name for p in skills_dir.iterdir() if p.is_dir()
    ) if skills_dir.is_dir() else frozenset()
    try:
        manifest = json.loads(
            (plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        # A manifest that parses but is not an object (`[]`, `"x"`, `null`) reached `.get` and
        # raised AttributeError past every handler -- a traceback before any session launched,
        # on the one path this helper documents as falling back rather than failing.
        name = manifest.get("name") if isinstance(manifest, dict) else None
        namespace = str(name or "").strip() or DEFAULT_PLUGIN_NAMESPACE
    except (OSError, json.JSONDecodeError):
        namespace = DEFAULT_PLUGIN_NAMESPACE
    return agents, skills, namespace

# The code whose bytes decide a verdict, named for `evaluator_identity`. Two benchmarks produced by
# different grading code are not comparable even when every other condition matches, and this is
# the only place that says which files those are.
EVALUATOR_PATHS = (
    REPO / "scripts" / "eval_routing.py",
    REPO / "fleet" / "routing.py",
    REPO / "fleet" / "nativecases.py",
    REPO / "fleet" / "stream.py",
    # The emitters `nativecases` generates prompts and grader regexes with. A change here alters
    # the tool permissions a session runs under or the pattern a grader matches, so leaving it out
    # made two runs measuring different generated inputs carry the same evaluator hash.
    REPO / "fleet" / "frontmatter.py",
    # Decides the recorded auth conditions AND whether a batch is accepted at all, so a change
    # here changes which runs become a benchmark. The retiring runner hashed it for that reason.
    REPO / "scripts" / "eval_clean_room.py",
    # The identity machinery itself, and the path primitives it and the generator validate with.
    # A change to either moves selection or plugin identity, or what paths are accepted, while
    # every other listed byte stays the same -- captures from different logic would look reusable.
    REPO / "fleet" / "provenance.py",
    REPO / "fleet" / "fs.py",
)


def cli_version() -> str | None:
    """The Claude Code version this measurement ran against, or None if it cannot be read."""
    if CLAUDE is None:
        return None
    try:
        result = subprocess.run(
            [CLAUDE, "--version"], capture_output=True, encoding="utf-8", timeout=30
        )
        return (result.stdout or "").strip() or None
    except Exception:
        return None


def plugin_dir_label(plugin_dir: Path) -> str:
    """The plugin_dir as recorded in a benchmark's conditions.

    Recorded verbatim, the default bakes the operator's filesystem layout into a committed
    artifact, where it is identity noise that makes identical runs from two machines diff. An
    external plugin_dir still moves the separately recorded plugin hash.
    """
    try:
        return str(plugin_dir.resolve().relative_to(REPO))
    except ValueError:
        return "<external-plugin-dir>"


def write_cases(eval_dir: Path, files: dict[str, str], spec: dict) -> None:
    """Write the generated case tree, replacing whatever was there.

    Replacing rather than merging is the point: a case removed from the cluster must disappear from
    the measurement, and a leftover directory from a previous cluster would otherwise be run and
    scored as if the cluster still declared it.
    """
    # This REMOVES a directory tree, so the path it was handed is checked before anything is
    # deleted. A `..` anywhere in it means the caller assembled it from a name that climbed out of
    # the intended root -- the traversal is already done by the time it arrives here, so refusing
    # the un-normalised path is the last point at which it can be caught. (Checking `eval_dir`
    # against its own parent, which a first version did, is vacuous: every path is under its own
    # parent.) The caller separately validates the cluster name as a single path segment.
    if ".." in eval_dir.parts:
        raise ValueError(
            f"generated eval directory must be a normalised path, not one that climbs out of its "
            f"root: {eval_dir}"
        )
    targets = {
        relative: fs.contained_path(eval_dir, relative, what="generated case file")
        for relative in files
    }
    if eval_dir.exists():
        shutil.rmtree(eval_dir)
    for relative, content in files.items():
        target = targets[relative]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (eval_dir / "GENERATED.json").write_text(nativecases.manifest(spec, files), encoding="utf-8")


def native_command(
    plugin_dir: Path, eval_dir_name: str, result_path: Path, args: argparse.Namespace
) -> list[str]:
    """The native invocation, with the flags this measurement depends on rather than defaults.

    `--keep-temp` is load-bearing and not a debugging convenience: without it the run's trace is
    deleted before the result document that names it can be read, and the fleet-side verdict has
    nothing to grade. `--threshold 0` hands the exit code to this script -- the native score comes
    from tripwire graders that are not the verdict, so letting it decide the exit would report a
    routing result this measurement never computed. `--ablation none` keeps the run to the
    with-plugin arm; a no-plugin baseline cannot route to a fleet component by construction.
    """
    return [
        CLAUDE, "plugin", "eval", str(plugin_dir),
        "--eval-dir", eval_dir_name,
        "--runs", str(args.runs),
        "--concurrency", str(args.concurrency),
        "--threshold", "0",
        "--ablation", "none",
        "--no-publish",
        "--trust-plugin",
        "--keep-temp",
        "--json", str(result_path),
        *(("--model", args.model) if args.model else ()),
        # `is not None`, not truthiness: `--max-cost-usd 0` is falsey, and silently dropping it
        # launched an UNCAPPED paid run for a caller asking for a zero budget.
        *(
            ("--max-cost-usd", str(args.max_cost_usd))
            if args.max_cost_usd is not None
            else ()
        ),
    ]


class MalformedNativeResult(Exception):
    """The harness wrote valid JSON in a shape this cannot read."""


class RegistrationIncomplete(RuntimeError):
    """A session did not register a component the selected cluster is graded against.

    Aborts the batch rather than excluding the run, which is the contract `evals/README.md`
    records as retained from the retired runner: a partially or intermittently loaded plugin
    means the whole measurement ran against an incomplete competition, and excluding only the
    affected runs lets the remaining ones pass every case and write a benchmark that reads clean.
    """


def _run_records(result: object) -> dict[str, list[dict]]:
    """Per-case run records from the native result document, keyed by case name.

    Every level is type-checked rather than assumed. The document is written by an early-access
    CLI whose schema can move under a version bump, and a partial failure can emit a structurally
    incomplete one -- and this runs AFTER the sessions are paid for, so a shape surprise here must
    become the documented measurement-failure exit rather than an AttributeError traceback.
    """
    if not isinstance(result, dict):
        raise MalformedNativeResult(f"result document is {type(result).__name__}, not an object")
    cases = result.get("cases")
    if not isinstance(cases, list):
        raise MalformedNativeResult(f"'cases' is {type(cases).__name__}, not a list")
    records: dict[str, list[dict]] = {}
    for case in cases:
        if not isinstance(case, dict):
            raise MalformedNativeResult(f"a case entry is {type(case).__name__}, not an object")
        arms = case.get("arms")
        if not isinstance(arms, dict):
            raise MalformedNativeResult(f"case {case.get('name')!r} 'arms' is not an object")
        # Default only an ABSENT field. `or []` also swallowed `{}`, `""`, `false` and `null`,
        # so a malformed schema read as zero launched runs, got padded like an ordinary early
        # stop, and wrote an INCONCLUSIVE benchmark instead of failing as unreadable.
        runs = arms.get("with", [])
        if not isinstance(runs, list) or any(not isinstance(run, dict) for run in runs):
            raise MalformedNativeResult(
                f"case {case.get('name')!r} run records are not a list of objects"
            )
        records[str(case.get("name"))] = list(runs)
    return records


def fired_per_run(
    runs: list[dict],
    roster: frozenset[str],
    auth_check: Callable[[str, str], None] = lambda _text, _stderr: None,
    namespace: str = DEFAULT_PLUGIN_NAMESPACE,
) -> tuple[list[frozenset[str] | None], list[str], list[str], list[dict]]:
    """Each run's firing set, or None when the run produced no usable transcript.

    USABILITY, not the harness's `error` field, decides which is which -- and the difference is
    not academic. The harness reports a run that hit its turn or time limit as an error, but that
    transcript very often already contains the routing decision; treating every error as an
    invalid run made a first end-to-end measurement report INCONCLUSIVE on a case whose trace was
    perfectly readable. The rule the retiring runner arrived at, kept exactly:

    a run counts as a measurement when something fired, or when the session reached a final
    result that was not an error. Anything else is silence that decided nothing, and scoring it as
    "did not route" greens negatives vacuously and drops misses out of a positive's denominator.

    A trace that cannot be read at all is an invalid run whatever the harness said about it, since
    there is nothing left to grade. Reasons are carried back so the artifact can say why a rate
    rests on fewer runs than were attempted, and `models` reports what actually ran.
    """
    fired: list[frozenset[str] | None] = []
    notes: list[str] = []
    models: list[str] = []
    surfaces: list[dict[str, list[str]]] = []
    for index, run in enumerate(runs):
        label = f"run {index + 1}"
        try:
            text = Path(str(run.get("tracePath"))).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            # Classified HERE, on the one path that has no transcript to classify from: an
            # authentication failure can prevent the trace from being written at all, and the
            # `continue` below would otherwise skip the classifier entirely, letting earlier
            # successful runs carry the batch to exit 0 during an outage. Running this check
            # before the read instead made it fire on runs whose trace exists: the classifier
            # keeps a completed non-error result as a measurement, and it cannot see that
            # exception in an empty transcript, so one readable, completed run whose harness
            # error string merely mentions authentication aborted the whole paid batch.
            auth_check("", str(run.get("error") or ""))
            fired.append(None)
            # An empty surface keeps `surfaces` index-aligned with `fired`; the registration check
            # in `_scored` zips them, and a short list would silently shift every later run.
            surfaces.append({"agents": [], "skills": []})
            notes.append(f"{label}: trace unreadable ({exc}); harness said {run.get('error')!r}")
            continue
        # An authentication failure part-way through a batch invalidates the WHOLE measurement,
        # not just the runs it touched: excluding them silently lets the earlier valid runs pass
        # every case and write a benchmark at exit 0. The retiring runner aborted for this, and
        # `eval_clean_room` still owns the classifier -- it keys off the run's own stream, and
        # deliberately keeps a completed non-error result as a measurement.
        auth_check(text, str(run.get("error") or ""))
        model = stream.observed_model(text)
        if not model:
            # Model identity is a required comparability condition, so a run that cannot say which
            # model produced it is not a measurement -- recording its rate while leaving
            # `models_observed` silently short is how two incomparable artifacts look alike.
            fired.append(None)
            surfaces.append({"agents": [], "skills": []})
            notes.append(f"{label}: no model observed in the transcript")
            continue
        models.append(model)
        surfaces.append(stream.registered_components(text))
        found = frozenset(routing.fired_components(text, roster, namespace))
        if found or stream.session_completed(text):
            fired.append(found)
            if run.get("error"):
                # Graded anyway, but the trouble stays visible: a rate that came from cut
                # sessions is not the same measurement as one that came from clean ones.
                notes.append(f"{label}: graded despite {run['error']!r}")
            continue
        fired.append(None)
        notes.append(f"{label}: no usable transcript ({run.get('error') or 'no final result'})")
    return fired, notes, models, surfaces


def _scored(
    case: dict,
    members: list[str],
    runs: list[dict],
    roster: frozenset[str],
    threshold: float,
    auth_check: Callable[[str, str], None] = lambda _text, _stderr: None,
    agents: frozenset[str] = frozenset(),
    namespace: str = DEFAULT_PLUGIN_NAMESPACE,
) -> dict:
    fired, notes, models, surfaces = fired_per_run(runs, roster, auth_check, namespace)

    # A run whose session never REGISTERED the components this case is graded against cannot
    # evidence that they did not fire: they could not have. Without this, a stale or external
    # `--plugin-dir` that omits a component turned every negative naming it into a vacuous pass --
    # the retiring runner refused such a batch outright, and dropping that guard was a false-green
    # generator, not a simplification.
    _polarity, targets = routing.scoring_targets(case, members)
    # EVERY member of the selected cluster, not just this case's graded targets -- and read from
    # the cluster definition, never from the plugin under test. Intersecting with that plugin's
    # own agent roster dropped precisely the member a stale `--plugin-dir` had deleted, so the
    # guard could not fire for the one case it exists for: a narrowed negative grading a
    # still-loaded skill would pass against an incomplete competition. A member is required
    # whether it is an agent or a skill; the distinction was only ever a way to classify, and
    # classifying from the tested plugin is what made the check self-defeating. Verified against
    # the 303-run anchor: requiring all members invalidates zero runs there.
    required = targets | set(members)
    for index, surface in enumerate(surfaces):
        if fired[index] is None:
            continue
        # Qualified, not bare: `other-plugin:root-cause` must not satisfy a requirement for this
        # plugin's `root-cause`.
        registered = {*surface.get("agents", []), *surface.get("skills", [])}
        missing = {
            name for name in required if f"{namespace}:{name}" not in registered
        }
        if missing:
            # Abort, do not exclude. Excluding left the batch able to write a passing benchmark
            # from the runs that happened to load the whole fleet, and -- when every run was
            # excluded -- an INCONCLUSIVE artifact at exit 3 rather than no artifact at all.
            raise RegistrationIncomplete(
                f"case {case['id']!r} run {index + 1}: graded component(s) {sorted(missing)} "
                "were not registered in this session, so the batch ran against an incomplete "
                "routing competition"
            )
    verdict = routing.grade_case(case, members, fired)
    member_set = set(members)
    valid = [f for f in fired if f is not None]
    cluster_hits = sum(1 for f in valid if f & member_set)
    if verdict.inconclusive:
        detail = (
            "INCONCLUSIVE — no run produced a usable transcript "
            f"({verdict.invalid_runs} attempted)"
        )
    elif verdict.polarity == "positive":
        detail = (
            f"expected {sorted(verdict.targets)} fired in "
            f"{verdict.hits}/{verdict.valid_runs} runs"
        )
    else:
        broad = verdict.targets == frozenset(members)
        scope = "cluster" if broad else f"{sorted(verdict.targets)}"
        detail = f"{scope} fired in {verdict.hits}/{verdict.valid_runs} runs (want 0)"
    if verdict.invalid_runs and not verdict.inconclusive:
        detail += f" [{verdict.invalid_runs} run(s) excluded: no usable transcript]"
    rate = verdict.rate
    return {
        "id": case["id"],
        "polarity": verdict.polarity,
        "tags": case.get("tags", []),
        "passed": verdict.passed(threshold),
        "inconclusive": verdict.inconclusive,
        "runs_excluded": verdict.invalid_runs,
        "cluster_fire_rate": (
            round(cluster_hits / verdict.valid_runs, 3) if verdict.valid_runs else 0.0
        ),
        # For a negative this is the rate of NOT firing, matching the retiring runner's artifact.
        "correct_rate": round(
            (rate if verdict.polarity == "positive" else 1 - rate) if rate is not None else 0.0, 3
        ),
        "detail": detail,
        # What else fired -- diagnostic, e.g. a negative correctly landing outside the cluster.
        "also_fired": sorted({c for f in valid for c in f} - member_set),
        # Per-run firing sets, so a surprising verdict can be audited from the artifact instead of
        # re-run to find out what happened.
        "fired_per_run": [sorted(f) if f is not None else None for f in fired],
        "notes": notes,
        "models_observed": sorted(set(models)),
        # How many runs produced a usable transcript. Recorded because `main` later OVERRIDES
        # `inconclusive` for a case the harness stopped short of, and the uniformity filter must
        # not read a flag that has been repurposed: such a case really did observe a surface, and
        # dropping it from the uniformity check while the batch union still counted it let a
        # batch whose competitions differed report `components_uniform: true`.
        "runs_observed": sum(1 for f in fired if f is not None),
        # Both this union and `components_uniform` below read the SAME valid runs. Including an
        # excluded run here let a case report union X u Y while flagging itself uniform, and the
        # batch check then accepted a second case whose valid runs really saw X u Y.
        "components_observed": {
            key: sorted({
                name
                for s, f in zip(surfaces, fired, strict=True) if f is not None
                for name in s.get(key, [])
            })
            for key in ("agents", "skills")
        },
        # Whether every run that produced a surface saw the SAME one. The union above cannot tell
        # "all runs saw this" from "one run saw an extra component", and only the first supports
        # the uniform-competition claim the artifact is stored to make.
        "components_uniform": len({
            (tuple(s.get("agents", [])), tuple(s.get("skills", [])))
            for s, f in zip(surfaces, fired, strict=True) if f is not None
        }) <= 1,
    }


def _batch_components_uniform(scored: list[dict]) -> bool:
    """Whether every valid run in the WHOLE batch saw the same routing competition.

    A per-case flag is true when every run of case A saw surface X and every run of case B saw a
    different surface Y, which is precisely the changing competition this is stored to rule out.
    """
    # `runs_observed`, NOT `inconclusive`. I declined this finding once on the grounds that
    # `CaseVerdict.inconclusive` is `valid_runs == 0` and therefore agreed with the surfaces --
    # true of the verdict, and false of the artifact, because `main` later sets `inconclusive` on
    # a case the harness stopped short of even though its launched runs observed a real surface.
    # That case then vanished from this check while the batch-level union still counted it, so a
    # batch measured against two different competitions could report `components_uniform: true`.
    # `runs_observed` is written by `_scored` and never repurposed, which is the whole point.
    surfaces = {
        (tuple(e["components_observed"]["agents"]), tuple(e["components_observed"]["skills"]))
        for e in scored
        # Subscript, not `.get(..., 0)`: a default would silently drop an entry that lacks the
        # field, and dropping every entry reports a uniform batch over no surfaces at all.
        if e["runs_observed"] > 0
    }
    return len(surfaces) <= 1 and all(e["components_uniform"] for e in scored)


def _recovered_trace_records(document: object) -> dict[str, list[dict]]:
    """Trace paths salvaged from a result document too malformed to read as records.

    Only for the unreadable-shape exit, where `_run_records` refused before producing anything to
    clean up. Walks whatever structure survived for `tracePath` strings; what it cannot recognise
    is simply not recovered. Safe to point at arbitrary strings because the remover deletes only
    directories the harness itself named (`claude-eval-`), never a path this walk invents.
    """
    found: list[dict] = []
    pending: list[object] = [document]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            trace = node.get("tracePath")
            if isinstance(trace, str) and trace:
                found.append({"tracePath": trace})
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    return {"<unreadable result>": found}


def _remove_kept_temp_dirs(runs_by_case: dict[str, list[dict]]) -> None:
    """`--keep-temp` leaves one directory per run, and the harness warns it could not seal them.

    They hold a copy of the plugin under test and whatever the sessions wrote, so leaving them is
    both a disk problem and a disclosure. Removal is best effort and never fails a measurement that
    already happened: the trace has been read by the time this runs.
    """
    roots = {
        Path(str(run.get("tracePath"))).parent.parent
        for runs in runs_by_case.values()
        for run in runs
        if run.get("tracePath")
    }
    failures: list[str] = []

    def _record(directory: Path):
        # Bound per directory rather than closing over the loop variable, which would report
        # whichever root the loop happened to end on.
        return lambda *_args: failures.append(str(directory))

    # Every spelling of the trusted temp root, not just this process's canonical one. On macOS
    # `fleet.provenance` canonicalizes Python's cached root to `/private/var/...` while the
    # spawned harness inherits the ordinary `TMPDIR=/var/folders/...`, so its `tracePath` keeps
    # the un-canonical spelling and a single-root comparison matched nothing -- skipping every
    # cleanup and leaving the plugin copies and transcripts behind after each eval. Recognising
    # both spellings only decides WHICH root is trusted; the strict link walk below still runs
    # from whichever one matched, so an arbitrary intermediate symlink is refused either way.
    candidate_roots = {tempfile.gettempdir(), os.environ.get("TMPDIR") or ""}
    temp_roots = {
        fs.absolute_without_resolving(Path(spelling))
        for raw in list(candidate_roots)
        if raw
        for spelling in (raw, os.path.realpath(raw))
    }
    for root in roots:
        # The NAME is not ownership. A `tracePath` is harness output, and on the malformed-result
        # path it is recovered from a document nothing validated -- so a path like
        # `/home/user/claude-eval-project/out/trace.jsonl` would have had its project directory
        # recursively deleted. Containment under the process temp root is what actually says the
        # harness made it; the name check stays as the second half of the pair.
        absolute = fs.absolute_without_resolving(root)
        temp_root = next((t for t in temp_roots if t in absolute.parents), None)
        if temp_root is None:
            continue
        if not root.name.startswith("claude-eval-"):
            continue
        # Lexical containment is not physical containment: `/tmp/link/claude-eval-victim` passes
        # the check above while `/tmp/link` is a symlink out of the temp tree, and `rmtree`
        # follows intermediate links. Every component between the temp root and the target is
        # checked with the kernel's own link test -- the same primitive the provenance walk uses
        # -- before anything is deleted.
        relative = absolute.relative_to(temp_root)
        walked = temp_root
        crossed = False
        for part in relative.parts:
            walked = walked / part
            try:
                if fs.is_link_or_reparse(walked.lstat()):
                    crossed = True
                    break
            except OSError:
                # Missing or unreadable: either way there is nothing here we can prove is the
                # harness's, and a path we cannot inspect is never one we recursively delete.
                crossed = True
                break
        if crossed:
            continue
        shutil.rmtree(root, onerror=_record(root))
    if failures:
        # Best effort still, but never silent: these hold a copy of the plugin under test and the
        # sessions' traces, and the operator is the only one who can clear what is left.
        print(
            "! could not remove kept eval directories, which hold a plugin copy and session "
            f"traces: {', '.join(sorted(set(failures)))}",
            file=sys.stderr,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "cluster", nargs="?", default=str(REPO / "evals" / "routing" / "prompt-tooling.json"),
        help="path to a cluster JSON file",
    )
    parser.add_argument("--runs", type=int, default=3, help="runs per case (default 3)")
    parser.add_argument(
        "--plugin-dir", type=Path, default=REPO, help="plugin to load (default this repo)"
    )
    parser.add_argument("--case", default="*", help="glob over case ids (default all)")
    parser.add_argument("--limit", type=int, default=0, help="cap number of cases (0 = all)")
    parser.add_argument("--concurrency", type=int, default=4, help="parallel runs (default 4)")
    parser.add_argument(
        "--timeout", type=int, default=180,
        help="per-run seconds before the session is cut and its partial transcript graded "
             "(default 180)",
    )
    parser.add_argument(
        "--max-turns", type=int, default=nativecases.DEFAULT_MAX_TURNS,
        help=f"turns per run before the session is cut (default {nativecases.DEFAULT_MAX_TURNS}). "
             "A measurement condition, not a convenience: a routing decision missed because the "
             "session ran out of turns reads as a routing failure",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="positive passes at this fire rate; must be > 0 and <= 1 (default 0.5)",
    )
    parser.add_argument("--output-dir", type=Path, default=None, help="write benchmark.json here")
    parser.add_argument(
        "--max-cost-usd", type=float, default=None,
        help="hand the native harness a hard cost ceiling; it stops launching runs when hit, and "
             "the cases it never reached are reported INCONCLUSIVE rather than failed",
    )
    # Without this the sessions take whatever model the CLI defaults to, which is NOT the model of
    # the session that launched them. That silently invalidated a comparison once: two runs believed
    # to differ by model tier were both sonnet.
    parser.add_argument(
        "--model", default=None,
        help="model for the eval sessions (alias or id). Default: the CLI's own default, which is "
             "NOT inherited from the launching session",
    )
    parser.add_argument(
        "--clean-room", action="store_true",
        help="relocate CLAUDE_CONFIG_DIR to a temp dir holding only credentials. MEASURED "
             "2026-09-14 "
             "to change nothing under the native harness, which sets its own config dir: the child "
             "session's component surface was identical with and without it. Kept for a non-native "
             "caller and recorded, but read `components_observed` in the conditions -- that is the "
             "surface the sessions actually saw",
    )
    return parser


def checked_cluster_shape(spec: object) -> dict:
    """The cluster document, or a ValueError naming what is wrong with its shape.

    ONE parser for this fact, because the cluster is read twice: once before the sessions and
    once after, to prove it did not change under them. The post-session read had no shape check
    at all, so a cluster edited mid-batch into a scalar case ended the paid run in an
    AttributeError traceback instead of the documented exit -- the same defect the pre-session
    check exists for, on the path where a session has already been bought.
    """
    if (
        not isinstance(spec, dict)
        or not isinstance(spec.get("cluster"), str)
        or not spec["cluster"].strip()
    ):
        raise ValueError("needs a top-level object with a non-empty 'cluster'")
    cases = spec.get("cases")
    # Checked before any caller calls `.get()` on an entry: `"cases": null` or an entry like `42`
    # otherwise raised TypeError/AttributeError as a traceback.
    if not isinstance(cases, list) or not cases or any(
        not isinstance(case, dict) for case in cases
    ):
        raise ValueError("'cases' must be a non-empty list of objects")
    return spec


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.runs < 1:
        print(f"--runs must be >= 1 (got {args.runs}); 0 would make every negative pass vacuously",
              file=sys.stderr)
        return 2
    try:
        args.threshold = routing.validated_threshold(args.threshold)
    except ValueError as exc:
        print(f"--{exc}", file=sys.stderr)
        return 2
    if CLAUDE is None:
        print("claude CLI not found on PATH", file=sys.stderr)
        return 2

    cluster_path = Path(args.cluster)
    try:
        spec = json.loads(provenance._read_regular_file(cluster_path).decode("utf-8"))
    except (provenance.ProvenanceError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"cluster error: {exc}", file=sys.stderr)
        return 2
    try:
        checked_cluster_shape(spec)
    except ValueError as exc:
        print(f"cluster error: {exc}", file=sys.stderr)
        return 2
    try:
        members = provenance.validated_members(spec.get("members"))
        # Checked HERE, with the rest of the cluster, rather than where it is joined to a path:
        # the name becomes a directory `write_cases` removes before recreating, so a traversing
        # name must be refused before anything is computed or any session is paid for.
        fs.safe_path_segment(spec["cluster"], what="cluster")
    except (provenance.ProvenanceError, ValueError) as exc:
        print(f"{exc}", file=sys.stderr)
        return 2

    raw_cases = spec["cases"]
    cases = [c for c in raw_cases if fnmatch.fnmatch(str(c.get("id")), args.case)]
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        print(f"no cases in {cluster_path} match --case {args.case!r}", file=sys.stderr)
        return 2
    # Every selected case is validated BEFORE any session is paid for. The retiring runner learned
    # this the expensive way: a malformed target raised only at scoring time, after the whole batch
    # had run.
    for case in cases:
        try:
            routing.scoring_targets(case, members)
            # `scoring_targets` never looks at the prompt, so without this a `None` prompt reached
            # the generator, became the literal string "None", and bought a paid session and a
            # recorded routing verdict for input the retiring runner refused outright.
            prompt = case.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(
                    f"case {case.get('id')!r} prompt must be a non-empty string (got {prompt!r})"
                )
            # The ORIGINAL value, not `str()` of it: coercion accepted a missing id as the string
            # "None" and a numeric one as "42", and a missing id then raised KeyError inside the
            # generator rather than exiting 2 here. `safe_path_segment` rejects a non-string and an
            # empty one itself, so no separate type check is added -- one a mutation could not
            # make fail is a guard this repository treats as worse than none.
            fs.safe_path_segment(case.get("id"), what="case id")
        except ValueError as exc:
            print(f"cluster error: {exc}", file=sys.stderr)
            return 2

    # Classified for EVERY run, not just clean-room ones. Recording `null` on an ordinary run made
    # two benchmarks taken against different providers -- Anthropic versus Bedrock versus Vertex --
    # look identical in their conditions, which is exactly the comparison this block exists to stop.
    try:
        auth_mode = eval_clean_room.auth_provider_mode(None, clean_room=bool(args.clean_room))
    except eval_clean_room.AuthUnavailable as exc:
        print(f"clean room unavailable: {exc}", file=sys.stderr)
        return 2

    # Everything from here runs INSIDE the stack. Entering `clean_env()` copies `.credentials.json`
    # into a temp directory immediately, so any return or raise between that entry and the
    # `with` that was supposed to hold it -- a provenance failure, a duplicate case id -- left the
    # credential copy on disk. The stack now wraps the whole post-entry path, and `_run_batch`
    # holds the part that can fail.
    with contextlib.ExitStack() as stack:
        env: dict | None = None
        if args.clean_room:
            try:
                # `clean_env()` raises AuthUnavailable when ENTERED, not when constructed, so it
                # is entered inside the handler that turns that into exit 2.
                env = stack.enter_context(eval_clean_room.clean_env())
            except eval_clean_room.AuthUnavailable as exc:
                print(f"clean room unavailable: {exc}", file=sys.stderr)
                return 2
            print("! --clean-room was measured on 2026-09-14 to change nothing under `claude "
                  "plugin eval`, which sets its own config dir. Read `components_observed` in the "
                  "written conditions for the surface these sessions actually saw.",
                  file=sys.stderr)
        return _run_batch(args, spec, members, cases, env, auth_mode)


def _run_batch(args, spec: dict, members: list, cases: list, env, auth_mode) -> int:
    """The measurement itself, split out so the clean room's context wraps every exit path.

    Not a cosmetic split: with the body inline, an early return between entering `clean_env()` and
    the `with` that held it left a copy of the operator's credentials in a temp directory.
    """
    cluster_path = Path(args.cluster)
    try:
        before = provenance.benchmark_provenance(
            [cluster_path], cases, args.case, args.plugin_dir, args.limit or None,
            evaluator_paths=list(EVALUATOR_PATHS), members=members,
        )
    except provenance.ProvenanceError as exc:
        print(f"provenance error: {exc}", file=sys.stderr)
        return 2

    # Read from the plugin being evaluated, not this checkout: `--plugin-dir` can name another
    # revision or another plugin, and grading those runs against this repository's roster produces
    # a confident verdict about something that was never measured.
    fleet_agents, fleet_skills, namespace = plugin_roster(args.plugin_dir)
    fleet_roster = fleet_agents | fleet_skills

    try:
        # `cluster_files` refuses duplicate ids, and that refusal was outside every handler: the
        # CLI ended in a traceback instead of the documented configuration-error exit 2.
        files = nativecases.cluster_files(
            spec, cases, agents=fleet_agents,
            max_turns=args.max_turns, timeout_seconds=args.timeout,
        )
    except ValueError as exc:
        print(f"cluster error: {exc}", file=sys.stderr)
        return 2

    with contextlib.ExitStack() as frozen_stack:
        try:
            # `frozen_plugin()` re-reads the plugin and hashes the private copy when it is
            # ENTERED, so a plugin that became unreadable or changed since `before` raises
            # here -- past the handler above, which has already returned. Entering it inside
            # its own handler keeps an anticipated provenance failure at the documented
            # exit 2 instead of a traceback.
            frozen, identity = frozen_stack.enter_context(
                provenance.frozen_plugin(args.plugin_dir)
            )
        except provenance.ProvenanceError as exc:
            print(f"provenance error: {exc}", file=sys.stderr)
            return 2
        # The name is already validated as a single path segment above, and `write_cases` refuses
        # an un-normalised directory of its own; a third check here would be one no test can make
        # fire, which is the kind of guard this repository treats as worse than none.
        # The snapshot is taken AFTER `before` was computed, so the source could have changed in
        # between: the sessions would run these bytes while the benchmark recorded the earlier
        # hash, and a source that changed back before the final reread would hide it completely.
        # The retiring runner compared these two and so does this.
        if identity["sha256"] != before["plugin"]["sha256"]:
            print(
                "\nprovenance error: the plugin changed between recording its identity and "
                "freezing the copy to execute; benchmark.json was not written",
                file=sys.stderr,
            )
            return 2
        eval_dir_name = f"evals/generated/{spec['cluster']}"
        write_cases(frozen / eval_dir_name, files, spec)
        result_path = frozen / "native-result.json"
        try:
            completed = subprocess.run(
                native_command(frozen, eval_dir_name, result_path, args),
                env=env, encoding="utf-8", errors="replace",
            )
        except OSError as exc:
            # The PATH check at startup is not a guarantee at launch: the CLI can be replaced,
            # lose its execute bit, or vanish in between. The retiring runner caught a broken
            # spawn; leaving it uncaught turned a measurement failure into a traceback, which
            # reads as a bug in the runner rather than as "nothing was measured".
            print(f"\ncould not launch the native harness ({exc}); benchmark.json was not "
                  "written", file=sys.stderr)
            return 3
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"\nnative harness produced no readable result ({exc}); exit "
                  f"{completed.returncode}. benchmark.json was not written", file=sys.stderr)
            return 3
        try:
            runs_by_case = _run_records(result)
        except MalformedNativeResult as exc:
            # The runs are already paid for and `--keep-temp` has already left their directories,
            # each holding a plugin copy and a session transcript. Rejecting the shape is no
            # reason to leave them: the structured records are unavailable here, so the trace
            # paths are recovered from whatever the document does carry.
            _remove_kept_temp_dirs(_recovered_trace_records(result))
            print(f"\nnative harness wrote an unreadable result ({exc}); exit "
                  f"{completed.returncode}. benchmark.json was not written", file=sys.stderr)
            return 3
        try:
            # The copy that actually RAN, not the source checkout. Checking the source cannot
            # see a mutation a session made inside the private snapshot -- which is the one thing
            # this check exists to catch, and what the retiring runner passed here.
            provenance.verify_frozen_plugin(frozen, identity)
        except provenance.ProvenanceError as exc:
            # Cleanup before returning: `runs_by_case` already names every preserved trace, and
            # these directories hold a copy of the plugin under test plus the sessions'
            # transcripts. An early return here left exactly the disclosure the helper exists for.
            _remove_kept_temp_dirs(runs_by_case)
            print(f"\nprovenance error: {exc}; benchmark.json was not written", file=sys.stderr)
            return 2
    # Grade BEFORE cleaning up: the verdict is computed from the traces inside those kept
    # directories, and reversing these two lines deletes the evidence first and reports every case
    # INCONCLUSIVE with an unreadable-trace note. It did, on the first end-to-end run.
    # A case the harness stopped short of -- `--max-cost-usd` aborts before launching a run --
    # comes back with fewer records than were requested. Grading that array as-is computed a 1/1
    # rate while the artifact still claimed `runs_per_case: 3`, and a passing first run could exit
    # 0. Padding to the requested count makes the unreached runs invalid, so they are excluded and
    # reported rather than silently shrinking the denominator.
    scored = []
    try:
        for case in cases:
            records = list(runs_by_case.get(str(case["id"]), []))
            if len(records) > args.runs:
                # Only a shortfall was handled. An early-access schema returning EXTRA records
                # graded all of them while the artifact still said `runs_per_case: args.runs`.
                print(
                    f"\nnative harness returned {len(records)} runs for case {case['id']!r} but "
                    f"{args.runs} were requested; benchmark.json was not written", file=sys.stderr,
                )
                _remove_kept_temp_dirs(runs_by_case)
                return 3
            missing = args.runs - len(records)
            if missing > 0:
                records += [
                    {"tracePath": None, "error": "run never launched (harness stopped early)"}
                    for _ in range(missing)
                ]
            entry = _scored(
                case, members, records, fleet_roster, args.threshold,
                eval_clean_room.raise_if_auth_failed, fleet_agents, namespace,
            )
            if missing > 0 and not entry["inconclusive"]:
                # Padding alone only shrinks the denominator: a case whose single launched run
                # passed was still graded 1/1 and reported as a result, while the artifact claimed
                # `runs_per_case: 3`. A case the harness never finished was not measured at the
                # run count this benchmark states, so it is INCONCLUSIVE regardless of how its
                # launched runs went.
                entry["inconclusive"] = True
                entry["passed"] = False
                entry["detail"] = (
                    f"INCONCLUSIVE — only {args.runs - missing} of {args.runs} requested runs "
                    "were launched (harness stopped early)"
                )
            scored.append(entry)
    except RegistrationIncomplete as exc:
        # Exit 2, not 3: this is a misconfigured plugin under test, not a transient measurement
        # failure to re-run. `evals/README.md` records the contract.
        _remove_kept_temp_dirs(runs_by_case)
        print(f"\neval aborted: {exc}; benchmark.json was not written", file=sys.stderr)
        return 2
    except eval_clean_room.AuthUnavailable as exc:
        # Aborting the batch, not excluding the affected runs: an authentication outage part-way
        # through invalidates the measurement, and excluding its runs would let the earlier valid
        # ones pass every case and write a benchmark at exit 0. Exit 3 says "no measurement
        # happened, re-run", which is the actionable answer here.
        _remove_kept_temp_dirs(runs_by_case)
        print(f"\neval aborted: {exc}; benchmark.json was not written", file=sys.stderr)
        return 3
    _remove_kept_temp_dirs(runs_by_case)
    inconclusive = [s for s in scored if s["inconclusive"]]
    passed = sum(1 for s in scored if s["passed"])

    for entry in scored:
        mark = "…" if entry["inconclusive"] else ("✓" if entry["passed"] else "✗")
        print(f"{mark} {entry['id']:40s} {entry['detail']}")
        if entry["also_fired"]:
            print(f"    also fired: {', '.join(entry['also_fired'])}")
    summary = f"\n{passed}/{len(scored)} passed"
    if inconclusive:
        summary += f", {len(inconclusive)} INCONCLUSIVE"
    print(summary)
    if result.get("partial"):
        print("! the native harness stopped early (cost ceiling); unreached cases are INCONCLUSIVE")

    # Read off the transcripts (what actually ran), not from the request. More than one entry
    # means the batch itself was not uniform and must not be diffed as a single baseline.
    models = sorted({m for entry in scored for m in entry["models_observed"]})
    conditions = {
        "cli_version": cli_version(),
        "model_requested": args.model,
        "models_observed": models,
        "plugin_dir": plugin_dir_label(args.plugin_dir),
        "threshold": args.threshold,
        # A shorter timeout or turn cap excludes more runs and therefore moves every rate here. Two
        # benchmarks taken at different ones are not comparable and would otherwise look identical.
        "timeout_s": args.timeout,
        "max_turns": args.max_turns,
        "concurrency": args.concurrency,
        "auth_provider": auth_mode,
        # What the flag ASKED for. It is not evidence of isolation: measured on 2026-09-14 it
        # changes nothing under the native harness, which sets its own config dir. The surface the
        # sessions actually saw is `components_observed` below, read off their own init events --
        # a condition has to be observed, not asserted by the caller that wanted it.
        "clean_room_requested": bool(args.clean_room),
        "harness": "claude plugin eval",
        # The routing competition, observed. Two artifacts whose non-fleet components differ were
        # measured against different competitions and must not be diffed as one baseline.
        "components_observed": {
            key: sorted({n for entry in scored for n in entry["components_observed"][key]})
            for key in ("agents", "skills")
        },
        # A union alone cannot distinguish "every run saw this surface" from "one run saw an extra
        # component", and it is the first reading that the artifact is meant to support. False here
        # means the batch was measured against changing competition and is not one baseline.
        # Across the WHOLE batch. A per-case flag is true when every run of case A saw surface X
        # and every run of case B saw a different surface Y, which is exactly the changing
        # competition this is stored to rule out.
        "components_uniform": _batch_components_uniform(scored),
        "native_claude_version": result.get("claudeVersion"),
        "native_cost_usd": result.get("costUsd"),
    }

    if len(models) > 1:
        # The retiring runner said this loudly and the first rewrite dropped it. A benchmark whose
        # runs spanned tiers is not one baseline, and nothing downstream can tell from the rates.
        print(f"\n! WARNING: runs did not use one model ({', '.join(models)}) — this benchmark "
              "mixes conditions and must not be diffed as a single baseline", file=sys.stderr)

    benchmark = {
        "cluster": spec["cluster"],
        "runs_per_case": args.runs,
        "members": sorted(members),
        "conditions": conditions,
        "provenance": before,
        "summary": {"passed": passed, "total": len(scored)},
        "cases": scored,
    }
    if args.output_dir:
        try:
            latest_spec = checked_cluster_shape(
                json.loads(provenance._read_regular_file(cluster_path).decode("utf-8"))
            )
            latest_cases = [
                c for c in latest_spec["cases"] if fnmatch.fnmatch(str(c.get("id")), args.case)
            ]
            if args.limit:
                latest_cases = latest_cases[:args.limit]
            latest_members = provenance.validated_members(latest_spec.get("members"))
            # The targets need the same revalidation as the membership: `scoring_targets`
            # canonicalizes with `set()`, so an unhashable target in a cluster edited mid-batch
            # would raise past the ProvenanceError handler below.
            for latest_case in latest_cases:
                try:
                    routing.scoring_targets(latest_case, latest_members)
                except ValueError as exc:
                    raise provenance.ProvenanceError(
                        f"cluster error after sessions: {exc}"
                    ) from exc
            after = provenance.benchmark_provenance(
                [cluster_path], latest_cases, args.case, args.plugin_dir, args.limit or None,
                evaluator_paths=list(EVALUATOR_PATHS), members=latest_members,
            )
        except (
            provenance.ProvenanceError, KeyError, TypeError, ValueError,
            UnicodeDecodeError, json.JSONDecodeError,
        ) as exc:
            # UnicodeDecodeError and JSONDecodeError were absent here while the pre-session read
            # caught both: a cluster edited mid-batch into invalid UTF-8 or JSON ended the paid
            # run in a traceback rather than the documented exit 2 with a diagnostic.
            print(f"provenance error after sessions: {exc}", file=sys.stderr)
            return 2
        if not provenance._content_provenance_matches(before, after):
            print("provenance error: eval source, selected cases, evaluator, or plugin content "
                  "changed while the batch was running; benchmark.json was not written",
                  file=sys.stderr)
            return 2
        args.output_dir.mkdir(parents=True, exist_ok=True)
        # Atomic, via the kernel's own primitive: an in-place write truncates any existing
        # benchmark first, so an interruption or a full disk destroyed a valid prior capture and
        # left a plausible truncated one -- after these sessions were already paid for.
        fs.atomic_write_bytes(
            args.output_dir / "benchmark.json",
            json.dumps(benchmark, indent=2).encode("utf-8"),
        )
        print(f"\nwrote {args.output_dir / 'benchmark.json'}")

    # Distinct exits, because the two non-zero outcomes ask for different responses: 1 is a routing
    # verdict to investigate, 3 is a measurement that did not happen and wants a re-run. A real
    # failure outranks an inconclusive -- it is the actionable one. (2 stays usage errors.)
    if passed != len(scored) - len(inconclusive):
        return 1
    return 3 if inconclusive else 0


if __name__ == "__main__":
    raise SystemExit(main())
