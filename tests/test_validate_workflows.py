from __future__ import annotations

import re
import unittest

from scripts import generate_platform_adapters
from scripts import validate_fleet
from tests.support import REPO, repo_copy


class WorkflowEvidenceEnumTests(unittest.TestCase):
    def test_workflow_evidence_enum_drift_is_reported(self) -> None:
        # Proven against a COPY of the real repository so the test breaks the actual shipped
        # workflow, not a synthetic shape that could drift away from it.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8").replace(
                    "const EVIDENCE = ['verified', 'sourced', 'unverified']",
                    "const EVIDENCE = ['verified', 'cited', 'unverified']",
                ),
                encoding="utf-8",
            )
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertTrue(any("canonical" in i and "deep-review" in i for i in issues), issues)

class WorkflowMetaContractTests(unittest.TestCase):
    def test_statement_before_meta_is_reported(self) -> None:
        # Mutation against a COPY of the real shipped workflow, in exactly the shape a merged
        # review-fix commit shipped it: constants declared above `export const meta`. Valid
        # JavaScript, invisible to review, unloadable by the Workflow runtime.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                "const SCOPE_MODEL = 'sonnet'\n" + wf.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertTrue(
            any("first statement" in i and "deep-review" in i for i in issues), issues
        )

    def test_identifier_inside_meta_is_reported(self) -> None:
        # The other half of the same merged breakage: meta.phases referencing a constant.
        # The runtime requires meta to be a pure literal, so the reference fails at load.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8").replace(
                    "model: 'sonnet'", "model: SCOPE_MODEL", 1
                ),
                encoding="utf-8",
            )
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertTrue(
            any("pure literal" in i and "SCOPE_MODEL" in i for i in issues), issues
        )

    def test_leading_block_comment_is_not_a_violation(self) -> None:
        # A `/* ... */` licence or rationale block ahead of meta is a comment, not a statement.
        # A first-statement scan that only skips `//` lines fails a workflow the runtime loads
        # fine -- a false positive that would teach maintainers to work around the rule.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                "/* Deep review pipeline.\n   const SCOPE_MODEL = 'sonnet'\n*/\n"
                + wf.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            self.assertEqual(validate_fleet.validate_workflow_meta_contract(dst), [])

    def test_meta_prefixed_export_without_meta_is_reported(self) -> None:
        # `export const metadata = {...}` shares the prefix but exports no `meta` at all, so a
        # prefix check reads it as satisfied and the workflow cannot load.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8").replace(
                    "export const meta =", "export const metadata =", 1
                ),
                encoding="utf-8",
            )
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertTrue(
            any("first statement" in i and "deep-review" in i for i in issues), issues
        )

    def test_identifier_inside_meta_array_is_reported(self) -> None:
        # The pure-literal contract is violated the same way whether the identifier follows a
        # colon or sits inside an array, but only the colon form is visible to a value-position
        # scan -- so the array form would ship unloadable with the validator green.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8").replace(
                    "phases: [", "phases: [SCOPE_PHASE,", 1
                ),
                encoding="utf-8",
            )
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertTrue(
            any("pure literal" in i and "SCOPE_PHASE" in i for i in issues), issues
        )

    def test_template_literal_inside_meta_is_reported(self) -> None:
        # An interpolating template literal is not a pure literal, and its identifier hides
        # inside the string span where no identifier scan can reach it -- so the construct
        # itself must be the finding.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8").replace(
                    "model: 'sonnet'", "model: `${SCOPE_MODEL}`", 1
                ),
                encoding="utf-8",
            )
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertTrue(
            any("template literal" in i and "deep-review" in i for i in issues), issues
        )

    def test_non_object_meta_is_reported_not_raised(self) -> None:
        # `export const meta = null` has no brace to match: the brace search raised ValueError
        # and crashed the whole validator instead of reporting the workflow that cannot load.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text("export const meta = null\n", encoding="utf-8")
            issues = validate_fleet.validate_workflow_meta_contract(dst)
        self.assertTrue(any("first statement" in i for i in issues), issues)

    def test_body_reference_to_meta_is_reported(self) -> None:
        # Mutation in exactly the shape the 1.7.0 acceptance run caught live: the body deriving
        # a constant FROM meta. The runtime evaluates the body with the meta export isolated, so
        # this validated clean, installed everywhere, and died at every load with
        # "meta is not defined" -- zero agents, no install-time error.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8").replace(
                    "const SCOPE_MODEL = 'sonnet'",
                    "const SCOPE_MODEL = meta.phases[0].model",
                    1,
                ),
                encoding="utf-8",
            )
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertTrue(
            any("not in scope at execution" in i and "deep-review" in i for i in issues),
            issues,
        )

    def test_body_spread_of_meta_is_reported(self) -> None:
        # `{ ...meta }` references the export and dies at load exactly like a bare reference,
        # but the first version of the scan read the spread's third dot as member access and
        # skipped it (review finding) -- shipping the same unloadable class the scan exists for.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8") + "\nconst record = { ...meta, run: 1 }\n",
                encoding="utf-8",
            )
            issues = validate_fleet.validate_workflow_meta_contract(dst)
        self.assertTrue(
            any("not in scope at execution" in i for i in issues), issues
        )

    def test_body_template_interpolation_of_meta_is_reported(self) -> None:
        # Blanking erases backtick contents, so `${meta...}` was invisible to the identifier
        # scan (review finding) while the runtime executes it at load. The meta-object side
        # banned template literals for this exact reason; the body side scans raw spans.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8")
                + "\nlog(`lanes run ${meta.phases[1].model}`)\n",
                encoding="utf-8",
            )
            issues = validate_fleet.validate_workflow_meta_contract(dst)
        self.assertTrue(
            any("template literal interpolates" in i for i in issues), issues
        )

    def test_body_ternary_reference_to_meta_is_reported(self) -> None:
        # `flag ? meta : x` puts a colon after `meta`, and the first key-exemption swallowed it
        # (review finding) -- yet it is a live reference that dies at load. Key position
        # requires a preceding `{` or `,`; a ternary consequent has neither.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8") + "\nconst pick = flag ? meta : 'none'\n",
                encoding="utf-8",
            )
            issues = validate_fleet.validate_workflow_meta_contract(dst)
        self.assertTrue(
            any("not in scope at execution" in i for i in issues), issues
        )

    def test_quoted_meta_string_in_interpolation_stays_legal(self) -> None:
        # `${flag ? 'meta' : ''}` interpolates a STRING named meta, not the export; the raw
        # scan false-fired on it (review finding), failing a workflow the runtime loads fine.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8") + "\nlog(`${flag ? 'meta' : ''}`)\n",
                encoding="utf-8",
            )
            self.assertEqual(validate_fleet.validate_workflow_meta_contract(dst), [])

    def test_body_member_access_and_key_named_meta_stay_legal(self) -> None:
        # `packet.meta` and `{ meta: ... }` are ordinary body JavaScript the runtime loads fine;
        # flagging them would teach maintainers the scan cries wolf and to work around it.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8")
                + "\nconst summary = { meta: 'record' }\nlog(String(summary.meta))\n",
                encoding="utf-8",
            )
            self.assertEqual(validate_fleet.validate_workflow_meta_contract(dst), [])

    def test_lane_literals_match_meta_phase_models(self) -> None:
        # The meta.phases model entries are what the progress UI displays; the SCOPE_MODEL /
        # LANE_MODEL literals are what the agents actually run. The runtime forbids sharing one
        # value (meta must be pure, the body cannot read meta), so only this check keeps the
        # display from claiming one model while the lanes run another.
        text = (REPO / "workflows" / "deep-review.js").read_text(encoding="utf-8")
        phase_models = re.findall(r"model:\s*'([a-z0-9-]+)'", text)
        scope = re.search(r"const SCOPE_MODEL = '([a-z0-9-]+)'", text)
        lane = re.search(r"const LANE_MODEL = '([a-z0-9-]+)'", text)
        self.assertIsNotNone(scope, "SCOPE_MODEL literal not found")
        self.assertIsNotNone(lane, "LANE_MODEL literal not found")
        self.assertEqual(
            phase_models[:2],
            [scope.group(1), lane.group(1)],
            "meta.phases models and the body literals have drifted",
        )

