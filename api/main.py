"""
api/main.py — Optional FastAPI backend (bonus marks).

Run with:  uvicorn api.main:app --reload
Docs at:   http://localhost:8000/docs
"""
import os
import sys
from typing import List

from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

# allow importing ingest.py / rag.py from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest import ingest_pdfs
from rag import ask as rag_ask, stats as rag_stats

app = FastAPI(title="Finance RAG API")


class AskRequest(BaseModel):
    question: str
    top_k: int = 4


@app.post("/ingest")
async def ingest_endpoint(files: List[UploadFile] = File(...)):
    os.makedirs("data", exist_ok=True)
    saved_paths = []
    for f in files:
        path = os.path.join("data", f.filename)
        with open(path, "wb") as out:
            out.write(await f.read())
        saved_paths.append(path)

    n_files, n_chunks = ingest_pdfs(saved_paths)
    return {"files": n_files, "chunks": n_chunks}


@app.post("/ask")
async def ask_endpoint(req: AskRequest):
    return rag_ask(req.question, top_k=req.top_k)


@app.get("/stats")
async def stats_endpoint():
    return rag_stats()
