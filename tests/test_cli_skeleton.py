"""The runnable starter must keep confirmation text out of machine-readable stdout."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / 'skills/sre-tool/assets/cli_skeleton.py'
spec = importlib.util.spec_from_file_location('cli_skeleton', SOURCE)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class TerminalInput(io.StringIO):
    def isatty(self):
        return True


class ConfirmationOutputTest(unittest.TestCase):
    def invoke(self, flags, stdin):
        stdout, stderr = io.StringIO(), io.StringIO()
        removed = []
        with tempfile.TemporaryDirectory() as temporary, \
                mock.patch.object(cli, 'CONFIG_PATH', str(Path(temporary) / 'missing.json')), \
                mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(cli, 'delete', side_effect=removed.append), \
                mock.patch.object(cli.signal, 'signal'), \
                mock.patch.object(cli.sys, 'stdin', stdin), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli.main(['prune', '--json', *flags])
        return status, stdout.getvalue(), stderr.getvalue(), removed

    def test_interactive_confirmation_preserves_json_and_effect(self):
        """A real input prompt used to precede the JSON document on stdout."""
        status, stdout, stderr, removed = self.invoke([], TerminalInput('yes\n'))
        self.assertEqual(status, cli.EXIT_OK)
        self.assertEqual(json.loads(stdout), {
            'applied': True, 'count': 1,
            'items': [{'name': 'snapshot-2026-05-01', 'age_days': 84}],
        })
        self.assertIn('delete 1 snapshot(s)?', stderr)
        self.assertEqual(removed, ['snapshot-2026-05-01'])

    def test_unattended_confirmation_requires_explicit_yes(self):
        for flags, permitted in (([], False), (['--yes'], True)):
            with self.subTest(flags=flags):
                status, stdout, stderr, removed = self.invoke(flags, io.StringIO())
                if permitted:
                    self.assertEqual(status, cli.EXIT_OK)
                    self.assertTrue(json.loads(stdout)['applied'])
                    self.assertEqual(removed, ['snapshot-2026-05-01'])
                else:
                    self.assertEqual(status, cli.EXIT_USAGE)
                    self.assertEqual(stdout, '')
                    self.assertIn('pass --yes', stderr)
                    self.assertEqual(removed, [])

    def test_decline_and_dry_run_cannot_delete(self):
        status, stdout, stderr, removed = self.invoke([], TerminalInput('no\n'))
        self.assertEqual(status, cli.EXIT_FAILURE)
        self.assertEqual(stdout, '')
        self.assertIn('aborted', stderr)
        self.assertEqual(removed, [])
        status, stdout, stderr, removed = self.invoke(['--dry-run'], io.StringIO())
        self.assertEqual(status, cli.EXIT_OK)
        self.assertFalse(json.loads(stdout)['applied'])
        self.assertEqual(removed, [])


if __name__ == '__main__':
    unittest.main()
