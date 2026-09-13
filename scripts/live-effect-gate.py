#!/usr/bin/env python3
"""Optional PreToolUse live-effect interposition for homelab-engineer.

Shipped by the sde-agents PLUGIN and registered through `hooks/hooks.json` as a second
`PreToolUse`/`Bash` hook, beside `readonly-guard.py`. Like the guard it is SESSION-WIDE and scopes
ITSELF: it no-ops unless the pending call's `agent_type` names a gated agent, and a plain main
loop — which carries no `agent_type` key — is never inspected. (The reasons a plugin agent cannot
carry its own `hooks:` are the guard docstring's; they are not restated here.)

POLICY. SDE_AGENTS_LIVE_EFFECT_POLICY is selected in the operator's host launch environment:
unset or `host` returns no decision, leaving the host's normal permissions in charge; `prompt`
opts into the existing partial filter below. An invalid value fails closed for the scoped agent.
The hook shell also short-circuits `host`, so that policy does not depend on a working Python.
No policy emits `allow`, grants task authority, or overrides another host control. Agents must
not change this launch policy to obtain permission for their own work. Repository/tool-input
claims do not select policy. A same-user process can edit host configuration; this selector is
operator configuration, not a tamper-proof security boundary.

Before 2026-08-29 the agent was told to prove that a human-interposing control existed by
"inspecting the effective control for that argv" without invoking it. Claude Code exposes no such
evaluation to the model (the effective mode includes CLI flags it cannot see, and settings files
it can read are ones it can also write), so that earlier rule sent every live apply to operator
handoff. This hook supplies interposition for the calls it covers, not every live-effect argv.
The current bounded-authority policy does not waive any prompt/denial the hook actually returns.

IN PROMPT POLICY, THE ROSTER IS DENYLIST-SHAPED — the opposite of the guard, for a different job. The
guard enforces read-only, where a missed writer is a silent breach, so it enumerates readers. This
gate adds a fleet-owned prompt where the fleet KNOWS an effect is live; for anything unlisted the
host's own permission flow remains the floor, exactly as it was before this file existed. An
allowlist here would prompt on every Tier 1 `git commit` and `sed -i` and teach the operator to
click through. The roster grows by RECURRENCE: a lab incident or drill that shows an unlisted live
effect adds one entry with its transcript cited — never by exempting an entry.

IN PROMPT POLICY, PERMISSION MODE IS THE OTHER HALF. The payload carries `permission_mode`
(default|plan|acceptEdits|auto|dontAsk|bypassPermissions — code.claude.com/docs/en/hooks). Under
`bypassPermissions`, `dontAsk`, and `auto` no human answers a prompt, and a hook `deny` still wins
there (hooks-guide: deny beats every mode). So a live verb in a suppressed mode is DENIED with an
operator-handoff reason: the agent's text says bypass is not a decision, and this is the line
that makes it true. An ABSENT `permission_mode` is denied too — if the field is ever renamed
upstream, live effects stop loudly (every one hands off) instead of the gate quietly asking into
a session that suppresses the prompt. Readers never depend on the mode.

WHAT CANNOT BE BOUND, ASKS. A wrapper shell (`sh -c`, `eval`), command substitution, an
interactive `ssh` with no remote command, `find -exec`, `sudo -i`, or an unparseable quote cannot
be confidently classified; the gate asks rather than guessing.

Decision transport: exit EXIT_ALLOW (42) with empty stdout is "no decision"; EXIT_ASK (45) and
EXIT_DENY (43) print the permissionDecision JSON; EXIT_INDETERMINATE (44) is the answer for input
the gate cannot parse, and the hook shell then falls back to its raw agent match (a static ask, or
a static deny when the raw payload names a suppressed mode). The distinctive codes are how the
hook tells this gate's answer from a stand-in interpreter that merely exits 0; the shell string
translates them to the documented exit-0 contract. tests/test_live_effect_gate.py pins the codes
and PLUGIN_NAME to readonly-guard.py's, and tests/test_hook_wiring.py runs the shell string.

Honest boundary: this is a command filter, not a sandbox. It cannot see what a listed reader does
with a flag it did not consider, and it cannot see inside a script the agent wrote and then ran
(`python3 deploy.py` is not on the roster — the agent's own Tier discipline covers what it
authors). OS-level least privilege stays load-bearing.
"""
import json
import os
import re
import shlex
import sys

PLUGIN_NAME = "sde-agents"
GATED_AGENT_NAMES = frozenset({"homelab-engineer"})
_GATED = frozenset(GATED_AGENT_NAMES) | frozenset(
    f"{PLUGIN_NAME}:{name}" for name in GATED_AGENT_NAMES
)

