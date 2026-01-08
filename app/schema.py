from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect

from app.config import settings
from app.db import get_engine


@dataclass
class TableInfo:
    name: str
    columns: list[str]
    foreign_keys: list[dict[str, Any]]


class SchemaCatalog:
    def __init__(self) -> None:
        self._cache: dict[str, Any] | None = None
        self._loaded_at: float = 0.0

    def _is_cache_valid(self) -> bool:
        if not self._cache:
            return False
        return (time.time() - self._loaded_at) < settings.schema_cache_ttl_seconds

    def refresh(self) -> dict[str, TableInfo]:
        inspector = inspect(get_engine())
        tables = inspector.get_table_names(schema=settings.db_schema)
        tables = self._filter_tables(tables)
        tables = tables[: settings.schema_max_tables]
        catalog: dict[str, TableInfo] = {}

        for table in tables:
            columns = inspector.get_columns(table, schema=settings.db_schema)
            column_names = [col["name"] for col in columns][: settings.schema_max_columns]
            fks = inspector.get_foreign_keys(table, schema=settings.db_schema)
            fk_entries: list[dict[str, Any]] = []
            for fk in fks:
                constrained = fk.get("constrained_columns") or []
                referred_table = fk.get("referred_table")
                referred_columns = fk.get("referred_columns") or []
                if not referred_table or not constrained or not referred_columns:
                    continue
                fk_entries.append(
                    {
                        "column": constrained[0],
                        "ref_table": referred_table,
                        "ref_column": referred_columns[0],
                    }
                )
            catalog[table] = TableInfo(
                name=table,
                columns=column_names,
                foreign_keys=fk_entries,
            )

        self._cache = catalog
        self._loaded_at = time.time()
        return catalog

    def get(self) -> dict[str, TableInfo]:
        if self._is_cache_valid():
            return self._cache or {}
        return self.refresh()

    def summarize(self, tables: list[str]) -> str:
        catalog = self.get()
        lines: list[str] = []
        for table in tables:
            info = catalog.get(table)
            if not info:
                continue
            column_str = ", ".join(info.columns)
            lines.append(f"- {info.name}({column_str})")
            for fk in info.foreign_keys:
                lines.append(
                    f"  - fk: {info.name}.{fk['column']} -> {fk['ref_table']}.{fk['ref_column']}"
                )
        return "\n".join(lines)

    def _filter_tables(self, tables: list[str]) -> list[str]:
        if settings.db_tables_allowlist:
            allowed = {name.lower() for name in settings.db_tables_allowlist}
            tables = [name for name in tables if name.lower() in allowed]
        if settings.db_tables_denylist:
            blocked = {name.lower() for name in settings.db_tables_denylist}
            tables = [name for name in tables if name.lower() not in blocked]
        return tables


schema_catalog = SchemaCatalog()
