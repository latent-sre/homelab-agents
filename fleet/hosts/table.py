"""The rewrite table: every projection from canonical Claude prose to a host's honest statement.

Order is load-bearing — each rewrite's output is the next one's input — so the tables read in the
order the hand-written chains ran: the shared text projections, then the per-agent authority
contracts, then the two bundled reference resources.

Every entry carries the count it must land across one generation run. `fleet/hosts/rewrites.py`
owns why that count exists; `expect` here is the measured, reviewed number, and a mismatch is a
generation failure rather than a silently uncorrected adapter.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Final

from fleet.hosts.rewrites import AT_LEAST_ONE, Rewrite, check_table
from fleet.references import namespaced_reference_re

# Where each host installs the fleet's skills, for the one rewrite that must name a real path.
COPILOT_SKILL_ROOT: Final = ".github/skills"
CODEX_SKILL_ROOT: Final = "plugins/sde-agents/skills"

HOST_LABEL: Final = {"codex": "Codex", "copilot": "Copilot/VS Code", "portable": "the host"}


# --- pattern translations ----------------------------------------------------------------
# A plugin-root path resolves only under Claude. Carried unchanged it points at a file the host
# does not package while reading like an enforced boundary, so each form becomes the thing the
# reader can actually find.


def _installed_skill(match: re.Match[str]) -> str:
    name = match.group("name")
    resource = match.group("resource")
    if not resource or resource == "SKILL.md":
        return f"the installed `{name}` skill"
    return f"the installed `{name}` skill's `{resource}` resource"


def _installed_agent(match: re.Match[str]) -> str:
    return f"the installed `{match.group('name')}` agent definition"


def _trusted_fleet_control(match: re.Match[str]) -> str:
    return f"an operator-provided trusted copy of the fleet's `{match.group('name')}` control"


# The namespace is the plugin's, and only Claude resolves it. There is exactly one matcher for
# a namespaced reference in this repository (`fleet.references`), and the host projection uses
# it rather than a second grammar: a looser one rewrites the namespace inside a URL or path, and
# a stricter one silently skips a malformed reference the validator is meant to reject.
FLEET_NAMESPACE: Final = "sde-agents"
_NAMESPACED_REFERENCE_RE: Final = namespaced_reference_re(FLEET_NAMESPACE)


def _host_reference(invocation_prefix: str) -> Callable[[re.Match[str]], str]:
    """Render one reference the way this host spells it: a slash command keeps its own prefix,
    a bare cross-reference keeps just the component name."""

    def render(match: re.Match[str]) -> str:
        target = match.group("target")
        return f"{invocation_prefix}{target}" if match.group("slash") else target

    return render


TEXT_REWRITES: Final[tuple[Rewrite, ...]] = (
    Rewrite(
        id="text.plugin-root.skill-placeholder",
        why="The documentation placeholder form resolves to nothing off Claude, and a reader "
        "told to open it would look for a literal `<name>` directory.",
        find="`${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`",
        replace="the installed skill named by this step",
        expect=2,
    ),
    Rewrite(
        id="text.plugin-root.skill-path",
        why="A concrete plugin-root skill path is a Claude runtime expansion; every other host "
        "must be pointed at the installed skill by name instead of a path that will not exist.",
        find=r"`?\$\{CLAUDE_PLUGIN_ROOT\}/skills/"
        r"(?P<name>[a-z0-9]+(?:-[a-z0-9]+)*)"
        r"(?:/(?P<resource>[A-Za-z0-9_./<>*-]+))?`?",
        replace=_installed_skill,
        expect=AT_LEAST_ONE,
        regex=True,
    ),
    Rewrite(
        id="text.plugin-root.agent-path",
        why="Same expansion for an agent definition path.",
        find=r"`?\$\{CLAUDE_PLUGIN_ROOT\}/agents/(?P<name>[a-z0-9]+(?:-[a-z0-9]+)*)\.md`?",
        replace=_installed_agent,
        expect=AT_LEAST_ONE,
        regex=True,
    ),
    Rewrite(
        id="text.canonical-skill-path",
        why="A repository-relative `skills/<name>/…` path is this repo's layout, not an install "
        "layout; other hosts resolve a skill by name through their own catalog.",
        find=r"`skills/(?P<name>[a-z0-9]+(?:-[a-z0-9]+)*)/(?P<resource>[A-Za-z0-9_./<>*-]+)`",
        replace=_installed_skill,
        expect=AT_LEAST_ONE,
        regex=True,
    ),
    Rewrite(
        id="text.service-onboard-lookup",
        why="An operational lookup, not Claude-format documentation: a project-scoped skill may "
        "live in a different directory on every target host.",
        find="the target repo's `.claude/skills/service-onboard/SKILL.md` when present, "
        "otherwise\n  the installed `service-onboard` skill",
        replace="the target repo's own project-scoped `service-onboard` skill if this host "
        "discovers one, otherwise the installed `service-onboard` skill",
        expect=2,
    ),
    Rewrite(
        id="text.plugin-install-substitution",
        why="The parenthetical explains Claude's variable substitution, which no other host "
        "performs.",
        find=r"once the plugin is installed \(that variable is substituted for you with an "
        r"absolute path\)",
        replace="from the installed plugin",
        expect=2,
        regex=True,
    ),
    Rewrite(
        id="text.project-context.bridge-parenthetical",
        why="`CLAUDE.md` and its `@AGENTS.md` bridge are a Claude loading convention; other "
        "hosts load their own project-instruction file.",
        find="(`CLAUDE.md`, which Claude Code loads for you; or an `AGENTS.md` it imports via "
        "`@AGENTS.md`)",
        replace="(`AGENTS.md`, `CLAUDE.md`, or the current host's project-instruction equivalent)",
        expect=2,
    ),
    Rewrite(
        id="text.project-context.usually-claude-md",
        why="Naming CLAUDE.md as the usual file is a Claude-only default.",
        find="path (usually the repo's CLAUDE.md)",
        replace="path to the repo's active project-instruction file",
        expect=2,
    ),
    Rewrite(
        id="text.project-context.bridge-sentence",
        why="Same bridge convention in its longer prose form, including the README pointer.",
        find=r"project context \(CLAUDE\.md, or an AGENTS\.md bridged by a CLAUDE\.md containing "
        r"`@AGENTS\.md` — see the\s+plugin README's \"Project context convention\"\)",
        replace="project context (prefer its existing `AGENTS.md`; otherwise use the instruction "
        "file that its host already loads — see the plugin README's \"Project context "
        'convention")',
        expect=2,
        regex=True,
    ),
    Rewrite(
        id="text.preload.skills-and-your-prompt",
        why="A spawned worker's context on another host is whatever that host supplies, not a "
        "Claude preload set.",
        find="its preloaded skills, and your prompt",
        replace="the skills supplied to it, and your prompt",
        expect=2,
    ),
    Rewrite(
        id="text.agent-tool.spawn",
        why="`Agent` is Claude's tool name; other hosts spawn subagents through their own "
        "mechanism, and naming a tool the host lacks reads as an available capability.",
        find="Use the Agent tool to spawn",
        replace="Use the host's subagent mechanism to spawn",
        expect=2,
    ),
    Rewrite(
        id="text.agent-tool.via",
        why="Same tool name in its prepositional form.",
        find="via the Agent tool",
        replace="via the host's subagent mechanism",
        expect=2,
    ),
    Rewrite(
        id="text.agent-tool.unavailable",
        why="Same tool name in the fallback clause.",
        find="If the Agent tool is unavailable",
        replace="If subagent spawning is unavailable",
        expect=4,
    ),
    Rewrite(
        id="text.worker-context-inheritance",
        why="Claude's worker isolation is a runtime guarantee; elsewhere the context a worker "
        "receives depends on the host's fork or context mode, so the guarantee becomes an "
        "instruction to choose that mode explicitly.",
        find=r"- \*\*Workers never see the parent conversation\.\*\* A spawned worker gets its "
        r"definition, the project context, the skills supplied to it, and your prompt — nothing "
        r"else unless you explicitly fork, resume, or supply it\. Construct exactly the context "
        r"each one needs; underspecified handoffs are the #1 multi-agent bug\.",
        replace="- **Never rely on implicit context inheritance.** A spawned worker receives only "
        "what the host's selected context or fork mode supplies. Choose that mode explicitly "
        "when available, and construct exactly the prompt and context the worker needs; "
        "underspecified handoffs are the #1 multi-agent bug.",
        expect=2,
        regex=True,
    ),
    Rewrite(
        id="text.authoring-claude-suites",
        why="The adapter's own subject is the host it is generated for.",
        find="authoring suites of Claude Code agents, skills, and workflows",
        replace="authoring suites of host-native agents, skills, and workflows",
        expect=2,
    ),
    Rewrite(
        id="text.claude-subagent-suites",
        why="Same subject in the scaling sentence.",
        find="from Claude Code subagent suites to production LLM orchestration",
        replace="from host-native subagent suites to production LLM orchestration",
        expect=2,
    ),
    Rewrite(
        id="text.preload.code-craft-common",
        why="Same preload concept for the builder's common craft skill.",
        find="`code-craft` is the common preload.",
        replace="`code-craft` is the common required skill.",
        expect=2,
    ),
    Rewrite(
        id="text.preload.builder-preloads",
        why="Same preload concept in the builder's own description.",
        find="The builder preloads code craft",
        replace="The builder requires code craft",
        expect=2,
    ),
    Rewrite(
        id="text.workflow-tool",
        why="Claude's Workflow tool is not a capability other hosts expose under that name.",
        find="Claude Code's Workflow tool or equivalent",
        replace="the current host's workflow or orchestration mechanism",
        expect=2,
    ),
    Rewrite(
        id="text.namespace.reference",
        why="A namespaced reference resolves only under the Claude plugin namespace, so each "
        "host spells the same invocation its own way: Copilot as a slash command, Codex as "
        "`$name`, and a bare cross-reference as the component name alone.",
        find=_NAMESPACED_REFERENCE_RE.pattern,
        replace={
            "copilot": _host_reference("/"),
            "codex": _host_reference("$"),
            "portable": _host_reference(""),
        },
        expect=AT_LEAST_ONE,
        regex=True,
    ),
)


# --- per-agent authority contracts -------------------------------------------------------
# Each canonical role states its boundary in terms of Claude's controls: a `tools:` allowlist, a
# scoped PreToolUse hook, a preloaded skill. Where the target host has no such control, carrying
# the sentence unchanged states absent authority as if it were enforced — the "authority is the
# host's own control, never prose" rule inverted. These rewrites say what each host can actually
# hold, and name what stays cooperative.

_BUILDER_LOADING = {
    host: (
        "apply. For common and conditional guidance, resolve the named skill's actual\n"
        "SKILL.md path from the host's available-skills catalog, then read that file using\n"
        f"{reader}. The repository-local fallback paths\n"
        "below are relative to the repository root; use them only when present. A skill\n"
        "name is a lookup key, not a path. Do not invent versioned cache locations or\n"
        "ask the operator to use a picker in place of your file lookup."
    )
    for host, reader in (
        ("codex", "an available filesystem tool or a read-only shell command"),
        ("copilot", "the host's read/search tools"),
    )
}

_CODE_REVIEWER_ENFORCEMENT = {
    "copilot": (
        "This profile receives no execute tool, so shell execution is unavailable by capability."
    ),
    "codex": (
        "This profile cannot remove inherited shell authority, and its requested sandbox can be "
        "overridden by parent permissions; the no-execution rule is cooperative."
    ),
}


def _code_reviewer_inspection(enforcement: str) -> str:
    return (
        "**Inspection only. You may not execute code** — no test runners, build tools, "
        "scripts, or repository validators. Cite the builder's packet or CI evidence; when it "
        "is missing or unconvincing, report that as a finding and name "
        "`verification-engineer` as the independently executed escalation. "
        f"{enforcement} Use read/search inspection and name anything the host cannot expose.\n\n"
        "| Rationalization | Reality |\n"
        "|---|---|\n"
        '| "Just run the tests to confirm" | Running repository code is not read-only, '
        "whatever the command looks like. |\n"
        '| "The host boundary will catch me anyway" | Capability and sandbox controls do '
        "not make arbitrary code safe to execute. |\n"
        '| A review "seems to require" running or changing something | Stop and report that '
        "instead. |\n"
    )


_PRINCIPAL_INSPECTION = {
    "copilot": (
        "This profile has no execute tool; use read/search for inspection and name evidence the "
        "host cannot expose."
    ),
    "codex": (
        "Codex still exposes shell execution inside the workspace sandbox, but this role must not "
        "run builds, tests, or scripts; use read/search for inspection and name evidence the host "
        "cannot expose."
    ),
}


def _principal_edit_boundary(inspection: str) -> str:
    return (
        "Your edit authority covers exactly these artifact classes: design docs, ADRs and "
        "decision records, plans, and risk registers in the repository's documentation home "
        "— never source files, configs, tests, or scripts. "
        f"{inspection} The document-only edit boundary remains cooperative, so when a task "
        "pushes you toward writing code, stop and hand it down instead."
    )


AGENT_REWRITES: tuple[Rewrite, ...] = (
    Rewrite(
        id="agent.sde-fullstack.conditional-loading",
        why="The canonical route tells the builder to Read plugin paths. Off Claude those paths "
        "do not resolve, so the route must become a catalog lookup or the builder silently "
        "skips the discipline the table routes to.",
        find="apply. Load other guidance before the work it governs, using the Read tool and "
        "these plugin paths:",
        replace=_BUILDER_LOADING,
        expect=2,
        agents=("sde-fullstack",),
    ),
    *(
        Rewrite(
            id=f"agent.sde-fullstack.route.{skill}",
            why=f"The `{skill}` routing row must name a path this host can actually open; the "
            "name-only form left by the plugin-root translation is not a fallback path.",
            find=f"| the installed `{skill}` skill |",
            replace={
                "codex": f"| `{CODEX_SKILL_ROOT}/{skill}/SKILL.md` |",
                "copilot": f"| `{COPILOT_SKILL_ROOT}/{skill}/SKILL.md` |",
            },
            expect=2,
            agents=("sde-fullstack",),
        )
        for skill in ("backend-craft", "frontend-craft", "root-cause", "ci-actions")
    ),
    Rewrite(
        id="agent.write-edit-authority",
        why="`Write` and `Edit` are Claude tool names; the authority exists on other hosts under "
        "different names, so the grant is described by what it permits.",
        find="You hold Write and Edit **to author tests**",
        replace="You hold edit authority **to author tests**",
        expect=2,
    ),
    Rewrite(
        id="agent.no-agent-tool",
        why="'You hold no Agent tool' is a Claude `tools:` fact. Copilot reproduces it by "
        "omitting the alias; Codex cannot remove inherited subagent authority at all, so there "
        "the no-spawn rule must be stated as cooperative rather than enforced.",
        find=r"you hold no `Agent`\s+tool, so",
        replace={
            "copilot": "this profile receives no `agent` tool, so",
            "codex": "Codex custom-agent TOML cannot remove inherited subagent authority,\nso "
            "the role's no-spawn rule is cooperative; therefore",
        },
        expect=8,
        regex=True,
    ),
    Rewrite(
        id="agent.code-reviewer.pr-history",
        why="The canonical step runs `gh` behind Claude's reader allowlist. Neither host scopes "
        "that guard, so the step becomes host PR context with the evidence gap named.",
        find="Check review comments on recent merged PRs that touched the same files "
        "(`gh pr list` / `gh pr view` — read-only, on the allowlist) for standing objections "
        "that apply again.",
        replace="Use the host's read-only GitHub or PR context, when available, to check recent "
        "merged PRs that touched the same files for standing objections that apply again; name "
        "the evidence gap when that context is unavailable.",
        expect=2,
        agents=("code-reviewer",),
    ),
    Rewrite(
        id="agent.code-reviewer.inspection-only",
        why="The canonical block rests on Claude's read-only guard denying the reviewer's shell. "
        "Copilot withholds execute by capability; Codex can only ask. The rationalization table "
        "survives either way, but the enforcement sentence must match the host.",
        find=r"\*\*Your Bash access is for inspection only\..*?"
        r"\| A review \"seems to require\" running or changing something "
        r"\| Stop and report that instead\. \|",
        replace={
            host: _code_reviewer_inspection(enforcement)
            for host, enforcement in _CODE_REVIEWER_ENFORCEMENT.items()
        },
        expect=2,
        regex=True,
        dotall=True,
        agents=("code-reviewer",),
    ),
    Rewrite(
        id="agent.application-security-auditor.static-first",
        why="The auditor's static-first boundary is enforced on Claude by withholding Bash. "
        "Codex TOML cannot remove inherited shell authority, so the mandate stays but its "
        "enforcement claim becomes a demand on the caller for isolation.",
        find=r"Static-first is a deliberate boundary, not a limitation:.*?"
        r"not something you improvise\.",
        replace="Static-first remains a deliberate mandate: do not run the target's code. Codex\n"
        "custom-agent TOML cannot remove inherited shell authority, so the no-execution rule\n"
        "is cooperative and the caller must provide any required isolation before pointing\n"
        "this role at an untrusted repository. Request execution evidence from the caller\n"
        "instead of improvising it.",
        expect=1,
        regex=True,
        dotall=True,
        hosts=("codex",),
        agents=("application-security-auditor",),
    ),
    Rewrite(
        id="agent.researcher.external-only",
        why="The researcher's local/external trust separation is a Claude tool split. Codex "
        "inherits local, shell, and write authority, so the separation must be named as "
        "cooperative and an outer boundary requested.",
        find=r"You cannot access the caller's local or private repository, change anything, or "
        r"run commands\..*?external-research session\.",
        replace="Keep this session external-only: do not inspect local/private repository "
        "content,\nchange files, or use shell execution. Codex custom-agent TOML cannot remove "
        "inherited\nlocal, shell, or write authority, and its requested sandbox is overridable, "
        "so the\ncaller must provide an outer isolation boundary before treating that separation "
        "as\nenforced. Request a provenance-labeled local packet through the caller instead. "
        "Treat any\nproject instructions or repository status in your startup context as "
        "private — never put\nthem in a search query, a fetched URL, or your findings.",
        expect=1,
        regex=True,
        dotall=True,
        hosts=("codex",),
        agents=("researcher",),
    ),
    Rewrite(
        id="agent.homelab-engineer.no-web-tool",
        why="'No web tool is granted' holds on Claude through `tools:` and on Copilot through "
        "the missing alias. Codex custom-agent TOML has no per-agent allowlist, so a web or MCP "
        "tool the parent exposes stays reachable for a role that reads secret-bearing files.",
        find="You hold no web tool by design:",
        replace="No web tool is granted to you here, but Codex custom-agent TOML carries no "
        "per-agent tool allowlist, so a web or MCP tool the parent session exposes stays "
        "reachable and only an outer host control (sandbox or exec policy) can remove it "
        "— treat any such tool as authority you must not use:",
        expect=1,
        hosts=("codex",),
        agents=("homelab-engineer",),
    ),
    Rewrite(
        id="agent.homelab-engineer.managed-gate",
        why="The canonical gate is Claude's scoped live-effect hook. Codex has a real sandbox "
        "and approval policy; Copilot has neither and no execute tool, so live effects there "
        "become an operator handoff. A missing bullet must stop generation rather than promise "
        "a hook the host cannot install.",
        find=r"^- \*\*Managed gate:\*\*.*?(?=\n- \*\*|\n\n)",
        replace={
            "codex": "- **Managed gate:** use Codex's actual sandbox and approval policy. "
            "Traverse any required\n  prompt and respect denials. An available "
            "`codex execpolicy check` may clarify a rule;\n  it is not a mandatory extra gate. "
            "When effective host permissions allow the authorized\n  action without prompting, "
            "execute normally. Do not invent a prompt requirement or\n  route around an actual "
            "restriction.",
            "copilot": "- **Managed gate:** this generated profile has no execute tool and "
            "cannot install a scoped\n  live-effect hook on Copilot or VS Code. Live effects "
            "therefore require operator handoff: give\n  the prepared command and mark execution "
            "pending. Do not substitute another tool to evade\n  the profile's execution "
            "restriction.",
        },
        expect=2,
        regex=True,
        dotall=True,
        multiline=True,
        agents=("homelab-engineer",),
    ),
    Rewrite(
        id="agent.homelab-engineer.standing-policy",
        why="The standing-policy bullet describes Claude's allow rules. Codex has operator/host "
        "rules of its own; on Copilot no permission rule can add the execute tool this profile "
        "lacks, so the handoff must report a missing capability, not a missing decision.",
        find=r"^- \*\*Standing policy:\*\*.*?(?=\n- \*\*|\n\n)",
        replace={
            "codex": "- **Standing policy:** respect the effective operator/host rules. An allow "
            "rule permits\n  execution within the bounded user request; it does not grant new "
            "task scope. Do not require\n  a root-owned rule or edit policy to authorize your "
            "own work. Full access does not authorize\n  unrelated work or an undisclosed "
            "destructive consequence.",
            "copilot": "- **Standing policy:** host permission rules do not add an execute tool "
            "to this profile.\n  Retain the user's authorization in the handoff; report the "
            "missing execution capability,\n  not a missing user decision.",
        },
        expect=2,
        regex=True,
        dotall=True,
        multiline=True,
        agents=("homelab-engineer",),
    ),
    Rewrite(
        id="agent.repository-investigator.local-only",
        why="The canonical paragraph claims a PreToolUse reader allowlist behind Bash. That hook "
        "is Claude-only: on Copilot the profile holds no shell at all, and on Codex every "
        "boundary is cooperative — including against a repository whose own git config executes "
        "code. Prose naming a control the host cannot load reads as armor and is nothing.",
        find=r"Your context is deliberately local-only:.*?fetched external content\.",
        replace={
            "copilot": "Keep the investigation local-only: do not fetch external content or "
            "change\nfiles. This profile receives no shell/execute tool — Copilot and VS Code "
            "cannot\nscope Claude's per-agent command guard — so gather history evidence "
            "through\nread/search tools and name the commit-history evidence you could not "
            "reach. The\nlocal-only boundary prevents private source from sharing a subordinate "
            "context\nwith fetched external content.",
            "codex": "Keep the investigation local-only and do not fetch external content or "
            "change\nfiles. Codex custom-agent TOML cannot remove inherited web, shell, or "
            "write\nauthority, its requested sandbox is overridable, and the source profile's\n"
            "reader-allowlist command guard does not exist on this host — so every boundary\n"
            "here is cooperative: use the shell only for read-only repository inspection\n"
            "(`git log`, `git blame`, `git show`, `git rev-parse`, search), never for code\n"
            "execution or deliberate network access — against a partial clone any reader that\n"
            "materializes an absent object (`git show`, `git log -p`, `git blame`) still\n"
            "lazily fetches it from the repository's own remote, so never report no-network as\n"
            "a verified fact without naming the commands you ran — and let the caller provide\n"
            "an outer isolation\nboundary before treating that separation as enforced. The "
            "provenance rule is\npart of that cooperation, and it binds harder here than on the "
            "source host:\ngit executes code named by a repository's local config — diff drivers "
            "under\n`git log`/`git show`, a `core.fsmonitor` command under even `git status` — "
            "so a\nrepository that *arrived* as a directory, archive, or mounted volume gets no "
            "git\ncommands at all, step 2's `rev-parse`/`status` included, until your caller "
            "states\nthe isolation boundary; inspect it with read/search tools and say why. No "
            "command\nguard backs this on Codex, so nothing but this instruction stands between "
            "an\narrived repository and its own diff driver.",
        },
        expect=2,
        regex=True,
        dotall=True,
        agents=("repository-investigator",),
    ),
    *(
        Rewrite(
            id=f"agent.repository-investigator.method-step.{index}",
            why="The method steps name git commands Claude's guard allows. This profile holds no "
            "shell at all, so an instruction to run them would contradict the boundary the "
            "paragraph above just drew.",
            find=old,
            replace=new,
            expect=1,
            hosts=("copilot",),
            agents=("repository-investigator",),
        )
        for index, (old, new) in enumerate(
            (
                (
                    "Name the repository root and the revision — `git rev-parse HEAD`, with\n"
                    "   `git status` to detect a dirty tree; on untrusted provenance both wait "
                    "for the isolation\n   boundary above.",
                    "Name the repository root and the revision supplied by the caller or "
                    "exposed\n   by the host context.",
                ),
                (
                    "For revision-bound claims, read the named revision's bytes with\n"
                    "   `git show <revision>:<path>` rather than the working file.",
                    "For revision-bound claims, use the host's read/search view explicitly\n"
                    "   bound to the named revision. If that view is unavailable, name the gap\n"
                    "   and label any current-file citations as working-tree evidence.",
                ),
                (
                    'When the question is "how did it get this way" or "why is this here", '
                    "history is the evidence:\n   `git log`/`git blame` on the region, citing "
                    "the commit that introduced or last changed it.",
                    'When the question is "how did it get this way" or "why is this here", '
                    "history is the evidence:\n   use the host's read-only history context when "
                    "available, and name the commit-history\n   evidence you could not reach.",
                ),
            ),
            start=1,
        )
    ),
    Rewrite(
        id="agent.verification-engineer.tool-boundary",
        why="The verifier's independence rests on Claude's per-role tool list. Codex cannot "
        "reproduce it, and no tool layer distinguishes a test path from product code, so the "
        "test-only boundary must be stated as cooperative.",
        find=r"Your tool list is the platform-enforced boundary;.*?"
        r"voids your independence along with your verdict\.",
        replace="Effective authority comes from the parent session and its requested sandbox; "
        "Codex\ncustom-agent TOML cannot reproduce the canonical per-role tool list. This role's"
        "\nmandate permits edits only to author tests, but that test-only boundary is\n"
        "cooperative because no tool layer distinguishes a test path from product code. Any\n"
        "edit outside test code voids your independence along with your verdict.",
        expect=1,
        regex=True,
        dotall=True,
        hosts=("codex",),
        agents=("verification-engineer",),
    ),
    Rewrite(
        id="agent.multi-agent-architect.tools-are-authority",
        why="'Enforce roles at the tool layer' is advice the architect cannot follow on a host "
        "with no per-agent tool list; on Codex the equivalent control is an outer boundary.",
        find="- **Tools are authority.** An agent's tool list encodes its mandate: reviewers "
        "can't edit, researchers can't write. Enforce roles at the tool layer, not with prose.",
        replace="- **Effective capabilities are authority.** Use each target host's structural "
        "tool,\n  sandbox, permission, or isolation controls to match the mandate. Codex "
        "custom-agent\n  TOML has no per-agent tool list, so a reviewer-no-edit or "
        "researcher-no-write rule\n  needs a stronger outer boundary; prose alone does not "
        "enforce it.",
        expect=1,
        hosts=("codex",),
        agents=("multi-agent-architect",),
    ),
    Rewrite(
        id="agent.principal-engineer.edit-boundary",
        why="The canonical paragraph names Claude's `Write` and `Edit` grants and says the "
        "boundary is cooperative there too; each host needs its own inspection sentence, and "
        "Codex keeps "
        "shell inside the sandbox where Copilot has no execute tool at all.",
        find=r"Your Write and Edit grants cover exactly these artifact classes:.*?"
        r"The Write boundary stays cooperative — no tool boundary distinguishes a design doc "
        r"from a source file — so when a task pushes you toward writing code, stop and hand it "
        r"down instead\.",
        replace={
            host: _principal_edit_boundary(inspection)
            for host, inspection in _PRINCIPAL_INSPECTION.items()
        },
        expect=2,
        regex=True,
        dotall=True,
        agents=("principal-engineer",),
    ),
    Rewrite(
        id="agent.prompt-engineer.tools-are-authority",
        why="Authoring advice that says 'scope the tool list' assumes every target host has one.",
        find="**Tools are authority.** When authoring agents, scope the tool list to the mandate "
        'instead of writing "do not edit files" in prose. Runtime constraints hold; '
        "instructions bend.",
        replace="**Runtime capabilities are authority.** When authoring agents, use the target "
        "host's tool, sandbox, and permission controls to match the mandate instead of relying "
        "on prose. Runtime constraints hold; instructions bend.",
        expect=2,
        agents=("prompt-engineer",),
    ),
    Rewrite(
        id="agent.prompt-engineer.host-configuration",
        why="A '## Claude Code specifics' section in a Codex or Copilot profile documents the "
        "wrong platform's field set; each adapter must send the author to its own host's "
        "contract, and only the Claude-facing one keeps the frontmatter reference by path.",
        find=r"## Claude Code specifics\n\n.*?(?=\n## Voice)",
        replace={
            "codex": "## Host-specific configuration\n\nAuthority lives in host configuration, "
            "not prose, and the field set moves with the platform. Before editing "
            f"{HOST_LABEL['codex']} agent or skill metadata, read that host's current official "
            "contract. When editing a canonical source definition instead, also consult the "
            "installed `prompt-craft` skill's source-host frontmatter reference. Name the "
            "contract used in the change packet.",
            "copilot": "## Host-specific configuration\n\nAuthority lives in host configuration, "
            "not prose, and the field set moves with the platform. Before editing "
            f"{HOST_LABEL['copilot']} agent or skill metadata, read that host's current official "
            "contract. Use the installed `prompt-craft` skill's "
            "`references/claude-code-frontmatter.md` resource only when the target is a "
            "canonical Claude definition. Name the contract used in the change packet.",
        },
        expect=2,
        regex=True,
        dotall=True,
        agents=("prompt-engineer",),
    ),
    Rewrite(
        id="agent.multi-agent-architect.deliverable-target",
        why="The deliverable clause names Claude's own file layout as the target; a Codex "
        "architect ships TOML profiles and installed skills instead.",
        find=r"and, when the target is Claude Code, the actual agent and `SKILL\.md` files "
        r"\(`\.claude/agents/\*\.md` in a project, `agents/\*\.md` in a plugin — "
        r"the reference below settles which\), written to match",
        replace="and, when the target is Codex, the actual `.codex/agents/*.toml` profiles and "
        "installed skills, written to match",
        expect=1,
        regex=True,
        hosts=("codex",),
        agents=("multi-agent-architect",),
    ),
    Rewrite(
        id="agent.multi-agent-architect.frontmatter-source",
        why="'The fleet's single source of truth' is this repository's Claude reference; an "
        "architect working on another host must read that host's contract instead.",
        find=r"Before writing any frontmatter, read the fleet's single source of truth — .*?"
        r"name it in your packet\.",
        replace={
            "codex": f"Before writing any frontmatter, read the current {HOST_LABEL['codex']} "
            "contract. When editing a canonical source definition instead, also consult the "
            "installed `prompt-craft` skill's source-host frontmatter reference, so authority "
            "and ignored fields come from the target host rather than memory; name the sources "
            "in your packet.",
            "copilot": "Before writing any frontmatter, read the current "
            f"{HOST_LABEL['copilot']} contract — or the installed `prompt-craft` skill's "
            "`references/claude-code-frontmatter.md` resource when the target is Claude — so "
            "authority and ignored fields come from the target host rather than memory; name "
            "the sources in your packet.",
        },
        expect=2,
        regex=True,
        dotall=True,
        agents=("multi-agent-architect",),
    ),
    # Codex ships no CLAUDE.md convention at all, so the two-file parenthetical the shared text
    # projection leaves behind is narrowed once more for that host only.
    Rewrite(
        id="agent.codex.project-instruction-parenthetical",
        why="Naming CLAUDE.md to a Codex reader offers a file that host never loads.",
        find="(`AGENTS.md`, `CLAUDE.md`, or the current host's project-instruction equivalent)",
        replace="(`AGENTS.md` or the current host's project-instruction equivalent)",
        expect=1,
        hosts=("codex",),
    ),
)


# --- bundled reference resources ---------------------------------------------------------
# Two prompt-craft references teach how authority is configured. Their canonical text teaches
# Claude's `tools:` allowlist; on a host with different controls the lesson must be the one that
# host can act on, or the reader configures a restriction that does not exist.

_SECURITY_TOOL_SECTION = {
    "copilot": """## Tool grants are the actual security boundary

