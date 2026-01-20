from __future__ import annotations

from contextlib import asynccontextmanager

import redis.asyncio as redis


@asynccontextmanager
async def redis_lock(client: redis.Redis, key: str, ttl: int = 60):
    acquired = await client.set(name=key, value="1", nx=True, ex=ttl)
    try:
        yield bool(acquired)
    finally:
        if acquired:
            await client.delete(key)
