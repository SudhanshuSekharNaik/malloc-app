---
title: Malloc Career Intelligence OS
emoji: ⚡
colorFrom: purple
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# malloc() — AI Career & Intelligence OS

Voice-enabled personal AI assistant with long-term memory. Scoped as a
5-day MVP: text + voice input, memory extraction, RAG retrieval,
remember/forget/update commands, a simple dashboard. Explicitly out of
scope for the MVP: auth, microservices, memory consolidation,
multi-agent setups, advanced reranking, Kubernetes, custom model
training. **This README reflects Day 1 only** (plain chat loop, no
memory); sections grow as each day lands. Do not describe unimplemented
days as if they exist.

## Problem & motivation

General-purpose chat assistants forget everything between sessions. malloc()'s
goal is a personal assistant that can remember useful facts about a user over
time, retrieve the right memory at the right moment, update memories when
they change, resolve conflicts when new information contradicts old, and
forget things on request. Stage 1 builds the plain chat loop everything else
sits on top of — no memory yet, deliberately.

## Architecture (Day 1)

```
User → Streamlit → FastAPI (/chat) → conversation/message storage (SQLite) → LLM → Response
```

LangChain and FAISS are in the eventual stack (for Day 2/3 memory
extraction and RAG retrieval) but deliberately not installed yet —
Day 1 has nothing for them to do.

Two things are already separated even though Stage 1 doesn't need it yet:

- **Conversation history** (this stage) — the raw back-and-forth of one
  conversation, stored in full.
- **Long-term memory** (Stage 3+) — a small, curated set of durable facts
  extracted *from* conversation history. Not built yet.

This separation is the single most important architectural decision in the
project (see Stage 3 plan below) — conversation history and long-term memory
must never be conflated, so the schema and code paths are kept apart from
day one.

## Memory types, lifecycle, retrieval, conflict resolution, agent
architecture, voice architecture, privacy model, evaluation methodology

Not implemented yet. These sections will be filled in as Stages 3–12 land.

## API (Day 1-2)

- `POST /chat` — `{user_external_id, conversation_id?, message}` → `{conversation_id, reply}`.
  Creates a user/conversation on first contact; omit `conversation_id` to
  start a new conversation, pass it back to continue one. After the reply
  is generated, runs best-effort memory extraction on the turn (see below).
- `GET /chat/{conversation_id}` — full message history for a conversation.
- `GET /memories/{user_external_id}` — list that user's active stored memories.
- `POST /media/transcribe` — upload an audio file → `{text}` (faster-whisper).
- `POST /media/caption` — upload an image file → `{caption}` (BLIP image captioning).
- `POST /ats/check` (and `/api/ats/check`) — audit resume parseability & ATS compatibility.
- `POST /matcher/suggest-edits` (and `/api/resume/suggest-edits`) — generate opt-in bullet rewrites, evidenced keyword additions, and clarity polish with strict fabrication guardrail.
- `POST /insights/analyze` (and `/api/company/insights`) — multi-layer company size classification, industry tagging, culture sentiment scoring, and interview intelligence.
- `GET /insights/{company_name}` — quick company intelligence lookup.
- `GET /health` — liveness check.

## Company Insights Engine with Pretrained Transformers Classifiers

Multi-layer company analysis integrating zero-shot natural language inference, specialized text classification, and quantifiable sentiment analysis without violating anti-scraping boundaries.

### Multi-Layer Model Pipeline

1. **Layer 1 — Zero-Shot Company Size Classification**:
   - Model: **`facebook/bart-large-mnli`** (large zero-shot NLI pipeline).
   - Candidate Labels: `"large multinational corporation"`, `"early-stage startup"`, `"established mid-size company"`.
   - Combines scraped About narrative with structured numeric facts (`founded_year`, `employee_count_estimate`).
   - **Disagreement Guardrail**: Cross-checks model label against extracted numbers (e.g. flags conflict if model predicts "startup" for a 50,000-employee company).
2. **Layer 1b — Industry Classification**:
   - Model: **`sampathkethineedi/industry-classification`** (DistilBERT fine-tuned on 62 business industry categories).
   - Operates on bounded 512-character company description.
