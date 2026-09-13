"""Schema integrity for evals/routing/*.json -- the rules that keep the scorer honest."""

from __future__ import annotations

import json
from pathlib import Path

from fleet.findings import Finding
from fleet.rules import rule
from fleet.snapshot import Fleet


def _routing_issues(
    root: Path, agent_names: list[str], skill_names: list[str]
) -> list[tuple[str, Path]]:
    """Schema integrity for evals/routing/*.json — the rules that keep the scorer honest.

    Every rule here is a tripwire for a measurement that would silently lie. The scorer grades a
    positive against its own expect_fires but reports the CLUSTER's fire rate, so a positive
    naming a component outside the declared members can pass while the reported rate reads zero
    (observed live in pos-ci-actions-harden, which accepted code-reviewer). Both target lists
    match components BY NAME, so a typo'd member or target expects or forbids nothing and passes
    vacuously. A misspelled polarity used to fall through to the negative branch, and an empty
    explicit forbidden set therefore passed every run. Case ids are also the keys a before/after
    diff aligns on, so a duplicate makes two measurements read as one.
    """
    issues: list[tuple[str, Path]] = []
    routing = root / "evals" / "routing"
    if not routing.is_dir():
        return issues
    components = set(agent_names) | set(skill_names)
    for path in sorted(routing.glob("*.json")):
        rel = path.relative_to(root).as_posix()
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            issues.append(
                (
                    f"{rel}: unreadable cluster file ({exc}) — the runner would fail loudly, but a "
                    f"cluster nobody can run measures nothing while still looking like coverage.",
                    path,
                )
            )
            continue
        if not isinstance(doc, dict):
            issues.append(
                (
                    f"{rel}: top-level JSON value is not an object — the runner needs named "
                    f"cluster, "
                    f"members, and cases fields, so this file cannot describe a measurement.",
                    path,
                )
            )
            continue
        cluster = doc.get("cluster")
        if not isinstance(cluster, str) or not cluster.strip():
            issues.append(
                (
                    f"{rel}: missing non-empty 'cluster' string — benchmark artifacts need a "
                    f"stable "
                    f"cluster identity or results cannot be aligned.",
                    path,
                )
            )
        members = doc.get("members")
        if not isinstance(members, list) or not members:
            issues.append(
                (
                    f"{rel}: no non-empty 'members' list — every routing assertion grades against "
                    f"the "
                    f"member set, so without one the file asserts nothing.",
                    path,
                )
            )
            continue
        member_set: set[str] = set()
        for index, member in enumerate(members, start=1):
            if not isinstance(member, str) or not member.strip():
                issues.append(
                    (
                        f"{rel}: member #{index} is not a non-empty component name — target "
                        f"matching "
                        f"is string-based, so a malformed member can never fire.",
                        path,
                    )
                )
                continue
            member_set.add(member)
            if member not in components:
                issues.append(
                    (
                        f"{rel}: member {member!r} is not a fleet component — a name that "
                        f"resolves to "
                        f"nothing can be expected or forbidden and never match, passing vacuously.",
                        path,
                    )
                )

        cases = doc.get("cases")
        if not isinstance(cases, list) or not cases:
            issues.append(
                (
                    f"{rel}: no non-empty 'cases' list — a cluster without runnable assertions can "
                    f"look like coverage while measuring nothing.",
                    path,
                )
            )
            continue
        seen_ids: set[str] = set()
        for index, case in enumerate(cases, start=1):
            if not isinstance(case, dict):
                issues.append(
                    (
                        f"{rel}: case #{index} is not an object — the runner cannot read its "
                        f"identity, "
                        f"prompt, polarity, or expectations.",
                        path,
                    )
                )
                continue
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id.strip():
                issues.append(
                    (
                        f"{rel}: case #{index} has no non-empty 'id' — results without a stable "
                        f"key "
                        f"cannot be aligned across benchmark runs.",
                        path,
                    )
                )
                case_label = f"#{index}"
            else:
                case_label = repr(case_id)
                if case_id in seen_ids:
                    issues.append(
                        (
                            f"{rel}: duplicate case id {case_id!r} — ids are what a before/after "
                            f"diff "
                            f"aligns on, so a duplicate makes two measurements read as one.",
                            path,
                        )
                    )
                seen_ids.add(case_id)

            prompt = case.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                issues.append(
                    (
                        f"{rel}: case {case_label} has no non-empty 'prompt' — a case with no "
                        f"runnable "
                        f"input cannot produce routing evidence.",
                        path,
                    )
                )

            polarity = case.get("polarity")
            if polarity not in ("positive", "negative"):
                issues.append(
                    (
                        f"{rel}: case {case_label} polarity must be exactly positive or negative "
                        f"(got {polarity!r}) — any other value used to fall through as a negative "
                        f"and "
                        f"could pass without testing the intended route.",
                        path,
                    )
                )
                continue

            if polarity == "positive":
                field = "expect_fires"
            elif "expect_not_fires" in case:
                field = "expect_not_fires"
            else:
                # Omission deliberately means the whole cluster; only an explicitly empty list is
                # invalid because it overrides that useful default with a vacuous prohibition.
                continue

            targets = case.get(field)
            if not isinstance(targets, list) or not targets:
                issues.append(
                    (
                        f"{rel}: case {case_label} {field} must be a non-empty list — an empty or "
                        f"wrongly typed target set can make the assertion vacuous.",
                        path,
                    )
                )
                continue
            for target in targets:
                if not isinstance(target, str) or not target.strip():
                    issues.append(
                        (
                            f"{rel}: case {case_label} {field} contains {target!r}, not a "
                            f"non-empty "
                            f"component name — malformed targets can never match a firing.",
                            path,
                        )
                    )
                    continue
                if target not in member_set:
                    if field == "expect_fires":
                        issues.append(
                            (
                                f"{rel}: case {case_label} expects {target!r}, outside the "
                                f"cluster's "
                                f"members — the scorer would pass the case on a fire the cluster "
                                f"rate "
                                f"does not count, so the case can pass while the reported rate "
                                f"reads zero.",
                                path,
                            )
                        )
                    else:
                        issues.append(
                            (
                                f"{rel}: case {case_label} forbids {target!r}, outside the "
                                f"cluster's "
                                f"members — a non-member can never fire as this cluster, so the "
                                f"prohibition matches nothing and the negative passes vacuously.",
                                path,
                            )
                        )
    return issues


@rule(
    "routing.cluster",
    group="routing",
    why="A cluster file that names a non-member, a duplicate id, an empty target set, or a "
    "misspelled polarity measures nothing while still looking like coverage.",
)
def routing_clusters(fleet: Fleet) -> list[Finding]:
    return [
        Finding("routing.cluster", text, path)
        for text, path in _routing_issues(fleet.root, fleet.agent_names, fleet.skill_names)
    ]
