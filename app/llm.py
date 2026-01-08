from __future__ import annotations

import json
from typing import Any

import requests

from app.config import settings


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.embedding_model = settings.ollama_embedding_model

    def chat(self, messages: list[dict[str, str]], temperature: float | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature or settings.ollama_temperature},
        }
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=settings.ollama_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        message = data.get("message", {})
        return message.get("content", "").strip()

    def embed(self, text: str) -> list[float]:
        payload = {"model": self.embedding_model, "prompt": text}
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json=payload,
            timeout=settings.ollama_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embedding", [])

    @staticmethod
    def safe_json(text: str) -> dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}


ollama_client = OllamaClient()
