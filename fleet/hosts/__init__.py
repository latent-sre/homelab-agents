"""Host projections: what the fleet's canonical Claude prose becomes on another host.

The canonical definitions state every boundary in terms of Claude's controls — a `tools:`
allowlist, a scoped `PreToolUse` hook, a preloaded skill. Copilot/VS Code and Codex have
different controls, and some have none, so a sentence carried across unchanged states absent
authority as though it were enforced. That is the "authority is the host's own control, never
prose" rule inverted, and it is what this package exists to prevent.

- `rewrites.py` — the `Rewrite` record, the run `Ledger`, and why every rewrite declares the
  count it must land.
- `table.py` — the rewrites themselves, in the order they apply.
- `toml.py` — the Codex emitter, which parses back everything it writes.

`scripts/generate_platform_adapters.py` is the only consumer; it holds the host file layouts,
the tool-alias maps, and the safety checks on the generated trees.
"""
