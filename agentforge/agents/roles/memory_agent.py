"""Memory Agent — manages context retrieval and injection."""
from __future__ import annotations
from typing import Any
from agentforge.agents.base import BaseAgent, AgentResult
from agentforge.core.memory.long_term import LongTermMemory
from agentforge.core.memory.short_term import ShortTermMemory


class MemoryAgent(BaseAgent):
    role = 'memory'
    system_prompt = (
        'You are a memory management agent. Your job is to retrieve relevant context, '
        'store important information, and provide concise memory summaries to other agents.'
    )

    def __init__(self, session_id: str = 'default', **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.short_term = ShortTermMemory(session_id=session_id)
        self.long_term = LongTermMemory()

    async def run(self, task: str, **kwargs: Any) -> AgentResult:
        """Retrieve relevant memory context for a task."""
        # Search long-term memory for relevant context
        memories = await self.long_term.search(task, k=5)
        context = '\n'.join(f'- {m}' for m in memories) if memories else 'No relevant prior context.'

        # Store task in short-term memory
        await self.short_term.store(f'task: {task}')

        result = await self.chat(f'Summarize relevant context for this task: {task}\n\nAvailable memories:\n{context}')
        return AgentResult(output=result.output, token_usage=result.token_usage,
                           metadata={'memories_found': len(memories)})

    async def remember(self, content: str, metadata: dict | None = None) -> None:
        await self.long_term.store(content, metadata=metadata or {})

    async def recall(self, query: str, k: int = 5) -> list[str]:
        return await self.long_term.search(query, k=k)
