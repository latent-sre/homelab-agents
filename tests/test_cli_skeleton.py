"""The runnable starter must validate destructive inputs and report actual partial outcomes."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / 'skills/sre-tool/assets/cli_skeleton.py'
spec = importlib.util.spec_from_file_location('cli_skeleton', SOURCE)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
NO_CONFIG = object()


class TerminalInput(io.StringIO):
    def isatty(self):
        return True


class CliTestCase(unittest.TestCase):
    def invoke(self, flags, stdin=None, *, config=NO_CONFIG, environment=None, remove=None,
               items=None, machine=True):
        stdout, stderr = io.StringIO(), io.StringIO()
        removed = []
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / 'config.json'
            if config is not NO_CONFIG:
                config_path.write_text(json.dumps(config), encoding='utf-8')
            inventory = items if items is not None else cli.discover()
            with mock.patch.object(cli, 'CONFIG_PATH', str(config_path)), \
                mock.patch.dict(os.environ, environment or {}, clear=True), \
                mock.patch.object(cli, 'delete', side_effect=remove or removed.append), \
                mock.patch.object(cli, 'discover', return_value=inventory), \
                mock.patch.object(cli.signal, 'signal'), \
                mock.patch.object(
                    cli.sys, 'stdin', stdin if stdin is not None else io.StringIO()), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = cli.main(['prune', *(['--json'] if machine else []), *flags])
        return status, stdout.getvalue(), stderr.getvalue(), removed


class ConfirmationOutputTest(CliTestCase):
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


class ConfigInputTest(CliTestCase):
    def test_file_threshold_rejects_wrong_types_and_negative_values_before_effects(self):
        for value in (True, False, '30', 1.5, None, [], {}, -1):
            with self.subTest(value=value):
                status, stdout, stderr, removed = self.invoke(
                    ['--yes'], config={'older_than': value})
                self.assertEqual(status, cli.EXIT_USAGE)
                self.assertEqual(stdout, '')
                self.assertIn('config.json', stderr)
                self.assertEqual(removed, [])

    def test_file_root_must_be_an_object(self):
        for config in ([], None, '30', 30, True):
            with self.subTest(config=config):
                status, stdout, stderr, removed = self.invoke(['--yes'], config=config)
                self.assertEqual(status, cli.EXIT_USAGE)
                self.assertIn('JSON object', stderr)
                self.assertEqual(stdout, '')
                self.assertEqual(removed, [])

    def test_effective_source_follows_flag_environment_file_default_precedence(self):
        cases = (
            ([], NO_CONFIG, {}, 1),
            ([], {'older_than': 0}, {}, 2),
            ([], {'older_than': True}, {'LAB_OLDER_THAN': '30'}, 1),
            (['--older-than', '30'], {'older_than': True}, {'LAB_OLDER_THAN': 'bad'}, 1),
        )
        for flags, config, environment, count in cases:
            with self.subTest(flags=flags, config=config, environment=environment):
                status, stdout, stderr, removed = self.invoke(
                    ['--dry-run', *flags], config=config, environment=environment)
                self.assertEqual(status, cli.EXIT_OK, stderr)
                self.assertEqual(json.loads(stdout)['count'], count)
                self.assertEqual(removed, [])

    def test_invalid_effective_environment_is_a_usage_error(self):
        for value in ('bad', '1.5', '-1'):
            with self.subTest(value=value):
                status, stdout, stderr, removed = self.invoke(
                    ['--yes'], environment={'LAB_OLDER_THAN': value})
                self.assertEqual(status, cli.EXIT_USAGE)
                self.assertIn('$LAB_OLDER_THAN', stderr)
                self.assertEqual(stdout, '')
                self.assertEqual(removed, [])


class PartialResultsTest(CliTestCase):
    ITEMS = [
        {'name': 'first', 'age_days': 3},
        {'name': 'second', 'age_days': 2},
        {'name': 'third', 'age_days': 1},
    ]

    def test_failure_preserves_completed_items_and_marks_raising_effect_unknown(self):
        for failure_at in (0, 1):
            for error_type in (cli.Failure, OSError):
                with self.subTest(failure_at=failure_at, error_type=error_type):
                    effects = []

                    # Bound as defaults, not captured: the closure is consumed in this
                    # iteration today, and a late-binding capture would silently grade a later
                    # iteration's case if that ever stopped being true.
                    def remove(name, effects=effects, failure_at=failure_at,
                               error_type=error_type):
                        effects.append(name)
                        if len(effects) == failure_at + 1:
                            # The effect happened before its acknowledgement failed.
                            raise error_type('acknowledgement lost')

                    status, stdout, stderr, _ = self.invoke(
                        ['--older-than', '0', '--yes'], items=self.ITEMS, remove=remove)
                    self.assertEqual(status, cli.EXIT_FAILURE)
                    self.assertEqual(json.loads(stdout), {
                        'applied': None,
                        'count': failure_at,
                        'items': self.ITEMS[:failure_at],
                        'complete': False,
                        'unknown': [self.ITEMS[failure_at]],
                        'not_attempted': self.ITEMS[failure_at + 1:],
                    })
                    self.assertEqual(
                        effects, [item['name'] for item in self.ITEMS[:failure_at + 1]])
                    self.assertIn('acknowledgement lost', stderr)
                    self.assertIn('outcome unknown', stderr)

    def test_human_failure_reports_confirmed_success_and_unknown_item_separately(self):
        for failure_at in (0, 1):
            with self.subTest(failure_at=failure_at):
                calls = []

                def remove(name, calls=calls, failure_at=failure_at):
                    calls.append(name)
                    if len(calls) == failure_at + 1:
                        raise cli.Failure('target unavailable')

                status, stdout, stderr, _ = self.invoke(
                    ['--older-than', '0', '--yes'], items=self.ITEMS, remove=remove, machine=False)
                self.assertEqual(status, cli.EXIT_FAILURE)
                self.assertEqual(stdout, 'deleted first (3d)\n' if failure_at else '')
                self.assertIn(self.ITEMS[failure_at]['name'], stderr)
                self.assertIn('outcome unknown', stderr)
                self.assertIn(f'{2 - failure_at} not attempted', stderr)
                self.assertEqual(calls, ['first', 'second'] if failure_at else ['first'])

    def test_debug_preserves_the_original_effect_error_as_the_cause(self):
        def remove(_name):
            raise OSError('connection lost')

        with self.assertRaises(cli.Failure) as caught:
            self.invoke(['--yes', '--debug'], remove=remove)
        self.assertIsInstance(caught.exception.__cause__, OSError)
        self.assertEqual(str(caught.exception.__cause__), 'connection lost')

    def test_success_and_dry_run_keep_the_existing_json_contract(self):
        for flags, applied in ((['--yes'], True), (['--dry-run'], False)):
            with self.subTest(applied=applied):
                status, stdout, stderr, removed = self.invoke(
                    ['--older-than', '0', *flags], items=self.ITEMS)
                self.assertEqual(status, cli.EXIT_OK, stderr)
                self.assertEqual(json.loads(stdout), {
                    'applied': applied, 'count': 3, 'items': self.ITEMS,
                })
                self.assertEqual(removed, ['first', 'second', 'third'] if applied else [])


if __name__ == '__main__':
    unittest.main()
