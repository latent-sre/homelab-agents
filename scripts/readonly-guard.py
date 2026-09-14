#!/usr/bin/env python3
"""PreToolUse guard — enforce read-only agents at the command level, by ALLOWLIST.

Shipped by the sde-agents PLUGIN and registered through `hooks/hooks.json`, which Claude Code
installs as a SESSION-WIDE PreToolUse hook. It therefore has to scope ITSELF: it no-ops unless the
calling agent is in GUARDED_AGENTS.

Why it cannot simply live on the agent, as it used to: a plugin-shipped agent's `hooks:` frontmatter
is SILENTLY IGNORED ("For security reasons, `hooks`, `mcpServers`, and `permissionMode` are not
supported for plugin-shipped agents" — code.claude.com/docs/en/plugins-reference). Probed on CLI
2.1.200: a plugin agent's frontmatter hook never fired, while a byte-identical hook on a
project-scope agent did. Leaving `hooks:` on the agent would read as armor and provide none, so
validate_fleet.py now rejects that key outright.

Nor can the `tools:` field do this job. A scoped grant like `tools: Bash(git diff:*)` LOOKS like it
narrows Bash, and does nothing: probed on CLI 2.1.200, agents granted `Bash(git diff:*)` and
`Bash(git diff *)` both ran `git status` exactly like an agent granted a bare `Bash`. Re-probed
2026-09-13 on CLI 2.1.270 (three runs: both spellings, `default` and `dontAsk` permission modes,
project-scope subagent, the subagent's own Bash tool_result as the oracle): unchanged, `git status`
ran every time — even though the subagent reference now describes the specifier as an enforced
allowlist. Scoped specifiers are real, but only in settings.json permission rules — which are
session-wide and would restrict the USER's Bash too. There is no native per-agent command
scoping. This hook is not a workaround for a better mechanism; it is the only mechanism.

ALLOWLIST, NOT DENYLIST — the load-bearing design decision.

  This guard used to enumerate the state-changing verbs and deny them. That is an unbounded problem
  and it lost: `git clone`, `git submodule update`, `git lfs pull`, `npm ci`, `uv sync`,
  `gh api -f` (which POSTs) and `curl --json` all sailed through, while `rg "gh pr create" docs/` —
  a harmless search whose TEXT contained a verb — was denied. Every new tool ships new ways to
  write, so a denylist is permanently behind, and its failure mode is SILENT: an unlisted writer
  simply runs.

  So it is inverted. We enumerate what a read-only reviewer actually NEEDS — a bounded, knowable
  set — and deny everything else. Failure now means a legitimate read gets blocked: loud, obvious,
  and fixed by adding one entry. That is the right direction to fail in.

  It also means the guard no longer has to out-parse a hostile shell. Anything it cannot confidently
  understand — command substitution, redirection, a subshell, an unbalanced quote — is simply not on
  the list, and is denied.

NO CODE EXECUTION, DELIBERATELY. There is no `python`, `pytest`, `npm`, or `make` on the allowlist,
and no exemption for any script — not even this repository's own validator. Running a repo's test
suite executes that repo's code under your account; no command filter can make that read-only, and
pretending otherwise is the dishonest part. A reviewer cites the builder's test evidence or CI
instead. This also dissolves, rather than fixes, the old relative-path exemption for
`scripts/validate_fleet.py`, which a repository under review could have supplied itself.

Honest boundary — this is still NOT a sandbox. An allowlisted command with a flag combination we
did not consider may yet do something surprising, and a reviewer that can read files can read
secrets. The LOAD-BEARING control remains OS-level least privilege. What this now guarantees is far
narrower and far more defensible than before: nothing outside a short, reviewed list of readers ever
runs.

GIT IS AN INTERPRETER WHEN ITS CONFIG SAYS SO — the one hole no flag list can close. Probed on git
2.43: with `diff.<driver>.command` (or `.textconv`) in a repo's LOCAL `.git/config` and a
`.gitattributes` line selecting that driver, a BARE `git diff` — no flags at all — executes the
named program. So `--ext-diff`/`--textconv` are deliberately NOT denied here: denying them would
close nothing while reading as armor, which is the failure mode this file exists to avoid. The
mitigating fact is that the vector needs local config: `git clone` does not carry the remote's
config, so a hostile repo you cloned yourself cannot set the driver, and `.gitattributes` alone
falls back to git's internal diff. It bites when a repo ARRIVES as a directory or archive
(mounted volume, tarball, handover) with its `.git/config` already written. Treat "review a repo
directory you did not clone" as running its code, and let OS-level least privilege — not this
guard — be what holds. (`core.pager` is NOT part of this: probed on the same version, git skips
the pager entirely when stdout is not a TTY, which it never is under a hook.)
Two same-family residuals, reviewer-reproduced on the same version. First, `git status` executes
a `core.fsmonitor` command from that same LOCAL config — which is why the investigator's arrival
boundary withholds ALL git commands, not merely history commands, until provenance is stated
(the prose is the fix; this docstring owns the statement of why). Second, in a partial clone an
any allowlisted reader that materializes an absent object — `git show <old>:<path>`, `git log -p`,
`git blame <rev> -- <file>` — lazily fetches it from the repo's own configured remote (reproduced
on git 2.43 under `GIT_TRACE_PACKET=1`: `command=fetch` with a `want <blob>` packet). The class,
not the command list, is the boundary: an outbound fetch inside the investigator's no-network
slice. Hash-verified,
so a tampering remote cannot inject content, but a real hole in the literal claim;
`GIT_NO_LAZY_FETCH=1` would close it if this guard ever gains an env channel, and until then the
no-network claim is qualified here rather than overstated.

SCOPING CONTRACT (probed, not assumed): the stdin payload carries `agent_type` — namespaced for a
plugin agent (`sde-agents:code-reviewer`), bare for a project/user-scope one. A PLAIN main loop
carries no `agent_type` key, which is what makes a session-wide hook safe: the user's own Bash in
an ordinary session never matches GUARDED_AGENTS and is never inspected. A session launched with
`--agent` does carry that agent's name (inside a subagent, the subagent's type takes precedence),
so a main session deliberately run as a guarded agent is guarded on purpose, not as collateral.
`scripts/probe_plugin.py` drives that clause as of 2026-08-17 — a `--agent sde-agents:code-reviewer`
session attempting a denylisted command, which the guard must deny — so the instrument exists; the
clause is observed once a probe run records it, and until then it is instrumented rather than
witnessed. It is the half a pinned-binary change could break in the dangerous direction: if
`--agent` stopped populating `agent_type`, an operator running the reviewer as their whole session
would be unguarded while every subagent assertion stayed green.
The field and its plugin-scoped values are documented in the upstream hooks reference
(code.claude.com/docs/en/hooks.md); this docstring owns the fleet's statement of the contract —
other files point here rather than restating it. Documentation is not proof a newly pinned binary
still honors the contract: if `agent_type` is renamed (or the plugin namespaced form changes) the
guard would silently stop guarding — see the contract canary in main().

Decision transport: a deny is the permissionDecision JSON on stdout with exit EXIT_DENY (43); an
allow is empty stdout with exit EXIT_ALLOW (42). The distinctive codes are how the hook tells THIS
guard's answer from a stand-in interpreter that merely exits 0 — see the comment at EXIT_ALLOW.
Anything else — including EXIT_INDETERMINATE (44), the deliberate answer for input the guard
cannot parse — is not an answer at all: the hook falls through to its raw guarded-agent match,
denying for guarded payloads and no-oping for everyone else.
The hook shell string translates them back to the documented exit-0 contract
(https://code.claude.com/docs/en/hooks) before Claude Code sees anything.

Covered by tests/test_readonly_guard.py (pure-stdlib, runs offline in CI).
"""
import json
import re
import shlex
import sys

