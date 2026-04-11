"""Global skill registry — discover and manage installed skills."""
from __future__ import annotations
from agentforge.skills.base import BaseSkill

_registry: dict[str, type[BaseSkill]] = {}

def register(cls: type[BaseSkill]) -> type[BaseSkill]:
    """Decorator: register a skill class."""
    _registry[cls.name] = cls
    return cls

def get(name: str) -> type[BaseSkill] | None:
    return _registry.get(name)

def all_skills() -> dict[str, type[BaseSkill]]:
    return dict(_registry)

def list_names() -> list[str]:
    return sorted(_registry.keys())

def categories() -> dict[str, list[str]]:
    cats: dict[str, list[str]] = {}
    for name, cls in _registry.items():
        cats.setdefault(cls.category, []).append(name)
    return cats
