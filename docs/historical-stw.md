# Historical STW replay

Implementation under review on `feature/historical-stw`, based on
`9f5e28271c8342dd46aeaf0088df5ef7c4b43c9c`. No new commit baseline is claimed.

## Source and contracts

In InfluxDB replay mode, `InfluxDBTelemetrySource.speeds()` supplies STW rows
using the existing `ts` / `speed_kts` contract. `/api/sessions/{id}/replay`
exposes these as `samples[].stw` in knots; `samples[].sog` remains independent.
The existing STW gauge and sparkline need no frontend changes. SQLite replay,
session metadata and polar grading retain their existing behavior.

For Signal K, configure the exact vessel in `HELMLOG_INFLUX_VESSEL` and the
case-sensitive STW source in `HELMLOG_INFLUX_STW_SOURCE`. Both are required;
the GPS source is not reused for STW. Queries select
`navigation.speedThroughWater`, field `value`, with those context/source tags.
The native m/s contract follows `sk_reader.py`; conversion to knots happens
once at the adapter boundary (factor 1.943844492). Synthetic schema queries
`sailing.speed_kts`, which is already in knots.

The earliest valid reading in each UTC second is selected after sorting
across Flux tables. Zero is retained; absent, non-finite and negative readings
are omitted without altering raw data. There is no forward fill, SOG
substitution or SQLite fallback in InfluxDB mode. Missing STW is null in a
second contributed by another instrument; no STW-only seconds are invented.
A missing source configuration raises an error rather than mixing sources.

## Read-only historical verification

On 2026-10-20, the local InfluxDB 2.7.12 instance at port 18086 contained
`RattlerOrg` / `RattlerBucket` history for development session 2. Its replay
window, including prestart, is 2026-10-10 20:30–22:11 UTC
(2026-10-11 09:30–11:11 NZDT).

A query without a context/source filter found all 6,061 STW readings in that
window under `vessels.urn:mrn:imo:mmsi:512009320`, `source=Seatalk1.ST`,
`self=true`, field `value`. The adapter returned 6,058 distinct seconds,
including 16 zero seconds; maximum STW was approximately 8.90 knots.
The replay HTTP response matched every adapter STW second and value.
SQLite was opened read-only and grading was excluded from this verification
to prevent writes to grade caches. Browser rendering was not exercised.

Older history includes context `12009320` and a lowercase `seatalk1.ST`
source. Their relationship to `512009320` is not established; they are not
combined. Local results do not establish production availability or retention.

## Current, stale values and caches

Replay already calls `compute_set_drift()` when STW, SOG, COG and heading
are available in the same second. Adding historical STW activates that existing
calculation; it does not validate a current measurement. In the verification
window, 6,057 seconds produced derived current, with drift reaching 7.87 knots.
The maximum occurs at 2026-10-10 21:16:16 UTC, when recorded STW is zero
while SOG is 7.87 knots; the existing formula therefore reports all ground
speed as current. A zero STW reading can be an instrument anomaly even though
it must be preserved as recorded. This is a concrete misleading-current risk,
not a validated 7.87-knot current observation.
These values require investigation before tactical use: heading/STW accuracy,
subsecond alignment, heel/leeway and compass calibration can affect the result.
No current formula, thresholds or calibration defaults are changed here.
Missing STW leaves both set and drift null; valid zero STW still permits the
existing calculation. Regression tests cover these distinctions.

The frontend's existing preceding-sample lookup has no age limit, so a total
telemetry gap can leave old readings visible. This change does not add frontend
age handling or fill missing STW readings.

The replay endpoint currently returns a direct JSON response and bypasses
T1/T2 response caching despite its stale cache-version comment. Track and
summary caches use SQLite-derived hashes that do not capture external InfluxDB
changes or source selection. No caches are cleared or redesigned here. Manual
UI verification must confirm the running code and selected source; refresh the
page to fetch replay again after loading the changed development process.
Duplicate wind methods are unchanged and remain separate technical debt.

## Validation results

- All 165 test modules ran once in eight file batches without coverage
  instrumentation: 2,968 passed, 3 skipped, 2 failed.
- Both failures (`test_replay_emits_etag_and_304` and
  `test_replay_cache_blob_written_and_invalidated`) reproduce on unchanged
  development HEAD `9f5e282`; they reflect the existing replay cache bypass.
- The focused adapter, STW, prestart and current modules pass all 39 tests,
  including nine new STW cases. Separate focused coverage executes all
  statements in both new adapter methods. The new route regressions also
  fail on the original code because it returns SQLite STW instead.
- An earlier instrumented run exposed the existing timing-sensitive
  `test_state_surfaces_scheduled_start`; it reproduced on the baseline and
  passed in the final assertion run.
- Required repository-wide static checks remain blocked by baseline issues:
  Ruff reports eight errors, format checking flags two files, and mypy
  reports 21 errors. The same diagnostics occur on unchanged `9f5e282`;
  the STW additions introduce no new diagnostics. New adapter methods pass
  formatting independently; duplicate wind methods are unchanged.

These results do not make the repository's PR gate green. Unrelated cache,
wind-cleanup, formatting and typing fixes require separate work.
