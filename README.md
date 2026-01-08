# DB-AI Backend (Ollama + SQL)

A small, DB-aware chatbot backend with an Ollama LLM, schema-aware SQL generation, and an optional RAG layer.

## Quick start

1) Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Copy `.env.example` to `.env` and update values.

3) Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /health` – basic health check
- `GET /schema` – current schema catalog (tables, columns, foreign keys)
- `POST /chat` – ask a question and get an answer
- `POST /rag/ingest` – add a document to the local vector store (when `RAG_ENABLED=true`)

## Example request

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"Top 5 customers by revenue last month?","include_debug":true}'
```

## Notes

- SQL is constrained to read-only `SELECT` and limited to allowed tables.
- For complex databases, tune `SCHEMA_MAX_CANDIDATES` and allow/deny lists.
- The local vector store is for small datasets. For production, replace it with pgvector, Qdrant, or another vector DB.
- To switch databases, set `DB_DIALECT` and driver, or provide `DB_URL` directly.
