# EduPolicy AI - Intelligent Document Question Answering System

Upload PDF/DOCX documents, ask questions in natural language, get answers **only from your documents**, with citations (document name + page/section).

## Architecture
```
Upload -> extract text -> clean -> chunk (900 chars, 150 overlap) -> embeddings -> ChromaDB
Question -> similarity search (top 5) -> relevance filter -> Claude (context only) -> answer + sources
                                         \-> nothing relevant => "I could not find this information in the uploaded documents."
```
| Layer | Tech |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Metadata / history / users | SQLite (default) or PostgreSQL via `DATABASE_URL` |
| Vector DB + embeddings | ChromaDB (built-in MiniLM embedding model, runs locally) |
| LLM | Anthropic Claude API (optional - offline mode shows the best matching passage) |

## How to run

**Requirements:** Python 3.10+ and internet on first run (ChromaDB downloads a ~80 MB embedding model once).

```bash
# 1. go into the project folder
cd edupolicy-ai

# 2. virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. install
pip install -r requirements.txt

# 4. configure
cp .env.example .env              # Windows: copy .env.example .env
#   open .env and paste your ANTHROPIC_API_KEY  (skip for offline mode)

# 5. start backend  (terminal 1)
uvicorn backend.main:app --reload

# 6. start frontend (terminal 2, same venv)
streamlit run frontend/streamlit_app.py
```
Open http://localhost:8501. API docs: http://localhost:8000/docs

**Logins:** `admin / admin123` (upload, delete, ask) and `student / student123` (ask only).

**Quick demo:** log in as admin -> upload `sample_docs/college_policy.docx` -> ask
"What is the attendance requirement for first-year students?" -> then ask "What is the capital of France?" to see hallucination control.

### Using PostgreSQL (optional)
Create a database, then set in `.env`: `DATABASE_URL=postgresql://user:password@localhost:5432/edupolicy`. Tables are created automatically.

## API
| Method | Endpoint | Role | Purpose |
|---|---|---|---|
| POST | /auth/login | - | get token |
| POST | /documents | admin | upload + index PDF/DOCX |
| GET | /documents | any | list documents |
| DELETE | /documents/{id} | admin | delete doc + its vectors |
| POST | /ask | any | `{question, doc_ids?}` -> answer + sources |
| GET / DELETE | /history | any | your chat history |

## Tests
`pytest -q` (unit tests) and manual cases in `tests/TEST_CASES.md`.

## Project structure
```
backend/  config.py db.py auth.py processing.py vectorstore.py rag.py main.py
frontend/ streamlit_app.py
tests/    test_chunking.py TEST_CASES.md
sample_docs/
```

## Troubleshooting
- *"Cannot reach the backend"* - start uvicorn first; check `API_URL`.
- *First upload is slow* - embedding model is downloading once.
- *"No extractable text found"* - the PDF is scanned images; OCR is not included (listed under future work).
- *Answers say "Offline mode"* - `ANTHROPIC_API_KEY` missing in `.env`; restart uvicorn after editing.

## Limitations / future work
OCR for scanned PDFs, hybrid (keyword + vector) search, re-ranking, streaming answers, JWT auth with bcrypt passwords, per-document permissions.
