"""
rag.py — Retrieve relevant chunks from ChromaDB and ask Gemini to answer.
"""
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

from ingest import get_collection, embed_text, EMBEDDING_MODEL

load_dotenv()
_genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Google has been aggressively restricting new API keys to its newest models —
# gemini-2.5-flash (and even 2.5-flash-lite/2.5-pro) now return 404 for new
# keys months ahead of their official shutdown dates. gemini-3.5-flash is the
# current GA model available to new users as of Aug 2026. If this 404s for
# you too, try "gemini-3.5-flash-lite" or check
# https://ai.google.dev/gemini-api/docs/models for what's current.
GENERATION_MODEL = "gemini-3.5-flash"
TEMPERATURE = 0.1  # within the 0-0.2 range required by the assignment
# Note: Google has marked temperature/top_p/top_k as deprecated params in its
# latest API release (still functional as of Aug 2026). If a future SDK
# update rejects this, drop the temperature arg from GenerateContentConfig.

SYSTEM_INSTRUCTION = (
    "You are a financial analyst assistant. Answer only using the context "
    "provided below, which is extracted from quarterly results PDFs. "
    "If the context does not contain the answer, reply exactly: "
    "'This information is not available in the uploaded documents.' "
    "Do not use outside knowledge and do not guess. When you cite a number, "
    "mention which file/quarter it came from."
)


def retrieve(question: str, top_k: int = 4):
    collection = get_collection()
    query_embedding = embed_text(question, task_type="RETRIEVAL_QUERY")
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    chunks = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    for doc, meta in zip(docs, metas):
        chunks.append({"text": doc, "file": meta.get("file"), "page": meta.get("page")})
    return chunks


def ask(question: str, top_k: int = 4):
    chunks = retrieve(question, top_k=top_k)

    if not chunks:
        return {
            "answer": "This information is not available in the uploaded documents.",
            "sources": [],
        }

    context = "\n\n".join(
        f"[Source: {c['file']}, page {c['page']}]\n{c['text']}" for c in chunks
    )
    prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"

    response = _genai_client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=TEMPERATURE,
        ),
    )
    answer = response.text.strip()

    sources = [{"file": c["file"], "page": c["page"]} for c in chunks]
    return {"answer": answer, "sources": sources}


def stats():
    collection = get_collection()
    return {
        "collection_name": collection.name,
        "total_chunks": collection.count(),
        "embedding_model": EMBEDDING_MODEL,
        "llm_model": GENERATION_MODEL,
    }