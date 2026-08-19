Malloc() — AI Career & Intelligence OS

<p align="center">
  <b>A personal AI career operating system for resume intelligence, job analysis, company research, job-scam detection, personalized outreach, long-term memory, and application tracking.</b>
</p>

<p align="center">
  <a href="https://malloc-app.onrender.com/">Live Demo</a> ·
  <a href="https://malloc-app.onrender.com/docs">API Docs</a> ·
  <a href="https://github.com/SudhanshuSekharNaik/malloc-app">GitHub</a>
</p>

Overview

Malloc() is an AI-powered career intelligence platform that brings the major stages of a job search into one system.

Instead of treating resume matching, ATS analysis, company research, job authenticity, application drafting, and application tracking as separate tools, Malloc() connects them into an end-to-end workflow.

                         MALLOC()
                 AI CAREER INTELLIGENCE OS
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   Understand Me        Understand Jobs      Understand Companies
        │                     │                     │
        └──────────────┬──────┴──────────────┘
                       ▼
              Evaluate Opportunities
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Resume         ATS       Authenticity
       Matching      Audit        Shield
          │            │            │
          └────────────┼────────────┘
                       ▼
                Prepare Application
                       │
                       ▼
                 AI Outreach
                       │
                       ▼
                 Job Tracker

Core principle

AI handles repetitive analysis and preparation; the user remains in control of important decisions and external actions.

Live Application

Resource

Link

Live Website

https://malloc-app.onrender.com/

Swagger / OpenAPI

https://malloc-app.onrender.com/docs

GitHub Repository

https://github.com/SudhanshuSekharNaik/malloc-app

Features

1. AI Assistant & Memory Vault

Malloc() includes a conversational AI assistant with a separate long-term memory layer.

Capabilities

Conversational AI

Voice input

Image attachment / captioning

Structured memory extraction

Memory retrieval

Skills, facts, experiences, and preferences

Vector-based retrieval

Persistent user context

Pydantic validation for structured LLM output

Memory architecture

Conversation
     │
     ▼
LLM Response
     │
     ▼
Memory Extraction
     │
     ▼
Structured Entities
 ┌───┼───────────────┐
 ▼   ▼               ▼
Facts Skills    Experiences
     │
     ▼
Vector Index / Retrieval
     │
     ▼
Relevant Context
     │
     ▼
Future AI Responses

Conversation history and long-term memory are deliberately treated as separate concepts.

A key reliability rule is:

Memory extraction must never break the main chat experience.

Memory extraction runs as a best-effort operation and structured output is validated before persistence.

2. Resume Matcher

The Resume Matcher compares a candidate profile against a target job description and identifies technical and experience gaps.

Workflow

Resume
  │
  ├───────────────┐
  ▼               ▼
Profile        Job Description
  │               │
  └───────┬───────┘
          ▼
     Fit Analysis
          │
   ┌──────┴───────┐
   ▼              ▼
Matched        Missing /
Skills         Critical Gaps
   │              │
   └──────┬───────┘
          ▼
Tailoring Recommendations
          │
          ▼
Suggested Resume Edits
          │
          ▼
     User Review

Features

Resume upload

Job description ingestion

Semantic fit scoring

Skill extraction

Keyword matching

Critical-gap detection

Seniority-fit analysis

Resume bullet rewriting

Tailored outreach pitch

Application tracker integration

Anti-fabrication guardrail

Generated resume edits are checked against the original resume before being accepted.

The system is designed to avoid introducing unsupported:

Metrics

Numbers

Percentages

Technologies

Tools

Experience claims

Every suggested edit can be accepted or dismissed by the user.

3. ATS Parseability Audit

The ATS Checker focuses on whether a resume is structurally readable by Applicant Tracking Systems.

It combines deterministic rules with NLP-based signals.

Architecture

                     Resume
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      Deterministic Rules     NLP Signals
             │                   │
       ┌─────┼─────┐        ┌────┴────┐
       ▼     ▼     ▼        ▼         ▼
    Format Sections Layout  Entities  Role
    Contact Length  Bullets          Signals
             │                   │
             └─────────┬─────────┘
                       ▼
                ATS Parseability
                       │
                       ▼
             Priority Recommendations

Checks include

File format compatibility

Standard ATS section headers

Contact information detection

LinkedIn / GitHub detection

Single-column layout

