"""Skill definition rules: frontmatter namespace, identity, bundle links in both directions."""

from __future__ import annotations

import re
from pathlib import Path

from fleet.findings import Finding
from fleet.policy import POLICY
from fleet.rules import rule
from fleet.rules.agents import description_findings, name_findings
from fleet.snapshot import Definition, Fleet

# The optional `./` is load-bearing. Without it the lookbehind rejected any link written
# `./references/foo.md`, so such a link matched nothing: the existence check never ran (a broken
# path shipped silently) and the orphan check counted the target as unlinked. The dot remains in
# the leading boundary: without it matching restarts inside `../references` or `foo.references`.
BUNDLE_REF_RE = re.compile(
    r"(?<![\w./])(?:\./)?(?:references|assets|scripts)/[A-Za-z0-9._/-]*[A-Za-z0-9_-]"
)

GROUP = "skills"


def bundle_references(text: str) -> set[str]:
    """Every bundle path named in a SKILL.md, normalized so `./references/x.md` and
    `references/x.md` are the same reference. Both direction checks read this."""
    return {
        match.group(0).rstrip(".,;:)]}").removeprefix("./")
        for match in BUNDLE_REF_RE.finditer(text)
    }


@rule("skills.directory", group=GROUP, why="A repository with no skills/ ships nothing.")
def skills_directory(fleet: Fleet) -> list[Finding]:
    if fleet.skills_dir_exists:
        return []
    path = fleet.root / "skills"
    return [Finding("skills.directory", f"{path}: missing skills directory", path)]


@rule(
    "skill.frontmatter",
    group=GROUP,
    why="A skill directory without a readable SKILL.md is a component that looks shipped.",
)
def skill_frontmatter(fleet: Fleet) -> list[Finding]:
    if not fleet.skills_dir_exists:
        return []
    findings = [
        Finding("skill.frontmatter", f"{d}: missing SKILL.md", d)
        for d in fleet.skill_dirs_without_skill_md
    ]
    findings += [
        Finding("skill.frontmatter", f"{s.path}: missing or malformed frontmatter", s.path)
        for s in fleet.skills
        if s.fields is None
    ]
    # Legacy order: per directory, so a missing SKILL.md sorts with its siblings.
    return sorted(findings, key=lambda f: str(f.path))


@rule(
    "skill.frontmatter.keys",
    group=GROUP,
    why="A misspelled key silently drops what it configured, e.g. a side-effect skill left "
    "model-invocable.",
)
def skill_frontmatter_keys(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    for skill in fleet.parsed_skills:
        for key in skill.fields or {}:
            if key not in POLICY.known_skill_fields:
                findings.append(
                    Finding(
                        "skill.frontmatter.keys",
                        f"{skill.path}: unknown frontmatter key {key!r} is not a Claude Code "
                        f"skill field. "
                        f"An unrecognized key is not guaranteed to fail loudly, so a typo "
                        f"silently drops "
                        f"what it configured (e.g. 'disable-model-invocaton' would leave a "
                        f"side-effect "
                        f"skill model-invocable).",
                        skill.path,
                    )
                )
    return findings


@rule(
    "skill.identity",
    group=GROUP,
    why="The name is the invocation key; it must match its directory.",
)
def skill_identity(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    for skill in fleet.parsed_skills:
        name = skill.field("name")
        findings.extend(name_findings(name, "skill", skill, "skill.identity"))
        if name and name != skill.directory.name:
            findings.append(
                Finding(
                    "skill.identity",
                    f"{skill.path}: skill name {name!r} must match directory "
                    f"{skill.directory.name!r}",
                    skill.path,
                )
            )
        findings.extend(description_findings(skill, "skill", "skill.identity"))
    return findings


def _bundle_link_findings(fleet: Fleet, skill: Definition) -> list[Finding]:
    findings: list[Finding] = []
    for reference in sorted(bundle_references(skill.text or "")):
        local_target = skill.directory / Path(reference)
        shared_target = fleet.root / Path(reference)
        if not local_target.exists() and not shared_target.exists():
            findings.append(
                Finding(
                    "skill.bundle.links",
                    f"{skill.path}: referenced file does not exist: {reference}",
                    skill.path,
                )
            )
    return findings


def _orphan_findings(skill: Definition) -> list[Finding]:
    """The other direction: every file under references/ must be named by a link in SKILL.md.
    A references/*.md file with no routing-table row is dead knowledge that looks shipped."""
    findings: list[Finding] = []
    references_dir = skill.directory / "references"
    if not references_dir.is_dir():
        return findings
    linked = bundle_references(skill.text or "")
    for ref_file in sorted(references_dir.rglob("*")):
        if not ref_file.is_file():
            continue
        rel = ref_file.relative_to(skill.directory).as_posix()
        if rel not in linked:
            findings.append(
                Finding(
                    "skill.bundle.orphans",
                    f"{ref_file}: orphaned -- no skill-relative link to {rel!r} found in "
                    f"{skill.path}; a "
                    f"reference file with no routing-table row is unreachable by any means. "
                    f"Routing-table "
                    f"links must be written skill-relative (e.g. {rel!r}) -- a full path such as "
                    f"'{skill.directory.name}/{rel}' will not be recognized by this check",
                    ref_file,
                )
            )
    return findings


@rule(
    "skill.bundle",
    group=GROUP,
    why="A link to a missing bundle file ships silently; an unlinked references/ file is "
    "unreachable knowledge that looks shipped.",
)
def skill_bundle(fleet: Fleet) -> list[Finding]:
    findings: list[Finding] = []
    for skill in fleet.parsed_skills:
        findings.extend(_bundle_link_findings(fleet, skill))
        findings.extend(_orphan_findings(skill))
    return findings


@rule("skills.roster", group=GROUP, why="No skills, or two with one name, ships a broken fleet.")
def skills_roster(fleet: Fleet) -> list[Finding]:
    if not fleet.skills_dir_exists:
        return []
    skills_dir = fleet.root / "skills"
    names = [s.name for s in fleet.parsed_skills]
    findings: list[Finding] = []
    if not names:
        findings.append(
            Finding("skills.roster", f"{skills_dir}: no skill definitions found", skills_dir)
        )
    if len(names) != len(set(names)):
        findings.append(
            Finding("skills.roster", f"{skills_dir}: duplicate skill names", skills_dir)
        )
    return findings
