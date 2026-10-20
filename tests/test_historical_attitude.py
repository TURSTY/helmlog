"""Historical attitude display and isolation from current corrections."""

import math
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from helmlog.current import compute_set_drift
from helmlog.nmea2000 import PGN_ATTITUDE, AttitudeRecord
from helmlog.storage import Storage
from helmlog.telemetry_influx import InfluxDBTelemetrySource
from helmlog.web import create_app

START = datetime(2026, 10, 10, 20, 50, tzinfo=UTC)
SOURCE = "can0.c0788c002270a682"


@pytest.mark.asyncio
@pytest.mark.parametrize("schema", ["signalk", "sailing"])
async def test_attitude_conversion_partial_data_and_order(schema: str) -> None:
    records = []
    for field, offset, value in [
        ("roll", 900, 0.9),
        ("roll", 100, -0.2),
        ("pitch", 200, -0.1),
        ("roll", 1100, 0.0),
        ("pitch", 1200, float("nan")),
        ("roll", 2100, None),
        ("pitch", 2200, float("inf")),
        ("pitch", 3100, 0.25),
    ]:
        record = MagicMock()
        record.values = {
            "_measurement": f"navigation.attitude.{field}" if schema == "signalk" else "sailing",
            "_field": "value"
            if schema == "signalk"
            else {"roll": "heel_deg", "pitch": "trim_deg"}[field],
            "_value": value,
            "_time": START + timedelta(milliseconds=offset),
        }
        records.append(record)
    with patch("helmlog.telemetry_influx.InfluxDBClient") as factory:
        query = factory.return_value.query_api.return_value.query
        query.return_value = [MagicMock(records=records[:1]), MagicMock(records=records[1:])]
        source = InfluxDBTelemetrySource(
            url="http://unused",
            token="test",
            org="test",
            bucket="test",
            schema=schema,
            vessel="512009320",
            attitude_source=SOURCE,
        )
        try:
            rows = await source.attitudes(START, START + timedelta(seconds=4))
            convert = math.degrees if schema == "signalk" else float
            assert rows == [
                {
                    "ts": START.isoformat(),
                    "heel_deg": pytest.approx(convert(-0.2)),
                    "trim_deg": pytest.approx(convert(-0.1)),
                },
                {
                    "ts": (START + timedelta(seconds=1)).isoformat(),
                    "heel_deg": 0.0,
                    "trim_deg": None,
                },
                {
                    "ts": (START + timedelta(seconds=3)).isoformat(),
                    "heel_deg": None,
                    "trim_deg": pytest.approx(convert(0.25)),
                },
            ]
            flux = query.call_args.args[0]
            assert (START + timedelta(seconds=4, microseconds=1)).isoformat() in flux
            if schema == "signalk":
                assert 'r.context == "vessels.urn:mrn:imo:mmsi:512009320"' in flux
                assert f'r.source == "{SOURCE}"' in flux
                assert 'r._measurement == "navigation.attitude.roll"' in flux
                assert 'r._measurement == "navigation.attitude.pitch"' in flux
                assert 'r._field == "value"' in flux
                assert "pypilot" not in flux and 'mmsi:12009320"' not in flux
            else:
                assert 'r._measurement == "sailing"' in flux
                assert 'r._field == "heel_deg"' in flux and 'r._field == "trim_deg"' in flux
        finally:
            source.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("vessel,selection", [(None, SOURCE), ("512009320", None)])
async def test_attitude_requires_explicit_selection(
    vessel: str | None, selection: str | None
) -> None:
    with patch("helmlog.telemetry_influx.InfluxDBClient") as factory:
        source = InfluxDBTelemetrySource(
            url="http://unused",
            token="test",
            org="test",
            bucket="test",
            schema="signalk",
            vessel=vessel,
            attitude_source=selection,
        )
        try:
            with pytest.raises(ValueError, match="vessel and attitude_source"):
                await source.attitudes(START, START)
            factory.return_value.query_api.assert_not_called()
        finally:
            source.close()