Table/layout risks

Resume length

Bullet-point scannability

Skill/entity extraction

Job-role/domain signals

4. Job Authenticity Shield

A three-layer hybrid system evaluates potential employment-scam signals in job postings.

Job Posting
     │
     ▼
┌─────────────────────────┐
│ Layer 1                 │
│ Rule-Based Red Flags    │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ Layer 2                 │
│ BERT ML Classification  │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ Layer 3                 │
│ RAG + LLM Reasoning     │
└────────────┬────────────┘
             ▼
      Risk Assessment
      + Supporting Evidence

Rule-based signals

The system can evaluate signals including:

Suspicious contact channels

Telegram / WhatsApp recruitment

Upfront payment requests

Equipment-purchase patterns

URL-shortener usage

Suspicious compensation language

Structural anomalies

ML layer

A BERT-based classifier provides an additional fake-vs-real job-posting signal.

RAG layer

Fraud-related knowledge is embedded into a vector index and retrieved for evidence-grounded reasoning.

Important limitation

The authenticity result is a risk indicator, not definitive proof that a job or company is fraudulent.

5. Company Intelligence

Company Insights combines classification, sentiment analysis, and structured reasoning to generate a company-specific preparation brief.

Pipeline

Company / Job Information
          │
          ▼
Company Size
          │
          ▼
Industry Classification
          │
          ▼
Culture / Sentiment
          │
          ▼
Interview Intelligence
          │
          ▼
Preparation Blueprint

Models

Model

Purpose

facebook/bart-large-mnli

Zero-shot company-size classification

sampathkethineedi/industry-classification

Industry classification

distilbert-base-uncased-finetuned-sst-2-english

Sentiment analysis

Output

Company-size classification

Industry classification

Confidence signals

Sentiment breakdown

Positive / critical aspects

Interview focus areas

Hiring-process stages

Targeted preparation tips

6. AI Outreach & Gmail

Malloc() converts job information into a personalized, reviewable application workflow.

Job Posting
    │
    ▼
Parse Posting
    │
    ▼
Select Role
    │
    ▼
Draft Personalized Email
    │
    ▼
Fabrication Audit
    │
    ▼
Human Review
    │
    ▼
Gmail OAuth
    │
    ▼
User-Initiated Send
    │
    ▼
Job Tracker

Features

Informal job-post parsing

Role selection

Resume-grounded email drafting

Anti-fabrication audit

Resume attachment

Gmail OAuth2

Application logging

User-controlled sending

The application is not silently auto-sent. External email transmission requires explicit user action.

7. Job Tracker

The Job Tracker maintains application history and follow-up timelines.

Application lifecycle

Applied
  │
  ├── Interview
  ├── Offer
  ├── Rejected
  └── Follow-up

Stored information

Company

Role

Application date

Status

Follow-up date

Job URL

Notes

Referral information

Application history

API

POST   /jobs
GET    /jobs/{user_external_id}
GET    /jobs/{user_external_id}/due-followups
PATCH  /jobs/{job_id}
DELETE /jobs/{job_id}

System Architecture

┌─────────────────────────────────────────────────────┐
│                     WEB UI                          │
│          HTML / CSS / JavaScript / Tailwind         │
└─────────────────────────┬───────────────────────────┘
                          │
                       REST/JSON
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                    FASTAPI                          │
│              Unified API Gateway                    │
│                    Python 3.11                      │
└─────────────┬────────────────┬──────────────────────┘
              │                │
              ▼                ▼
       ┌────────────┐   ┌──────────────┐
       │   Memory   │   │  ML Pipelines│
       │   Engine   │   │              │
       ├────────────┤   ├──────────────┤
       │ Extraction │   │ BERT         │
       │ Synthesis  │   │ BART         │
       │ Retrieval  │   │ DistilBERT   │
       │ CRUD       │   │ Embeddings   │
       └─────┬──────┘   └──────┬───────┘
             │                 │
             └────────┬────────┘
                      ▼
               ┌─────────────┐
               │ LLM / RAG   │
               │ Groq        │
               │ Llama       │
               │ FAISS       │
               └──────┬──────┘
                      │
                      ▼
        ┌──────────────────────────────┐
        │ Persistence & Integrations  │
        │ SQLAlchemy / SQLite         │
        │ Google OAuth2 / Gmail API   │
        └──────────────────────────────┘

