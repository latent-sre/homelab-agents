"""Frontmatter scalars a conforming YAML parser would refuse, or this dialect would mangle."""

from __future__ import annotations

from fleet.findings import Finding
from fleet.frontmatter import TOP_LEVEL_KEY_RE, flow_scalar_defect
from fleet.policy import POLICY
from fleet.rules import rule
from fleet.snapshot import Fleet


@rule(
    "frontmatter.scalar",
    group="scalars",
    why="A prose scalar with an unbalanced quote, a bad escape, or an unquoted ': ' validates "
    "here and re-serializes cleanly, while a host with a strict parser drops the component "
    "with no error anyone sees.",
)
def frontmatter_scalars(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    rid = "frontmatter.scalar"
    for definition in fleet.definitions():
        path = definition.path
        if definition.span is None:
            continue  # Absent or unterminated frontmatter is the agent/skill rules' report to make.
        for line in definition.lines[1 : definition.span]:
            # TOP_LEVEL_KEY_RE is anchored at column zero, so the indented continuation lines of
            # a `description: >` block scalar never reach this check -- and a colon-space is
            # legal inside one, which is why they must not.
            match = TOP_LEVEL_KEY_RE.match(line)
            if not match:
                continue
            key, value = match.groups()
            value = value.strip()
            if key not in POLICY.prose_scalar_fields or not value:
                continue
            # A quoted scalar may hold anything -- but only once its quote CLOSES, closes with
            # nothing after it, and escapes nothing YAML does not define (review finding, PR #107:
            # skipping on the opening character alone left `"Use when routing: requests` reachable).
            if value[0] in "\"'":
                defect = flow_scalar_defect(value)
                if defect is None:
                    continue
                findings.append(
                    Finding(
                        rid,
                        f"{path}: {key!r} frontmatter value {defect}. Nothing downstream can see "
                        f"it: "
                        f"this validator's parser takes the whole line and every generated copy "
                        f"re-serializes what it took, so the fleet validates while the host either "
                        f"drops the component with no error anyone sees or ships the wrong string. "
                        f"Close the quote, and put nothing after it.",
                        path,
                    )
                )
                continue
            # A flow collection (`argument-hint: [a path: here]`) parses too -- badly, but it
            # PARSES, and this rule may only claim what it can prove.
            if value[0] in "[{":
                continue
            if ": " in value:
                findings.append(
                    Finding(
                        rid,
                        f"{path}: unquoted {key!r} frontmatter value contains ': ', which a "
                        f"conforming YAML parser rejects as a nested mapping key. This validator's "
                        f"own parser and every generated copy quote or re-serialize the value, so "
                        f"the whole fleet validates while a host that parses strict YAML drops the "
                        f"component without an error anyone sees. Wrap the value in double quotes.",
                        path,
                    )
                )
    return findings
