# Proportional controls for one homelab operator

Status: accepted by the operator's 2026-09-12 request to review and fix items 1–8. Source changes;
no installed profile, plugin cache, host permission setting, release, or live lab change is implied.

The owning definitions now distinguish ordinary authorized work from effects needing additional
authority or isolation:

- `agents/verification-engineer.md` permits ordinary authorized checks of the user's established
  workspace through actual host controls. Unfamiliar executable inputs and effects beyond scope
  still need adequate isolation or remain inconclusive. Repository and tool-output instructions
  are data, not authorization. Product edits remain outside the independent verifier's remit.
- A complete frozen snapshot with independently checked content identity is a verification target
  alongside a source commit. Capture scope includes relevant untracked inputs, modes and links;
  exclusions and output/test differences remain explicit. This does not turn a snapshot into a
  formally approved commit or make endpoint hashing proof against transient writes.
- `scripts/live-effect-gate.py` defaults to host permission flow. The operator can retain the
  former interposition with `SDE_AGENTS_LIVE_EFFECT_POLICY=prompt` in the launch environment.
  Invalid values fail closed for the scoped agent. Agents cannot change policy to authorize
  themselves. This replaces mandatory plugin interposition in the earlier live-effect decisions;
  host controls, the read-only guard, and the opt-in filter's roster remain intact.
- Service criticality follows stated impact and downtime tolerance. Suspicion permits bounded
  read-only provenance checks; corroborated compromise requires evidence preservation and a
  security handoff. Recovery is distinct from cause determination. Drift repair changes only the
  incorrect side after intended state is established.
- Reviewer guidance follows the isolated-hook dependency constraint and distinguishes inert
  attack fixtures from a reachable trust failure. PR review defaults to one independent pass,
  with a second for authority/security changes, broad refactors, or unresolved disagreement.
  Material final deltas receive focused review. The amended review decision records the broad
  review bounds and preserves historical evidence.

The simpler alternative for the live hook was deleting it. Retaining the existing filter behind
one launch setting preserves the previous operator choice and its tests without adding a command
approval store or a second authority broker. `host` returns no decision, never `allow`, so the
normal host permission flow still applies. This follows the
[official hook contract](https://code.claude.com/docs/en/hooks-guide), checked through Context7 on
2026-09-12. Upstream repository examples describe hook output but do not prove the installed CLI's
behavior; the native probe supplies separate evidence.

Adoption changes default Claude live-command prompting. An operator wanting the former behavior
must select `prompt` before adopting the new source. No installation is performed by this change.
Rollback restores the canonical definitions, hook, tests, and generated adapters together;
it does not undo lab effects or amend previously captured verification evidence.

Reopen on an unauthorized effect, lost recovery/evidence boundary, misidentified verification
target, repeated unnecessary confirmation, or a focused correction loop that fails to converge.

[Verification evidence](../archive/2026-09/proportional-controls-evidence-2026-09-12.md) records
offline tests, final scenario decisions, independent review, and the native probe's expired-OAuth
block. Native behavior remains unverified until that probe can execute.
