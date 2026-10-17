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