- Use only documented Copilot/VS Code tool aliases in an explicit `tools:` list. Unknown names are
  ignored, so a plausible-looking alias is not a restriction until the host accepts it.
- For a read-only role, omit `edit`, `execute`, and `web`; prose does not narrow a granted tool.
- Shell/execute is the universal escape hatch. Copilot and VS Code `PreToolUse` input does not
  identify the active custom agent, and VS Code ignores hook matchers, so do not claim an
  agent-scoped shell guard. Remove `execute` or isolate the role instead.
- Keep private data, untrusted input, and outbound or write authority out of one context.

""",
    "codex": """## Parent permissions determine effective authority

- Standalone Codex custom agents request `sandbox_mode` and inherit session configuration; they do
  not carry a per-agent Claude or Copilot `tools:` allowlist.
- Parent live permission changes and full-access mode can override the profile's requested sandbox
  and are reapplied to child agents. Use `sandbox_mode = "read-only"` as a safer default for
  investigative roles, never as proof of an immutable no-write boundary.
- Shell execution can still run untrusted code even when filesystem writes are denied. If a role
  must not execute code, state that cooperative limit and remove untrusted inputs or shell
  authority at a stronger outer boundary when available.
- Codex plugins package skills but not custom-agent TOML, so review the standalone agent and plugin
  skill surfaces as separate install artifacts.

