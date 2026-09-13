"""Repository coverage policy for the cross-host conformance manifest."""

from __future__ import annotations

import json

from fleet import modules
from fleet.findings import Finding
from fleet.policy import POLICY
from fleet.rules import rule
from fleet.snapshot import Fleet


@rule(
    "conformance.manifest",
    group="conformance",
    why="Without one authoritative schema, malformed lanes can silently disappear from the "
    "cross-host baseline; a missing host or an optional required baseline changes what was "
    "measured without saying so.",
)
def host_conformance_manifest(fleet: Fleet) -> list[Finding]:
    if not fleet.ships_as_plugin:
        return []
    root = fleet.root
    path = root / "evals" / "conformance" / "hosts.json"
    schema = root / "scripts" / "host_conformance_schema.py"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        module = modules.load_module_by_content(schema, "host_conformance_schema")
        if module is None:
            raise ImportError(f"cannot load {schema}")
        module.validate_manifest(document)
    except Exception as exc:
        return [
            Finding(
                "conformance.manifest",
                f"{path}: host conformance manifest is missing, unreadable, or invalid ({exc}). "
                f"Without one authoritative schema, malformed lanes can silently disappear from "
                f"the "
                f"cross-host baseline.",
                path,
            )
        ]
    lanes = document["lanes"]
    findings: list[Finding] = []
    static_hosts = {
        lane.get("host")
        for lane in lanes
        if isinstance(lane, dict) and lane.get("kind") == "static"
    }
    missing_hosts = sorted(POLICY.conformance_required_hosts - static_hosts)
    if missing_hosts:
        findings.append(
            Finding(
                "conformance.manifest",
                f"{path}: static conformance lanes are missing hosts {missing_hosts}. A generated "
                f"host "
                f"surface could drift while the cross-host report still looks complete.",
                path,
            )
        )
    baseline = POLICY.conformance_required_baseline_model
    # The schema guarantees exactly one such lane; `next` with a default keeps a schema change
    # from turning this rule into an uncaught StopIteration.
    sol_lane = next(
        (
            lane
            for lane in lanes
            if isinstance(lane, dict)
            and lane.get("kind") == "model-baseline"
            and lane.get("model") == baseline
        ),
        None,
    )
    if sol_lane is None or not sol_lane.get("required"):
        findings.append(
            Finding(
                "conformance.manifest",
                f"{path}: {baseline} baseline is not required. The operator selected Sol as a "
                f"separately reported baseline; making it optional silently changes what was "
                f"measured.",
                path,
            )
        )
    return findings
