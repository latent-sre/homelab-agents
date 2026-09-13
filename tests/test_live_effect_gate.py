"""Offline tests for scripts/live-effect-gate.py.

Runs the gate exactly as the hook does: as a subprocess with the pending tool call piped as JSON
on stdin. The verdict is carried by the EXIT CODE as well as stdout (42 no decision / 43 deny /
44 indeterminate / 45 ask), so the hook can tell the real gate from a stand-in interpreter that
merely exits 0; `decision()` asserts the two agree on every call.

The gate is registered SESSION-WIDE (hooks/hooks.json), so it must no-op for every caller it does
not name. A payload WITHOUT `agent_type` therefore exercises nothing: `bash_call` supplies the
gated agent by default, or the whole roster below would pass while testing the short-circuit.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from scripts import validate_fleet

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "live-effect-gate.py"
gate = validate_fleet.load_gate(REPO)
guard = validate_fleet.load_guard(REPO)

HOMELAB = "sde-agents:homelab-engineer"


def run_gate(stdin_text: str, policy: str | None = "prompt") -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("SDE_AGENTS_LIVE_EFFECT_POLICY", None)
    if policy is not None:
        env["SDE_AGENTS_LIVE_EFFECT_POLICY"] = policy
    return subprocess.run(
        [sys.executable, "-I", "-S", str(GATE)],
        input=stdin_text.encode("utf-8"),
        capture_output=True,
        env=env,
        timeout=30,
    )


def bash_call(command: str, agent_type: str | None = HOMELAB, mode: str | None = "default") -> str:
    data: dict = {
        "hook_event_name": "PreToolUse",
        "session_id": "s-1",
        "cwd": str(REPO),
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    if mode is not None:
        data["permission_mode"] = mode
    if agent_type is not None:
        data["agent_id"] = "a-1"
        data["agent_type"] = agent_type
    return json.dumps(data)


def decision(proc: subprocess.CompletedProcess) -> str:
    """'none' / 'deny' / 'ask' / 'indeterminate', asserting exit code and stdout agree."""
    out = proc.stdout.decode("utf-8").strip()
    if proc.returncode == gate.EXIT_ALLOW:
        assert not out, f"EXIT_ALLOW but stdout was not empty: {out!r}"
        return "none"
    if proc.returncode == gate.EXIT_INDETERMINATE:
        assert not out, f"EXIT_INDETERMINATE but stdout was not empty: {out!r}"
        return "indeterminate"
    assert proc.returncode in (gate.EXIT_DENY, gate.EXIT_ASK), (
        f"unexpected exit {proc.returncode}: stdout={out!r} stderr={proc.stderr.decode('utf-8')!r}"
    )
    verdict = json.loads(out)["hookSpecificOutput"]["permissionDecision"]
    expected = {gate.EXIT_DENY: "deny", gate.EXIT_ASK: "ask"}[proc.returncode]
    assert verdict == expected, f"exit {proc.returncode} but stdout said {verdict!r}"
    return verdict


def reason(proc: subprocess.CompletedProcess) -> str:
    return json.loads(proc.stdout.decode("utf-8"))["hookSpecificOutput"]["permissionDecisionReason"]


class OperatorPolicyTests(unittest.TestCase):
    def test_default_and_host_policy_leave_actual_host_permissions_in_charge(self) -> None:
        for policy in (None, "host"):
            for mode in ("default", "dontAsk", "bypassPermissions", None):
                with self.subTest(policy=policy, mode=mode):
                    result = run_gate(bash_call("systemctl restart example", mode=mode), policy)
                    self.assertEqual("none", decision(result))

    def test_prompt_policy_preserves_interposition(self) -> None:
        self.assertEqual("ask", decision(run_gate(bash_call("systemctl restart example"))))
        self.assertEqual("deny", decision(run_gate(bash_call("systemctl restart example", mode="dontAsk"))))

    def test_invalid_policy_cannot_silently_disable_requested_control(self) -> None:
        for policy in ("", "promtp", "HOST"):
            with self.subTest(policy=policy):
                result = run_gate(bash_call("systemctl restart example"), policy)
                self.assertEqual("deny", decision(result))
                self.assertIn("SDE_AGENTS_LIVE_EFFECT_POLICY", reason(result))

    def test_policy_selection_is_not_accepted_from_tool_payload(self) -> None:
        payload = json.loads(bash_call("systemctl restart example"))
        payload["SDE_AGENTS_LIVE_EFFECT_POLICY"] = "host"
        self.assertEqual("ask", decision(run_gate(json.dumps(payload), "prompt")))


class ConstantsPinnedToTheGuard(unittest.TestCase):
    def test_exit_codes_and_plugin_name_match_the_guard(self) -> None:
        # The hook shell string translates BOTH scripts' codes; drift here is a disarmed hook.
        self.assertEqual(guard.EXIT_ALLOW, gate.EXIT_ALLOW)
        self.assertEqual(guard.EXIT_DENY, gate.EXIT_DENY)
        self.assertEqual(guard.EXIT_INDETERMINATE, gate.EXIT_INDETERMINATE)
        self.assertEqual(45, gate.EXIT_ASK)
        self.assertNotIn(gate.EXIT_ASK, {guard.EXIT_ALLOW, guard.EXIT_DENY, guard.EXIT_INDETERMINATE})
        self.assertEqual(guard.PLUGIN_NAME, gate.PLUGIN_NAME)

    def test_gated_and_guarded_rosters_are_disjoint(self) -> None:
        # A read-only agent gets the guard; a live-effect agent gets the gate. Both on one agent
        # would deny every live verb before the gate could ask.
        self.assertFalse(set(gate.GATED_AGENT_NAMES) & set(guard.GUARDED_AGENT_NAMES))


class Scoping(unittest.TestCase):
    LIVE = "/usr/bin/docker compose -f /srv/media/docker-compose.yml up -d jellyfin"

    def test_main_loop_is_never_gated(self) -> None:
        self.assertEqual("none", decision(run_gate(bash_call(self.LIVE, agent_type=None))))

    def test_other_agents_are_never_gated(self) -> None:
        for other in ("sde-agents:sde-fullstack", "sde-agents:code-reviewer", "sde-fullstack"):
            with self.subTest(agent=other):
                self.assertEqual("none", decision(run_gate(bash_call(self.LIVE, agent_type=other))))

    def test_bare_and_namespaced_names_are_both_gated(self) -> None:
        for name in ("homelab-engineer", HOMELAB):
            with self.subTest(agent=name):
                self.assertEqual("ask", decision(run_gate(bash_call(self.LIVE, agent_type=name))))

    def test_non_bash_tools_get_no_decision(self) -> None:
        payload = json.loads(bash_call(self.LIVE))
        payload["tool_name"] = "Write"
        self.assertEqual("none", decision(run_gate(json.dumps(payload))))

    def test_malformed_payload_is_indeterminate(self) -> None:
        self.assertEqual("indeterminate", decision(run_gate(bash_call(self.LIVE)[:-1])))
        self.assertEqual("indeterminate", decision(run_gate("[]")))


class Modes(unittest.TestCase):
    LIVE = "sudo systemctl restart jellyfin"

    def test_prompting_modes_ask(self) -> None:
        for mode in ("default", "acceptEdits", "plan"):
            with self.subTest(mode=mode):
                out = run_gate(bash_call(self.LIVE, mode=mode))
                self.assertEqual("ask", decision(out))
                self.assertIn("matched rule `systemctl restart`", reason(out))

    def test_suppressed_modes_deny_with_operator_handoff(self) -> None:
        for mode in sorted(gate.SUPPRESSED_MODES):
            with self.subTest(mode=mode):
                out = run_gate(bash_call(self.LIVE, mode=mode))
                self.assertEqual("deny", decision(out))
                self.assertIn(mode, reason(out))
                self.assertIn("operator handoff", reason(out))

    def test_missing_mode_fails_closed_for_a_live_verb_only(self) -> None:
        self.assertEqual("deny", decision(run_gate(bash_call(self.LIVE, mode=None))))
        self.assertIn("permission_mode", reason(run_gate(bash_call(self.LIVE, mode=None))))
        self.assertEqual("none", decision(run_gate(bash_call("git status", mode=None))))


class Roster(unittest.TestCase):
    ASKS = (
        "docker compose -f /srv/media/docker-compose.yml up -d jellyfin",
        "docker-compose up -d",
        "docker compose down",
        "docker restart jellyfin",
        "docker volume rm media_cache",
        "docker system prune -f",
        "podman compose up -d",
        "systemctl restart jellyfin",
        "systemctl --user enable --now syncthing",
        "systemctl daemon-reload",
        "sudo -u root systemctl reload caddy",
        "ssh nuc-01 'systemctl restart jellyfin'",
        "ssh -p 2222 admin@nuc-01 docker compose up -d",
        "reboot",
        "shutdown -r now",
        "apt-get install -y caddy",
        "apt upgrade -y",
        "dnf remove -y nginx",
        "pacman -Syu",
        "ufw allow 443/tcp",
        "nft add rule inet filter input tcp dport 22 accept",
        "iptables -A INPUT -p tcp --dport 22 -j ACCEPT",
        "firewall-cmd --add-service=https --permanent",
        "ip link set eth0 down",
        "ip route add 10.0.0.0/24 via 10.0.0.1",
        "nmcli con up lan",
        "wg-quick up wg0",
        "zfs destroy tank/media@old",
        "zpool export tank",
        "lvremove /dev/vg0/old",
        "mkfs.ext4 /dev/sdb1",
        "wipefs -a /dev/sdb",
        "dd if=/dev/zero of=/dev/sdb bs=1M",
        "mount /dev/sdb1 /mnt/backup",
        "rm -rf /srv/media/jellyfin-cache",
        "rm -f /etc/caddy/Caddyfile",
        "chown -R jellyfin:jellyfin /srv/media",
        "qm stop 104",
        "pct destroy 200",
        "virsh shutdown ci-runner",
        "kubectl apply -f deploy.yaml",
        "kubectl rollout restart deployment/jellyfin",
        "helm upgrade --install grafana grafana/grafana",
        "ansible-playbook site.yml",
        "terraform apply",
        "caddy reload --config /etc/caddy/Caddyfile",
        "nginx -s reload",
        "certbot renew",
        "crontab /tmp/new-cron",
        "kill -9 4242",
        "pkill -f jellyfin",
        "useradd -m operator",
        "passwd operator",
        "bash -c 'docker compose up -d'",
        "sh -c \"systemctl restart jellyfin\"",
        "eval \"$CMD\"",
        "docker compose -f \"$(pwd)/docker-compose.yml\" up -d",
        "find /srv -name '*.log' -exec rm {} \\;",
        "ssh nuc-01",
        "sudo -i",
        "docker compose ps && docker compose up -d",
        "echo 'unbalanced",
    )
    NO_DECISION = (
        "git status",
        "git commit -am 'pin jellyfin'",
        "git push origin main",
        "docker compose -f /srv/media/docker-compose.yml ps",
        "docker compose logs --tail 100 jellyfin",
        "docker compose config",
        "docker image ls | grep jellyfin",
        "docker inspect jellyfin",
        "systemctl status jellyfin",
        "systemctl is-active caddy",
        "journalctl -u jellyfin -n 200",
        "apt list --upgradable",
        "dnf check-update",
        "ufw status verbose",
        "nft list ruleset",
        "iptables -L -n",
        "firewall-cmd --list-all",
        "ip addr show",
        "ip route",
        "zfs list -t snapshot",
        "zpool status",
        "lsblk -f",
        "df -h",
        "rm /tmp/scratch.txt",
        "qm list",
        "kubectl get pods -A",
        "kubectl describe deployment jellyfin",
        "ansible-playbook site.yml --check --diff",
        "terraform plan",
        "caddy validate --config /etc/caddy/Caddyfile",
        "nginx -t",
        "certbot certificates",
        "crontab -l",
        "ssh nuc-01 'systemctl status jellyfin'",
        "sudo systemctl status jellyfin",
        "curl -fsS http://localhost:8096/health",
        "dig jellyfin.lan",
        "ps aux | grep jellyfin",
        "cat /srv/media/docker-compose.yml",
        "docker compose logs jellyfin 2>&1 | tail -50",
    )

    def test_live_effects_ask(self) -> None:
        for command in self.ASKS:
            with self.subTest(command=command):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_readers_get_no_decision(self) -> None:
        for command in self.NO_DECISION:
            with self.subTest(command=command):
                self.assertEqual("none", decision(run_gate(bash_call(command))))

    def test_generated_coverage_of_the_whole_roster(self) -> None:
        """Every table entry must drive the classifier; a typo'd or orphaned entry fails here.

        ASKS above is the curated behavioral sample; this test walks the tables themselves so
        that an executable added to a roster without ever being exercised cannot pass silently.
        """
        flag_probe = {
            "rm": "rm -rf /srv/x", "chown": "chown -R a:a /srv/x", "chmod": "chmod -R 755 /srv/x",
            "iptables": "iptables -A INPUT -j DROP", "ip6tables": "ip6tables -F",
            "nginx": "nginx -s reload", "pacman": "pacman -Syu",
            "ansible": "ansible all -m shell -a id", "pihole": "pihole -g",
        }
        for exe in sorted(gate.ALWAYS_LIVE):
            with self.subTest(always=exe):
                self.assertEqual("ask", decision(run_gate(bash_call(f"{exe} x"))))
        for prefix, live in sorted(gate.LIVE_SUBCOMMANDS.items()):
            with self.subTest(prefix=prefix):
                head = " ".join(prefix)
                self.assertEqual("ask", decision(run_gate(bash_call(f"{head} {sorted(live)[0]} x"))))
                self.assertEqual("none", decision(run_gate(bash_call(f"{head} zzz-not-live x"))))
        for exe, reads in sorted(gate.READ_UNLESS.items()):
            with self.subTest(read_unless=exe):
                self.assertEqual("ask", decision(run_gate(bash_call(f"{exe} zzz-live"))))
                self.assertEqual("none", decision(run_gate(bash_call(f"{exe} {sorted(reads)[0]}"))))
        self.assertEqual(set(flag_probe), set(gate.FLAG_LIVE), "every FLAG_LIVE executable needs a probe here")
        for exe, command in sorted(flag_probe.items()):
            with self.subTest(flag=exe):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_reason_names_the_matched_rule(self) -> None:
        out = run_gate(bash_call("docker compose -f x.yml up -d web"))
        self.assertIn("matched rule `docker compose up`", reason(out))
        out = run_gate(bash_call("ssh nuc-01 'zfs destroy tank/x'"))
        self.assertIn("matched rule `zfs destroy`", reason(out))
        out = run_gate(bash_call("bash -c 'true'"))
        self.assertIn("cannot bind", reason(out))


class DiagnosticCommands(unittest.TestCase):
    """Read verbs and their operands must not become live verbs or suppressed-mode denials."""

    def test_diagnostics_do_not_acquire_live_authority_requirements(self) -> None:
        for command in (
            "mount", "mount -l", "mount --show-labels",
            "docker inspect restart", "docker logs stop",
            "docker --context restart inspect stop",
            "docker -H tcp://host:2376 inspect restart",
            "docker compose -f up -p restart logs stop",
            "docker compose --file=up --project-name=restart ps",
            "systemctl status restart", "systemctl --user show reboot",
            "kubectl rollout status deployment/jellyfin",
            "kubectl --context restart rollout history deployment/jellyfin",
            "kubectl -n media rollout status deployment/jellyfin",
            "terraform state list", "terraform state show resource.restart",
            "terraform -chdir=infra state pull", "tofu state list",
            "ssh nuc-01 'docker inspect restart'",
        ):
            for mode in ("default", "dontAsk", "auto", "bypassPermissions", None):
                with self.subTest(command=command, mode=mode):
                    self.assertEqual("none", decision(run_gate(bash_call(command, mode=mode))))

    def test_boolean_values_and_supported_aliases_are_diagnostics(self) -> None:
        for command in (
            "docker --tls=false inspect restart", "docker --debug=true inspect restart",
            "docker -D=false logs stop", "docker --tlsverify=false ps restart",
            "docker-compose logs restart", "docker-compose -f up -p restart ps",
            "k3s kubectl rollout status deployment/jellyfin",
            "k3s kubectl --context restart rollout history deployment/jellyfin",
            "ssh nuc-01 'docker-compose logs restart'",
        ):
            for mode in ("default", "dontAsk", "auto", "bypassPermissions", None):
                with self.subTest(command=command, mode=mode):
                    self.assertEqual("none", decision(run_gate(bash_call(command, mode=mode))))

    def test_aliases_and_boolean_flags_do_not_exempt_live_commands(self) -> None:
        for command in (
            "docker --tls=false restart jellyfin", "docker --debug=true restart jellyfin",
            "docker-compose -f logs up -d", "k3s kubectl rollout restart deployment/jellyfin",
            "k3s kubectl rollout undo deployment/jellyfin",
            "docker-compose logs restart && docker-compose restart jellyfin",
            "k3s kubectl --unknown-option rollout status restart",
        ):
            for mode, expected in (("default", "ask"), ("dontAsk", "deny")):
                with self.subTest(command=command, mode=mode):
                    self.assertEqual(expected, decision(run_gate(bash_call(command, mode=mode))))

    def test_neighboring_effects_keep_the_managed_gate(self) -> None:
        for command in (
            "mount -a", "mount /dev/sdb1 /mnt/backup", "mount -o remount,ro /srv",
            "docker --context inspect restart jellyfin",
            "docker compose -f logs -p ps up -d",
            "kubectl rollout restart deployment/jellyfin",
            "kubectl rollout undo deployment/jellyfin", "kubectl rollout pause deployment/jellyfin",
            "terraform state rm resource.x", "terraform state mv resource.x resource.y",
            "terraform state push snapshot.json", "terraform state replace-provider old new",
            "tofu state rm resource.x", "terraform state future-command",
            "docker inspect restart && docker restart jellyfin",
            "mount; systemctl restart jellyfin",
            "ssh nuc-01 'terraform state list; terraform apply'",
            "kubectl --unknown-option value rollout restart deployment/jellyfin",
        ):
            for mode, expected in (("default", "ask"), ("dontAsk", "deny")):
                with self.subTest(command=command, mode=mode):
                    self.assertEqual(expected, decision(run_gate(bash_call(command, mode=mode))))

    def test_unrecognized_option_arity_cannot_establish_a_diagnostic(self) -> None:
        for command in (
            "docker --unknown-option inspect restart jellyfin",
            "kubectl --unknown-option rollout status restart",
            "mount --all --show-labels",
        ):
            with self.subTest(command=command):
                self.assertEqual("deny", decision(run_gate(bash_call(command, mode="dontAsk"))))

    def test_option_operands_survive_normalization_before_diagnostic_recognition(self) -> None:
        for command in (
            "docker --config cfg=prod restart inspect",
            "docker --config '>cfg' restart inspect",
            "ssh nuc-01 \"docker --config cfg=prod restart inspect\"",
            "ssh nuc-01 \"docker --config '>cfg' restart inspect\"",
        ):
            for mode, expected in (("default", "ask"), ("dontAsk", "deny"), (None, "deny")):
                with self.subTest(command=command, mode=mode):
                    self.assertEqual(expected, decision(run_gate(bash_call(command, mode=mode))))
        for command in (
            "docker --config cfg=prod inspect restart",
            "MODE=inspect docker --config cfg=prod inspect restart",
            "env MODE=inspect docker --config cfg=prod inspect restart",
        ):
            with self.subTest(command=command):
                self.assertEqual("none", decision(run_gate(bash_call(command, mode="dontAsk"))))

    def test_redirection_shaped_data_retains_conservative_classification(self) -> None:
        # The existing splitter loses quoting around redirection-shaped operands. Until it can
        # prove those positions, do not apply the new diagnostic shortcut to this spelling.
        for command in ("docker --config '>cfg' inspect restart", "docker inspect restart 2>&1"):
            with self.subTest(command=command):
                self.assertEqual("deny", decision(run_gate(bash_call(command, mode="dontAsk"))))

    def test_retaining_operands_does_not_shrink_existing_live_detection(self) -> None:
        for command in (
            "docker compose -f a=b.yml -f c=d.yml -f e=f.yml up -d",
            "docker --config a=b --context c=d --host e=f restart inspect",
            "ssh nuc-01 'docker compose -f a=b.yml -f c=d.yml -f e=f.yml up -d'",
        ):
            for mode, expected in (("default", "ask"), ("dontAsk", "deny"), (None, "deny")):
                with self.subTest(command=command, mode=mode):
                    self.assertEqual(expected, decision(run_gate(bash_call(command, mode=mode))))


class GateBypassShapesFromReview(unittest.TestCase):
    """Argv shapes that reached "no decision" while still executing a live effect (PR #164 review).

    Risk hypothesis: `match()` under-matching is indistinguishable, at the hook boundary, from
    `match()` correctly seeing a reader -- both are (None, None) -> EXIT_ALLOW. So a parser gap is
    a SILENT hole: the gate reports success while the effect runs unprompted. Every case below was
    reproduced against the shipped parser before the fix; each asserts the prompt, and the last
    test asserts the half that actually matters -- deny under a mode that suppresses prompts.
    """

    def test_unquoted_newline_separates_commands(self) -> None:
        # shlex treats "\n" as plain whitespace, so `git status\ndocker compose up -d` collapsed
        # into a single `git` segment and the live docker command disappeared from the parse.
        for command in ("git status\ndocker compose up -d",
                        "echo hi\nsystemctl restart jellyfin",
                        "git status\r\ndocker compose up -d"):
            with self.subTest(command=command):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_backslash_newline_stays_one_command(self) -> None:
        # The inverse guard: a shell line continuation joins its lines, so the split must not
        # break `docker compose \<newline> up -d` into two unmatched halves.
        out = run_gate(bash_call("docker compose \\\n up -d web"))
        self.assertEqual("ask", decision(out))
        self.assertIn("matched rule `docker compose up`", reason(out))

    def test_newline_inside_quotes_is_not_a_separator(self) -> None:
        self.assertEqual("none", decision(run_gate(bash_call("echo 'a\nb'"))))

    def test_long_form_recursive_and_force_flags(self) -> None:
        # GNU documents `-r, -R, --recursive`; only the short cluster was recognized.
        for command in ("rm --recursive --force /srv/media",
                        "rm --force /etc/caddy/Caddyfile",
                        "chown --recursive jellyfin /srv/media",
                        "chmod --recursive 777 /srv/media"):
            with self.subTest(command=command):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_wrapper_mandatory_operands_are_skipped(self) -> None:
        # `timeout DURATION COMMAND` and `chroot NEWROOT COMMAND`: the positional operand was
        # mistaken for the wrapped executable, so the real command was never classified.
        for command in ("timeout 10 systemctl restart jellyfin",
                        "timeout -k 5 10 systemctl restart jellyfin",
                        "chroot /mnt systemctl restart jellyfin"):
            with self.subTest(command=command):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_wrapped_reader_still_gets_no_decision(self) -> None:
        # Skipping operands must not turn every wrapped reader into a prompt.
        for command in ("timeout 10 git status", "chroot /mnt git status"):
            with self.subTest(command=command):
                self.assertEqual("none", decision(run_gate(bash_call(command))))

    def test_ssh_options_that_execute_locally_are_unbound(self) -> None:
        # ProxyCommand/LocalCommand run on the LOCAL host before the remote command; the option
        # was silently stripped, leaving only a harmless-looking remote reader to classify.
        for command in ("ssh -oProxyCommand='systemctl restart jellyfin' host true",
                        "ssh -o ProxyCommand='systemctl restart jellyfin' host true",
                        "ssh -oLocalCommand='reboot' host true"):
            with self.subTest(command=command):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_global_options_before_a_compound_subcommand(self) -> None:
        # A global option's VALUE became the first word, so the exact prefix comparison failed.
        for command, rule in (("docker --context production compose up -d web", "docker compose up"),
                              ("podman --connection production compose down", "podman compose down"),
                              ("ip -n lab link set eth0 down", "ip link set")):
            with self.subTest(command=command):
                out = run_gate(bash_call(command))
                self.assertEqual("ask", decision(out))
                self.assertIn(f"matched rule `{rule}`", reason(out))

    def test_every_bypass_shape_denies_under_a_suppressed_mode(self) -> None:
        # This is the finding's real severity: before the fix each of these returned EXIT_ALLOW
        # under dontAsk, so the effect ran with no human able to answer anything.
        for command in ("git status\ndocker compose up -d",
                        "rm --recursive --force /srv/media",
                        "timeout 10 systemctl restart jellyfin",
                        "chroot /mnt systemctl restart jellyfin",
                        "ssh -oProxyCommand='systemctl restart jellyfin' host true",
                        "docker --context production compose up -d web"):
            with self.subTest(command=command):
                self.assertEqual("deny", decision(run_gate(bash_call(command, mode="dontAsk"))))


class GateShapesFromReviewRoundsTwoAndThree(unittest.TestCase):
    """The second and third review rounds, including two regressions round one introduced.

    Risk hypothesis is unchanged from `GateBypassShapesFromReview`: an under-matching parser is
    indistinguishable from a reader at the hook boundary. What is new here is the OTHER direction —
    round one's newline split turned heredoc BODIES into commands, so a Tier 1 runbook write
    acquired a live-effect decision. Both directions are held below, because a gate that cries wolf
    on ordinary writes teaches the operator to click through the prompts that matter.
    """

    def test_parameter_expansion_in_executable_position_is_unbound(self) -> None:
        # `cmd=systemctl` then `$cmd restart jellyfin`: bash expands and restarts, the gate saw a
        # word it could not resolve to an executable and said nothing.
        for command in ("cmd=systemctl\n$cmd restart jellyfin",
                        "$CMD restart jellyfin",
                        "${CMD} restart jellyfin"):
            with self.subTest(command=command):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_execution_prefixes_are_looked_through(self) -> None:
        # `command` and `exec` are bash builtins that execute their argument; treating either as
        # the executable hid the real verb behind it.
        for command in ("command systemctl restart jellyfin",
                        "exec systemctl restart jellyfin",
                        "builtin command docker compose up -d"):
            with self.subTest(command=command):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_long_wrapper_options_consume_their_value(self) -> None:
        # `ionice --class 2 systemctl restart` — the long alias was missing, so `2` was read as
        # the wrapped executable.
        for command in ("ionice --class 2 systemctl restart jellyfin",
                        "ionice --classdata 4 systemctl restart jellyfin",
                        "nice --adjustment 5 systemctl restart jellyfin"):
            with self.subTest(command=command):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_shell_grouping_is_unbound(self) -> None:
        # A subshell or brace group runs the command while presenting the grouping token as the
        # executable.
        for command in ("(systemctl restart jellyfin)",
                        "{ systemctl restart jellyfin ; }",
                        "! systemctl restart jellyfin"):
            with self.subTest(command=command):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_heredoc_body_is_data_not_commands(self) -> None:
        # REGRESSION from round one: the newline split turned every body line into a command, so
        # writing a runbook that MENTIONS a live verb was gated as if it ran one.
        for command in ("cat > /tmp/runbook <<'EOF'\nsystemctl restart jellyfin\nEOF",
                        "cat > /tmp/r <<EOF\ndocker compose up -d\nEOF",
                        "cat > /tmp/r <<-'EOF'\n\tzfs destroy tank/x\n\tEOF"):
            with self.subTest(command=command):
                self.assertEqual("none", decision(run_gate(bash_call(command))))

    def test_a_real_command_after_a_heredoc_still_matches(self) -> None:
        # The heredoc skip must not become a hiding place: what follows the terminator is code.
        out = run_gate(bash_call("cat > /tmp/r <<'EOF'\nnotes\nEOF\nsystemctl restart jellyfin"))
        self.assertEqual("ask", decision(out))
        self.assertIn("matched rule `systemctl restart`", reason(out))

    def test_renamed_identity_key_fails_closed(self) -> None:
        # The guard already carries this canary: if the payload names a gated agent under some
        # OTHER agent-ish key while `agent_type` is absent, the identity contract changed and the
        # gate must not read it as an unrelated caller and step aside.
        payload = json.loads(bash_call("systemctl restart jellyfin", agent_type=None))
        payload["subagent_type"] = HOMELAB
        self.assertEqual("deny", decision(run_gate(json.dumps(payload))))

    def test_quoted_heredoc_opener_does_not_swallow_the_next_command(self) -> None:
        # REGRESSION from the heredoc fix: `<<EOF` appearing as quoted DATA was read as a real
        # opener, so the stripper consumed every following line looking for a terminator that
        # never came — hiding a genuine live command behind `echo '<<EOF'`.
        for command in ("echo '<<EOF'\nsystemctl restart jellyfin",
                        'echo "<<EOF"\ndocker compose up -d',
                        "grep -n '<<-EOF' file.sh\nsystemctl restart jellyfin"):
            with self.subTest(command=command):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_the_canary_ignores_agent_names_in_the_command_itself(self) -> None:
        # The command is user-controlled text; a main-session command that merely mentions the
        # agent must not be denied.
        payload = json.loads(bash_call("git commit -m 'fix sde-agents:homelab-engineer'",
                                       agent_type=None))
        self.assertEqual("none", decision(run_gate(json.dumps(payload))))


if __name__ == "__main__":
    unittest.main()
