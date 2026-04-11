"""CrewAI framework adapter."""
from __future__ import annotations
from agentforge.skills.base import BaseSkill, SkillInput

class CrewAIAdapter:
    """Wraps AgentForge skills as CrewAI tools and assembles crews."""

    def skill_to_tool(self, skill: BaseSkill):
        """Convert a BaseSkill to a CrewAI BaseTool."""
        try:
            from crewai_tools import BaseTool
            import asyncio

            class _SkillTool(BaseTool):
                name: str = skill.name
                description: str = skill.description

                def _run(self, **kwargs) -> str:
                    result = asyncio.get_event_loop().run_until_complete(
                        skill.execute(SkillInput(data=kwargs))
                    )
                    return str(result.data) if result.success else f'Error: {result.error}'

            return _SkillTool()
        except ImportError:
            raise ImportError('crewai not installed. Run: pip install crewai crewai-tools')

    def build_crew(self, agents_skills: list[tuple[str, list[BaseSkill]]], task_description: str):
        """Build a CrewAI Crew from agent-skill pairings."""
        from crewai import Agent, Task, Crew
        crew_agents, crew_tasks = [], []
        for agent_name, skills in agents_skills:
            tools = [self.skill_to_tool(s) for s in skills]
            agent = Agent(role=agent_name, goal=f'Complete tasks using {agent_name} capabilities',
                          backstory=f'Expert {agent_name} agent.', tools=tools, verbose=True)
            crew_agents.append(agent)
            crew_tasks.append(Task(description=task_description, agent=agent, expected_output='Task result'))
        return Crew(agents=crew_agents, tasks=crew_tasks, verbose=True)
