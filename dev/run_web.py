"""Standalone HelmLog development web server.

Starts the FastAPI interface without starting CAN or audio logging.
Uses a separate SQLite database for development.
"""

import asyncio
import os
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "dev-data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

os.environ["DB_PATH"] = str(DATA_DIR / "helmlog-dev.db")
os.environ["WEB_PORT"] = "3002"
os.environ["WEB_HOST"] = "127.0.0.1"
os.environ["AUTH_DISABLED"] = "true"

from helmlog.storage import Storage, StorageConfig
from helmlog.web import create_app


async def main():
    storage = Storage(StorageConfig())
    await storage.connect()

    try:
        app = create_app(storage)

        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=3002,
            log_level="info",
        )

        server = uvicorn.Server(config)
        await server.serve()

    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
