<!-- Environment card + mission block — instantiate into the target repo's CLAUDE.md at Phase 0.
     Every slot: fill it, or write "none — <why>". A blank slot reads as forgotten, not as empty.
     Builders, reviewers, and future maintenance sessions parse this back out — keep values exact
     (real paths, real commands), never prose descriptions of values. -->

## Environment card

- **Toolchain**: <!-- required: language/runtime + version, package manager, path if non-standard -->
- **Run**: <!-- required: the exact command that starts the tool locally -->
- **Test**: <!-- required: the exact command that runs the tests -->
- **Ports**: <!-- required: every port the tool binds, and what owns each -->
- **Module identity**: <!-- required: module/package name from `git remote -v` + manifests, never inferred -->
- **Credentials**: <!-- required: where secrets live (env file path, store) — never the values -->
- **Verification boundary**: <!-- before executable verification: owner, availability, enforced
     credential/network/filesystem controls, permitted effects, runtime/image digest if applicable,
     writable scratch and retained evidence paths; unavailable means affected criteria inconclusive -->
- **Evidence/state contract**: <!-- existing provider's schema, validator and transition authority,
     or "none — use the explicit verification packet and plan"; do not invent fleet machinery -->
- **Progress**: <!-- required: where builders append phase markers — one writer per file. Solo
     builder: .agents/PROGRESS.md. Parallel batch: each builder appends only to its own shard,
     .agents/progress/<component>.md. The orchestrator's plan file (default .agents/plan.md) is
     separate and orchestrator-owned — builders never write it. -->

## Mission block

- **Purpose**: <!-- required: what this tool is for, one sentence -->
- **Mission transaction**: <!-- required: the one real-world exchange that proves the tool does its
     job, stated verbatim and executably (exact request → expected observable result). Boot,
     build-clean, and container-healthy are table stakes, never this. -->
- **Threat model**: <!-- required: what a P0 means here — what must never happen -->
- **Pipeline visibility**: <!-- required: what the verification pipeline can and cannot see
     (e.g. "can curl the API; cannot reach the real NAS") — reviewers weigh evidence against this -->
