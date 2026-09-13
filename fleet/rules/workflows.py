"""Workflow (`workflows/*.js`) rules: the evidence enum, line endings, the meta contract, and
the Claude-only host boundary. Ported verbatim; each docstring carries its incident."""

from __future__ import annotations

import re
from pathlib import Path

from fleet import fs, modules
from fleet.findings import Finding
from fleet.policy import POLICY
from fleet.rules import rule
from fleet.rules.adapters import load_platform_adapter_generator
from fleet.snapshot import Fleet

WORKFLOW_EVIDENCE_ENUM_RE = re.compile(r"const\s+EVIDENCE\s*=\s*\[([^\]]*)\]")
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _executing_generator():
    """The generator of the executing checkout, for a tree that ships no manifest of its own."""
    module = modules.load_module_by_content(
        _REPO_ROOT / "scripts" / "generate_platform_adapters.py", "platform_adapters"
    )
    if module is None:
        raise ImportError("cannot load the executing checkout's adapter generator")
    return module


def validate_workflow_evidence_enums(root: Path) -> list[str]:
    """Every workflow script that declares an EVIDENCE enum must match the canonical triad."""
    issues: list[str] = []
    workflows_dir = root / "workflows"
    if not workflows_dir.is_dir():
        return issues
    for path in sorted(workflows_dir.glob("*.js")):
        text = fs.read_text(path)
        matches = WORKFLOW_EVIDENCE_ENUM_RE.findall(text)
        if "evidence" in text and not matches:
            issues.append(
                f"{path}: declares an evidence field without a parseable `const EVIDENCE = [...]` "
                f"enum, so the canonical triad cannot be pinned and drift would be invisible "
                f"until a live run fails schema validation."
            )
        for group in matches:
            values = tuple(v.strip().strip("'\"") for v in group.split(",") if v.strip())
            if values != POLICY.workflow_evidence_enum:
                issues.append(
                    f"{path}: workflow evidence enum {values!r} does not match the canonical "
                    f"triad {POLICY.workflow_evidence_enum!r} from EVIDENCE_LABEL_STEMS; a "
                    f"drifted enum "
                    f"ships a packet contract that fails five retries deep with no load-time error."
                )
    return issues


def validate_workflow_line_endings(root: Path) -> list[str]:
    """No workflow script may contain a carriage return in the bytes actually on disk, and
    `.gitattributes` must carry the `*.js text eol=lf` rule that prevents Windows checkout
    translation from re-introducing them.

    The Workflow tool rejects any script containing \\r ("control characters that would be
    hidden in the approval dialog") BEFORE execution, so a CRLF workflow ships as configured
    and fails on first invocation with no load-time error -- proven on installed 1.6.10, where
    Windows checkout translation made the fleet's only workflow unrunnable (#75) while the
    probe passed against its own LF-written fixture. Checking only checkout bytes misses the
    configuration regression: a fresh Windows clone after the rule is removed would get CRLF
    and fail silently, and the byte check would pass on any machine where the file was already
    LF. Both conditions must hold -- no \\r bytes AND the pin must be present.
    """
    issues: list[str] = []
    workflows_dir = root / "workflows"
    if not workflows_dir.is_dir():
        return issues

    # Check that the eol pin is present in .gitattributes -- the byte check below passes on
    # any machine where files were already checked out as LF, so removing the rule would not
    # be caught by bytes alone. A fresh Windows clone after the rule is removed gets CRLF and
    # fails on first workflow invocation, exactly the silent failure class this rule closes.
    gitattributes = root / ".gitattributes"
    content = (
        gitattributes.read_text(encoding="utf-8", errors="replace")
        if gitattributes.is_file()
        else ""
    )
    if "*.js text eol=lf" not in content:
        issues.append(
            f"{gitattributes}: missing `*.js text eol=lf` rule; without it, Windows "
            f"checkout translation will convert workflows/*.js to CRLF and the Workflow "
            f"tool will refuse to run them -- the byte check alone cannot catch this "
            f"because it passes on any machine where the files are already LF on disk."
        )

    for path in sorted(workflows_dir.glob("*.js")):
        if b"\r" in path.read_bytes():
            issues.append(
                f"{path}: contains carriage returns; the Workflow tool refuses \\r-bearing "
                f"scripts before execution, so this workflow would install everywhere and run "
                f"nowhere -- check the `*.js text eol=lf` line in .gitattributes."
            )
    return issues


