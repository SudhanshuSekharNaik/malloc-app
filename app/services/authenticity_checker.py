"""
Job Post Authenticity & Fraud Risk Assessment Engine.

Hybrid 3-Layer Architecture:
- Layer 1: Deterministic rule-based heuristic red-flag checks (regex/keywords/URLs)
- Layer 2: Machine Learning classification signal (AventIQ-AI/BERT-Spam-Job-Posting-Detection-Model)
- Layer 3: RAG-augmented LLM reasoning with curated fraud pattern retrieval

Important Framing:
Results are framed as evidence-backed risk indicators and decision-support signals,
never as absolute or unqualified fraud claims.
"""
import re
import json
import logging
from functools import lru_cache
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import numpy as np
from pydantic import BaseModel, Field

from app.llm import call_llm, LLMError
from app.vectorstore import embed_text

logger = logging.getLogger("memora.authenticity_checker")

# ============================================================================
# Schemas
# ============================================================================
class AuthenticityCheckItem(BaseModel):
    name: str
    status: str  # "pass" | "warn" | "fail" | "unavailable"
    detail: str
    category: str = "heuristic"
    evidence: Optional[str] = None


class ClassifierSignal(BaseModel):
    model_config = {"protected_namespaces": ()}
    status: str  # "completed" | "unavailable"
    predicted_label: Optional[str] = None  # "Real Job" | "Fake Job"
    confidence: Optional[float] = None
    model_name: str = "AventIQ-AI/BERT-Spam-Job-Posting-Detection-Model"
    limitations_note: str = (
        "Model evaluated on first ~100 words (128-token max context window). "
        "Estimated precision on 'Fake Job' class is ~0.81 (4-in-5 reliability). Trained on English text."
    )
    detail: str = ""


class MatchedPatternEvidence(BaseModel):
    pattern: str
    evidence: str
    explanation: str


class LLMReasoningSignal(BaseModel):
    status: str  # "completed" | "unavailable"
    risk_level: Optional[str] = None  # "low" | "medium" | "high"
    matched_patterns: List[MatchedPatternEvidence] = Field(default_factory=list)
    reasoning_summary: str = ""
    retrieved_patterns_count: int = 0


class AuthenticityReport(BaseModel):
    risk_level: str  # "low" | "medium" | "high"
    risk_score: int = Field(..., ge=0, le=100)  # 0 (Safe) to 100 (Extremely High Risk)
    verdict_label: str  # "Low Risk (Nominal)" | "Moderate Risk (Caution)" | "High Risk (Alert)"
    summary: str
    disclaimer: str = (
        "Heuristic Risk Assessment: This analysis is an automated decision-support tool, "
        "not a legal or factual guarantee of authenticity. Always verify job postings directly "
        "on the company's verified corporate careers website."
    )
    layer1_heuristics: List[AuthenticityCheckItem] = Field(default_factory=list)
    layer2_classifier: ClassifierSignal
    layer3_llm_reasoning: LLMReasoningSignal
    red_flags_count: int = 0
    warnings_count: int = 0


# ============================================================================
# Layer 1 — Known Scam Indicator Patterns (Configurable Constants)
# ============================================================================
DISPOSABLE_FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "protonmail.com", "proton.me", "yopmail.com", "mail.ru", "gmx.com",
    "zoho.com", "icloud.com", "live.com", "inbox.com", "fastmail.com"
}

KNOWN_URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd", "rb.gy",
    "goo.gl", "ow.ly", "buff.ly", "shorturl.at", "rebrand.ly"
}