EXIT_ALLOW = 42          # no decision; the host's own permission flow applies
EXIT_DENY = 43
EXIT_INDETERMINATE = 44  # unparseable input; the hook's raw fallback decides
EXIT_ASK = 45

SUPPRESSED_MODES = frozenset({"bypassPermissions", "dontAsk", "auto"})

# Executables whose EVERY invocation is a live effect on a host.
ALWAYS_LIVE = frozenset({
    "reboot", "shutdown", "poweroff", "halt", "init", "telinit",
    "mkfs", "mkfs.ext4", "mkfs.xfs", "mkfs.btrfs", "mkfs.vfat", "mkswap", "wipefs", "dd",
    "parted", "fdisk", "sfdisk", "cfdisk", "resize2fs", "xfs_growfs",
    "lvremove", "lvresize", "lvreduce", "lvextend", "lvcreate", "vgremove", "vgextend",
    "vgreduce", "pvremove", "pvcreate",
    "mount", "umount", "swapon", "swapoff",
    "iptables-restore", "ip6tables-restore", "wg-quick",
    "kill", "pkill", "killall",
    "useradd", "usermod", "userdel", "groupadd", "groupdel", "passwd", "chpasswd",
    "shred", "truncate", "chattr",
    "kubeadm",
})

# Executables (or compound prefixes) where only the listed first word after them is live.
LIVE_SUBCOMMANDS: dict[tuple[str, ...], frozenset[str]] = {
    ("docker",): frozenset({"run", "start", "stop", "restart", "rm", "kill", "pause", "unpause",
                            "exec", "update", "load", "prune"}),
    ("docker", "compose"): frozenset({"up", "down", "restart", "stop", "start", "rm", "kill",
                                      "exec", "run", "create"}),
    ("docker", "system"): frozenset({"prune"}),
    ("docker", "volume"): frozenset({"rm", "prune", "create"}),
    ("docker", "network"): frozenset({"rm", "prune", "create"}),
    ("docker", "image"): frozenset({"rm", "prune"}),
    ("docker", "container"): frozenset({"rm", "prune", "stop", "kill", "start", "restart"}),
    ("docker-compose",): frozenset({"up", "down", "restart", "stop", "start", "rm", "kill",
                                    "exec", "run", "create"}),
    ("podman",): frozenset({"run", "start", "stop", "restart", "rm", "kill", "pause", "unpause",
                            "exec", "update", "load", "prune"}),
    ("podman", "compose"): frozenset({"up", "down", "restart", "stop", "start", "rm", "kill",
                                      "exec", "run", "create"}),
    ("podman", "system"): frozenset({"prune"}),
    ("podman", "volume"): frozenset({"rm", "prune", "create"}),
    ("podman-compose",): frozenset({"up", "down", "restart", "stop", "start", "rm", "kill"}),
    ("systemctl",): frozenset({"start", "stop", "restart", "reload", "reload-or-restart",
                               "try-restart", "enable", "disable", "mask", "unmask",
                               "daemon-reload", "kill", "isolate", "reboot", "poweroff", "halt",
                               "suspend", "hibernate", "set-property", "revert", "edit"}),
    ("apt",): frozenset({"install", "remove", "purge", "upgrade", "full-upgrade", "dist-upgrade",
                         "autoremove", "reinstall"}),
    ("apt-get",): frozenset({"install", "remove", "purge", "upgrade", "dist-upgrade",
                             "autoremove", "reinstall"}),
    ("dnf",): frozenset({"install", "remove", "upgrade", "update", "downgrade", "autoremove",
                         "reinstall", "distro-sync", "swap"}),
    ("yum",): frozenset({"install", "remove", "upgrade", "update", "downgrade", "autoremove",
                         "reinstall"}),
    ("zypper",): frozenset({"install", "remove", "update", "dup", "patch", "in", "rm"}),
    ("apk",): frozenset({"add", "del", "upgrade"}),
    ("snap",): frozenset({"install", "remove", "refresh", "revert", "enable", "disable"}),
    ("brew",): frozenset({"install", "uninstall", "upgrade", "reinstall"}),
    ("ip", "link"): frozenset({"set", "add", "del", "delete"}),
    ("ip", "addr"): frozenset({"add", "del", "delete", "flush", "replace"}),
    ("ip", "address"): frozenset({"add", "del", "delete", "flush", "replace"}),
    ("ip", "route"): frozenset({"add", "del", "delete", "replace", "change", "flush"}),
    ("ip", "rule"): frozenset({"add", "del", "delete"}),
    ("nmcli", "con"): frozenset({"up", "down", "add", "delete", "modify", "reload"}),
    ("nmcli", "connection"): frozenset({"up", "down", "add", "delete", "modify", "reload"}),
    ("nmcli", "dev"): frozenset({"connect", "disconnect", "reapply", "modify"}),
    ("nmcli", "device"): frozenset({"connect", "disconnect", "reapply", "modify"}),
    ("wg",): frozenset({"set", "setconf", "syncconf", "addconf"}),
    ("zfs",): frozenset({"destroy", "rollback", "create", "rename", "receive", "recv", "set",
                         "inherit", "promote", "mount", "unmount", "umount", "share", "unshare",
                         "upgrade", "load-key", "unload-key", "change-key"}),
    ("zpool",): frozenset({"destroy", "remove", "offline", "online", "replace", "clear", "import",
                           "export", "attach", "detach", "add", "upgrade", "initialize", "trim"}),
    ("btrfs", "subvolume"): frozenset({"delete", "create", "snapshot"}),
    ("btrfs", "device"): frozenset({"remove", "add", "delete"}),
    ("btrfs", "filesystem"): frozenset({"resize", "defragment"}),
    ("btrfs", "balance"): frozenset({"start"}),
    ("qm",): frozenset({"start", "stop", "shutdown", "reboot", "reset", "suspend", "resume",
                        "destroy", "set", "migrate", "rollback", "restore", "resize", "clone",
                        "create", "importdisk", "move-disk", "move_disk", "disk", "template",
                        "unlink", "delsnapshot", "snapshot"}),
    ("pct",): frozenset({"start", "stop", "shutdown", "reboot", "destroy", "set", "migrate",
                         "rollback", "restore", "resize", "clone", "create", "template",
                         "delsnapshot", "snapshot", "exec", "push"}),
    ("pvesh",): frozenset({"create", "set", "delete"}),
    ("pvesm",): frozenset({"remove", "add", "set", "alloc", "free"}),
    ("virsh",): frozenset({"start", "shutdown", "destroy", "reboot", "reset", "undefine", "define",
                           "attach-device", "attach-disk", "attach-interface", "detach-device",
                           "detach-disk", "detach-interface", "snapshot-revert",
                           "snapshot-delete", "setmem", "setvcpus", "migrate", "suspend",
                           "resume", "managedsave", "restore"}),
    ("vboxmanage",): frozenset({"startvm", "controlvm", "unregistervm", "modifyvm", "snapshot"}),
    ("kubectl",): frozenset({"apply", "delete", "rollout", "scale", "patch", "replace", "drain",
                             "cordon", "uncordon", "taint", "exec", "edit", "create", "expose",
                             "set", "annotate", "label", "cp"}),
    ("k3s", "kubectl"): frozenset({"apply", "delete", "rollout", "scale", "patch", "replace",
                                   "drain", "cordon", "uncordon", "taint", "exec", "edit",
                                   "create", "expose", "set"}),
    ("helm",): frozenset({"install", "upgrade", "uninstall", "rollback", "delete"}),
    ("talosctl",): frozenset({"apply-config", "upgrade", "reboot", "reset", "shutdown", "edit",
                              "patch"}),
    ("terraform",): frozenset({"apply", "destroy", "import", "taint", "untaint", "state"}),
    ("tofu",): frozenset({"apply", "destroy", "import", "taint", "untaint", "state"}),
    ("pulumi",): frozenset({"up", "destroy"}),
    ("caddy",): frozenset({"reload", "run", "start", "stop"}),
    ("pihole",): frozenset({"restartdns", "enable", "disable", "updatePihole", "updateGravity"}),
    ("unbound-control",): frozenset({"reload", "flush", "flush_zone", "stop", "start",
                                     "local_zone", "local_data"}),
}

