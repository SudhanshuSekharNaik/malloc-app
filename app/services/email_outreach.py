"""
Memora — Email Outreach & Apply via Email Service
Multi-step pipeline:
- Step 1: Hybrid informal/emoji job posting parsing (Regex + LLM fallback).
- Step 2: Role selection & resume alignment recommendation.
- Step 3: Humanly-written application email drafting grounded strictly in resume facts,
  enforcing anti-cliché blocklist, skill fabrication guards, and weak secondary detector signal.
- Step 4: Review and send via official Gmail API with OAuth2 (gmail.send scope ONLY).
"""
import re
import sys
import json
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.llm import call_llm, LLMError
from app.services.scraper import fetch_url_content

# Suppress Windows torchvision DLL initialization crash
if "torchvision" not in sys.modules:
    sys.modules["torchvision"] = None

logger = logging.getLogger("memora.email_outreach")

# OAuth2 Constants
# NOTE: Scope is strictly limited to gmail.send (send-only).
# Under no circumstances should gmail.readonly or full mailbox access be requested.
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_SEND_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

# Maintained Anti-Cliché Blocklist for Application Emails
# Overused corporate tropes that sound robotic or overly formal for informal/direct job postings
CLICHE_BLOCKLIST: List[str] = [
    "i am writing to express my interest in",
    "i believe i would be a great fit for this position",
    "please find my resume attached for your consideration",
    "i look forward to hearing from you",
    "to whom it may concern",
    "dear hiring manager",
    "with great enthusiasm",
    "esteemed organization",
    "dynamic and fast-paced environment",
    "proven track record of success",
    "humble applicant",
    "synergies",
    "in reference to your job posting",
    "allow me to introduce myself",
    "i am thrilled to apply",
    "i am confident that my skills",
    "best regards,"
]

DETECTOR_MODEL_NAME = "openai-community/roberta-base-openai-detector"
ROLE_MODEL_NAME = "srivihari/resume-job-role-classifier"
NER_MODEL_NAME = "yashpwr/resume-ner-bert-v2"


# ============================================================================
# Lazy-Loaded HuggingFace Transformers Pipelines
# ============================================================================

def _safe_import_transformers_pipeline():
    from transformers import pipeline
    return pipeline


@lru_cache(maxsize=1)
def _get_detector_pipeline():
    """
    Lazy-loads openai-community/roberta-base-openai-detector if locally cached.
    
    IMPORTANT CAVEAT / MAINTENANCE NOTE:
    This model was trained specifically on GPT-2 era outputs. Its accuracy against modern
    frontier LLMs (Llama-3, Claude, GPT-4) is modest, and developer documentation explicitly notes
    it is not intended as a standalone authoritative detector.
    
    In this app, it is used strictly as a weak, non-blocking diagnostic signal ("secondary AI-style signal").
    The primary human-feel assurance comes from prompt engineering and the maintained CLICHE_BLOCKLIST.
    """
    try:
        pipeline = _safe_import_transformers_pipeline()
        return pipeline("text-classification", model=DETECTOR_MODEL_NAME, model_kwargs={"local_files_only": True})
    except Exception as exc:
        logger.info("AI Detector model not loaded locally: %s. Using heuristic signal.", exc)
        return None


@lru_cache(maxsize=1)
def _get_role_classifier_pipeline():
    """Lazy-loads srivihari/resume-job-role-classifier if locally cached."""
    try:
        pipeline = _safe_import_transformers_pipeline()
        return pipeline("text-classification", model=ROLE_MODEL_NAME, model_kwargs={"local_files_only": True})
    except Exception as exc:
        logger.info("Role classifier not loaded locally: %s. Using domain keyword alignment.", exc)
        return None


@lru_cache(maxsize=1)
def _get_ner_pipeline():
    """Lazy-loads yashpwr/resume-ner-bert-v2 token classification pipeline if locally cached."""
    try:
        pipeline = _safe_import_transformers_pipeline()
        return pipeline("token-classification", model=NER_MODEL_NAME, aggregation_strategy="simple", model_kwargs={"local_files_only": True})
    except Exception as exc:
        logger.info("Resume NER model not loaded locally: %s. Using regex keyword extraction.", exc)
        return None


# ============================================================================
# Step 1 — Hybrid Informal JD Parser (Emoji/Keyword Regex + LLM Fallback)
# ============================================================================

