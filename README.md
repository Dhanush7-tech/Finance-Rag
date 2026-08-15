# Finance RAG — Quarterly Results Q&A

A RAG system that lets an analyst upload a company's quarterly results PDFs and
ask plain-English questions, with every answer backed by a cited file + page number.

> **Note on API keys:** this build uses **Google's Gemini API** instead of OpenAI,
> via the current `google-genai` SDK, with `gemini-embedding-001` for embeddings
> and `gemini-3.5-flash` for generation (both free-tier). Get a free key at
> https://aistudio.google.com/apikey — no billing setup required. Google has been
> retiring/restricting model names for new API keys every few weeks — if you get
> a 404 on the generation model, check https://ai.google.dev/gemini-api/docs/models
> for whatever's current and swap `GENERATION_MODEL` in `rag.py`.

## Company chosen

**Infosys Limited** (NSE, BSE, NYSE: INFY) — quarterly press releases downloaded
from Infosys's [Investor Pack page](https://www.infosys.com/investors/shareholder-services/investor-pack.html).

PDFs used (in `data/`):
- Q2 FY26 (quarter ended Sep 30, 2025) — https://www.infosys.com/investors/reports-filings/quarterly-results/2025-2026/q2/documents/ifrs-inr-press-release.pdf
- Q3 FY26 (quarter ended Dec 31, 2025) — https://www.infosys.com/investors/reports-filings/quarterly-results/2025-2026/q3/documents/ifrs-inr-press-release.pdf
- Q4 FY26 (quarter ended Mar 31, 2026) — https://www.infosys.com/investors/reports-filings/quarterly-results/2025-2026/q4/documents/ifrs-inr-press-release.pdf
- Q1 FY27 (quarter ended Jun 30, 2026) — https://www.infosys.com/investors/reports-filings/quarterly-results/2026-2027/q1/documents/ifrs-inr-press-release.pdf

## Setup

```bash
git clone https://github.com/Dhanush7-tech/Finance-Rag.git
cd Finance-Rag
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and paste your free Gemini key:
# GOOGLE_API_KEY=your_key_here
```

## Run — Streamlit app

```bash
streamlit run app.py
```

Open the local URL Streamlit prints, upload your PDFs in the sidebar, click
**Index documents**, then ask questions in the main panel.

## Run — optional FastAPI backend (bonus)

```bash
uvicorn api.main:app --reload
```

Test endpoints at http://localhost:8000/docs, or:

```bash
curl -X POST http://localhost:8000/ingest -F "files=@data/ifrs-inr-press-release.pdf"
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
     -d '{"question": "What was total revenue in the most recent quarter?", "top_k": 4}'
curl http://localhost:8000/stats
```

## Persistence

ChromaDB is persisted to `chroma_db/` on disk. Stop the app, start it again —
already-indexed documents remain searchable with no re-upload needed.

## Chunking choice

- **Chunk size: 1000 characters** — large enough that most single financial
  tables (revenue, profit, segment breakdown) stay inside one chunk, small
  enough to stay within the 800–1200 char range and keep retrieval precise.
- **Overlap: 150 characters** — enough that a sentence split across a chunk
  boundary still appears whole in at least one neighboring chunk.

Collection stats after indexing all 4 quarters: **90 chunks stored**,
embedding model `gemini-embedding-001`, LLM `gemini-3.5-flash`.


## Screenshots

<img width="1917" height="889" alt="Screenshot 2026-08-15 103942" src="https://github.com/user-attachments/assets/ded474d2-7619-4230-8e09-f9f64fb7b2de" />


## What didn't work well (honest notes)

- Vague questions like "what was total revenue" (without specifying "most
  recent quarter" explicitly) caused the model to return revenue for every
  period mentioned across the retrieved chunks instead of a single figure.
  Rephrasing questions to name the quarter explicitly gets cleaner answers.


## Architecture


PDF (data/) → pypdf per-page text extraction
            → RecursiveCharacterTextSplitter (1000/150)
            → Gemini gemini-embedding-001
            → ChromaDB (persisted to chroma_db/)
                    ↓ top-k similarity search on question embedding
            → context + question → Gemini 3.5 Flash (temp 0.1)
            → answer + [file, page] sources

