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
        schema: str = "sailing",
        vessel: str | None = None,
        gps_source: str | None = None,
    ) -> None:
        if schema not in ("sailing", "signalk"):
            raise ValueError(f"Unsupported InfluxDB schema: {schema}")

        self.url = url
        self.org = org
        self.bucket = bucket
        self.schema = schema
        self.vessel = vessel
        self.gps_source = gps_source
        self.client = InfluxDBClient(url=url, token=token, org=org)

    def close(self) -> None:
        self.client.close()

    def positions(
        self,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Return GPS positions in HelmLog-compatible column names."""

        if self.schema == "signalk":
            if not self.vessel or not self.gps_source:
                raise ValueError("Signal K requires vessel and gps_source")

            measurement = "navigation.position"
            lat_field = "lat"
            lon_field = "lon"
            filters = (
                f'  |> filter(fn: (r) => r.context == '
                f'"vessels.urn:mrn:imo:mmsi:{self.vessel}")\n'
                f'  |> filter(fn: (r) => r.source == "{self.gps_source}")\n'
            )
        else:
            measurement = "sailing"
            lat_field = "latitude"
            lon_field = "longitude"
            filters = ""

        query = f'''
from(bucket: "{self.bucket}")
  |> range(start: {start.isoformat()}, stop: {(end + timedelta(microseconds=1)).isoformat()})
  |> filter(fn: (r) => r._measurement == "{measurement}")
{filters}  |> filter(fn: (r) => r._field == "{lat_field}" or r._field == "{lon_field}")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "{lat_field}", "{lon_field}"])
  |> sort(columns: ["_time"])
'''

        tables = self.client.query_api().query(query, org=self.org)
        positions = []

        for table in tables:
            for record in table.records:
                lat = record.values.get(lat_field)
                lon = record.values.get(lon_field)

                if lat is None or lon is None:
                    continue

                lat = float(lat)
                lon = float(lon)

                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    continue

                if abs(lat) < 0.001 and abs(lon) < 0.001:
                    continue

                positions.append(
                    {
                        "ts": record.get_time().isoformat(),
                        "latitude_deg": lat,
                        "longitude_deg": lon,
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
        if self.schema == "signalk":
            if not self.vessel or not self.gps_source:
                raise ValueError("Signal K requires vessel and gps_source")

            measurements = [
                ("navigation.speedOverGround", "sog_kts", 1.943844492),
                (
                    "navigation.courseOverGroundTrue",
                    "cog_deg",
                    180.0 / 3.141592653589793,
                ),
            ]

            # Collect SOG and COG independently, then merge by UTC second.
            by_second: dict[str, dict[str, Any]] = {}

            for measurement, output_field, conversion in measurements:
                query = f'''
from(bucket: "{self.bucket}")
  |> range(start: {start.isoformat()}, stop: {(end + timedelta(microseconds=1)).isoformat()})
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r.context == "vessels.urn:mrn:imo:mmsi:{self.vessel}")
  |> filter(fn: (r) => r.source == "{self.gps_source}")
  |> filter(fn: (r) => r._field == "value")
  |> keep(columns: ["_time", "_value"])
  |> sort(columns: ["_time"])
'''

                tables = self.client.query_api().query(query, org=self.org)

                # Sort across Flux tables so the earliest reading wins.
                readings = []
                for table in tables:
                    for record in table.records:
                        value = record.values.get("_value")
                        if value is not None:
                            readings.append((record.get_time(), float(value)))

                readings.sort(key=lambda item: item[0])

                for timestamp, value in readings:
                    second = timestamp.replace(microsecond=0).isoformat()

                    if second not in by_second:
                        by_second[second] = {
                            "ts": second,
                            "sog_kts": None,
                            "cog_deg": None,
                        }

                    if by_second[second][output_field] is not None:
                        continue

                    converted = value * conversion

                    if output_field == "cog_deg":
                        converted %= 360.0

                    by_second[second][output_field] = converted

            return [
                by_second[second]
                for second in sorted(by_second)
            ]

        # Original synthetic telemetry reader.
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
