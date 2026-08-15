# Finance RAG — Quarterly Results Q&A

A RAG system that lets an analyst upload a company's quarterly results PDFs and
ask plain-English questions, with every answer backed by a cited file + page number.

> **Note on API keys:** this build uses **Google's Gemini API** instead of OpenAI,
> via the current `google-genai` SDK, with `gemini-embedding-001` for embeddings
> and `gemini-3.5-flash-lite` for generation (both free-tier). Get a free key at
> https://aistudio.google.com/apikey — no billing setup required.
>
> Two things worth knowing if you rebuild this: **(1)** Google has been
> retiring/restricting model names for new API keys every few weeks during this
> project — if you get a 404, check https://ai.google.dev/gemini-api/docs/models
> for whatever's current. **(2)** brand-new models get a much stricter free-tier
> *daily* quota than slightly older/lighter ones — `gemini-3.5-flash` capped out
> at 20 requests/day on a fresh key, while `gemini-3.5-flash-lite` allows far
> more (~1,000+/day), which is why this project uses Flash-Lite for generation.

## Company chosen

**Infosys Limited** (NSE, BSE, NYSE: INFY) — quarterly press releases downloaded
from Infosys's [Investor Pack page](https://www.infosys.com/investors/shareholder-services/investor-pack.html).

### Document register

| # | File name | Quarter | Pages | Type | Text selectable? |
|---|---|---|---|---|---|
| 1 | `ifrs-inr-press-release (3).pdf` | Q2 FY26 (qtr ended Sep 30, 2025) | 8 | Press release | ✅ |
| 2 | `ifrs-inr-press-release (2).pdf` | Q3 FY26 (qtr ended Dec 31, 2025) | 9 | Press release | ✅ |
| 3 | `ifrs-inr-press-release (1).pdf` | Q4 FY26 (qtr ended Mar 31, 2026) | 8 | Press release | ✅ |
| 4 | `ifrs-inr-press-release.pdf`     | Q1 FY27 (qtr ended Jun 30, 2026) | 8 | Press release | ✅ |

Source links:
- Q2 FY26 — https://www.infosys.com/investors/reports-filings/quarterly-results/2025-2026/q2/documents/ifrs-inr-press-release.pdf
- Q3 FY26 — https://www.infosys.com/investors/reports-filings/quarterly-results/2025-2026/q3/documents/ifrs-inr-press-release.pdf
- Q4 FY26 — https://www.infosys.com/investors/reports-filings/quarterly-results/2025-2026/q4/documents/ifrs-inr-press-release.pdf
- Q1 FY27 — https://www.infosys.com/investors/reports-filings/quarterly-results/2026-2027/q1/documents/ifrs-inr-press-release.pdf

The four files download with generic names (`ifrs-inr-press-release.pdf`,
`(1)`, `(2)`, `(3)`) because Infosys serves every quarter's press release at
the same relative filename — the app's `detect_quarter()` function reads each
PDF's actual announcement date off page 1 to tell them apart, rather than
relying on filename.

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
already-indexed documents remain searchable with no re-upload needed. Verified
by restarting Streamlit mid-project and confirming chunk count (122) and
answer quality were unchanged.

## Chunking decision

| | Value |
|---|---|
| Chunk size | **1000 characters** |
| Overlap | **150 characters** |
| Total chunks (final, 4 files) | **122** |

**Reason:** 1000 chars keeps most single-page financial tables intact while
staying within the assignment's 800–1200 range; 150 char overlap preserves
sentences that fall on a chunk boundary.

### The retrieval fix that mattered most

Early testing showed the single biggest failure mode called out in the
assignment guide: four quarters of the same press release use nearly
identical wording ("revenue grew during the quarter…"), so a plain chunk of
text doesn't tell an embedding model which quarter it's from. A question like
*"what was total revenue"* returned a blended answer citing three different
quarters at once.

**Fix:** every chunk's text is now prefixed with a machine-detected quarter
label — `[Infosys Q1 FY27 — ifrs-inr-press-release.pdf]` — *before* it gets
embedded, not just stored as metadata afterward. This makes the quarter part
of what similarity search actually matches on. `detect_quarter()` in
`ingest.py` reads the announcement date from each PDF's page 1 (e.g.
"Bengaluru, India – April 23, 2026") and maps it to Infosys's fiscal calendar
(FY = April–March). This fixed the issue: rerunning the same revenue question
afterward returned one clean, correctly-attributed figure.

## Prompt (system instruction)
    You are a financial analyst assistant. Answer only using the context
     provided below, which is extracted from quarterly results PDFs. Each
     chunk of context is labeled with the quarter and file it came from —
     pay close attention to that label and do not mix figures from different
     quarters together unless the question explicitly asks for a comparison
     across quarters. State every figure with its unit and the specific
     quarter/period it applies to (e.g. '₹41,764 crore for Q3 FY26'), not as
     a bare number.
     Some questions ask you to summarize, compose, or restate information
     (e.g. 'give me a summary for a client email') rather than quote a single
     fact — for these, synthesize an answer by combining multiple facts from
     the context in your own words; this is not the same as inventing
     information, and you should do it freely as long as every fact you use
     actually appears in the context.
     Only reply with 'This information is not available in the uploaded
     documents.' when the context genuinely contains nothing relevant to
     answer from — not merely because no single sentence states the answer
     verbatim. Do not use outside knowledge and do not guess at figures.


