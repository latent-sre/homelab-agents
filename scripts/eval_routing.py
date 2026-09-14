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

**The clean room.** Also measured, and the opposite of what the phase-4 plan assumed: the eval
child session inherits the operator's component surface. Its `init` event listed `code-review`,
`debug` and `verify` alongside the fleet -- direct routing competitors. `--clean-room` therefore
survives, using the same `CLAUDE_CONFIG_DIR` lever as before.

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
import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)  # `import fleet` when run as `python3 scripts/<name>.py`

from fleet import nativecases, provenance, routing, stream  # noqa: E402

REPO = Path(_REPO_ROOT)
CLAUDE = shutil.which("claude")

FLEET_AGENTS = frozenset(p.stem for p in (REPO / "agents").glob("*.md"))
FLEET_SKILLS = frozenset(
    p.name for p in (REPO / "skills").iterdir() if p.is_dir()
) if (REPO / "skills").is_dir() else frozenset()
FLEET = FLEET_AGENTS | FLEET_SKILLS

# The code whose bytes decide a verdict, named for `evaluator_identity`. Two benchmarks produced by
# different grading code are not comparable even when every other condition matches, and this is
# the only place that says which files those are.
EVALUATOR_PATHS = (
    REPO / "scripts" / "eval_routing.py",
    REPO / "fleet" / "routing.py",
    REPO / "fleet" / "nativecases.py",
    REPO / "fleet" / "stream.py",
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
    if eval_dir.exists():
        shutil.rmtree(eval_dir)
    for relative, content in files.items():
        target = eval_dir / relative
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
        *(("--max-cost-usd", str(args.max_cost_usd)) if args.max_cost_usd else ()),
    ]


def _run_records(result: dict) -> dict[str, list[dict]]:
    """Per-case run records from the native result document, keyed by case name."""
    records: dict[str, list[dict]] = {}
    for case in result.get("cases") or []:
        arms = case.get("arms") or {}
        records[str(case.get("name"))] = list(arms.get("with") or [])
    return records


def fired_per_run(
    runs: list[dict], roster: frozenset[str]
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
            fired.append(None)
            notes.append(f"{label}: trace unreadable ({exc}); harness said {run.get('error')!r}")
            continue
        model = stream.observed_model(text)
        if model:
            models.append(model)
        surfaces.append(stream.registered_components(text))
        found = frozenset(routing.fired_components(text, roster))
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
    case: dict, members: list[str], runs: list[dict], roster: frozenset[str], threshold: float
) -> dict:
    fired, notes, models, surfaces = fired_per_run(runs, roster)
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
        "components_observed": {
            key: sorted({name for s in surfaces for name in s.get(key, [])})
            for key in ("agents", "skills")
        },
    }


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
    for root in roots:
        if root.name.startswith("claude-eval-"):
            shutil.rmtree(root, ignore_errors=True)


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
    if (
        not isinstance(spec, dict)
        or not isinstance(spec.get("cluster"), str)
        or not spec["cluster"].strip()
    ):
        print("cluster error: needs a top-level object with a non-empty 'cluster'", file=sys.stderr)
        return 2
    try:
        members = provenance.validated_members(spec.get("members"))
    except provenance.ProvenanceError as exc:
        print(f"{exc}", file=sys.stderr)
        return 2

    cases = [c for c in spec.get("cases", []) if fnmatch.fnmatch(str(c.get("id")), args.case)]
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
        except ValueError as exc:
            print(f"cluster error: {exc}", file=sys.stderr)
            return 2

    clean_room = contextlib.nullcontext(None)
    auth_mode: dict | None = None
    if args.clean_room:
        try:
            from scripts import eval_clean_room
        except ImportError:  # running as a bare script rather than a package
            sys.path.insert(0, str(REPO / "scripts"))
            import eval_clean_room  # type: ignore[no-redef]
        try:
            auth_mode = eval_clean_room.auth_provider_mode(None, clean_room=True)
        except eval_clean_room.AuthUnavailable as exc:
            print(f"clean room unavailable: {exc}", file=sys.stderr)
            return 2
        clean_room = eval_clean_room.clean_env()
        print("! --clean-room was measured on 2026-09-14 to change nothing under `claude plugin "
              "eval`, which sets its own config dir. Read `components_observed` in the written "
              "conditions for the surface these sessions actually saw.", file=sys.stderr)

    try:
        before = provenance.benchmark_provenance(
            [cluster_path], cases, args.case, args.plugin_dir, args.limit or None,
            evaluator_paths=list(EVALUATOR_PATHS), members=members,
        )
    except provenance.ProvenanceError as exc:
        print(f"provenance error: {exc}", file=sys.stderr)
        return 2

    files = nativecases.cluster_files(
        spec, cases, agents=FLEET_AGENTS,
        max_turns=args.max_turns, timeout_seconds=args.timeout,
    )

    with clean_room as env, provenance.frozen_plugin(args.plugin_dir) as (frozen, identity):
        eval_dir_name = f"evals/generated/{spec['cluster']}"
        write_cases(frozen / eval_dir_name, files, spec)
        result_path = frozen / "native-result.json"
        completed = subprocess.run(
            native_command(frozen, eval_dir_name, result_path, args),
            env=env, encoding="utf-8", errors="replace",
        )
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"\nnative harness produced no readable result ({exc}); exit "
                  f"{completed.returncode}. benchmark.json was not written", file=sys.stderr)
            return 3
        runs_by_case = _run_records(result)
        try:
            provenance.verify_frozen_plugin(args.plugin_dir, identity)
        except provenance.ProvenanceError as exc:
            print(f"\nprovenance error: {exc}; benchmark.json was not written", file=sys.stderr)
            return 2
    # Grade BEFORE cleaning up: the verdict is computed from the traces inside those kept
    # directories, and reversing these two lines deletes the evidence first and reports every case
    # INCONCLUSIVE with an unreadable-trace note. It did, on the first end-to-end run.
    scored = [
        _scored(case, members, runs_by_case.get(str(case["id"]), []), FLEET, args.threshold)
        for case in cases
    ]
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
        "native_claude_version": result.get("claudeVersion"),
        "native_cost_usd": result.get("costUsd"),
    }

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
            latest_spec = json.loads(provenance._read_regular_file(cluster_path).decode("utf-8"))
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
        except (provenance.ProvenanceError, KeyError, TypeError) as exc:
            print(f"provenance error after sessions: {exc}", file=sys.stderr)
            return 2
        if not provenance._content_provenance_matches(before, after):
            print("provenance error: eval source, selected cases, evaluator, or plugin content "
                  "changed while the batch was running; benchmark.json was not written",
                  file=sys.stderr)
            return 2
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "benchmark.json").write_text(
            json.dumps(benchmark, indent=2), encoding="utf-8"
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
