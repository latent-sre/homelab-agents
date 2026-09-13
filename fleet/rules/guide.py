"""Drift tripwires for the repository's own agent guide and engineering-program map."""

from __future__ import annotations

import re
from pathlib import Path

from fleet import fs
from fleet.findings import Finding
from fleet.policy import POLICY
from fleet.rules import rule
from fleet.rules.references import INLINE_CODE_RE
from fleet.snapshot import Fleet

# A path-shaped token inside an inline code span. Deliberately excludes glob/placeholder
# characters (`*`, `<`, `>`, `$`, `{`) so illustrative forms like `agents/*.md` self-exclude and
# only concrete, resolvable paths are asserted.
GUIDE_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_./-]*")


def _has_import(path: Path) -> bool:
    return path.is_file() and any(
        line.strip() == POLICY.guide_import for line in fs.read_text(path).splitlines()
    )


def _stale_path_findings(root: Path, doc: Path) -> list[Finding]:
    found: list[Finding] = []
    for span in INLINE_CODE_RE.findall(fs.read_text(doc)):
        for token in GUIDE_PATH_TOKEN_RE.findall(span):
            token = token.rstrip(".,;:")
            # Bare filenames and lone directory mentions are prose, not resolvable claims; only
            # a multi-segment path asserts a location worth checking.
            if len([part for part in token.split("/") if part]) < 2:
                continue
            if not (root / token.rstrip("/")).exists():
                found.append(
                    Finding(
                        "guide.stale-path",
                        f"{doc}: names '{token}', which does not exist in this repository. A "
                        f"stale path here fails nowhere at runtime — it just misleads every "
                        f"future session that reads it.",
                        doc,
                    )
                )
    return found


@rule(
    "guide",
    group="guide",
    why="Claude Code loads CLAUDE.md, not AGENTS.md: a lost import orphans the guide, a renamed "
    "script leaves it pointing at nothing, an alias change leaves it teaching a stale policy.",
    emits=("guide", "guide.bridge", "guide.stale-path", "guide.model-aliases"),
)
def agent_guide(fleet: Fleet) -> list[Finding]:
    """Self-gating: a repo with no AGENTS.md makes no guide claims; same for the program map."""
    root = fleet.root
    findings: list[Finding] = []
    guide = root / "AGENTS.md"
    bridge = root / "CLAUDE.md"

    # The program map is checked BEFORE the guide's early return: a check that a missing
    # UNRELATED file disarms is enforcement prose with no guard behind it (PR #133 finding).
    program = root / POLICY.program_doc
    if program.is_file():
        findings += _stale_path_findings(root, program)

    if not guide.is_file():
        if _has_import(bridge):
            findings.append(
                Finding(
                    "guide.bridge",
                    f"{bridge}: imports {POLICY.guide_import} but AGENTS.md does not exist — the "
                    f"import "
                    f"resolves to nothing and the project context silently loads empty.",
                    bridge,
                )
            )
        return findings

    if not _has_import(bridge):
        findings.append(
            Finding(
                "guide.bridge",
                f"{guide}: exists but {root / 'CLAUDE.md'} does not carry a line reading "
                f"{POLICY.guide_import!r}. Claude Code reads CLAUDE.md, not AGENTS.md (the "
                f"README's own "
                f"bridge convention), so without the import this guide is never loaded by the tool "
                f"it is written for.",
                guide,
            )
        )

    findings += _stale_path_findings(root, guide)

    text = fs.read_text(guide)
    for alias in sorted(POLICY.model_aliases):
        if f"`{alias}`" not in text:
            findings.append(
                Finding(
                    "guide.model-aliases",
                    f"{guide}: the model-alias paraphrase omits `{alias}`; [models] aliases in "
                    f"fleet/policy.toml is the source of truth — fix the paraphrase, never the "
                    f"source.",
                    guide,
                )
            )
    return findings
