"""Tests for historical InfluxDB telemetry replay."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from helmlog.telemetry_influx import InfluxDBTelemetrySource


def test_synthetic_positions() -> None:
    """Existing synthetic GPS replay must remain functional."""
    timestamp = datetime(2026, 10, 11, 1, 0, tzinfo=UTC)

    record = MagicMock()
    record.values = {
        "latitude": -41.25,
        "longitude": 174.85,
    }
    record.get_time.return_value = timestamp

    with patch("helmlog.telemetry_influx.InfluxDBClient") as client_class:
        client = client_class.return_value
        client.query_api.return_value.query.return_value = [
            MagicMock(records=[record])
        ]

        source = InfluxDBTelemetrySource(
            url="http://localhost:18086",
            token="test-token",
            org="rattler-dev",
            bucket="RattlerDev",
        )

        positions = source.positions(timestamp, timestamp)

        assert positions == [
            {
                "ts": timestamp.isoformat(),
                "latitude_deg": -41.25,
                "longitude_deg": 174.85,
            }
        ]

        query = client.query_api.return_value.query.call_args.args[0]
        assert 'r._measurement == "sailing"' in query

        source.close()


def test_signalk_positions() -> None:
    """Read Rattler GPS positions using Signal K measurement and tags."""
    timestamp = datetime(2026, 10, 11, 0, 0, tzinfo=UTC)

    record = MagicMock()
    record.values = {
        "lat": -41.2494368,
        "lon": 174.902272,
    }
    record.get_time.return_value = timestamp

    with patch("helmlog.telemetry_influx.InfluxDBClient") as client_class:
        client = client_class.return_value
        client.query_api.return_value.query.return_value = [
            MagicMock(records=[record])
        ]

        source = InfluxDBTelemetrySource(
            url="http://localhost:18086",
            token="test-token",
            org="RattlerOrg",
            bucket="RattlerBucket",
            schema="signalk",
            vessel="512009320",
            gps_source="can0.c078c3003f034c09",
        )

        positions = source.positions(timestamp, timestamp)

        assert positions == [
            {
                "ts": timestamp.isoformat(),
                "latitude_deg": -41.2494368,
                "longitude_deg": 174.902272,
            }
        ]

        query = client.query_api.return_value.query.call_args.args[0]

        assert 'r._measurement == "navigation.position"' in query
        assert 'r.context == "vessels.urn:mrn:imo:mmsi:512009320"' in query
        assert 'r.source == "can0.c078c3003f034c09"' in query

        source.close()


def test_signalk_invalid_positions() -> None:
    """Reject invalid GPS coordinates from historical Signal K data."""
    timestamp = datetime(2026, 10, 11, 0, 0, tzinfo=UTC)

    coordinates = [
        (-0.0000001, 0.0),
        (95.0, 174.9),
        (-41.2494368, 174.902272),
    ]

    records = []
    for lat, lon in coordinates:
        record = MagicMock()
        record.values = {"lat": lat, "lon": lon}
        record.get_time.return_value = timestamp
        records.append(record)

    with patch("helmlog.telemetry_influx.InfluxDBClient") as client_class:
        client = client_class.return_value
        client.query_api.return_value.query.return_value = [
            MagicMock(records=records)
        ]

        source = InfluxDBTelemetrySource(
            url="http://localhost:18086",
            token="test-token",
            org="RattlerOrg",
            bucket="RattlerBucket",
            schema="signalk",
            vessel="512009320",
            gps_source="can0.c078c3003f034c09",
        )

        positions = source.positions(timestamp, timestamp)

        assert len(positions) == 1
        assert positions[0]["latitude_deg"] == pytest.approx(-41.2494368)
        assert positions[0]["longitude_deg"] == pytest.approx(174.902272)

        source.close()


def test_signalk_cogsog() -> None:
    """Convert Signal K SOG and COG into HelmLog units."""
    import asyncio

    timestamp = datetime(2026, 10, 11, 0, 0, tzinfo=UTC)

    sog_record = MagicMock()
    sog_record.values = {"_value": 4.0}
    sog_record.get_time.return_value = timestamp

    cog_record = MagicMock()
    cog_record.values = {"_value": 1.5707963267948966}
    cog_record.get_time.return_value = timestamp

    with patch("helmlog.telemetry_influx.InfluxDBClient") as client_class:
        client = client_class.return_value
        client.query_api.return_value.query.side_effect = [
            [MagicMock(records=[sog_record])],
            [MagicMock(records=[cog_record])],
        ]

        source = InfluxDBTelemetrySource(
            url="http://localhost:18086",
            token="test-token",
            org="RattlerOrg",
            bucket="RattlerBucket",
            schema="signalk",
            vessel="512009320",
            gps_source="can0.c078c3003f034c09",
        )

        rows = asyncio.run(source.cogsog(timestamp, timestamp))

        assert any(
            row["sog_kts"] == pytest.approx(7.775377968)
            for row in rows
            if row["sog_kts"] is not None
        )
        assert any(
            row["cog_deg"] == pytest.approx(90.0)
            for row in rows
            if row["cog_deg"] is not None
        )

        source.close()
