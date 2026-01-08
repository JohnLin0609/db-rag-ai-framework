from __future__ import annotations

import re
from typing import Iterable

import sqlparse
from sqlparse.sql import Identifier, IdentifierList
from sqlparse.tokens import Keyword


def normalize_identifier(name: str) -> str:
    return name.strip().strip('"').split(".")[-1].lower()


def _extract_from_token(token) -> list[str]:
    if isinstance(token, IdentifierList):
        names = []
        for identifier in token.get_identifiers():
            real_name = identifier.get_real_name() or identifier.get_name() or ""
            names.append(normalize_identifier(real_name))
        return names
    if isinstance(token, Identifier):
        real_name = token.get_real_name() or token.get_name() or ""
        return [normalize_identifier(real_name)]
    return []


def extract_tables(sql: str) -> set[str]:
    tables: set[str] = set()
    parsed = sqlparse.parse(sql)
    for stmt in parsed:
        from_seen = False
        for token in stmt.tokens:
            if token.ttype is Keyword and token.value.upper() in {"FROM", "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN"}:
                from_seen = True
                continue
            if from_seen:
                tables.update(_extract_from_token(token))
                if token.ttype is Keyword:
                    from_seen = False
    return {t for t in tables if t}


def is_select_only(sql: str) -> bool:
    statements = sqlparse.parse(sql)
    if len(statements) != 1:
        return False
    statement_type = statements[0].get_type()
    return statement_type.upper() == "SELECT"


def strip_trailing_semicolon(sql: str) -> str:
    return sql.strip().rstrip(";")


def has_limit(sql: str) -> bool:
    return bool(re.search(r"\blimit\b", sql, flags=re.IGNORECASE))


def ensure_limit(sql: str, limit: int) -> str:
    if has_limit(sql):
        return sql
    return f"{sql.rstrip()} LIMIT {limit}"


def validate_sql(sql: str, allowed_tables: Iterable[str]) -> tuple[bool, str]:
    cleaned = strip_trailing_semicolon(sql)
    if not is_select_only(cleaned):
        return False, "Only SELECT queries are allowed."
    tables = extract_tables(cleaned)
    allowed = {normalize_identifier(name) for name in allowed_tables}
    disallowed = {name for name in tables if name not in allowed}
    if disallowed:
        return False, f"Disallowed tables detected: {', '.join(sorted(disallowed))}"
    return True, ""