class WorkflowLineEndingTests(unittest.TestCase):
    def test_crlf_workflow_is_reported(self) -> None:
        # Mutation against a COPY of the real shipped workflow: re-encode it exactly the way
        # Windows checkout translation did on installed 1.6.10 (#75) — the failure the rule
        # exists to catch — rather than a synthetic file that could drift from the real shape.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_bytes(wf.read_bytes().replace(b"\n", b"\r\n"))
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertTrue(
            any("carriage returns" in i and "deep-review" in i for i in issues), issues
        )

    def test_missing_gitattributes_js_eol_rule_is_reported(self) -> None:
        # Removing the `*.js text eol=lf` rule from .gitattributes is a configuration
        # regression: any subsequent fresh Windows checkout would translate workflows to CRLF
        # and the Workflow tool would refuse to run them. The byte check alone cannot catch
        # this because the file on disk stays LF until the next checkout. Verify that the
        # validator fires when only the rule is removed (bytes left intact).
        with repo_copy() as dst:
            ga = dst / ".gitattributes"
            ga.write_text(
                "\n".join(
                    line
                    for line in ga.read_text(encoding="utf-8").splitlines()
                    if "*.js text eol=lf" not in line
                )
                + "\n",
                encoding="utf-8",
            )
            issues = validate_fleet.validate_workflow_line_endings(dst)
        self.assertTrue(
            any("missing" in i and "*.js text eol=lf" in i for i in issues), issues
        )

    def test_missing_gitattributes_file_is_reported(self) -> None:
        # Deleting the whole file is the same configuration regression as deleting its JS
        # rule. An existence guard must not turn the more severe mutation into a false green.
        with repo_copy() as dst:
            (dst / ".gitattributes").unlink()
            issues = validate_fleet.validate_workflow_line_endings(dst)
        self.assertTrue(
            any("missing" in i and "*.js text eol=lf" in i for i in issues), issues
        )