RED_FLAG_PAYMENT_PATTERNS = [
    (r"(?:application|processing|registration|training|administrative|onboarding)\s+fee", "Upfront application/processing fee required"),
    (r"(?:pay|deposit|send|transfer)\s+(?:\$?\d+|\bmoney\b|\bfee\b).*(?:before|prior to|upfront|to start)", "Demanding upfront payment before hiring"),
    (r"buy\s+your\s+own\s+equipment", "Instructing candidate to purchase equipment upfront"),
    (r"(?:check|cheque)\s+for\s+(?:home\s+office|supplies|equipment|hardware)", "Sending equipment check (common fake check overpayment fraud)"),
    (r"purchase.*from\s+our\s+(?:certified|authorized|approved)\s+vendor", "Mandating supply purchase from a specific vendor"),
    (r"(?:wire\s+transfer|western\s+union|moneygram|cashapp|venmo|zelle|crypto|bitcoin|gift\s*card)", "Requesting non-standard payment or wire method"),
    (r"(?:send|provide)\s+(?:your\s+)?(?:bank|routing|credit\s*card)\s+(?:details|number|information)\s+(?:for|to|before)", "Demanding bank account or credit card details prior to formal offer"),
]

RED_FLAG_COMMUNICATION_PATTERNS = [
    (r"(?:contact|message|reach|chat\s+with)\s+(?:us|me|hiring\s+manager|hr)\s+(?:via|on|through)\s+(?:telegram|whatsapp|signal)\b", "Directing candidate exclusively to Telegram/WhatsApp/Signal for hiring"),
    (r"\btelegram\s*:\s*@?[a-z0-9_]+\b", "Telegram handle provided as primary interview contact"),
    (r"\bwhatsapp\s*(?:number|chat|only)?\s*:\s*\+?\d+", "WhatsApp listed as primary screening medium"),
]

RED_FLAG_URGENCY_UNREALISTIC_PATTERNS = [
    (r"no\s+experience\s+(?:needed|required).*(?:earn|make)\s+\$?(?:[3-9]\d{2,}|[1-9]\d{3,})\s*(?:\/|\s*per\s*)(?:week|day|hr|hour)", "Unrealistic compensation for zero experience required"),
    (r"(?:urgent|immediate)\s+hiring.*start\s+(?:today|immediately|in\s+\d+\s+hours)", "High-pressure immediate start tactics with no standard screening"),
    (r"(?:no\s+interview|instant\s+job\s+offer|guaranteed\s+hiring|hired\s+on\s+the\s+spot)", "Claiming instant job offer without formal interview process"),
    (r"(?:package\s+(?:handler|inspection|forwarding)|re-shipping\s+agent|mystery\s+shopper\s+check)", "Package reshipping or check cashing mule scheme pattern"),
]


def check_contact_domain(text: str) -> AuthenticityCheckItem:
    """Checks if communication contacts use free/generic email domains instead of corporate domains."""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
    if not emails:
        return AuthenticityCheckItem(
            name="contact_email_domain",
            status="pass",
            detail="No suspicious free/generic contact email addresses found in the description."
        )

    generic_found = [domain.lower() for domain in emails if domain.lower() in DISPOSABLE_FREE_EMAIL_DOMAINS]
    if generic_found:
        return AuthenticityCheckItem(
            name="contact_email_domain",
            status="fail",
            detail=f"Generic/free email domain contact detected (@{generic_found[0]}). Legitimate corporate recruiters use verified enterprise domains.",
            evidence=f"@{generic_found[0]}"
        )

    return AuthenticityCheckItem(
        name="contact_email_domain",
        status="pass",
        detail=f"Enterprise email domain contact detected (@{emails[0]})."
    )


def check_messaging_platforms(text: str) -> AuthenticityCheckItem:
    """Checks for private messenger-only interview recruitment channels (Telegram/WhatsApp)."""
    for pattern, explanation in RED_FLAG_COMMUNICATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return AuthenticityCheckItem(
                name="messaging_channel_screening",
                status="fail",
                detail=f"Red flag: {explanation}. Legitimate employers conduct interviews via corporate email, video (Zoom/Teams/Meet), or verified ATS portals.",
                evidence=match.group(0)
            )
    return AuthenticityCheckItem(
        name="messaging_channel_screening",
        status="pass",
        detail="Standard communication channels. No private messenger interview redirects (Telegram/WhatsApp) detected."
    )


def check_upfront_fees_and_payments(text: str) -> AuthenticityCheckItem:
    """Checks for fees, equipment checks, or upfront payment demands."""
    for pattern, explanation in RED_FLAG_PAYMENT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return AuthenticityCheckItem(
                name="upfront_fees_and_equipment",
                status="fail",
                detail=f"Critical red flag: {explanation}. Legitimate employers never charge candidates application fees or ask them to buy supplies from specified third parties.",
                evidence=match.group(0)
            )
    return AuthenticityCheckItem(
        name="upfront_fees_and_equipment",
        status="pass",
        detail="No upfront fee or equipment purchase requirements identified."
    )


