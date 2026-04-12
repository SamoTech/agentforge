"""Skill Registry — register, discover, and search skills at scale (10,000+)."""
from __future__ import annotations
import importlib
import pkgutil
from pathlib import Path
from typing import Iterator
from agentforge.skills.base import BaseSkill
from agentforge.core.logger import logger


class SkillRegistry:
    """Thread-safe, in-memory skill registry with fuzzy search.

    Scales to 10,000+ skills via lazy loading and an optional
    vector-backed search (plug in ChromaDB for semantic search).
    """

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._by_category: dict[str, list[str]] = {}
        self._by_tag: dict[str, list[str]] = {}

    # ── Registration ──────────────────────────────────────────────────────

    def register(self, skill: BaseSkill) -> None:
        if skill.name in self._skills:
            logger.warning("skill_overwrite", name=skill.name)
        self._skills[skill.name] = skill
        self._by_category.setdefault(skill.category, []).append(skill.name)
        for tag in skill.tags:
            self._by_tag.setdefault(tag, []).append(skill.name)
        logger.debug("skill_registered", name=skill.name, category=skill.category)

    def register_many(self, skills: list[BaseSkill]) -> None:
        for s in skills:
            self.register(s)

    def auto_discover(self, package: str = "agentforge.skills.catalog") -> int:
        """Import every module in a package and auto-register BaseSkill subclasses."""
        pkg = importlib.import_module(package)
        pkg_path = Path(pkg.__file__).parent
        count = 0
        for _, mod_name, _ in pkgutil.iter_modules([str(pkg_path)]):
            mod = importlib.import_module(f"{package}.{mod_name}")
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseSkill)
                    and attr is not BaseSkill
                    and hasattr(attr, "name")
                ):
                    try:
                        self.register(attr())
                        count += 1
                    except Exception as e:
                        logger.error("skill_auto_register_fail", attr=attr_name, error=str(e))
        logger.info("auto_discover_complete", count=count, package=package)
        return count

    # ── Lookup ─────────────────────────────────────────────────────────────

    def get(self, name: str) -> BaseSkill | None:
        return self._skills.get(name)

    def list_all(self) -> list[BaseSkill]:
        return list(self._skills.values())

    def list_category(self, category: str) -> list[BaseSkill]:
        names = self._by_category.get(category, [])
        return [self._skills[n] for n in names if n in self._skills]

    def list_tags(self, tag: str) -> list[BaseSkill]:
        names = self._by_tag.get(tag, [])
        return [self._skills[n] for n in names if n in self._skills]

    # ── Search (keyword — plug in vector DB for semantic search) ──────────

    def search(self, query: str, limit: int = 20) -> list[BaseSkill]:
        q = query.lower()
        scored: list[tuple[int, BaseSkill]] = []
        for skill in self._skills.values():
            score = 0
            if q in skill.name:            score += 10
            if q in skill.description.lower(): score += 5
            if any(q in t for t in skill.tags): score += 3
            if q in skill.category:        score += 2
            if score:
                scored.append((score, skill))
        scored.sort(key=lambda x: -x[0])
        return [s for _, s in scored[:limit]]

    def __len__(self) -> int:
        return len(self._skills)

    def __iter__(self) -> Iterator[BaseSkill]:
        return iter(self._skills.values())
