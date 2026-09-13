"""The one exit-code ladder for every fleet instrument that reports a verdict.

Before this module the instruments disagreed on what a non-zero exit meant: one used 2 for
"inconclusive" and another used 3, while a third used 2 for a usage error, and a caller that
mapped one instrument's codes onto another's turned a clock problem into a fleet defect. The
ladder below is ordered by how DEFINITE the answer is, and a caller must consult it rather than
compare against literals:

* `EXIT_OK` (0): every check computed and every check passed.
* `EXIT_FAIL` (1): at least one check computed a failure. Outranks everything below because a
  failure is a definite answer.
* `EXIT_NOT_COMPUTED` (2): no failure, but at least one check could not be computed. A clean
  report with a hole in it is not evidence of health, so it cannot exit 0.
* `EXIT_WARN` (3): every check computed, none failed, at least one warned. A warning that exited
  0 once made an instrument agree that a tree was healthy while printing that it was not (issue
  #126); the operator learned to ignore it, which is the same silence the code exists to break.

A "skip" -- a check whose precondition was absent, such as a host that is not installed -- is
deliberately NOT on the ladder: it is a declared non-measurement, not a hole in one.
"""

from __future__ import annotations

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_NOT_COMPUTED = 2
EXIT_WARN = 3


def exit_status(*, failed: int, not_computed: int, warned: int) -> int:
    """The ladder applied to a report's counts."""
    if failed:
        return EXIT_FAIL
    if not_computed:
        return EXIT_NOT_COMPUTED
    if warned:
        return EXIT_WARN
    return EXIT_OK
