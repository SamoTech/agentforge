"""Base classes for all AgentForge skills."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillInput:
    data: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillOutput:
    success: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0          # ← was missing; caused AttributeError on all LLM skills
    cost_usd: float = 0.0         # ← convenience field for billing

    @classmethod
    def fail(cls, error: str) -> "SkillOutput":
        """Shorthand for a failed output."""
        return cls(success=False, error=error)

    def __getattr__(self, name: str) -> Any:
        # Allow dot-access into .data for convenience (e.g. output.summary)
        _data = object.__getattribute__(self, "data")
        if name in _data:
            return _data[name]
        raise AttributeError(name)


class BaseSkill(ABC):
    """Every skill must inherit this and implement ``execute``."""

    name: str = ""
    description: str = ""
    category: str = "general"
    tags: list[str] = []
    level: str = "advanced"       # basic | intermediate | advanced
    stability: str = "stable"     # stable | experimental | deprecated
    requires_llm: bool = False
    requires_network: bool = False
    input_schema: dict = {}
    output_schema: dict = {}

    @abstractmethod
    async def execute(self, inp: SkillInput) -> SkillOutput:
        """Execute the skill asynchronously."""
        ...

    def to_dict(self) -> dict:
        return {
            "name":           self.name,
            "description":    self.description,
            "category":       self.category,
            "tags":           self.tags,
            "level":          self.level,
            "stability":      self.stability,
            "requires_llm":   self.requires_llm,
            "requires_network": self.requires_network,
            "input_schema":   self.input_schema,
            "output_schema":  self.output_schema,
        }

    def __repr__(self) -> str:
        return f"<Skill:{self.name} level={self.level}>"
