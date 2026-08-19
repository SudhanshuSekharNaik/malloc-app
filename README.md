⚡ Malloc() — AI Career & Intelligence OS

<p align="center"><strong>An AI-powered career operating system combining long-term memory, GenAI, RAG, resume intelligence, ATS analysis, job-authenticity detection, company intelligence, personalized outreach, and application tracking.</strong></p>

<p align="center">
<a href="https://malloc-app.onrender.com/">🌐 Live Demo</a> •
<a href="https://malloc-app.onrender.com/docs">📚 API Docs</a> •
<a href="https://github.com/SudhanshuSekharNaik/malloc-app">💻 GitHub</a>
</p>

🚀 What is Malloc()?

Malloc() is a unified AI career-intelligence platform for managing the job-search lifecycle from one workspace.

Instead of building isolated tools for resume analysis, ATS checking, job research, fraud detection, email drafting, and application tracking, Malloc() connects them into a single workflow.

Job / Resume Input
       │
       ▼
┌──────────────────────────────┐
│     MALLOC() CAREER OS       │
├──────────────────────────────┤
│ AI Assistant + Memory Vault  │
│ Resume Matcher               │
│ ATS Parseability Audit       │
│ Job Authenticity Shield      │
│ Company Intelligence         │
│ AI Outreach + Gmail OAuth    │
│ Job Tracker + Follow-ups     │
└──────────────────────────────┘
       │
       ▼
Evidence-grounded career decisions

Principle: use AI to reduce repetitive career work while keeping important decisions and external actions under user control.

🌐 Live Application

Live Demo: https://malloc-app.onrender.com/

The deployed application exposes the AI Assistant, Memory Vault, Resume Matcher, ATS Checker, Job Authenticity Audit, Company Insights, Apply via Email, Job Tracker, and FastAPI Swagger/OpenAPI explorer.

✨ Core Capabilities

1. 🧠 AI Assistant + Long-Term Memory

Malloc() provides a conversational AI interface with persistent structured memory.

Capabilities:

Text conversations

Voice input support

Image attachment / captioning support

Structured memory extraction

Memory search and retrieval

Long-term facts, skills, experiences, and preferences

Pydantic validation for structured LLM output

Memory architecture

Conversation History
        │ extraction
        ▼
Structured Memory
 ├── Facts
 ├── Skills
 ├── Experiences
 └── Preferences
        │
        ▼
Vector Retrieval / RAG
        │
        ▼
Relevant Context → LLM

Conversation history and long-term memory are deliberately separated. The system does not treat every conversational message as permanent memory.

Reliability rule: memory extraction must never break the main chat flow. Extraction is best-effort and invalid model output is rejected rather than trusted blindly.

2. 🎯 Resume Matcher & AI Resume Editing

The Resume Matcher compares a candidate resume with a target job specification and produces an explainable fit analysis.

Resume → Profile ─────────────┐
                              ├→ Fit Analysis → Skill Gaps
Job Description → Extraction ┘                    │
                                                  ▼
                                      Tailoring Recommendations
                                                  │
                                                  ▼
                                           Suggested Edits
                                                  │
                                                  ▼
                                           Human Review

Features:

Resume upload and profile storage

Job description input

Semantic fit scoring

Matched keyword extraction

Critical skill-gap detection

Seniority-fit analysis

Tailoring recommendations

Per-bullet resume rewriting

Tailored outreach pitch

Job-tracker integration

Anti-fabrication guardrail

AI suggestions are validated against the source resume. Unsupported metrics, numbers, percentages, tools, technologies, and claims are flagged rather than silently inserted. Suggestions remain opt-in and can be accepted or dismissed individually.

3. 📄 ATS Parseability Audit

The ATS Checker evaluates whether a resume is structurally readable by Applicant Tracking Systems, independently of a specific job description.

Hybrid scoring

Resume
  ├── Deterministic Rules
  │    ├── File format
  │    ├── Section headers
  │    ├── Contact information
  │    ├── Tables / layout
  │    ├── Filename hygiene
  │    └── Length / density
  │
  └── NLP Signals
       ├── Entity extraction
       └── Role/domain classification
                │
                ▼
          ATS Parseability Score
                │
                ▼
       Prioritized Recommendations

Checks include PDF/TXT/DOCX compatibility, standard sections, contact detectability, LinkedIn/GitHub links, single-column layout, table risks, resume length, bullet scannability, entity extraction, and role coherence.

4. 🛡️ Job Authenticity Shield

A hybrid security engine evaluates job postings for employment-scam indicators.