""",
}

_TOOLS_MANDATE_SECTION = {
    "copilot": """## The tool list is the mandate

An agent's capabilities are its tools, not its prose. Use the least documented native aliases that
make the job possible and enumerate them explicitly. Unknown names are ignored. A read-only
investigator normally needs `read` and `search`, with no `edit`, `execute`, or `web`; pair each
additional grant with its reason in the agent body.

""",
    "codex": """## Parent permissions and inherited configuration are the mandate

Codex custom-agent TOML does not use Claude or Copilot `tools:` frontmatter. Start investigative
roles with a requested `sandbox_mode = "read-only"`, review inherited shell, MCP, skill, and
subagent authority, and remember that parent permission changes can override the profile default.
Prose can narrow a mandate cooperatively, but it cannot remove a capability that the runtime still
exposes.

""",
}

SECURITY_REFERENCE_REWRITES: Final[tuple[Rewrite, ...]] = (
    Rewrite(
        id="resource.agent-security.tool-grants",
        why="The section teaches that a Claude `tools:` list is the boundary. Copilot's aliases "
        "behave differently and Codex has no per-agent list at all, so each host gets the lesson "
        "it can act on.",
        find=r"## Tool grants are the actual security boundary\n.*?"
        r"(?=## Content boundaries in the prompt itself)",
        replace=_SECURITY_TOOL_SECTION,
        expect=2,
        regex=True,
        dotall=True,
    ),
    Rewrite(
        id="resource.agent-security.review-questions",
        why="Two review questions ask about a `tools:` list and a `Bash` grant by name; on "
        "another host the reviewer must ask what structural control enforces the claim.",
        find="2. Does its `tools:` list say exactly what it can do — with nothing inherited and "
        "no fake scoping?\n"
        "3. If it holds `Bash` or a write tool, what enforces the limit its prose claims?",
        replace="2. Does the host configuration grant exactly the authority the role needs, with "
        "no plausible-looking but inert\n   restriction?\n"
        "3. What structural capability, sandbox, or isolation boundary enforces every limit "
        "the\n   prose claims?",
        expect=2,
    ),
)

TOOLS_REFERENCE_REWRITES: Final[tuple[Rewrite, ...]] = (
    Rewrite(
        id="resource.tools.mandate",
        why="The section teaches enumerating a Claude tool list; Codex has none, so its mandate "
        "comes from the requested sandbox and inherited configuration instead.",
        find=r"## The tool list is the mandate\n.*?"
        r"(?=## When to promote a Bash invocation into a real tool)",
        replace=_TOOLS_MANDATE_SECTION,
        expect=2,
        regex=True,
        dotall=True,
    ),
    Rewrite(
        id="resource.tools.promote-heading",
        why="`Bash` is Claude's tool name; the heading must name the capability, not the tool.",
        find="## When to promote a Bash invocation into a real tool",
        replace="## When to promote a shell invocation into a real tool",
        expect=2,
    ),
)

# --- read-only skill bodies --------------------------------------------------------------
# A skill whose canonical frontmatter carries `disallowed-tools` tells the reader that the field
# removed Write and Edit. The portable frontmatter drops that field, and Claude's reviewer guard
# keys on guarded AGENT identities so it never covered a skill anyway -- so on any other host the
# sentence states a control that is not there. These are projections like any other, and they are
# counted like any other.

SKILL_READONLY_REWRITES: Final[tuple[Rewrite, ...]] = (
    Rewrite(
        id="skill.readonly.disallowed-tools-claim",
        why="`disallowed-tools` is dropped from the portable frontmatter, so a body still "
        "crediting it with removing Write and Edit names a deny that this copy does not carry.",
        find=r"All checks are read-only\. `disallowed-tools` removes Write and Edit while this "
        r"skill is active,\s+but Bash can still mutate",
        replace="All checks are read-only. This portable adapter has no cross-host write-tool "
        "deny, and shell access can still mutate",
        # Two skills carry the sentence, each generated for both hosts.
        expect=4,
        regex=True,
    ),
    Rewrite(
        id="skill.readonly.guard-coverage",
        why="The paragraph explains which Claude hook does and does not cover the skill; off "
        "Claude there is no such hook at all, so only the parent host's sandbox is a boundary.",
        find=r"Whether you were invoked directly from the main session or under "
        r"`homelab-engineer`, the reviewer's Bash guard does not cover this skill \(that hook "
        r"keys on guarded \*agent\* identities, and the main loop carries none at all\) — the "
        r"read-only-ness here is cooperative, not enforced\. `NotebookEdit` is in "
        r"`disallowed-tools` for the same reason as Write and Edit: it is a write tool, and a "
        r"denylist that names only the obvious two leaves the third\.",
        replace="The parent host's sandbox or permission profile is the only hard boundary here; "
        "the skill's read-only posture is cooperative, and no write-capable tool is within its "
        "mandate.",
        expect=2,
        regex=True,
    ),
    Rewrite(
        id="skill.readonly.cooperative-aside",
        why="The shorter form of the same guard aside.",
        find=r"The\s+read-only-ness here is cooperative, not enforced \(the reviewer's Bash "
        r"guard keys on guarded\s+\*agent\* identities, not skills\)\.",
        replace="The parent host's sandbox or permission profile is the only hard boundary here; "
        "the skill's read-only posture is cooperative.",
        expect=2,
        regex=True,
    ),
)

ALL_REWRITES: Final[tuple[Rewrite, ...]] = (
    *TEXT_REWRITES,
    *AGENT_REWRITES,
    *SKILL_READONLY_REWRITES,
    *SECURITY_REFERENCE_REWRITES,
    *TOOLS_REFERENCE_REWRITES,
)

# Two entries sharing an id share one count in the ledger, so one could land the whole total
# while the other lost its anchor and landed nothing -- the miss masked by its twin. Refuse at
# import, so a committed table can never load in a state nothing can judge.
check_table(ALL_REWRITES)
