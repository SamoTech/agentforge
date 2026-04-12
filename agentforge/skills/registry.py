"""
Advanced Skill Registry
Features: hot reload, versioning, category filtering, health checks, OpenAI tool export
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import pkgutil
import sys
from pathlib import Path
from typing import Optional, Type

from agentforge.skills.base import BaseSkill, SkillCategory

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Central registry for all AgentForge skills.
    Supports: hot reload, versioning, category filtering, OpenAI tool export.
    """

    def __init__(self):
        self._skills: dict[str, Type[BaseSkill]] = {}
        self._instances: dict[str, BaseSkill] = {}
        self._loaded_modules: set[str] = set()

    def register(self, skill_class: Type[BaseSkill]) -> Type[BaseSkill]:
        """Register a skill class. Can be used as a decorator."""
        if not issubclass(skill_class, BaseSkill):
            raise TypeError(f"{skill_class} must inherit from BaseSkill")
        name = skill_class.name
        if name in self._skills:
            existing_ver = self._skills[name].version
            new_ver = skill_class.version
            if new_ver > existing_ver:
                logger.info(f"Upgrading skill '{name}' {existing_ver} -> {new_ver}")
            else:
                logger.debug(f"Skill '{name}' already registered, skipping")
                return skill_class
        self._skills[name] = skill_class
        logger.info(f"Registered skill: {name} v{skill_class.version}")
        return skill_class

    def get(self, name: str) -> BaseSkill:
        """Get a singleton instance of a skill by name."""
        if name not in self._skills:
            raise KeyError(
                f"Skill '{name}' not found. Available: {list(self._skills.keys())}"
            )
        if name not in self._instances:
            self._instances[name] = self._skills[name]()
        return self._instances[name]

    def get_class(self, name: str) -> Type[BaseSkill]:
        if name not in self._skills:
            raise KeyError(f"Skill '{name}' not found")
        return self._skills[name]

    def list_all(self) -> list[dict]:
        return [
            {
                "name": cls.name,
                "description": cls.description,
                "category": cls.category,
                "version": cls.version,
                "tags": cls.tags,
            }
            for cls in self._skills.values()
        ]

    def list_by_category(self, category: SkillCategory) -> list[dict]:
        return [s for s in self.list_all() if s["category"] == category]

    def search(self, query: str) -> list[dict]:
        query = query.lower()
        return [
            s
            for s in self.list_all()
            if query in s["name"].lower()
            or query in s["description"].lower()
            or any(query in t.lower() for t in s.get("tags", []))
        ]

    def to_openai_tools(self, names: Optional[list[str]] = None) -> list[dict]:
        """Export skills as OpenAI tool specs for function calling."""
        targets = names or list(self._skills.keys())
        return [
            self._skills[n].to_openai_tool()
            for n in targets
            if n in self._skills
        ]

    def auto_discover(self, package_path: Optional[str] = None):
        """Auto-discover and register all skills in the catalog."""
        if package_path is None:
            catalog_path = Path(__file__).parent / "catalog"
        else:
            catalog_path = Path(package_path)

        for module_info in pkgutil.iter_modules([str(catalog_path)]):
            module_name = f"agentforge.skills.catalog.{module_info.name}"
            if module_name in self._loaded_modules:
                continue
            try:
                module = importlib.import_module(module_name)
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseSkill)
                        and obj is not BaseSkill
                        and hasattr(obj, "name")
                        and obj.name != "base_skill"
                    ):
                        self.register(obj)
                self._loaded_modules.add(module_name)
            except Exception as e:
                logger.error(f"Failed to load skill module '{module_name}': {e}")

    def hot_reload(self, skill_name: str):
        """Reload a specific skill module from disk."""
        if skill_name in self._instances:
            del self._instances[skill_name]
        for mod_name in list(self._loaded_modules):
            if skill_name in mod_name:
                self._loaded_modules.discard(mod_name)
                if mod_name in sys.modules:
                    del sys.modules[mod_name]
        self.auto_discover()
        logger.info(f"Hot-reloaded skill: {skill_name}")

    def health_check(self) -> dict:
        stats = {}
        for name, instance in self._instances.items():
            stats[name] = instance.get_stats()
        return {
            "total_registered": len(self._skills),
            "total_instantiated": len(self._instances),
            "skill_stats": stats,
        }

    def unregister(self, name: str):
        self._skills.pop(name, None)
        self._instances.pop(name, None)
        logger.info(f"Unregistered skill: {name}")


# Global singleton
registry = SkillRegistry()