Job Posting
     │
     ▼
Layer 1 — Rule-based red flags
     │
     ▼
Layer 2 — BERT classification
     │
     ▼
Layer 3 — RAG + LLM reasoning
     │
     ▼
Risk Score + Evidence

Layer 1 — deterministic checks

Detects signals including suspicious/free contact domains, Telegram/WhatsApp recruitment redirects, upfront payment requests, equipment-check patterns, URL shorteners, suspicious compensation language, and structural anomalies.

Layer 2 — ML signal

A BERT-based fake-vs-real job-posting classifier provides a secondary classification signal.

Layer 3 — RAG reasoning

A curated employment-fraud knowledge base is embedded and searched using vector similarity. Retrieved patterns are passed to the reasoning layer to produce evidence-grounded risk analysis.

Safety framing: authenticity results are risk indicators and decision-support signals, not definitive declarations that a company or posting is fraudulent.

5. 🏢 Company Intelligence

Company Insights provides multi-layer analysis of a company and potential role.

Company / Job Information
          │
          ▼
Zero-Shot Size Classification
          │
          ▼
Industry Classification
          │
          ▼
Culture / Sentiment Analysis
          │
          ▼
Interview Intelligence

Models

facebook/bart-large-mnli — zero-shot company-size classification

sampathkethineedi/industry-classification — industry classification

distilbert-base-uncased-finetuned-sst-2-english — sentiment analysis

Output

Company-size classification

Industry category

Confidence signals

Sentiment breakdown

Praised and criticized aspects

Interview focus areas

Hiring-process preparation

Targeted preparation tips

Grounding/disagreement warnings when signals conflict

6. ✉️ AI Outreach + Gmail

Malloc() converts informal job posts into structured, resume-grounded application workflows.

Informal Job Post
      ↓
Parse Posting
      ↓
Extract Company / Role / Contact
      ↓
Select Resume Profile
      ↓
Draft Personalized Email
      ↓
Fabrication Audit
      ↓
Human Review
      ↓
Gmail OAuth
      ↓
User-Initiated Send
      ↓
Job Tracker

The Gmail integration uses official Gmail API authorization, requires user authorization, keeps the draft editable, runs a fabrication audit, and does not silently auto-send applications. Users explicitly initiate the send action.

7. 📋 Job Tracker

Tracks applications and follow-up timelines.

Applied → Interview / No Response / Offer / Rejected

Tracked fields: company, role, application date, status, follow-up date, job URL, notes, technical notes, salary/referral information, and history.

API

POST   /jobs
GET    /jobs/{user_external_id}
GET    /jobs/{user_external_id}/due-followups
PATCH  /jobs/{job_id}
DELETE /jobs/{job_id}

The MVP uses pull-based follow-up checks rather than unnecessary background scheduler infrastructure.

🏗️ System Architecture

                     Web UI
             Cyber HUD / Tailwind / JS
                       │
                    REST/JSON
                       │
                       ▼
              ┌─────────────────┐
              │     FastAPI     │
              │ Unified Gateway │
              │   Python 3.11  │
              └────────┬────────┘
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
 Memory Engine    ML Pipelines      LLM Engine
 Extraction       BERT/BART         Groq / Llama
 Synthesis        DistilBERT        RAG
 Retrieval        SST-2             Guardrails
       │               │                │
       └───────────────┼────────────────┘
                       ▼
             Persistence / Storage
          SQLAlchemy ORM + SQLite
             FAISS Vector Index
                       │
                       ▼
             External Integrations
          Gmail OAuth2 / Hugging Face

🧰 Tech Stack

Backend

Python 3.11

FastAPI

Pydantic

SQLAlchemy

SQLite

Uvicorn

AI / ML

Groq LLM inference

Llama models

Hugging Face Transformers

BERT

BART

DistilBERT

Sentence Transformers

FAISS

RAG

Multimodal

faster-whisper — speech transcription

BLIP — image captioning

Frontend

HTML

CSS

JavaScript

Tailwind CSS

Cyber-HUD themed interface

Integrations

Gmail API

Google OAuth2

REST APIs

OpenAPI / Swagger

Deployment

Render

🔌 API Surface

Core

GET  /health
POST /chat
GET  /chat/{conversation_id}
GET  /memories/{user_external_id}

Multimodal

POST /media/transcribe
POST /media/caption

Resume / ATS

POST /ats/check
POST /api/ats/check
POST /matcher/suggest-edits
POST /api/resume/suggest-edits

Company Intelligence