# The plugin name is the namespace Claude Code prepends to every component this plugin ships;
# it must equal `name` in .claude-plugin/plugin.json (validate_fleet.py enforces that).
PLUGIN_NAME = "sde-agents"
# Agents this guard applies to — the read-only agents that still hold Bash. Both the namespaced
# form (how a plugin agent identifies itself) and the bare form (project/user scope) are guarded, so
# the guard cannot be sidestepped by installing the agent a different way.
# validate_fleet.py cross-checks this against agents/: hold Bash and you must be listed here.
#
# `principal-engineer` is guarded despite holding Write: its document mandate cannot be
# enforced by the tool boundary, but inspection-only Bash can. Its design remit includes
# strategic architecture; both depths use this same guarded identity. The validator compels
# membership only for Bash holders without write tools, so this document writer is here by
# choice. The hook roster is checked against this set to prevent a silently unguarded name.
#
# `repository-investigator` holds Bash solely for git history and revision identity (log, blame,
# show, rev-parse) and no write tool, so the validator compels its membership. Its local-only trust
# boundary survives the grant only because its SLICE of the allowlist carries no network command:
# the `gh` readers below are network fetches (PR bodies, issue text, `gh search code` results from
# arbitrary GitHub repositories), which is exactly the external content this role's trust split
# exists to keep out of the same context as private source. So the gh family is scoped to the
# roles whose remit includes PR context, via NETWORK_AGENT_NAMES below, rather than granted with the
# roster (PR #141 review finding: a uniform roster grant handed the investigator `gh search code`).
GUARDED_AGENT_NAMES = frozenset({
    "code-reviewer", "principal-engineer", "repository-investigator",
})
# Roles entitled to the allowlist's NETWORK reads — the `gh` subcommands, and the bare
# `git remote show` (which queries the remote unless `-n` is given). Membership here means
# "fetched external content may share this role's context"; the investigator is deliberately
# absent, and any future roster member starts absent until its trust boundary is argued.
NETWORK_AGENT_NAMES = frozenset({
    "code-reviewer", "principal-engineer",
})
GUARDED_AGENTS = frozenset(
    set(GUARDED_AGENT_NAMES) | {f"{PLUGIN_NAME}:{name}" for name in GUARDED_AGENT_NAMES}
)

