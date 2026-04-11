"""Executor Agent — executes a single task step using available skills."""
from __future__ import annotations
from typing import Any
from agentforge.agents.base import BaseAgent, AgentResult
from agentforge.skills.base import BaseSkill, SkillInput


class ExecutorAgent(BaseAgent):
    role = 'executor'
    system_prompt = (
        'You are an execution agent. You receive a task step and must complete it '
        'by calling the appropriate skill or reasoning through to an answer. '
        'Be concise and precise. Return only the result, no filler text.'
    )

    async def run(self, task: str, skill_name: str | None = None, **kwargs: Any) -> AgentResult:
        """Execute a task, optionally forcing a specific skill."""
        if skill_name and skill_name in self.skills:
            skill = self.skills[skill_name]
            skill_result = await skill.execute(SkillInput(data={'input': task, **kwargs}))
            if skill_result.success:
                return AgentResult(
                    output=str(skill_result.data),
                    skills_used=[skill_name],
                    metadata={'skill': skill_name},
                )
        # Fallback: LLM reasoning
        return await self.chat(task)
