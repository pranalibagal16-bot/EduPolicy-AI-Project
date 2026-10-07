"""Question -> retrieve -> context -> LLM -> answer (+ citations, hallucination control)."""
from . import vectorstore
from .config import ANTHROPIC_API_KEY, LLM_MODEL, TOP_K, MIN_SCORE, NOT_FOUND_MSG

SYSTEM = (
    "You are EduPolicy AI. Answer the question using ONLY the numbered context passages. "
    "Do not use outside knowledge. If the passages do not contain the answer, reply with exactly: NOT_FOUND. "
    "Be concise and mention which source number(s) you used, like [1] or [2]."
)


def _cite(h: dict) -> dict:
    return {"document": h["doc_name"], "page": h["page"] or None,
            "section": h["section"] or None, "score": h["score"], "snippet": h["text"][:300]}


def answer_question(question: str, doc_ids: list[int] | None = None) -> dict:
    hits = [h for h in vectorstore.search(question, TOP_K, doc_ids) if h["score"] >= MIN_SCORE]
    if not hits:
        return {"answer": NOT_FOUND_MSG, "sources": []}

    if not ANTHROPIC_API_KEY:   # offline fallback so the project still runs without a key
        top = hits[0]
        return {"answer": "(Offline mode - no LLM key set) Most relevant passage:\n\n" + top["text"],
                "sources": [_cite(top)]}

    context = "\n\n".join(
        f"[{i}] ({h['doc_name']}, {'page ' + str(h['page']) if h['page'] else 'section: ' + (h['section'] or 'n/a')})\n{h['text']}"
        for i, h in enumerate(hits, 1))
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=LLM_MODEL, max_tokens=600, temperature=0, system=SYSTEM,
        messages=[{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}])
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if text.upper().startswith("NOT_FOUND"):
        return {"answer": NOT_FOUND_MSG, "sources": []}
    return {"answer": text, "sources": [_cite(h) for h in hits]}