3. **Layer 2 — Official Domain & About Text Parsing**:
   - Extracts structured signals while strictly adhering to ToS (no direct Glassdoor, AmbitionBox, or raw Google search scraping).
4. **Layer 3 — Culture Synthesis & Quantifiable Sentiment**:
   - Model: **`distilbert-base-uncased-finetuned-sst-2-english`** (SST-2 sentiment pipeline).
   - Computes quantifiable `sentiment_breakdown` (`positive_count`, `negative_count`, `total`) alongside cited qualitative praised/criticized aspects.
5. **Layer 4 — Interview Intelligence**:
   - Curates key focus areas (Architecture, Clean Coding, Behavioral), hiring stages, and targeted preparation tips.


## Suggested Resume Edits & Anti-Fabrication Guardrail

Directly within the Resume Matcher, generates concrete, actionable bullet rewrites and keyword placement recommendations to align an uploaded resume with a target job specification.

### 4-Layer Architecture

1. **Layer 1 — Skill Gap & Evidence Analysis**:
   - Reuses skill extraction and keyword overlap from the Resume Matcher.
   - Cross-references missing job skills with the entire resume body: if a skill is mentioned in experience or project descriptions but absent from the explicit Skills list, it surfaces as a safe *"Add to Skills section"* recommendation.
2. **Layer 2 — Targeted Bullet Rewriting**:
   - Model: **`vsr9awc/resume-optimizer`** (Qwen2.5-1.5B-Instruct fine-tuned on 96,000+ resume bullet optimization pairs).
   - Operates **per-bullet** on experience and project achievements rather than whole-document blobs.
   - *Caveat*: As a smaller community fine-tune, all outputs are marked as draft AI suggestions requiring human review.
3. **Layer 3 — Programmatic Fabrication Guardrail (Strict Safety Layer)**:
   - Programmatically verifies that no new metrics, numbers, percentages, dollar figures, or unsupported tools are hallucinated.
   - Unverified numbers are flagged with clear warnings or discarded before reaching the UI.
4. **Layer 4 — Grammar & Clarity Polish**:
   - Model: **`AventIQ-AI/t5-small-grammar-correction`** (T5-small on JFLEG) for phrasing refinement.
   - Opt-in UI: Users can individually **Accept** (modifying active editor text) or **Dismiss** suggestions.


## ATS (Applicant Tracking System) Checker

Scores a resume's raw **parseability, formatting, and structural readability**
independently of any specific job description, preventing silent rejection before
a human recruiter ever reviews it.

### Hybrid Scoring Architecture

1. **Layer 1 — Deterministic Rule-Based Parseability (65% Weight)**:
   - **File Format**: Standard PDF/TXT/DOCX compatibility.
   - **Filename Hygiene**: Warns against special characters and generic names.
   - **Standard Section Headers**: Validates presence of Experience, Education, Skills, and Summary headers.
   - **Contact Detectability**: Regex-based verification of email, phone number, and LinkedIn/GitHub links.
   - **Multi-Column & Table Detection**: Heuristics to catch formatting artifacts that break ATS text extraction.
   - **Length & Density**: Configurable word count checks (150–1600 words) and bullet-point scannability ratios.

2. **Layer 2 — Content Quality via HuggingFace Models (35% Weight)**:
   - **`yashpwr/resume-ner-bert-v2`**: BERT token-classification pipeline extracting structured entities (Skills, Designation, Degree).
   - **`srivihari/resume-job-role-classifier`**: DistilBERT text-classification pipeline assessing role domain coherence and confidence.
   - **Lazy-Loaded & Best-Effort**: Models load on first use and are cached as singletons (`@lru_cache`). If model download or inference fails, the request returns 200 OK with Layer 1 rule checks and ML checks marked `unavailable`.

3. **Combined Scoring & Output**:
   - `overall_score` (0–100) with traffic-light verdicts: `ATS-Friendly` (≥80), `Needs Improvement` (50–79), `High Risk` (<50).
   - Prioritized, actionable improvement recommendations list.

## Job application tracker

