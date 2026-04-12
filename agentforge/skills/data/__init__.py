"""
Data Skills sub-package.
Skills for data analysis, transformation, database queries, and processing.
All implementations live in agentforge/skills/catalog/ and are
auto-discovered by the registry.
"""
from agentforge.skills.registry import registry

def get_data_skills():
    from agentforge.skills.base import SkillCategory
    return registry.list_by_category(SkillCategory.DATA)

__all__ = ["get_data_skills"]
