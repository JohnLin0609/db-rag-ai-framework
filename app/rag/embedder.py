from __future__ import annotations

from typing import Protocol

from app.llm import ollama_client


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class OllamaEmbedder:
    def embed(self, text: str) -> list[float]:
        return ollama_client.embed(text)
