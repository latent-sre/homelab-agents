"""Executes the shipped deep-review workflow the way the Workflow runtime does.

`workflows/deep-review.js` has shipped unloadable twice — once with the lane constants declared
ahead of `export const meta`, once deriving them FROM `meta`. Both parse as valid JavaScript and
read as configured in review; the runtime extracts `meta` statically and evaluates the body with
that export isolated, so the second shape died at every invocation with "meta is not defined"
(2026-08-09, CLI 2.1.226, run wf_c1db8dfb-b9f) with zero agents spawned and no install-time error.

`scripts/validate_fleet.validate_workflow_meta_contract` catches that class lexically and
documents its own limit: "Nesting a template or extra braces inside an interpolation stays out of
this flat scan's reach -- a missed exotic nesting is a silent non-fire." This module narrows that
limit by execution instead of pattern-matching: the body is isolated from `meta` exactly as the
runtime isolates it, then run under Node against stubbed `agent`/`parallel`/`phase` primitives, so
any surviving reference throws here instead of in production. The gap is real rather than
theoretical — this body line passes the whole validator clean and dies here with the historical
"ReferenceError: meta is not defined" (mutation-proven when this module landed):

    const label = `${ ({}).nope ?? meta }`

Narrows, not closes: the two instruments are complementary rather than nested, and one compound
shape defeats both. `_META_EXPORT` below ends the export at a column-0 `}`, so a `meta` reformatted
without one (a single-line object) lets the lazy match run past it and silently delete a body
prefix. On its own that still fails loudly, and the validator catches it — but a deleted prefix
whose only `meta` reference is nested-brace-template-shaped is invisible to both at once
(independently reproduced at verification, 2026-08-10). A brace-matching end anchor, the depth
count the validator already carries, would retire the hole; it is unbuilt, so the boundary is
stated here rather than implied away.

Node is an external binary, not a repository dependency: a machine without it skips.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.support import REPO

NODE = shutil.which("node")
WORKFLOW = REPO / "workflows" / "deep-review.js"

# Leading comments and blank lines are legal ahead of `meta` — tests/test_validate_fleet.py's
# test_leading_block_comment_is_not_a_violation blesses exactly that, and validate_fleet.py
# blanks comments so its own first-statement scan agrees. Anchoring the strip at byte 0 would
# contradict both and fail a workflow the runtime loads fine.
_LEADING_TRIVIA = re.compile(r"(?:\s|//[^\n]*|/\*.*?\*/)*", re.DOTALL)
_META_EXPORT = re.compile(r"export const meta = \{.*?^\}$\n?", re.DOTALL | re.MULTILINE)

# `parallel` resolves a failed thunk to null (documented runtime contract), so the stub returns
# whatever the fixture supplies — including null — rather than inventing a shape.
_HARNESS = """\
import { readFileSync } from 'node:fs'
const payload = JSON.parse(readFileSync(process.argv[2], 'utf8'))
const args = payload.args ?? null
const labels = []
const phase = () => {}
const agent = async (prompt, options) => {
  labels.push(options.label)
  if (!(options.label in payload.responses)) {
    throw new Error(`no fixture response for lane ${options.label}`)
  }
  return payload.responses[options.label]
}
const parallel = async (lanes) => Promise.all(lanes.map((lane) => lane().catch(() => null)))
const execute = async () => {
__WORKFLOW_BODY__
}
const result = await execute()
process.stdout.write(JSON.stringify({ result, labels }))
"""

SCOPE = {
    "base_ref": "1111111111111111111111111111111111111111",
    "head_sha": "2222222222222222222222222222222222222222",
    "tree_dirty": False,
    "changed_files": ["scripts/validate_fleet.py"],
    "diff_summary": "scripts/validate_fleet.py: one rule added",
}

CRITICAL_FINDING = {
    "file": "scripts/validate_fleet.py",
    "line": 12,
    "claim": "the new rule never fires",
    "severity": "P1",
    "evidence": "verified",
    "failure_scenario": "a violating fixture validates clean",
}


def packet(verdict: str = "approve", findings: list[dict] | None = None) -> dict:
    return {"findings": findings or [], "verdict": verdict, "not_checked": "nothing"}


def isolated_body() -> str:
    """The shipped workflow with the `meta` export removed — the runtime's execution view."""
    source = WORKFLOW.read_text(encoding="utf-8")
    start = _LEADING_TRIVIA.match(source).end()
    match = _META_EXPORT.match(source, start)
    if match is None:
        raise AssertionError(
            f"cannot isolate the `meta` export in {WORKFLOW}: after leading comments and "
            f"whitespace the first statement must be `export const meta = {{` closed by a "
            f"column-0 `}}`. Anything ahead of it is the first historical break — the runtime "
            f"extracts meta statically and the workflow will not load."
        )
    return source[match.end() :]


