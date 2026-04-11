"""Planner Agent — decomposes complex tasks into executable plans."""
from __future__ import annotations
import json
from typing import Any
from agentforge.agents.base import BaseAgent, AgentResult


class PlannerAgent(BaseAgent):
    role = 'planner'
    system_prompt = (
        'You are an expert task planner. Given a complex task, break it down into '
        'clear, actionable steps. Each step should be specific and executable. '
        'Return a JSON object with a "steps" array and a "reasoning" string.'
    )

    async def run(self, task: str, **kwargs: Any) -> AgentResult:
        result = await self.chat(task)
        try:
            data = json.loads(result.output)
            steps = data.get('steps', [task])
            reasoning = data.get('reasoning', '')
        except (json.JSONDecodeError, AttributeError):
            steps = [task]
            reasoning = ''
        return AgentResult(
            output=json.dumps({'steps': steps, 'reasoning': reasoning}),
            token_usage=result.token_usage,
            metadata={'steps': steps, 'reasoning': reasoning},
        )

    async def create_plan(self, task: str) -> list[str]:
        result = await self.run(task)
        return result.metadata.get('steps', [task])
