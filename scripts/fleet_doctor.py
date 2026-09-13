#!/usr/bin/env python3
"""Report fleet repository and host-installation health without changing either.

The doctor is intentionally narrower than an installer or repair command. It reads repository
state, validates generated adapters and manifests in memory, asks installed CLIs only for version
and plugin-list information, and reports drift. It never generates, installs, fetches, prunes, or
runs a model session.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

# Importing repository helpers would otherwise create `scripts/__pycache__` in a clean checkout,
# violating the doctor's read-only contract before its first check ran.
sys.dont_write_bytecode = True

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)  # `import fleet` when run as `python3 scripts/<name>.py`

from fleet import diagnostics as _diagnostics  # noqa: E402
from fleet import proc as _proc  # noqa: E402

try:
    from scripts import (
        fleet_records,
        generate_platform_adapters,
        install_codex_agents,
        validate_fleet,
    )
except ModuleNotFoundError:
    import fleet_records  # type: ignore[no-redef]
    import generate_platform_adapters  # type: ignore[no-redef]
    import install_codex_agents  # type: ignore[no-redef]
    import validate_fleet  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parent.parent
STATUSES = ("pass", "warn", "fail", "skip", "inconclusive")


# The kernel's result, not a second one. This module used to keep its own three-field copy and
# downgrade into it, which collapsed "the CLI timed out" and "the CLI is not installed" into a
# single returncode 127 -- two different things for the operator to do, reported identically. One
# type per fact (AGENTS.md); `ok` is the read every check below wants, because a timed-out result
# carries returncode None, and `if result.returncode:` would call that a success.
CommandResult = _proc.CommandResult


@dataclass(frozen=True)
class Check:
    check_id: str
    status: str
    summary: str
    details: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"unknown fleet-doctor status: {self.status}")


CommandRunner = Callable[[Sequence[str]], CommandResult]
Which = Callable[[str], str | None]


def _command_name(executable: str) -> str:
    return Path(executable).stem.lower()


def _assert_read_only_command(argv: Sequence[str]) -> None:
    """Reject command drift before subprocess execution can acquire mutation authority."""

    if not argv:
        raise ValueError("empty command")
    name = _command_name(argv[0])
    tail = tuple(argv[1:])
    allowed = (
        name == "git"
        and len(tail) >= 5
        and tail[:2] == ("--no-optional-locks", "-C")
        and tuple(tail[3:]) in {("rev-parse", "HEAD"), ("status", "--short")}
    ) or (name in {"claude", "codex"} and tail in {("--version",), ("plugin", "list")})
    allowed = allowed or (name == "code" and tail == ("--version",))
    if not allowed:
        raise ValueError(
            "fleet doctor refused a command outside its read-only allowlist: "
            + repr(list(argv))
        )


def _run_read_only(argv: Sequence[str]) -> CommandResult:
    _assert_read_only_command(argv)
    return _proc.run(argv, timeout=30)


def _failure_details(result: CommandResult) -> dict[str, object]:
    """What the operator needs to choose between retrying and repairing the installation.

    `stderr` alone is empty for both of the failures this module keeps apart -- a timeout and a
    binary that never started put their cause in `error`, not on the stream -- so reporting only
    stderr produced an identical empty diagnostic for each and defeated the point of holding the
    kernel's richer result (Codex, PR #190). The flags are included so a reader of the JSON does
    not have to infer the kind from prose.
    """
    details: dict[str, object] = {"stderr": result.stderr.strip()}
    if result.error:
        details["error"] = result.error
    if result.timed_out:
        details["timed_out"] = True
    if result.failed_to_start:
        details["failed_to_start"] = True
    return details


def _git_checks(root: Path, run: CommandRunner) -> list[Check]:
    head = run(("git", "--no-optional-locks", "-C", str(root), "rev-parse", "HEAD"))
    if not head.ok:
        return [
            Check(
                "repository.git",
                "inconclusive",
                "Git could not identify the repository revision.",
                _failure_details(head),
            )
        ]

    checks = [
        Check(
            "repository.git",
            "pass",
            "Git repository revision identified.",
            {"revision": head.stdout.strip()},
        )
    ]
    status = run(("git", "--no-optional-locks", "-C", str(root), "status", "--short"))
    if not status.ok:
        checks.append(
            Check(
                "repository.worktree",
                "inconclusive",
                "Git could not inspect worktree state.",
                {"stderr": status.stderr.strip()},
            )
        )
    elif status.stdout.strip():
        checks.append(
            Check(
                "repository.worktree",
                "warn",
                "The worktree contains local changes; results describe this exact working tree.",
                {"entries": status.stdout.splitlines()},
            )
        )
    else:
        checks.append(Check("repository.worktree", "pass", "The worktree is clean."))
    return checks


# The skill listing sent to the model is budgeted in CHARACTERS: context-window tokens x 4
# chars/token x `skillListingBudgetFraction` (default 0.01) -- exactly 8,000 on a 200k-token
# Claude model under those settings. This estimate does not measure the active host's catalog. Over
# budget, Claude Code does not drop a skill; it silently degrades plugin entries to bare
# `- name` lines with no description (bundled skills are exempt and charge the budget first),
# independently of Codex's token-based catalog budget. Probed on Claude CLI 2.1.233: binary constants
# (fraction 0.01, 4 chars/token, 200k default window, 1536-char per-description cap) plus live
# headless sessions -- a 200k-window model rendered 18 of this fleet's 19 entries name-only
# while larger-window models rendered all of them in full. The failure is silent at runtime:
# description-driven skill routing simply stops, and nothing in a session says so.
_SKILL_LISTING_BUDGET_CHARS = 8000
_SKILL_LISTING_MAX_DESC_CHARS = 1536


def _workflow_listing_entries(root: Path, plugin_name: str) -> tuple[list[tuple[str, str]], list[str]]:
    """((name, description) entries, unextractable-file paths) for workflows/*.js meta literals.

    Workflows appear in the model's skill listing exactly like skills (observed live on CLI
    2.1.233: `- sde-agents:deep-review: <meta description>`), so a budget sum that skipped them
    would under-report by each workflow's full entry. String spans are located on the
    validator's blanked text -- quotes survive blanking while contents (including escaped
    quotes) do not -- so the first matching close quote is the real end of the literal, and the
    raw slice between the quotes is the description as the runtime reads it.
    """
    entries: list[tuple[str, str]] = []
    failed: list[str] = []
    workflows_dir = root / "workflows"
    if not workflows_dir.is_dir():
        return entries, failed
    for path in sorted(workflows_dir.glob("*.js")):
        text = path.read_text(encoding="utf-8")
        blanked = validate_fleet._blank_js_strings_and_comments(text)
        # Bound the search to the meta object's TOP LEVEL. An unscoped file-wide regex would take
        # whichever `description:` appears first — a nested `phases: [{description: 'tiny'}]` or
        # a schema constant later in the body — and silently undercount the listing by the whole
        # real entry (PR #141 round-2 finding). Blanked text has no braces inside strings, so
        # brace depth is reliable.
        fields: dict[str, str] = {}
        declaration = validate_fleet._META_DECLARATION_RE.search(blanked)
        if declaration is not None:
            open_index = declaration.end() - 1
            depth = 0
            close_index = None
            for index in range(open_index, len(blanked)):
                if blanked[index] in "{[":
                    depth += 1
                elif blanked[index] in "}]":
                    depth -= 1
                    if depth == 0:
                        close_index = index
                        break
            if close_index is not None:
                meta_blanked = blanked[open_index + 1 : close_index]
                for key in ("name", "description"):
                    for match in re.finditer(rf"\b{key}\s*:\s*(['\"`])", meta_blanked):
                        prefix = meta_blanked[: match.start()]
                        if prefix.count("{") + prefix.count("[") != prefix.count(
                            "}"
                        ) + prefix.count("]"):
                            continue  # nested inside phases/args/etc., not the listing field
                        end = meta_blanked.find(match.group(1), match.end())
                        if end == -1:
                            break
                        start = open_index + 1 + match.end()
                        fields[key] = text[start : open_index + 1 + end]
                        break
        if "description" in fields:
            entries.append((fields.get("name", path.stem), fields["description"]))
        else:
            # workflows/ is auto-discovered, so every .js here IS a listed workflow and its meta
            # must carry a description. Skipping it would shrink the sum toward a false pass —
            # the caller turns this into an inconclusive verdict, never a smaller total.
            failed.append(path.relative_to(root).as_posix())
    return entries, failed


def _skill_listing_budget_check(root: Path) -> Check:
    try:
        manifest = json.loads(
            (root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        if not isinstance(manifest, dict):
            # json.loads happily returns a list/string/null, and the name lookup below would
            # raise TypeError — outside the except clause — exactly when the manifest is
            # damaged. Same documented inconclusive path as the non-string name.
            raise ValueError(
                ".claude-plugin/plugin.json root is not an object: "
                f"{type(manifest).__name__}"
            )
        plugin_name = manifest["name"]
        if not isinstance(plugin_name, str) or not plugin_name:
            # A non-string name would raise TypeError five frames deep in fleet_records and
            # print a traceback exactly when the manifest is damaged; make it the documented
            # inconclusive path instead.
            raise ValueError(
                ".claude-plugin/plugin.json 'name' is not a non-empty string: "
                f"{plugin_name!r}"
            )
        records = fleet_records.collect(root)
        unreadable = sorted(
            path.relative_to(root).as_posix()
            for path in records.unparseable
            if path.name == "SKILL.md"
        )
        listed: list[tuple[str, str]] = []
        dmi_chars = 0
        for member in records.members:
            if member.kind != "skill":
                continue
            entry_cost = len(f"- {plugin_name}:{member.name}: ") + min(
                len(member.description), _SKILL_LISTING_MAX_DESC_CHARS
            )
            # disable-model-invocation removes the entry from the model's listing (absence
            # verified live on CLI 2.1.233), so it costs the budget nothing THERE — but CLIs of
            # the 2.1.212 era listed flagged plugin skills anyway, so the excluded cost is
            # reported rather than dropped: headroom on those hosts must cover it.
            if member.fields.get("disable-model-invocation", "").strip().lower() == "true":
                dmi_chars += entry_cost
                continue
            listed.append((member.name, member.description))
        workflow_entries, workflow_failed = _workflow_listing_entries(root, plugin_name)
        listed.extend(workflow_entries)
        unreadable += workflow_failed
    except (OSError, ValueError, KeyError) as exc:
        return Check(
            "repository.skill-listing-budget",
            "inconclusive",
            "The model-visible skill listing could not be computed.",
            {"error": str(exc)},
        )
    if unreadable:
        # An unparseable definition is omitted from the sum, so any verdict computed over the
        # remainder would report headroom the model does not have. No verdict beats a wrong one.
        return Check(
            "repository.skill-listing-budget",
            "inconclusive",
            f"{len(unreadable)} skill/workflow definition(s) could not be parsed, so the "
            f"listing sum would be an undercount and any pass would claim fictitious headroom.",
            {"unreadable": unreadable},
        )
    # A list, not a dict: skills and workflow metas share this namespace, and keying a dict by
    # name would let a collision silently overwrite one entry — an undercount toward a false
    # pass, the direction every other branch of this check refuses. The model's listing shows
    # both colliding entries, so the sum counts both.
    entry_lengths = [
        (
            f"{plugin_name}:{name}",
            len(f"- {plugin_name}:{name}: ")
            + min(len(description), _SKILL_LISTING_MAX_DESC_CHARS),
        )
        for name, description in listed
    ]
    total = sum(length for _, length in entry_lengths) + max(0, len(entry_lengths) - 1)
    over = total > _SKILL_LISTING_BUDGET_CHARS
    largest = sorted(entry_lengths, key=lambda item: -item[1])[:3]
    details = {
        "host": "claude",
        "assumed_context_window_tokens": 200000,
        "observed_host_listing": False,
        "total_chars": total,
        "budget_chars": _SKILL_LISTING_BUDGET_CHARS,
        "entries": len(entry_lengths),
        "largest_entries": [f"{name} ({length} chars)" for name, length in largest],
        "dmi_excluded_chars": dmi_chars,
    }
    headroom = _SKILL_LISTING_BUDGET_CHARS - total
    legacy_over = bool(dmi_chars and not over and dmi_chars > headroom)
    details["legacy_dmi_over_headroom"] = legacy_over
    dmi_note = ""
    if dmi_chars:
        dmi_note = (
            f" Headroom excludes {dmi_chars} chars of disable-model-invocation entries that "
            f"pre-2.1.233 CLIs still list"
            + (
                " — which exceeds the remaining headroom, so those hosts are over budget "
                "despite this pass."
                if legacy_over
                else "."
            )
        )
    # The 8,000 figure is the FLEET's worst-case allowance, not the host's: bundled skills are
    # budget-exempt and charged first, and their share varies by environment (measured ~5.5-6k
    # chars in one container), so a pass here is necessary, never sufficient, for full survival
    # on a given 200k-context host. The doctor runs no model session by contract, so the host's
    # actual bundled share is unobservable here — a live listing probe on the target host is the
    # sufficiency check.
    shared_note = (
        " Budget is shared with budget-exempt bundled skills charged first, so this is the "
        "fleet's own footprint only — a live listing probe on the target host is the "
        "sufficiency check. The active host's context and settings were not measured."
    )
    return Check(
        "repository.skill-listing-budget",
        "warn" if over else "pass",
        (
            f"Estimated Claude skill listing is ~{total} chars for {len(entry_lengths)} entries, "
            f"over the assumed {_SKILL_LISTING_BUDGET_CHARS}-char budget at 200k context -- "
            f"over-budget entries can degrade to bare names under those settings. The active "
            f"host's context and settings were not measured. Trim the "
            f"largest descriptions, or raise skillListingBudgetFraction in the consuming "
            f"repository's settings."
            if over
            else f"Estimated Claude skill listing is ~{total} chars for {len(entry_lengths)} "
            f"entries, within the {_SKILL_LISTING_BUDGET_CHARS}-char worst-case budget "
            f"({headroom} chars of headroom).{shared_note}{dmi_note}"
        ),
        details,
    )


def _repository_checks(root: Path) -> list[Check]:
    checks: list[Check] = []
    checks.append(_skill_listing_budget_check(root))
    adapter_issues = generate_platform_adapters.validate_generated_outputs(root)
    checks.append(
        Check(
            "repository.generated-adapters",
            "fail" if adapter_issues else "pass",
            (
                f"Generated adapters have {len(adapter_issues)} issue(s)."
                if adapter_issues
                else "Generated adapters match canonical sources."
            ),
            {"issues": adapter_issues} if adapter_issues else {},
        )
    )

    contract_issues = generate_platform_adapters.validate_platform_contracts(root)
    checks.append(
        Check(
            "repository.platform-contracts",
            "fail" if contract_issues else "pass",
            (
                f"Platform manifests or authority adapters have {len(contract_issues)} issue(s)."
                if contract_issues
                else "Platform manifests and authority adapters are aligned."
            ),
            {"issues": contract_issues} if contract_issues else {},
        )
    )

    crlf_paths: list[str] = []
    try:
        for source in generate_platform_adapters._canonical_skill_files(root):
            if source.suffix.lower() not in generate_platform_adapters._TEXT_RESOURCE_SUFFIXES:
                continue
            if b"\r" in source.read_bytes():
                crlf_paths.append(str(source.relative_to(root)))
    except (OSError, ValueError) as exc:
        checks.append(
            Check(
                "repository.canonical-eol",
                "inconclusive",
                "Canonical resource line endings could not be inspected.",
                {"error": str(exc)},
            )
        )
    else:
        checks.append(
            Check(
                "repository.canonical-eol",
                "warn" if crlf_paths else "pass",
                (
                    "Canonical text contains CR bytes; generation normalizes it, but the checkout "
                    "does not match the repository's LF policy."
                    if crlf_paths
                    else "Canonical text resources use LF line endings."
                ),
                {"paths": crlf_paths} if crlf_paths else {},
            )
        )
    return checks


def _cli_checks(which: Which, run: CommandRunner) -> tuple[list[Check], dict[str, str]]:
    checks: list[Check] = []
    executables: dict[str, str] = {}
    for host, command in (
        ("claude", "claude"),
        ("codex", "codex"),
        ("vscode", "code"),
    ):
        executable = which(command)
        if not executable:
            checks.append(
                Check(
                    f"host.{host}.cli",
                    "skip",
                    f"{host} CLI is not installed or not on PATH.",
                )
            )
            continue
        executables[host] = executable
        version = run((executable, "--version"))
        if not version.ok:
            checks.append(
                Check(
                    f"host.{host}.cli",
                    "inconclusive",
                    f"{host} CLI was found but its version could not be read.",
                    {"executable": executable, **_failure_details(version)},
                )
            )
        else:
            checks.append(
                Check(
                    f"host.{host}.cli",
                    "pass",
                    f"{host} CLI is available.",
                    {
                        "executable": executable,
                        "version": version.stdout.strip(),
                    },
                )
            )
    return checks, executables


def _same_location(candidate: Path, expected: Path) -> bool:
    try:
        return candidate.exists() and candidate.resolve() == expected.resolve()
    except OSError:
        return False


def _plugin_listing_check(
    host: str,
    executable: str,
    run: CommandRunner,
) -> tuple[Check, bool]:
    listing = run((executable, "plugin", "list"))
    if not listing.ok:
        return (
            Check(
                f"host.{host}.plugin",
                "inconclusive",
                f"{host} plugin inventory could not be read.",
                _failure_details(listing),
            ),
            False,
        )
    installed = "sde-agents" in listing.stdout.lower()
    return (
        Check(
            f"host.{host}.plugin",
            "pass" if installed else "warn",
            (
                "sde-agents is present in the host plugin inventory."
                if installed
                else "sde-agents is absent from the host plugin inventory."
            ),
        ),
        installed,
    )


def _installation_checks(
    root: Path,
    home: Path,
    executables: dict[str, str],
    run: CommandRunner,
    *,
    codex_home: Path | None = None,
) -> list[Check]:
    checks: list[Check] = []
    claude_plugin_installed = False
    if "claude" in executables:
        plugin_check, claude_plugin_installed = _plugin_listing_check(
            "claude", executables["claude"], run
        )
        checks.append(plugin_check)

    claude_agents = home / ".claude" / "agents"
    claude_skills = home / ".claude" / "skills"
    junction_mode = _same_location(claude_agents, root / "agents") and _same_location(
        claude_skills, root / "skills"
    )
    if junction_mode:
        checks.append(
            Check(
                "host.claude.deployment",
                "warn",
                "Claude loads the fleet through user-scope links; plugin namespacing is bypassed.",
            )
        )
    elif claude_plugin_installed:
        checks.append(
            Check(
                "host.claude.deployment",
                "pass",
                "Claude plugin mode is visible and no complete fleet junction deployment was found.",
            )
        )
    else:
        checks.append(
            Check(
                "host.claude.deployment",
                "skip",
                "No complete Claude fleet deployment was detected.",
            )
        )

    if junction_mode and not claude_plugin_installed:
        checks.append(
            Check(
                "host.claude.readonly-guard",
                "warn",
                "The Claude-only read-only guard is dormant in normal junction sessions.",
            )
        )
    elif claude_plugin_installed:
        checks.append(
            Check(
                "host.claude.readonly-guard",
                "pass",
                "Plugin mode can load the Claude read-only guard; behavioral proof remains a probe.",
            )
        )
    else:
        checks.append(
            Check(
                "host.claude.readonly-guard",
                "skip",
                "No Claude plugin deployment was found, so guard readiness was not asserted.",
            )
        )

    if "codex" in executables:
        plugin_check, _ = _plugin_listing_check("codex", executables["codex"], run)
        checks.append(plugin_check)

    resolved_codex_home = codex_home or Path(
        os.environ.get("CODEX_HOME", home / ".codex")
    ).expanduser()
    try:
        plan = install_codex_agents.build_sync_plan(
            root / generate_platform_adapters.CODEX_AGENTS,
            resolved_codex_home / "agents",
        )
    except (OSError, ValueError) as exc:
        checks.append(
            Check(
                "host.codex.custom-agents",
                "inconclusive",
                "Codex custom-agent synchronization could not be inspected.",
                {"error": str(exc)},
            )
        )
    else:
        if plan.conflicts:
            checks.append(
                Check(
                    "host.codex.custom-agents",
                    "fail",
                    "Unmanaged Codex custom-agent files conflict with generated fleet roles.",
                    {"conflicts": [str(path) for path in plan.conflicts]},
                )
            )
        elif plan.out_of_sync:
            checks.append(
                Check(
                    "host.codex.custom-agents",
                    "warn",
                    "Codex custom agents are not synchronized with generated fleet roles.",
                    {
                        "updates": len(plan.writes),
                        "stale_managed": len(plan.removals),
                    },
                )
            )
        else:
            checks.append(
                Check(
                    "host.codex.custom-agents",
                    "pass",
                    "Codex custom agents match generated fleet roles.",
                )
            )
    return checks


def collect_report(
    root: Path = REPO_ROOT,
    *,
    home: Path | None = None,
    codex_home: Path | None = None,
    run: CommandRunner = _run_read_only,
    which: Which = shutil.which,
    now: datetime | None = None,
) -> dict[str, object]:
    root = root.resolve()
    home = (home or Path.home()).resolve()
    checks = _git_checks(root, run)
    checks.extend(_repository_checks(root))
    cli_checks, executables = _cli_checks(which, run)
    checks.extend(cli_checks)
    checks.extend(
        _installation_checks(
            root,
            home,
            executables,
            run,
            codex_home=codex_home,
        )
    )
    counts = Counter(check.status for check in checks)
    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "schema_version": 1,
        "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
        "root": str(root),
        "summary": {status: counts.get(status, 0) for status in STATUSES},
        "checks": [asdict(check) for check in checks],
    }


def render_human(report: dict[str, object]) -> str:
    lines = [f"Fleet doctor: {report['root']}"]
    for check in report["checks"]:  # type: ignore[index]
        lines.append(
            f"[{check['status'].upper():12}] {check['check_id']}: {check['summary']}"
        )
    summary = report["summary"]  # type: ignore[assignment]
    lines.append(
        "Summary: "
        + ", ".join(f"{status}={summary[status]}" for status in STATUSES)
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="fleet repository root")
    parser.add_argument("--json", action="store_true", help="emit the versioned JSON report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = collect_report(args.root)
    except (OSError, ValueError) as exc:
        print(f"fleet doctor could not produce a report: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_human(report))
    # A warning used to exit 0, which made the doctor agree with any caller that asked "is this
    # healthy?" while printing that it was not. Field-proven cost (issue #126): a stale standalone
    # Codex `homelab-engineer` profile shadowed the shipped one for a whole session -- the doctor
    # had already detected it and reported WARN, and the operator found the drift the hard way,
    # through `install_codex_agents.py --check`, because nothing an exit status reaches ever said
    # so. Warnings are distinct from failures rather than promoted into them: 1 still means a check
    # FAILED, 3 means no check failed but at least one warning needs attention (host drift is the
    # common cause, not the only one — CRLF paths and listing-budget overruns warn too; an absent
    # host CLI is a skip, not a warning), and only 0 means nothing needs attention.
    # A per-check `inconclusive` reached no exit status at all, so a check the doctor could not
    # compute exited 0 — the doctor agreeing that everything is fine on the strength of an answer
    # it never obtained (DOCTOR-002). That is the same defect as the warnings one above, one level
    # down: the report said so on stdout and nothing a caller can branch on did.
    #
    # It maps to 2, which already means "the doctor could not tell you" — the code the whole-report
    # failure above returns. The ladder is ordered by how definite the answer is: 1 first, because
    # a check that FAILED is a definite negative and the most actionable thing here; then 2, where
    # nothing failed but the no-failures claim rests on checks that did not all run; then 3 for
    # warnings, where everything computed. A skip is not in the ladder — an absent host CLI is a
    # known, expected non-answer, not an unexpected one.
    # The ladder itself is the kernel's (fleet/diagnostics.py) so every instrument exits alike.
    summary = report["summary"]  # type: ignore[assignment]
    return _diagnostics.exit_status(
        failed=summary["fail"], not_computed=summary["inconclusive"], warned=summary["warn"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
