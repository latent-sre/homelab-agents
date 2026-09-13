"""Structured validation findings and the renderers every instrument shares.

A finding used to be a free-form string, so a reworded diagnostic was a test failure and no
consumer could filter by rule, path, or severity. A `Finding` keeps the exact message register
the fleet already relies on -- what broke *and why it would have failed silently* -- and adds the
handles a consumer needs: a stable rule id, the path, and the line when one is known.

`text` is the complete legacy message, path prefix included, and stays byte-identical across the
migration so every existing assertion holds; the human renderer prints it unchanged. The JSON
and GitHub-annotation renderers are where the structure pays off.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from fleet import diagnostics

SEVERITIES = ("error", "warning")


@dataclass(frozen=True)
class Finding:
    """One rule's verdict about one place in the tree."""

    rule: str
    text: str
    path: Path | None = None
    line: int | None = None
    severity: str = "error"

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"unknown finding severity: {self.severity!r}")
        if not self.rule:
            raise ValueError("a finding must name its rule")

    def relative_path(self, root: Path) -> str | None:
        """The path as a repo-relative POSIX string, or the absolute path when outside root."""
        if self.path is None:
            return None
        try:
            return Path(self.path).relative_to(root).as_posix()
        except ValueError:
            return Path(self.path).as_posix()


class Report:
    """The findings of one validation run over one root, with the renderers and exit code."""

    def __init__(self, root: Path, findings: Iterable[Finding]) -> None:
        self.root = Path(root)
        self.findings: tuple[Finding, ...] = tuple(findings)

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == "error")

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == "warning")

    @property
    def texts(self) -> list[str]:
        """The legacy `list[str]` view: every finding's full message, in order."""
        return [finding.text for finding in self.findings]

    def exit_status(self) -> int:
        return diagnostics.exit_status(
            failed=len(self.errors), not_computed=0, warned=len(self.warnings)
        )

    def render_human(self, *, success: str = "") -> str:
        if not self.findings:
            return success
        lines = ["Fleet validation failed:"]
        lines += [f"- {finding.text}" for finding in self.findings]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "root": self.root.as_posix(),
            "summary": {"error": len(self.errors), "warning": len(self.warnings)},
            "findings": [
                {
                    "rule": f.rule,
                    "severity": f.severity,
                    "path": f.relative_path(self.root),
                    "line": f.line,
                    "message": f.text,
                }
                for f in self.findings
            ],
        }

    def render_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def render_github(self) -> str:
        """GitHub Actions workflow commands, one annotation per finding.

        `::error file=...,line=...,title=<rule>::<message>` surfaces each finding inline on the
        PR diff instead of only in a job log nobody opens. Newlines and the characters the
        command grammar reserves are percent-encoded per the Actions specification.
        """
        lines = []
        for finding in self.findings:
            properties = []
            relative = finding.relative_path(self.root)
            if relative:
                properties.append(f"file={_escape_property(relative)}")
            if finding.line is not None:
                properties.append(f"line={finding.line}")
            properties.append(f"title={_escape_property(finding.rule)}")
            lines.append(
                f"::{finding.severity} {','.join(properties)}::{_escape_data(finding.text)}"
            )
        return "\n".join(lines)


def _escape_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(value: str) -> str:
    return _escape_data(value).replace(":", "%3A").replace(",", "%2C")


def texts(findings: Sequence[Finding]) -> list[str]:
    return [finding.text for finding in findings]