Core structure for job tracking, follow-up reminders, and (future)
reports. New table: `job_applications` (company, role, status, applied
date, follow-up date, notes, job URL).

- `POST /jobs` — log a new application. `follow_up_days` (default 7)
  sets `follow_up_date = applied_date + N days` automatically.
- `GET /jobs/{user_external_id}` — all applications for a user.
- `GET /jobs/{user_external_id}/due-followups` — applications whose
  follow-up date has passed and are still open (`applied`/`interview`/
  `no_response` — not `offer`/`rejected`, which are terminal).
- `PATCH /jobs/{job_id}` — update any field (status, notes, etc.).
- `DELETE /jobs/{job_id}`.

**Reminders are pull-based, not push-based**: there's no background
scheduler (APScheduler/Celery) sending notifications. The Streamlit
Job Tracker tab checks `due-followups` on page load and shows a banner
if anything's overdue. That covers the actual need for a single-user
MVP without adding scheduler infrastructure — revisit only if you need
a reminder to reach you *without* opening the app.

Not yet built: weekly/monthly reports, resume upload/parsing, and the
job-post → research → rating → draft-email pipeline — these are
separate features layered on top of this table, not built yet.

## Memory extraction (Day 2)

After every chat turn, `app/memory_extraction.py` sends the turn to the
LLM with a dedicated system prompt and asks for one of two actions:

```json
{"action": "STORE", "memory_type": "semantic", "content": "...", "importance": 0.8, "confidence": 0.9}
```
or
```json
{"action": "IGNORE", "memory_type": null, "content": null, "importance": null, "confidence": null}
```

The response is validated with a Pydantic model (`MemoryExtraction`) —
malformed or schema-violating output raises `ExtractionError` rather
than being trusted. `STORE` results are written to the `memories` table;
`IGNORE` and any failure are simply skipped.

**The one rule this is built around: extraction must never break chat.**
It runs *after* the chat reply has already been generated and returned,
and every failure mode (LLM error, bad JSON, schema violation) is caught
and logged rather than propagated — verified by
`test_chat_succeeds_even_if_extraction_fails`.

