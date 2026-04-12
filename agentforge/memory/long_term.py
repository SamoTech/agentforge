"""Long-term memory backed by ChromaDB — persistent, user-scoped vector store."""
from __future__ import annotations
import uuid
from agentforge.core.config import settings
from agentforge.core.logger import logger


class LongTermMemory:
    """Persistent vector memory using ChromaDB.

    Each user gets an isolated collection: {prefix}{user_id}
    Supports add, query (semantic search), delete, and count.
    """

    def __init__(self, user_id: str) -> None:
        self.user_id        = user_id
        self._collection    = None
        self._embed_fn      = None

    async def _init(self):
        if self._collection is not None:
            return
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from sentence_transformers import SentenceTransformer
        client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        col_name = f"{settings.chroma_collection_prefix}{self.user_id}"
        self._collection = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.debug("ltm_init", user=self.user_id, collection=col_name)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        return self._embed_model.encode(texts, normalize_embeddings=True).tolist()

    # ── Store ──────────────────────────────────────────────────────────────

    async def add(
        self,
        text: str,
        metadata: dict | None = None,
        doc_id: str | None = None,
    ) -> str:
        await self._init()
        doc_id = doc_id or str(uuid.uuid4())
        embedding = self._embed([text])[0]
        self._collection.add(
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata or {}],
        )
        logger.debug("ltm_add", user=self.user_id, doc_id=doc_id)
        return doc_id

    async def add_many(self, items: list[dict]) -> list[str]:
        """Batch insert. Each item: {text, metadata?, id?}"""
        await self._init()
        ids   = [i.get("id") or str(uuid.uuid4()) for i in items]
        texts = [i["text"] for i in items]
        metas = [i.get("metadata", {}) for i in items]
        embs  = self._embed(texts)
        self._collection.add(ids=ids, documents=texts, embeddings=embs, metadatas=metas)
        return ids

    # ── Retrieve ───────────────────────────────────────────────────────────

    async def query(
        self,
        text: str,
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        await self._init()
        embedding = self._embed([text])[0]
        kwargs: dict = {"query_embeddings": [embedding], "n_results": top_k}
        if where:
            kwargs["where"] = where
        results = self._collection.query(**kwargs)
        hits = []
        for i, doc_id in enumerate(results["ids"][0]):
            hits.append({
                "id":       doc_id,
                "text":     results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })
        return hits

    async def delete(self, doc_id: str) -> None:
        await self._init()
        self._collection.delete(ids=[doc_id])

    async def count(self) -> int:
        await self._init()
        return self._collection.count()
