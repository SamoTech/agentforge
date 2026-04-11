"""RAG (Retrieval-Augmented Generation) — knowledge base search + LLM answer."""
from __future__ import annotations
from openai import AsyncOpenAI
from agentforge.core.config import settings
from agentforge.core.memory.long_term import LongTermMemory


class RAGPipeline:
    """Retrieve relevant chunks from vector DB, then generate an LLM answer."""

    def __init__(self, collection_name: str = 'knowledge_base'):
        self.memory = LongTermMemory(collection_name=collection_name)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def ingest(self, texts: list[str], metadatas: list[dict] | None = None) -> None:
        """Ingest documents into the vector store."""
        for i, text in enumerate(texts):
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            await self.memory.store(text, metadata=meta)

    async def answer(self, question: str, k: int = 5, system_prompt: str | None = None) -> dict:
        """Answer a question using retrieved context."""
        chunks = await self.memory.search(question, k=k)
        context = '\n\n---\n\n'.join(chunks) if chunks else 'No relevant context found.'

        messages = [
            {'role': 'system', 'content': system_prompt or 'Answer the question based strictly on the provided context. If the context does not contain enough information, say so clearly.'},
            {'role': 'user', 'content': f'Context:\n{context}\n\nQuestion: {question}'},
        ]
        response = await self.client.chat.completions.create(
            model=settings.openai_default_model,
            messages=messages,
            temperature=0.1,
        )
        return {
            'answer': response.choices[0].message.content,
            'chunks_used': len(chunks),
            'context': context,
        }
