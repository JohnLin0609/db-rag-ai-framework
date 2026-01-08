from __future__ import annotations

from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(settings.db_url, pool_pre_ping=True)


def run_query(sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    engine = get_engine()
    with engine.connect() as connection:
        result = connection.execute(text(sql), params or {})
        rows = result.fetchmany(settings.max_result_rows)
        columns = list(result.keys())
    data = [dict(zip(columns, row)) for row in rows]
    return {"columns": columns, "rows": data}
