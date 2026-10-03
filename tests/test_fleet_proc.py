"""Kernel subprocess runner: every failure path yields a result, and streams are always text."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

from fleet import proc


class DecodeStreamTests(unittest.TestCase):
    def test_bytes_str_and_none_all_decode_to_text(self) -> None:
        self.assertEqual(proc.decode_stream(b"caf\xc3\xa9"), "café")
        self.assertEqual(proc.decode_stream("already text"), "already text")
        self.assertEqual(proc.decode_stream(None), "")
        self.assertEqual(proc.decode_stream(b"\xff"), "�")


class RunTests(unittest.TestCase):
    def test_a_completed_command_reports_its_streams_and_code(self) -> None:
        result = proc.run(
            [
                sys.executable,
                "-c",
                "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)",
            ],
            timeout=30,
        )
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout.strip(), "out")
        self.assertEqual(result.stderr.strip(), "err")
        self.assertFalse(result.ok)
        self.assertFalse(result.timed_out)
        self.assertFalse(result.failed_to_start)
        self.assertIsNone(result.error)

    def test_a_timeout_keeps_the_partial_stream_as_text(self) -> None:
        # The partial stdout of a killed process arrives from TimeoutExpired as BYTES even when
        # encoding= was passed; one former runner rendered it as the literal text "b'...'".
        result = proc.run(
            [sys.executable, "-c", "import sys,time; print('partial', flush=True); time.sleep(30)"],
            timeout=2,
        )
        self.assertTrue(result.timed_out)
        self.assertIsNone(result.returncode)
        self.assertFalse(result.ok)
        self.assertEqual(result.stdout.strip(), "partial")
        self.assertNotIn("b'", result.stdout)
        self.assertIn("timed out", result.error or "")

    def test_a_missing_binary_is_a_result_not_an_exception(self) -> None:
        result = proc.run(["definitely-not-a-binary-on-this-host-xyz"], timeout=5)
        self.assertTrue(result.failed_to_start)
        self.assertEqual(result.returncode, 127)
        self.assertFalse(result.ok)
        self.assertTrue(result.error)

    def test_cwd_reaches_the_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = proc.run(
                [sys.executable, "-c", "import os; print(os.getcwd())"], timeout=30, cwd=tmp
            )
            self.assertTrue(result.ok, result)
            self.assertEqual(
                os.path.normcase(os.path.realpath(tmp)),
                os.path.normcase(os.path.realpath(result.stdout.strip())),
            )


if __name__ == "__main__":
    unittest.main()
