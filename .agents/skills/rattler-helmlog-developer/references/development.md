# Development and safety workflow
- GitHub is authoritative for shared skill and code; do not assume ChatGPT or Codex auto-load a GitHub-hosted skill. Document per-client setup after confirming available features.
- Verify `git status`, branch, commit, upstream divergence before editing. Do not overwrite local changes.
- Dockerbox development checkout: `~/development/helmlog`; development web port 3002 and test InfluxDB 18086 are historical observations, not permanent guarantees.
- Protect production OpenPlotter InfluxDB from writes. Keep environment credentials outside Git.
- Preserve root AGENTS.md worktree, TDD, PR, risk-tier and other development requirements except the explicit Rattler overrides. All four checks (pytest, Ruff check, Ruff format check, mypy) must pass before a PR.
- Cache checklist: confirm changed source file, process/container running version, Python restart needed, T1 invalidation, T2 SQLite cached replay, browser hard refresh/static assets, API response freshness. Record exact remedy per change. Avoid destructive cache clearing.
- Require explicit user approval BEFORE every `git commit`, `git push`, merge, or production deployment; do not follow conflicting automatic commit/push instructions. Prepare diffs and report tests first.
- On milestones, refresh verified code references, SHA, architecture and decisions.

## Validation budget

- Classify risk by behavior and affected modules, not diff size. Preserve
  upstream TDD, critical/high-risk and mandatory integration-test requirements.
- Small, isolated changes: targeted tests, relevant static checks and one
  practical verification. Documentation-only iterations need documentation
  checks, not application tests. Wider architectural changes need broader
  integration tests; major milestones need the full repository suite.
- The upstream pre-PR gate remains mandatory: all four checks must pass.
  Targeted iteration checks do not replace it. Approval to defer an expensive
  check leaves the gate unmet; it does not waive the requirement.
- Before expensive validation (full suites, broad coverage, costly integration
  or replay checks, or repository-wide baseline comparisons), report commands,
  scope, expected cost and reusable evidence, then request explicit approval.
  Default to one approved full-suite run; retries or alternative full-suite
  runs require further approval.
- Reuse completed results when relevant code, dependencies and configuration
  are unchanged. After changes, rerun affected checks only unless evidence
  warrants broader validation. TDD red/green runs remain necessary.
- Stop and report unrelated baseline failures instead of repeatedly debugging
  them. Reuse known baseline evidence; use at most one focused reproduction
  when needed to establish whether a failure predates the change. Do not
  launch a repository-wide baseline comparison automatically or claim a
  failing check passed.
- Keep investigations concise, batch independent reads and tool calls, and
  avoid unrelated audits or changes. Record commands and outcomes once so
  later review, commits and integration can reuse the evidence.