def parse_informal_jd_regex(text: str) -> Dict[str, Any]:
    """
    Fast, deterministic regex parser for emoji-bulleted & informal job postings.
    Extracts company, positions, experience, location, working days, HR email, and contact phone.
    """
    result: Dict[str, Any] = {
        "company_name": None,
        "open_positions": [],
        "experience_required": None,
        "location": None,
        "working_days": None,
        "hr_email": None,
        "contact_phone": None,
        "raw_text": text,
        "extraction_confidence": "low"
    }

    if not text or not text.strip():
        return result

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # 1. HR Email extraction (Anchor on 📧 or standard email pattern)
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", text)
    if email_match:
        result["hr_email"] = email_match.group(0).strip()

    # 2. Contact Phone extraction (Anchor on 📞, 📱, Contact, Phone or international format)
    phone_match = re.search(
        r"(?:📞|📱|Contact|Phone|WhatsApp|Call)?[:\s]*((?:\+?\d{1,3}[-.\s]?)?\(?\d{2,5}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5})",
        text,
        re.I
    )
    if phone_match:
        cand_phone = phone_match.group(1).strip()
        # Verify it has at least 8 digits
        if len(re.sub(r"\D", "", cand_phone)) >= 8:
            result["contact_phone"] = cand_phone

    # 3. Line-by-line parsing for emoji & keyword anchors
    in_positions_block = False
    extracted_positions: List[str] = []

    for line in lines:
        # Check company line (🏢 or 'Company:')
        if re.search(r"^(?:🏢|🏢\s*Company|Company|Client|Organization)\s*[:\-]\s*(.+)", line, re.I):
            m = re.search(r"^(?:🏢|🏢\s*Company|Company|Client|Organization)\s*[:\-]\s*(.+)", line, re.I)
            result["company_name"] = m.group(1).strip()
            in_positions_block = False
            continue
        elif "🏢" in line and not result["company_name"]:
            cleaned = re.sub(r"^[🏢\s:–\-]+", "", line).strip()
            if cleaned:
                result["company_name"] = cleaned
            in_positions_block = False
            continue

        # Check positions header (💼 or 'Open Positions:' / 'Positions:')
        pos_header_match = re.search(
            r"^(?:💼\s*(?:Open\s+Positions?|Positions?|Hiring\s+for|Roles?|Vacanc(?:y|ies))?|Open\s+Positions?|Positions?|Hiring\s+for|Roles?|Vacanc(?:y|ies)|💼)\s*[:\-]?\s*(.*)",
            line,
            re.I
        )
        if pos_header_match and (
            "💼" in line or any(k in line.lower() for k in ("position", "hiring", "role", "vacancy", "vacancies"))
        ):
            in_positions_block = True
            rest = pos_header_match.group(1).strip()
            # If rest has actual position names (not just header labels)
            if rest and not re.match(r"^(?:Open\s+Positions?|Positions?|Roles?|Vacanc(?:y|ies))\s*[:\-]?$", rest, re.I):
                items = [p.strip() for p in re.split(r"[,/|;]", rest) if p.strip()]
                for item in items:
                    if not re.match(r"^(?:Open\s+Positions?|Positions?|Roles?|Vacanc(?:y|ies))\s*[:\-]?$", item, re.I):
                        extracted_positions.append(item)
            continue

        # If inside positions block, collect bulleted items
        if in_positions_block:
            # If line starts another emoji header, exit positions block
            if any(emoji in line for emoji in ("🎯", "📍", "🗓️", "📅", "📧", "✉️", "📞", "📱", "💰", "💵", "🕒")):
                in_positions_block = False
            elif line.startswith(("*", "-", "•", "–", "—", "▪", "+")) or re.match(r"^\d+[\.\)]\s+", line):
                pos = re.sub(r"^(?:[*\-•–—▪+]|\d+[\.\)])\s*", "", line).strip()
                if pos and len(pos) < 60 and not re.match(r"^(?:Open\s+Positions?|Positions?|Roles?|Vacanc(?:y|ies))\s*[:\-]?$", pos, re.I):
                    extracted_positions.append(pos)
                continue
            elif len(line) < 45 and not line.endswith(":") and not any(k in line.lower() for k in ("experience", "location", "apply", "contact")):
                if not re.match(r"^(?:Open\s+Positions?|Positions?|Roles?|Vacanc(?:y|ies))\s*[:\-]?$", line.strip(), re.I):
                    extracted_positions.append(line.strip())
                continue
            else:
                in_positions_block = False

        # Experience (🎯 or 'Experience:')
        if re.search(r"(?:🎯|Experience|Exp|Eligibility)\s*[:\-]\s*(.+)", line, re.I):
            m = re.search(r"(?:🎯|Experience|Exp|Eligibility)\s*[:\-]\s*(.+)", line, re.I)
            result["experience_required"] = m.group(1).strip()
            continue

        # Location (📍 or 'Location:')
        if re.search(r"(?:📍|Location|Place|Job Location|Work Location)\s*[:\-]\s*(.+)", line, re.I):
            m = re.search(r"(?:📍|Location|Place|Job Location|Work Location)\s*[:\-]\s*(.+)", line, re.I)
            result["location"] = m.group(1).strip()
            continue

        # Working Days / Hours (🗓️, 📅, 'Working Days:')
        if re.search(r"(?:🗓️|📅|Working Days|Working Hours|Schedule|Days)\s*[:\-]\s*(.+)", line, re.I):
            m = re.search(r"(?:🗓️|📅|Working Days|Working Hours|Schedule|Days)\s*[:\-]\s*(.+)", line, re.I)
            result["working_days"] = m.group(1).strip()
            continue

    # Deduplicate and clean positions
    cleaned_positions = []
    header_blacklist = {"open positions", "positions", "open position", "position", "role", "roles", "vacancies", "vacancy"}
    for p in extracted_positions:
        p_clean = re.sub(r"\s+", " ", p).strip().rstrip(":")
        if p_clean and p_clean.lower() not in header_blacklist and p_clean not in cleaned_positions:
            cleaned_positions.append(p_clean)
    result["open_positions"] = cleaned_positions

    # Check confidence
    if result["company_name"] and (result["open_positions"] or result["hr_email"]):
        result["extraction_confidence"] = "high"
    elif result["open_positions"] or result["hr_email"]:
        result["extraction_confidence"] = "moderate"

    return result


