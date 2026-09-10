#!/usr/bin/env python3
"""Clean-room support for model-driven plugin evals.

`claude -p` normally inherits personal agents, skills, plugins, settings, and CLAUDE.md. That makes
an eval describe the operator's machine rather than the plugin under test. This module relocates the
Claude configuration to a temporary directory containing only authentication material and refuses
to turn runner/auth failures into routing outcomes.

Adapted from latent-sre/sre-agents' clean-room design, with a Python 3.10-compatible cleanup path.
Source: https://github.com/latent-sre/sre-agents (MIT; Copyright 2026 SRE + SDE Agent Fleet
contributors). The repository-root LICENSE carries the MIT text; the reviewed source revision and
adaptation decision are recorded in docs/archive/2026-07/verification-round-outcomes-2026-07-29.md (retired to Git history).
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

CREDENTIALS = ".credentials.json"
AUTH_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_FOUNDRY_API_KEY",
    "ANTHROPIC_FOUNDRY_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_MANTLE",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS",
    # A managed host (Claude Code on the web, and other hosted runners) resolves credentials for
    # the CLI itself and injects them out of band — typically through an inherited file descriptor
    # that no child of this process can read. Auth genuinely works in such an environment, and it
    # works inside the room, but none of the signals above are visible, so the credential-file
    # precheck below would refuse a host that is in fact authenticated. That refusal is the wrong
    # failure: the precheck exists so an UNAUTHENTICATED trace cannot be mistaken for a valid
    # result, not to require one particular credential transport. This entry is the same exemption
    # API-key/Bedrock/Vertex users already get for needing no credential file — and it is recorded
    # under its own `auth` label rather than borrowed from theirs, so an artifact never claims a
    # credential source it did not use.
    "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST",
)
CONTAMINATING_ENV_VARS = (
    "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD",
    # Phantom in current docs (see the note in clean_env), scrubbed anyway: the room must not SET
    # it, but it must not INHERIT it either — an operator who exported it would otherwise carry an
    # undocumented variable into an environment the artifact records as clean.
    "CLAUDE_CODE_DISABLE_POLICY_SKILLS",
    "CLAUDE_CODE_ENABLE_BACKGROUND_PLUGIN_REFRESH",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
    "CLAUDE_CODE_PLUGIN_CACHE_DIR",
    "CLAUDE_CODE_PLUGIN_SEED_DIR",
    "CLAUDE_CODE_SIMPLE",
    "CLAUDE_CODE_SYNC_PLUGIN_INSTALL",
    "CLAUDE_CODE_SYNC_PLUGIN_INSTALL_TIMEOUT_MS",
    "CLAUDE_CODE_SYNC_SKILLS",
    "CLAUDE_CODE_SYNC_SKILLS_INSTALL_TIMEOUT_MS",
    "CLAUDE_CODE_SYNC_SKILLS_WAIT_TIMEOUT_MS",
    "CLAUDE_CODE_TASK_LIST_ID",
    "CLAUDE_CODE_TEAM_NAME",
)
AUTH_MARKERS = (
    "authentication_failed",
    "not logged in",
    "failed to authenticate",
    "oauth session expired",
)

PROVIDER_ENV_VARS = {
    "bedrock": ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_ANTHROPIC_AWS"),
    "vertex": ("CLAUDE_CODE_USE_VERTEX",),
    "foundry": (
        "CLAUDE_CODE_USE_FOUNDRY",
        "ANTHROPIC_FOUNDRY_API_KEY",
        "ANTHROPIC_FOUNDRY_AUTH_TOKEN",
    ),
    "mantle": ("CLAUDE_CODE_USE_MANTLE",),
}


class AuthUnavailable(RuntimeError):
    """The harness cannot authenticate and therefore cannot produce a measurement."""


def user_config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


def has_environment_auth() -> bool:
    return any(os.environ.get(name) for name in AUTH_ENV_VARS)


def auth_provider_mode(env: dict[str, str] | None = None, *, clean_room: bool = False) -> dict:
    """Describe authentication/provider selection without copying credential values.

    This is measurement metadata, not an authentication preflight. Claude can resolve credentials
    inside its own configuration or a cloud provider chain, so an absent environment signal is
    deliberately labeled rather than guessed. Multiple provider selectors are surfaced as
    ambiguous instead of silently choosing one.
    """
    environment = os.environ if env is None else env
    providers = sorted(
        provider
        for provider, names in PROVIDER_ENV_VARS.items()
        if any(environment.get(name) for name in names)
    )
    provider = providers[0] if len(providers) == 1 else (
        "anthropic" if not providers else f"ambiguous:{','.join(providers)}"
    )

    if any(environment.get(name) for name in (
        "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_REFRESH_TOKEN"
    )):
        auth = "oauth-token-env"
    elif any(environment.get(name) for name in (
        "ANTHROPIC_API_KEY", "ANTHROPIC_FOUNDRY_API_KEY"
    )):
        auth = "api-key-env"
    elif any(environment.get(name) for name in (
        "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_FOUNDRY_AUTH_TOKEN"
    )):
        auth = "auth-token-env"
    elif providers:
        auth = "provider-chain-env"
    elif environment.get("CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"):
        # Ranked below every explicit signal, provider selectors included: an exported key, token, or
        # Bedrock/Vertex/Foundry selector says what the session actually authenticated with, while
        # the host flag only says the host COULD supply something. Ranking it above the provider
        # chain produced the one thing this function exists to prevent — a record whose `auth`
        # contradicts its own `provider`, e.g. provider "bedrock" labelled "host-managed-provider".
        auth = "host-managed-provider"
    elif clean_room:
        auth = "credentials-file-copy"
    else:
        auth = "cli-config-or-platform-chain"
    return {"provider": provider, "auth": auth}


def require_credentials() -> Path:
    credentials = user_config_dir() / CREDENTIALS
    if not credentials.is_file():
        raise AuthUnavailable(
            f"no Claude credentials at {credentials}. The clean room refuses to run because an "
            "unauthenticated trace can look like a valid no-route result. Run `claude` and /login, "
            "set an API-key/Bedrock/Vertex auth variable, or point CLAUDE_CONFIG_DIR at a logged-in "
            "configuration directory."
        )
    return credentials


def _warn_cleanup(function, path, exc_info) -> None:
    detail = exc_info[1] if isinstance(exc_info, tuple) else exc_info
    print(
        f"eval_clean_room: WARNING: could not remove {path} ({function.__name__}: {detail}). "
        "The directory may contain a copy of Claude credentials; remove it manually.",
        file=sys.stderr,
    )


@contextlib.contextmanager
def clean_env():
    """Yield an environment isolated from personal Claude configuration.

    API-key/Bedrock/Vertex users need no credential file. Subscription users get a permission-
    restricted copy of only `.credentials.json`; skills, agents, plugins, settings, and CLAUDE.md
    are intentionally not copied.
    """
    credentials = None if has_environment_auth() else require_credentials()
    room = Path(tempfile.mkdtemp(prefix="sde-agents-cleanroom-"))
    try:
        os.chmod(room, stat.S_IRWXU)
        if credentials is not None:
            destination = room / CREDENTIALS
            shutil.copyfile(credentials, destination)
            os.chmod(destination, stat.S_IRUSR | stat.S_IWUSR)
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(room))
        for name in CONTAMINATING_ENV_VARS:
            env.pop(name, None)
        # The branch this was salvaged from also set CLAUDE_CODE_DISABLE_POLICY_SKILLS=1 here.
        # Verified against current docs (2026-07-29, CLI 2.1.220): no such variable exists — the
        # documented neighbor is CLAUDE_CODE_DISABLE_BUNDLED_SKILLS (v2.1.169), which disables the
        # CLI's OWN built-in skills. That is a different measurement condition (every existing
        # baseline ran with built-ins present), so it is deliberately not set: a knob that changes
        # comparability belongs in a conditions block, not silently inside the room. Setting the
        # phantom name would have shipped isolation that reads as armor and is nothing.
        env["CLAUDE_CODE_SKIP_PROMPT_HISTORY"] = "1"
        yield env
    finally:
        # onerror works on the repository's existing Python floor; upstream's onexc requires 3.12.
        shutil.rmtree(room, onerror=_warn_cleanup)


def result_event(transcript: str) -> dict | None:
    """Return the final structured CLI result event, if one was emitted."""
    result = None
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            result = event
    return result


def raise_if_auth_failed(transcript: str, returncode: int, stderr: str = "") -> None:
    """Raise AuthUnavailable when this failed CLI run carries an authentication signature.

    Authentication classification stays separate from runner completion policy so routing can
    retain its intentional measurement case: a non-error result event paired with a non-zero CLI
    exit. It keys off the run's own stream; a separate auth-status preflight can be stale relative
    to the API request.
    """
    event = result_event(transcript)
    # Routing deliberately keeps a completed, non-error result as a measurement even when the CLI
    # process exits non-zero afterward. Do not reclassify the model's successful result text or
    # accompanying stderr as an auth outage merely because those strings mention authentication.
    if event is not None and not event.get("is_error"):
        return
    evidence = "\n".join((json.dumps(event or {}), stderr or "", transcript or "")).casefold()
    if any(marker in evidence for marker in AUTH_MARKERS):
        raise AuthUnavailable("Claude authentication failed during the eval; refresh /login and rerun")