# Exit codes AUTHENTICATE the guard's answer to the hook — they are not decoration.
#
# The hook must locate a Python at runtime (the plugin has no install step that could pin an
# absolute interpreter, and on Windows the Microsoft Store `python3` stub wins the PATH lookup).
# If the hook simply took "exit 0 + empty stdout" as ALLOW, then ANY binary named `python3` that
# exits 0 — a PATH-planted shim, the Store stub on a bad day — would be accepted as the guard and
# would silently allow every command. So an ALLOW must be positively asserted with a code no
# accidental or hostile stand-in produces; the hook treats anything else as "this was not my guard"
# and moves to the next candidate interpreter, failing closed if none answers correctly.
EXIT_ALLOW = 42
EXIT_DENY = 43
# The third answer, deliberately NOT authoritative: "this input is not something I can vouch for."
# Input the guard cannot parse must never earn EXIT_ALLOW — 42 stops the hook cold, so a truncated
# GUARDED payload would never reach the hook's raw agent_type fallback that exists to deny exactly
# that (GOV-001: reproduced — the same guarded push that denies intact flipped to allow when the
# JSON was cut). Exiting with neither sentinel makes the hook treat this run like a stand-in
# interpreter's: it falls through to the fallback, which fails closed for guarded payloads and
# no-ops for everyone else. The value only needs to be not-42-and-not-43; it is pinned anyway so
# the tests can tell a deliberate indeterminate from an uncaught crash's exit 1.
EXIT_INDETERMINATE = 44

# --- shell constructs we refuse to reason about ---------------------------------------------
# An allowlist only means something if the string really is the commands we think it is. Command
# substitution, redirection, process substitution and backgrounding all smuggle in a second command
# (or a write) past the token inspection below, so their mere PRESENCE is disqualifying. A `>` or
# `$(` inside a quoted search pattern is denied too — a false positive we accept, because the deny
# is loud and the alternative is guessing at shell quoting, which is how the old denylist lost.
_STRUCTURE_DENY = re.compile(
    r"\$\(|`|<\(|\$\{"       # command / process substitution, ${...}
    r"|>|<"                  # any redirection, including heredocs
    r"|(?<!&)&(?!&)"         # a lone & (background); && is a separator, handled below
)
# Operator tokens that separate one command from the next. Every resulting segment must stand on its
# own as an allowed read — `git log; rm -rf /` gets no free pass from its harmless first half.
_SEPARATORS = {"|", "||", "&&", ";", "\n"}
# Every character `shlex(punctuation_chars=True)` treats as an operator character. It emits a RUN
# of adjacent ones as a SINGLE token, which is the bypass found by the property test below:
# `ls;(rm -rf /)` lexes as ['ls', ';(', 'rm', '-rf', '/', ')'], and `;(` is not in _SEPARATORS, so
# the line never splits. The whole thing stayed one segment whose command is the allowed `ls`,
# with `rm -rf /` riding in as its arguments -- ALLOWED, while both `rm -rf /` and `(rm -rf /)`
# are denied on their own. Any operator token that is not exactly a separator we recognise is
# therefore structure we do not understand, and is denied. A quoted `(` in a search pattern is
# denied with it: after posix lexing it is the same token, and the guard's standing trade is a
# loud false positive over a silent allow.
_OPERATOR_CHARS = frozenset("();<>|&")

