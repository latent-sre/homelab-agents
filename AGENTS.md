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
  `python3 scripts/install_codex_agents.py --user --check`; repair Codex agent drift with
  `python3 scripts/install_codex_agents.py --user`.
- **T2:** CI (`.github/workflows/validate.yml`); nothing to run locally.
- **T3 — before a release or after a Claude CLI upgrade:** `python3 scripts/probe_plugin.py`.

Load the plugin from the working tree while editing it: `claude --plugin-dir .`.

## Opening a pull request

Topic branch and merge-commit PR, never a direct push. A canonical edit and everything it requires
(regenerated adapters, inventory, roster entry) land in the same commit. One independent review
before merge; two for changes to the guard or other authority boundaries. `CONTRIBUTING.md` owns
naming, the template, and requesting review.

## Hard rules with no playbook exceptions

- **Keep isolated hooks dependency-free.** The hook runs its script with `python -I -S`, so it
  stays standard-library and never imports `fleet/`; a missing import makes the guard deny every
  scoped Bash call. `fleet/` stays standard-library too, so it can never
  become a hook import. The dev group in `pyproject.toml` is optional tooling.
- **The read-only guard's allowlist grows only by readers**, never by anything that can
  execute a program. Never port the hook to Codex or VS Code.
- **Never hand-edit generated output:** `.github/agents/`, `.github/skills/`, `.codex/agents/`,
  `plugins/sde-agents/skills/`, and `hooks/hooks.json`. `--write` overwrites it and the validator
  rejects any drift.
- **One parser per fact.** Read frontmatter, `tools:`, references, and the tree snapshot through
  `fleet/`, and use the kernel's copy of every other primitive; never write a second one.
- **Authority is the host's own control, never prose:** Claude's guard, VS Code's omitted
  `execute`, and Codex's parent-session permissions plus supported capability switches. A Codex
  custom-agent `sandbox_mode` does not override its parent's permissions.
- **Proportionality.** No check that re-proves an existing fact, no speed claim without a
  before/after on one machine, and no new mechanism without a task using it now — otherwise record
  it in `docs/fleet-roadmap.md`. Nothing enforces this.
- **One writer per checkout.** Concurrent work gets its own worktree, and measurements (evals, the
  probe, the test suite) run only on a tree nothing else is writing.
- **Read a revision as bytes:** `git show <rev>:<path>`, not the working tree.
- **Keep workflow `permissions:` at `contents: read`.** Actions float on major-version tags, so a
  moved tag must not be able to write.
- **The source wins on drift.** Where two files disagree, fix the paraphrase, or fix a real defect
  at the source and re-propagate it. The ownership list is in `docs/fleet-development.md` under
  "Working on the fleet itself".

## Style

- Wrap new or edited Markdown at about 100 columns; leave untouched lines alone.
- Script comments explain *why*, not what.
- Descriptions lead with capability, then triggers, then negative routing.
