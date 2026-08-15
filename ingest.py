"""
ingest.py — Load PDFs, chunk their text, embed with Gemini, store in ChromaDB.

Pipeline: PDF -> per-page text -> recursive character chunks -> embeddings -> Chroma.
Each chunk keeps its source file name and page number so answers can be verified.
"""
import os
import glob
from pathlib import Path

import chromadb
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY not found. Copy .env.example to .env and add your free "
        "key from https://aistudio.google.com/apikey"
    )
_genai_client = genai.Client(api_key=GOOGLE_API_KEY)

# Current Gemini embedding model (replaces the retired text-embedding-004).
EMBEDDING_MODEL = "gemini-embedding-001"
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "quarterly_reports"

# Chunk size 1000 chars keeps most single-page financial tables inside one chunk,
# while staying within the 800-1200 char range required by the assignment.
# 150 char overlap is enough that a sentence split across a chunk boundary
# still appears whole in at least one chunk, without bloating chunk count.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

_chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)


def get_collection():
    return _chroma_client.get_or_create_collection(name=COLLECTION_NAME)


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT"):
    """Embed a single string using Gemini's free gemini-embedding-001 model."""
    result = _genai_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return result.embeddings[0].values


def load_pdf_pages(pdf_path: str):
    """Return a list of (page_number, text) tuples for a PDF, 1-indexed pages.
    Pages with no extractable text (e.g. scanned images) are skipped."""
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i, text))
    return pages


def chunk_pages(pages, file_name: str):
    """Split page text into overlapping chunks, tagging each with its page number."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for page_num, text in pages:
        for piece in splitter.split_text(text):
            chunks.append({"text": piece, "file": file_name, "page": page_num})
    return chunks


def ingest_pdfs(pdf_paths):
    """Ingest a list of PDF file paths into ChromaDB.
    Returns (file_count, chunk_count)."""
    collection = get_collection()
    total_chunks = 0

    for pdf_path in pdf_paths:
        file_name = Path(pdf_path).name
        pages = load_pdf_pages(pdf_path)
        if not pages:
            print(f"WARNING: no extractable text in {file_name} "
                  f"(likely a scanned PDF) — skipped.")
            continue

        chunks = chunk_pages(pages, file_name)

        ids, embeddings, documents, metadatas = [], [], [], []
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{file_name}::p{chunk['page']}::c{idx}"
            embeddings.append(embed_text(chunk["text"]))
            documents.append(chunk["text"])
            metadatas.append({"file": chunk["file"], "page": chunk["page"]})
            ids.append(chunk_id)

        if ids:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
        total_chunks += len(ids)

    return len(pdf_paths), total_chunks


def ingest_folder(folder: str = "data"):
    """Convenience: ingest every PDF already sitting in a folder (used by CLI)."""
    pdf_paths = sorted(glob.glob(os.path.join(folder, "*.pdf")))
    return ingest_pdfs(pdf_paths)


if __name__ == "__main__":
    n_files, n_chunks = ingest_folder("data")
    print(f"{n_files} files processed, {n_chunks} chunks stored.")
