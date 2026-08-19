# malloc() — AI Career Intelligence Engine

`SYS_CORE_v2.4` · `AI CAREER OS` · `86/86 pytests passing`

An autonomous AI career intelligence system that constructs persistent memory of who you are, evaluates job opportunities against your resume, audits ATS parseability, shields you from scam postings, researches companies, and drafts outreach — all wired into one FastAPI backend with a terminal-styled web UI.

---

## Why "malloc()"

Named after the C memory-allocation primitive — because that's exactly what the core of this system does: it allocates persistent memory for facts about you (skills, preferences, career history) as you talk to it, the same way `malloc()` reserves memory for a program to use later.

## What it does

malloc() is not a single chatbot — it's a pipeline of purpose-built modules that cover the full job-search loop:

| Stage | Module | What it does |
|---|---|---|
| 1 | **Job Ingestion** | Paste a job posting (URL, raw text, even informal WhatsApp/LinkedIn-style text) |
| 2 | **JD Parsing** | Extracts role, required skills, recruiter contact, and company from unstructured text |
| 3 | **Fit Analysis** | Scores your resume against the role, surfaces matched vs. missing keywords, and generates a fit percentage with reasoning |
| 4 | **ATS Audit** | Rule-based structure/format checks plus BERT entity extraction to estimate how well a resume will survive an Applicant Tracking System |
| 5 | **Scam Shield** | 3-layer authenticity check (heuristic red-flags → BERT spam classifier → RAG-based fraud-pattern reasoning) that rates a posting's risk before you apply |
| 6 | **Company Intel** | Zero-shot company size/industry classification plus sentiment analysis on culture, with an interview-prep blueprint generated per company |
| 7 | **AI Outreach** | Drafts a tailored, resume-grounded application email (with an anti-fabrication guardrail so it never invents experience you don't have), sent via Gmail OAuth — **never auto-sends** without your review |
| 8 | **Job Tracker** | Logs every application, tracks status, and surfaces follow-ups that are due |

Everything you tell the AI Assistant — skills, preferences, background facts — is continuously extracted into a persistent **Memory Vault**, so later modules (fit analysis, outreach drafting) can draw on it automatically instead of you re-explaining yourself every time.

## Core principles

- **Never fabricates.** The outreach drafter is explicitly grounded in your actual resume text — every claim in a drafted email is checked against what you've actually said, not invented to sound impressive.
- **Never auto-sends.** Gmail integration uses the `gmail.send` OAuth2 scope specifically so the system can send on your behalf *only after* you've reviewed and approved a draft — it cannot act autonomously on your inbox.
- **Classification failures never block core actions.** If a scam-check, fit-score, or entity-extraction model fails or times out, the module degrades gracefully rather than preventing you from applying or continuing.

## System modules

- 🧠 **AI Assistant** — conversational interface; every fact you share is auto-extracted into long-term memory
- 🗄️ **Memory Vault** — persistent, structured store of extracted facts/skills/preferences with full CRUD
- 📄 **Resume Matcher** — deep multi-dimensional fit scoring, skill-gap detection, concrete bullet-rewrite suggestions
- 🛡️ **ATS Parseability Audit** — deterministic layout/section checks + BERT entity-signal extraction
- 🔒 **Job Authenticity Shield** — rule-based heuristics + BERT spam classifier + RAG fraud-pattern reasoning
- 🏢 **Company Insights** — zero-shot size/industry classification, culture sentiment, interview-prep blueprint
- ✉️ **Apply via Email** — informal JD parsing → resume-grounded draft → fabrication audit → Gmail OAuth send
- 💼 **Job Tracker** — application log, status pipeline, and follow-up due-dates

## Architecture

```
                Web UI (Terminal/HUD style, Tailwind, Vanilla JS)
                              │
                    REST / JSON (async HTTP)
                              │
          FastAPI Unified Gateway Service (Python 3.11)
              (Pydantic v2 strict validation, modular routers)
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  Memory Engine          ML Pipelines           LLM Engine
  • Extraction           • BERT NER/Spam        • Groq Llama-3.1
  • Synthesis            • BART Zero-Shot       • Anti-cliché
  • CRUD store           • DistilBERT SST-2     • Anti-fabrication
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
          Persistence & Integrations
          SQLAlchemy ORM + SQLite · Google OAuth2 (gmail.send)
          · Faster-Whisper (voice) · BLIP (vision)
```

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11 |
| LLM inference | Groq (Llama 3.1, 8B/70B) |
| ML classifiers | BERT (NER, spam detection), BART (zero-shot classification), DistilBERT (SST-2 sentiment) |
| Voice / Vision | Faster-Whisper (speech-to-text), BLIP (image captioning) |
| Auth & email | Google OAuth2, `gmail.send` scope only |
| Data layer | SQLAlchemy ORM over SQLite |
| Frontend | Vanilla JS + Tailwind, terminal/HUD-styled interface |
| Validation | Pydantic v2 |
| Testing | pytest — 86/86 passing |

## API documentation

Interactive OpenAPI/Swagger docs are available at `/docs` once the backend is running.

## Local setup

```bash
git clone <this-repo-url>
cd malloc

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env        # fill in GROQ_API_KEY and Google OAuth credentials

uvicorn app.main:app --reload
```

Then open the frontend (`streamlit run streamlit_app.py`, or the web UI's entry point, depending on your current frontend) and visit the local URL it prints.

## Roadmap / not yet built

- Weekly/monthly application reports (reply rate, callback rate over time)
- Resume field extraction into structured profile data (education, contact details)
- Background reminder delivery (current follow-up reminders are surfaced when you open the Job Tracker, not pushed proactively)

## License

_Add your license here._