def _blank_js_strings_and_comments(source: str) -> str:
    """Overwrite the contents of '...', \"...\", and `...` literals -- and the whole of `//` and
    `/* */` comments -- with spaces, so structural scans (first-statement detection, brace
    matching, identifier detection) cannot be fooled by braces or identifier-shaped text that is
    only prose. Comments must blank the same way strings do: a leading licence or rationale block
    scanned as code reads as a statement ahead of `meta` and fails a workflow the runtime loads
    fine.

    Length and newlines are preserved, so an offset found in the blanked text indexes the same
    character of the raw source -- the checks that must see original bytes (a template literal's
    backticks inside meta) slice the identical span."""
    out = list(source)
    length = len(source)
    index = 0
    while index < length:
        ch = source[index]
        if ch in "'\"`":
            quote = ch
            index += 1
            while index < length:
                current = source[index]
                if current == "\\":
                    # Blank the escape and whatever it escapes together, so an escaped closing
                    # quote cannot end the literal early and leak the rest of the file into a
                    # scan as if it were code.
                    out[index] = " "
                    if index + 1 < length and source[index + 1] != "\n":
                        out[index + 1] = " "
                    index += 2
                    continue
                if current == quote:
                    index += 1
                    break
                if current != "\n":
                    out[index] = " "
                index += 1
            continue
        if ch == "/" and index + 1 < length and source[index + 1] == "/":
            while index < length and source[index] != "\n":
                out[index] = " "
                index += 1
            continue
        if ch == "/" and index + 1 < length and source[index + 1] == "*":
            out[index] = out[index + 1] = " "
            index += 2
            while index < length:
                if source[index] == "*" and index + 1 < length and source[index + 1] == "/":
                    out[index] = out[index + 1] = " "
                    index += 2
                    break
                if source[index] != "\n":
                    out[index] = " "
                index += 1
            continue
        index += 1
    return "".join(out)


# Identifier-shaped tokens that are legal literal values inside a pure-literal object.
_META_LITERAL_KEYWORDS = {"true", "false", "null", "undefined"}
# The declaration must be matched whole: `export const metadata = {...}` shares this prefix, and
# accepting it would let a workflow with no `meta` export at all validate clean while the runtime
# cannot load it. Requiring the opening brace here also means a non-object meta
# (`export const meta = null`) is a reported finding rather than a brace-search traceback.
_META_DECLARATION_RE = re.compile(r"export\s+const\s+meta\s*=\s*\{")
_META_IDENTIFIER_RE = re.compile(r"[A-Za-z_$][\w$]*")


