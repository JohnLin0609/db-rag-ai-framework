from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(key)
    if value is None:
        return default
    return value


def _env_bool(key: str, default: bool = False) -> bool:
    value = _env(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(key: str, default: int) -> int:
    value = _env(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    value = _env(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_csv(key: str) -> list[str]:
    value = _env(key)
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _build_db_url(
    dialect: str,
    driver: str,
    user: str,
    password: str,
    host: str,
    port: str,
    database: str,
) -> str:
    if dialect == "sqlite":
        path = database or "./app.db"
        return f"sqlite:///{path}"
    driver_part = f"+{driver}" if driver else ""
    auth = ""
    if user:
        auth = user
        if password:
            auth += f":{password}"
        auth += "@"
    host_part = host or "localhost"
    port_part = f":{port}" if port else ""
    db_part = f"/{database}" if database else ""
    return f"{dialect}{driver_part}://{auth}{host_part}{port_part}{db_part}"


@dataclass(frozen=True)
class Settings:
    app_name: str
    host: str
    port: int
    debug: bool

    db_url: str
    db_schema: str
    db_tables_allowlist: list[str]
    db_tables_denylist: list[str]
    max_result_rows: int

    schema_cache_ttl_seconds: int
    schema_max_tables: int
    schema_max_columns: int
    schema_max_candidates: int

    ollama_base_url: str
    ollama_model: str
    ollama_embedding_model: str
    ollama_timeout_seconds: int
    ollama_temperature: float

    rag_enabled: bool
    rag_store_path: str
    rag_top_k: int
    rag_max_chunk_chars: int

    memory_max_messages: int

    @classmethod
    def load(cls) -> "Settings":
        db_url = _env("DB_URL")
        if not db_url:
            db_url = _build_db_url(
                dialect=_env("DB_DIALECT", "postgresql"),
                driver=_env("DB_DRIVER", "psycopg2"),
                user=_env("DB_USER", "postgres"),
                password=_env("DB_PASSWORD", "postgres"),
                host=_env("DB_HOST", "localhost"),
                port=_env("DB_PORT", "5432"),
                database=_env("DB_NAME", "postgres"),
            )

        return cls(
            app_name=_env("APP_NAME", "db-ai"),
            host=_env("APP_HOST", "0.0.0.0"),
            port=_env_int("APP_PORT", 8000),
            debug=_env_bool("APP_DEBUG", False),
            db_url=db_url,
            db_schema=_env("DB_SCHEMA", "public"),
            db_tables_allowlist=_env_csv("DB_TABLES_ALLOWLIST"),
            db_tables_denylist=_env_csv("DB_TABLES_DENYLIST"),
            max_result_rows=_env_int("MAX_RESULT_ROWS", 200),
            schema_cache_ttl_seconds=_env_int("SCHEMA_CACHE_TTL_SECONDS", 300),
            schema_max_tables=_env_int("SCHEMA_MAX_TABLES", 200),
            schema_max_columns=_env_int("SCHEMA_MAX_COLUMNS", 40),
            schema_max_candidates=_env_int("SCHEMA_MAX_CANDIDATES", 30),
            ollama_base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=_env("OLLAMA_MODEL", "llama3.1"),
            ollama_embedding_model=_env("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
            ollama_timeout_seconds=_env_int("OLLAMA_TIMEOUT_SECONDS", 120),
            ollama_temperature=_env_float("OLLAMA_TEMPERATURE", 0.2),
            rag_enabled=_env_bool("RAG_ENABLED", False),
            rag_store_path=_env("RAG_STORE_PATH", "./rag_store.json"),
            rag_top_k=_env_int("RAG_TOP_K", 4),
            rag_max_chunk_chars=_env_int("RAG_MAX_CHUNK_CHARS", 1000),
            memory_max_messages=_env_int("MEMORY_MAX_MESSAGES", 12),
        )


settings = Settings.load()
