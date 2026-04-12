"""LangChain framework adapter — wraps AgentForge skills as LangChain tools."""
from __future__ import annotations
from typing import Any
from agentforge.skills.base import BaseSkill, SkillInput

class LangChainAdapter:
    """Converts AgentForge skills to LangChain BaseTool instances."""

    def skill_to_tool(self, skill: BaseSkill):
        """Wrap a BaseSkill as a LangChain StructuredTool."""
        try:
            from langchain.tools import StructuredTool

            async def _run(**kwargs: Any) -> str:
                result = await skill.execute(SkillInput(data=kwargs))
                return str(result.data) if result.success else f'Error: {result.error}'

            return StructuredTool.from_function(
                name=skill.name,
                description=skill.description,
                coroutine=_run,
            )
        except ImportError:
            raise ImportError('langchain not installed. Run: pip install langchain langchain-openai')

    def build_agent(self, skills: list[BaseSkill], model: str = 'gpt-4o', system_prompt: str = ''):
        """Build a LangChain OpenAI Functions agent with AgentForge skills as tools."""
        from langchain_openai import ChatOpenAI
        from langchain.agents import create_openai_functions_agent, AgentExecutor
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        tools = [self.skill_to_tool(s) for s in skills]
        llm = ChatOpenAI(model=model, temperature=0)
        prompt = ChatPromptTemplate.from_messages([
            ('system', system_prompt or 'You are a helpful AI agent.'),
            MessagesPlaceholder('chat_history', optional=True),
            ('human', '{input}'),
            MessagesPlaceholder('agent_scratchpad'),
        ])
        agent = create_openai_functions_agent(llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True)