@pytest.mark.asyncio
async def test_attitude_empty_history() -> None:
    with patch("helmlog.telemetry_influx.InfluxDBClient") as factory:
        factory.return_value.query_api.return_value.query.return_value = []
        source = InfluxDBTelemetrySource(
            url="http://unused",
            token="test",
            org="test",
            bucket="test",
            schema="signalk",
            vessel="512009320",
            attitude_source=SOURCE,
        )
        try:
            assert await source.attitudes(START, START) == []
        finally:
            source.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,sqlite_heel,remote_heel",
    [
        ("sqlite", None, None),
        ("sqlite", 12.0, None),
        ("influxdb", None, -20.0),
        ("influxdb", None, 0.0),
        ("influxdb", None, None),
        ("influxdb", 12.0, -20.0),
        ("influxdb", 12.0, 0.0),
        ("influxdb", 12.0, None),
    ],
)
async def test_attitude_replay_display_preserves_current_inputs(
    storage: Storage,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    sqlite_heel: float | None,
    remote_heel: float | None,
) -> None:
    race = await storage.start_race(
        event="Attitude", name="Replay", start_utc=START, date_str="2026-10-10", race_num=1
    )
    await storage.end_race(race.id, START + timedelta(seconds=1))
    if sqlite_heel is not None:
        await storage.write(AttitudeRecord(PGN_ATTITUDE, 0, START, sqlite_heel, -3.0))
    db = storage._conn()
    for table, columns, values in [
        ("speeds", "speed_kts", "6"),
        ("cogsog", "sog_kts,cog_deg", "7,90"),
        ("headings", "heading_deg", "90"),
    ]:
        await db.execute(
            f"INSERT INTO {table} (ts,source_addr,{columns}) VALUES (?,0,{values})",
            (START.isoformat(),),
        )
    await db.commit()
    storage._leeway_k = 10.0
    storage._compass_offset_port = 3.0
    storage._compass_offset_stbd = -4.0
    for key, value in {
        "HELMLOG_TELEMETRY_SOURCE": mode,
        "INFLUX_URL": "http://unused",
        "INFLUX_TOKEN": "test",
        "INFLUX_ORG": "test",
        "INFLUX_BUCKET": "test",
        "HELMLOG_INFLUX_SCHEMA": "signalk",
        "HELMLOG_INFLUX_VESSEL": "512009320",
        "HELMLOG_INFLUX_ATTITUDE_SOURCE": SOURCE,
    }.items():
        monkeypatch.setenv(key, value)
    with patch("helmlog.telemetry_influx.InfluxDBTelemetrySource") as factory:
        source = factory.return_value
        source.speeds = AsyncMock(return_value=[{"ts": START.isoformat(), "speed_kts": 6.0}])
        source.cogsog = AsyncMock(
            return_value=[{"ts": START.isoformat(), "sog_kts": 7.0, "cog_deg": 90.0}]
        )
        source.headings = AsyncMock(return_value=[{"ts": START.isoformat(), "heading_deg": 90.0}])
        source.winds = AsyncMock(return_value=[])
        prestart = START - timedelta(minutes=5)
        source.attitudes = AsyncMock(
            return_value=[]
            if remote_heel is None
            else [
                {"ts": prestart.isoformat(), "heel_deg": -5.0, "trim_deg": 0.0},
                {"ts": START.isoformat(), "heel_deg": remote_heel, "trim_deg": None},
                {
                    "ts": (START + timedelta(seconds=1)).isoformat(),
                    "heel_deg": None,
                    "trim_deg": -2.0,
                },
            ]
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(storage)), base_url="http://test"
        ) as client:
            response = await client.get(f"/api/sessions/{race.id}/replay")
        assert response.status_code == 200
        samples = {s["ts"]: s for s in response.json()["samples"]}
        sample = samples[START.strftime("%Y-%m-%dT%H:%M:%SZ")]
        assert sample["heel"] == (remote_heel if mode == "influxdb" else sqlite_heel)
        assert sample["trim"] == (-3.0 if mode == "sqlite" and sqlite_heel is not None else None)
        expected = compute_set_drift(
            7.0,
            90.0,
            6.0,
            90.0,
            heel_deg=sqlite_heel,
            leeway_k=10.0,
            compass_offset_port=3.0,
            compass_offset_stbd=-4.0,
        )
        assert expected is not None
        assert sample["set"] == pytest.approx(expected[0])
        assert sample["drift"] == pytest.approx(expected[1])
        if mode == "influxdb":
            assert factory.call_args.kwargs["attitude_source"] == SOURCE
            source.attitudes.assert_awaited_once_with(
                START - timedelta(minutes=20), START + timedelta(seconds=1)
            )
            source.close.assert_called_once()
            if remote_heel is not None:
                assert samples[prestart.strftime("%Y-%m-%dT%H:%M:%SZ")]["heel"] == -5.0
                partial = samples[(START + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")]
                assert partial["heel"] is None and partial["trim"] == -2.0
        else:
            factory.assert_not_called()
