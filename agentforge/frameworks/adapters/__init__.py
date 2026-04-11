"""Unified framework adapter interface."""
from agentforge.frameworks.adapters.langchain_adapter import LangChainAdapter
from agentforge.frameworks.adapters.autogen_adapter import AutoGenAdapter
from agentforge.frameworks.adapters.crewai_adapter import CrewAIAdapter

ADAPTERS = {'langchain': LangChainAdapter, 'autogen': AutoGenAdapter, 'crewai': CrewAIAdapter}

def get_adapter(framework: str):
    cls = ADAPTERS.get(framework)
    if not cls: raise ValueError(f'Unknown framework: {framework}. Available: {list(ADAPTERS)}')
    return cls()
