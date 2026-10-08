import json, uuid
from pathlib import Path
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .config import UPLOAD_DIR
from .db import Base, engine, get_db, Document, ChatMessage, User
from .auth import seed_users, login, current_user, require_admin
from . import processing, vectorstore, rag

Base.metadata.create_all(engine)
seed_users()
app = FastAPI(title="EduPolicy AI")


class LoginIn(BaseModel):
    username: str
    password: str


class AskIn(BaseModel):
    question: str
    doc_ids: list[int] | None = None


@app.post("/auth/login")
def do_login(body: LoginIn, db: Session = Depends(get_db)):
    token, u = login(db, body.username, body.password)
    return {"token": token, "username": u.username, "role": u.role}


@app.post("/documents")
def upload(file: UploadFile = File(...), user: User = Depends(require_admin), db: Session = Depends(get_db)):
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in ("pdf", "docx"):
        raise HTTPException(400, "Only PDF and DOCX files are supported")
    path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{file.filename}"
    path.write_bytes(file.file.read())
    try:
        sections = processing.extract_document(path, ext)
    except Exception as e:
        path.unlink(missing_ok=True)
        raise HTTPException(422, f"Could not read file: {e}")
    chunks = processing.build_chunks(sections)
    if not chunks:
        path.unlink(missing_ok=True)
        raise HTTPException(422, "No extractable text found (scanned PDF?)")
    doc = Document(filename=file.filename, file_type=ext, pages=len(sections),
                   chunks=len(chunks), stored_path=str(path), uploaded_by=user.id)
    db.add(doc); db.commit(); db.refresh(doc)
    vectorstore.add_chunks(doc.id, doc.filename, chunks)
    return {"id": doc.id, "filename": doc.filename, "chunks": doc.chunks}


@app.get("/documents")
def list_docs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": d.id, "filename": d.filename, "type": d.file_type, "pages": d.pages,
             "chunks": d.chunks, "uploaded": d.created_at.isoformat()}
            for d in db.query(Document).order_by(Document.id.desc())]


@app.delete("/documents/{doc_id}")
def delete_doc(doc_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    vectorstore.delete_document(doc_id)
    Path(d.stored_path).unlink(missing_ok=True)
    db.delete(d); db.commit()
    return {"deleted": doc_id}


@app.post("/ask")
def ask(body: AskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not body.question.strip():
        raise HTTPException(400, "Question is empty")
    result = rag.answer_question(body.question.strip(), body.doc_ids)
    db.add(ChatMessage(user_id=user.id, question=body.question, answer=result["answer"],
                       sources=json.dumps(result["sources"])))
    db.commit()
    return result


@app.get("/history")
def history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(ChatMessage).filter_by(user_id=user.id).order_by(ChatMessage.id).all()
    return [{"id": r.id, "question": r.question, "answer": r.answer,
             "sources": json.loads(r.sources), "time": r.created_at.isoformat()} for r in rows]


@app.delete("/history")
def clear_history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.query(ChatMessage).filter_by(user_id=user.id).delete(); db.commit()
    return {"cleared": True}