# Executables that are live UNLESS their first non-option word (or an option) is one of these.
READ_UNLESS: dict[str, frozenset[str]] = {
    "ufw": frozenset({"status", "show", "version", "--version", "help", "--help"}),
    "nft": frozenset({"list", "monitor", "describe", "-c", "--check"}),
    "firewall-cmd": frozenset({"--state", "--get-active-zones", "--get-zones", "--get-services",
                               "--get-default-zone", "--version", "--help"}),
    "crontab": frozenset({"-l"}),
    "certbot": frozenset({"certificates", "show_account", "--version", "--help", "--dry-run"}),
    "haproxy": frozenset({"-c", "-v", "-vv"}),
    "ansible-playbook": frozenset({"--check", "--syntax-check", "--list-tasks", "--list-hosts"}),
}

# Executables that are live only when an option matches (they may also carry word rules above).
FLAG_LIVE: dict[str, re.Pattern[str]] = {
    # Long forms carry the same authority as the short cluster: GNU documents `-r, -R, --recursive`
    # and `-f, --force`, so matching only `-rf` left `rm --recursive --force` unmatched.
    "rm": re.compile(r"^-[A-Za-z]*[rRf]|^--(?:recursive|force)$"),
    "chown": re.compile(r"^-[A-Za-z]*R|^--recursive$"),
    "chmod": re.compile(r"^-[A-Za-z]*R|^--recursive$"),
    "iptables": re.compile(r"^-(?:A|I|D|F|X|P|R|N|E|Z)$|^--(?:append|insert|delete|flush|"
                           r"delete-chain|policy|replace|new-chain|rename-chain|zero)$"),
    "ip6tables": re.compile(r"^-(?:A|I|D|F|X|P|R|N|E|Z)$|^--(?:append|insert|delete|flush|"
                            r"delete-chain|policy|replace|new-chain|rename-chain|zero)$"),
    "nginx": re.compile(r"^-s$"),
    "pacman": re.compile(r"^-[SRU]"),
    "pihole": re.compile(r"^-(?:g|up|a)$"),
    "ansible": re.compile(r"^-m$"),   # resolved further in _classify: read modules are exempt
}
_ANSIBLE_READ_MODULES = frozenset({"ping", "setup", "gather_facts", "debug", "stat", "slurp",
                                   "fetch"})
