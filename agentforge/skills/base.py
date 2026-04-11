"""BaseSkill abstract class — all skills implement this contract."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillInput:
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillOutput:
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any, **meta) -> 'SkillOutput':
        return cls(success=True, data=data, metadata=meta)

    @classmethod
    def fail(cls, error: str, **meta) -> 'SkillOutput':
        return cls(success=False, error=error, metadata=meta)


class BaseSkill(ABC):
    name: str = 'base_skill'
    description: str = 'A base skill'
    category: str = 'general'
    version: str = '1.0.0'

    @abstractmethod
    async def execute(self, input: SkillInput) -> SkillOutput:
        ...

    def __repr__(self):
        return f'<Skill name={self.name} category={self.category}>'
