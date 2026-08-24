from __future__ import annotations

import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.logging_config import get_logger

logger = get_logger("database.connection")


class DatabaseManager:
    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._connection = await aiosqlite.connect(str(self._db_path))
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA foreign_keys=ON")
        await self._connection.execute("PRAGMA busy_timeout=5000")
        logger.info("Database initialized at %s", self._db_path)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        if not self._connection:
            await self.initialize()
        yield self._connection

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        async with self.get_connection() as conn:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor

    async def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        async with self.get_connection() as conn:
            await conn.executemany(sql, params_list)
            await conn.commit()

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        async with self.get_connection() as conn:
            cursor = await conn.execute(sql, params)
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        async with self.get_connection() as conn:
            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


_db_instance: DatabaseManager | None = None


async def get_database(db_path: str | Path = "data/aegiscyber.db") -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager(db_path)
        await _db_instance.initialize()
    return _db_instance


async def close_database() -> None:
    global _db_instance
    if _db_instance:
        await _db_instance.close()
        _db_instance = None
