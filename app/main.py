from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.pipeline import pipeline
from app.schema import schema_catalog


app = FastAPI(title=settings.app_name)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    include_debug: bool = False


class ChatResponse(BaseModel):
    answer: str
    sql: str
    data: dict[str, Any]
    debug: Optional[dict[str, Any]] = None


class RAGIngestRequest(BaseModel):
    doc_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    metadata: Optional[dict[str, Any]] = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/schema")
def schema_summary() -> dict[str, Any]:
    catalog = schema_catalog.get()
    return {
        "tables": {
            name: {"columns": info.columns, "foreign_keys": info.foreign_keys}
            for name, info in catalog.items()
        }
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = pipeline.run(request.question, session_id=request.session_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ChatResponse(
        answer=result.answer,
        sql=result.sql,
        data=result.data,
        debug=result.debug if request.include_debug else None,
    )


@app.post("/rag/ingest")
def rag_ingest(request: RAGIngestRequest) -> dict[str, str]:
    if not settings.rag_enabled:
        raise HTTPException(status_code=400, detail="RAG is disabled.")
    pipeline.ingest_document(request.doc_id, request.text, request.metadata)
    return {"status": "ok"}
