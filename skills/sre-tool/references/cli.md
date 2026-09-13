# The CLI contract — what an operator tool owes its caller

Read before building or changing a command-line tool. The universal rules live in
`skills/sre-tool/SKILL.md`. On any conflict, SKILL.md wins.

An operator tool is called by a human at 3 a.m. *and* by a script at 3 a.m. Both need the same
things: a truthful exit code, output they can parse, and no surprises.

## Streams and exit codes

- **stdout is the result; stderr is everything else.** Progress, warnings, and logs go to stderr, so
  `tool list | jq .` never breaks because a status line landed in the JSON. This is the single most
  violated rule in internal tooling, and it is why `2>/dev/null` exists in so many runbooks.
- **Exit 0 means it worked.** Non-zero means it did not, and the code is meaningful: `1` general
  failure, `2` usage error (bad flags — distinguishable so a wrapper can tell "you called me wrong"
  from "the operation failed"), and any tool-specific codes documented in `--help`. A tool that exits
  0 on failure will be trusted by a script that then does the wrong thing.
- **Never print a stack trace as the primary error.** Catch the expected failures, print a
  one-line diagnosis to stderr with what to do next, and reserve tracebacks for `--debug`.
- **A partial failure is a failure.** Processing 9 of 10 items exits non-zero and says which one
  did not return successfully; a summary line on stderr and confirmed successes on stdout. An effect
  can commit before its acknowledgement fails: mark the raising item's outcome unknown and stop
  further effects until reconciliation, rather than reporting it as definitely untouched.

## Machine-readable output

- **`--json` emits one JSON document on stdout and nothing else** — no banner, no progress, no
  trailing summary. Its schema is a contract: adding a field is fine, renaming or removing one is a
  breaking change for whatever parses it.
- Prefer JSON Lines for streams (one object per line, flushed) so a caller can process incrementally.
- Human output can be pretty (colors, tables, alignment); **detect a non-TTY and drop the styling**
  automatically, because ANSI escapes in a log file are noise nobody asked for. Honor `NO_COLOR`.
- Keep the human and machine paths from diverging: derive both from the same data structure, so a
  field added to one appears in the other.

The starter preserves `applied`/`count`/`items` for success and dry-run. On an apply failure it emits
`applied: null`, `complete: false`, confirmed successes in `count`/`items`, the raising item in
`unknown`, and the unattempted remainder in `not_attempted`. Null means the overall outcome needs
reconciliation, not that nothing changed; callers must inspect the nonzero exit and item outcomes.

## Configuration precedence, stated in one place

**Flag > environment variable > config file > default**, documented in `--help`. Anything else
surprises somebody: a script that sets a flag must win over the operator's shell env. Print the
effective configuration under `--debug` — "which config did it actually use" is a question that
otherwise costs an hour.

## Secrets

- **Never accept a secret as a command-line argument.** Argv is visible in `ps`, in shell history,
  and in CI logs. Take secrets from an environment variable, a file path, or stdin.
- Never log a secret, including in the effective-config dump above — print the source
  (`token: <from $LAB_TOKEN>`), never the value.

## Destructive operations

- **`--dry-run` computes the plan and prints it; only the effect is gated.** Same rule and the same
  spy-based proof as `sde-agents:code-craft`'s Python and Bash references — a dry-run that is a
  separate code path proves nothing about the real one.
- **Confirm interactively for anything irreversible**, and offer `--yes` for automation. Skip the
  prompt automatically when stdin is not a TTY *only* if `--yes` was passed; otherwise fail with a
  usage error rather than hanging forever waiting for input nobody can give.
- **Idempotent where possible**, and say so: re-running after a partial failure should converge, not
  double-apply.
- Name the blast radius in the plan output — how many things, which ones, on which host.

## Shape

- One command does one thing; subcommands for related operations (`tool service restart`), a noun-verb
  shape kept consistent across the whole tool.
- `--help` on every level, with at least one worked example — the example is what people actually
  read.
- `--version` that prints something traceable to a commit.
- Long-running work: progress on stderr, and a timeout with a non-zero exit rather than hanging.
- Signals: handle `SIGINT`/`SIGTERM` by cleaning up (remove the temp dir, release the lock) and
  exiting non-zero. A tool that leaves a lock behind on Ctrl-C blocks the next run.

## Starting one

[`assets/cli_skeleton.py`](../assets/cli_skeleton.py) is a runnable stdlib-only implementation of
every rule above — streams, exit codes, precedence, `--json`, dry-run with the effect injected, and
signal cleanup — with a spy-based dry-run test in its docstring.

## Verify

Run it four ways and paste the evidence: `--help` (documents the precedence), the happy path with
`--json | jq .` (clean parse), a deliberate failure (non-zero exit, one-line stderr message), and
`--dry-run` on something destructive (plan printed, nothing changed — proven by a spy or by checking
the target afterwards).