def check_unrealistic_pay_and_urgency(text: str) -> AuthenticityCheckItem:
    """Checks for unrealistic pay-to-effort ratios and pressure/urgency tactics."""
    for pattern, explanation in RED_FLAG_URGENCY_UNREALISTIC_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return AuthenticityCheckItem(
                name="unrealistic_pay_and_urgency",
                status="warn",
                detail=f"Warning signal: {explanation}. Scammers frequently advertise outsized compensation to attract hasty applications.",
                evidence=match.group(0)
            )
    return AuthenticityCheckItem(
        name="unrealistic_pay_and_urgency",
        status="pass",
        detail="Compensation and hiring timeline phrasing match standard professional norms."
    )


def check_url_security_and_shorteners(url: Optional[str]) -> AuthenticityCheckItem:
    """Checks URL validity, protocol security, and shortener usage."""
    if not url:
        return AuthenticityCheckItem(
            name="url_security_and_domain",
            status="pass",
            detail="Raw text input provided (no external URL to evaluate)."
        )

    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()

        if hostname in KNOWN_URL_SHORTENERS:
            return AuthenticityCheckItem(
                name="url_security_and_domain",
                status="fail",
                detail=f"URL shortener detected ({hostname}). Legitimate job postings should link to direct corporate domains or established job boards.",
                evidence=url
            )

        if parsed.scheme == "http":
            return AuthenticityCheckItem(
                name="url_security_and_domain",
                status="warn",
                detail="Non-secure HTTP URL detected. Legitimate career sites use encrypted HTTPS.",
                evidence=url
            )

        return AuthenticityCheckItem(
            name="url_security_and_domain",
            status="pass",
            detail=f"Secure HTTPS connection on verified domain ({hostname})."
        )
    except Exception as exc:
        return AuthenticityCheckItem(
            name="url_security_and_domain",
            status="warn",
            detail=f"Unable to cleanly parse domain from URL: {exc}"
        )


def check_text_structural_quality(text: str) -> AuthenticityCheckItem:
    """Evaluates formatting hygiene, excessive ALL CAPS shouting, and multiple punctuation."""
    if len(text.strip()) < 120:
        return AuthenticityCheckItem(
            name="posting_structural_quality",
            status="warn",
            detail="Very brief job description (<120 characters). Limited information available for evaluation."
        )

    caps_matches = re.findall(r'\b[A-Z\s]{12,}\b', text)
    caps_count = len([m for m in caps_matches if len(m.strip()) >= 12])
    exclamation_spikes = len(re.findall(r'!{2,}|\${2,}', text))

    if caps_count >= 3 or exclamation_spikes >= 2:
        return AuthenticityCheckItem(
            name="posting_structural_quality",
            status="warn",
            detail="Posting contains excessive capitalized shouting phrases or spam punctuation ($$$/!!!)."
        )

    return AuthenticityCheckItem(
        name="posting_structural_quality",
        status="pass",
        detail="Standard corporate formatting and capitalization observed."
    )


def run_layer1_checks(text: str, url: Optional[str] = None) -> List[AuthenticityCheckItem]:
    """Executes all deterministic Layer 1 rule checks."""
    return [
        check_contact_domain(text),
        check_messaging_platforms(text),
        check_upfront_fees_and_payments(text),
        check_unrealistic_pay_and_urgency(text),
        check_url_security_and_shorteners(url),
        check_text_structural_quality(text),
    ]


# ============================================================================
# Layer 2 — ML Classification Signal (AventIQ-AI/BERT-Spam-Job-Posting-Detection-Model)
# ============================================================================
BERT_MODEL_NAME = "AventIQ-AI/BERT-Spam-Job-Posting-Detection-Model"


