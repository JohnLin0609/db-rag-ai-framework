from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

from app.rag.base import VectorDocument, VectorResult
from app.rag.embedder import Embedder, OllamaEmbedder


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class LocalVectorStore:
    def __init__(self, path: str, embedder: Embedder | None = None) -> None:
        self.path = Path(path)
        self.embedder = embedder or OllamaEmbedder()
        self._data: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._data = []
            return
        try:
            self._data = json.loads(self.path.read_text())
        except json.JSONDecodeError:
            self._data = []

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))

    def add(self, documents: Iterable[VectorDocument]) -> None:
        existing = {item["doc_id"]: item for item in self._data if "doc_id" in item}
        for doc in documents:
            embedding = self.embedder.embed(doc.text)
            existing[doc.doc_id] = {
                "doc_id": doc.doc_id,
                "text": doc.text,
                "embedding": embedding,
                "metadata": doc.metadata,
            }
        self._data = list(existing.values())
        self._persist()

    def search(self, query: str, top_k: int) -> list[VectorResult]:
        query_embedding = self.embedder.embed(query)
        scored: list[VectorResult] = []
        for item in self._data:
            score = _cosine_similarity(query_embedding, item.get("embedding", []))
            scored.append(
                VectorResult(
                    doc_id=item.get("doc_id", ""),
                    text=item.get("text", ""),
                    score=score,
                    metadata=item.get("metadata", {}),
                )
            )
        scored.sort(key=lambda result: result.score, reverse=True)
        return scored[:top_k]
