"""Central Orchestrator — routes tasks to the right agents and skills."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from openai import AsyncOpenAI
from agentforge.core.config import settings
from agentforge.core.logger import logger


@dataclass
class OrchestrationResult:
    output: str
    skills_used: list[str] = field(default_factory=list)
    token_usage: int = 0
    cost_usd: float = 0.0
    metadata: dict = field(default_factory=dict)


class Orchestrator:
    """
    Central brain that:
    1. Receives user task
    2. Planner agent breaks it into steps
    3. Executor agents run each step using skills
    4. Memory agent injects relevant context
    5. Returns final result
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_default_model

    async def run(self, task: str, context: dict | None = None) -> OrchestrationResult:
        logger.info('Orchestrator.run', task=task[:80])

        # Step 1: Plan
        plan = await self._plan(task)
        logger.info('Plan created', steps=len(plan))

        # Step 2: Execute each step
        results = []
        skills_used = []
        total_tokens = 0

        for step in plan:
            step_result, step_skills, tokens = await self._execute_step(step, task)
            results.append(step_result)
            skills_used.extend(step_skills)
            total_tokens += tokens

        # Step 3: Synthesize
        final_output = await self._synthesize(task, results)

        cost = total_tokens * 0.000015  # gpt-4o approx cost per token
        return OrchestrationResult(
            output=final_output,
            skills_used=list(set(skills_used)),
            token_usage=total_tokens,
            cost_usd=cost,
        )

    async def _plan(self, task: str) -> list[str]:
        """Use Planner to decompose task into steps."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {'role': 'system', 'content': 'You are a task planner. Break the user task into 2-5 concrete steps. Return a JSON array of step strings.'},
                {'role': 'user', 'content': task},
            ],
            response_format={'type': 'json_object'},
            temperature=0,
        )
        import json
        try:
            data = json.loads(response.choices[0].message.content)
            return data.get('steps', [task])
        except Exception:
            return [task]

    async def _execute_step(self, step: str, original_task: str) -> tuple[str, list[str], int]:
        """Execute a single plan step."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {'role': 'system', 'content': f'You are an executor agent. Complete this step as part of the larger task: "{original_task}"'},
                {'role': 'user', 'content': step},
            ],
            temperature=0.3,
        )
        output = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        return output, ['llm_generate'], tokens

    async def _synthesize(self, task: str, step_results: list[str]) -> str:
        """Synthesize all step results into final answer."""
        combined = '\n\n'.join(f'Step {i+1}: {r}' for i, r in enumerate(step_results))
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {'role': 'system', 'content': 'Synthesize the step results into a coherent final answer for the original task.'},
                {'role': 'user', 'content': f'Task: {task}\n\nStep results:\n{combined}'},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content
