from __future__ import annotations

import asyncio
from typing import Optional

import asyncpg

from src.shared.config.settings import load_settings


_pool: Optional[asyncpg.Pool] = None
_init_lock = asyncio.Lock()


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool
    async with _init_lock:
        if _pool is None:
            settings = load_settings()
            _pool = await asyncpg.create_pool(dsn=settings.db.dsn, min_size=1, max_size=5)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def ping() -> bool:
    pool = await init_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 as ok")
    return bool(row and row["ok"] == 1)


