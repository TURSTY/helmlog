"""Seed synthetic sailing telemetry for development testing."""

import math
import os
from datetime import UTC, datetime, timedelta

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

URL = "http://127.0.0.1:18086"
ORG = "rattler-dev"
BUCKET = "RattlerBucket"
TOKEN = os.environ["INFLUXDB_ADMIN_TOKEN"]

start = datetime(2026, 9, 26, 2, 0, tzinfo=UTC)

with InfluxDBClient(url=URL, token=TOKEN, org=ORG) as client:
    writer = client.write_api(write_options=SYNCHRONOUS)

    points = []

    for second in range(601):
        ts = start + timedelta(seconds=second)

        # Synthetic movement around Wellington Harbour.
        lat = -41.255 + second * 0.000005
        lon = 174.905 + second * 0.000012

        sog_kts = 6.2 + 0.4 * math.sin(second / 40)
        cog_deg = 65 + 5 * math.sin(second / 90)

        point = (
            Point("sailing")
            .tag("source", "synthetic")
            .field("latitude", lat)
            .field("longitude", lon)
            .field("sog_kts", sog_kts)
            .field("cog_deg", cog_deg)
            .time(ts, WritePrecision.S)
        )
        points.append(point)

    writer.write(bucket=BUCKET, org=ORG, record=points)

print(f"Inserted {len(points)} synthetic GPS records.")
