from __future__ import annotations

import redis.asyncio as redis


async def get_flag(client: redis.Redis, key: str) -> bool:
    value = await client.get(key)
    return value == b"1"


async def set_flag(client: redis.Redis, key: str, enabled: bool) -> None:
    if enabled:
        await client.set(key, "1")
    else:
        await client.delete(key)
