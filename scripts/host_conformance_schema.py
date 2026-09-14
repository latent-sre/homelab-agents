#!/usr/bin/env python3
"""Pure host-conformance manifest schema shared by validation and execution."""

from __future__ import annotations

from collections.abc import Mapping

HOSTS = {"claude", "codex", "vscode"}
KINDS = {"static", "discovery", "behavioral", "model-baseline"}
REASONING_EFFORTS = {"none", "low", "medium", "high", "xhigh", "max"}


class ConformanceError(ValueError):
    pass


def validate_manifest(data: Mapping[str, object]) -> None:
    if set(data) != {"schema_version", "description", "model_guidance", "cases", "lanes"}:
        raise ConformanceError("conformance manifest has missing or unknown top-level fields")
    if data["schema_version"] != 1:
        raise ConformanceError("unsupported conformance schema version")
    if not isinstance(data["description"], str) or not data["description"].strip():
        raise ConformanceError("conformance description must be non-empty")
    if not isinstance(data["model_guidance"], str) or not data["model_guidance"].startswith(
        "https://developers.openai.com/"
    ):
        raise ConformanceError("model_guidance must cite the official OpenAI developer docs")
    if not isinstance(data["cases"], list) or not isinstance(data["lanes"], list):
        raise ConformanceError("cases and lanes must be arrays")

    cases: dict[str, Mapping[str, object]] = {}
    for case in data["cases"]:
        if not isinstance(case, dict) or set(case) != {"id", "prompt", "expected"}:
            raise ConformanceError("each conformance case must contain id, prompt, and expected")
        if not isinstance(case["id"], str) or case["id"] in cases:
            raise ConformanceError("conformance case IDs must be unique strings")
        if not isinstance(case["prompt"], str) or not case["prompt"].strip():
            raise ConformanceError("conformance case prompt must be non-empty")
        if not isinstance(case["expected"], dict):
            raise ConformanceError("conformance case expected value must be an object")
        cases[case["id"]] = case

    lane_ids: set[str] = set()
    sol_lanes = 0
    for lane in data["lanes"]:
        if not isinstance(lane, dict):
            raise ConformanceError("each conformance lane must be an object")
        required = {"id", "host", "kind", "required"}
        if not required <= set(lane):
            raise ConformanceError("conformance lane is missing id, host, kind, or required")
        if lane["id"] in lane_ids or not isinstance(lane["id"], str):
            raise ConformanceError("conformance lane IDs must be unique strings")
        lane_ids.add(lane["id"])
        if lane["host"] not in HOSTS or lane["kind"] not in KINDS:
            raise ConformanceError(f"invalid host or kind in lane {lane['id']!r}")
        if not isinstance(lane["required"], bool):
            raise ConformanceError("lane required must be boolean")
        if lane["kind"] == "model-baseline":
            expected_fields = {
                "id",
                "host",
                "kind",
                "model",
                "reasoning_effort",
                "sandbox",
                "case",
                "timeout_seconds",
                "required",
            }
            if set(lane) != expected_fields:
                raise ConformanceError(
                    f"model baseline lane {lane['id']!r} has missing or unknown fields"
                )
            if lane["host"] != "codex":
                raise ConformanceError(
                    "model baseline lanes currently require the Codex JSON driver"
                )
            if lane["case"] not in cases:
                raise ConformanceError(f"lane {lane['id']!r} references an unknown case")
            if lane["reasoning_effort"] not in REASONING_EFFORTS:
                raise ConformanceError(f"lane {lane['id']!r} has invalid reasoning effort")
            if lane["sandbox"] != "read-only":
                raise ConformanceError("model baselines must use the read-only sandbox")
            if lane["model"] == "gpt-5.6-sol":
                sol_lanes += 1
                if lane["reasoning_effort"] != "high":
                    raise ConformanceError(
                        "gpt-5.6-sol baseline must preserve the fleet's explicit high effort"
                    )
    if sol_lanes != 1:
        raise ConformanceError("manifest must contain exactly one explicit gpt-5.6-sol lane")
