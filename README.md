# Finance RAG — Quarterly Results Q&A

A RAG system that lets an analyst upload a company's quarterly results PDFs and
ask plain-English questions, with every answer backed by a cited file + page number.

> **Note on API keys:** this build uses **Google's Gemini API** instead of OpenAI,
> via the current `google-genai` SDK, with `gemini-embedding-001` for embeddings
> and `gemini-2.5-flash` for generation (both free-tier). Get a free key at
> https://aistudio.google.com/apikey — no billing setup required. Google's model
> names change every few months — if you hit a 404 on a model, check
> https://ai.google.dev/gemini-api/docs/pricing for the current free-tier lineup.

## Company chosen

`<TODO: e.g. Infosys>` — quarterly press releases downloaded from
`<TODO: link to Investor Relations page>`

PDFs used (place in `data/`):
- `<TODO: Q1FY25.pdf — link>`
- `<TODO: Q2FY25.pdf — link>`
- `<TODO: Q3FY25.pdf — link>`
- `<TODO: Q4FY25.pdf — link>`

## Setup

```bash
git clone <your-repo-url>
cd finance-rag
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
curl -X POST http://localhost:8000/ingest -F "files=@data/Q1FY25.pdf"
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

## Test questions and answers

`<TODO: run each question in the app, paste the exact answer it gave>`

1. What was total revenue in the most recent quarter you loaded?
   → `<answer>`
2. Compare net profit across all the quarters you loaded. Which was highest?
   → `<answer>`
3. How did revenue in the latest quarter compare with the same quarter of the
   previous year?
   → `<answer>`
4. What did management say about the demand outlook or business environment?
   → `<answer>`
5. Which business segment or geography grew fastest, and by how much?
   → `<answer>`
6. What was the operating margin in each quarter, and is the trend rising or
   falling?
   → `<answer>`
7. Was any dividend declared? State the amount per share and the record date.
   → `<answer>`
8. What risks, headwinds, or challenges are mentioned in the documents?
   → `<answer>`
9. Give me a three-line summary of the latest quarter for a client email.
   → `<answer>`
10. Trap question — "What is the CEO's personal shareholding in 2015?"
    → `<should be: "This information is not available in the uploaded documents.">`

## Screenshots

`<TODO: paste screenshots of upload, indexing confirmation, an answered
question with sources, and the trap question being refused>`

## What didn't work well (honest notes)

`<TODO: e.g. financial tables sometimes extract with columns run together;
increasing chunk size to ~1200 helped for the segment-wise revenue table but
not for the cash-flow statement; retrieval occasionally pulled the prior
quarter's page instead of the latest when a question didn't name the quarter
explicitly>`

## Architecture

```
PDF (data/) → pypdf per-page text extraction
            → RecursiveCharacterTextSplitter (1000/150)
            → Gemini text-embedding-004
            → ChromaDB (persisted to chroma_db/)
                    ↓ top-k similarity search on question embedding
            → context + question → Gemini 1.5 Flash (temp 0.1)
            → answer + [file, page] sources
```
