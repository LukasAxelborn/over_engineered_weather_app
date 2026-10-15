"""Postgres access for server-side favorites + search history."""
from typing import Any, Optional

import asyncpg

from .config import settings

_pool: Optional[asyncpg.Pool] = None


async def connect() -> None:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def ping() -> bool:
    try:
        assert _pool is not None
        async with _pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception:
        return False


async def _init_schema(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            device_id   TEXT NOT NULL,
            id          TEXT NOT NULL,
            name        TEXT NOT NULL,
            latitude    DOUBLE PRECISION NOT NULL,
            longitude   DOUBLE PRECISION NOT NULL,
            admin1      TEXT,
            country     TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (device_id, id)
        );
        CREATE TABLE IF NOT EXISTS search_history (
            id          BIGSERIAL PRIMARY KEY,
            device_id   TEXT NOT NULL,
            name        TEXT NOT NULL,
            latitude    DOUBLE PRECISION NOT NULL,
            longitude   DOUBLE PRECISION NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_history_device_time
            ON search_history (device_id, created_at DESC);
        """
    )


async def ensure_schema() -> None:
    """Idempotently create tables (belt-and-braces alongside db/init/*.sql)."""
    assert _pool is not None
    async with _pool.acquire() as conn:
        await _init_schema(conn)


def _row_to_fav(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "name": row["name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "admin1": row["admin1"] or "",
        "country": row["country"] or "",
    }


async def list_favorites(device_id: str) -> list[dict[str, Any]]:
    assert _pool is not None
    rows = await _pool.fetch(
        "SELECT name, latitude, longitude, admin1, country FROM favorites "
        "WHERE device_id = $1 ORDER BY created_at ASC",
        device_id,
    )
    return [_row_to_fav(r) for r in rows]


async def upsert_favorite(device_id: str, fav: dict[str, Any]) -> None:
    assert _pool is not None
    fid = f"{float(fav['latitude']):.3f},{float(fav['longitude']):.3f}"
    await _pool.execute(
        """
        INSERT INTO favorites (device_id, id, name, latitude, longitude, admin1, country)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (device_id, id) DO UPDATE
            SET name = EXCLUDED.name,
                admin1 = EXCLUDED.admin1,
                country = EXCLUDED.country
        """,
        device_id, fid, fav["name"], float(fav["latitude"]), float(fav["longitude"]),
        fav.get("admin1", ""), fav.get("country", ""),
    )


async def delete_favorite(device_id: str, fid: str) -> None:
    assert _pool is not None
    await _pool.execute(
        "DELETE FROM favorites WHERE device_id = $1 AND id = $2", device_id, fid
    )


async def add_history(device_id: str, entry: dict[str, Any], keep: int = 100) -> None:
    assert _pool is not None
    async with _pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO search_history (device_id, name, latitude, longitude) "
                "VALUES ($1, $2, $3, $4)",
                device_id, entry["name"], float(entry["latitude"]), float(entry["longitude"]),
            )
            await conn.execute(
                "DELETE FROM search_history WHERE device_id = $1 AND id NOT IN ("
                "  SELECT id FROM search_history WHERE device_id = $1 "
                "  ORDER BY created_at DESC LIMIT $2)",
                device_id, keep,
            )


async def list_history(device_id: str, limit: int = 20) -> list[dict[str, Any]]:
    assert _pool is not None
    rows = await _pool.fetch(
        "SELECT name, latitude, longitude, created_at FROM search_history "
        "WHERE device_id = $1 ORDER BY created_at DESC LIMIT $2",
        device_id, limit,
    )
    return [
        {
            "name": r["name"],
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
