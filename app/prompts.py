SYSTEM_PROMPT = """
You are a careful data assistant. You must only generate read-only SQL queries.
Use only the provided schema. Never invent tables or columns.
If you are unsure, ask for clarification instead of guessing.
""".strip()

TABLE_SELECTION_PROMPT = """
Given the user question and candidate schema, choose the minimum set of tables
and join paths needed to answer. Output JSON only with keys:
- tables: list of table names
- join_path: list of relations in the form "table.column -> table.column"
- notes: short reasoning

User question:
{question}

Candidate schema:
{schema}
""".strip()

SQL_GENERATION_PROMPT = """
Generate a single SQL SELECT statement to answer the question.
Rules:
- Use only these tables: {tables}
- Use only columns shown in the schema.
- Use the join paths provided if possible.
- Avoid SELECT *; choose explicit columns.
- Add LIMIT {limit} unless it is already present.
- Output JSON only with keys: sql, notes

User question:
{question}

Schema:
{schema}

Join paths:
{join_path}
""".strip()

ANSWER_PROMPT = """
Answer the user question using the SQL results and any retrieved context.
If data is missing, state the limitation clearly.

Question:
{question}

SQL used:
{sql}

SQL results:
{results}

Context:
{context}
""".strip()
