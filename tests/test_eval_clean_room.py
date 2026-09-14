"""Offline tests for scripts/eval_clean_room.py."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import eval_clean_room


class CleanEnvironmentTest(unittest.TestCase):
    def _config(self, root: Path) -> Path:
        config = root / "config"
        (config / "skills" / "personal").mkdir(parents=True)
        (config / "agents").mkdir()
        (config / "plugins").mkdir()
        (config / "CLAUDE.md").write_text("personal instructions", encoding="utf-8")
        (config / eval_clean_room.CREDENTIALS).write_text(
            '{"token":"test-secret"}', encoding="utf-8"
        )
        return config

    def test_clean_room_copies_only_credentials_and_removes_itself(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            config = self._config(Path(root))
            room = None
            with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(config)}, clear=False):
                # Without this the assertion silently inverts on any machine that exports
                # ANTHROPIC_API_KEY: environment auth skips the credential copy, so the room is
                # empty and the test stops covering the copy path it exists to cover.
                for key in eval_clean_room.AUTH_ENV_VARS:
                    os.environ.pop(key, None)
                with eval_clean_room.clean_env() as env:
                    room = Path(env["CLAUDE_CONFIG_DIR"])
                    self.assertEqual(
                        [eval_clean_room.CREDENTIALS], [p.name for p in room.iterdir()]
                    )
                    self.assertEqual(
                        '{"token":"test-secret"}',
                        (room / eval_clean_room.CREDENTIALS).read_text(encoding="utf-8"),
                    )
                    self.assertFalse((room / "skills").exists())
                    self.assertFalse((room / "agents").exists())
                    self.assertFalse((room / "plugins").exists())
                    self.assertFalse((room / "CLAUDE.md").exists())
            self.assertIsNotNone(room)
            self.assertFalse(room.exists())

    def test_missing_credentials_refuses_instead_of_creating_fake_no_route(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(
                os.environ,
                {"CLAUDE_CONFIG_DIR": root},
                clear=False,
            ):
                for key in eval_clean_room.AUTH_ENV_VARS:
                    os.environ.pop(key, None)
                with self.assertRaises(eval_clean_room.AuthUnavailable):
                    with eval_clean_room.clean_env():
                        pass

    def test_api_key_auth_uses_empty_isolated_config(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(
                os.environ,
                {"CLAUDE_CONFIG_DIR": root, "ANTHROPIC_API_KEY": "test-not-real"},
                clear=False,
            ):
                with eval_clean_room.clean_env() as env:
                    room = Path(env["CLAUDE_CONFIG_DIR"])
                    self.assertEqual([], list(room.iterdir()))

    def test_oauth_token_is_a_supported_clean_room_auth_source(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(
                os.environ,
                {"CLAUDE_CONFIG_DIR": root, "CLAUDE_CODE_OAUTH_TOKEN": "test-not-real"},
                clear=False,
            ):
                with eval_clean_room.clean_env() as env:
                    self.assertEqual("test-not-real", env["CLAUDE_CODE_OAUTH_TOKEN"])

    def test_personal_skill_and_plugin_sync_environment_is_scrubbed(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(
                os.environ,
                {
                    "CLAUDE_CONFIG_DIR": root,
                    "ANTHROPIC_API_KEY": "test-not-real",
                    "CLAUDE_CODE_SYNC_SKILLS": "1",
                    "CLAUDE_CODE_PLUGIN_SEED_DIR": "/personal/plugins",
                    "CLAUDE_CODE_DISABLE_POLICY_SKILLS": "1",
                },
                clear=False,
            ):
                with eval_clean_room.clean_env() as env:
                    self.assertNotIn("CLAUDE_CODE_SYNC_SKILLS", env)
                    self.assertNotIn("CLAUDE_CODE_PLUGIN_SEED_DIR", env)
                    # The salvage source set CLAUDE_CODE_DISABLE_POLICY_SKILLS here; that variable
                    # exists in no current documentation, so the room must NOT set it — and must
                    # scrub an externally exported copy, or the phantom leaks in via inheritance.
                    self.assertNotIn("CLAUDE_CODE_DISABLE_POLICY_SKILLS", env)
                    self.assertEqual("1", env["CLAUDE_CODE_SKIP_PROMPT_HISTORY"])

    def test_auth_provider_mode_records_kind_without_secret_value(self) -> None:
        mode = eval_clean_room.auth_provider_mode({
            "ANTHROPIC_API_KEY": "test-super-secret",
            "CLAUDE_CODE_USE_VERTEX": "1",
        })
        self.assertEqual({"provider": "vertex", "auth": "api-key-env"}, mode)
        self.assertNotIn("test-super-secret", json.dumps(mode))

    def test_clean_room_without_environment_auth_records_credential_copy(self) -> None:
        self.assertEqual(
            {"provider": "anthropic", "auth": "credentials-file-copy"},
            eval_clean_room.auth_provider_mode({}, clean_room=True),
        )

    def test_host_managed_provider_runs_without_a_credential_file(self) -> None:
        """A managed host authenticates the CLI out of band; refusing it measures nothing.

        The risk this covers is the inverse of the refusal path above: on Claude Code on the web
        and similar hosted runners the token arrives through an inherited descriptor no child can
        read, so every visible auth signal is absent while sessions authenticate normally. Without
        this branch the room refuses on a host that is authenticated, and the whole behavioral
        suite is unrunnable there for a reason that has nothing to do with authentication.
        """
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(
                os.environ,
                {"CLAUDE_CONFIG_DIR": root, "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST": "1"},
                clear=False,
            ):
                for key in eval_clean_room.AUTH_ENV_VARS:
                    if key != "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST":
                        os.environ.pop(key, None)
                with eval_clean_room.clean_env() as env:
                    room = Path(env["CLAUDE_CONFIG_DIR"])
                    # No credential file exists to copy, and none is invented.
                    self.assertEqual([], list(room.iterdir()))
                    self.assertEqual("1", env["CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"])

    def test_host_managed_provider_is_recorded_under_its_own_auth_label(self) -> None:
        """The artifact must not claim a credential source the session did not use."""
        self.assertEqual(
            {"provider": "anthropic", "auth": "host-managed-provider"},
            eval_clean_room.auth_provider_mode({"CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST": "1"}),
        )
        # Ranked below every explicit credential: an exported key is what the session actually
        # used, so the host flag must not mask it.
        self.assertEqual(
            {"provider": "anthropic", "auth": "api-key-env"},
            eval_clean_room.auth_provider_mode({
                "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST": "1",
                "ANTHROPIC_API_KEY": "test-not-real",
            }),
        )
        # An unset/empty flag is not a host-managed session, and must still reach the refusal path.
        self.assertEqual(
            {"provider": "anthropic", "auth": "cli-config-or-platform-chain"},
            eval_clean_room.auth_provider_mode({"CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST": ""}),
        )

    def test_explicit_provider_selector_outranks_the_host_marker(self) -> None:
        """An `auth` label must never contradict the `provider` it is recorded beside.

        A cloud host can set both a provider selector and the managed-host marker. Ranking the
        marker first produced records like provider "bedrock" with auth "host-managed-provider" —
        self-contradictory provenance, and exactly the mislabelling this function exists to
        prevent. The selectors are already environment auth, so they describe what the session
        actually authenticated with; the host flag only says the host could supply something.
        """
        for selector, provider in (
            ("CLAUDE_CODE_USE_BEDROCK", "bedrock"),
            ("CLAUDE_CODE_USE_VERTEX", "vertex"),
            ("CLAUDE_CODE_USE_FOUNDRY", "foundry"),
        ):
            with self.subTest(selector=selector):
                self.assertEqual(
                    {"provider": provider, "auth": "provider-chain-env"},
                    eval_clean_room.auth_provider_mode({
                        selector: "1",
                        "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST": "1",
                    }),
                )


class AuthenticationFailureClassificationTest(unittest.TestCase):
    def test_stderr_only_auth_failure_is_unavailable_case_insensitively(self) -> None:
        with self.assertRaises(eval_clean_room.AuthUnavailable):
            eval_clean_room.raise_if_auth_failed(
                "", "NOT LOGGED IN · PLEASE RUN /LOGIN"
            )

    def test_resultless_transcript_auth_failure_is_unavailable(self) -> None:
        transcript = '{"type":"system","subtype":"authentication_failed"}'

        with self.assertRaises(eval_clean_room.AuthUnavailable):
            eval_clean_room.raise_if_auth_failed(transcript)


if __name__ == "__main__":
    unittest.main()
