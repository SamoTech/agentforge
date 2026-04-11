"""Specialist Agent — domain expert (code, research, data, etc.)."""
from __future__ import annotations
from typing import Any, Literal
from agentforge.agents.base import BaseAgent, AgentResult

Domain = Literal['code', 'research', 'data', 'writing', 'math', 'security']

SYSTEM_PROMPTS: dict[str, str] = {
    'code': 'You are an expert software engineer. Write clean, efficient, well-documented code. Always include error handling.',
    'research': 'You are a research analyst. Provide thorough, cited analysis. Be objective and evidence-based.',
    'data': 'You are a data scientist. Analyze data carefully, show your reasoning, and provide actionable insights.',
    'writing': 'You are a professional writer and editor. Write clearly, engagingly, and adapt tone to context.',
    'math': 'You are a mathematician. Solve problems step by step, showing all work. Verify your answers.',
    'security': 'You are a cybersecurity expert. Identify vulnerabilities, suggest mitigations, follow OWASP guidelines.',
}


class SpecialistAgent(BaseAgent):
    role = 'specialist'

    def __init__(self, domain: Domain = 'code', **kwargs):
        super().__init__(**kwargs)
        self.domain = domain
        self.system_prompt = SYSTEM_PROMPTS.get(domain, SYSTEM_PROMPTS['code'])

    async def run(self, task: str, **kwargs: Any) -> AgentResult:
        return await self.chat(task)
