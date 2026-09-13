"""Generated host adapters must be byte-current with the canonical fleet."""

from __future__ import annotations

from pathlib import Path

from fleet import modules
from fleet.findings import Finding
from fleet.rules import rule
from fleet.snapshot import Fleet


def load_platform_adapter_generator(root: Path):
    """Load the adapter generator shipped by the tree under validation (authority comes from the
    checkout being validated, never the executing one)."""
    source = Path(root) / "scripts" / "generate_platform_adapters.py"
    module = modules.load_module_by_content(source, "platform_adapters")
    if module is None:
        raise ImportError(f"cannot load {source}")
    return module


@rule(
    "adapters.generated",
    group="adapters",
    why="Without the generator, or with stale bytes, the Copilot, VS Code, and Codex copies drift "
    "from the canonical definitions while the canonical fleet stays green.",
)
def generated_adapters(fleet: Fleet) -> list[Finding]:
    if not fleet.ships_as_plugin:
        return []
    source = fleet.root / "scripts" / "generate_platform_adapters.py"
    if not source.is_file():
        return [
            Finding(
                "adapters.generated",
                f"{source}: missing platform adapter generator. The Copilot, VS Code, and Codex "
                f"copies would have no mechanical link to the canonical Claude definitions.",
                source,
            )
        ]
    try:
        module = load_platform_adapter_generator(fleet.root)
        issues = module.validate_platform_support(fleet.root)
    except Exception as exc:
        return [
            Finding(
                "adapters.generated",
                f"{source}: platform adapter validation crashed: {exc}. A broken checker must fail "
                f"loudly rather than certifying stale host copies.",
                source,
            )
        ]
    # Each issue names the generated or canonical file it is about; attribute it there.
    return [Finding.from_text("adapters.generated", issue) for issue in issues]
