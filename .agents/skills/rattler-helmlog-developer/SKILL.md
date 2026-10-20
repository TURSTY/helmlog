---
name: rattler-helmlog-developer
description: Develop and maintain Rattler's HelmLog fork with historical Signal K telemetry from InfluxDB, racing analysis, replay, and safe Dockerbox workflows.
---
# Rattler HelmLog Developer

Use this skill when discussing, investigating, implementing, testing or deploying Rattler-specific HelmLog functionality. Read the relevant files in `references/` before making recommendations. GitHub code is authoritative; reference documentation is a verified snapshot, not a substitute for checking changed code.

## Project locations
- Upstream: `weaties/helmlog`; fork: `TURSTY/helmlog`.
- Development host: Dockerbox, Ubuntu 24.04; checkout `~/development/helmlog`.
- Baseline: branch `feature/influx-telemetry-source`, clean working tree at `acc3ba959f660c13c2cb03fdc20f5221efdeef2d` (confirmed by user 2026-10-20). Verify current branch and HEAD before work.
- OpenPlotter/Signal K feeds InfluxDB 2, bucket `RattlerBucket`. Keep source data read-only.
- Development web application was on port 3002; isolated test InfluxDB on 18086. Verify current configuration.
- Skill source belongs in this fork and should be usable with ChatGPT and Codex across machines. Repository storage does not automatically install it in either assistant.

## Scope
This skill is a reusable **development guide**, not an instruction to implement the roadmap immediately. For a skill-maintenance request, update documentation and package only; do not start feature development without a separate request.

## Required workflow
1. Identify the requested feature and consult architecture, data contracts, and decisions.
2. Inspect relevant current fork code and upstream changes; never invent file paths, APIs or measurement availability.
3. Verify telemetry measurement, field, source, vessel context, timestamps, and units against historical data before implementing a new mapping.
4. Propose a small implementation and verification plan. Preserve upstream compatibility by keeping extensions modular.
5. Use pragmatic automated tests and targeted manual replay checks. Do not call a feature complete until tested or explicitly mark it unverified.
6. Diagnose the relevant cache layer (browser assets, running Python process, HelmLog T1/T2 cache, test fixtures, deployment image); restart/invalidate appropriately and verify new code is serving. Never clear all caches reflexively.
7. Ask user approval BEFORE commit, push, merge or production deployment. No destructive database operations without explicit approval.
8. After meaningful milestones update references, decision log, current commit baseline, tests, and roadmap; do not commit those updates without approval.

## Architecture and quality rules
- Historical telemetry: InfluxDB; HelmLog session metadata and annotations: SQLite.
- Support retrospective selection of any time range available under InfluxDB retention.
- Prefer a configured source per measurement, with explicitly defined fallback and provenance.
- Preserve Signal K native SI values at the database boundary; convert once into verified HelmLog contracts at adapter boundary. Calculations must have documented units.
- Preserve raw telemetry; quality filtering must be auditable. Filter impossible GPS jumps for analytical tracks without corrupting raw history. Avoid smoothing away real wind shifts.
- Long-term polars use explicitly classified RACE sessions only, and only qualifying samples. Maintain fastest credible and representative statistical polars separately. Factory Beneteau 523 polar may seed unobserved bins, always labeled as factory. Race-specific polars are generated on request.
- Fleet comparisons require only external boats' GPS track, SOG and COG; no full external boat manoeuvre analysis.
- Start analysis is a future goal: line geometry, start time, distance to line, crossing time, speed, and tactical approach; don't assume Vulcan start-line pings are historically available.
- Keep secrets out of code, commits, skill files, logs and examples.

## Reference freshness
The baseline is a snapshot, not a claim that every code path was audited. When the current commit differs, verify only the relevant contracts. Distinguish **verified code**, **user-approved requirements**, and **proposed designs**. Known gaps and code issues are not authorization to fix them.

## Read first
- `references/decisions.md`: binding product and engineering decisions.
- `references/data-contracts.md`: verified interface observations and open questions.
- `references/roadmap.md`: priorities and known technical debt.
- `references/development.md`: safe work and cache verification.
- `references/code-audit.md`: source-backed implementation findings, caveats and outstanding checks (read before extending replay or current calculations).
