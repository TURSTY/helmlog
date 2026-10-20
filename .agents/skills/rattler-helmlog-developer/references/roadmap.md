# Roadmap
## Existing
- InfluxDB historical replay for positions, COG/SOG, heading, apparent and true wind (reported implemented; verify end-to-end on current branch).
- SQLite-backed application/session metadata and historical session synthesis path (verify specifics).
## Immediate
1. First skill-driven implementation test (implemented locally, awaiting review; see [verification](../../../../docs/historical-stw.md)): historical STW (`navigation.speedThroughWater`). Verify field, source, vessel context, historical coverage and SI-to-HelmLog unit conversion before implementing; validate the adapter and replay contracts with tests.
2. Historical heel/trim are implemented locally, awaiting review; see [verification](../../../../docs/historical-attitude.md). Validate physical orientation and leeway calibration before allowing InfluxDB heel to affect current; then proceed with historical current analysis using existing calculations.
3. Enforce race-only polar eligibility (the audited builder selects all completed sessions); integrate historical InfluxDB telemetry into analysis rather than only the track route.

## Technical debt and verification
- Review duplicate `winds()` / `_winds_sync()` methods and tests as a separate cleanup task, not the first planned implementation test. Confirm the finding against actual HEAD before changing code.
- Audit complete backend-to-frontend telemetry contracts and external InfluxDB cache invalidation as part of relevant implementation verification.

## Later
- Long-term best and representative race-only polars; factory seeding with provenance.
- On-demand race polars, manoeuvres, comparative race analysis.
- External boat track/SOG/COG overlays.
- Start-line timing, speed and position analysis with manually supplied endpoints/time until Vulcan logging is verified.
