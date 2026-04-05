from __future__ import annotations

from math import sqrt
from typing import Any

from maya.enums import MemoryTier
from maya.persistence import PersistenceStore


class MemoryManager:
    def __init__(
        self,
        store: PersistenceStore,
        session_id: str | None = None,
        model_client: Any | None = None,
        embedding_model: str = "",
        base_url: str = "",
    ):
        self.store = store
        self.session_id = session_id
        self.model_client = model_client
        self.embedding_model = embedding_model
        self.base_url = base_url
        self.working_memory: dict[str, dict[str, Any]] = {}

    def read(self, agent_id: str, tier: MemoryTier, key: str | None = None, session_id: str | None = None) -> Any:
        if tier == MemoryTier.WORKING:
            values = self.working_memory.get(agent_id, {})
            if key:
                return values.get(key)
            return [{"key": item_key, "value": item_value, "metadata": {}, "agent_id": agent_id} for item_key, item_value in values.items()]
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("session_id is required for non-working memory read")
        rows = self.store.read_memory(session_id=session_id, tier=tier, agent_id=agent_id, key=key)
        if key:
            return rows[0]["value"] if rows else None
        return rows

    def write(
        self,
        agent_id: str,
        tier: MemoryTier,
        key: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
        memory_permission: str | None = None,
    ) -> None:
        if memory_permission == "none":
            raise PermissionError("memory write permission denied")
        if tier == MemoryTier.WORKING:
            self.working_memory.setdefault(agent_id, {})[key] = value
            return
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("session_id is required for non-working memory write")
        if tier == MemoryTier.SEMANTIC:
            vector = metadata.get("vector") if metadata else None
            if vector is None:
                vector = self.model_client.embed(model=self.embedding_model, base_url=self.base_url, texts=[str(value)])[0]
            metadata = {**(metadata or {}), "vector": vector}
        self.store.write_memory(session_id, agent_id, tier, key, value, metadata)

    def query_semantic(self, session_id: str, query: str, limit: int = 3) -> list[dict[str, Any]]:
        query_vector = self.model_client.embed(model=self.embedding_model, base_url=self.base_url, texts=[query])[0]
        entries = self.store.read_memory(session_id=session_id, tier=MemoryTier.SEMANTIC, limit=200)
        scored = []
        for entry in entries:
            vector = entry.get("metadata", {}).get("vector")
            if not vector:
                continue
            scored.append((self._cosine_similarity(query_vector, vector), entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def clear_working_memory(self, agent_id: str) -> None:
        self.working_memory.pop(agent_id, None)

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = sqrt(sum(value * value for value in left))
        right_norm = sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
