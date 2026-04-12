"""
Code Skills sub-package.
Skills focused on code generation, execution, analysis, and transformation.
All implementations live in agentforge/skills/catalog/ and are
auto-discovered by the registry.
"""
from agentforge.skills.registry import registry

# Re-export code-category skills for convenience
def get_code_skills():
    from agentforge.skills.base import SkillCategory
    return registry.list_by_category(SkillCategory.CODE)

__all__ = ["get_code_skills"]