# Positively bound diagnostic command paths. The live roster remains intact: a reader's operand
# named `restart` must not be interpreted as an executable subcommand. Unknown option arity or
# an unlisted command still uses the conservative live matcher below, never this read path.
_DIAGNOSTIC_PATHS = frozenset({
    ("docker", "inspect"), ("docker", "logs"), ("docker", "ps"),
    ("docker", "compose", "ps"), ("docker", "compose", "logs"),
    ("docker", "compose", "config"),
    ("systemctl", "status"), ("systemctl", "show"), ("systemctl", "is-active"),
    ("kubectl", "rollout", "status"), ("kubectl", "rollout", "history"),
    ("terraform", "state", "list"), ("terraform", "state", "show"),
    ("terraform", "state", "pull"),
    ("tofu", "state", "list"), ("tofu", "state", "show"), ("tofu", "state", "pull"),
})
_DIAGNOSTIC_VALUE_OPTIONS = {
    "docker": frozenset({"--context", "-c", "--host", "-H", "--config", "--log-level", "-l",
                          "--tlscacert", "--tlscert", "--tlskey"}),
    "compose": frozenset({"--file", "-f", "--project-name", "-p", "--project-directory",
                           "--env-file", "--profile", "--parallel", "--progress", "--ansi"}),
    "systemctl": frozenset({"--host", "-H", "--machine", "-M", "--root", "--image"}),
    "kubectl": frozenset({"--context", "--namespace", "-n", "--kubeconfig", "--cluster",
                           "--user", "--server", "-s", "--request-timeout"}),
}
_DIAGNOSTIC_SWITCHES = {
    "docker": frozenset({"--debug", "-D", "--tls", "--tlsverify"}),
    "compose": frozenset({"--compatibility", "--all-resources", "--dry-run"}),
    "systemctl": frozenset({"--user", "--system", "--no-pager", "--no-legend", "--plain"}),
}


def _is_diagnostic(tokens: list[str]) -> bool:
    """Recognize a read verb before considering its arguments; never guess option arity."""
    exe = _base(tokens[0])
    if exe == "mount":
        # No operands lists mounts. Other options may cause an effect even without operands
        # (`-a`), so the listing-only label switch is the sole supported option here.
        return all(token in ("-l", "--show-labels") for token in tokens[1:])
    # Normalize only supported frontends for diagnostic recognition. The original argv
    # still reaches the live matcher if no complete read path is recognized.
    if exe == "docker-compose":
        tokens = ["docker", "compose", *tokens[1:]]
        exe = "docker"
    elif exe == "k3s" and tokens[1:2] == ["kubectl"]:
        tokens = ["kubectl", *tokens[2:]]
        exe = "kubectl"
    path = (exe,)
    remaining = tokens[1:]
    while remaining:
        token, *remaining = remaining
        if token.startswith("-"):
            scope = "compose" if path == ("docker", "compose") else exe
            flag, equals, _ = token.partition("=")
            if exe in ("terraform", "tofu") and flag == "-chdir" and equals:
                continue
            values = _DIAGNOSTIC_VALUE_OPTIONS.get(scope, frozenset())
            if flag in values:
                if not equals:
                    if not remaining:
                        return False
                    remaining = remaining[1:]
                continue
            if flag in _DIAGNOSTIC_SWITCHES.get(scope, frozenset()):
                continue
            # The documented single-letter value options also accept an attached value.
            if len(token) > 2 and token[:2] in values and not token.startswith("--"):
                continue
            return False
        path += (token,)
        if path in _DIAGNOSTIC_PATHS:
            return True
        if not any(candidate[:len(path)] == path for candidate in _DIAGNOSTIC_PATHS):
            return False
    return False


