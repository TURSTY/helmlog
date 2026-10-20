"""Historical STW contracts, source isolation and replay integration."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from helmlog.storage import Storage
from helmlog.telemetry_influx import InfluxDBTelemetrySource
from helmlog.web import create_app

START = datetime(2026, 10, 10, 20, 50, tzinfo=UTC)


@pytest.mark.asyncio
@pytest.mark.parametrize("schema", ["signalk", "sailing"])
async def test_stw_units_quality_and_order(schema: str) -> None:
    records = []
    for offset, value in [
        (900, 8.0),
        (100, 2.0),
        (1100, 0.0),
        (2100, None),
        (3100, float("nan")),
        (4100, float("inf")),
        (5100, -1.0),
    ]:
        record = MagicMock()
        record.values = {"_value": value, "_time": START + timedelta(milliseconds=offset)}
        record.get_time.return_value = START + timedelta(milliseconds=offset)
        records.append(record)
    with patch("helmlog.telemetry_influx.InfluxDBClient") as client:
        query = client.return_value.query_api.return_value.query
        query.return_value = [MagicMock(records=records[:1]), MagicMock(records=records[1:])]
        source = InfluxDBTelemetrySource(
            url="http://unused",
            token="test",
            org="test",
            bucket="test",
            schema=schema,
            vessel="512009320",
            stw_source="Seatalk1.ST",
        )
        try:
            rows = await source.speeds(START, START + timedelta(seconds=6))
            assert rows == [
                {
                    "ts": START.isoformat(),
                    "speed_kts": pytest.approx(2 * 1.943844492 if schema == "signalk" else 2),
                },
                {"ts": (START + timedelta(seconds=1)).isoformat(), "speed_kts": 0.0},
            ]
            flux = query.call_args.args[0]
            assert (START + timedelta(seconds=6, microseconds=1)).isoformat() in flux
            if schema == "signalk":
                assert 'r._measurement == "navigation.speedThroughWater"' in flux
                assert 'r._field == "value"' in flux
                assert 'r.context == "vessels.urn:mrn:imo:mmsi:512009320"' in flux
                assert 'r.source == "Seatalk1.ST"' in flux
                assert 'mmsi:12009320"' not in flux
            else:
                assert 'r._measurement == "sailing"' in flux
                assert 'r._field == "speed_kts"' in flux
        finally:
            source.close()
        client.return_value.close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("vessel,source_name", [(None, "Seatalk1.ST"), ("512009320", None)])
async def test_stw_requires_explicit_selection(vessel: str | None, source_name: str | None) -> None:
    with patch("helmlog.telemetry_influx.InfluxDBClient") as client:
        source = InfluxDBTelemetrySource(
            url="http://unused",
            token="test",
            org="test",
            bucket="test",
            schema="signalk",
            vessel=vessel,
            stw_source=source_name,
        )
        try:
            with pytest.raises(ValueError, match="vessel and stw_source"):
                await source.speeds(START, START)
            client.return_value.query_api.assert_not_called()
        finally:
            source.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("stw", [None, 0.0, 5.0])
async def test_influx_replay_stw_is_independent(
    storage: Storage,
    monkeypatch: pytest.MonkeyPatch,
    stw: float | None,
) -> None:
    race = await storage.start_race(
        event="STW",
        name="STW replay",
        start_utc=START,
        date_str="2026-10-10",
        race_num=1,
    )
    await storage.end_race(race.id, START + timedelta(seconds=2))
    db = storage._conn()
    await db.execute(
        "INSERT INTO speeds (ts, source_addr, speed_kts) VALUES (?, 0, 99)",
        (START.isoformat(),),
    )
    await db.commit()
    for name, value in {
        "HELMLOG_TELEMETRY_SOURCE": "influxdb",
        "INFLUX_URL": "http://unused",
        "INFLUX_TOKEN": "test",
        "INFLUX_ORG": "test",
        "INFLUX_BUCKET": "test",
        "HELMLOG_INFLUX_SCHEMA": "signalk",
        "HELMLOG_INFLUX_VESSEL": "512009320",
        "HELMLOG_INFLUX_STW_SOURCE": "Seatalk1.ST",
    }.items():
        monkeypatch.setenv(name, value)
    with patch("helmlog.telemetry_influx.InfluxDBTelemetrySource") as factory:
        source = factory.return_value
        prestart = START - timedelta(minutes=5)
        source.speeds = AsyncMock(
            return_value=[]
            if stw is None
            else [
                {"ts": prestart.isoformat(), "speed_kts": stw},
                {"ts": START.isoformat(), "speed_kts": stw},
            ]
        )
        source.cogsog = AsyncMock(
            return_value=[
                {"ts": START.isoformat(), "sog_kts": 7.0, "cog_deg": 90.0},
                {"ts": (START + timedelta(seconds=1)).isoformat(), "sog_kts": 7.0, "cog_deg": 90.0},
            ]
        )
        source.headings = AsyncMock(return_value=[{"ts": START.isoformat(), "heading_deg": 90}])
        source.winds = AsyncMock(return_value=[])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(storage)),
            base_url="http://test",
        ) as client:
            response = await client.get(f"/api/sessions/{race.id}/replay")
        assert response.status_code == 200
        samples = {r["ts"]: r for r in response.json()["samples"]}
        sample = samples[START.strftime("%Y-%m-%dT%H:%M:%SZ")]
        assert sample["stw"] == stw
        assert sample["sog"] == 7.0
        assert sample["drift"] == (None if stw is None else pytest.approx(7 - stw))
        assert sample["set"] == (None if stw is None else pytest.approx(90))
        missing = samples[(START + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")]
        assert missing["stw"] is None
        assert missing["set"] is None and missing["drift"] is None
        if stw is not None:
            assert samples[prestart.strftime("%Y-%m-%dT%H:%M:%SZ")]["stw"] == stw
        source.speeds.assert_awaited_once_with(
            START - timedelta(minutes=20), START + timedelta(seconds=2)
        )
        assert factory.call_args.kwargs["stw_source"] == "Seatalk1.ST"
        source.close.assert_called_once()


@pytest.mark.asyncio
async def test_empty_stw_is_not_manufactured() -> None:
    with patch("helmlog.telemetry_influx.InfluxDBClient") as client:
        client.return_value.query_api.return_value.query.return_value = []
        source = InfluxDBTelemetrySource(
            url="http://unused",
            token="test",
            org="test",
            bucket="test",
            schema="signalk",
            vessel="512009320",
            stw_source="Seatalk1.ST",
        )
        try:
            assert await source.speeds(START, START) == []
        finally:
            source.close()


@pytest.mark.asyncio
async def test_stw_query_failure_closes_client(
    storage: Storage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from helmlog.routes.sessions import _compute_session_replay

    race = await storage.start_race(
        event="STW",
        name="Query failure",
        start_utc=START,
        date_str="2026-10-10",
        race_num=1,
    )
    await storage.end_race(race.id, START + timedelta(seconds=1))
    for name in ("INFLUX_URL", "INFLUX_TOKEN", "INFLUX_ORG", "INFLUX_BUCKET"):
        monkeypatch.setenv(name, "unused")
    monkeypatch.setenv("HELMLOG_TELEMETRY_SOURCE", "influxdb")
    with patch("helmlog.telemetry_influx.InfluxDBTelemetrySource") as factory:
        source = factory.return_value
        source.speeds = AsyncMock(side_effect=RuntimeError("query failed"))
        with pytest.raises(RuntimeError, match="query failed"):
            await _compute_session_replay(storage, race.id)
        source.close.assert_called_once()