class WorkflowHostBoundaryTests(unittest.TestCase):
    def test_adapter_referencing_workflow_is_reported(self) -> None:
        with repo_copy() as dst:
            adapter = next(iter(sorted((dst / ".github" / "agents").glob("*.md"))))
            adapter.write_text(
                adapter.read_text(encoding="utf-8")
                + "\nRun /sde-agents:deep-review before merging.\n",
                encoding="utf-8",
            )
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertTrue(any("no workflow runtime" in i for i in issues), issues)

    def test_generated_script_resource_referencing_workflow_is_reported(self) -> None:
        # Generated skill resources are not limited to the prose/config suffixes originally
        # scanned here. A shell asset carrying the same unusable instruction must not bypass
        # the host boundary merely because its extension was absent from a validator tuple.
        with repo_copy() as dst:
            resource = (
                dst
                / generate_platform_adapters.COPILOT_SKILLS
                / "probe"
                / "scripts"
                / "run.sh"
            )
            resource.parent.mkdir(parents=True)
            resource.write_text("Run /sde-agents:deep-review before merging.\n", encoding="utf-8")
            issues = validate_fleet.validate_workflow_host_boundary(dst)
        self.assertTrue(any("no workflow runtime" in i and "run.sh" in i for i in issues), issues)

    def test_every_declared_adapter_tree_is_actually_scanned(self) -> None:
        # Until `.claude/agents` was retired, only ONE of the four declared trees had coverage: a
        # declared-but-unscanned tree (typo, renamed directory, skipped branch) would leave the
        # boundary reading as enforced across all hosts while enforcing it on one. Plant the same
        # unusable instruction in each generator-owned tree and require the scan to name it. The
        # validator now reads this same tuple directly, so no equality tripwire is needed.
        with repo_copy() as dst:
            planted_paths = []
            for tree in generate_platform_adapters.GENERATED_ROOTS:
                base = dst / tree
                self.assertTrue(base.is_dir(), f"{tree} is declared but absent from the tree")
                planted = base / "boundary-probe.md"
                planted.write_text(
                    "Run /sde-agents:deep-review before merging.\n", encoding="utf-8"
                )
                planted_paths.append(planted)
            issues = validate_fleet.validate_workflow_host_boundary(dst)
            for planted in planted_paths:
                self.assertTrue(
                    any("no workflow runtime" in i and str(planted) in i for i in issues),
                    f"{planted}: declared adapter tree is not scanned; issues={issues}",
                )

    def test_adapter_roots_come_from_the_tree_under_validation(self) -> None:
        # `--root` may validate a checkout whose generator owns a newer host tree than the
        # validator process. Reading the executing checkout's tuple would omit that tree and
        # silently certify a workflow reference that the target checkout actually distributes.
        with repo_copy() as dst:
            generator = dst / "scripts" / "generate_platform_adapters.py"
            original = generator.read_text(encoding="utf-8")
            mutated = original.replace(
                "GENERATED_ROOTS = (\n",
                'GENERATED_ROOTS = (\n    Path("target-only-adapters"),\n',
                1,
            )
            self.assertNotEqual(original, mutated, "generator root declaration was not mutated")
            generator.write_text(mutated, encoding="utf-8")

            planted = dst / "target-only-adapters" / "boundary-probe.md"
            planted.parent.mkdir(parents=True)
            planted.write_text(
                "Run /sde-agents:deep-review before merging.\n", encoding="utf-8"
            )

            issues = validate_fleet.validate_workflow_host_boundary(dst)

        self.assertTrue(
            any("no workflow runtime" in i and "target-only-adapters" in i for i in issues),
            issues,
        )

    def test_untracked_python_cache_is_not_treated_as_a_shipped_workflow_reference(self) -> None:
        # The adapter generator already excludes runtime bytecode from distributable outputs.
        # A local import must not make the host-boundary scan certify a different file set.
        with repo_copy() as dst:
            byproduct = (
                dst
                / generate_platform_adapters.COPILOT_SKILLS
                / "probe"
                / "__pycache__"
                / "probe.pyc"
            )
            byproduct.parent.mkdir(parents=True)
            byproduct.write_bytes(b"runtime cache /sde-agents:deep-review")
            issues = validate_fleet.validate_workflow_host_boundary(dst)
        self.assertEqual([], issues)

if __name__ == "__main__":
    unittest.main()