# How far ahead of a compound prefix a global option's value may push it (`docker --context X
# compose up`). Bounded deliberately: widening it trades missed live effects for false prompts.
_OPTION_VALUE_WINDOW = 3

# Wrappers the gate looks through. Value: options that consume the next token.
WRAPPERS: dict[str, frozenset[str]] = {
    # Long aliases matter as much as the short forms: `ionice --class 2 systemctl restart` read
    # `2` as the wrapped executable and gated nothing, exactly as `-c 2` would have without `-c`
    # listed. Where a tool documents a long option that takes a value, it belongs here.
    "sudo": frozenset({"-u", "--user", "-g", "--group", "-C", "--close-from", "-D", "--chdir",
                       "-h", "--host", "-p", "--prompt", "-r", "--role", "-t", "--type",
                       "-T", "--command-timeout", "-U", "--other-user"}),
    "doas": frozenset({"-u", "-C"}),
    "env": frozenset({"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}),
    "nohup": frozenset(),
    "nice": frozenset({"-n", "--adjustment"}),
    "ionice": frozenset({"-c", "--class", "-n", "--classdata", "-p", "--pid"}),
    "timeout": frozenset({"-k", "--kill-after", "-s", "--signal"}),
    "time": frozenset({"-f", "--format", "-o", "--output"}),
    "stdbuf": frozenset({"-i", "--input", "-o", "--output", "-e", "--error"}),
    "chroot": frozenset({"--userspec", "--groups"}),
    # Bash execution prefixes: each runs the command that follows it, so looking through them is
    # the only way the real verb reaches classification (`command systemctl restart jellyfin`).
    "command": frozenset({"-p"}),
    "exec": frozenset({"-a"}),
    "builtin": frozenset(),
}
# Wrappers whose documented syntax puts MANDATORY positional operands before the wrapped command:
# `timeout [OPTION] DURATION COMMAND`, `chroot [OPTION] NEWROOT [COMMAND]`. Without this the
# operand is read as the executable, so `timeout 10 systemctl restart jellyfin` classified `10`,
# found nothing, and returned no decision while the restart ran.
WRAPPER_OPERANDS: dict[str, int] = {"timeout": 1, "chroot": 1}
_SSH_ARG_OPTIONS = frozenset({"-B", "-b", "-c", "-D", "-E", "-e", "-F", "-I", "-i", "-J", "-L",
                              "-l", "-m", "-O", "-o", "-p", "-Q", "-R", "-S", "-W", "-w"})
_SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "fish"})
_CONTROL = ("&&", "||", ";", "|", "&")
_REDIRECT_TARGET_RE = re.compile(r"^\d*[<>]{1,2}$")          # `>`, `>>`, `2>`: next token is the target
_REDIRECT_SELF_RE = re.compile(r"^\d*[<>]+&\d*$|^\d*[<>]{1,2}\S")  # `2>&1`, `>/dev/null`: self-contained
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

ASK_REASON = (
    "sde-agents live-effect gate: matched rule `{rule}` — a Tier 2/3 live effect from "
    "homelab-engineer. This prompt is the managed gate for this exact argv; accepting it is "
    "the decision, and the agent runs the command once."
)
ASK_UNBOUND = (
    "sde-agents live-effect gate: cannot bind this argv to one approved effect ({why}) — asking. "
    "homelab-engineer must present the exact command, never a wrapper or substitution."
)
DENY_SUPPRESSED = (
    "sde-agents live-effect gate: matched rule `{rule}` but permission_mode={mode} suppresses "
    "prompts, so no human can decide this invocation. Hand the exact command to the operator "
    "(Transport: operator handoff); bypass is not a decision."
)
DENY_IDENTITY = (
    "sde-agents live-effect gate: the payload names a gated agent under a key other than "
    "`agent_type`, which carried nothing. The hook payload contract has changed, so the gate "
    "cannot tell a gated caller from the main loop and fails closed rather than silently stop "
    "gating. Hand the exact command to the operator (Transport: operator handoff), re-run "
    "scripts/probe_plugin.py, and update scripts/live-effect-gate.py."
)
DENY_NO_MODE = (
    "sde-agents live-effect gate: matched rule `{rule}` but the hook payload carries no "
    "permission_mode, so the gate cannot tell whether a human can be asked. Hand the exact "
    "command to the operator (Transport: operator handoff). If Claude Code renamed the field, "
    "update scripts/live-effect-gate.py."
)


def _base(token: str) -> str:
    return token.rsplit("/", 1)[-1]


