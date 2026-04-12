"""Framework adapters — unified interface over LangChain, AutoGen, CrewAI, LlamaIndex."""
from agentforge.frameworks.adapters.langchain_adapter import LangChainAdapter
from agentforge.frameworks.adapters.autogen_adapter import AutoGenAdapter
from agentforge.frameworks.adapters.crewai_adapter import CrewAIAdapter
from agentforge.frameworks.adapters.llama_index_adapter import LlamaIndexAdapter

__all__ = [
    "LangChainAdapter",
    "AutoGenAdapter",
    "CrewAIAdapter",
    "LlamaIndexAdapter",
]
