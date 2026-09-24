# Decision: CI floats its toolchain instead of pinning it

**Status:** Accepted 2026-09-23 (operator ruling).

## What was decided

CI stops pinning three things:

- **The Claude Code CLI** in the `claude-plugin-contract` job installs `@latest` and stays a
  gating check. The job prints the version it tested, so a red run names the release that
  caused it.
- **ruff** installs unversioned in CI and is unpinned in `pyproject.toml`'s dev group. The lint
  gate is whatever the current release enforces.
- **Third-party GitHub Actions** are referenced by major version tag (`actions/checkout@v7`,
  `actions/setup-python@v7`) instead of a full commit SHA.

The other dev-group pins (`pytest`, `pyyaml`, `hypothesis`) are unchanged; the ruling named only
these three.

## Why

The pinned CLI lagged the one the operator runs (2.1.270 against 2.1.281 on the day of the
ruling). It also blocked the first new agent field — `omitClaudeMd` arrived in 2.1.271 — from being
tested by the job that exists to catch platform contract breaks. A pin tests an old CLI
thoroughly; the plugin ships to people running the new one.

## What lost

- **Hermetic CI.** An upstream release can turn a PR red without any change in the PR. Read the
  job's logged CLI or ruff version before debugging the diff.
- **The pin-bump trigger for the probe.** `scripts/probe_plugin.py` was owed at every CLI pin bump.
  With no pin, it is owed before every release instead, and after any red contract run that a new
  CLI release caused.
- **Supply-chain immutability for Actions.** A major tag can be moved by its upstream owner, so a
  compromised or careless release runs in this repository's CI. The workflow keeps
  `permissions: contents: read`, which caps what such a release can do with the job token. The
  fleet's own guidance for other repositories (`sde-agents:code-reviewer`, `sde-agents:ci-actions`)
  still recommends full-SHA pins; this ruling is a risk this repository accepts for itself.

## What would reopen this

An upstream CLI, ruff, or Action release that breaks CI more than once in a month, or any
security incident traced to a moved tag. Reopening restores the pins from Git history; nothing here
is one-way.