def parse_informal_jd_llm_fallback(text: str) -> Dict[str, Any]:
    """
    LLM structured JSON parser fallback when regex extraction confidence is low.
    """
    system_prompt = """You are a specialized Job Description Information Extraction Engine.
Parse the provided informal / social media / WhatsApp job posting into a structured JSON object.

Output MUST be a valid JSON object strictly matching this schema:
{
  "company_name": "Company Name",
  "open_positions": ["Position 1", "Position 2"],
  "experience_required": "e.g. 0-1 Year / Freshers",
  "location": "City, Area or Remote",
  "working_days": "e.g. 5 Days a Week",
  "hr_email": "email@domain.com or null",
  "contact_phone": "+91 9999999999 or null",
  "extraction_confidence": "high"
}

Do not include markdown fences or any other conversational text."""

    try:
        raw_res = call_llm([{"role": "user", "content": f"Job Posting Text:\n\n{text}"}], system=system_prompt)
        json_match = re.search(r"\{[\s\S]*\}", raw_res)
        if json_match:
            data = json.loads(json_match.group(0))
            data["raw_text"] = text
            if "open_positions" in data and isinstance(data["open_positions"], list):
                data["open_positions"] = [p.strip() for p in data["open_positions"] if p and p.strip()]
            return data
    except Exception as exc:
        logger.warning("LLM JD parser fallback failed: %s", exc)

    return {"raw_text": text, "open_positions": [], "extraction_confidence": "low"}


