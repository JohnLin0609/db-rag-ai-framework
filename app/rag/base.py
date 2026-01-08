from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol


@dataclass
class VectorDocument:
    doc_id: str
    text: str
    metadata: dict[str, Any]


@dataclass
class VectorResult:
    doc_id: str
    text: str
    score: float
    metadata: dict[str, Any]


class VectorStore(Protocol):
    def add(self, documents: Iterable[VectorDocument]) -> None:
        raise NotImplementedError

    def search(self, query: str, top_k: int) -> list[VectorResult]:
        raise NotImplementedError
