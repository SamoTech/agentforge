"""
Communication Skills sub-package.
Skills for email, messaging, notifications, and webhooks.
All implementations live in agentforge/skills/catalog/ and are
auto-discovered by the registry.
"""
from agentforge.skills.registry import registry

def get_communication_skills():
    from agentforge.skills.base import SkillCategory
    return registry.list_by_category(SkillCategory.COMMUNICATION)

__all__ = ["get_communication_skills"]
