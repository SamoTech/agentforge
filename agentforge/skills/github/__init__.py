"""
GitHub Skills sub-package.
Skills for GitHub repository, PR, issue, and CI management.
All implementations live in agentforge/skills/catalog/github_skill.py and are
auto-discovered by the registry.
"""
from agentforge.skills.registry import registry

def get_github_skills():
    from agentforge.skills.base import SkillCategory
    return registry.list_by_category(SkillCategory.GITHUB)

__all__ = ["get_github_skills"]
