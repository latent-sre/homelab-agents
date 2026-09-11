from __future__ import annotations

import json
import os
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from scripts import generate_platform_adapters
from scripts import validate_fleet
from tests.support import REPO, create_directory_link, git, remove_directory_link
COPILOT_TOOL_ALIASES = {"agent", "edit", "execute", "read", "search", "web"}
WRITE_TOOLS = {"Edit", "NotebookEdit", "Write"}


_create_directory_link = create_directory_link
_remove_directory_link = remove_directory_link


class PlatformAdapterTests(unittest.TestCase):
    def test_vscode_skill_relocation_reports_and_removes_the_retired_root(self) -> None:
        # VS Code discovers `.github/skills` without repository-specific settings. The former
        # Copilot CLI output root had no consumer, and regeneration must remove that stale tree
        # instead of leaving two plausible skill fleets behind.
        old_relative = Path("platforms/copilot/skills")
        new_relative = Path(".github/skills")
        self.assertEqual(new_relative, generate_platform_adapters.COPILOT_SKILLS)
        self.assertIn(old_relative, generate_platform_adapters.RETIRED_GENERATED_ROOTS)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            manifest = root / ".claude-plugin" / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("{}\n", encoding="utf-8")
            old_skill = root / old_relative / "probe" / "SKILL.md"
            old_skill.parent.mkdir(parents=True)
            old_skill.write_text("stale generated skill\n", encoding="utf-8")
            expected = {new_relative / "probe" / "SKILL.md": b"generated skill\n"}

            with mock.patch.object(
                generate_platform_adapters,
                "expected_outputs",
                return_value=expected,
            ):
                issues = generate_platform_adapters.validate_generated_outputs(root)
                self.assertTrue(
                    any(
                        str(root / old_relative) in issue
                        and "retired generated adapter root still exists" in issue
                        for issue in issues
                    ),
                    issues,
                )
                generate_platform_adapters.write_generated_outputs(root)

            self.assertFalse((root / old_relative).exists())
            self.assertEqual(
                b"generated skill\n",
                (root / new_relative / "probe" / "SKILL.md").read_bytes(),
            )

    def test_definition_parts_uses_one_coherent_source_snapshot(self) -> None:
        first = "---\nname: first\ndescription: First\n---\n\nfirst body\n"
        second = "---\nname: second\ndescription: Second\n---\n\nsecond body"
        path = Path("definition.md")

        with mock.patch.object(
            type(path),
            "read_text",
            side_effect=(first, second, second),
        ) as reader:
            fields, body, raw = generate_platform_adapters._definition_parts(path)

        self.assertEqual(1, reader.call_count)
        self.assertEqual("first", fields["name"])
        self.assertEqual(["name: first", "description: First"], raw)
        self.assertEqual("first body\n", body)

    def test_definition_parts_rejects_missing_required_frontmatter(self) -> None:
        variants = (
            ("---\n---\n\nBody.\n", "description, name"),
            ("---\nname: incomplete\n---\n\nBody.\n", "description"),
        )
        path = Path("definition.md")
        for source, missing in variants:
            with self.subTest(missing=missing), mock.patch.object(
                type(path), "read_text", return_value=source
            ), self.assertRaisesRegex(ValueError, f"required frontmatter.*{missing}"):
                generate_platform_adapters._definition_parts(path)

    def test_text_resources_are_lf_normalized_but_binary_resources_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            (root / "agents").mkdir(parents=True)
            resources = root / "skills" / "example" / "assets"
            resources.mkdir(parents=True)
            text_resource = resources / "config.yaml"
            binary_resource = resources / "fixture.bin"
            text_resource.write_bytes(b"first: line\r\nsecond: value\r\n")
            binary_bytes = b"\x89BIN\r\n\x00payload\r\n"
            binary_resource.write_bytes(binary_bytes)

            with mock.patch.object(
                generate_platform_adapters,
                "_guarded_names",
                return_value=set(),
            ):
                outputs = generate_platform_adapters.expected_outputs(root)

            relative = Path("example") / "assets"
            for target_root in (
                generate_platform_adapters.COPILOT_SKILLS,
                generate_platform_adapters.CODEX_SKILLS,
            ):
                self.assertEqual(
                    b"first: line\nsecond: value\n",
                    outputs[target_root / relative / text_resource.name],
                )
                self.assertEqual(
                    binary_bytes,
                    outputs[target_root / relative / binary_resource.name],
                )

    def test_declared_text_resource_with_invalid_utf8_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            (root / "agents").mkdir(parents=True)
            resources = root / "skills" / "example" / "assets"
            resources.mkdir(parents=True)
            (resources / "config.yaml").write_bytes(b"value: \xff\xfe\n")

            with mock.patch.object(
                generate_platform_adapters,
                "_guarded_names",
                return_value=set(),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "declared text resource is not valid UTF-8",
                ):
                    generate_platform_adapters.expected_outputs(root)

    def test_python_bytecode_caches_are_not_distribution_artifacts(self) -> None:
        relative = (
            Path("observability")
            / "scripts"
            / "__pycache__"
            / "adapter-test.pyc"
        )
        paths = (
            REPO / "skills" / relative,
            REPO / ".github" / "skills" / relative,
            REPO / "plugins" / "sde-agents" / "skills" / relative,
        )
        try:
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"transient bytecode")

            expected = generate_platform_adapters.expected_outputs(REPO)
            self.assertFalse(
                any("__pycache__" in path.parts for path in expected),
                expected,
            )
            self.assertEqual(
                [],
                generate_platform_adapters.validate_generated_outputs(REPO),
            )
        finally:
            for path in paths:
                path.unlink(missing_ok=True)
                try:
                    path.parent.rmdir()
                except OSError:
                    pass

    def test_tracked_runtime_byproduct_cannot_evade_generated_drift_check(self) -> None:
        payload = (
            REPO
            / generate_platform_adapters.CODEX_SKILLS
            / "observability"
            / "scripts"
            / "__pycache__"
            / "tracked-adapter-payload.py"
        )
        relative = payload.relative_to(REPO)
        try:
            payload.parent.mkdir(parents=True, exist_ok=True)
            payload.write_text("arbitrary tracked payload\n", encoding="utf-8")
            with mock.patch.object(
                generate_platform_adapters,
                "_repository_tracked_files",
                return_value={relative},
            ):
                issues = generate_platform_adapters.validate_generated_outputs(REPO)
            self.assertTrue(
                any(
                    str(relative) in issue
                    and "stale generated platform adapter" in issue
                    for issue in issues
                ),
                issues,
            )
        finally:
            payload.unlink(missing_ok=True)
            try:
                payload.parent.rmdir()
            except OSError:
                pass

    @unittest.skipUnless(shutil.which("git"), "git is required to build the parent work tree")
    def test_nested_non_repo_copy_does_not_inherit_parent_tracking_state(self) -> None:
        # The parent must be a git work tree, but not THIS one: writing transient entries into
        # the live repository races the pooled repo copy once tests run under a parallel runner,
        # and a synthetic parent proves the same non-inheritance.
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / "parent-repo"
            parent.mkdir()
            git(parent, "init", "-q")
            nested_copy = parent / "archive"
            nested_copy.mkdir()
            self.assertIsNone(
                generate_platform_adapters._repository_tracked_files(nested_copy)
            )

    def test_non_git_copy_validates_cache_shaped_files_strictly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "archive"
            payload = (
                root
                / generate_platform_adapters.CODEX_SKILLS
                / "__pycache__"
                / "packaged-payload.py"
            )
            (root / ".claude-plugin").mkdir(parents=True)
            (root / ".claude-plugin" / "plugin.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            payload.parent.mkdir(parents=True)
            payload.write_text("packaged payload\n", encoding="utf-8")

            with mock.patch.object(
                generate_platform_adapters,
                "expected_outputs",
                return_value={},
            ):
                issues = generate_platform_adapters.validate_generated_outputs(root)
            self.assertTrue(
                any(
                    str(payload.relative_to(root)) in issue
                    and "stale generated platform adapter" in issue
                    for issue in issues
                ),
                issues,
            )

    def test_validation_rejects_links_at_every_generated_tree_depth(self) -> None:
        placements = (
            ("root", generate_platform_adapters.COPILOT_SKILLS, Path(".")),
            ("parent", Path(".github"), Path("skills")),
            (
                "descendant",
                generate_platform_adapters.COPILOT_SKILLS / "redirected",
                Path("."),
            ),
        )
        for name, link_relative, sentinel_parent in placements:
            with self.subTest(placement=name), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                root = base / "repo"
                external = base / "external"
                link = root / link_relative
                (root / ".claude-plugin").mkdir(parents=True)
                (root / ".claude-plugin" / "plugin.json").write_text(
                    "{}\n", encoding="utf-8"
                )
                target = external / sentinel_parent
                target.mkdir(parents=True)
                sentinel = target / "outside-secret-name.txt"
                sentinel.write_text("must remain outside\n", encoding="utf-8")
                link.parent.mkdir(parents=True, exist_ok=True)
                _create_directory_link(external, link)
                try:
                    with mock.patch.object(
                        generate_platform_adapters, "expected_outputs", return_value={}
                    ):
                        issues = generate_platform_adapters.validate_generated_outputs(root)
                    self.assertTrue(
                        any(
                            "cannot inspect generated platform adapters" in issue
                            and "link, junction, or reparse point" in issue
                            and "Validation could read or certify a different tree." in issue
                            for issue in issues
                        ),
                        issues,
                    )
                    self.assertFalse(any(sentinel.name in issue for issue in issues), issues)
                finally:
                    _remove_directory_link(link)

    def test_validation_rejects_dangling_links_at_every_retired_root_depth(self) -> None:
        """PR #149: target existence cannot stand in for lexical link existence."""
        for name, link_relative in (
            ("leaf", Path(".claude") / "agents"),
            ("parent", Path(".claude")),
        ):
            with self.subTest(placement=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "repo"
                (root / ".claude-plugin").mkdir(parents=True)
                (root / ".claude-plugin" / "plugin.json").write_text(
                    "{}\n", encoding="utf-8"
                )
                retired = root / ".claude" / "agents"
                linked = root / link_relative

                def is_link(path: Path) -> bool:
                    return path == linked

                with (
                    mock.patch.object(
                        generate_platform_adapters, "expected_outputs", return_value={}
                    ),
                    mock.patch.object(
                        generate_platform_adapters,
                        "_repository_tracked_files",
                        return_value=set(),
                    ),
                    mock.patch.object(
                        generate_platform_adapters,
                        "_is_link_or_reparse_point",
                        side_effect=is_link,
                    ),
                ):
                    issues = generate_platform_adapters.validate_generated_outputs(root)

                matching = [issue for issue in issues if str(retired) in issue]
                self.assertEqual(1, len(matching), issues)
                self.assertIn("link, junction, or reparse point", matching[0])
                self.assertIn(str(linked), matching[0])
                self.assertIn("remove the offending link", matching[0])
                self.assertNotIn("generate_platform_adapters.py --write", matching[0])

    def test_write_rejects_links_at_every_generated_tree_ancestor(self) -> None:
        placements = (
            ("root", generate_platform_adapters.COPILOT_SKILLS, Path(".")),
            ("parent", Path(".github"), Path("skills")),
        )
        for name, link_relative, sentinel_parent in placements:
            with self.subTest(placement=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "repo"
                sensitive = root / "canonical-source"
                target = sensitive / sentinel_parent
                target.mkdir(parents=True)
                sentinel = target / "sentinel.txt"
                sentinel.write_text("must survive\n", encoding="utf-8")
                link = root / link_relative
                link.parent.mkdir(parents=True, exist_ok=True)
                _create_directory_link(sensitive, link)
                try:
                    with mock.patch.object(
                        generate_platform_adapters, "expected_outputs", return_value={}
                    ):
                        with self.assertRaisesRegex(ValueError, "link|junction|reparse"):
                            generate_platform_adapters.write_generated_outputs(root)
                    self.assertEqual(
                        "must survive\n", sentinel.read_text(encoding="utf-8")
                    )
                finally:
                    _remove_directory_link(link)

    def test_canonical_source_links_are_rejected_before_resource_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            external = base / "external"
            (root / "agents").mkdir(parents=True)
            (root / "skills").mkdir()
            external.mkdir()
            secret = external / "secret.bin"
            secret.write_bytes(b"external secret")
            link = root / "skills" / "linked-resource"
            _create_directory_link(external, link)
            try:
                with mock.patch.object(
                    generate_platform_adapters,
                    "_guarded_names",
                    return_value=set(),
                ):
                    with self.assertRaisesRegex(
                        ValueError,
                        "canonical source.*(?:link|junction|reparse)",
                    ):
                        generate_platform_adapters.expected_outputs(root)
                self.assertEqual(b"external secret", secret.read_bytes())
            finally:
                _remove_directory_link(link)

    def test_copilot_adapters_use_only_native_aliases(self) -> None:
        for path in sorted((REPO / ".github" / "agents").glob("*.agent.md")):
            with self.subTest(agent=path.stem):
                fields = validate_fleet.parse_frontmatter(path)
                self.assertIsNotNone(fields)
                tools = set(validate_fleet.split_tools(fields["tools"]))
                self.assertTrue(tools)
                self.assertLessEqual(tools, COPILOT_TOOL_ALIASES)

    def test_investigator_host_rewrite_fails_loudly_when_its_anchor_is_missing(self) -> None:
        # A zero-match rewrite would regenerate "clean" adapters that keep the Claude-only
        # guard claim on hosts that cannot load the guard, and byte-drift validation cannot
        # see it — the committed adapter carries the same silent miss. So a missed anchor must
        # be a generation error, not a no-op.
        for host in ("copilot", "codex"):
            with self.subTest(host=host):
                with self.assertRaisesRegex(ValueError, "repository-investigator"):
                    generate_platform_adapters.adapt_agent_contract(
                        "body text without the boundary paragraph",
                        name="repository-investigator",
                        host=host,
                    )
        # A missing method anchor must also fail after the boundary rewrite succeeds;
        # otherwise the no-shell host could retain an instruction to execute Git.
        _, body, _ = generate_platform_adapters._definition_parts(
            REPO / "agents/repository-investigator.md"
        )
        for anchor in (
            "Name the repository root and the revision",
            "For revision-bound claims, read the named revision's bytes",
            'When the question is "how did it get this way"',
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, body)
                with self.assertRaisesRegex(ValueError, "method-step anchor"):
                    generate_platform_adapters.adapt_agent_contract(
                        body.replace(anchor, "missing method anchor", 1),
                        name="repository-investigator",
                        host="copilot",
                    )

    def test_homelab_host_rewrite_fails_loudly_when_its_anchor_is_missing(self) -> None:
        # Same rule for the live-effect gate (GATE-006): the canonical transport bullet names a
        # Claude-only hook, and a silent zero-match rewrite would ship that claim to a host that
        # cannot load it. The real canonical body must rewrite cleanly on both hosts.
        for host in ("copilot", "codex"):
            with self.subTest(host=host):
                with self.assertRaisesRegex(ValueError, "homelab-engineer"):
                    generate_platform_adapters.adapt_agent_contract(
                        "body text without the transport bullet",
                        name="homelab-engineer",
                        host=host,
                    )
        canonical = (REPO / "agents" / "homelab-engineer.md").read_text(encoding="utf-8")
        for host, marker in (("copilot", "operator handoff"), ("codex", "codex execpolicy check")):
            with self.subTest(host=host):
                rewritten = generate_platform_adapters.adapt_agent_contract(
                    canonical, name="homelab-engineer", host=host
                )
                self.assertNotIn("hooks/hooks.json", rewritten)
                self.assertNotIn("live-effect gate — matched rule `docker compose up`", rewritten)
                self.assertIn(marker, rewritten)

    def test_homelab_codex_allows_authorized_native_execution_without_fake_gate(self) -> None:
        """Host adaptation must not restore the retired prompt-only execution policy."""
        canonical = (REPO / "agents" / "homelab-engineer.md").read_text(encoding="utf-8")
        rewritten = generate_platform_adapters.adapt_agent_contract(
            canonical, name="homelab-engineer", host="codex"
        )
        self.assertIn("allow the authorized", rewritten)
        self.assertIn("action without prompting, execute normally", rewritten)
        self.assertIn("Traverse any required", rewritten)
        self.assertIn("respect denials", rewritten)
        self.assertNotIn("sandbox and command-approval prompt must interpose", rewritten)
        self.assertNotIn("only an exec-policy rule under a root-owned path", rewritten)
        self.assertNotIn("live-effect hook asks", rewritten)

    def test_homelab_copilot_handoff_tracks_missing_capability_not_missing_consent(self) -> None:
        """The native-execution path cannot accidentally grant the no-shell host a tool."""
        canonical = (REPO / "agents" / "homelab-engineer.md").read_text(encoding="utf-8")
        rewritten = generate_platform_adapters.adapt_agent_contract(
            canonical, name="homelab-engineer", host="copilot"
        )
        self.assertIn("has no execute tool", rewritten)
        self.assertIn("mark execution pending", rewritten)
        self.assertIn("not a missing user decision", rewritten)
        self.assertIn("Do not substitute another tool", " ".join(rewritten.split()))

    def test_homelab_duplicate_transport_policy_is_rejected(self) -> None:
        """Two competing transport bullets must not yield a plausible generated control."""
        canonical = (REPO / "agents" / "homelab-engineer.md").read_text(encoding="utf-8")
        for label in ("Managed gate", "Standing policy"):
            start = canonical.index(f"- **{label}:**")
            end = canonical.index("\n- **", start + 1)
            duplicate = canonical + "\n\n" + canonical[start:end] + "\n\n"
            for host in ("copilot", "codex"):
                with self.subTest(label=label, host=host):
                    with self.assertRaisesRegex(ValueError, "expected one.*transport anchor"):
                        generate_platform_adapters.adapt_agent_contract(
                            duplicate, name="homelab-engineer", host=host
                        )

    def test_guarded_copilot_agents_have_no_shell_tool(self) -> None:
        guard = validate_fleet.load_guard(REPO)
        for name in sorted(guard.GUARDED_AGENT_NAMES):
            with self.subTest(agent=name):
                fields = validate_fleet.parse_frontmatter(
                    REPO / ".github" / "agents" / f"{name}.agent.md"
                )
                tools = set(validate_fleet.split_tools(fields["tools"]))
                self.assertNotIn("execute", tools)

    def test_copilot_builder_retains_execution_and_edit_authority(self) -> None:
        fields = validate_fleet.parse_frontmatter(
            REPO / ".github" / "agents" / "sde-fullstack.agent.md"
        )
        tools = set(validate_fleet.split_tools(fields["tools"]))
        self.assertIn("execute", tools)
        self.assertIn("edit", tools)

    def test_preloaded_claude_skills_become_explicit_host_requirements(self) -> None:
        canonical = validate_fleet.parse_frontmatter(
            REPO / "agents" / "sde-fullstack.md"
        )
        skill_names = validate_fleet.split_tools(canonical["skills"])
        self.assertEqual(["code-craft"], skill_names)
        paths = (
            REPO / ".github" / "agents" / "sde-fullstack.agent.md",
            REPO / ".codex" / "agents" / "sde-fullstack.toml",
        )
        for path in paths:
            with self.subTest(path=path.relative_to(REPO)):
                text = path.read_text(encoding="utf-8")
                normalized = " ".join(text.split())
                for skill_name in skill_names:
                    self.assertIn(skill_name, text)
                self.assertIn("every listed installed skill", normalized)
                self.assertNotIn("preloaded craft skills", text)
                self.assertNotIn("which is **not** preloaded", text)
                self.assertNotIn("already in your context", text)
                self.assertNotIn("already in your\ncontext", text)

    def test_codex_sandbox_mode_tracks_canonical_write_authority(self) -> None:
        for source in sorted((REPO / "agents").glob("*.md")):
            with self.subTest(agent=source.stem):
                fields = validate_fleet.parse_frontmatter(source)
                tools = set(validate_fleet.split_tools(fields["tools"]))
                expected = "workspace-write" if tools & WRITE_TOOLS else "read-only"
                generated = tomllib.loads(
                    (REPO / ".codex" / "agents" / f"{source.stem}.toml").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(source.stem, generated["name"])
                self.assertEqual(expected, generated["sandbox_mode"])

    def test_builder_conditional_skills_have_resolvable_host_paths(self) -> None:
        source = REPO / "agents" / "sde-fullstack.md"
        for host, root, render in (
            ("copilot", ".github/skills", lambda: generate_platform_adapters.render_copilot_agent(
                source, guarded_names=set())),
            ("codex", "plugins/sde-agents/skills", lambda: generate_platform_adapters.render_codex_agent(source)),
        ):
            with self.subTest(host=host):
                text = render()
                self.assertNotIn("using the Read tool and these plugin paths", text)
                self.assertIn("available-skills catalog", text)
                self.assertIn("use them only when present", text)
                for name in ("backend-craft", "frontend-craft", "root-cause", "ci-actions"):
                    path = f"{root}/{name}/SKILL.md"
                    self.assertIn(f"`{path}`", text)
                    self.assertTrue((REPO / path).is_file())

    def test_builder_loading_rewrite_rejects_missing_or_duplicate_routes(self) -> None:
        _, body, _ = generate_platform_adapters._definition_parts(REPO / "agents/sde-fullstack.md")
        for host in ("codex", "copilot"):
            adapted = generate_platform_adapters.adapt_text(body, host)
            for anchor in (
                "apply. Load other guidance before the work it governs, using the Read tool and these plugin paths:",
                *(f"| the installed `{name}` skill |" for name in
                  ("backend-craft", "frontend-craft", "root-cause", "ci-actions")),
            ):
                for broken in (adapted.replace(anchor, "missing route"), adapted + "\n" + anchor):
                    with self.subTest(host=host, anchor=anchor), self.assertRaisesRegex(
                        ValueError, "expected one.*skill-loading"
                    ):
                        generate_platform_adapters.adapt_agent_contract(broken, name="sde-fullstack", host=host)

    def test_investigator_provenance_boundary_survives_every_host_rewrite(self) -> None:
        # The canonical untrusted-provenance paragraph is REPLACED wholesale on both non-Claude
        # hosts, so a boundary added canonically silently fails to reach them — which is exactly
        # what happened when the all-git rule landed: the Codex adapter kept step 2's "wait for
        # the isolation boundary above" pointing at a paragraph that no longer carried one, while
        # step 4 still instructed `git log`. Each host must state the rule in its own terms, or
        # (Copilot) hold no shell and instruct no git at all.
        codex = tomllib.loads(
            (REPO / ".codex" / "agents" / "repository-investigator.toml").read_text(
                encoding="utf-8"
            )
        )
        codex_body = " ".join(codex["developer_instructions"].split())
        self.assertIn("arrived", codex_body)
        self.assertIn("no git commands at all", codex_body)
        self.assertIn("core.fsmonitor", codex_body)
        self.assertIn("git show <revision>:<path>", codex_body)
        self.assertIn("label citations as working-tree evidence", codex_body)

        copilot_body = " ".join(
            (REPO / ".github" / "agents" / "repository-investigator.agent.md")
            .read_text(encoding="utf-8")
            .split()
        )
        # The no-shell profile closes the same hole by instructing no git at all; a step that
        # named one would be an instruction this host cannot honor and a boundary it cannot keep.
        self.assertNotIn("git rev-parse", copilot_body)
        self.assertNotIn("git log", copilot_body)
        self.assertNotIn("git show", copilot_body)
        self.assertIn("read/search view explicitly bound to the named revision", copilot_body)
        self.assertIn("label any current-file citations as working-tree evidence", copilot_body)

    def test_codex_adapters_do_not_claim_overridable_defaults_are_controls(self) -> None:
        for path in sorted((REPO / ".codex" / "agents").glob("*.toml")):
            with self.subTest(agent=path.stem):
                generated = tomllib.loads(path.read_text(encoding="utf-8"))
                instructions = generated["developer_instructions"]
                normalized = " ".join(instructions.split())
                self.assertIn(
                    "Parent session permissions can override this requested sandbox",
                    normalized,
                )
                self.assertIn(
                    "Codex custom-agent TOML does not provide a per-agent tool allowlist",
                    normalized,
                )
                for false_control in (
                    "Filesystem mutation is enforced by",
                    "The read-only sandbox enforces filesystem immutability",
                    "this role has no subagent-spawn authority",
                    "you hold no shell",
                    "no write tools, no shell",
                    "safe to spawn speculatively",
                    "Your tool list is the platform-enforced boundary",
                    "reviewers can't edit, researchers can't write",
                    "you hold no `Agent` tool",
                    "This role has no `Agent` tool",
                ):
                    self.assertNotIn(false_control.casefold(), normalized.casefold())

    def test_host_agent_adapters_have_no_claude_runtime_references(self) -> None:
        paths = [
            *(REPO / ".github" / "agents").glob("*.agent.md"),
            *(REPO / ".codex" / "agents").glob("*.toml"),
        ]
        for path in sorted(paths):
            with self.subTest(path=path.relative_to(REPO)):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("sde-agents:", text)
                self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", text)
                self.assertNotIn("the variable is substituted", text)
                self.assertNotIn("platform-facts owner", text)
                for false_control in (
                    "A `PreToolUse` hook backs this",
                    "is **enforced** by a `PreToolUse` hook",
                    "that half is **enforced**: a `PreToolUse` hook",
                    "`permissionMode` is inert",
                    "add a destructive-command matcher",
                    "Your Bash access",
                    "you hold no `Agent` tool",
                    "Read/Grep/Glob",
                    "read-only, on the allowlist",
                    "hooks/hooks.json",
                    "## Claude Code specifics",
                    "Claude Code sandbox counts only",
                    "authoring suites of Claude Code agents",
                    "Before writing any frontmatter, read the fleet's single source",
                ):
                    self.assertNotIn(false_control.casefold(), text.casefold())

    def test_host_skills_have_no_live_claude_namespace_references(self) -> None:
        roots = (
            REPO / generate_platform_adapters.COPILOT_SKILLS,
            REPO / "plugins" / "sde-agents" / "skills",
        )
        for root in roots:
            claude_reference = (
                root
                / "prompt-craft"
                / "references"
                / "claude-code-frontmatter.md"
            )
            for path in sorted(root.rglob("*.md")):
                if path == claude_reference:
                    continue
                with self.subTest(path=path.relative_to(REPO)):
                    text = path.read_text(encoding="utf-8")
                    self.assertNotIn("sde-agents:", text)
                    self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", text)
                    self.assertNotRegex(text, r"`skills/[a-z0-9-]+/")
                    for false_control in (
                        "Plugin-shipped agents silently ignore",
                        "`Bash(git diff:*)`",
                        "`memory:` auto-enables",
                        "via the Agent tool",
                        "If the Agent tool is unavailable",
                        "its preloaded skills",
                        "Workers never see the parent conversation",
                        "**not** the parent's conversation",
                        "preloads this skill",
                        "builder preloads both craft skills",
                        "A researcher with WebFetch",
                    ):
                        self.assertNotIn(false_control, text)

    def test_explicit_only_skills_keep_host_specific_invocation_controls(self) -> None:
        for name in ("host-onboard", "service-onboard"):
            with self.subTest(skill=name):
                copilot_skill = (
                    REPO
                    / generate_platform_adapters.COPILOT_SKILLS
                    / name
                    / "SKILL.md"
                )
                copilot_fields = validate_fleet.parse_frontmatter(copilot_skill)
                self.assertEqual(
                    "true",
                    copilot_fields["disable-model-invocation"],
                )

                codex_skill = (
                    REPO
                    / "plugins"
                    / "sde-agents"
                    / "skills"
                    / name
                    / "SKILL.md"
                )
                codex_fields = validate_fleet.parse_frontmatter(codex_skill)
                self.assertNotIn("disable-model-invocation", codex_fields)
                policy = (
                    codex_skill.parent / "agents" / "openai.yaml"
                ).read_text(encoding="utf-8")
                self.assertIn("display_name:", policy)
                self.assertIn("short_description:", policy)
                self.assertIn("allow_implicit_invocation: false", policy)

    def test_onboarding_map_stays_model_visible_and_keeps_pointing_at_both_workflows(
        self,
    ) -> None:
        """The discovery half of the onboarding lane, whose loss is silent (LANE-001, issue #61).

        `service-onboard` and `host-onboard` are deliberately explicit-only, which on Codex means
        the model cannot enumerate or recommend them at all -- plain-language onboarding intent had
        no model-reachable path to either. `onboarding-map` is the repair: it must stay
        model-invocable on every host, and it must keep naming both workflows. Marking it
        explicit-only, or letting its table stop naming a workflow, raises no error anywhere; the
        discovery path simply disappears again and only a field report would find it.
        """
        canonical = REPO / "skills" / "onboarding-map" / "SKILL.md"
        canonical_fields = validate_fleet.parse_frontmatter(canonical)
        self.assertNotIn("disable-model-invocation", canonical_fields)

        copilot_skill = (
            REPO
            / generate_platform_adapters.COPILOT_SKILLS
            / "onboarding-map"
            / "SKILL.md"
        )
        copilot_fields = validate_fleet.parse_frontmatter(copilot_skill)
        self.assertNotIn("disable-model-invocation", copilot_fields)

        codex_skill = (
            REPO / "plugins" / "sde-agents" / "skills" / "onboarding-map" / "SKILL.md"
        )
        codex_fields = validate_fleet.parse_frontmatter(codex_skill)
        self.assertNotIn("disable-model-invocation", codex_fields)
        # `allow_implicit_invocation: false` in the generated Codex policy is the exact byte that
        # hides a skill from the model, so asserting its absence anywhere under the skill IS this
        # skill's model visibility on that host -- and it survives a generator that later emits a
        # policy file for other reasons.
        for generated in sorted(codex_skill.parent.rglob("*")):
            if generated.is_file():
                with self.subTest(file=str(generated.relative_to(REPO))):
                    self.assertNotIn(
                        "allow_implicit_invocation: false",
                        generated.read_text(encoding="utf-8"),
                    )

        for skill_file, namespace, invocation in (
            (canonical, "sde-agents:", "/sde-agents:"),
            (copilot_skill, "", "/"),
            (codex_skill, "", "$"),
        ):
            with self.subTest(skill=str(skill_file.relative_to(REPO))):
                text = skill_file.read_text(encoding="utf-8")
                for workflow in ("service-onboard", "host-onboard", "homelab-engineer"):
                    self.assertIn(f"`{namespace}{workflow}`", text)
                # The map's whole added value on a host that hides these workflows is naming how
                # to invoke them THERE. A regression in the generator's per-host sigil would leave
                # a Codex user typing Claude syntax that does nothing, and the fleet-wide
                # `sde-agents:`-absence check above cannot see a sigil that is merely wrong.
                for workflow in ("service-onboard", "host-onboard"):
                    self.assertIn(f"`{invocation}{workflow}`", text)

    def test_the_codex_plugin_root_cannot_reach_the_claude_guard(self) -> None:
        # Structural, not declarative. The previous version of this test also asserted that the
        # root Copilot manifest pointed `hooks` at an empty override file -- an assertion that
        # passed while proving nothing, because VS Code reads component overrides from the
        # format's own manifest (`.claude-plugin/plugin.json`) and never from that root file, so
        # it fell back to `hooks/hooks.json` -- the guard itself. Only the absence of a hook file
        # at the host's own hookConfigPath actually keeps a non-Claude host away from the guard.
        codex = json.loads(
            (
                REPO
                / "plugins"
                / "sde-agents"
                / ".codex-plugin"
                / "plugin.json"
            ).read_text(encoding="utf-8")
        )
        self.assertNotIn("hooks", codex)
        self.assertFalse(
            (REPO / "plugins" / "sde-agents" / "hooks" / "hooks.json").exists()
        )

    def test_manifest_identity_and_versions_cannot_drift(self) -> None:
        manifests = [
            json.loads(
                (REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
            ),
            json.loads(
                (
                    REPO
                    / "plugins"
                    / "sde-agents"
                    / ".codex-plugin"
                    / "plugin.json"
                ).read_text(encoding="utf-8")
            ),
        ]
        for field in (
            "name",
            "version",
            "description",
            "author",
            "homepage",
            "repository",
            "license",
            "keywords",
        ):
            with self.subTest(field=field):
                self.assertEqual(
                    [manifests[0][field]] * len(manifests),
                    [m[field] for m in manifests],
                )

        # Codex is the only remaining non-Claude manifest. It packages skills from its own nested
        # plugin root and must not claim to package agents -- Codex plugins do not load custom-agent
        # TOML, so an `agents` field would read as distribution while loading nothing.
        self.assertNotIn("agents", manifests[1])
        self.assertEqual("./skills/", manifests[1]["skills"])

    def test_codex_marketplace_points_to_the_isolated_plugin_root(self) -> None:
        marketplace = json.loads(
            (
                REPO / ".agents" / "plugins" / "marketplace.json"
            ).read_text(encoding="utf-8")
        )
        entries = [
            entry
            for entry in marketplace["plugins"]
            if entry["name"] == "sde-agents"
        ]
        self.assertEqual(1, len(entries))
        self.assertEqual(
            {
                "source": "local",
                "path": "./plugins/sde-agents",
            },
            entries[0]["source"],
        )


if __name__ == "__main__":
    unittest.main()
