from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque

from app.config import settings


class ConversationMemory:
    def __init__(self, max_messages: int | None = None) -> None:
        self.max_messages = max_messages or settings.memory_max_messages
        self._store: dict[str, Deque[dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=self.max_messages)
        )

    def add(self, session_id: str, role: str, content: str) -> None:
        if not session_id:
            return
        self._store[session_id].append({"role": role, "content": content})

    def get(self, session_id: str) -> list[dict[str, str]]:
        if not session_id:
            return []
        return list(self._store.get(session_id, []))
