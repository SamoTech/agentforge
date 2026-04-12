"""Base skill interface — every skill inherits from BaseSkill."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class SkillInput:
    data: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)   # injected memory/context
    agent_id: str | None = None
    task_id: str | None = None


@dataclass
class SkillOutput:
    data: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None
    tokens_used: int = 0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    # convenience shorthand
    @property
    def result(self) -> Any:
        return self.data.get("result")

    @classmethod
    def fail(cls, error: str) -> "SkillOutput":
        return cls(success=False, error=error)


class BaseSkill(ABC):
    """Abstract base for all AgentForge skills."""

    # ── Metadata (required on every subclass) ─────────────────────────────
    name: str                      # unique slug, e.g. "web_search"
    description: str               # one-liner shown in discovery
    category: str                  # perception | code | web | data | communication …
    tags: list[str] = []           # searchable labels
    level: str = "basic"           # basic | intermediate | advanced
    stability: str = "stable"      # stable | experimental | deprecated
    input_schema: dict  = {}       # JSON-Schema style {field: {type, required, description}}
    output_schema: dict = {}       # same for outputs
    requires_llm: bool = False     # needs an LLM call
    requires_network: bool = False # makes external HTTP requests

    @abstractmethod
    async def execute(self, inp: SkillInput) -> SkillOutput:
        """Run the skill. Must be async."""
        ...

    async def __call__(self, inp: SkillInput) -> SkillOutput:
        t0 = time.perf_counter()
        out = await self.execute(inp)
        out.latency_ms = (time.perf_counter() - t0) * 1000
        return out

    def meta(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "level": self.level,
            "stability": self.stability,
            "requires_llm": self.requires_llm,
            "requires_network": self.requires_network,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }
