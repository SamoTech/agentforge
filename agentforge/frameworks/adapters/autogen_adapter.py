"""AutoGen framework adapter."""
from __future__ import annotations
from agentforge.skills.base import BaseSkill, SkillInput

class AutoGenAdapter:
    """Integrates AgentForge skills into AutoGen agents as function_map."""

    def build_function_map(self, skills: list[BaseSkill]) -> dict:
        """Create an AutoGen-compatible function_map from a list of skills."""
        import asyncio
        function_map = {}
        for skill in skills:
            def make_fn(s: BaseSkill):
                def fn(**kwargs):
                    result = asyncio.get_event_loop().run_until_complete(
                        s.execute(SkillInput(data=kwargs))
                    )
                    return str(result.data) if result.success else f'Error: {result.error}'
                fn.__name__ = s.name
                fn.__doc__ = s.description
                return fn
            function_map[skill.name] = make_fn(skill)
        return function_map

    def build_assistant(self, skills: list[BaseSkill], name: str = 'AgentForge Assistant',
                         system_message: str = ''):
        """Build an AutoGen AssistantAgent with AgentForge skill functions."""
        try:
            from autogen import AssistantAgent
            return AssistantAgent(
                name=name,
                system_message=system_message or 'You are a helpful AI assistant.',
                function_map=self.build_function_map(skills),
            )
        except ImportError:
            raise ImportError('pyautogen not installed. Run: pip install pyautogen')