Tech Stack

Backend

Python 3.11

FastAPI

Pydantic

SQLAlchemy

SQLite

Uvicorn

AI / ML

Groq

Llama

Hugging Face Transformers

BERT

BART

DistilBERT

Sentence Transformers

FAISS

Retrieval-Augmented Generation

Multimodal

faster-whisper

BLIP

Frontend

HTML

CSS

JavaScript

Tailwind CSS

Cyber-HUD interface

Integrations

Gmail API

Google OAuth2

REST APIs

OpenAPI / Swagger

Deployment

Render

API Overview

The FastAPI backend exposes endpoints for the major career workflows.

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

Authenticity

POST /authenticity/check
POST /api/jobs/authenticity-check

Job Tracker

POST   /jobs
GET    /jobs/{user_external_id}
GET    /jobs/{user_external_id}/due-followups
PATCH  /jobs/{job_id}
DELETE /jobs/{job_id}

Interactive API documentation:
https://malloc-app.onrender.com/docs

Engineering Principles

Malloc() follows explicit guardrails around AI-generated output and external actions.

Principle

Implementation

Structured AI output

Pydantic validation

Memory isolation

Chat history separated from long-term memory

Anti-fabrication

Resume edits checked against source facts

User control

External email requires explicit send action

Fraud safety

Authenticity score treated as decision support

Fault tolerance

Optional memory/model failures do not break core flows

Minimal infrastructure

MVP avoids unnecessary background systems

Traceability

AI recommendations expose their supporting signals

Testing

The current system dashboard reports:

86 / 86 tests passing
100% passing

Run the test suite locally:

pytest tests/ -v

Local Setup

1. Clone

git clone https://github.com/SudhanshuSekharNaik/malloc-app.git
cd malloc-app

2. Create a virtual environment

Windows

python -m venv .venv
.venv\Scripts\activate

Linux / macOS

python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Configure environment variables

cp .env.example .env

Configure the required credentials in .env, including the LLM provider and Gmail OAuth configuration if those features are enabled.

Example:

GROQ_API_KEY=your_key
LLM_PROVIDER=groq

5. Start the API

uvicorn app.main:app --reload

6. Open API documentation

http://127.0.0.1:8000/docs

Project Structure

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
│
├── streamlit_app.py
├── requirements.txt
├── .env.example
├── README.md
└── ...

Roadmap

Implemented

AI career assistant

Structured long-term memory

Memory extraction and retrieval

Resume matcher

Semantic fit analysis

Skill-gap detection

AI resume edits

Anti-fabrication validation

ATS parseability audit

NLP entity signals

Job authenticity audit

Rule-based fraud detection

BERT fraud classification

RAG-based fraud reasoning

Company size classification

Industry classification

Sentiment analysis

Interview intelligence

Personalized application emails

Gmail OAuth workflow

User-controlled email sending

Job application tracker

Follow-up tracking

Swagger / OpenAPI documentation

Render deployment

Future

Production-grade vector database

Advanced retrieval / reranking

Memory consolidation and versioning

More robust model evaluation benchmarks

Background notification infrastructure

Additional job-board integrations

Production-grade authentication and tenant isolation

Expanded multimodal career workflows

Responsible Use

Malloc() is an AI-assisted career decision-support system.

Its outputs should be reviewed by the user before acting on them, especially:

Job authenticity assessments

Company intelligence

Resume modifications

AI-generated outreach

Career recommendations

The system does not guarantee that a job posting is legitimate, that a company is suitable, or that a recommendation will produce a particular career outcome.

Project Snapshot





Project

Malloc()

Version

v2.4

Category

AI Career Intelligence

Backend

FastAPI / Python

AI

LLM + NLP + RAG

ML

BERT / BART / DistilBERT

Vector Search

FAISS

Database

SQLAlchemy / SQLite

Multimodal

Whisper + BLIP

Email

Gmail API + OAuth2

Deployment

Render

Testing

86/86 passing

License

MIT

Author

Sudhanshu Sekhar Naik

AI/ML Engineer · Generative AI · Backend Engineering · Computer Vision

GitHub: https://github.com/SudhanshuSekharNaik

Malloc(): https://github.com/SudhanshuSekharNaik/malloc-app

Live Demo: https://malloc-app.onrender.com/

License

This project is licensed under the MIT License.
