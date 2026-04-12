"""LlamaIndex adapter — wrap AgentForge skills as LlamaIndex FunctionTools."""
from __future__ import annotations
from typing import Any
from agentforge.skills.base import BaseSkill, SkillInput


class LlamaIndexAdapter:
    """Adapts AgentForge BaseSkill instances into LlamaIndex FunctionTool objects.

    Usage::

        from agentforge.frameworks.adapters.llama_index_adapter import LlamaIndexAdapter
        from agentforge.skills.catalog.web_search import WebSearchSkill

        tool = LlamaIndexAdapter.to_tool(WebSearchSkill())
        # tool is now a llama_index.core.tools.FunctionTool
    """

    @staticmethod
    def to_tool(skill: BaseSkill) -> Any:
        """Convert a single BaseSkill to a LlamaIndex FunctionTool."""
        try:
            from llama_index.core.tools import FunctionTool
        except ImportError as exc:
            raise ImportError(
                "llama-index-core is required for the LlamaIndex adapter. "
                "Install it with: pip install llama-index-core"
            ) from exc

        import asyncio

        async def _async_fn(**kwargs: Any) -> str:
            result = await skill.execute(SkillInput(data=kwargs))
            if not result.success:
                return f"Error: {result.error}"
            return str(result.data)

        def _sync_fn(**kwargs: Any) -> str:
            return asyncio.get_event_loop().run_until_complete(_async_fn(**kwargs))

        return FunctionTool.from_defaults(
            fn=_sync_fn,
            async_fn=_async_fn,
            name=skill.name,
            description=skill.description,
        )

    @staticmethod
    def to_tools(skills: list[BaseSkill]) -> list[Any]:
        """Convert a list of BaseSkill instances to LlamaIndex FunctionTools."""
        return [LlamaIndexAdapter.to_tool(s) for s in skills]

    @staticmethod
    def build_query_engine(skills: list[BaseSkill], llm: Any | None = None) -> Any:
        """Build a LlamaIndex ReActAgent backed by AgentForge skills.

        Args:
            skills: List of AgentForge skills to expose.
            llm:    Optional LlamaIndex LLM instance. Falls back to OpenAI default.

        Returns:
            A llama_index.core.agent.ReActAgent ready to run tasks.
        """
        try:
            from llama_index.core.agent import ReActAgent
        except ImportError as exc:
            raise ImportError(
                "llama-index-core is required. Install with: pip install llama-index-core"
            ) from exc

        tools = LlamaIndexAdapter.to_tools(skills)
        return ReActAgent.from_tools(tools, llm=llm, verbose=True)