Not yet built: UPDATE/conflict resolution (a fact contradicting an
existing memory just gets extracted as a new row for now — Stage 6/7's
temporal + conflict-resolution logic hasn't landed), and remember/forget
commands (Day 4).

`/media/*` routes only produce text — they don't call the LLM. Feed the
returned text into `/chat` yourself (that's how voice/image input is
meant to compose with the existing chat flow, rather than duplicating
logic inside the media routes).

## Multimodal + vector store components

- `app/speech.py` — faster-whisper wrapper (`transcribe(audio_path)`), model size `base`, CPU/int8.
- `app/vision.py` — BLIP image captioning wrapper (`caption_image(image_path)`). This is captioning, not OCR — it describes an image, it doesn't read text inside one.
- `app/vectorstore.py` — `sentence-transformers` (`all-MiniLM-L6-v2`) embeddings + a FAISS flat index (`MemoryVectorStore`) with `add`/`search`. This is the piece Day 3's RAG memory retrieval will plug into.

Two things worth knowing before relying on these:
- **Model weights are not bundled** — the first call to any of these
  downloads from Hugging Face on your machine (needs internet, and disk:
  torch + transformers + the model weights add up to a few GB).
- **The vector store is in-memory only right now** — it does not survive
  a process restart. Persisting it (to a FAISS index file, or moving
  into pgvector per the original architecture plan) is a Day 3 task,
  not done yet. `remove()` is intentionally unimplemented for the same
  reason — soft-delete at the DB layer (mark inactive, filter after
  search) is the intended approach once real memories exist, per the
  temporal-memory design.

## Local setup

```bash
cd memora
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Get a **free** Groq API key (no credit card needed) at
https://console.groq.com/keys and put it in `.env` as `GROQ_API_KEY`.
This is the default provider — no billing setup required to get running.

Prefer to use Claude instead? Set `LLM_PROVIDER=anthropic` and
`ANTHROPIC_API_KEY` in `.env` (requires a funded console.anthropic.com
account).

```bash
uvicorn app.main:app --reload
```

In a second terminal, start the Streamlit UI:

```bash
streamlit run streamlit_app.py
```

Or skip the UI and hit the API directly:

```bash
curl -X POST localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_external_id": "demo-user", "message": "Hey, who are you?"}'
```

## Tests

```bash
pytest tests/ -v
```

Tests mock the LLM call, so they run without a real `ANTHROPIC_API_KEY`.
6/6 passing as of Stage 1.

## Deployment

Not implemented yet (Stage 14 in the master plan / end of the 8-week
timeline). Stage 1 is local-only.

## Future improvements / roadmap

5-day MVP plan:

- **Day 1** ✅ Core chatbot + database — Streamlit → FastAPI → LLM → Response,
  conversation/message storage.
- **Day 2** ✅ Long-term memory extraction — structured STORE/IGNORE actions
  via Pydantic (`app/memory_extraction.py`), `memories` table, best-effort
  (never breaks chat on failure). Plus multimodal input scaffolding
  (`/media/transcribe`, `/media/caption`) and a vector store module
  (`app/vectorstore.py`) ready for Day 3.
- **Day 3** — RAG-based memory retrieval: wire `app/vectorstore.py` into
  the chat flow — embed stored memories on STORE, embed the incoming
  query, retrieve top-K relevant memories, inject into the LLM's context.
- **Day 4** — Remember / forget / update commands (explicit user control
  over what's stored) + wiring `/media/transcribe` into the chat flow.
- **Day 5** — Simple memory dashboard (list, search, edit, delete) +
  end-to-end pass.

Deferred beyond the MVP: authentication, memory consolidation, temporal
HISTORICAL/ACTIVE status tracking, conflict resolution beyond simple
STORE (an UPDATE that contradicts an existing memory currently just
becomes a second row), a LangGraph multi-tool agent, advanced reranking,
and a formal precision/recall/F1 evaluation harness.

## Job Post Authenticity & Fraud Risk Checker

`malloc()` includes a hybrid 3-layer security engine for evaluating job postings against employment fraud and scam patterns (`/authenticity/check` and `/api/jobs/authenticity-check`):

### 3-Layer Hybrid Architecture
1. **Layer 1: Rule-Based Red-Flag Heuristics (Deterministic)**
   - Regex and keyword scanning for disposable/free email contact domains (`@gmail.com`, `@yahoo.com`), private messaging interview redirection (Telegram/WhatsApp/Signal), upfront payment/processing fee demands, fake equipment checks, and URL shorteners (`bit.ly`, `tinyurl.com`).
2. **Layer 2: ML Binary Classification Signal**
   - Model: `AventIQ-AI/BERT-Spam-Job-Posting-Detection-Model` (`bert-base-uncased` fine-tuned on fake-vs-real job postings).
   - **Documented Model Limitations**:
     * **128-token max context window** (~100 words): Focuses on job title, lead paragraph, and red-flag dense sections.
     * **Precision on "Fake Job" class is ~0.81**: Real-world class imbalance means "Fake Job" prediction represents ~4-in-5 reliability.
     * **English language trained**: Evaluated only on English postings.
3. **Layer 3: RAG-Augmented LLM Reasoning**
   - Curated knowledge base of 18+ employment fraud patterns (advance equipment check fraud, phishing for banking details, pyramid/MLM schemes, reshipping mule operations).
   - Embedded with `all-MiniLM-L6-v2` cosine similarity retrieval (top-k=4).
   - Structured Pydantic validation requiring exact cited quotes from the posting.

### Critical Framing & Disclaimer
- Results are always framed as **objective risk indicators with cited evidence**, never as unqualified factual claims about a company.
- A permanent disclaimer informs users that this is a heuristic decision-support signal, not a definitive verification.

## Engineering rules (apply at every stage)

- Don't over-engineer the first version.
- Don't store every conversation as memory.
- Never let the LLM directly execute database mutations.
- Validate structured LLM outputs with Pydantic.
- Keep memory retrieval separate from conversation history.
- Keep current conversation context separate from long-term memory.
- Track memory versions.
- Make memory deletion reliable.
- Never fabricate memory — if nothing relevant exists, say so.

