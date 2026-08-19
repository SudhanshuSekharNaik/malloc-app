<div align="center">

# malloc()

### memory allocated for your career.

an ai that remembers you, checks your resume, sniffs out scam job posts,
and drafts your outreach — so you don't have to explain yourself 47 times a week.

[![live demo](https://img.shields.io/badge/demo-malloc--app.onrender.com-B4FF39?style=for-the-badge&logo=render&logoColor=black)](https://malloc-app.onrender.com/)
[![tests](https://img.shields.io/badge/pytest-86%2F86_passing-B4FF39?style=for-the-badge&logo=pytest&logoColor=black)](#)
[![python](https://img.shields.io/badge/python-3.11-8A8A9E?style=for-the-badge&logo=python&logoColor=white)](#)
[![fastapi](https://img.shields.io/badge/fastapi-async-8A8A9E?style=for-the-badge&logo=fastapi&logoColor=white)](#)
[![groq](https://img.shields.io/badge/llm-groq_llama_3.1-FF5C7A?style=for-the-badge&logo=lightning&logoColor=white)](#)

**[▶ try it live](https://malloc-app.onrender.com/)** · [what it does](#-what-it-actually-does) · [modules](#-modules) · [stack](#-stack) · [run it locally](#-run-it-locally)

</div>

<br>

> heads up: it's on render's free tier, so the first load after it's been idle
> takes ~30-60s to wake up. it's not broken, it's just yawning.

<br>

## 🧠 the pitch

most job-search tools make you fill out forms. malloc() just remembers.

talk to it like you'd talk to a friend who happens to have read your resume,
knows every scam-job red flag, and never gets tired of researching companies
at 2am. it builds a persistent memory of who you are, then uses that memory
across every other module — so your fit score, your outreach email, and your
ATS check are all grounded in the same actual you, not a generic template.

named after `malloc()`, the C function that reserves memory for a program to
use later. that's the whole bit — it allocates memory for *you*.

<br>

## ⚙️ what it actually does

```
job posting  ──▶  parsed  ──▶  scam-checked  ──▶  scored vs your resume
                                                          │
                                                          ▼
                                          company researched + interview prep
                                                          │
                                                          ▼
                                        outreach email drafted (grounded, not fabricated)
                                                          │
                                                          ▼
                                              logged in tracker + follow-up reminders
```

every step reads from and writes back to one shared **memory vault** — nothing
gets re-explained twice.

<br>

## 📦 modules

<details>
<summary><b>🤖 ai_assistant</b> — the thing you actually talk to</summary>
<br>

chat interface. every fact you mention — skills, preferences, background —
gets auto-extracted and dropped into your memory vault in the background.
you don't tag anything. you don't fill out a profile form. you just talk.

</details>

<details>
<summary><b>🗄️ memory_vault</b> — persistent structured memory</summary>
<br>

everything the assistant extracts, stored as structured entities with
confidence scores. full CRUD — see it, search it, edit it, delete it.
this is the thing every other module reads from.

</details>

<details>
<summary><b>📄 resume_matcher</b> — fit scoring that isn't vibes-based</summary>
<br>

deep comparative scoring between your resume and a target role. surfaces
matched keywords, critical missing keywords, seniority-fit gaps, and
concrete bullet-point rewrites — you approve each edit, nothing auto-applies.

</details>

<details>
<summary><b>🛡️ ats_checker</b> — will a bot even read your resume?</summary>
<br>

rule-based layout/format validation + BERT entity extraction, scored as a
single parseability index. catches the stuff that silently tanks resumes:
bad filenames, table-heavy layouts, missing section headers.

</details>

<details>
<summary><b>🔒 authenticity</b> — scam job shield</summary>
<br>

3-layer fraud check on any posting before you waste time on it:
heuristic red-flag rules → BERT spam classifier → RAG-based fraud-pattern
reasoning. outputs a plain risk score, not a black box.

</details>

<details>
<summary><b>🏢 company_insights</b> — know before you apply</summary>
<br>

zero-shot company size/industry classification, culture sentiment from
available signals, and an actual interview-prep blueprint per company —
not a generic "tips for interviews" page.

</details>

<details>
<summary><b>✉️ apply_via_email</b> — drafts, never sends without you</summary>
<br>

parses even messy/informal job posts (yes, including WhatsApp-forward-style
text), drafts a resume-grounded outreach email, runs it through a
fabrication audit so it never invents experience you don't have, then sends
via Gmail OAuth (`gmail.send` scope only) — **only after you review it.**

</details>

<details>
<summary><b>💼 job_tracker</b> — the follow-up you keep forgetting</summary>
<br>

logs every application with status, applied date, and follow-up due-date.
surfaces a reminder the moment something's overdue. no scheduler, no push
notifications — checks when you open the tab, which is honestly when you'd
actually act on it anyway.

</details>

<br>

## 🏗️ stack

<div align="center">

| layer | tech |
|:--|:--|
| backend | `FastAPI` · `Python 3.11` · `Pydantic v2` |
| llm | `Groq` — `Llama 3.1` (8B / 70B) |
| ml classifiers | `BERT` (NER + spam) · `BART` (zero-shot) · `DistilBERT` (sentiment) |
| voice / vision | `Faster-Whisper` · `BLIP` |
| auth | `Google OAuth2` — send-only scope |
| data | `SQLAlchemy` ORM over `SQLite` |
| frontend | vanilla JS + Tailwind, terminal/HUD aesthetic |
| tests | `pytest` — 86/86 green |

</div>

<br>

## 🔐 the rules it doesn't break

- **never fabricates.** outreach drafts are grounded in your actual resume text — checked, not improvised
- **never auto-sends.** every email needs your eyes on it first
- **never blocks on a failed classifier.** if a scam-check or fit-score model chokes, you can still apply — degrade, don't block

<br>

## 🚀 run it locally

```bash
git clone <this-repo-url>
cd malloc

python -m venv .venv
source .venv/bin/activate      # windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env           # drop in your GROQ_API_KEY + Google OAuth creds

uvicorn app.main:app --reload
```

or just skip all that → **[malloc-app.onrender.com](https://malloc-app.onrender.com/)**

<br>

## 🗺️ not built yet

- [ ] weekly/monthly reports (reply rate, callback rate over time)
- [ ] resume field extraction into structured profile (education, contact)
- [ ] push-based reminders (currently pull-based — checked on tab open)

<br>

<div align="center">

built by an engineer who kept forgetting which jobs they'd applied to.

`malloc()` — allocate once, remember forever.

</div>
