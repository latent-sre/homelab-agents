"""One subprocess runner for every instrument that spawns a CLI.

Four instruments used to call `subprocess.run` themselves and disagreed on the failure paths:
one turned a timed-out stream into the text `b'...'` by calling `str()` on bytes, another raised
`TimeoutExpired` out of a probe leg and discarded every later check (roadmap PROBE-006). This
module owns those decisions once.

Decoding is explicit UTF-8 with replacement. `text=True` would use the locale encoding, which on
Windows is cp1252 and blows up on a CLI's box-drawing output -- leaving `stdout` as None rather
than failing honestly, so a probe would report a crash as though it were a verdict.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


def decode_stream(value: object) -> str:
    """Text for a captured stream, whatever the failure path handed us.

    Not a convenience wrapper: `subprocess.TimeoutExpired.stdout` is **bytes even when the call
    passed `encoding=`**, so an `isinstance(value, str)` test silently yields "" and throws away the
    partial transcript of a session that was already paid for. Every reader routes through here so
    the bytes/str asymmetry is answered in one place.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return ""


@dataclass(frozen=True)
class CommandResult:
    """What one spawned command did, including the two ways it can fail to answer.

    `returncode` is None when the process was killed by the timeout; `error` carries the
    exception text when the process timed out or never started. A caller deciding a verdict must
    look at `timed_out` and `failed_to_start` before trusting `stdout`: a timed-out stream is a
    partial transcript, not a completed answer.
    """

    argv: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    failed_to_start: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out and not self.failed_to_start


def run(
    argv: Sequence[str],
    *,
    timeout: float,
    cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None,
    stdin: str | None = None,
) -> CommandResult:
    """Run `argv` to completion and report it; never raises for a timeout or a missing binary.

    A `timeout` is required, not defaulted: every caller is spawning something that can hang (a
    model session, a CLI waiting on a network), and an unbounded wait is a hung instrument that
    reports nothing. The partial streams of a timed-out process are decoded and returned so the
    evidence already paid for survives the failure.
    """
    args = [os.fspath(part) for part in argv]
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
            cwd=None if cwd is None else os.fspath(cwd),
            env=None if env is None else dict(env),
            input=stdin,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            tuple(args),
            None,
            decode_stream(exc.stdout),
            decode_stream(exc.stderr),
            timed_out=True,
            error=str(exc),
        )
    except OSError as exc:
        return CommandResult(tuple(args), 127, "", "", failed_to_start=True, error=str(exc))
    return CommandResult(
        tuple(args),
        completed.returncode,
        decode_stream(completed.stdout),
        decode_stream(completed.stderr),
    )


def run_completed(argv: Sequence[str], *, timeout: float, **kwargs) -> subprocess.CompletedProcess:
    """`subprocess.run` with the kernel's decoding, for callers that still want the raw object.

    Timeouts and missing binaries RAISE here, as they do from `subprocess.run`. This exists so an
    instrument that has not yet moved its verdict logic onto `run()` shares the encoding decision
    today; new code uses `run()`.
    """
    return subprocess.run(
        [os.fspath(part) for part in argv],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        **kwargs,
    )