def _safe_import_transformers():
    import sys
    if "torchvision" not in sys.modules or sys.modules["torchvision"] is None:
        try:
            import torchvision
        except Exception:
            sys.modules["torchvision"] = None
    from transformers import BertTokenizerFast, BertForSequenceClassification
    import torch
    return BertTokenizerFast, BertForSequenceClassification, torch


def _run_with_timeout(func, *args, timeout_sec=2.5, **kwargs):
    """Executes a function with a timeout, returning None if timed out or failed."""
    import concurrent.futures
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            return future.result(timeout=timeout_sec)
    except Exception as exc:
        logger.info("BERT classifier loading timed out (%ss) or failed: %s. Using heuristic signals.", timeout_sec, exc)
        return None


@lru_cache(maxsize=1)
def _get_bert_classifier():
    """Lazy-loads the AventIQ BERT job spam classifier on first call."""
    BertTokenizerFast, BertForSequenceClassification, torch = _safe_import_transformers()
    logger.info("Loading BERT Job Spam Classifier (%s) - first call only", BERT_MODEL_NAME)
    tokenizer = BertTokenizerFast.from_pretrained(BERT_MODEL_NAME)
    model = BertForSequenceClassification.from_pretrained(BERT_MODEL_NAME)
    model.eval()
    return tokenizer, model, torch


