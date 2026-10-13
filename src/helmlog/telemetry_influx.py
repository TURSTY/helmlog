"""Read historical sailing telemetry from InfluxDB 2."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from influxdb_client import InfluxDBClient


class InfluxDBTelemetrySource:
    """Read historical telemetry without modifying the source database."""

    def __init__(
        self,
        *,
        url: str,
        token: str,
        org: str,
        bucket: str,
    ) -> None:
        self.url = url
        self.org = org
        self.bucket = bucket
        self.client = InfluxDBClient(url=url, token=token, org=org)

    def close(self) -> None:
        self.client.close()

    def positions(
        self,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Return GPS positions in HelmLog-compatible column names."""

        query = f'''
from(bucket: "{self.bucket}")
  |> range(start: {start.isoformat()}, stop: {(end + timedelta(microseconds=1)).isoformat()})
  |> filter(fn: (r) => r._measurement == "sailing")
  |> filter(fn: (r) => r._field == "latitude" or r._field == "longitude")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "latitude", "longitude"])
  |> sort(columns: ["_time"])
'''

        tables = self.client.query_api().query(query, org=self.org)

        positions = []

        for table in tables:
            for record in table.records:
                lat = record.values.get("latitude")
                lon = record.values.get("longitude")

                if lat is None or lon is None:
                    continue

                positions.append(
                    {
                        "ts": record.get_time().isoformat(),
                        "latitude_deg": float(lat),
                        "longitude_deg": float(lon),
                    }
                )

        positions.sort(key=lambda p: p["ts"])
        return positions

    async def cogsog(
        self,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Return historical COG/SOG records for HelmLog replay."""
        import asyncio

        return await asyncio.to_thread(self._cogsog_sync, start, end)

    def _cogsog_sync(
        self,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        query = f'''
from(bucket: "{self.bucket}")
  |> range(start: {start.isoformat()}, stop: {(end + timedelta(microseconds=1)).isoformat()})
  |> filter(fn: (r) => r._measurement == "sailing")
  |> filter(fn: (r) => r._field == "sog_kts" or r._field == "cog_deg")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "sog_kts", "cog_deg"])
  |> sort(columns: ["_time"])
'''

        tables = self.client.query_api().query(query, org=self.org)
        rows = []

        for table in tables:
            for record in table.records:
                sog = record.values.get("sog_kts")
                cog = record.values.get("cog_deg")

                if sog is None and cog is None:
                    continue

                rows.append(
                    {
                        "ts": record.get_time().isoformat(),
                        "sog_kts": float(sog) if sog is not None else None,
                        "cog_deg": float(cog) if cog is not None else None,
                    }
                )

        rows.sort(key=lambda row: row["ts"])
        return rows
