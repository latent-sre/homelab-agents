#!/usr/bin/env python3
"""Run versioned cross-host conformance lanes without blending host or model results."""

from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)  # `import fleet` when run as `python3 scripts/<name>.py`

from fleet import digest as _digest  # noqa: E402
from fleet import proc as _proc  # noqa: E402

try:
    from scripts import generate_platform_adapters, stream_events
    from scripts.host_conformance_schema import (
        ConformanceError,
        validate_manifest,
    )
except ModuleNotFoundError:
    import generate_platform_adapters  # type: ignore[no-redef]
    import stream_events  # type: ignore[no-redef]
    from host_conformance_schema import (  # type: ignore[no-redef]
        ConformanceError,
        validate_manifest,
    )


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "evals" / "conformance" / "hosts.json"
VERDICTS = {"pass", "fail", "inconclusive", "skip"}


@dataclass(frozen=True)
class CommandResult:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False


@dataclass(frozen=True)
class HostResult:
    lane_id: str
    host: str
    kind: str
    verdict: str
    started_at: str
    ended_at: str
    duration_ms: int
    cli_version: str | None = None
    requested_model: str | None = None
    observed_models: list[str] = field(default_factory=list)
    reasoning_effort: str | None = None
    prompt_digest: str | None = None
    timeout_seconds: int | None = None
    exit_code: int | None = None
    transcript_digest: str | None = None
    details: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(f"unknown host verdict: {self.verdict}")


Runner = Callable[[Sequence[str], Path, int], CommandResult]
Which = Callable[[str], str | None]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run(argv: Sequence[str], cwd: Path, timeout: int) -> CommandResult:
    """The kernel runner, narrowed to this module's result shape.

    A timed-out stream used to be rendered with `str()` on the bytes `TimeoutExpired` hands
    back, so a partial transcript read as the literal text `b'...'`; the kernel decodes it.
    """
    result = _proc.run(argv, cwd=cwd, timeout=timeout)
    if result.failed_to_start:
        return CommandResult(127, "", result.error or "")
    return CommandResult(
        result.returncode, result.stdout, result.stderr, timed_out=result.timed_out
    )


