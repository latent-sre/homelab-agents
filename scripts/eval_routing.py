#!/usr/bin/env python3
"""Routing evals: generate a cluster's cases and run them with `claude plugin eval`.

`evals/routing/<cluster>.json` is the source. This writes the native case layout to
`evals/generated/<cluster>/` (git-ignored, rewritten every run; `fleet/nativecases.py` owns the
graders) and runs the harness once per polarity, because the two pass at different bars and the
harness takes a single `--threshold`:

- positives (`--tag positive --threshold 0.5`): an expected destination fired in at least half the
  runs;
- negatives (`--tag negative --threshold 1.0`): no forbidden destination fired in any run.

The exit status is the worse of the two runs: 0 every case met its bar, 1 a case fell below it, 2
the harness could not complete (for example a cost ceiling). `--dry-run` writes the cases and
prints the commands without starting a paid session. Results and the HTML report land under the
generated directory.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))  # `import fleet` when run as `python3 scripts/<name>.py`

from fleet import nativecases  # noqa: E402

BARS = (("positive", "0.5"), ("negative", "1.0"))


def write_cases(spec: dict, plugin_dir: Path) -> str:
    """Write the cluster's native cases below the plugin; return the `--eval-dir` value."""
    eval_dir = f"evals/generated/{spec['cluster']}"
    target = plugin_dir / eval_dir
    files = nativecases.cluster_files(spec, spec["cases"])
    if target.exists():
        shutil.rmtree(target)  # a stale case directory must not survive into this run
    for relative, text in files.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    (target / "MANIFEST.json").write_text(nativecases.manifest(spec, files), encoding="utf-8")
    return eval_dir


def commands(
    spec: dict, plugin_dir: Path, eval_dir: str, args: argparse.Namespace
) -> list[list[str]]:
    """One `claude plugin eval` invocation per polarity the cluster actually has."""
    base = [
        "claude", "plugin", "eval", str(plugin_dir),
        "--eval-dir", eval_dir,
        "--runs", str(args.runs),
        "--concurrency", str(args.concurrency),
        "--ablation", "none",
        "--no-publish",
        "--trust-plugin",
    ]
    if args.model:
        base += ["--model", args.model]
    if args.max_cost_usd is not None:
        base += ["--max-cost-usd", str(args.max_cost_usd)]
    if args.case:
        base += ["--case", args.case]
    present = {
        case.get("polarity")
        for case in spec["cases"]
        if not args.case or fnmatch.fnmatchcase(str(case.get("id")), args.case)
    }
    return [[*base, "--tag", tag, "--threshold", bar] for tag, bar in BARS if tag in present]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a routing cluster with claude plugin eval.")
    parser.add_argument("cluster", type=Path, help="path to a cluster JSON file")
    parser.add_argument("--runs", type=int, default=3, help="runs per case (default 3)")
    parser.add_argument("--concurrency", type=int, default=4, help="parallel runs, 1-8 (default 4)")
    parser.add_argument("--model", help="model for the eval sessions (default: the CLI's own)")
    parser.add_argument(
        "--max-cost-usd", type=float, help="hard cost ceiling for each polarity run"
    )
    parser.add_argument("--case", help="glob over case names")
    parser.add_argument(
        "--plugin-dir", type=Path, default=REPO, help="plugin to load (default: this repo)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="write the cases and print the commands only"
    )
    args = parser.parse_args(argv)

    try:
        spec = json.loads(args.cluster.read_text(encoding="utf-8"))
        eval_dir = write_cases(spec, args.plugin_dir)
    except (OSError, ValueError, KeyError) as exc:
        print(f"cannot generate cases from {args.cluster}: {exc}", file=sys.stderr)
        return 2
    print(f"cases written to {args.plugin_dir / eval_dir}")

    claude = shutil.which("claude")
    if claude is None and not args.dry_run:
        print("the claude CLI is not on PATH; nothing was run", file=sys.stderr)
        return 2
    worst = 0
    for command in commands(spec, args.plugin_dir, eval_dir, args):
        print(" ".join(command))
        if not args.dry_run:
            worst = max(worst, subprocess.run([claude, *command[1:]]).returncode)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
