"""Long-term memory — ChromaDB vector store for semantic recall."""
from __future__ import annotations
from agentforge.core.config import settings

class LongTermMemory:
    """Semantic long-term memory backed by ChromaDB."""

    def __init__(self, collection_name: str = 'default'):
        self.collection_name = f'{settings.chroma_collection_prefix}{collection_name}'
        self._client = None
        self._collection = None

    def _get_client(self):
        if not self._client:
            try:
                import chromadb
                self._client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
                self._collection = self._client.get_or_create_collection(self.collection_name)
            except ImportError:
                raise ImportError('chromadb not installed. Run: pip install chromadb')
        return self._collection

    async def store(self, content: str, metadata: dict | None = None, doc_id: str | None = None) -> None:
        import uuid
        collection = self._get_client()
        collection.add(documents=[content], metadatas=[metadata or {}], ids=[doc_id or str(uuid.uuid4())])

    async def search(self, query: str, k: int = 5) -> list[str]:
        try:
            collection = self._get_client()
            results = collection.query(query_texts=[query], n_results=k)
            return results['documents'][0] if results['documents'] else []
        except Exception:
            return []

    async def delete(self, doc_id: str) -> None:
        collection = self._get_client()
        collection.delete(ids=[doc_id])
