# Development and safety workflow
- GitHub is authoritative for shared skill and code; do not assume ChatGPT or Codex auto-load a GitHub-hosted skill. Document per-client setup after confirming available features.
- Verify `git status`, branch, commit, upstream divergence before editing. Do not overwrite local changes.
- Dockerbox development checkout: `~/development/helmlog`; development web port 3002 and test InfluxDB 18086 are historical observations, not permanent guarantees.
- Protect production OpenPlotter InfluxDB from writes. Keep environment credentials outside Git.
- Tests: targeted pytest for adapters, conversions, quality filters, source selection; end-to-end replay for timeline/graphs. Use Ruff/mypy where relevant.
- Cache checklist: confirm changed source file, process/container running version, Python restart needed, T1 invalidation, T2 SQLite cached replay, browser hard refresh/static assets, API response freshness. Record exact remedy per change. Avoid destructive cache clearing.
- Require user approval before `git commit`, `git push`, merge, or production deployment. Prepare diffs and report tests first.
- On milestones, refresh verified code references, SHA, architecture and decisions.
