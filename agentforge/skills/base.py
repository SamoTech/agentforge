"""
AgentForge Advanced Skill Base
Provides: retry logic, streaming, telemetry, timeout, caching, rate-limiting
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class SkillCategory(str, Enum):
    CODE = "code"
    COMMUNICATION = "communication"
    DATA = "data"
    GITHUB = "github"
    PERCEPTION = "perception"
    SEARCH = "search"
    MEMORY = "memory"
    REASONING = "reasoning"
    FILESYSTEM = "filesystem"
    API = "api"


@dataclass
class SkillResult:
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    latency_ms: float = 0.0
    cached: bool = False
    tokens_used: int = 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "latency_ms": self.latency_ms,
            "cached": self.cached,
            "tokens_used": self.tokens_used,
        }


@dataclass
class SkillConfig:
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    enable_cache: bool = True
    cache_ttl_seconds: int = 300
    rate_limit_per_minute: int = 60
    stream: bool = False


class RateLimiter:
    def __init__(self, max_per_minute: int):
        self._max = max_per_minute
        self._calls: list[float] = []

    async def acquire(self):
        now = time.monotonic()
        self._calls = [c for c in self._calls if now - c < 60]
        if len(self._calls) >= self._max:
            wait = 60 - (now - self._calls[0])
            logger.warning(f"Rate limit hit, waiting {wait:.1f}s")
            await asyncio.sleep(wait)
        self._calls.append(time.monotonic())


class SkillCache:
    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}

    def _key(self, skill_name: str, params: dict) -> str:
        raw = f"{skill_name}:{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, skill_name: str, params: dict, ttl: int) -> Optional[Any]:
        key = self._key(skill_name, params)
        if key in self._store:
            value, ts = self._store[key]
            if time.monotonic() - ts < ttl:
                return value
            del self._store[key]
        return None

    def set(self, skill_name: str, params: dict, value: Any):
        key = self._key(skill_name, params)
        self._store[key] = (value, time.monotonic())

    def invalidate(self, skill_name: str):
        keys = [k for k in self._store if k.startswith(skill_name[:4])]
        for k in keys:
            del self._store[k]


_global_cache = SkillCache()


class BaseSkill(ABC):
    """
    Advanced base class for all AgentForge skills.
    All skills inherit from this and implement `_execute`.
    """

    name: str = "base_skill"
    description: str = "Base skill"
    category: SkillCategory = SkillCategory.API
    version: str = "1.0.0"
    tags: list[str] = []
    input_schema: dict = {}
    output_schema: dict = {}

    def __init__(self, config: Optional[SkillConfig] = None):
        self.config = config or SkillConfig()
        self._rate_limiter = RateLimiter(self.config.rate_limit_per_minute)
        self._cache = _global_cache
        self._call_count = 0
        self._error_count = 0
        self._total_latency = 0.0
        logger.info(f"Skill '{self.name}' v{self.version} initialized")

    @abstractmethod
    async def _execute(self, **kwargs) -> Any:
        """Core skill logic — implement in subclass."""
        ...

    async def execute(self, **kwargs) -> SkillResult:
        """
        Public entry point with retry, cache, rate-limit, timeout, telemetry.
        """
        start = time.monotonic()
        self._call_count += 1

        # Cache check
        if self.config.enable_cache:
            cached = self._cache.get(self.name, kwargs, self.config.cache_ttl_seconds)
            if cached is not None:
                return SkillResult(
                    success=True,
                    data=cached,
                    latency_ms=(time.monotonic() - start) * 1000,
                    cached=True,
                )

        # Rate limit
        await self._rate_limiter.acquire()

        # Retry loop
        last_error = None
        delay = self.config.retry_delay

        for attempt in range(self.config.max_retries + 1):
            try:
                result_data = await asyncio.wait_for(
                    self._execute(**kwargs),
                    timeout=self.config.timeout_seconds,
                )
                latency = (time.monotonic() - start) * 1000
                self._total_latency += latency

                if self.config.enable_cache:
                    self._cache.set(self.name, kwargs, result_data)

                logger.info(
                    f"[{self.name}] success attempt={attempt + 1} latency={latency:.1f}ms"
                )
                return SkillResult(
                    success=True,
                    data=result_data,
                    latency_ms=latency,
                    metadata={"attempt": attempt + 1},
                )

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.config.timeout_seconds}s"
                logger.warning(f"[{self.name}] timeout attempt={attempt + 1}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[{self.name}] error attempt={attempt + 1}: {e}")

            if attempt < self.config.max_retries:
                await asyncio.sleep(delay)
                delay *= self.config.retry_backoff

        self._error_count += 1
        return SkillResult(
            success=False,
            data=None,
            error=last_error,
            latency_ms=(time.monotonic() - start) * 1000,
        )

    async def stream(self, **kwargs) -> AsyncGenerator[str, None]:
        """Override for streaming skills."""
        result = await self.execute(**kwargs)
        yield str(result.data)

    def get_stats(self) -> dict:
        avg_latency = (
            self._total_latency / self._call_count if self._call_count else 0
        )
        return {
            "name": self.name,
            "version": self.version,
            "calls": self._call_count,
            "errors": self._error_count,
            "avg_latency_ms": round(avg_latency, 2),
            "error_rate": round(self._error_count / max(self._call_count, 1), 3),
        }

    def to_openai_tool(self) -> dict:
        """Export skill as OpenAI function-calling tool spec."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema or {"type": "object", "properties": {}},
            },
        }

    def to_langchain_tool(self):
        """Export as LangChain BaseTool."""
        try:
            from langchain.tools import StructuredTool
            return StructuredTool.from_function(
                coroutine=self._execute,
                name=self.name,
                description=self.description,
            )
        except ImportError:
            raise RuntimeError("langchain not installed")
