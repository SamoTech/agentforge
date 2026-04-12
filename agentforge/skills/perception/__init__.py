"""
Perception Skills sub-package.
Skills for OCR, image analysis, audio transcription, and document parsing.
All implementations live in agentforge/skills/catalog/ and are
auto-discovered by the registry.
"""
from agentforge.skills.registry import registry

def get_perception_skills():
    from agentforge.skills.base import SkillCategory
    return registry.list_by_category(SkillCategory.PERCEPTION)

__all__ = ["get_perception_skills"]