_HEREDOC_OPENER_RE = re.compile(r"<<-?\s*(?:'([^']*)'|\"([^\"]*)\"|([A-Za-z_][A-Za-z0-9_]*))")


def _heredoc_delimiters(line: str, quote: str | None) -> tuple[list[str], str | None]:
    """Delimiters opened by this line, and the quote state carried to the next.

    Scanned rather than matched, because an opener only counts in shell OPERATOR position: a
    `<<EOF` sitting inside quotes is data (`echo '<<EOF'`), and treating it as a declaration made
    the body stripper eat every following line hunting a terminator that never arrives — which
    hides a real live command behind a quoted string. The delimiter itself may still be quoted
    (`<<'EOF'`), so it is read here in place rather than by masking quotes away first.
    """
    delimiters: list[str] = []
    index = 0
    length = len(line)
    while index < length:
        char = line[index]
        if quote is None and char == "\\":
            index += 2
            continue
        if quote is None and char in "\"'":
            quote = char
            index += 1
            continue
        if quote is not None:
            if char == quote:
                quote = None
            index += 1
            continue
        if char == "<" and line.startswith("<<", index):
            if line.startswith("<<<", index):      # here-STRING, no body to skip
                index += 3
                continue
            found = _HEREDOC_OPENER_RE.match(line, index)
            if found:
                delimiters.append(found.group(1) or found.group(2) or found.group(3))
                index = found.end()
                continue
            index += 2
            continue
        index += 1
    return delimiters, quote


def _strip_heredoc_bodies(command: str) -> str:
    """Drop heredoc BODIES before the newline split; they are data, never commands.

    Regression this repairs: once unquoted newlines became command separators, every line of a
    heredoc body became a command, so `cat > runbook <<'EOF' / systemctl restart jellyfin / EOF`
    — an ordinary Tier 1 write that merely MENTIONS a live verb — was gated as if it ran one. A
    gate that prompts on routine writes teaches the operator to click through the prompts that
    matter, so this direction is as load-bearing as the under-match it came from. What follows the
    terminator is code again and is kept.
    """
    if "<<" not in command:
        return command
    lines = command.splitlines()
    out: list[str] = []
    index = 0
    quote: str | None = None
    while index < len(lines):
        line = lines[index]
        out.append(line)
        index += 1
        # Only the delimiters introduced on THIS line open bodies, and bash consumes them in
        # order. Quote state carries across lines because a string may legitimately span them.
        delimiters, quote = _heredoc_delimiters(line, quote)
        for delimiter in delimiters:
            while index < len(lines) and lines[index].strip() != delimiter:
                index += 1
            index += 1  # the terminator line itself is not a command either
    return "\n".join(out)


def _normalize_newlines(command: str) -> str:
    """Rewrite unquoted newlines to `;` so they separate commands.

    `shlex` treats a newline as ordinary whitespace, which silently JOINS two commands into one
    token list: `git status\\ndocker compose up -d` parsed as a single `git` segment and the live
    docker command vanished from the parse entirely — (None, None), i.e. no decision, i.e. it ran.
    A backslash-newline is the shell's line CONTINUATION and joins instead, and a newline inside
    quotes is data, so both are preserved rather than split.
    """
    out: list[str] = []
    quote: str | None = None
    index = 0
    length = len(command)
    while index < length:
        char = command[index]
        if quote != "'" and char == "\\" and index + 1 < length:
            following = command[index + 1]
            if following in "\r\n":
                index += 2
                if following == "\r" and index < length and command[index] == "\n":
                    index += 1
                out.append(" ")
                continue
            out.append(char)
            out.append(following)
            index += 2
            continue
        if quote is None and char in "\"'":
            quote = char
        elif quote is not None and char == quote:
            quote = None
        elif quote is None and char in "\r\n":
            out.append(" ; ")
            index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _segments(command: str) -> list[list[str]] | None:
    """Split a shell command into simple-command token lists; None when it cannot be bound."""
    if "$(" in command or "`" in command or "<(" in command or ">(" in command:
        return None
    command = _normalize_newlines(_strip_heredoc_bodies(command))
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    segments: list[list[str]] = [[]]
    skip_next = False
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if token in _CONTROL:
            segments.append([])
            continue
        if _REDIRECT_TARGET_RE.match(token):
            skip_next = True
            continue
        if _REDIRECT_SELF_RE.match(token):
            continue          # `2>&1` carries an `&` that is not a control operator
        if any(op in token for op in _CONTROL):
            return None
        segments[-1].append(token)
    return [seg for seg in segments if seg]


def _strip_options(tokens: list[str], arg_options: frozenset[str]) -> list[str]:
    out = list(tokens)
    while out and out[0].startswith("-"):
        flag = out.pop(0)
        if flag in arg_options and out:
            out.pop(0)
    return out


