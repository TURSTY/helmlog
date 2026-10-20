# Roadmap
## Existing
- InfluxDB historical replay for positions, COG/SOG, heading, apparent and true wind (reported implemented; verify end-to-end on current branch).
- SQLite-backed application/session metadata and historical session synthesis path (verify specifics).
## Immediate
1. Review duplicate wind methods and tests.
2. Audit complete backend-to-frontend telemetry contracts and external InfluxDB cache invalidation.
3. Add STW, heel, trim, and current set/drift; verify source paths and unit conversions.
4. Enforce race-only polar eligibility (current builder selects all completed sessions); integrate historical InfluxDB telemetry into analysis rather than only the track route.
## Later
- Long-term best and representative race-only polars; factory seeding with provenance.
- On-demand race polars, manoeuvres, comparative race analysis.
- External boat track/SOG/COG overlays.
- Start-line timing, speed and position analysis with manually supplied endpoints/time until Vulcan logging is verified.