def validate_workflow_meta_contract(root: Path) -> list[str]:
    """`export const meta` must be each workflow's first statement, the meta object must be a
    pure literal, and the body must not reference `meta`.

    The Workflow runtime extracts `meta` statically before execution: a statement ahead of it,
    or an identifier reference inside it, parses as valid JavaScript and reads as configured in
    review, then fails at workflow load with no install-time error. Proven live: a review-fix
    commit moved the lane-model constants above `meta` and referenced them from
    `meta.phases[*].model`, shipping the fleet's only workflow in a shape the runtime cannot
    load -- the validator passed, the tests passed, and nothing would have said so before the
    first billed invocation.

    The body ban is the same failure from the other side, and its proof is the 1.7.0 acceptance
    run: the repair derived the constants FROM meta (`const SCOPE_MODEL = meta.phases[0].model`),
    which this validator blessed -- but the runtime evaluates the body with the meta export
    isolated, so `meta` is not in scope at execution and every invocation died at load with
    "meta is not defined" (2026-08-09, CLI 2.1.226, run wf_c1db8dfb-b9f, zero agents spawned).
    Both directions of sharing one value between meta and the body are therefore banned; the
    only loadable shape is a repeated literal held equal by a deterministic check."""
    issues: list[str] = []
    workflows_dir = root / "workflows"
    if not workflows_dir.is_dir():
        return issues
    for path in sorted(workflows_dir.glob("*.js")):
        text = fs.read_text(path)
        blanked = _blank_js_strings_and_comments(text)
        first = re.search(r"\S", blanked)
        if first is None:
            issues.append(
                f"{path}: workflow file has no statements; it exports no `meta` and cannot load."
            )
            continue
        start = first.start()
        line_end = blanked.find("\n", start)
        found = text[start : line_end if line_end != -1 else len(text)].strip()
        declaration = _META_DECLARATION_RE.match(blanked, start)
        if declaration is None:
            issues.append(
                f"{path}: `export const meta = {{` is not the file's first statement (found "
                f"{found[:60]!r} first); the Workflow runtime requires an object-literal meta to "
                f"lead the file, so this workflow would install everywhere and fail to load "
                f"with no install-time error."
            )
            continue
        open_index = declaration.end() - 1
        depth = 0
        close_index = None
        for index in range(open_index, len(blanked)):
            if blanked[index] == "{":
                depth += 1
            elif blanked[index] == "}":
                depth -= 1
                if depth == 0:
                    close_index = index
                    break
        if close_index is None:
            issues.append(
                f"{path}: could not brace-match the meta object literal; an unparseable meta "
                f"fails at workflow load with no install-time error."
            )
            continue
        if "`" in text[open_index : close_index + 1]:
            # A template literal is not a pure literal the moment it interpolates, and the
            # interpolated identifier lives inside the blanked span where no scan can see it --
            # so the construct itself is the finding rather than its contents.
            issues.append(
                f"{path}: meta contains a template literal; the runtime requires meta to be a "
                f"pure literal, and an interpolated `${{...}}` reads as configured while failing "
                f"at workflow load -- use a plain quoted string."
            )
        meta_block = blanked[open_index : close_index + 1]
        for match in _META_IDENTIFIER_RE.finditer(meta_block):
            token = match.group(0)
            if token in _META_LITERAL_KEYWORDS:
                continue
            after = meta_block[match.end() :].lstrip()
            if after[:1] == ":":
                # A property key, not a value.
                continue
            issues.append(
                f"{path}: meta contains the identifier reference {token!r}; the "
                f"runtime requires meta to be a pure literal, so a variable here parses as "
                f"valid JavaScript, reads as configured, and fails at workflow load with no "
                f"install-time error -- repeat the value as a literal on both sides and let a "
                f"deterministic check hold the copies equal (the body cannot read meta either)."
            )
        body_offset = close_index + 1
        for match in _META_IDENTIFIER_RE.finditer(blanked, body_offset):
            if match.group(0) != "meta":
                continue
            preceding = blanked[: match.start()].rstrip()
            if preceding.endswith(".") and not preceding.endswith(".."):
                # `something.meta` is a property of another object, not the export. Spread
                # (`...meta`) must NOT take this exit: it references the export and dies at
                # load exactly like a bare reference (review finding on the first version of
                # this scan, which read the third spread dot as member access).
                continue
            if blanked[match.end() :].lstrip()[:1] == ":" and preceding[-1:] in {"{", ","}:
                # `{ meta: ... }` in a body-local object is a key, not a reference -- but only
                # in key position (after `{` or `,`). A colon alone also follows a ternary
                # consequent (`flag ? meta : x`), which IS a live reference that dies at load;
                # the first version of this exemption swallowed it (review finding).
                continue
            line_number = blanked.count("\n", 0, match.start()) + 1
            issues.append(
                f"{path}:{line_number}: the workflow body references `meta`; the runtime "
                f"evaluates the body with the meta export isolated, so `meta` is not in scope "
                f"at execution -- the script validates, installs everywhere, then fails every "
                f"invocation at load with 'meta is not defined'. Repeat the value as a literal "
                f"and let a deterministic check hold the copies equal. A body-local `meta` "
                f"declaration is banned by this same scan -- rename it."
            )
            break
        # The meta-side template ban above has a body-side twin: blanking erases backtick
        # contents, so a `${meta...}` interpolation is invisible to the identifier scan while
        # the runtime executes it at body load and dies the same way. Surviving backticks in
        # the blanked text are exactly the real template delimiters (quoted and commented
        # backticks were blanked), so pair them and scan the RAW spans for interpolated `meta`.
        # Nesting a template or extra braces inside an interpolation stays out of this flat
        # scan's reach -- a missed exotic nesting is a silent non-fire, the right failure
        # direction for a tripwire.
        tick_positions = [i for i in range(body_offset, len(blanked)) if blanked[i] == "`"]
        for open_tick, close_tick in zip(tick_positions[0::2], tick_positions[1::2], strict=False):
            raw_span = text[open_tick : close_tick + 1]
            # Blank quoted strings inside each interpolation before searching: `${flag ? 'meta'
            # : ''}` interpolates a STRING named meta, not the export, and the raw scan
            # false-fired on it (review finding) -- failing a workflow the runtime loads fine.
            interpolated = any(
                re.search(
                    r"(?<![.\w$])meta\b(?!\s*:)",
                    re.sub(r"'[^'\n]*'|\"[^\"\n]*\"", " ", interp.group(1)),
                )
                for interp in re.finditer(r"\$\{([^}]*)\}", raw_span)
            )
            if interpolated:
                line_number = text.count("\n", 0, open_tick) + 1
                issues.append(
                    f"{path}:{line_number}: a body template literal interpolates `meta`; the "
                    f"runtime evaluates the body with the meta export isolated, so the "
                    f"interpolation throws at load with 'meta is not defined' -- and the "
                    f"identifier scan cannot see it because string contents are blanked. "
                    f"Interpolate a repeated literal constant instead."
                )
                break
    return issues


