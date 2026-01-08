from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.db import run_query
from app.llm import ollama_client
from app.memory import ConversationMemory
from app.prompts import ANSWER_PROMPT, SQL_GENERATION_PROMPT, SYSTEM_PROMPT, TABLE_SELECTION_PROMPT
from app.rag import LocalVectorStore, VectorDocument
from app.schema import schema_catalog
from app.sql import ensure_limit, strip_trailing_semicolon, validate_sql


@dataclass
class ChatResult:
    answer: str
    sql: str
    data: dict[str, Any]
    debug: dict[str, Any]


def _tokenize(text: str) -> set[str]:
    return {token for token in re.split(r"\W+", text.lower()) if token}


def _identifier_tokens(name: str) -> set[str]:
    parts = re.split(r"[_\W]+", name.lower())
    return {part for part in parts if part}


def _safe_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*", "", cleaned)
        cleaned = cleaned.strip("`\n ")
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


class ChatPipeline:
    def __init__(self) -> None:
        self.memory = ConversationMemory()
        self.rag_store = LocalVectorStore(settings.rag_store_path) if settings.rag_enabled else None

    def _candidate_tables(self, question: str) -> list[str]:
        catalog = schema_catalog.get()
        question_tokens = _tokenize(question)
        scored: list[tuple[str, int]] = []
        for table, info in catalog.items():
            table_tokens = _identifier_tokens(table)
            score = len(question_tokens & table_tokens) * 3
            for column in info.columns:
                column_tokens = _identifier_tokens(column)
                score += len(question_tokens & column_tokens)
            if score > 0:
                scored.append((table, score))
        if not scored:
            return list(catalog.keys())[: settings.schema_max_candidates]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [table for table, _ in scored[: settings.schema_max_candidates]]

    def _select_tables(self, question: str, candidates: list[str]) -> dict[str, Any]:
        schema_text = schema_catalog.summarize(candidates)
        prompt = TABLE_SELECTION_PROMPT.format(question=question, schema=schema_text)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        response = ollama_client.chat(messages)
        payload = _safe_json(response)
        tables = payload.get("tables") or candidates
        tables = [table for table in tables if table in candidates]
        join_path = payload.get("join_path") or []
        notes = payload.get("notes", "")
        return {"tables": tables, "join_path": join_path, "notes": notes, "schema": schema_text}

    def _generate_sql(self, question: str, selection: dict[str, Any]) -> dict[str, Any]:
        schema_text = selection["schema"]
        tables = selection["tables"]
        join_path = selection.get("join_path", [])
        prompt = SQL_GENERATION_PROMPT.format(
            question=question,
            tables=", ".join(tables),
            schema=schema_text,
            join_path="\n".join(join_path) if join_path else "(none)",
            limit=settings.max_result_rows,
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        response = ollama_client.chat(messages)
        payload = _safe_json(response)
        sql = payload.get("sql", "").strip()
        if sql:
            sql = ensure_limit(strip_trailing_semicolon(sql), settings.max_result_rows)
        return {"sql": sql, "notes": payload.get("notes", ""), "raw": response}

    def _build_context(self, question: str) -> str:
        if not self.rag_store:
            return ""
        results = self.rag_store.search(question, settings.rag_top_k)
        lines = [f"- {item.text}" for item in results]
        return "\n".join(lines)

    def ingest_document(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        if not self.rag_store:
            return
        metadata = metadata or {}
        chunks = [text[i : i + settings.rag_max_chunk_chars] for i in range(0, len(text), settings.rag_max_chunk_chars)]
        documents = [
            VectorDocument(doc_id=f"{doc_id}-{idx}", text=chunk, metadata=metadata)
            for idx, chunk in enumerate(chunks)
        ]
        self.rag_store.add(documents)

    def run(self, question: str, session_id: str | None = None) -> ChatResult:
        candidates = self._candidate_tables(question)
        selection = self._select_tables(question, candidates)
        sql_payload = self._generate_sql(question, selection)
        sql = sql_payload.get("sql", "")

        valid, error = validate_sql(sql, selection["tables"])
        if not valid:
            raise ValueError(error)

        data = run_query(sql)
        context = self._build_context(question)

        answer_prompt = ANSWER_PROMPT.format(
            question=question,
            sql=sql,
            results=json.dumps(data, ensure_ascii=True),
            context=context or "(none)",
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": answer_prompt},
        ]
        response = ollama_client.chat(messages)

        if session_id:
            self.memory.add(session_id, "user", question)
            self.memory.add(session_id, "assistant", response)

        debug = {
            "candidates": candidates,
            "selection": selection,
            "sql_notes": sql_payload.get("notes"),
            "sql_raw": sql_payload.get("raw"),
        }
        return ChatResult(answer=response, sql=sql, data=data, debug=debug)


pipeline = ChatPipeline()