def _unwrap(tokens: list[str], *, diagnostics: bool = False) -> tuple[list[str] | None, str | None]:
    """Look through wrappers; return (inner tokens, unbound reason)."""
    while tokens:
        # Only prefix assignments belong to the shell/env wrapper. An assignment-shaped option
        # value (`docker --config cfg=prod restart inspect`) is an argv operand, not disposable.
        while tokens and _ASSIGN_RE.match(tokens[0]):
            tokens = tokens[1:]
        if not tokens:
            return [], None
        head = tokens[0]
        # Shell grouping puts a reserved token where the executable should be, so the real verb is
        # never classified: `(systemctl restart jellyfin)` and `{ systemctl restart jellyfin ; }`
        # both run the restart. The parser does not model group boundaries, so it says so.
        if head[:1] in ("(", "{", "!") or head in (")", "}"):
            return None, "shell grouping or reserved syntax hides the command boundary"
        # The executable itself comes from an expansion, so its identity is not in this argv:
        # `cmd=systemctl; $cmd restart jellyfin` restarts the service either way.
        if "$" in head:
            return None, "the executable comes from a parameter expansion"
        exe = _base(head)
        if exe in _SHELLS:
            if "-c" in tokens[1:]:
                return None, f"wrapper shell `{exe} -c`"
            return None, f"interactive shell `{exe}`"
        if exe in ("eval", "xargs", "su"):
            return None, f"`{exe}` cannot bind an argv"
        if exe == "find" and any(token in ("-exec", "-execdir", "-delete", "-ok") for token in tokens):
            return None, "`find -exec`/`-delete` runs an unbound command"
        if exe == "sudo" and any(token in ("-i", "-s", "-e") for token in tokens[1:]):
            return None, "`sudo -i`/`-s`/`-e` opens an unbound shell"
        if exe == "ssh":
            # ProxyCommand/LocalCommand execute on the LOCAL host, before and independently of the
            # remote command. `_strip_options` discarded them as ordinary options, so
            # `ssh -oProxyCommand='systemctl restart jellyfin' host true` classified only `true`.
            # The payload is an arbitrary shell string, so it is never bound — it is asked.
            if any(name in " ".join(tokens[1:]).lower()
                   for name in ("proxycommand", "localcommand")):
                return None, "`ssh` option runs a local command (ProxyCommand/LocalCommand)"
            rest = _strip_options(tokens[1:], _SSH_ARG_OPTIONS)
            if len(rest) < 2:
                return None, "interactive `ssh` with no remote command"
            remote = " ".join(rest[1:])
            segments = _segments(remote)
            if segments is None:
                return None, "remote `ssh` command cannot be parsed"
            for segment in segments:
                inner, why = _unwrap(segment, diagnostics=diagnostics)
                if why is not None:
                    return None, why
                if inner and _classify(inner, diagnostics=diagnostics) is not None:
                    return inner, None
            return segments[-1], None
        if exe in WRAPPERS:
            tokens = _strip_options(tokens[1:], WRAPPERS[exe])
            for _ in range(WRAPPER_OPERANDS.get(exe, 0)):
                if tokens:
                    tokens.pop(0)
            continue
        return tokens, None
    return [], None


def _classify(tokens: list[str], *, diagnostics: bool = False) -> str | None:
    """The matched live rule for one simple command, or None for a reader/unknown."""
    if not tokens:
        return None
    if diagnostics and _is_diagnostic(tokens):
        return None
    # Keep the legacy conservative view for live detection: preserving assignment-shaped option
    # values must not push a formerly detected live verb out of its bounded scan window. This
    # lossy view is never evidence for recognizing a diagnostic command above.
    tokens = [token for token in tokens if not _ASSIGN_RE.match(token)]
    if not tokens:
        return None
    exe = _base(tokens[0])
    words = [token for token in tokens[1:] if not token.startswith("-")]
    options = [token for token in tokens[1:] if token.startswith("-")]
    if exe in ALWAYS_LIVE:
        return exe
    if exe in READ_UNLESS:
        first = words[0] if words else ""
        if first in READ_UNLESS[exe] or any(opt in READ_UNLESS[exe] for opt in options):
            return None
        if exe == "firewall-cmd" and any(opt.startswith(("--list", "--query", "--get")) for opt in options):
            return None
        return exe
    if exe in FLAG_LIVE:
        if exe == "ansible":
            module = tokens[tokens.index("-m") + 1] if "-m" in tokens[:-1] else ""
            if "--check" in tokens or module in _ANSIBLE_READ_MODULES:
                return None
            return "ansible"
        if any(FLAG_LIVE[exe].match(opt) for opt in options):
            return exe
        # no flag matched: fall through — the same executable may also carry word rules
    longest: str | None = None
    for prefix, live in LIVE_SUBCOMMANDS.items():
        if prefix[0] != exe:
            continue
        rest = list(prefix[1:])
        # A GLOBAL option's value lands among the words ahead of the compound prefix
        # (`docker --context production compose up`, `ip -n lab link set`), so requiring the
        # prefix at position 0 missed those entirely. No table knows every tool's option arity,
        # so the prefix is searched within a small leading window instead. A single-word prefix
        # needs no window: the `following` scan below already covers the option-value case.
        starts = range(_OPTION_VALUE_WINDOW) if rest else range(1)
        for start in starts:
            if words[start:start + len(rest)] != rest:
                continue
            # An option's argument (`-f docker-compose.yml`) sits among the words ahead of the
            # subcommand, so the subcommand is the first LIVE word within the next three — a
            # false positive here is one extra prompt.
            following = words[start + len(rest):start + len(rest) + 3]
            hit = next((word for word in following if word in live), None)
            if hit is not None:
                rule = " ".join(prefix + (hit,))
                if longest is None or len(rule) > len(longest):
                    longest = rule
    return longest