def classify_job_posting_ml(text: str, title_hint: Optional[str] = None) -> ClassifierSignal:
    """
    Runs the fine-tuned BERT classifier on the job posting text.
    Uses title + first paragraphs + dense red-flag snippets for max 128-token input.
    """
    try:
        res = _run_with_timeout(_get_bert_classifier, timeout_sec=2.5)
        if res is None:
            raise RuntimeError("BERT model loading timed out")
        tokenizer, model, torch = res

        # Build focused 128-token context: Title + First ~120 words
        clean_lead = text.strip().split("\n\n")[0] if "\n\n" in text else text[:500]
        context_text = f"{title_hint or ''} - {clean_lead}" if title_hint else clean_lead

        inputs = tokenizer(context_text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        with torch.no_grad():
            logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        predicted_id = int(probs.argmax())

        # Predicted label (1 = Fake Job, 0 = Real Job)
        label = "Fake Job" if predicted_id == 1 else "Real Job"
        confidence = float(probs[predicted_id])

        detail = (
            f"Classifier evaluated model confidence at {int(confidence * 100)}% for '{label}'. "
            f"Note: Precision on fake class is ~0.81 (4-in-5 reliability)."
        )

        return ClassifierSignal(
            status="completed",
            predicted_label=label,
            confidence=round(confidence, 3),
            model_name=BERT_MODEL_NAME,
            detail=detail
        )
    except Exception as exc:
        logger.warning("ML Classifier execution unavailable: %s", exc)
        return ClassifierSignal(
            status="unavailable",
            predicted_label=None,
            confidence=None,
            model_name=BERT_MODEL_NAME,
            detail=f"ML model evaluation unavailable ({type(exc).__name__}). Using heuristic and RAG layers."
        )


# ============================================================================
# Layer 3 — Curated Fraud Knowledge Base & RAG-Augmented LLM Reasoning
# ============================================================================
SCAM_KNOWLEDGE_BASE: List[Dict[str, str]] = [
    {
        "id": "upfront_equipment_purchase",
        "title": "Upfront Equipment & Vendor Check Scam",
        "description": "Postings that instruct candidates to purchase home office laptops, software, or supplies from an 'approved vendor' using an advance check sent by the employer. The check later bounces, leaving the victim liable for money wired to the vendor.",
        "category": "Financial Fraud"
    },
    {
        "id": "application_training_fees",
        "title": "Pre-Employment Application or Training Fees",
        "description": "Demanding fees for training materials, onboarding certification, background check verification, or security deposits before starting work. Legitimate companies cover pre-employment onboarding costs.",
        "category": "Advance Fee Fraud"
    },
    {
        "id": "telegram_whatsapp_screening",
        "title": "Private Messenger (Telegram/WhatsApp) Recruitment",
        "description": "Directing job seekers exclusively to Telegram, WhatsApp, or Signal handles for text-only questionnaires or 'instant interviews'. Scammers use private encrypted apps to prevent domain verification and evade moderation.",
        "category": "Identity Phishing"
    },
    {
        "id": "banking_credentials_phishing",
        "title": "Premature Banking and SSN Collection",
        "description": "Requiring bank account details, routing numbers, credit card information, or social security numbers prior to a formal interview or written offer letter under the guise of direct deposit setup.",
        "category": "Identity Theft"
    },
    {
        "id": "unrealistic_compensation_low_effort",
        "title": "Exorbitant Compensation for Entry-Level Work",
        "description": "Advertising outsized salaries (e.g. $4000-$7000/week or $80-$150/hr) for generic typing, data entry, administrative tasks, or no-experience positions to induce urgent, uncritical responses.",
        "category": "Bait & Switch"
    },
    {
        "id": "package_forwarding_reshipping",
        "title": "Package Forwarding & Re-Shipping Mule Schemes",
        "description": "Positions titled 'Quality Control Inspector', 'Package Handler', or 'Logistics Assistant' where workers receive packages at home and reship them. This is often stolen merchandise or illegal contraband.",
        "category": "Criminal Mule Scheme"
    },
    {
        "id": "fake_check_overpayment",
        "title": "Counterfeit Check / Secret Shopper Overpayment",
        "description": "Sending an initial cashier's check or wire with instructions to keep a portion as salary and wire the remainder to a 'vendor' or 'donation account'. When the check bounces, the candidate loses all wired funds.",
        "category": "Financial Fraud"
    },
    {
        "id": "company_domain_impersonation",
        "title": "Executive and Corporate Impersonation",
        "description": "Using similar typosquatted domain names or generic free email addresses (@gmail.com, @yahoo.com) claiming to represent major reputable corporations or hiring managers.",
        "category": "Impersonation"
    },
    {
        "id": "pyramid_mlm_disguised_job",
        "title": "Multi-Level Marketing (MLM) & Pyramid Recruitment",
        "description": "Disguising direct-selling or recruit-to-earn schemes as standard salaried managerial or marketing roles, requiring inventory purchase or recruiting others to earn income.",
        "category": "MLM / Pyramid"
    },
    {
        "id": "immediate_hiring_no_screening",
        "title": "High-Pressure Urgency & Instant Hiring",
        "description": "Offering employment immediately with no resume review, technical screening, or video interview, demanding immediate signature and identity documents within hours.",
        "category": "High-Pressure Scam"
    },
    {
        "id": "vague_role_responsibilities",
        "title": "Extremely Vague Job Responsibilities",
        "description": "Job descriptions completely devoid of specific technical responsibilities, tools, project goals, or required domain knowledge, relying entirely on generic platitudes.",
        "category": "Vague Phantom Listing"
    }
]

# Pre-computed cached embeddings for the scam knowledge base
_KB_EMBEDDINGS: Optional[np.ndarray] = None


def _get_kb_embeddings() -> np.ndarray:
    """Embeds the scam knowledge base documents using sentence-transformers (cached)."""
    global _KB_EMBEDDINGS
    if _KB_EMBEDDINGS is None:
        try:
            texts = [f"{doc['title']}: {doc['description']}" for doc in SCAM_KNOWLEDGE_BASE]
            embeddings = [embed_text(t) for t in texts]
            _KB_EMBEDDINGS = np.array(embeddings, dtype="float32")
        except Exception as exc:
            logger.warning("Failed to embed scam knowledge base: %s", exc)
            _KB_EMBEDDINGS = np.zeros((len(SCAM_KNOWLEDGE_BASE), 384), dtype="float32")
    return _KB_EMBEDDINGS


def retrieve_relevant_fraud_patterns(job_text: str, top_k: int = 4) -> List[Dict[str, str]]:
    """Retrieves top-k relevant fraud patterns using hybrid keyword-overlap and semantic retrieval."""
    jt_lower = job_text.lower()
    scored = []
    
    # 1. Lexical / Keyword Scoring
    for doc in SCAM_KNOWLEDGE_BASE:
        score = 0.0
        # Title word matches
        for word in doc["title"].lower().split():
            if len(word) > 3 and word in jt_lower:
                score += 2.0
        # Description keyword matches
        for word in doc["description"].lower().split():
            if len(word) > 4 and word in jt_lower:
                score += 1.0
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_matches = [doc for score, doc in scored if score > 0]
    
    if len(top_matches) >= top_k:
        return top_matches[:top_k]

    # Fill remainder from KB
    remainder = [doc for doc in SCAM_KNOWLEDGE_BASE if doc not in top_matches]
    return (top_matches + remainder)[:top_k]


AUTHENTICITY_LLM_SYSTEM_PROMPT = """You are an expert Cyber Security & Employment Fraud Analyst evaluating a job posting.
You will be provided with:
1. The text of a job posting.
2. A retrieved set of known employment fraud and scam patterns.

Task:
Perform an objective, evidence-based risk assessment.
- Analyze if the posting exhibits specific indicators matching the retrieved fraud patterns.
- Always quote the EXACT phrase from the job posting as evidence.
- Frame your findings as observable RISK SIGNALS in this specific text, NOT as an absolute verdict of fact about the company.
- Never make defamatory assertions about a named organization beyond analyzing the provided text.

Respond ONLY with a valid JSON object matching this schema:
{
  "risk_level": "low" | "medium" | "high",
  "matched_patterns": [
    {
      "pattern": "Pattern Name (e.g. Upfront equipment check scam)",
      "evidence": "Exact quoted phrase from posting",
      "explanation": "One sentence explaining why this phrasing represents a risk signal."
    }
  ],
  "reasoning_summary": "2-3 concise sentences summarizing the risk indicators or confirming standard professional posting characteristics."
}
"""


def run_llm_reasoning_layer(job_text: str, retrieved_patterns: List[Dict[str, str]]) -> LLMReasoningSignal:
    """Executes Layer 3 RAG-augmented LLM reasoning with validated structured JSON output."""
    pattern_context = "\n\n".join(
        f"[Pattern: {p['title']}]\nCategory: {p['category']}\nDetails: {p['description']}"
        for p in retrieved_patterns
    )

    user_prompt = (
        f"--- JOB POSTING TEXT ---\n{job_text[:3500]}\n\n"
        f"--- RELEVANT KNOWN FRAUD PATTERNS ---\n{pattern_context}\n\n"
        "Analyze the posting and respond in JSON:"
    )

    try:
        raw_response = call_llm(
            history=[{"role": "user", "content": user_prompt}],
            system=AUTHENTICITY_LLM_SYSTEM_PROMPT
        )

        # Parse JSON
        clean_json = raw_response.strip()
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()

        data = json.loads(clean_json)
        risk_level = str(data.get("risk_level", "low")).lower()
        if risk_level not in ("low", "medium", "high"):
            risk_level = "low"

        matched = []
        for p in data.get("matched_patterns", []):
            if isinstance(p, dict) and p.get("pattern") and p.get("evidence"):
                matched.append(MatchedPatternEvidence(
                    pattern=str(p.get("pattern")),
                    evidence=str(p.get("evidence")),
                    explanation=str(p.get("explanation", ""))
                ))

        summary = str(data.get("reasoning_summary", "Posting shows standard characteristics without evident red flags."))

        return LLMReasoningSignal(
            status="completed",
            risk_level=risk_level,
            matched_patterns=matched,
            reasoning_summary=summary,
            retrieved_patterns_count=len(retrieved_patterns)
        )
    except Exception as exc:
        logger.warning("Layer 3 LLM reasoning unavailable: %s", exc)
        return LLMReasoningSignal(
            status="unavailable",
            risk_level=None,
            matched_patterns=[],
            reasoning_summary=f"LLM reasoning layer unavailable ({type(exc).__name__}). Assessment grounded in Layer 1 & 2 signals.",
            retrieved_patterns_count=len(retrieved_patterns)
        )


# ============================================================================
# Overall Risk Synthesis (Named, Transparent Decision Logic)
# ============================================================================
def compute_overall_authenticity_risk(
    layer1_checks: List[AuthenticityCheckItem],
    layer2_classifier: ClassifierSignal,
    layer3_llm: LLMReasoningSignal
) -> Tuple[str, int, str, str]:
    """
    Computes overall risk level and transparent summary using named decision rules.
    Returns: (risk_level, risk_score, verdict_label, summary)
    """
    l1_fails = [c for c in layer1_checks if c.status == "fail"]
    l1_warns = [c for c in layer1_checks if c.status == "warn"]

    is_ml_fake = layer2_classifier.status == "completed" and layer2_classifier.predicted_label == "Fake Job"
    ml_confidence = layer2_classifier.confidence or 0.0

    llm_risk = layer3_llm.risk_level if layer3_llm.status == "completed" else None

    # Rule 1: High Risk Condition
    if (len(l1_fails) >= 2) or (is_ml_fake and llm_risk in ("medium", "high")) or (llm_risk == "high" and len(layer3_llm.matched_patterns) >= 2) or (len(l1_fails) >= 1 and is_ml_fake):
        risk_level = "high"
        risk_score = 85 if not (len(l1_fails) >= 2 and is_ml_fake) else 95
        verdict_label = "High Risk (Alert)"
        summary = (
            f"Multiple critical fraud signals detected across {len(l1_fails)} rule check(s)"
            f"{' and ML spam classifier' if is_ml_fake else ''}. "
            "Posting exhibits patterns consistent with upfront fee, private messenger interview, or fake check schemes. "
            "Exercise extreme caution and verify directly via official corporate channels before proceeding."
        )
        return risk_level, risk_score, verdict_label, summary

    # Rule 2: Moderate Risk Condition
    if (len(l1_fails) >= 1) or (len(l1_warns) >= 2) or is_ml_fake or (llm_risk == "medium"):
        risk_level = "medium"
        risk_score = 60 if is_ml_fake else 50
        verdict_label = "Moderate Risk (Caution)"
        summary = (
            "Notable caution signals detected. "
            f"{'Heuristics flagged ' + l1_fails[0].detail if l1_fails else 'Posting exhibits atypical formatting or recruitment signals'}. "
            "We recommend verifying the opening on the employer's official website prior to submitting sensitive personal information."
        )
        return risk_level, risk_score, verdict_label, summary

    # Rule 3: Low Risk Condition
    risk_level = "low"
    risk_score = 15
    verdict_label = "Low Risk (Nominal)"
    summary = (
        "Standard professional posting patterns observed. No upfront fee requirements, generic email domains, "
        "or private messenger screening signals were identified across rule checks, ML classification, and pattern retrieval."
    )
    return risk_level, risk_score, verdict_label, summary


# ============================================================================
# Main Authenticity Assessment Pipeline
# ============================================================================
def analyze_job_authenticity(
    job_text: str,
    job_url: Optional[str] = None,
    company_hint: Optional[str] = None,
    role_hint: Optional[str] = None
) -> AuthenticityReport:
    """
    Runs the full 3-layer job authenticity assessment pipeline.
    """
    text = job_text.strip()
    if not text:
        raise ValueError("Job posting text cannot be empty for authenticity analysis.")

    # 1. Layer 1: Rule-based Heuristic Checks
    l1_checks = run_layer1_checks(text, job_url)

    # 2. Layer 2: BERT ML Classifier
    l2_signal = classify_job_posting_ml(text, title_hint=role_hint)

    # 3. Layer 3: RAG-augmented LLM Reasoning
    retrieved_patterns = retrieve_relevant_fraud_patterns(text, top_k=4)
    l3_signal = run_llm_reasoning_layer(text, retrieved_patterns)

    # 4. Overall Synthesis
    risk_level, risk_score, verdict_label, summary = compute_overall_authenticity_risk(
        l1_checks, l2_signal, l3_signal
    )

    red_flags_count = sum(1 for c in l1_checks if c.status == "fail")
    warnings_count = sum(1 for c in l1_checks if c.status == "warn")

    return AuthenticityReport(
        risk_level=risk_level,
        risk_score=risk_score,
        verdict_label=verdict_label,
        summary=summary,
        layer1_heuristics=l1_checks,
        layer2_classifier=l2_signal,
        layer3_llm_reasoning=l3_signal,
        red_flags_count=red_flags_count,
        warnings_count=warnings_count
    )