# --- the allowlist --------------------------------------------------------------------------
# Plain readers and filters: they consume input and print. None can write a file on their own (a
# redirect would be needed, and redirects are refused above). `sed` and `awk` are deliberately ABSENT
# — both can write files without any redirect (`sed -i`, awk's `print > "f"` and `system()`).
# `sort`, `tree`, and `less` are likewise absent: their `-o` options write files, and `less` also
# supports interactive command execution.
_SIMPLE_READERS = frozenset({
    "cat", "head", "tail", "nl", "wc", "uniq", "cut", "tr", "column",
    "grep", "egrep", "fgrep",
    "ls", "stat", "du", "basename", "dirname", "realpath", "pwd",
    "echo", "cmp", "jq", "true", "false",
})
# `file` and the standalone `diff` are deliberately absent. Both look like readers but expose
# execution-capable options (`file -C` invokes a compiler; GNU diff's pagination path invokes a
# pager). `git diff`, `cmp`, and the metadata readers above cover the actual review need without
# carrying two more flag surfaces whose safe subsets would need permanent maintenance.
# `ag` (the silver searcher) was here and is deliberately GONE: it documents `--pager COMMAND`,
# the same execute-a-program lever gated on `rg` and `less`, and it is not installed on the
# machines this fleet was probed on — so its exec-flag surface cannot be enumerated the way `rg`'s
# was. It is also fully redundant: `rg` and `grep` are both allowlisted. Per this file's own rule,
# the allowlist carries what a reviewer NEEDS, and an un-enumerable tool that nothing needs is the
# easiest kind to leave off. Restoring it means adding a flag gate like `_RG_EXECUTION_FLAGS`,
# verified against the installed binary — not just putting the name back.
# ripgrep flags that run an external program (or a PATH-resolved helper) mid-search, turning a
# reader into code execution. `--pre COMMAND` runs COMMAND on every file; `--hostname-bin COMMAND`
# runs COMMAND to resolve the hostname for hyperlinks (rg 14+); `--search-zip`/`-z` shells out to
# decompressors found on PATH, which a planted `gzip` subverts. `rg` is useful enough for review to
# retain with this gate — enumerate EVERY exec-capable flag, since one unlisted flag reopens the
# hole (proven: `--hostname-bin=/bin/sh` executed before this list grew past `--pre`).
_RG_EXECUTION_FLAGS = frozenset({"--pre", "--hostname-bin", "--search-zip", "-z"})