def match(command: str) -> tuple[str | None, str | None]:
    """(matched live rule, unbound reason) — (None, None) means no decision."""
    segments = _segments(command)
    if segments is None:
        return None, "command substitution, an unbalanced quote, or an operator inside a word"
    # shlex strips quotes before _segments discards redirection-shaped tokens. For example,
    # quoted '>cfg' may be an option value. Do not trust shifted positions for a read shortcut;
    # keep the pre-existing conservative matcher for any command containing that syntax.
    diagnostics = not any(char in command for char in "<>")
    for segment in segments:
        inner, why = _unwrap(segment, diagnostics=diagnostics)
        if why is not None:
            return None, why
        rule = _classify(inner or [], diagnostics=diagnostics)
        if rule is not None:
            return rule, None
    return None, None


def _decision(kind: str, why: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": kind,
                                   "permissionDecisionReason": why}}


def decide(payload: dict) -> tuple[int, dict | None]:
    policy = os.environ.get("SDE_AGENTS_LIVE_EFFECT_POLICY", "host")
    if policy == "host":
        return EXIT_ALLOW, None
    if payload.get("tool_name") != "Bash" or payload.get("agent_type") not in _GATED:
        # Contract canary, the guard's (readonly-guard.py, `main`) applied to this roster. If
        # `agent_type` is renamed upstream while the payload still names a gated agent under some
        # other agent-ish key, every call would look like an unrelated caller and the gate would
        # quietly stop gating — the silent-disarm class this fleet hardens against. Keyed, not a
        # substring search: `tool_input` is excluded because the command is user-controlled text
        # (`git commit -m "fix sde-agents:homelab-engineer"` must not be denied), and only keys
        # whose NAME contains "agent" are consulted, so `cwd` and `transcript_path` cannot trip it.
        # Residual: a rename to a key without "agent" in it is the probe's to catch.
        if payload.get("tool_name") == "Bash" and payload.get("agent_type") is None and any(
            "agent" in key.lower() and isinstance(value, str) and value in _GATED
            for key, value in payload.items()
            if key != "tool_input"
        ):
            return EXIT_DENY, _decision("deny", DENY_IDENTITY)
        return EXIT_ALLOW, None
    if policy != "prompt":
        return EXIT_DENY, _decision(
            "deny", "Invalid SDE_AGENTS_LIVE_EFFECT_POLICY: operator must select host or prompt "
            "in the host launch environment; the agent must not change policy to authorize itself.",
        )
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return EXIT_INDETERMINATE, None
    rule, why = match(command)
    if rule is None and why is None:
        return EXIT_ALLOW, None
    label = rule if rule is not None else f"unbound: {why}"
    mode = payload.get("permission_mode")
    if mode is None:
        return EXIT_DENY, _decision("deny", DENY_NO_MODE.format(rule=label))
    if mode in SUPPRESSED_MODES:
        return EXIT_DENY, _decision("deny", DENY_SUPPRESSED.format(rule=label, mode=mode))
    if rule is None:
        return EXIT_ASK, _decision("ask", ASK_UNBOUND.format(why=why))
    return EXIT_ASK, _decision("ask", ASK_REASON.format(rule=rule))


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except ValueError:
        sys.exit(EXIT_INDETERMINATE)
    if not isinstance(payload, dict):
        sys.exit(EXIT_INDETERMINATE)
    code, decision = decide(payload)
    if decision is not None:
        sys.stdout.write(json.dumps(decision, separators=(",", ":")))
    sys.exit(code)


if __name__ == "__main__":
    main()
