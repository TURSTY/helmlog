# Historical heel and trim replay

Implementation under review on `feature/historical-attitude`, based on
`5c5654981ad586bcd0c061020f75cf3c537e7a24`. No new commit baseline is claimed.

## Source and display contract

Configure `HELMLOG_INFLUX_ATTITUDE_SOURCE=can0.c0788c002270a682` with
`HELMLOG_INFLUX_VESSEL=512009320` and the existing Signal K replay settings.
The adapter queries `navigation.attitude.roll` and `navigation.attitude.pitch`,
field `value`, in one query with exact source/context filters. There is no
fallback to pypilot, other contexts, or SQLite for the InfluxDB display.
Missing required selection raises an error instead of mixing sources.

`attitudes()` returns `ts`, `heel_deg` and `trim_deg`; replay exposes the existing
`heel` and `trim` fields. Signal K radians are converted to degrees once.
Synthetic `sailing.heel_deg` / `sailing.trim_deg` values are already degrees.
Each field uses its earliest finite reading per UTC second, independently.
Zeros and negative values are preserved; missing components remain null.
No smoothing, sign inversion or installation-specific offset is introduced.

Existing HelmLog display convention is positive heel = starboard down and
positive trim = bow up. Physical orientation of the selected sensor remains
unverified; signed readings are passed through rather than claiming a verified
installation calibration. Existing frontend and SQLite display behavior are
unchanged.

## Current isolation

The new InfluxDB attitude series is display-only. Replay retains the original
SQLite attitude series separately for the existing current calculation. Thus
an absent SQLite heel still passes `None` to `compute_set_drift()`, while an
existing SQLite heel retains its previous leeway and per-tack compass effects.
This preserves current inputs in both replay modes, including mixed historical
sessions; it is not a fallback for the displayed heel or trim.

No current formula or calibration defaults change. InfluxDB heel cannot
activate leeway or select a compass offset through this change. Enabling that
later requires an explicit reviewed change after orientation and leeway
calibration have been validated. Displayed heel and current's legacy heel
input may intentionally differ. Existing STW/current quality risks still apply.

## One read-only historical verification

On 2026-10-20, verification used local InfluxDB at `127.0.0.1:18086`, organization
`RattlerOrg`, bucket `RattlerBucket`, and session 2 metadata from SQLite opened
with `mode=ro` and `query_only=ON`. Grading was excluded to prevent cache writes.
The window was 2026-10-10 20:30–22:11 UTC, including prestart
(2026-10-11 09:30–11:11 NZDT).

- Raw selected-source history: 10,369 roll and 10,369 pitch readings.
- Replay matched independently converted raw readings for all 6,060 seconds.
- Downsampled heel range: -35.23 to +26.52 degrees; trim: -1.51 to +1.57 degrees.
- One zero heel second and 87 zero trim seconds were preserved.
- The original SQLite window contained no attitudes. All 6,057 calculable
  current samples matched their prior, heel-free inputs with default K=10.
  Using the displayed heel instead would have changed 6,040 current samples;
  the isolation mechanism prevented those changes.

Physical orientation, production operation and browser rendering were not
validated. The existing GUI age-limit and cache limitations documented in
[historical STW](historical-stw.md) remain unchanged. No running server was
restarted or reconfigured.

## Focused validation

TDD began with 11 failing new cases and two passing SQLite cases. After
implementation, all 39 selected tests passed: attitude adapter/replay isolation,
STW regressions, current calculations and existing SQLite heel/trim replay.
Tests include empty data, missing components, signed/zero values, exact source
selection, prestart data and preservation of legacy current inputs even when
SQLite heel differs from displayed InfluxDB heel.

Changed-file Ruff reports only the known duplicate-wind F811 error. Scoped
mypy for the two touched source files reports the same 19 diagnostics as saved
baseline evidence; no baseline suite was rerun. Changed route/tests and both
new adapter methods pass formatting. Duplicate wind methods, current formulas,
frontend, caching and polar code remain unchanged. Repository-wide validation
was not run; mandatory pre-PR checks are not waived.
