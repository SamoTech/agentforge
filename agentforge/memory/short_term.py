"""Short-term memory backed by Redis — per-session, TTL-scoped."""
from __future__ import annotations
import json
from datetime import timedelta
from agentforge.core.config import settings
from agentforge.core.logger import logger


class ShortTermMemory:
    """Session-scoped memory stored in Redis with configurable TTL.

    Key schema:  agentforge:mem:session:{session_id}:messages  → Redis List
                 agentforge:mem:session:{session_id}:kv:{key}  → Redis String
    """

    DEFAULT_TTL = timedelta(hours=6)

    def __init__(self, session_id: str, ttl: timedelta | None = None) -> None:
        self.session_id = session_id
        self.ttl        = ttl or self.DEFAULT_TTL
        self._redis     = None  # lazy-init

    async def _client(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    # ── Message history ───────────────────────────────────────────────────

    async def add_message(self, role: str, content: str) -> None:
        r = await self._client()
        key = f"agentforge:mem:session:{self.session_id}:messages"
        msg = json.dumps({"role": role, "content": content})
        await r.rpush(key, msg)
        await r.expire(key, int(self.ttl.total_seconds()))
        logger.debug("stm_add_message", session=self.session_id, role=role)

    async def get_messages(self, last_n: int = 20) -> list[dict]:
        r = await self._client()
        key = f"agentforge:mem:session:{self.session_id}:messages"
        raw = await r.lrange(key, -last_n, -1)
        return [json.loads(m) for m in raw]

    async def clear_messages(self) -> None:
        r = await self._client()
        await r.delete(f"agentforge:mem:session:{self.session_id}:messages")

    # ── Key-value scratch space ────────────────────────────────────────────

    async def set(self, key: str, value: str) -> None:
        r = await self._client()
        rkey = f"agentforge:mem:session:{self.session_id}:kv:{key}"
        await r.set(rkey, value, ex=int(self.ttl.total_seconds()))

    async def get(self, key: str) -> str | None:
        r = await self._client()
        return await r.get(f"agentforge:mem:session:{self.session_id}:kv:{key}")

    async def delete(self, key: str) -> None:
        r = await self._client()
        await r.delete(f"agentforge:mem:session:{self.session_id}:kv:{key}")

    # ── Context window helper ─────────────────────────────────────────────

    async def get_context_window(self, last_n: int = 10) -> str:
        """Return messages formatted for LLM context injection."""
        msgs = await self.get_messages(last_n)
        return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in msgs)
