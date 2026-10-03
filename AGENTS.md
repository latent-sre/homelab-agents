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
- **T1 — before push:** `python3 -m unittest discover -s tests`,
  `python3 scripts/validate_claude_plugin.py` (needs the Claude CLI; exits 2 without it), and
  `python3 scripts/fleet_doctor.py`, which CI never runs. Exit codes: 1 failed, 2 not computed,
  3 warnings. Repair Codex agent drift with `python3 scripts/install_codex_agents.py --user`.
- **T2:** CI's three-OS matrix (`.github/workflows/validate.yml`); nothing to run locally.
- **T3 — before a release or after a Claude CLI upgrade:** `python3 scripts/probe_plugin.py` and
  every routing cluster in `evals/routing/`, before and after.

Load the plugin from the working tree while editing it: `claude --plugin-dir .` (`README.md`
covers the VS Code and Codex loops).

## Change playbooks

**Editing a description** — descriptions drive routing, so run the overlapping cluster in
`evals/routing/` before and after and compare the rates; `evals/README.md` owns how runs are
compared.

**Touching a Claude hook** (`scripts/readonly-guard.py`, `scripts/live-effect-gate.py`, or the
shell template in `fleet/hooks.py`) — read both docstrings first, then run the tests and the
probe. Rosters change in the script constants and reach `hooks/hooks.json` only through `--write`;
an agent is on one roster or neither. The guard's allowlist grows only by readers, never by
anything that can execute a program; the gate's roster grows only by a live effect an incident or
drill showed, never by exemption. Never port either hook to Codex or VS Code: their `PreToolUse`
payload has no agent identity to scope on. Keep them out structurally — no file at that host's
hook-config path, hence no `hooks/` under `plugins/sde-agents/`; a manifest override does not do
it.

**Changing validator behavior** — a rule is a pure function in `fleet/rules/` with a stable id and
a one-line why; vocabularies live in `fleet/policy.toml`. Land it with a fixture under
`tests/fixtures/` or a mutation test that fails without it.

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
to the guard, the gate, or other authority boundaries. `CONTRIBUTING.md` owns branch naming, the
PR template, and requesting review.

## Hard rules with no playbook exceptions

- **Keep isolated hooks dependency-free.** The hooks run their scripts with `python -I -S`, so
  both stay standard-library and never import `fleet/`; a missing import makes the guard deny, and
  the gate ask or deny, every scoped Bash call. `fleet/` stays standard-library too, so it can never
  become a hook import. The dev group in `pyproject.toml` is optional tooling.
- **Never hand-edit generated output:** `.github/agents/`, `.github/skills/`, `.codex/agents/`,
  `plugins/sde-agents/skills/`, and `hooks/hooks.json`. `--write` overwrites it and the validator
  rejects any drift.
- **One parser per fact.** Read frontmatter, `tools:`, references, and the tree snapshot through
  `fleet/` (re-exported by `scripts/fleet_records.py`), and use the kernel's copy of every other
  primitive; never write a second one.
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