def parse_informal_jd(text: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
    """
    Main Step 1 Parser:
    1. If URL is given, fetches text via scraper.
    2. Runs hybrid regex parser.
    3. If regex extraction confidence is low or positions list is empty, merges with LLM extraction.
    """
    raw_content = (text or "").strip()

    # If URL is provided, fetch page content
    if url and url.strip():
        try:
            fetched_text = fetch_url_content(url.strip())
            if fetched_text:
                raw_content = f"{raw_content}\n\n{fetched_text}".strip() if raw_content else fetched_text
        except Exception as exc:
            logger.warning("Could not fetch JD URL %s: %s", url, exc)

    if not raw_content:
        return {
            "company_name": None,
            "open_positions": [],
            "experience_required": None,
            "location": None,
            "working_days": None,
            "hr_email": None,
            "contact_phone": None,
            "raw_text": "",
            "extraction_confidence": "low"
        }

    # Step 1a: Fast regex extraction
    regex_res = parse_informal_jd_regex(raw_content)

    # Step 1b: If regex got high confidence and non-empty positions, return directly
    if regex_res.get("extraction_confidence") == "high" and regex_res.get("open_positions"):
        return regex_res

    # Step 1c: Try LLM extraction if LLM key configured and regex had missing critical fields
    if not regex_res.get("open_positions") or not regex_res.get("company_name"):
        llm_res = parse_informal_jd_llm_fallback(raw_content)
        # Merge results, prioritizing non-null values
        for k, v in llm_res.items():
            if v and (not regex_res.get(k) or k == "open_positions"):
                regex_res[k] = v
        if regex_res.get("open_positions"):
            regex_res["extraction_confidence"] = "moderate"

    return regex_res


# ============================================================================
# Step 2 — Role Selection & Resume Alignment Recommendation
# ============================================================================

def recommend_role_for_resume(positions: List[str], resume_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Evaluates which of the listed positions closest matches the candidate's resume.
    Uses srivihari/resume-job-role-classifier or keyword alignment.
    Returns (recommended_role_name, recommendation_reason).
    """
    if not positions:
        return None, None
    if len(positions) == 1:
        return positions[0], "Single position listed in job posting."

    if not resume_text or len(resume_text.strip()) < 40:
        return positions[0], "Defaulting to first listed position."

    resume_lower = resume_text.lower()
    best_role = positions[0]
    best_score = -1
    best_matched_terms = []

    # Common domain keyword associations
    domain_map = {
        "android": ["android", "kotlin", "java", "gradle", "jetpack", "mobile", "xml", "sdk", "apk"],
        "ios": ["ios", "swift", "swiftui", "objective-c", "xcode", "cocoapods", "mobile", "uikit"],
        "web": ["html", "css", "javascript", "typescript", "react", "vue", "angular", "node", "frontend", "web"],
        "graphic": ["photoshop", "illustrator", "figma", "canva", "ui/ux", "branding", "typography", "graphic", "design"],
        "python": ["python", "django", "fastapi", "flask", "pandas", "numpy", "sqlalchemy"],
        "backend": ["api", "database", "sql", "postgresql", "rest", "backend", "microservices", "redis"],
        "qa": ["qa", "testing", "selenium", "pytest", "cypress", "manual testing", "automation"],
        "flutter": ["flutter", "dart", "cross-platform", "mobile"]
    }

    for pos in positions:
        pos_lower = pos.lower()
        score = 0
        matched_keywords = []

        # Check exact words in position title
        for word in re.findall(r"\w+", pos_lower):
            if len(word) > 2 and word in resume_lower:
                score += 3
                matched_keywords.append(word)

        # Check mapped technical domain terms
        for domain, keywords in domain_map.items():
            if domain in pos_lower:
                for kw in keywords:
                    if re.search(r"\b" + re.escape(kw) + r"\b", resume_lower):
                        score += 1
                        if kw not in matched_keywords:
                            matched_keywords.append(kw)

        if score > best_score:
            best_score = score
            best_role = pos
            best_matched_terms = matched_keywords

    reason = (
        f"Your resume matches key proficiencies for {best_role} "
        f"({', '.join(best_matched_terms[:3]) if best_matched_terms else 'strongest background overlap'})."
    )
    return best_role, reason


# ============================================================================
# Step 3 — Anti-Cliché Blocklist & Fabrication Guardrail
# ============================================================================

def check_cliches(text: str) -> List[str]:
    """
    Checks drafted email text against the maintained CLICHE_BLOCKLIST.
    Returns list of matched cliché strings found.
    """
    if not text:
        return []
    text_lower = text.lower()
    matched = []
    for phrase in CLICHE_BLOCKLIST:
        if phrase in text_lower:
            matched.append(phrase)
    return matched


def extract_technical_nouns(text: str) -> List[str]:
    """
    Extracts technical terms, tools, libraries, certifications, and metrics from text.
    Uses resume NER model if available, plus curated tech regex.
    """
    found_terms: Set[str] = set()

    # 1. Regex technical dictionary matching
    tech_patterns = [
        r"\b(?:Python|Java|C\+\+|Golang|Rust|Swift|Kotlin|Dart|PHP|Ruby|TypeScript|JavaScript|SQL)\b",
        r"\b(?:React|Next\.js|Vue|Angular|FastAPI|Django|Flask|Spring Boot|Express|Node\.js|Flutter)\b",
        r"\b(?:Docker|Kubernetes|AWS|GCP|Azure|Terraform|CI/CD|PostgreSQL|MySQL|MongoDB|Redis|GraphQL|REST)\b",
        r"\b(?:Figma|Photoshop|Illustrator|Canva|Android Studio|Xcode|Git|GitHub|Linux|Jira|SQLite|Jetpack Compose)\b",
        r"\b(?:Machine Learning|Deep Learning|PyTorch|TensorFlow|LLM|RAG|LangChain|NLP|Computer Vision)\b",
        r"\b(?:\d+\+?\s*(?:years?|yrs?|months?|users?|QPS|SLA|%|percent|projects?|clients?))\b"
    ]

    for pat in tech_patterns:
        for m in re.finditer(pat, text, re.I):
            term = m.group(0).strip()
            if len(term) >= 2:
                found_terms.add(term)

    # 2. HuggingFace NER token extraction if available
    ner = _get_ner_pipeline()
    if ner is not None:
        try:
            entities = ner(text[:1500])
            for ent in entities:
                grp = ent.get("entity_group", "").lower()
                w = ent.get("word", "").strip()
                if grp in ("skill", "designation", "degree") and len(w) >= 2:
                    # Clean up noisy multi-word BERT spans (e.g. remove verbs/prepositions)
                    cleaned_subterms = re.split(r"\b(?:focuses|focusing|focus|with|using|in|on|and|for|by|from|to|my|our|their|a|an|the|is|are|have|has)\b", w, flags=re.I)
                    for sub in cleaned_subterms:
                        sub = sub.strip()
                        if len(sub) >= 2 and sub.lower() not in COMMON_EXCLUSIONS:
                            found_terms.add(sub)
        except Exception:
            pass

    return sorted(list(found_terms), key=lambda x: len(x), reverse=True)


COMMON_EXCLUSIONS = {
    "team", "role", "background", "experience", "work", "projects", "project", "application",
    "developer", "engineer", "software", "code", "call", "intern", "company",
    "systems", "system", "details", "applicant", "hiring", "position", "positions", "opening", "samples",
    "databases", "database", "stack", "environment", "environments", "review",
    "hi", "hello", "best", "regards", "thanks", "sincerely", "candidate", "internship"
}


def check_email_fabrications(
    draft_body: str,
    resume_text: str,
    jd_text: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Validates that proper nouns, technical tools, skills, and metrics in the email draft
    are traceable to the user's resume text or the JD itself.
    Flags any ungrounded assertions for user review before sending.
    """
    flags: List[Dict[str, str]] = []
    if not draft_body or not resume_text:
        return flags

    resume_lower = resume_text.lower()
    jd_lower = (jd_text or "").lower()

    # Extract nouns & skills from draft
    draft_terms = extract_technical_nouns(draft_body)

    for term in draft_terms:
        term_clean = term.strip()
        term_lower = term_clean.lower()

        # Skip generic conversational & structural words
        if term_lower in COMMON_EXCLUSIONS or len(term_clean) < 3:
            continue

        # Check if term is grounded in resume or JD
        in_resume = bool(re.search(r"\b" + re.escape(term_lower) + r"\b", resume_lower))
        in_jd = bool(re.search(r"\b" + re.escape(term_lower) + r"\b", jd_lower))

        # Also check individual keywords if multi-word term (e.g. "Android development")
        words = [w for w in re.findall(r"\w+", term_lower) if w not in COMMON_EXCLUSIONS and len(w) > 2]
        if words and all((w in resume_lower or w in jd_lower) for w in words):
            in_resume = True

        # If not present in resume and not present in JD context, flag it
        if not in_resume and not in_jd:
            # Find snippet in draft containing the ungrounded term
            snippet = ""
            for sentence in re.split(r"[.!?\n]", draft_body):
                if term_lower in sentence.lower():
                    snippet = sentence.strip()
                    break

            flags.append({
                "term": term_clean,
                "reason": f"'{term_clean}' was mentioned in the email draft but was not found in your uploaded resume.",
                "snippet": snippet or term_clean
            })

    return flags


def evaluate_ai_detector_score(text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Runs weak secondary detector signal on draft text.
    Surfaces clear documented caveats explaining that modern LLMs can trigger false signals.
    """
    try:
        detector = _get_detector_pipeline()
        if detector is not None:
            res = detector(text[:512])[0]
            label = res.get("label", "").lower()
            score = float(res.get("score", 0.0))

            # roberta-base-openai-detector returns Real vs Fake
            # If label is 'Fake' (AI-generated), fake score is score; if 'Real', fake score is 1 - score
            ai_prob = score if "fake" in label else (1.0 - score)
            note = (
                f"Secondary AI style signal: {round(ai_prob * 100)}% "
                f"(Diagnostic heuristic trained on GPT-2 — non-authoritative; anti-cliché blocklist provides primary check)."
            )
            return round(ai_prob, 2), note
    except Exception as exc:
        logger.warning("AI Detector execution failed: %s", exc)

    # Fast heuristic fallback based on cliches and sentence rhythm
    cliches = check_cliches(text)
    cliche_penalty = min(len(cliches) * 0.2, 0.6)
    est_prob = round(0.12 + cliche_penalty, 2)
    note = (
        f"Secondary AI style signal: {round(est_prob * 100)}% "
        f"(Diagnostic heuristic — anti-cliché blocklist provides primary check)."
    )
    return est_prob, note


# ============================================================================
# Step 3 — Draft Personalized Application Email
# ============================================================================

def generate_email_draft_prompt(
    resume_text: str,
    role_title: str,
    jd_data: Dict[str, Any],
    applicant_name: str,
    custom_instructions: Optional[str] = None
) -> Tuple[str, str]:
    """Constructs prompt pair for personalized, humanly written email draft."""
    company = jd_data.get("company_name") or "the hiring team"
    location = jd_data.get("location") or "the advertised location"
    exp = jd_data.get("experience_required") or "the required experience"

    system_prompt = f"""You are an expert career advisor writing a concise, authentic, human job application email for a candidate applying to an informal job posting.

NON-NEGOTIABLE WRITING RULES:
1. Small-company informal register: Write in a natural, conversational, professional tone appropriate for a direct HR/founder email (WhatsApp/social media post context).
2. Concise: Keep the email body between 100 and 160 words across 3 short paragraphs.
3. GROUNDED IN REAL RESUME FACTS ONLY: Reference 1-2 specific, real technologies, projects, or accomplishments from the candidate's resume relevant to the '{role_title}' role. NEVER invent, hallucinate, or exaggerate any skill, company, degree, or metric not in the resume.
4. STRICT ANTI-CLICHÉ ENFORCEMENT: DO NOT USE ANY OF THESE CLICHÉS:
   - "I am writing to express my interest in..."
   - "I believe I would be a great fit for this position..."
   - "Please find my resume attached for your consideration..."
   - "I look forward to hearing from you..."
   - "To Whom It May Concern"
   - "Dear Hiring Manager"
   - "With great enthusiasm"
   - "Esteemed organization"
   - "Proven track record"
5. Opening: Start with a simple, friendly greeting (e.g. "Hi {company} team," or "Hi,").
6. Closing: Close simply with the applicant's name (e.g. "Best,\\n{applicant_name}").

OUTPUT FORMAT:
Reply ONLY with a JSON object:
{{
  "subject": "Application for {role_title} — {applicant_name}",
  "body": "Email body text here..."
}}
Do not include any conversational preamble or markdown backticks other than the raw JSON object."""

    user_prompt = f"""Candidate Name: {applicant_name}
Target Role: {role_title}
Company: {company}
Location: {location}
Required Experience: {exp}

Candidate Resume Text:
\"\"\"{resume_text[:2500]}\"\"\"

{f'Additional User Custom Notes: {custom_instructions}' if custom_instructions else ''}

Generate the personalized, grounded application email JSON now:"""

    return system_prompt, user_prompt


def _parse_llm_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """Robustly parses JSON objects from LLM responses even with literal newlines or markdown."""
    if not raw_text:
        return None
    json_match = re.search(r"\{[\s\S]*\}", raw_text)
    if json_match:
        cand = json_match.group(0)
        try:
            return json.loads(cand, strict=False)
        except Exception:
            pass
        # Fallback: extract subject and body via regex if strict parsing failed
        data = {}
        subj_m = re.search(r'"subject"\s*:\s*"([^"]+)"', cand)
        if subj_m:
            data["subject"] = subj_m.group(1).strip()
        body_m = re.search(r'"body"\s*:\s*"([\s\S]+?)"\s*\}', cand)
        if body_m:
            data["body"] = body_m.group(1).strip().replace('\\n', '\n')
        if data:
            return data
    return None


def draft_application_email(
    resume_text: str,
    selected_role: str,
    parsed_jd: Dict[str, Any],
    applicant_name: Optional[str] = None,
    custom_instructions: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes Step 3:
    1. Generates concise, grounded email draft via LLM.
    2. Runs anti-cliché blocklist; if clichés detected, regenerates once with explicit avoidance instructions.
    3. Runs fabrication guardrail against resume and JD.
    4. Evaluates secondary AI detector signal.
    """
    app_name = (applicant_name or "Applicant").strip()
    role = (selected_role or "Software Engineer").strip()
    company = parsed_jd.get("company_name") or "Hiring Team"
    hr_email = parsed_jd.get("hr_email")

    subject = f"Application for {role} — {app_name}"
    body = ""

    # 1. Attempt LLM generation
    system_p, user_p = generate_email_draft_prompt(resume_text, role, parsed_jd, app_name, custom_instructions)
    try:
        raw_res = call_llm([{"role": "user", "content": user_p}], system=system_p)
        data = _parse_llm_json(raw_res)
        if data:
            subject = data.get("subject", subject)
            body = data.get("body", "")
    except Exception as exc:
        logger.warning("LLM Email drafting failed: %s. Using heuristic template.", exc)

    # 2. Heuristic Fallback if LLM is unavailable or returned empty body
    if not body or len(body.strip()) < 30:
        skills = extract_technical_nouns(resume_text)
        top_skills = ", ".join(skills[:3]) if skills else "software engineering and application development"
        body = (
            f"Hi {company} team,\n\n"
            f"I saw your opening for the {role} position and wanted to connect directly. "
            f"My technical background centers on {top_skills}, building reliable applications and collaborating in agile teams.\n\n"
            f"Given your requirements ({parsed_jd.get('experience_required') or 'relevant experience'}), my recent projects align well with your tech stack.\n\n"
            f"Happy to share project samples or hop on a quick call at your convenience.\n\n"
            f"Best,\n{app_name}"
        )

    # 3. Check for clichés and regenerate once if found
    cliches = check_cliches(body)
    if cliches and len(body) > 50:
        try:
            avoid_instruction = f"IMPORTANT: Your previous draft contained forbidden clichés: {cliches}. Rewrite the email completely without these phrases."
            raw_retry = call_llm([{"role": "user", "content": f"{user_p}\n\n{avoid_instruction}"}], system=system_p)
            retry_data = _parse_llm_json(raw_retry)
            if retry_data:
                body = retry_data.get("body", body)
                subject = retry_data.get("subject", subject)
                cliches = check_cliches(body)
        except Exception:
            pass

    # 4. Check for fabrications against resume & JD
    fabrication_flags = check_email_fabrications(body, resume_text, parsed_jd.get("raw_text", ""))

    # 5. Evaluate weak secondary detector signal
    ai_score, ai_note = evaluate_ai_detector_score(body)

    return {
        "subject": subject,
        "body": body,
        "recipient": hr_email,
        "selected_role": role,
        "company_name": company,
        "flagged_fabrications": fabrication_flags,
        "cliches_detected": cliches,
        "ai_detector_score": ai_score,
        "ai_detector_note": ai_note
    }


# ============================================================================
# Step 4 — Google OAuth2 & Gmail API Sender (gmail.send scope ONLY)
# ============================================================================

def create_gmail_oauth_url(user_id: str, redirect_uri: Optional[str] = None) -> Tuple[str, str]:
    """
    Constructs the Google OAuth2 consent URL.
    Scope is strictly restricted to 'https://www.googleapis.com/auth/gmail.send' (send-only).
    Returns (auth_url, state_param).
    """
    client_id = settings.google_client_id.strip() if settings.google_client_id else ""
    red_uri = redirect_uri or settings.google_redirect_uri

    state_payload = base64.urlsafe_b64encode(json.dumps({"user_id": user_id}).encode()).decode()

    params = {
        "client_id": client_id,
        "redirect_uri": red_uri,
        "response_type": "code",
        "scope": f"{GMAIL_SEND_SCOPE} https://www.googleapis.com/auth/userinfo.email",
        "access_type": "offline",
        "prompt": "consent",
        "state": state_payload
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return auth_url, state_payload


def exchange_oauth_code(code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """
    Exchanges Google authorization code for access and refresh tokens.
    """
    client_id = settings.google_client_id.strip()
    client_secret = settings.google_client_secret.strip()
    red_uri = redirect_uri or settings.google_redirect_uri

    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET) are not configured in settings.")

    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": red_uri,
        "grant_type": "authorization_code"
    }

    with httpx.Client(timeout=10.0) as client:
        token_resp = client.post(GOOGLE_TOKEN_URL, data=payload)
        if token_resp.status_code != 200:
            err_data = token_resp.json() if "json" in token_resp.headers.get("content-type", "") else {}
            raise RuntimeError(f"OAuth token exchange failed: {err_data.get('error_description') or token_resp.text}")

        tokens = token_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Retrieve user email
        email_resp = client.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        user_email = email_resp.json().get("email") if email_resp.status_code == 200 else None

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "scopes": tokens.get("scope", GMAIL_SEND_SCOPE),
            "email": user_email
        }


def refresh_access_token_if_needed(token_record: Any, db: Any) -> str:
    """
    Refreshes access token if expired and updates database record.
    """
    now = datetime.now(timezone.utc)
    if token_record.expires_at and token_record.expires_at > (now + timedelta(seconds=60)):
        return token_record.access_token

    if not token_record.refresh_token:
        return token_record.access_token

    client_id = settings.google_client_id.strip()
    client_secret = settings.google_client_secret.strip()

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": token_record.refresh_token,
        "grant_type": "refresh_token"
    }

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(GOOGLE_TOKEN_URL, data=payload)
        if resp.status_code == 200:
            data = resp.json()
            token_record.access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            token_record.expires_at = now + timedelta(seconds=expires_in)
            db.commit()
            return token_record.access_token

    return token_record.access_token


def send_gmail_message(
    access_token: str,
    to_email: str,
    subject: str,
    body_text: str,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Builds MIME email message, encodes in base64url, and sends via official Gmail API REST endpoint.
    
    IMPORTANT SAFETY REQUIREMENT:
    This function is only called when the user explicitly triggers the Send action from the review step.
    Drafting an email never invokes this function.
    """
    if not to_email or "@" not in to_email:
        raise ValueError("A valid recipient email address is required to send an application.")
    if not subject or not subject.strip():
        raise ValueError("Email subject cannot be empty.")
    if not body_text or not body_text.strip():
        raise ValueError("Email body cannot be empty.")

    # 1. Create MIME message
    if attachment_bytes and attachment_filename:
        msg = MIMEMultipart()
        msg["To"] = to_email.strip()
        msg["Subject"] = subject.strip()
        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        part = MIMEApplication(attachment_bytes, Name=attachment_filename)
        part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
        msg.attach(part)
    else:
        msg = MIMEText(body_text, "plain", "utf-8")
        msg["To"] = to_email.strip()
        msg["Subject"] = subject.strip()

    # 2. Encode to base64url as required by Gmail API
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    # 3. Call Gmail API v1 messages.send
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    with httpx.Client(timeout=12.0) as client:
        resp = client.post(
            GMAIL_SEND_API_URL,
            headers=headers,
            json={"raw": raw_message}
        )

        if resp.status_code not in (200, 201):
            err_msg = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", resp.text)
            except Exception:
                pass
            raise RuntimeError(f"Gmail API send failed ({resp.status_code}): {err_msg}")

        result_data = resp.json()
        message_id = result_data.get("id", f"msg-{datetime.now(timezone.utc).timestamp()}")

        return {
            "success": True,
            "message_id": message_id,
            "recipient": to_email,
            "subject": subject,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
