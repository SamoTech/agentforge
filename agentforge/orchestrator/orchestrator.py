"""Central Orchestrator — routes tasks to the right agents and skills."""
from __future__ import annotations
import json
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
    1. Receives user task + optional conversation context
    2. Planner agent breaks it into steps (context-aware)
    3. Executor agents run each step using skills
    4. Memory agent injects relevant context
    5. Returns final result
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_default_model

    async def run(self, task: str, context: list[dict] | None = None) -> OrchestrationResult:
        """Run a task, optionally with conversation history context.

        Args:
            task:    The user's task or message.
            context: Optional list of prior conversation messages in
                     OpenAI message format: [{"role": ..., "content": ...}].
                     Injected into the planner and executor prompts so the
                     orchestrator is aware of prior conversation turns.
        """
        logger.info("orchestrator_run", task=task[:80], context_msgs=len(context or []))

        plan = await self._plan(task, context)
        logger.info("plan_created", steps=len(plan))

        results: list[str] = []
        skills_used: list[str] = []
        total_tokens = 0

        for step in plan:
            step_result, step_skills, tokens = await self._execute_step(step, task, context)
            results.append(step_result)
            skills_used.extend(step_skills)
            total_tokens += tokens

        final_output = await self._synthesize(task, results, context)

        cost = total_tokens * 0.000015  # gpt-4o approx cost per token
        return OrchestrationResult(
            output=final_output,
            skills_used=list(set(skills_used)),
            token_usage=total_tokens,
            cost_usd=cost,
        )

    async def _plan(self, task: str, context: list[dict] | None) -> list[str]:
        """Use Planner to decompose task into steps, injecting prior context."""
        system_msg = (
            "You are a task planner. "
            "Break the user task into 2-5 concrete steps. "
            "Return a JSON object with a single key 'steps' containing an array of step strings. "
            "Use the conversation history (if any) to understand what has already been done "
            "and avoid repeating work."
        )
        messages: list[dict] = [{"role": "system", "content": system_msg}]

        # Inject prior conversation turns so the planner has full context
        if context:
            messages.extend(context)

        messages.append({"role": "user", "content": task})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
        try:
            data = json.loads(response.choices[0].message.content)
            return data.get("steps", [task])
        except Exception:
            return [task]

    async def _execute_step(
        self,
        step: str,
        original_task: str,
        context: list[dict] | None,
    ) -> tuple[str, list[str], int]:
        """Execute a single plan step, aware of the original conversation context."""
        system_msg = (
            f"You are an executor agent completing one step of a larger task. "
            f'Original task: "{original_task}". '
            "Use the conversation history (if provided) to stay consistent with prior work."
        )
        messages: list[dict] = [{"role": "system", "content": system_msg}]

        if context:
            messages.extend(context)

        messages.append({"role": "user", "content": step})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
        )
        output = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        return output, ["llm_generate"], tokens

    async def _synthesize(
        self,
        task: str,
        step_results: list[str],
        context: list[dict] | None,
    ) -> str:
        """Synthesize all step results into final answer, context-aware."""
        combined = "\n\n".join(f"Step {i + 1}: {r}" for i, r in enumerate(step_results))
        system_msg = (
            "Synthesize the step results into a coherent final answer for the original task. "
            "Be concise, accurate, and consistent with any prior conversation context."
        )
        messages: list[dict] = [{"role": "system", "content": system_msg}]

        if context:
            messages.extend(context)

        messages.append({
            "role": "user",
            "content": f"Task: {task}\n\nStep results:\n{combined}",
        })

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content