# `git` subcommands that have no write SUBCOMMAND (per `git-<name>(1)` synopsis). Several still
# accept `--output=<file>`/`-o <file>` to write a report to disk (diff, log, show, diff-tree,
# whatchanged) — those flag forms are rejected below in _git_allowed, since being on this list is
# not a licence to write files.
_GIT_READ = frozenset({
    "diff", "log", "show", "blame", "status", "shortlog", "describe", "rev-parse", "rev-list",
    "ls-files", "ls-tree", "cat-file", "show-ref", "grep", "whatchanged", "diff-tree",
    "merge-base", "name-rev", "version", "check-ignore",
})
# `check-ignore` earns its slot the way every reader must: a review NEED (proving a secret/key
# path is actually gitignored, negation rules included — reconstructing that from .gitignore by
# hand is where a reviewer silently gets it wrong) and a clean surface (it prints ignore status
# and the matching rule; per git-check-ignore(1) it has no exec-capable or output-redirect flag,
# so neither _GIT_READ_WRITE_FLAGS nor a `-O`-style gate applies).
# `help` was here and is deliberately GONE: `git help -w/--web` hands off to `git web--browse`,
# which runs the command named by the `web.browser`/`browser.<tool>.cmd` config, and `-i` shells
# out to an info reader. Removing the SUBCOMMAND closes every spelling at once, where denying the
# flags would leave the next viewer flag to be discovered. Nothing about reviewing a diff needs
# git's own manual.
# Flags on _GIT_READ subcommands that redirect output into a file. `--output=<file>` and its
# separate-argument form `-o <file>` are accepted by diff/log/show/diff-tree/whatchanged (they
# share the diff plumbing) and write to the named path with no shell redirect involved, so
# _STRUCTURE_DENY never sees them. Any occurrence is disqualifying.
_GIT_READ_WRITE_FLAGS = frozenset({"-o", "--output"})
# Flags on _GIT_READ subcommands that EXECUTE a program — the git twin of `rg --pre`. `git grep`
# opens matching files in a pager named by `--open-files-in-pager[=CMD]` or its attached short form
# `-O<CMD>`, and runs CMD even with no TTY (proven: `git grep -O/bin/sh` executed the pager). The
# `-O` short form can't be caught by the `split("=")` membership test the write-flags use, so
# _git_allowed rejects any `-O`-prefixed arg explicitly. That also denies `git diff -O<orderfile>`
# (a benign order file that shares the branch) — a false positive we accept, per this guard's
# fail-loud-not-silent rule.
_GIT_READ_EXEC_FLAGS = frozenset({"--open-files-in-pager"})
# Subcommands whose FIRST POSITIONAL decides read vs write (`git stash list` reads, a bare
# `git stash` pushes; `git submodule status` reads, `git submodule update` writes;
# `git reflog show` reads, `git reflog expire` prunes reflog entries).
_GIT_READ_VERBS = {
    "stash": frozenset({"list", "show"}),
    "worktree": frozenset({"list"}),
    "notes": frozenset({"list", "show"}),
    "submodule": frozenset({"status"}),
    "remote": frozenset({"show", "get-url"}),
    # `git reflog` with no subcommand defaults to `show`, but `expire`, `delete`, `drop`, and
    # `write` all mutate the reflog. Gate on an EXPLICIT read verb; a bare `git reflog` is denied
    # rather than defaulted, since the "no positional" shape here is indistinguishable from a
    # typo of a write verb and the safe direction is loud.
    "reflog": frozenset({"show", "list", "exists"}),
}
# Subcommands that list when read-flagged and CREATE when handed a bare name (`git branch feature`,
# `git tag v1.0`). Allowed only when no positional is present, or a read flag makes the intent
# explicit — and never when a write flag appears. The flag sets differ per subcommand on purpose:
# `-a` means --all for branch (read) but --annotate for tag (WRITE).
_GIT_LIST_LIKE = {
    "branch": {
        "read": frozenset({
            "-a", "-r", "-v", "-vv", "--all", "--remotes", "--verbose", "--list", "--contains",
            "--no-contains", "--merged", "--no-merged", "--show-current", "--format", "--sort",
            "--points-at", "-i", "--ignore-case",
        }),
        "write": frozenset({
            "-d", "-D", "-m", "-M", "-c", "-C", "-f", "--delete", "--move", "--copy", "--force",
            "--set-upstream-to", "-u", "--unset-upstream", "--track", "-t", "--no-track",
            "--edit-description",
        }),
    },
    "tag": {
        "read": frozenset({
            "-l", "--list", "-n", "--contains", "--no-contains", "--points-at", "--sort",
            "--format", "--merged", "--no-merged", "-v", "--verify", "-i", "--ignore-case",
        }),
        "write": frozenset({
            "-a", "--annotate", "-s", "--sign", "-d", "--delete", "-f", "--force", "-m", "-F",
            "-u", "--local-user", "--create-reflog",
        }),
    },
}
# `git config` writes whenever it is not explicitly reading, so require a read flag.
_GIT_CONFIG_READ = frozenset({
    "--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l",
})
# git's own global options, permitted between `git` and the subcommand. `-c key=val` is NOT here:
# it injects config into the command's execution, which is a lever we have no need to hand over.
_GIT_GLOBAL_WITH_VALUE = frozenset({"-C", "--git-dir", "--work-tree"})
_GIT_GLOBAL_BARE = frozenset({"--no-pager", "-P", "--no-replace-objects", "--literal-pathspecs"})

