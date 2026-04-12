"""
Advanced Memory Skill v2
Features: episodic + working memory, Ebbinghaus decay curves,
          token-overlap semantic search, importance scoring,
          memory consolidation, tag-based retrieval.
"""
from __future__ import annotations

import hashlib
import math
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from agentforge.skills.base import BaseSkill, SkillCategory, SkillConfig


@dataclass
class MemoryEntry:
    id: str
    content: str
    metadata: dict
    timestamp: float
    access_count: int = 0
    importance: float = 0.5
    tags: list = field(default_factory=list)

    def decay_score(self, now: float, half_life_hours: float = 24.0) -> float:
        hours_old = (now - self.timestamp) / 3600
        decay = math.exp(-0.693 * hours_old / half_life_hours)
        return self.importance * decay * (1 + 0.1 * self.access_count)


class MemorySkill(BaseSkill):
    name = "memory"
    description = (
        "Advanced memory management: store, retrieve, search, and consolidate memories "
        "with importance scoring, Ebbinghaus decay, and semantic tag search."
    )
    category = SkillCategory.MEMORY
    version = "2.0.0"
    tags = ["memory", "recall", "storage", "episodic", "working-memory"]

    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["store", "retrieve", "search", "forget", "consolidate", "list", "stats"],
            },
            "content": {"type": "string"},
            "query": {"type": "string"},
            "memory_id": {"type": "string"},
            "importance": {"type": "number", "minimum": 0, "maximum": 1},
            "tags": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer", "default": 10},
            "min_score": {"type": "number", "default": 0.1},
        },
        "required": ["action"],
    }

    def __init__(self):
        super().__init__(SkillConfig(enable_cache=False, max_retries=1))
        self._memories: dict[str, MemoryEntry] = {}
        self._working_memory: list[str] = []
        self._working_memory_limit = 7

    def _gen_id(self, content: str) -> str:
        return hashlib.sha256(f"{content}{time.time()}".encode()).hexdigest()[:12]

    def _similarity(self, a: str, b: str) -> float:
        tokens_a = set(a.lower().split())
        tokens_b = set(b.lower().split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        jaccard = len(intersection) / len(union)
        phrase_bonus = 0.3 if a.lower()[:30] in b.lower() or b.lower()[:30] in a.lower() else 0
        return min(1.0, jaccard + phrase_bonus)

    def _store(self, content: str, importance: float, tags: list, metadata: dict) -> dict:
        mem_id = self._gen_id(content)
        entry = MemoryEntry(
            id=mem_id, content=content, metadata=metadata,
            timestamp=time.time(), importance=max(0.0, min(1.0, importance)), tags=tags,
        )
        self._memories[mem_id] = entry
        self._working_memory.append(mem_id)
        if len(self._working_memory) > self._working_memory_limit:
            oldest_id = self._working_memory.pop(0)
            if oldest_id in self._memories and self._memories[oldest_id].importance < 0.3:
                del self._memories[oldest_id]
        return {"id": mem_id, "stored": True, "importance": importance}

    def _search(self, query: str, limit: int, min_score: float) -> list[dict]:
        now = time.time()
        scored = []
        for mem in self._memories.values():
            sim = self._similarity(query, mem.content)
            tag_bonus = 0.2 if any(query.lower() in t.lower() for t in mem.tags) else 0
            combined = sim + tag_bonus
            decay = mem.decay_score(now)
            final = combined * 0.7 + decay * 0.3
            if final >= min_score:
                scored.append((final, mem))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, mem in scored[:limit]:
            mem.access_count += 1
            d = asdict(mem)
            d["relevance_score"] = round(score, 4)
            results.append(d)
        return results

    async def _execute(
        self,
        action: str,
        content: str = "",
        query: str = "",
        memory_id: str = "",
        importance: float = 0.5,
        tags: Optional[list] = None,
        limit: int = 10,
        min_score: float = 0.1,
        metadata: Optional[dict] = None,
        **kwargs,
    ) -> Any:
        tags = tags or []
        metadata = metadata or {}

        match action:
            case "store":
                return self._store(content, importance, tags, metadata)
            case "retrieve":
                entry = self._memories.get(memory_id)
                if not entry:
                    return {"error": f"Memory '{memory_id}' not found"}
                entry.access_count += 1
                entry.importance = min(1.0, entry.importance + 0.05)
                return asdict(entry)
            case "search":
                return {"results": self._search(query, limit, min_score)}
            case "forget":
                if memory_id in self._memories:
                    del self._memories[memory_id]
                    return {"forgotten": True, "id": memory_id}
                return {"error": "Memory not found"}
            case "consolidate":
                now = time.time()
                to_remove = [
                    mid for mid, mem in self._memories.items()
                    if mem.decay_score(now, 48) < 0.05 and mid not in self._working_memory
                ]
                for mid in to_remove:
                    del self._memories[mid]
                return {"consolidated": True, "removed": len(to_remove), "remaining": len(self._memories)}
            case "list":
                now = time.time()
                mems = sorted(self._memories.values(), key=lambda m: m.decay_score(now), reverse=True)
                return {"memories": [asdict(m) for m in mems[:limit]], "working_memory": self._working_memory}
            case "stats":
                importances = [m.importance for m in self._memories.values()]
                return {
                    "total": len(self._memories),
                    "working_memory_size": len(self._working_memory),
                    "avg_importance": round(sum(importances) / max(len(importances), 1), 3),
                    "all_tags": list({t for m in self._memories.values() for t in m.tags}),
                }
            case _:
                return {"error": f"Unknown action: {action}"}