@unittest.skipUnless(NODE, "node is not installed; cannot execute the shipped workflow")
class DeepReviewExecutionTests(unittest.TestCase):
    def _execute(self, payload: dict) -> subprocess.CompletedProcess:
        harness = _HARNESS.replace("__WORKFLOW_BODY__", isolated_body())
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "harness.mjs"
            fixture = Path(tmp) / "payload.json"
            # LF, like the shipped workflow (.gitattributes pins `*.js text eol=lf`): the
            # harness must execute the same bytes the runtime would, not a CRLF translation
            # of them.
            script.write_text(harness, encoding="utf-8", newline="\n")
            fixture.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
            return subprocess.run(
                [NODE, str(script), str(fixture)],
                capture_output=True,
                text=True,
                check=False,
            )

    def _run(self, payload: dict) -> tuple[dict, list[str]]:
        completed = self._execute(payload)
        self.assertEqual(0, completed.returncode, completed.stderr)
        emitted = json.loads(completed.stdout)
        return emitted["result"], emitted["labels"]

    def test_workflow_body_never_references_meta(self) -> None:
        # The named guard for the 1.7.0 field failure. It fails by name rather than taking the
        # module down with an unrelated message, because the diagnosis is the whole value: a
        # ReferenceError here means the shipped workflow is dead at load everywhere it is
        # installed, whatever else the suite says.
        completed = self._execute(
            {"responses": {"scope": SCOPE, "review": packet(), "security": packet()}}
        )
        self.assertEqual(
            0,
            completed.returncode,
            "the workflow body must execute with the `meta` export isolated, as the runtime "
            "evaluates it. node reported:\n" + completed.stderr,
        )

    def test_merge_record_gates_on_criticals_then_verdicts_then_tree_state(self) -> None:
        # The record is the workflow's only output that anything acts on, and it is gated in
        # code rather than by the lanes: a P0/P1 finding must sink an "approve" lane, and a
        # dirty tree must cap the record at the reviewer's provisional form.
        cases = [
            ("merge", False, packet(), packet()),
            ("merge-with-nits", False, packet("approve-with-nits"), packet()),
            ("do-not-merge", False, packet("request-changes"), packet()),
            ("do-not-merge", False, packet(findings=[CRITICAL_FINDING]), packet()),
            # dirty tree: blocking conditions take precedence over tree state
            ("do-not-merge", True, packet(findings=[CRITICAL_FINDING]), packet()),
            ("do-not-merge", True, packet("request-changes"), packet()),
            ("provisional-commit-and-re-review", True, packet(), packet()),
        ]
        for expected, dirty, review, security in cases:
            with self.subTest(expected=expected, tree_dirty=dirty):
                result, _ = self._run(
                    {
                        "responses": {
                            "scope": {**SCOPE, "tree_dirty": dirty},
                            "review": review,
                            "security": security,
                        }
                    }
                )
                self.assertEqual(expected, result["verdict"])

    def test_empty_diff_returns_no_diff_without_spending_the_review_lanes(self) -> None:
        result, labels = self._run(
            {"responses": {"scope": {**SCOPE, "changed_files": [], "diff_summary": ""}}}
        )
        self.assertEqual("no-diff", result["verdict"])
        self.assertEqual(["scope"], labels)

    def test_unsupported_args_fail_closed_before_any_agent_runs(self) -> None:
        # Issues #63/#64: the natural wrong invocations. Each must cost nothing — a prose brief
        # silently defaulting to the ambient diff, or a range producing the conflated
        # working-tree-vs-range diff, are both worse than an error.
        for args in ("main..topic", "review the auth changes", "--stat"):
            with self.subTest(args=args):
                result, labels = self._run({"args": args, "responses": {}})
                self.assertEqual("inconclusive", result["verdict"])
                self.assertEqual("scope", result["failed_lane"])
                self.assertEqual([], labels)


if __name__ == "__main__":
    unittest.main()
