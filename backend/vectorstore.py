"""ChromaDB wrapper (persistent, cosine similarity, built-in MiniLM embeddings)."""
import chromadb
from .config import CHROMA_DIR

_client = None


def _col():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client.get_or_create_collection("edupolicy", metadata={"hnsw:space": "cosine"})


def add_chunks(doc_id: int, doc_name: str, chunks: list[dict]):
    col = _col()
    for i in range(0, len(chunks), 200):
        batch = chunks[i:i + 200]
        col.add(
            ids=[f"{doc_id}-{i + j}" for j in range(len(batch))],
            documents=[c["text"] for c in batch],
            metadatas=[{"doc_id": doc_id, "doc_name": doc_name,
                        "page": c["page"] or 0, "section": c["section"] or ""} for c in batch],
        )


def search(question: str, k: int, doc_ids: list[int] | None = None) -> list[dict]:
    col = _col()
    total = col.count()
    if total == 0:
        return []
    where = {"doc_id": {"$in": doc_ids}} if doc_ids else None
    res = col.query(query_texts=[question], n_results=min(k, total), where=where)
    hits = []
    for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append({"text": text, "score": round(1 - dist, 3), **meta})
    return hits


def delete_document(doc_id: int):
    _col().delete(where={"doc_id": doc_id})
