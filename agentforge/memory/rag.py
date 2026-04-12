"""RAG Pipeline — retrieval-augmented generation with ChromaDB + OpenAI."""
from __future__ import annotations
from agentforge.memory.long_term import LongTermMemory
from agentforge.core.logger import logger


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline.

    Flow:
        1. Embed the query
        2. Retrieve top-k docs from LongTermMemory
        3. Build a context-enriched prompt
        4. Call LLM and return grounded answer
    """

    def __init__(self, user_id: str, model: str = "gpt-4o-mini") -> None:
        self.memory = LongTermMemory(user_id)
        self.model  = model

    async def ingest(self, texts: list[str], metadatas: list[dict] | None = None) -> list[str]:
        """Ingest documents into the user's long-term memory."""
        items = [
            {"text": t, "metadata": (metadatas[i] if metadatas else {})}
            for i, t in enumerate(texts)
        ]
        ids = await self.memory.add_many(items)
        logger.info("rag_ingest", user=self.memory.user_id, count=len(ids))
        return ids

    async def query(
        self,
        question: str,
        top_k: int = 5,
        system_prompt: str | None = None,
    ) -> dict:
        """Answer a question using retrieved context."""
        # 1. Retrieve
        hits = await self.memory.query(question, top_k=top_k)
        if not hits:
            context = "No relevant documents found in memory."
        else:
            context = "\n\n".join(
                f"[Doc {i+1}] {h['text']}" for i, h in enumerate(hits)
            )

        # 2. Build prompt
        default_system = (
            "You are a helpful AI assistant. Answer the user's question using ONLY "
            "the provided context. If the context does not contain the answer, say so."
        )
        messages = [
            {"role": "system", "content": system_prompt or default_system},
            {"role": "user",   "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ]

        # 3. Generate
        try:
            from openai import AsyncOpenAI
            from agentforge.core.config import settings
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
            )
            answer = resp.choices[0].message.content or ""
            tokens = resp.usage.total_tokens
        except Exception as e:
            answer = f"LLM error: {e}"
            tokens = 0

        return {
            "answer":    answer,
            "sources":   hits,
            "tokens":    tokens,
            "model":     self.model,
        }

    async def chat(
        self,
        messages: list[dict],
        top_k: int = 5,
    ) -> dict:
        """Multi-turn RAG chat — retrieves context for the latest user message."""
        user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        hits     = await self.memory.query(user_msg, top_k=top_k)
        ctx      = "\n\n".join(f"[Doc {i+1}] {h['text']}" for i, h in enumerate(hits))
        augmented = [
            {"role": "system", "content": f"Relevant context:\n{ctx}\n\nAnswer based on this context when relevant."},
            *messages,
        ]
        from openai import AsyncOpenAI
        from agentforge.core.config import settings
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(model=self.model, messages=augmented)
        return {"answer": resp.choices[0].message.content, "sources": hits, "tokens": resp.usage.total_tokens}