# `gh` read-only subcommand pairs. `gh api` is absent by design: it silently switches to POST when
# given `-f`/`-F` fields, so "read-only gh api" is a shape too easy to get wrong.
_GH_EXECUTION_FLAGS = frozenset({"--web", "-w"})  # `gh ... --web` launches $BROWSER — an app, not a read.
_GH_READ = {
    "pr": frozenset({"view", "diff", "list", "checks", "status"}),
    "issue": frozenset({"view", "list", "status"}),
    "repo": frozenset({"view"}),
    "run": frozenset({"view", "list"}),
    "release": frozenset({"view", "list"}),
    "search": frozenset({"prs", "issues", "repos", "commits", "code"}),
}

# `find`'s action flags run commands or delete files — the reason `find` cannot simply be a reader.
_FIND_ACTIONS = ("-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprintf", "-fls")

_REASON = (
    "Blocked: this is a read-only agent, and its Bash access is limited to an ALLOWLIST of "
    "read-only commands (git diff/log/show/blame/status, rg, grep, ls, cat, head, find, gh pr "
    "view/diff, and similar filters). The command above is not on that list. Note this agent may "
    "NOT execute code — no test runners, no scripts, no package managers — because running a "
    "repository's code is not a read-only act, whatever the command looks like. Inspect with reads, "
    "cite the builder's or CI's test evidence rather than re-running it, and report anything that "
    "needs changing as a finding for the author to apply — never apply it yourself."
)


_LOCAL_ONLY_REASON = (
    "Blocked: this command is a network read — `gh` subcommands fetch PR, issue, and search "
    "content from GitHub, and a bare `git remote show` queries the remote (`-n` is the "
    "no-query form) — and this local-only role's allowlist deliberately excludes network reads "
    "so private source never shares a subordinate context with fetched external content. Use "
    "local git history and Read/Grep/Glob instead; if externally hosted context is "
    "load-bearing, request it from the caller as a separate provenance-labeled packet."
)


def _allow() -> None:
    """Positively assert ALLOW (no stdout, distinctive exit code) and stop."""
    sys.exit(EXIT_ALLOW)