def load_manifest(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConformanceError(f"cannot load conformance manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConformanceError("conformance manifest must be a JSON object")
    validate_manifest(data)
    return data


def _static_counts(root: Path, host: str) -> tuple[int, int]:
    if host == "claude":
        return (
            len(list((root / "agents").glob("*.md"))),
            len(list((root / "skills").glob("*/SKILL.md"))),
        )
    if host == "codex":
        return (
            len(list((root / generate_platform_adapters.CODEX_AGENTS).glob("*.toml"))),
            len(list((root / generate_platform_adapters.CODEX_SKILLS).glob("*/SKILL.md"))),
        )
    return (
        len(list((root / generate_platform_adapters.COPILOT_AGENTS).glob("*.agent.md"))),
        len(list((root / generate_platform_adapters.COPILOT_SKILLS).glob("*/SKILL.md"))),
    )


def _static_lane(
    root: Path,
    lane: Mapping[str, object],
    adapter_issues: Sequence[str],
) -> HostResult:
    started_at = _timestamp()
    start = time.monotonic()
    canonical_counts = _static_counts(root, "claude")
    host_counts = _static_counts(root, lane["host"])
    issues = list(adapter_issues)
    if host_counts != canonical_counts:
        issues.append(
            f"{lane['host']} inventory {host_counts} differs from canonical {canonical_counts}"
        )
    return HostResult(
        lane_id=lane["id"],
        host=lane["host"],
        kind=lane["kind"],
        verdict="fail" if issues else "pass",
        started_at=started_at,
        ended_at=_timestamp(),
        duration_ms=round((time.monotonic() - start) * 1000),
        details={
            "canonical_agents": canonical_counts[0],
            "canonical_skills": canonical_counts[1],
            "host_agents": host_counts[0],
            "host_skills": host_counts[1],
            "issues": issues,
        },
    )


def _cli_version(executable: str, root: Path, runner: Runner) -> str | None:
    result = runner((executable, "--version"), root, 30)
    if result.returncode != 0:
        return None
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else None


def _discovery_lane(
    root: Path,
    lane: Mapping[str, object],
    *,
    which: Which,
    runner: Runner,
) -> HostResult:
    started_at = _timestamp()
    start = time.monotonic()
    executable = which(lane["command"])
    if executable is None:
        return HostResult(
            lane_id=lane["id"],
            host=lane["host"],
            kind=lane["kind"],
            verdict="skip",
            started_at=started_at,
            ended_at=_timestamp(),
            duration_ms=round((time.monotonic() - start) * 1000),
            details={"reason": f"{lane['command']} is not on PATH"},
        )
    version = _cli_version(executable, root, runner)
    if version is None:
        verdict = "inconclusive"
        details: dict[str, object] = {"reason": "CLI version command failed"}
    else:
        verdict = "pass"
        details = {"executable": executable}
    if lane.get("plugin_inventory"):
        listing = runner((executable, "plugin", "list"), root, 60)
        details["plugin_inventory_read"] = listing.returncode == 0
        details["fleet_plugin_present"] = (
            listing.returncode == 0 and "sde-agents" in listing.stdout.lower()
        )
        details["plugin_inventory_digest"] = _digest.sha256_hex(
            (listing.stdout + listing.stderr).encode("utf-8")
        )
        if listing.returncode != 0:
            verdict = "inconclusive"
        elif not details["fleet_plugin_present"]:
            verdict = "inconclusive"
            details["reason"] = "CLI inventory was readable, but sde-agents is not installed"
    return HostResult(
        lane_id=lane["id"],
        host=lane["host"],
        kind=lane["kind"],
        verdict=verdict,
        started_at=started_at,
        ended_at=_timestamp(),
        duration_ms=round((time.monotonic() - start) * 1000),
        cli_version=version,
        details=details,
    )


def _behavioral_lane(root: Path, lane: Mapping[str, object], runner: Runner) -> HostResult:
    started_at = _timestamp()
    start = time.monotonic()
    timeout = lane["timeout_seconds"]
    result = runner((sys.executable, str(root / "scripts" / "probe_plugin.py")), root, timeout)
    if result.timed_out:
        verdict = "inconclusive"
    elif result.returncode == 0:
        verdict = "pass"
    elif result.returncode == 2:
        verdict = "inconclusive"
    else:
        verdict = "fail"
    transcript = result.stdout + result.stderr
    return HostResult(
        lane_id=lane["id"],
        host=lane["host"],
        kind=lane["kind"],
        verdict=verdict,
        started_at=started_at,
        ended_at=_timestamp(),
        duration_ms=round((time.monotonic() - start) * 1000),
        timeout_seconds=timeout,
        exit_code=result.returncode,
        transcript_digest=_digest.sha256_hex(transcript.encode("utf-8")),
        details={"timed_out": result.timed_out, "output_tail": transcript[-800:]},
    )


def build_codex_command(
    executable: str,
    root: Path,
    lane: Mapping[str, object],
    prompt: str,
) -> list[str]:
    return [
        executable,
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--color",
        "never",
        "--model",
        lane["model"],
        "--sandbox",
        lane["sandbox"],
        "-c",
        f'model_reasoning_effort="{lane["reasoning_effort"]}"',
        "--cd",
        str(root),
        prompt,
    ]


def _walk(value: object):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def parse_codex_jsonl(text: str) -> dict[str, object]:
    events = list(stream_events.iter_events(text))
    observed_models: set[str] = set()
    messages: list[str] = []
    usage: list[dict[str, object]] = []
    for event in events:
        for value in _walk(event):
            if isinstance(value, dict):
                model = value.get("model")
                if isinstance(model, str) and model.startswith("gpt-"):
                    observed_models.add(model)
                if value.get("type") == "agent_message" and isinstance(value.get("text"), str):
                    messages.append(value["text"])
                if "input_tokens" in value and "output_tokens" in value:
                    usage.append(dict(value))
    return {
        "events": len(events),
        "observed_models": sorted(observed_models),
        "last_message": messages[-1] if messages else None,
        "usage": usage[-1] if usage else None,
    }


def _extract_object(text: str | None) -> dict[str, object] | None:
    if not text:
        return None
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip() if len(lines) >= 3 else candidate
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def _model_lane(
    root: Path,
    lane: Mapping[str, object],
    case: Mapping[str, object],
    *,
    which: Which,
    runner: Runner,
) -> HostResult:
    started_at = _timestamp()
    start = time.monotonic()
    executable = which("codex")
    prompt = case["prompt"]
    prompt_digest = _digest.sha256_hex(prompt.encode("utf-8"))
    if executable is None:
        return HostResult(
            lane_id=lane["id"],
            host=lane["host"],
            kind=lane["kind"],
            verdict="skip",
            started_at=started_at,
            ended_at=_timestamp(),
            duration_ms=round((time.monotonic() - start) * 1000),
            requested_model=lane["model"],
            reasoning_effort=lane["reasoning_effort"],
            prompt_digest=prompt_digest,
            timeout_seconds=lane["timeout_seconds"],
            details={"reason": "codex is not on PATH"},
        )
    version = _cli_version(executable, root, runner)
    argv = build_codex_command(executable, root, lane, prompt)
    result = runner(argv, root, lane["timeout_seconds"])
    transcript = result.stdout + result.stderr
    parsed = parse_codex_jsonl(result.stdout)
    actual = _extract_object(parsed["last_message"])
    observed = parsed["observed_models"]
    if result.timed_out:
        verdict = "inconclusive"
        reason = "Codex baseline timed out"
    elif result.returncode != 0:
        unavailable_markers = ("not available", "access", "authentication", "rate limit")
        if any(marker in transcript.lower() for marker in unavailable_markers):
            verdict = "inconclusive"
            reason = "model access or authentication prevented the baseline"
        else:
            verdict = "fail"
            reason = "Codex baseline exited non-zero"
    elif observed and lane["model"] not in observed:
        verdict = "fail"
        reason = "observed model differs from requested model"
    elif actual != case["expected"]:
        verdict = "fail"
        reason = "final response did not match the deterministic case oracle"
    else:
        verdict = "pass"
        reason = "deterministic case oracle passed"
    details: dict[str, object] = {
        "case": case["id"],
        "reason": reason,
        "response": actual,
        "expected": case["expected"],
        "event_count": parsed["events"],
        "usage": parsed["usage"],
        "observed_model_exposed": bool(observed),
        "command_conditions": {
            "ephemeral": True,
            "ignore_user_config": True,
            "sandbox": lane["sandbox"],
            "optional_features_enabled": [],
            "pro_mode": False,
        },
    }
    return HostResult(
        lane_id=lane["id"],
        host=lane["host"],
        kind=lane["kind"],
        verdict=verdict,
        started_at=started_at,
        ended_at=_timestamp(),
        duration_ms=round((time.monotonic() - start) * 1000),
        cli_version=version,
        requested_model=lane["model"],
        observed_models=observed,
        reasoning_effort=lane["reasoning_effort"],
        prompt_digest=prompt_digest,
        timeout_seconds=lane["timeout_seconds"],
        exit_code=result.returncode,
        transcript_digest=_digest.sha256_hex(transcript.encode("utf-8")),
        details=details,
    )


def run_manifest(
    root: Path,
    manifest: Mapping[str, object],
    *,
    include_live: bool = False,
    include_models: bool = False,
    lane_pattern: str = "*",
    which: Which = shutil.which,
    runner: Runner = _run,
) -> dict[str, object]:
    cases = {case["id"]: case for case in manifest["cases"]}
    results: list[HostResult] = []
    adapter_issues: list[str] | None = None
    for lane in manifest["lanes"]:
        if not fnmatch.fnmatch(lane["id"], lane_pattern):
            continue
        if lane["kind"] == "static":
            if adapter_issues is None:
                adapter_issues = (
                    generate_platform_adapters.validate_platform_contracts(root)
                    + generate_platform_adapters.validate_generated_outputs(root)
                )
            result = _static_lane(root, lane, adapter_issues)
        elif lane["kind"] == "discovery":
            result = _discovery_lane(root, lane, which=which, runner=runner)
        elif lane["kind"] == "behavioral":
            if include_live:
                result = _behavioral_lane(root, lane, runner)
            else:
                now = _timestamp()
                result = HostResult(
                    lane_id=lane["id"],
                    host=lane["host"],
                    kind=lane["kind"],
                    verdict="skip",
                    started_at=now,
                    ended_at=now,
                    duration_ms=0,
                    details={"reason": "live lanes require --live"},
                )
        else:
            if include_models:
                result = _model_lane(
                    root,
                    lane,
                    cases[lane["case"]],
                    which=which,
                    runner=runner,
                )
            else:
                now = _timestamp()
                result = HostResult(
                    lane_id=lane["id"],
                    host=lane["host"],
                    kind=lane["kind"],
                    verdict="skip",
                    started_at=now,
                    ended_at=now,
                    duration_ms=0,
                    requested_model=lane["model"],
                    reasoning_effort=lane["reasoning_effort"],
                    prompt_digest=_digest.sha256_hex(cases[lane["case"]]["prompt"].encode("utf-8")),
                    timeout_seconds=lane["timeout_seconds"],
                    details={"reason": "model lanes require --models"},
                )
        results.append(result)
    counts = Counter(result.verdict for result in results)
    return {
        "schema_version": 1,
        "generated_at": _timestamp(),
        "root": str(root.resolve()),
        "manifest_digest": _digest.sha256_hex(_canonical_manifest(manifest)),
        "summary": {verdict: counts.get(verdict, 0) for verdict in sorted(VERDICTS)},
        "results": [asdict(result) for result in results],
    }


def _canonical_manifest(manifest: Mapping[str, object]) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--lane", default="*", help="glob over lane IDs")
    parser.add_argument("--live", action="store_true", help="run live behavioral lanes")
    parser.add_argument("--models", action="store_true", help="run live model-baseline lanes")
    parser.add_argument("--output", type=Path, help="write the report JSON to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        report = run_manifest(
            args.root,
            manifest,
            include_live=args.live,
            include_models=args.models,
            lane_pattern=args.lane,
        )
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8", newline="\n")
        print(rendered, end="")
    except (OSError, ConformanceError, ValueError) as exc:
        print(f"host conformance error: {exc}", file=sys.stderr)
        return 2
    return 1 if report["summary"]["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
