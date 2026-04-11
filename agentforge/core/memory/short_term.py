"""Short-term memory — Redis-backed session context."""
from __future__ import annotations
import json, time
from agentforge.core.config import settings

class ShortTermMemory:
    """Session-scoped memory using Redis lists."""

    def __init__(self, session_id: str = 'default', max_items: int = 50):
        self.session_id = session_id
        self.max_items = max_items
        self._redis = None
        self._key = f'agentforge:stm:{session_id}'

    async def _get_redis(self):
        if not self._redis:
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def store(self, content: str, metadata: dict | None = None) -> None:
        r = await self._get_redis()
        item = json.dumps({'content': content, 'timestamp': time.time(), 'metadata': metadata or {}})
        await r.lpush(self._key, item)
        await r.ltrim(self._key, 0, self.max_items - 1)
        await r.expire(self._key, 86400)  # 24h TTL

    async def get_recent(self, n: int = 10) -> list[dict]:
        r = await self._get_redis()
        items = await r.lrange(self._key, 0, n - 1)
        return [json.loads(i) for i in items]

    async def clear(self) -> None:
        r = await self._get_redis()
        await r.delete(self._key)
