"""The exit ladder is ordered by how definite the answer is."""

from __future__ import annotations

import unittest

from fleet import diagnostics as d


class ExitLadderTests(unittest.TestCase):
    def test_failure_outranks_a_hole_outranks_a_warning(self) -> None:
        self.assertEqual(d.exit_status(failed=1, not_computed=1, warned=1), d.EXIT_FAIL)
        self.assertEqual(d.exit_status(failed=0, not_computed=1, warned=1), d.EXIT_NOT_COMPUTED)
        self.assertEqual(d.exit_status(failed=0, not_computed=0, warned=1), d.EXIT_WARN)
        self.assertEqual(d.exit_status(failed=0, not_computed=0, warned=0), d.EXIT_OK)

    def test_the_codes_are_the_documented_literals(self) -> None:
        # Callers in shell and CI compare against these numbers; they are part of the contract.
        self.assertEqual((d.EXIT_OK, d.EXIT_FAIL, d.EXIT_NOT_COMPUTED, d.EXIT_WARN), (0, 1, 2, 3))


if __name__ == "__main__":
    unittest.main()
