# Repository guide for coding agents

`agents/` and `skills/` are the only authored source. Claude Code loads them directly; Codex and
VS Code load adapters generated from them. Edit the canonical file and regenerate — never a
generated copy, and never a fleet file under `~/.claude`, which no check sees and the next
reinstall replaces (`README.md` owns install detail). Read a script's docstring before you change
or run it. Why the fleet's disciplines exist is in `docs/engineering-program.md`.

## Validate before you push

- **T0 — every edit:** `python3 scripts/validate_fleet.py` (it also byte-checks every generated
  adapter), the owning test module (`python3 -m unittest discover -s tests -p test_<area>.py`),
  `uvx ruff@latest check .`, and `uvx ruff@latest format --check fleet`. Run both ruff commands:
  CI runs both on the latest ruff, and `check` passes code `format` would rewrite. After any agent
  or skill edit, run `python3 scripts/generate_platform_adapters.py --write`; after adding,
  renaming, or removing one, also run `python3 scripts/validate_fleet.py --write-inventory`.
- **T1 — before push:** `python3 -m unittest discover -s tests` and
  `python3 scripts/validate_claude_plugin.py` (needs the Claude CLI; exits 2 without it). Then
  check the installed copies, which CI never sees: `claude plugin list` and `codex plugin list`
  (is sde-agents installed and enabled?) and `python3 scripts/install_codex_agents.py --user
  --check`; repair Codex agent drift with `python3 scripts/install_codex_agents.py --user`.
- **T2:** CI on Windows (`.github/workflows/validate.yml`) runs on every PR, push to main, and
  weekly; nothing to run locally.
- **T3 — before a release or after a Claude CLI upgrade:** `python3 scripts/probe_plugin.py`.

Load the plugin from the working tree while editing it: `claude --plugin-dir .` (`README.md`
covers the VS Code and Codex loops).

## Change playbooks

**Editing a description** — descriptions drive routing and nothing measures it: try the requests
the edit should and should not catch in a fresh `claude --plugin-dir .` session before and after.

**Touching a Claude hook** (`scripts/readonly-guard.py`, or the shell template in
`fleet/hooks.py`) — read the guard's docstring first, then run the tests and the probe. The roster
changes in the script constant and reaches `hooks/hooks.json` only through `--write`. The guard's
allowlist grows only by readers, never by anything that can execute a program. Never port the hook
to Codex or VS Code: their `PreToolUse` payload has no agent identity to scope on. Keep it out
structurally — no file at that host's hook-config path, hence no `hooks/` under
`plugins/sde-agents/`; a manifest override does not do it.

**Changing validator behavior** — `scripts/validate_fleet.py` holds only checks for failures Claude
Code ignores silently; vocabularies are the constants at its top. Land a check with a test in
`tests/test_validate_fleet.py` that breaks the clean baseline tree in exactly that way.

**Adding a guard or check to a fleet script** — land a test that makes it fire, or prove it by
mutation. Do not call something "enforced" in prose unless a check stands behind it. A diagnostic
that names an external authority compares against a value obtained from that authority, never a
copy the checked party wrote.

Rarer work — adding an agent or skill, changing a validated record shape, retiring a tripwire —
is in `docs/fleet-development.md` under "Change playbooks for less frequent
work".

## Opening a pull request

Work lands on the default branch through a topic branch and a merge-commit PR, never a direct
push. A canonical edit and everything it requires (regenerated adapters, inventory, a roster
entry) land in the same commit. Get one independent review before merge, and a second for changes
to the guard or other authority boundaries. `CONTRIBUTING.md` owns branch and commit naming
(Conventional Commits), the PR template, and requesting review.

## Hard rules with no playbook exceptions

- **Keep isolated hooks dependency-free.** The hook runs its script with `python -I -S`, so it
  stays standard-library and never imports `fleet/`; a missing import makes the guard deny every
  scoped Bash call. `fleet/` stays standard-library too, so it can never
  become a hook import. The dev group in `pyproject.toml` is optional tooling.
- **Never hand-edit generated output:** `.github/agents/`, `.github/skills/`, `.codex/agents/`,
  `plugins/sde-agents/skills/`, and `hooks/hooks.json`. `--write` overwrites it and the validator
  rejects any drift.
- **One parser per fact.** Read frontmatter, `tools:`, references, and the tree snapshot through
  `fleet/`, and use the kernel's copy of every other primitive; never write a second one.
- **Authority is the host's own control, never prose:** Claude's guard, VS Code's omitted
  `execute`, Codex's `sandbox_mode`.
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
- Script comments explain *why* an invariant exists, not what the next line does.
- Descriptions lead with capability, then triggers, then negative routing.
- In human-facing updates, name a commit by its title; add a short ID
  (`git rev-parse --short=12 <rev>`) only when the exact revision matters.
