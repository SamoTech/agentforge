"""
Search Skills sub-package.
Skills for web search, web scraping, and information retrieval.
All implementations live in agentforge/skills/catalog/ and are
auto-discovered by the registry.
"""
from agentforge.skills.registry import registry

def get_search_skills():
    from agentforge.skills.base import SkillCategory
    return registry.list_by_category(SkillCategory.SEARCH)

__all__ = ["get_search_skills"]
