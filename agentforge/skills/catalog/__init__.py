"""
AgentForge Skill Catalog
Auto-registers all skills in this package on import.
"""
from agentforge.skills.registry import registry

registry.auto_discover()

__all__ = ["registry"]
