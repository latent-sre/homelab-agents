#!/usr/bin/env python3
"""Operator-CLI skeleton — every rule in references/cli.md, runnable.

Copy this, rename `prune` to your operation, and keep the structure: stdout is the result, stderr is
everything else, exit codes mean something, `--json` emits one document and nothing else, config
resolves flag > env > file > default, and the destructive path computes its plan unconditionally
while gating only the effect.

Successful and dry-run JSON keeps the applied/count/items shape. An effect that raises stops the
batch and emits applied=null, complete=false, confirmed successes in count/items, the raising item
in unknown, and the untouched remainder in not_attempted. An exception cannot prove no effect.

Standard library only, so it runs anywhere Python does.

    ./cli_skeleton.py prune --dry-run --json
    ./cli_skeleton.py prune --older-than 30 --yes
    LAB_OLDER_THAN=7 ./cli_skeleton.py prune --dry-run

The dry-run guarantee is the part worth testing, and the test is a spy — "it printed the right
thing" is not evidence that nothing happened:

    def test_dry_run_plans_but_does_not_delete():
        removed = []
        plan = prune(_fake_items(), older_than=30, dry_run=True, remove=removed.append)
        assert plan                # the decision ran
        assert removed == []       # and the effect did not
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from typing import Any, Callable, Iterable, Sequence

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2  # distinct so a wrapper can tell "called wrong" from "operation failed"

DEFAULTS = {"older_than": 14}
CONFIG_PATH = os.path.expanduser("~/.config/labtool.json")


# --- output -------------------------------------------------------------------------------------
# The whole contract in two functions: results go to stdout, everything else to stderr. Keeping
# them separate here is what stops a progress line from ending up inside `--json` output later.

def out(line: str) -> None:
    print(line, file=sys.stdout)


def note(line: str) -> None:
    """Progress, warnings, and diagnostics — never stdout, so `| jq` stays clean."""
    print(line, file=sys.stderr)


def styled(text: str, code: str) -> str:
    """Color only for a human on a terminal; ANSI escapes in a log file are noise."""
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return text
    return f"\033[{code}m{text}\033[0m"


# --- configuration ------------------------------------------------------------------------------

def resolve_config(args: argparse.Namespace) -> dict[str, Any]:
    """Flag > environment > config file > default. Documented in --help, printed under --debug."""
    config: dict[str, Any] = dict(DEFAULTS)
    sources = {key: "default" for key in config}

    try:
        with open(CONFIG_PATH, encoding="utf-8") as handle:
            file_config = json.load(handle)
            if not isinstance(file_config, dict):
                raise Usage(f"config {CONFIG_PATH} must contain a JSON object")
            for key, value in file_config.items():
                if key in config:
                    config[key], sources[key] = value, CONFIG_PATH
    except FileNotFoundError:
        pass
    except (OSError, json.JSONDecodeError) as exc:
        # A malformed config is a usage error, not a crash: say which file and what to fix.
        raise Usage(f"cannot read config {CONFIG_PATH}: {exc}") from exc

    if args.older_than is not None:
        config["older_than"], sources["older_than"] = args.older_than, "--older-than"
    elif (env := os.environ.get("LAB_OLDER_THAN")) is not None:
        try:
            config["older_than"], sources["older_than"] = int(env), "$LAB_OLDER_THAN"
        except ValueError as exc:
            raise Usage(f"$LAB_OLDER_THAN must be an integer, got {env!r}") from exc

    # Bound the threshold AFTER precedence resolves, so the check covers the flag, the environment,
    # and the config file with one rule instead of three. A negative age is not a smaller cleanup —
    # every item is "older than -1 day", so a typo (`--older-than -1`) or a malformed config value
    # silently turns a bounded prune into delete-everything. `argparse` accepts `-1` happily, and
    # the placeholder `delete()` below is meant to be replaced by a genuinely destructive call, so
    # this is exactly the input-bounding a destructive CLI owes its caller.
    # JSON booleans compare as integers in Python; accepting true silently broadens the prune.
    if type(config["older_than"]) is not int:
        raise Usage(
            f"--older-than must be an integer; got {config['older_than']!r} "
            f"(from {sources['older_than']})"
        )
    if config["older_than"] < 0:
        raise Usage(
            f"--older-than must be zero or more; got {config['older_than']} "
            f"(from {sources['older_than']}). A negative threshold matches EVERY item."
        )

    if args.debug:
        for key, value in config.items():
            note(f"config {key}={value} (from {sources[key]})")
    return config


class Usage(Exception):
    """A bad invocation — exits EXIT_USAGE, never a traceback."""


class Failure(Exception):
    """The operation genuinely failed — exits EXIT_FAILURE with a one-line diagnosis."""


class PartialFailure(Failure):
    """Carry confirmed results without claiming the raising operation had no effect."""

    def __init__(self, message: str, completed: list[dict[str, Any]],
                 unknown: dict[str, Any], not_attempted: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.completed = completed
        self.unknown = unknown
        self.not_attempted = not_attempted


# --- the operation -----------------------------------------------------------------------------

def prune(
    items: Iterable[dict[str, Any]],
    *,
    older_than: int,
    dry_run: bool,
    remove: Callable[[str], None],
) -> list[dict[str, Any]]:
    """Decide unconditionally; act only when not dry_run.

    `remove` is injected so a test can pass a spy. That injection is the whole reason the dry-run
    guarantee is testable rather than asserted in a comment.
    """
    planned = [item for item in items if item["age_days"] > older_than]  # DECISION — always runs
    if not dry_run:
        completed = []
        for index, item in enumerate(planned):
            try:
                remove(item["name"])                                     # EFFECT — the gated line
            except Exception as exc:
                # A lost acknowledgement may follow a committed effect; stop before more writes.
                raise PartialFailure(str(exc), completed, item, planned[index + 1:]) from exc
            completed.append(item)
    return planned


def discover() -> list[dict[str, Any]]:
    """Replace with the real inventory call. Raises Failure on an unreachable source."""
    return [
        {"name": "snapshot-2026-05-01", "age_days": 84},
        {"name": "snapshot-2026-07-20", "age_days": 4},
    ]


def delete(name: str) -> None:
    """Replace with the real destructive call."""
    note(f"deleted {name}")


# --- wiring ------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="labtool",
        description="Operate lab snapshots.",
        epilog=(
            "Configuration precedence: --flag > environment > %s > built-in default.\n"
            "Example: labtool prune --older-than 30 --dry-run --json" % CONFIG_PATH
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version="labtool 1.0.0 (commit unknown)")

    # Global flags live on a PARENT parser attached to each subcommand, not on the top-level parser.
    # Defining them in both places is the classic argparse trap: `tool --json prune` sets it True,
    # then the subparser re-parses and resets it to its own default, silently dropping the flag.
    # Attaching them only here means `tool prune --json` — the order people actually type — works.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="emit one JSON document on stdout, nothing else")
    common.add_argument("--debug", action="store_true", help="verbose diagnostics and effective config on stderr")

    sub = parser.add_subparsers(dest="command", required=True)
    prune_cmd = sub.add_parser("prune", parents=[common], help="remove snapshots older than a threshold")
    prune_cmd.add_argument("--older-than", type=int, default=None, metavar="DAYS")
    prune_cmd.add_argument("--dry-run", action="store_true", help="print the plan; change nothing")
    prune_cmd.add_argument("--yes", action="store_true", help="skip the confirmation prompt (for automation)")
    return parser


def confirm(count: int, assume_yes: bool) -> bool:
    """Irreversible work confirms — and never hangs waiting for a prompt nobody can answer."""
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        # Failing loudly beats blocking forever in CI, and beats silently proceeding.
        raise Usage("refusing to delete without confirmation: pass --yes for non-interactive use")
    # Confirmation is diagnostic output too: input(prompt) would corrupt --json stdout.
    print(f"delete {count} snapshot(s)? [y/N] ", file=sys.stderr, end="", flush=True)
    answer = input().strip().lower()
    return answer in {"y", "yes"}


def main(argv: Sequence[str] | None = None) -> int:
    # Clean up and exit non-zero on a signal, so an interrupted run leaves no lock behind.
    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = resolve_config(args)
        items = discover()
        planned = prune(
            items,
            older_than=config["older_than"],
            dry_run=True,  # plan first, always — the confirmation needs the real plan to show
            remove=delete,
        )

        if args.dry_run:
            emit(planned, args, applied=False)
            return EXIT_OK
        if not planned:
            emit(planned, args, applied=True)
            return EXIT_OK
        if not confirm(len(planned), args.yes):
            note("aborted")
            return EXIT_FAILURE

        prune(items, older_than=config["older_than"], dry_run=False, remove=delete)
        emit(planned, args, applied=True)
        return EXIT_OK

    except Usage as exc:
        note(f"{styled('usage error', '33')}: {exc}")
        return EXIT_USAGE
    except PartialFailure as exc:
        emit(exc.completed, args, applied=None, failure=exc)
        note(f"{styled('failed', '31')}: {exc}")
        if args.debug:
            raise
        return EXIT_FAILURE
    except Failure as exc:
        note(f"{styled('failed', '31')}: {exc}")
        return EXIT_FAILURE
    except Exception as exc:  # unexpected: one line by default, traceback under --debug
        if args.debug:
            raise
        note(f"{styled('failed', '31')}: unexpected error: {exc} (re-run with --debug for a traceback)")
        return EXIT_FAILURE


def emit(planned: list[dict[str, Any]], args: argparse.Namespace, *, applied: bool | None,
         failure: PartialFailure | None = None) -> None:
    """One JSON document on stdout for machines, a readable table for humans."""
    if args.json:
        result = {"applied": applied, "count": len(planned), "items": planned}
        if failure is not None:
            result.update(complete=False, unknown=[failure.unknown],
                          not_attempted=failure.not_attempted)
        out(json.dumps(result))
    elif failure is not None:
        for item in planned:
            out(f"deleted {item['name']} ({item['age_days']}d)")
    elif not planned:
        out("nothing to prune")
    else:
        verb = "would delete" if not applied else "deleted"
        for item in planned:
            out(f"{verb} {item['name']} ({item['age_days']}d)")
        note(f"{verb} {len(planned)} snapshot(s)")
    if failure is not None:
        note(f"{len(planned)} completed; {failure.unknown['name']}: outcome unknown; "
             f"{len(failure.not_attempted)} not attempted")


if __name__ == "__main__":
    sys.exit(main())
