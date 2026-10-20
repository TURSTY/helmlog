# Source audit — 2026-10-20 (partial)

Repository: TURSTY/helmlog, branch `feature/influx-telemetry-source`. These findings were inspected through GitHub file reads; original historical telemetry implementation baseline confirmed by user on Dockerbox: `acc3ba959f660c13c2cb03fdc20f5221efdeef2d`. The v1.0 skill installation baseline is `f1ec3728915ffb910456d9bf19b0840f84e26ef3`, not a new application-code audit. Neither marker asserts current HEAD. Check actual HEAD and relevant changes before relying on these findings.

## Confirmed adapter contract
- `src/helmlog/telemetry_influx.py`: `InfluxDBTelemetrySource.positions(start,end)` returns dictionaries with `ts`, `latitude_deg`, `longitude_deg` (decimal degrees).
- `cogsog(start,end)` is asynchronous and returns `ts`, `sog_kts`, `cog_deg`; Signal K speed is converted m/s to knots (factor 1.943844492) and course radians to degrees. SOG/COG are merged at UTC-second granularity.
- `headings(start,end)` is asynchronous and returns `ts`, `heading_deg`; current Signal K query hard-codes `navigation.headingTrue` and source `derived-data`; radians converted to degrees modulo 360.
- `winds(start,end)` is asynchronous and returns `ts`, `wind_speed_kts`, `wind_angle_deg`, `reference`; reference 0 true wind and 2 apparent. Signal K true wind source hard-coded `derived-data`, apparent wind `Seatalk1.ST`. Speed converted m/s to knots, angles radians to degrees. Samples with incomplete speed/angle pairs are dropped.
- IMPORTANT: `winds` and `_winds_sync` each occur twice in the inspected file. The later method definitions override the earlier ones. Investigate and remove duplicate safely after tests, with approval.
- The adapter is read-only with respect to InfluxDB; it performs queries and returns converted rows.

## Confirmed replay path and limits
- `src/helmlog/routes/sessions.py` selects the historical track source using `HELMLOG_TELEMETRY_SOURCE`, default `sqlite`; `influxdb` uses `INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET`, `HELMLOG_INFLUX_SCHEMA`, `HELMLOG_INFLUX_VESSEL`, `HELMLOG_INFLUX_GPS_SOURCE`.
- The inspected route uses InfluxDB positions for track GeoJSON and averages position samples per UTC second. Do not assume *all* summary/analysis endpoints use InfluxDB until separately verified.
- `src/helmlog/current.py` already implements `compute_set_drift(sog,cog,stw,hdg,heel_deg,leeway_k,compass_offset_port,compass_offset_stbd)`, returning `(set_deg, drift_kts)`; requires SOG/COG/STW/HDG. Set is direction current flows toward. Optional heel-based leeway and per-tack compass corrections exist. Reuse and test rather than duplicating calculations.
- `src/helmlog/cache.py` has T1 in-process TTL cache and T2 SQLite `web_cache` with data hash based on race rows, position row count, calibration and linked results. Since historical InfluxDB changes may not affect SQLite position row counts, verify cache invalidation for Influx-backed sessions before relying on cached summaries.

## Additional verified polar and storage contracts
- `src/helmlog/polar.py`: `build_polar_baseline(storage, min_sessions=3)` selects completed rows from `races` with `end_utc IS NOT NULL` **without** a `session_type = 'race'` filter. Therefore existing baseline selection does not meet Rattler's race-only requirement; fix in a future implementation task, not as part of skill finalization.
- The builder reads `speeds`, `winds`, `headings` through `storage.query_range`, which reads SQLite, not the historical InfluxDB adapter. The existing InfluxDB track override does not imply polar analysis uses InfluxDB.
- Builder bins TWS/TWA, computes `mean_bsp` and `p90_bsp`, and requires samples from at least three distinct sessions per bin by default. `polar_baseline` table stores those statistics plus `session_count`, `sample_count`, `built_at`; it does not store factory provenance or a separate maximum credible speed.
- `src/helmlog/polar.py` includes a race-window function with gun provenance (Vakaros race start or session start) and heuristic finish detection; these heuristics must be validated for Rattler's race formats.
- `src/helmlog/routes/polar.py` exposes `/api/polar/current` and admin `/api/polar/rebuild`; rebuild increments `polar_baseline_version` used by cached polar grades.
- `src/helmlog/storage.py`: `query_range(table,start,end,race_id=None)` queries SQLite rows from an allowlist of telemetry tables. `start_race(...)` auto-closes open races and sets active race state, so it is not an appropriate historical-session insertion method unchanged. `upsert_polar_baseline` deletes and replaces all baseline rows.
- `src/helmlog/race_classifier.py` is a heuristic classifier for **Gaia GPS imports**, not proof that Signal K history is automatically classified. Its defaults are centred near Seattle, not Wellington. Never silently use it to mark Rattler history as races.

## Implementation questions deferred until the next development task
- Confirm complete polar and replay data contracts, including race/session classification, creation APIs, analysis filters and race-only eligibility.
- Trace full replay API (track, timeline, instruments, wind, heel/trim, current), templates and frontend unit contracts.
- Confirm source precedence/fallback, exact source IDs and historic coverage for Precision-9 heel/trim and ST60 STW.
- Verify whether `HELMLOG_TELEMETRY_SOURCE` applies consistently across all replay endpoints and whether async/sync call sites are correct.
- Inspect tests and deployment commands on Dockerbox; check browser cache, process reload and T1/T2 invalidation using targeted tests.
- Review upstream changes when beginning a development milestone; update this audit if affected.

## Source URLs
- https://github.com/TURSTY/helmlog/blob/feature/influx-telemetry-source/src/helmlog/telemetry_influx.py
- https://github.com/TURSTY/helmlog/blob/feature/influx-telemetry-source/src/helmlog/routes/sessions.py
- https://github.com/TURSTY/helmlog/blob/feature/influx-telemetry-source/src/helmlog/current.py
- https://github.com/TURSTY/helmlog/blob/feature/influx-telemetry-source/src/helmlog/cache.py
