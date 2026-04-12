"""
LlamaIndex Framework Adapter
Bridges AgentForge skills with LlamaIndex tools and query engines.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from agentforge.skills.base import BaseSkill
from agentforge.skills.registry import registry

logger = logging.getLogger(__name__)


class LlamaIndexAdapter:
    """
    Wraps AgentForge skills as LlamaIndex FunctionTool objects.
    Enables AgentForge skills to be used inside LlamaIndex agents and pipelines.

    Usage:
        adapter = LlamaIndexAdapter()
        tools = adapter.get_tools(["web_search", "web_scraper"])
        agent = ReActAgent.from_tools(tools, llm=llm)
    """

    def __init__(self):
        try:
            import llama_index  # noqa: F401
            self._available = True
        except ImportError:
            self._available = False
            logger.warning("llama_index not installed. Run: pip install llama-index")

    def _check_available(self):
        if not self._available:
            raise RuntimeError(
                "llama_index is not installed. "
                "Install with: pip install llama-index"
            )

    def skill_to_function_tool(self, skill: BaseSkill):
        """
        Convert a single AgentForge BaseSkill to a LlamaIndex FunctionTool.
        """
        self._check_available()
        from llama_index.core.tools import FunctionTool
        import asyncio

        skill_name = skill.name
        skill_desc = skill.description

        async def _tool_fn(**kwargs) -> str:
            result = await skill.execute(**kwargs)
            if result.success:
                return str(result.data)
            return f"Error: {result.error}"

        def _sync_tool_fn(**kwargs) -> str:
            return asyncio.get_event_loop().run_until_complete(_tool_fn(**kwargs))

        return FunctionTool.from_defaults(
            fn=_sync_tool_fn,
            async_fn=_tool_fn,
            name=skill_name,
            description=skill_desc,
        )

    def get_tools(self, skill_names: Optional[list[str]] = None) -> list:
        """
        Get LlamaIndex FunctionTool objects for the specified skills.
        If skill_names is None, returns tools for all registered skills.
        """
        self._check_available()
        names = skill_names or [s["name"] for s in registry.list_all()]
        tools = []
        for name in names:
            try:
                skill = registry.get(name)
                tools.append(self.skill_to_function_tool(skill))
            except Exception as e:
                logger.error(f"Failed to convert skill '{name}' to LlamaIndex tool: {e}")
        return tools

    def create_query_engine_tool(self, skill_name: str, description: Optional[str] = None):
        """
        Wrap a skill as a LlamaIndex QueryEngineTool for use in agent pipelines.
        """
        self._check_available()
        from llama_index.core.tools import QueryEngineTool, ToolMetadata

        skill = registry.get(skill_name)

        class SkillQueryEngine:
            def query(self, query_str: str) -> Any:
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(
                    skill.execute(query=query_str)
                )
                return result.data if result.success else result.error

        return QueryEngineTool(
            query_engine=SkillQueryEngine(),
            metadata=ToolMetadata(
                name=skill_name,
                description=description or skill.description,
            ),
        )

    def create_react_agent(self, skill_names: Optional[list[str]] = None, llm=None):
        """
        Create a LlamaIndex ReAct agent backed by AgentForge skills.
        """
        self._check_available()
        from llama_index.core.agent import ReActAgent

        tools = self.get_tools(skill_names)
        return ReActAgent.from_tools(tools, llm=llm, verbose=True)
