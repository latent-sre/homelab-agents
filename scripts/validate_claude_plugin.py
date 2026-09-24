#!/usr/bin/env python3
"""Validate both the Claude marketplace and canonical plugin contents, offline.

Run after validate_fleet.py. A directory containing marketplace.json selects marketplace
validation, which does not inspect agents, skills, or hooks. Validate that manifest explicitly,
then validate the plugin manifest in a temporary copy of the canonical runtime components.
The copy excludes the repository's development-only CLAUDE.md/AGENTS.md bridge and marketplace;
it preserves component bytes, including malformed input, rather than suppressing CLI warnings.
This is a validation view, not a new distribution or an execution sandbox.

Requires an installed Claude CLI; never installs it or starts a model. Exit 0 means both checks
passed, 1 means validation failed, and 2 means a check could not complete. Temporary files are
cleaned up and the checkout is not changed. CLI upgrades still owe the native plugin probe.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def validate(root: Path, claude: str, *, run=None) -> int:
    run = subprocess.run if run is None else run
    marketplace = run(
        [claude, "plugin", "validate", str(root / ".claude-plugin/marketplace.json"), "--strict"],
        check=False, timeout=60,
    )
    with tempfile.TemporaryDirectory(prefix="sde-plugin-validation-") as temporary:
        stage = Path(temporary)
        (stage / ".claude-plugin").mkdir()
        shutil.copy2(root / ".claude-plugin/plugin.json", stage / ".claude-plugin/plugin.json")
        # Include auto-discovered components and runtime dependencies; never copy a generated
        # host adapter or the repository's development context in place of canonical content.
        for name in ("agents", "skills", "commands", "hooks", "scripts", "workflows"):
            source = root / name
            if source.exists():
                shutil.copytree(source, stage / name, symlinks=True)
        for name in (".mcp.json", ".lsp.json"):
            source = root / name
            if source.exists():
                shutil.copy2(source, stage / name)
        plugin = run(
            [claude, "plugin", "validate", str(stage / ".claude-plugin/plugin.json"), "--strict"],
            check=False, timeout=60,
        )
    codes = (marketplace.returncode, plugin.returncode)
    # Preserve an observed validation failure even when the sibling check was not computed.
    if 1 in codes:
        return 1
    return 2 if any(code != 0 for code in codes) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    claude = shutil.which("claude")
    if claude is None:
        print("claude CLI not found; platform validation was not computed", file=sys.stderr)
        return 2
    try:
        return validate(args.root.resolve(), claude)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"platform validation could not complete: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