def _deny(reason: str) -> None:
    """Emit the deny decision on stdout and assert DENY via the exit code."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(EXIT_DENY)


def _split_segments(tokens: list[str]) -> list[list[str]]:
    """Split a token stream on shell operators into individual commands."""
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in _SEPARATORS:
            segments.append(current)
            current = []
        else:
            current.append(token)
    segments.append(current)
    return [segment for segment in segments if segment]


def _positionals(args: list[str]) -> list[str]:
    return [arg for arg in args if not arg.startswith("-")]


def _git_allowed(args: list[str], *, network_allowed: bool = True) -> bool:
    # Step over git's global options to find the subcommand.
    index = 0
    while index < len(args) and args[index].startswith("-"):
        option = args[index]
        base = option.split("=", 1)[0]
        if base in _GIT_GLOBAL_WITH_VALUE:
            index += 1 if "=" in option else 2
        elif option in _GIT_GLOBAL_BARE:
            index += 1
        else:
            return False  # includes `-c key=val`
    if index >= len(args):
        return False
    subcommand, rest = args[index], args[index + 1:]

    if subcommand in _GIT_READ:
        # Even a read subcommand can escape read-only WITHOUT a shell redirect: `--output=<file>` /
        # `-o <file>` writes a report to disk, and `git grep --open-files-in-pager[=CMD]` / `-O<CMD>`
        # executes CMD. Reject every spelling — `--flag`, `--flag=x`, `-o x`, and the attached short
        # form `-O<CMD>` that the `split("=")` test alone would miss.
        for arg in rest:
            base = arg.split("=", 1)[0]
            if base in _GIT_READ_WRITE_FLAGS or base in _GIT_READ_EXEC_FLAGS:
                return False
            if arg.startswith("-O"):  # `-O`, `-O/bin/sh` (git grep pager exec)
                return False
        return True

    if subcommand in _GIT_READ_VERBS:
        verbs = _positionals(rest)
        if not (verbs and verbs[0] in _GIT_READ_VERBS[subcommand]):
            return False
        # A bare `git remote show <name>` QUERIES THE REMOTE — `-n` is git's documented
        # "do not query remotes" form — so for a role whose slice excludes network reads the
        # default spelling is a network fetch wearing a read verb (PR #141 round-2 finding).
        # `get-url` stays: it reads local config only.
        if not network_allowed and subcommand == "remote" and verbs[0] == "show":
            return "-n" in rest
        return True

    if subcommand == "config":
        return any(arg.split("=", 1)[0] in _GIT_CONFIG_READ for arg in rest)

    if subcommand in _GIT_LIST_LIKE:
        flags = _GIT_LIST_LIKE[subcommand]
        bare = [arg.split("=", 1)[0] for arg in rest if arg.startswith("-")]
        if any(flag in flags["write"] for flag in bare):
            return False
        if any(flag in flags["read"] for flag in bare):
            return True
        # No flags either way: listing is the default, but a positional means "create this".
        return not _positionals(rest)

    return False


def _gh_allowed(args: list[str]) -> bool:
    if any(arg.split("=", 1)[0] in _GH_EXECUTION_FLAGS for arg in args):
        return False
    positionals = _positionals(args)
    if len(positionals) < 2:
        return False
    group, verb = positionals[0], positionals[1]
    return verb in _GH_READ.get(group, frozenset())


def _rg_allowed(args: list[str]) -> bool:
    return not any(arg.split("=", 1)[0] in _RG_EXECUTION_FLAGS for arg in args)


def _segment_allowed(segment: list[str], *, network_allowed: bool = True) -> bool:
    command, args = segment[0], segment[1:]
    # A path to a binary (`/bin/cat`, `./deploy.sh`, `scripts/setup.sh`) is never allowed: the
    # allowlist names commands, and a path is how you smuggle a different one in.
    if "/" in command or "\\" in command or "=" in command:
        return False
    if command == "git":
        return _git_allowed(args, network_allowed=network_allowed)
    if command == "gh":
        return network_allowed and _gh_allowed(args)
    if command == "rg":
        return _rg_allowed(args)
    if command == "find":
        return not any(arg.startswith(_FIND_ACTIONS) for arg in args)
    return command in _SIMPLE_READERS


def _tokenize(line: str) -> list[str]:
    """Tokenize one line, with shell operators as their OWN tokens.

    `shlex.split` is the obvious choice and it is WRONG here: it splits on whitespace only, so
    `echo hi; git push` comes back as ['echo', 'hi;', 'git', 'push'] — one command, starting with an
    allowed reader, and the `git push` rides in behind it. That bypasses the entire allowlist, which
    is exactly the silent-allow failure this guard exists to prevent (caught by the corpus below).
    `punctuation_chars=True` makes shlex emit `;`, `|`, `||`, `&&`, `(`, `)` as separate tokens,
    while still honouring quotes — so an operator inside a quoted search pattern stays part of its
    argument and never splits anything.
    """
    lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    return list(lexer)


def is_allowed(command: str, *, network_allowed: bool = True) -> bool:
    """True only if every segment of every line of `command` is a known read-only command.

    `network_allowed=False` withholds the allowlist's network reads — the `gh` family and the
    bare `git remote show` — on top of the base allowlist: the slice a local-only role must not
    hold. The default stays True so the base allowlist keeps one meaning; main() computes the
    flag from NETWORK_AGENT_NAMES per guarded agent.
    """
    if not command.strip():
        return True  # nothing to run
    if _STRUCTURE_DENY.search(command):
        return False
    # A newline is a command separator just like `;`, and shlex treats it as plain whitespace —
    # so lines are split off BEFORE tokenizing. A quoted string that genuinely spans a newline is
    # torn in half by this and fails to lex, which denies. That is the correct direction to err.
    for line in command.splitlines():
        if not line.strip():
            continue
        try:
            tokens = _tokenize(line)
        except ValueError:
            return False  # unbalanced quotes: we do not understand it, so we do not permit it
        if any(
            token and set(token) <= _OPERATOR_CHARS and token not in _SEPARATORS
            for token in tokens
        ):
            # An operator run we do not recognise (`;(`, `&&(`, a stray `)`), so we cannot say
            # where one command ends and the next begins. Same rule as the unbalanced quote above.
            return False
        segments = _split_segments(tokens)
        if not segments or not all(
            _segment_allowed(segment, network_allowed=network_allowed) for segment in segments
        ):
            return False
    return True


def main() -> None:
    try:
        # Read raw bytes and decode with utf-8-sig so a leading BOM (which some Windows shells
        # and pipes prepend) is stripped reliably, regardless of the locale encoding.
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        # Never vouch for input you could not read: the hook's fallback decides (see the
        # EXIT_INDETERMINATE comment above for why this must not be _allow()).
        sys.exit(EXIT_INDETERMINATE)
    if not isinstance(data, dict):
        # Parseable JSON that is not the documented dict envelope is equally unreadable to the
        # scoping logic below — before this check it crashed on `.get` and only failed safe by
        # accident of the hook treating a traceback's exit 1 as indeterminate.
        sys.exit(EXIT_INDETERMINATE)

    if data.get("tool_name") != "Bash":
        _allow()

    # This hook is registered SESSION-WIDE (a plugin cannot scope a PreToolUse hook to one of its
    # own agents), so the guard scopes itself. A plain main loop carries NO `agent_type` key, so
    # the user's own Bash in an ordinary session exits here and is never inspected — that property
    # is what makes a session-wide read-only guard safe to ship at all. A `--agent` session is
    # guarded exactly when it runs as a guarded agent (see the scoping contract in the module
    # docstring).
    agent = data.get("agent_type")
    if agent not in GUARDED_AGENTS:
        # Contract canary. `agent_type` is documented upstream, but a rename (or a changed
        # plugin-namespaced form) in a newly pinned CLI would still make every payload look like
        # the main loop and the guard would quietly stop guarding — precisely
        # the silent-disarm class of bug this fleet hardened against in validate_fleet.py. So when
        # the payload still identifies a guarded agent under some OTHER key, yet no `agent_type`
        # did, treat the contract as broken and fail CLOSED.
        #
        # The check is deliberately keyed, not a substring search over the envelope:
        #   * `tool_input` is excluded outright — the command is attacker- and user-controlled
        #     text, and scanning it would deny an ordinary main-session command that merely
        #     MENTIONS the agent (`git commit -m "fix sde-agents:code-reviewer"`).
        #   * only keys whose NAME contains "agent" are consulted, and only for exact GUARDED
        #     values, so `cwd`/`transcript_path` — which could legitimately contain an agent's name
        #     as a directory component — can never trip it.
        # Residual: a rename to a key without "agent" in it is not caught here; that is what
        # scripts/probe_plugin.py exists to catch after a CLI upgrade.
        if agent is None and any(
            "agent" in key.lower() and isinstance(value, str) and value in GUARDED_AGENTS
            for key, value in data.items()
            if key != "tool_input"
        ):
            _deny(
                "Blocked: the read-only guard could not identify the calling agent. The PreToolUse "
                "payload named a guarded agent but carried no 'agent_type' field, so the hook payload "
                "contract has changed. The guard fails closed rather than silently stop guarding. "
                "Re-run the fleet probe (see docs/fleet-development.md, 'Verifying the host packages') and update "
                "GUARDED_AGENTS in scripts/readonly-guard.py."
            )
        _allow()

    command = (data.get("tool_input") or {}).get("command", "") or ""
    network_ok = agent.split(":", 1)[-1] in NETWORK_AGENT_NAMES
    if not is_allowed(command, network_allowed=network_ok):
        # A command the base allowlist would accept but the network scoping withheld gets the
        # reason that teaches the actual boundary — the generic reason lists `gh pr view` as
        # allowed, which for this role it deliberately is not.
        if not network_ok and is_allowed(command, network_allowed=True):
            _deny(_LOCAL_ONLY_REASON)
        _deny(_REASON)
    _allow()


if __name__ == "__main__":
    main()