Temperature: **0.1** (within the assignment's 0–0.2 range).

The second paragraph was added mid-project after question 9 (client summary)
was incorrectly refused — see honest notes below.

## Test questions and answers

| # | Question | Answer given | Correct? |
|---|---|---|---|
| 1 | Total revenue, most recent quarter | ₹48,211 crore, Q1 FY27 (qtr ended Jun 30, 2026), sourced from `ifrs-inr-press-release.pdf` pages 1 & 7 | ✅ verified by hand |
| 2 | Net profit across all quarters, highest? | Correctly compared all 4 loaded quarters; **Q4 FY26 highest at ₹8,509 crore** (before non-controlling interests) / ₹8,501 crore (after). Also surfaced prior-year (FY25) comparison figures present in the same source tables | ✅ |
| 3 | YoY revenue, latest vs same quarter last year | Q1 FY27: ₹48,211 crore vs Q1 FY26: ₹42,279 crore → **+14.0% YoY reported**, +2.4% in constant currency | ✅ math checks out |
| 4 | Management commentary on demand outlook | Pulled distinct, correctly-attributed CEO/CFO quotes and FY guidance ranges from all 4 quarters | ✅ |
| 5 | Fastest-growing segment/geography | "Not available in the uploaded documents" | ✅ **confirmed correct** — verified by full-text search across all 8 pages of all 4 PDFs; no segment/geography revenue breakdown exists in these Press Release PDFs (likely lives in Infosys's separate Fact Sheet document, not part of this dataset) |
| 6 | Operating margin per quarter, trend | Q1 FY27: 21.1%, Q3 FY26: 20.0%/21.0% (reported/adjusted), Q4 FY26: 20.3%/21.0% all correct; **Q2 FY26 (21.0%) incorrectly returned "not available"** even at top_k=8 | ⚠️ 3/4 correct — see honest notes |
| 7 | Dividend declared, amount + record date | ₹25/share proposed final dividend (FY26, per Q4 FY26 filing), ₹23/share interim dividend (announced in Q2 FY26). Record date correctly reported as not available | ✅ verified — record dates genuinely aren't in these press releases |
| 8 | Risks/headwinds mentioned | Correctly pulled the forward-looking-statements/risk-factors section (page 6) from all 4 filings | ✅ |
| 9 | 3-line summary of latest quarter for client email | Initially **incorrectly refused** ("not available") — fixed by rephrasing to name the quarter explicitly and updating the system prompt to allow synthesis. After the fix: correct, well-grounded figures for Q1 FY27, though the output reads as a dense stat list rather than genuinely email-toned prose | ⚠️ fixed, content correct, tone imperfect |
| 10 | Trap — CEO's personal shareholding in 2015 | "This information is not available in the uploaded documents." | ✅ correctly refused, no fabricated figure |

### Manual verification (figures checked by hand against the PDFs)

| Question | Figure app gave | Figure in actual PDF | Page | Match? |
|---|---|---|---|---|
| Q1 FY27 revenue | ₹48,211 crore | ₹48,211 crore | 7 | ✅ |
| Q1 FY27 operating margin | 21.1% | 21.1% | 1 | ✅ |
| Q1 FY27 operating profit | ₹10,163 crore | ₹10,163 crore | 7 | ✅ |
| Q1 FY27 basic EPS | ₹19.19 | ₹19.19 | 7 | ✅ |
| Q2 FY26 operating margin (asked directly) | 21.0% | 21.0% | 1 | ✅ |


## What didn't work well (honest notes)

- **Cross-quarter blending (fixed).** The single biggest issue: because all
  four press releases use nearly identical wording, early retrieval blended
  figures from multiple quarters into one answer. Fixed by prefixing each
  chunk's embedded text with a detected quarter label (see "retrieval fix"
  above). Confirmed working on both "most recent quarter" and specific-quarter
  questions afterward.
- **Q2 FY26 operating margin retrieval gap.** Even after the quarter-label
  fix and at top_k=8, one specific fact — Q2 FY26's operating margin — was
  never retrieved, consistently returning "not available" even though the
  figure (21.0%) is clearly present on page 1 of `ifrs-inr-press-release
  (3).pdf`. Likely cause: the operating margin appears in a short summary
  paragraph on page 1, which may embed less distinctly than the longer,
  more table-dense pages 7–8 that dominate retrieval for margin-related
  queries. Rephrasing the question to name each quarter explicitly recovered
  3 of 4 figures but not this one. Would likely need per-page-1 chunking
  changes or a higher top_k with re-ranking to fully fix — out of scope for
  this assignment's requirements.

