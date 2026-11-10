# Repository guide for coding agents

`agents/` and `skills/` are the only authored source; Codex and VS Code load adapters generated
from them. Edit the canonical file and regenerate — never a generated copy, and never a fleet file
under `~/.claude`. Read a script's docstring before you change or run it. Before you edit a
description, a hook, or the validator; add a guard or check to any fleet script; add an agent or
skill; change a validated record shape; or retire a tripwire, read the matching playbook in
`docs/fleet-development.md` under "Change playbooks". Why the fleet's disciplines exist is in
`docs/engineering-program.md`.

## Validate before you push

- **T0 — every edit:** `python3 scripts/validate_fleet.py`, the owning test module
  (`python3 -m unittest discover -s tests -p test_<area>.py`), `uvx ruff@latest check .`, and
  `uvx ruff@latest format --check fleet`. After any agent or skill edit, run
  `python3 scripts/generate_platform_adapters.py --write`; after adding, renaming, or removing one,
  also run `python3 scripts/validate_fleet.py --write-inventory`.
- **T1 — before push:** `python3 -m unittest discover -s tests` and
  `python3 scripts/validate_claude_plugin.py` (needs the Claude CLI). CI never sees the installed
  copies, so also check `claude plugin list`, `codex plugin list`, and
  `python3 scripts/install_codex_agents.py --user --check`.
- **T2:** CI (`.github/workflows/validate.yml`); nothing to run locally.
- **T3 — before a release or after a Claude CLI upgrade:** `python3 scripts/probe_plugin.py`.

Load the plugin from the working tree while editing it: `claude --plugin-dir .`.

## Opening a pull request

Topic branch and merge-commit PR, never a direct push. A canonical edit and everything it requires
(regenerated adapters, inventory, roster entry) land in the same commit. One independent review
before merge; two for changes to the guard or other authority boundaries. `CONTRIBUTING.md` owns
naming, the template, and requesting review.

## Hard rules

- **Keep isolated hooks dependency-free.** The hook runs `python -I -S`; a non-stdlib import makes the
  guard deny every scoped Bash call. `fleet/` stays standard-library too.
- **The read-only guard's allowlist grows only by readers**, never by anything that can execute a
  program. Never port the hook to Codex or VS Code.
- **Never hand-edit generated output:** `.github/agents/`, `.github/skills/`, `.codex/agents/`,
  `plugins/sde-agents/skills/`, `hooks/hooks.json`.
- **One parser per fact:** read frontmatter, `tools:`, references, and the tree snapshot through
  `fleet/`; never write a second parser.
- **Proportionality:** no check that re-proves an existing fact, no speed claim without a
  before/after on one machine, no new mechanism without a task using it now — record it in
  `docs/fleet-roadmap.md` instead.
- **Keep workflow `permissions:` at `contents: read`.**
- **One writer per checkout:** concurrent work gets its own worktree, and measurements run only on
  a tree nothing else is writing.
- **Where two files disagree, the source wins;** the ownership list is in
  `docs/fleet-development.md` under "Working on the fleet itself".

## Style

- Wrap new or edited Markdown at about 100 columns; leave untouched lines alone.
- Script comments explain *why*, not what.
- Descriptions lead with capability, then triggers, then negative routing.