# Workflows are Claude-only: the other hosts have no workflow runtime, so a generated adapter
# that mentions one teaches an instruction that cannot execute there -- it reads as configured
# and fails silently, the exact failure class the bare-skill-reference rule already catches for
# skills. Match both the invocation form and the directory form. Generated skill resources may
# use any extension, so scan bytes rather than maintaining a text-suffix allowlist that lets the
# same unusable instruction bypass the rule when it moves from Markdown into a shell asset.
def validate_workflow_host_boundary(root: Path) -> list[str]:
    """No generated non-Claude adapter may reference a plugin workflow."""
    issues: list[str] = []
    workflow_names = set()
    workflows_dir = root / "workflows"
    if workflows_dir.is_dir():
        workflow_names = {p.stem for p in workflows_dir.glob("*.js")}
    if not workflow_names:
        return issues

    generated_roots = _executing_generator().GENERATED_ROOTS
    if (root / ".claude-plugin" / "plugin.json").is_file():
        try:
            # Read authority from the checkout being validated. The content-keyed loader returns
            # the same module used by adapter byte validation, so a target-only tree cannot fall
            # outside this scan while its generated bytes still ship to a host.
            generated_roots = load_platform_adapter_generator(root).GENERATED_ROOTS
        except Exception:
            # validate_platform_adapters owns the precise load/crash diagnostic. Repeating it here
            # would turn one broken generator into two findings without adding evidence.
            return issues

    for tree in generated_roots:
        base = root / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(base)
            # The generator consumes this same predicate and never distributes these paths. A
            # local Python import therefore cannot make this scan inspect bytes no recipient gets.
            if fs.is_runtime_byproduct(relative):
                continue
            content = path.read_bytes()
            for name in sorted(workflow_names):
                invocation = f"/sde-agents:{name}".encode("ascii")
                directory_reference = f"workflows/{name}".encode("ascii")
                if invocation in content or directory_reference in content:
                    issues.append(
                        f"{path}: generated non-Claude adapter references the Claude-only "
                        f"workflow {name!r}; that host has no workflow runtime, so the "
                        f"instruction reads as available and fails silently at use time."
                    )
    return issues


def _wrap(rule_id: str, issues: list[str]) -> list[Finding]:
    """Findings from legacy `path: message` strings; the path prefix is parsed back out."""
    findings = []
    for text in issues:
        head = text.split(": ", 1)[0]
        # `path:line: message` carries a line number in the second segment.
        parts = head.rsplit(":", 1)
        line = None
        if len(parts) == 2 and parts[1].isdigit():
            head, line = parts[0], int(parts[1])
        findings.append(Finding(rule_id, text, Path(head), line))
    return findings


@rule(
    "workflow.evidence-enum",
    group="workflows",
    why="A drifted enum ships a packet contract that fails five retries deep with no load-time "
    "error.",
)
def workflow_evidence_enums(fleet: Fleet) -> list[Finding]:
    return _wrap("workflow.evidence-enum", validate_workflow_evidence_enums(fleet.root))


@rule(
    "workflow.line-endings",
    group="workflows",
    why="A CRLF workflow ships as configured and fails on first invocation; only the "
    ".gitattributes pin prevents it on a fresh Windows clone.",
)
def workflow_line_endings(fleet: Fleet) -> list[Finding]:
    return _wrap("workflow.line-endings", validate_workflow_line_endings(fleet.root))


@rule(
    "workflow.meta-contract",
    group="workflows",
    why="The runtime extracts meta statically; a non-literal meta or a body reference to it loads "
    "nowhere and fails every billed invocation.",
)
def workflow_meta_contract(fleet: Fleet) -> list[Finding]:
    return _wrap("workflow.meta-contract", validate_workflow_meta_contract(fleet.root))


@rule(
    "workflow.host-boundary",
    group="workflows",
    why="Other hosts have no workflow runtime; an adapter that mentions one reads as configured "
    "and fails silently.",
)
def workflow_host_boundary(fleet: Fleet) -> list[Finding]:
    return _wrap("workflow.host-boundary", validate_workflow_host_boundary(fleet.root))