POST /insights/analyze
POST /api/company/insights
GET  /insights/{company_name}

Job Authenticity

POST /authenticity/check
POST /api/jobs/authenticity-check

Job Tracker

POST   /jobs
GET    /jobs/{user_external_id}
GET    /jobs/{user_external_id}/due-followups
PATCH  /jobs/{job_id}
DELETE /jobs/{job_id}

Interactive API documentation: https://malloc-app.onrender.com/docs

🔐 Engineering & Safety Principles

Never allow an LLM to directly mutate the database.

Validate structured LLM outputs with Pydantic.

Never fabricate resume facts.

Keep conversation history separate from long-term memory.

Do not store every conversation as memory.

Make memory deletion reliable.

Keep external actions user-initiated.

Treat fraud detection as decision support, not definitive verification.

Fail gracefully when optional ML/model inference is unavailable.

Avoid unnecessary infrastructure in the MVP.

🧪 Testing

The current dashboard reports 86/86 tests passing (100%).

Run locally:

pytest tests/ -v

💻 Local Development

git clone https://github.com/SudhanshuSekharNaik/malloc-app.git
cd malloc-app
python -m venv .venv

Linux / macOS

source .venv/bin/activate

Windows

.venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Configure environment variables:

cp .env.example .env

Typical LLM configuration:

GROQ_API_KEY=your_key
LLM_PROVIDER=groq

Then start FastAPI:

uvicorn app.main:app --reload

Run the local UI according to the repository's configured frontend entry point.

For the deployed application, open:

https://malloc-app.onrender.com/

📁 High-Level Structure

malloc-app/
│
├── app/
│   ├── main.py
│   ├── memory_extraction.py
│   ├── speech.py
│   ├── vision.py
│   ├── vectorstore.py
│   └── ...
│
├── tests/
├── streamlit_app.py
├── requirements.txt
├── .env.example
└── README.md

🎯 Why Malloc() is Different

Most career tools solve one problem:

Resume Analyzer
OR
ATS Checker
OR
Job Tracker
OR
Company Research
OR
Email Generator

Malloc() connects these workflows:

AI Assistant
      │
Memory Vault
      │
      ├── Resume Matcher
      ├── ATS Checker
      └── Job Authenticity
               │
               ▼
       Company Intelligence
               │
               ▼
          AI Outreach
               │
               ▼
          Job Tracker

The objective is to build a career operating system, not another standalone chatbot: AI understands the user's profile, evaluates opportunities, prepares applications, and maintains continuity across the job-search lifecycle.

🗺️ Roadmap

Implemented

AI career assistant

Structured long-term memory architecture

Memory extraction

Vector retrieval components

Resume matcher and fit scoring

Skill-gap analysis

AI resume edit suggestions

Anti-fabrication validation

ATS parseability audit

BERT entity signals

Job authenticity audit

Rule-based fraud detection

BERT fraud classification

RAG fraud reasoning

Company size classification

Industry classification

Culture/sentiment analysis

Interview intelligence

Personalized application email drafting

Gmail OAuth workflow

User-initiated email sending

Job application tracker

Follow-up tracking

Interactive Swagger/OpenAPI explorer

Deployed web application

Future improvements

Production-grade persistent vector database

Advanced memory consolidation

Temporal memory versioning

Explicit conflict-resolution workflows

Advanced retrieval/reranking

Larger evaluation benchmark suite

Background notification infrastructure

Additional job-board integrations

Production authentication / multi-user isolation

More multimodal career workflows

⚠️ Responsible Use

Malloc() provides AI-assisted career decision support. Users should review outputs, especially job-authenticity assessments, company intelligence, resume modifications, AI-generated outreach, and career recommendations.

The system should not be treated as a definitive authority on whether a company, job posting, or career decision is legitimate or appropriate.

📌 Project Information

Property

Value

Project

Malloc()

Version

v2.4

Category

AI Career Intelligence

Backend

FastAPI / Python

AI

LLM + Transformers + RAG

Database

SQLAlchemy / SQLite

Vector Search

FAISS

Multimodal

Whisper + BLIP

Email

Gmail API + OAuth2

Deployment

Render

License

MIT

👨‍💻 Author

Sudhanshu Sekhar Naik
B.Tech — Information Technology
AI/ML Engineer • Generative AI • Backend Engineering • Computer Vision

GitHub: https://github.com/SudhanshuSekharNaik

Project: https://github.com/SudhanshuSekharNaik/malloc-app

Live Demo: https://malloc-app.onrender.com/

📜 License

This project is licensed under the MIT License.
