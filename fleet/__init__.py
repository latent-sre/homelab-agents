"""The fleet kernel: the primitives every maintainer instrument shares.

`scripts/` holds the fleet's instruments -- the validator, the adapter generator, the doctor, the
probes, the Codex installer -- and the two plugin hooks. Until 2026-09-13 each instrument carried
its own copy of the same primitives: a symlink/reparse-point check (three copies, one with a
divergent default), a subprocess runner (four, disagreeing on how a timed-out stream is decoded),
a stream-json decoder (four), a SHA-256 convention (two), and a frontmatter reader whose strict
companion lived in a different file. A defect fixed in one copy stayed live in the others, and
nothing could tell two instruments' readings of one tree apart. This package is the one home for
those primitives; the instruments import it and keep only their policy.

Design rules, binding on every module here:

* **Records, never judgments.** The kernel reads, decodes, hashes, and runs. Whether a tool grant
  is adopted, a description too long, or a command live is policy, and policy stays in the
  instrument that owns it (the principle `scripts/fleet_records.py` established).
* **The inspected tree is data.** Nothing under a caller-supplied root is imported or executed by
  a kernel function, so a foreign checkout or frozen baseline is safe to read.
* **Skip, never crash, on a line the reader cannot interpret** when the input is a transcript or
  a report that was already paid for; **refuse, never guess** when the input is a definition whose
  misreading would silently change what it configures. Each module's docstring says which side it
  is on and why.
* **Standard library only**, because the hooks that share `scripts/` with these instruments must
  stay importable under `python -I -S` and no kernel module may become a temptation to import
  from one. The dev dependency group in `pyproject.toml` serves tests and lint, never this package.

The plugin hooks (`scripts/readonly-guard.py`, `scripts/live-effect-gate.py`) do NOT import this
package: they are single self-contained files by contract (AGENTS.md, "Keep isolated hooks
dependency-free"), and the validator reads their rosters as data.

The migration that put the instruments on this kernel is recorded in
`docs/decisions/2026-09-13-machinery-rewrite.md`.
"""

from __future__ import annotations
