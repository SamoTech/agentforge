"""Base agent class — all agent roles inherit from this."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from openai import AsyncOpenAI
from agentforge.core.config import settings
from agentforge.skills.base import BaseSkill, SkillInput


@dataclass
class AgentMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class AgentResult:
    output: str
    skills_used: list[str] = field(default_factory=list)
    token_usage: int = 0
    metadata: dict = field(default_factory=dict)


class BaseAgent(ABC):
    role: str = 'base'
    system_prompt: str = 'You are a helpful AI agent.'

    def __init__(self, model: str | None = None, skills: list[BaseSkill] | None = None):
        self.model = model or settings.openai_default_model
        self.skills: dict[str, BaseSkill] = {s.name: s for s in (skills or [])}
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.memory: list[AgentMessage] = []

    def add_skill(self, skill: BaseSkill) -> None:
        self.skills[skill.name] = skill

    async def call_skill(self, name: str, **kwargs: Any) -> Any:
        skill = self.skills.get(name)
        if not skill:
            raise ValueError(f'Skill "{name}" not available on this agent')
        result = await skill.execute(SkillInput(data=kwargs))
        if not result.success:
            raise RuntimeError(f'Skill "{name}" failed: {result.error}')
        return result.data

    async def chat(self, user_input: str, extra_context: str = '') -> AgentResult:
        messages = [{'role': 'system', 'content': self.system_prompt}]
        if extra_context:
            messages.append({'role': 'system', 'content': f'Context: {extra_context}'})
        for m in self.memory[-10:]:
            messages.append({'role': m.role, 'content': m.content})
        messages.append({'role': 'user', 'content': user_input})

        response = await self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=0.3)
        output = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0

        self.memory.append(AgentMessage('user', user_input))
        self.memory.append(AgentMessage('assistant', output))
        return AgentResult(output=output, token_usage=tokens)

    @abstractmethod
    async def run(self, task: str, **kwargs: Any) -> AgentResult:
        ...
