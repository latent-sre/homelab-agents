---
name: routes-to-homelab-engineer
description: Pilot for MACH-001 phase 4. Prompt copied verbatim from evals/routing/investigation.json case pos-diagnose-idle-lab-failure, the one investigation-cluster positive that spawned an agent in every stored headless run (homelab-platform, now homelab-engineer, 6/6 across the 2026-08-18 captures).
tags: [native-pilot, investigation]
expected_outcome: The session delegates to the homelab-engineer agent through the Agent tool with a plugin-namespaced subagent_type, and never spawns code-reviewer, a cluster sibling that judges diffs rather than failures.
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

Monitoring found an unused Jellyfin test container stopped, but nobody is affected. Do not restart it yet; figure out why it exited.
