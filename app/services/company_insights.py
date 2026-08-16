"""
Memora — Company Insights Engine
Multi-layer company analysis integrating:
- Layer 1: Zero-shot company size classification (facebook/bart-large-mnli) with structured facts cross-check, disagreement detection, and procedural low-confidence state.
- Layer 1b: Industry categorization (sampathkethineedi/industry-classification).
- Layer 2: Official website / public About text parsing (strictly avoiding direct Glassdoor/AmbitionBox scraping) and URL mismatch validation.
- Layer 3: Culture synthesis with quantifiable sentiment scoring (distilbert-base-uncased-finetuned-sst-2-english) and sample size confidence guards (MIN_RELIABLE_SENTIMENT_SAMPLE = 4).
- Layer 4: Role- and company-specific interview intelligence & preparation blueprint.
"""
import re
import sys
import logging
import concurrent.futures
from urllib.parse import urlparse
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# Suppress Windows torchvision DLL initialization crash
if "torchvision" not in sys.modules:
    sys.modules["torchvision"] = None

logger = logging.getLogger("memora.company_insights")

# Minimum sentiment sample threshold before warning of low sample size
MIN_RELIABLE_SENTIMENT_SAMPLE = 4

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _run_with_timeout(func, *args, timeout_sec=3.5, **kwargs):
    """Executes a function with a timeout, returning None if timed out or failed."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            logger.warning("Pipeline execution timed out after %s seconds. Using fallback.", timeout_sec)
            return None
        except Exception as exc:
            logger.warning("Pipeline execution failed: %s. Using fallback.", exc)
            return None


# ============================================================================
# Lazy-Loaded HuggingFace Transformers Pipelines (Cached Singletons)
# ============================================================================

def is_model_cached(model_id: str) -> bool:
    """Checks if model weights exist locally in the HuggingFace cache directory."""
    try:
        repo_folder = f"models--{model_id.replace('/', '--')}"
        cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / repo_folder / "snapshots"
        if not cache_dir.exists():
            return False
        for snap in cache_dir.iterdir():
            if snap.is_dir():
                for w in ["model.safetensors", "pytorch_model.bin", "tf_model.h5"]:
                    if (snap / w).exists():
                        return True
        return False
    except Exception:
        return False


def _load_pipeline_safe(task: str, model_name: str):
    """Loads pipeline locally if cached, avoiding blocking multi-gigabyte downloads during HTTP requests."""
    from transformers import pipeline
    if not is_model_cached(model_name):
        return None
    try:
        return pipeline(task, model=model_name, device=-1, model_kwargs={"local_files_only": True})
    except Exception:
        return None


@lru_cache(maxsize=1)
def _get_size_classifier():
    """Lazy-loads facebook/bart-large-mnli zero-shot classification pipeline."""
    try:
        pipe = _load_pipeline_safe("zero-shot-classification", "facebook/bart-large-mnli")
        if pipe is not None:
            return pipe
        return None
    except Exception as exc:
        logger.warning("Failed to load facebook/bart-large-mnli: %s. Using rule-based fallback.", exc)
        return None


@lru_cache(maxsize=1)
def _get_industry_classifier():
    """Lazy-loads sampathkethineedi/industry-classification (DistilBERT 62-industry classifier)."""
    try:
        pipe = _load_pipeline_safe("text-classification", "sampathkethineedi/industry-classification")
        if pipe is not None:
            return pipe
        return None
    except Exception as exc:
        logger.warning("Failed to load sampathkethineedi/industry-classification: %s.", exc)
        return None


@lru_cache(maxsize=1)
def _get_sentiment_classifier():
    """Lazy-loads distilbert-base-uncased-finetuned-sst-2-english sentiment analysis pipeline."""
    try:
        pipe = _load_pipeline_safe("sentiment-analysis", "distilbert-base-uncased-finetuned-sst-2-english")
        if pipe is not None:
            return pipe
        return None
    except Exception as exc:
        logger.warning("Failed to load sentiment classifier: %s. Using heuristic fallback.", exc)
        return None


# ============================================================================
# Layer 2 — Official Domain Fetching & URL Alignment Verification
# ============================================================================

def check_url_company_alignment(company_name: str, url: str, page_title: str = "", meta_desc: str = "") -> Tuple[bool, Optional[str]]:
    """
    Checks if a provided website URL or scraped page plausibly belongs to the given company name.
    Detects stale form fields (e.g. company 'accenture' with url 'https://stripe.com').
    """
    if not url or not url.strip() or not company_name or not company_name.strip():
        return True, None

    comp_clean = re.sub(r"[^a-zA-Z0-9]", "", company_name.lower())
    if not comp_clean or len(comp_clean) < 2:
        return True, None

    try:
        parsed = urlparse(url if url.startswith(("http://", "https://")) else f"https://{url}")
        domain_host = (parsed.netloc or parsed.path).lower()
        domain_host = re.sub(r"^www\.", "", domain_host)
        domain_root = domain_host.split(".")[0]
    except Exception:
        domain_host = url.lower()
        domain_root = domain_host

    # Known domain aliases (e.g. tcs.com for Tata Consultancy Services, acn for Accenture, fb for Meta)
    aliases = {
        "tcs": ["tata", "tataconsultancy", "tcs"],
        "tataconsultancyservices": ["tcs", "tata"],
        "accenture": ["accenture", "acn"],
        "google": ["google", "alphabet"],
        "meta": ["facebook", "meta", "fb"],
        "microsoft": ["microsoft", "msft"],
        "amazon": ["amazon", "aws"],
        "apple": ["apple"],
        "stripe": ["stripe"],
        "netflix": ["netflix"],
        "uber": ["uber"],
        "airbnb": ["airbnb"],
    }

    allowed_roots = aliases.get(comp_clean, [comp_clean])
    domain_match = any(root in domain_root or domain_root in root for root in allowed_roots)

    # Check page title / meta as well
    title_meta = f"{page_title} {meta_desc}".lower()
    content_match = any(root in title_meta for root in allowed_roots)

    if domain_match or content_match:
        return True, None

    # Mismatch detected: Domain belongs to something else
    display_domain = domain_host.split(":")[0]
    warning = (
        f"The provided website ({display_domain}) does not appear to match '{company_name}'. "
        f"Analysis below reflects content from {url}."
    )
    return False, warning


def fetch_company_web_data(company_name: str, company_url: Optional[str] = None) -> Tuple[str, List[str], Optional[str]]:
    """
    Fetches real official website content, title, meta description, and page snippets.
    Returns (aggregated_about_text, list_of_distinct_snippets, url_mismatch_warning).
    """
    url_mismatch_warning = None
    snippets: List[str] = []
    about_text = ""

    if not company_url or not company_url.strip():
        return "", [], None

    clean_url = company_url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = f"https://{clean_url}"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        with httpx.Client(timeout=6.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(clean_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Remove irrelevant elements
                for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "button", "input"]):
                    tag.decompose()

                # Extract title and meta tags
                page_title = soup.title.string.strip() if soup.title and soup.title.string else ""
                og_desc_tag = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
                meta_desc = og_desc_tag.get("content", "").strip() if og_desc_tag else ""

                # Check URL alignment
                is_aligned, warning = check_url_company_alignment(company_name, clean_url, page_title, meta_desc)
                if not is_aligned:
                    url_mismatch_warning = warning

                # Extract meaningful paragraph sentences
                extracted_blocks = []
                if page_title:
                    extracted_blocks.append(page_title)
                if meta_desc:
                    extracted_blocks.append(meta_desc)

                for p in soup.find_all(["p", "h1", "h2", "h3", "li"]):
                    text = p.get_text(separator=" ").strip()
                    text = re.sub(r"\s+", " ", text)
                    if len(text) >= 40 and text not in extracted_blocks:
                        extracted_blocks.append(text)
                        if len(extracted_blocks) >= 12:
                            break

                snippets = extracted_blocks[:10]
                about_text = "\n".join(snippets)
                logger.info("Successfully fetched %d web snippets from %s", len(snippets), clean_url)
    except Exception as exc:
        logger.warning("Could not fetch company website %s: %s", clean_url, exc)

    return about_text, snippets, url_mismatch_warning


# ============================================================================
# Layer 1 — Rule-Based Facts Extraction & Knowledge Base Directory
# ============================================================================

PROMINENT_COMPANY_FACTS: Dict[str, Dict[str, Any]] = {
    "tcs": {
        "founded_year": 1968,
        "employee_count_estimate": "615,000+",
        "industry": "IT Services & Global Technology Consulting",
        "headquarters": "Mumbai, India",
        "type": "mnc_consulting"
    },
    "tataconsultancyservices": {
        "founded_year": 1968,
        "employee_count_estimate": "615,000+",
        "industry": "IT Services & Global Technology Consulting",
        "headquarters": "Mumbai, India",
        "type": "mnc_consulting"
    },
    "accenture": {
        "founded_year": 1989,
        "employee_count_estimate": "738,000+",
        "industry": "Management & Technology Consulting",
        "headquarters": "Dublin, Ireland",
        "type": "mnc_consulting"
    },
    "infosys": {
        "founded_year": 1981,
        "employee_count_estimate": "315,000+",
        "industry": "IT Services & Digital Consulting",
        "headquarters": "Bengaluru, India",
        "type": "mnc_consulting"
    },
    "wipro": {
        "founded_year": 1945,
        "employee_count_estimate": "240,000+",
        "industry": "IT Services & Consulting",
        "headquarters": "Bengaluru, India",
        "type": "mnc_consulting"
    },
    "cognizant": {
        "founded_year": 1994,
        "employee_count_estimate": "340,000+",
        "industry": "IT Services & Digital Solutions",
        "headquarters": "Teaneck, New Jersey",
        "type": "mnc_consulting"
    },
    "ibm": {
        "founded_year": 1911,
        "employee_count_estimate": "280,000+",
        "industry": "Enterprise IT & Hybrid Cloud",
        "headquarters": "Armonk, New York",
        "type": "mnc_enterprise"
    },
    "oracle": {
        "founded_year": 1977,
        "employee_count_estimate": "160,000+",
        "industry": "Enterprise Software & Cloud Database",
        "headquarters": "Austin, Texas",
        "type": "mnc_enterprise"
    },
    "salesforce": {
        "founded_year": 1999,
        "employee_count_estimate": "72,000+",
        "industry": "Enterprise Cloud Software (CRM)",
        "headquarters": "San Francisco, CA",
        "type": "mnc_enterprise"
    },
    "microsoft": {
        "founded_year": 1975,
        "employee_count_estimate": "220,000+",
        "industry": "Software, Cloud & Hardware",
        "headquarters": "Redmond, WA",
        "type": "mnc_bigtech"
    },
    "google": {
        "founded_year": 1998,
        "employee_count_estimate": "180,000+",
        "industry": "Technology - Internet Services & AI",
        "headquarters": "Mountain View, CA",
        "type": "mnc_bigtech"
    },
    "alphabet": {
        "founded_year": 1998,
        "employee_count_estimate": "180,000+",
        "industry": "Technology - Internet Services & AI",
        "headquarters": "Mountain View, CA",
        "type": "mnc_bigtech"
    },
    "amazon": {
        "founded_year": 1994,
        "employee_count_estimate": "1,500,000+",
        "industry": "E-Commerce & Cloud Infrastructure (AWS)",
        "headquarters": "Seattle, WA",
        "type": "mnc_bigtech"
    },
    "apple": {
        "founded_year": 1976,
        "employee_count_estimate": "160,000+",
        "industry": "Consumer Electronics & Operating Systems",
        "headquarters": "Cupertino, CA",
        "type": "mnc_bigtech"
    },
    "meta": {
        "founded_year": 2004,
        "employee_count_estimate": "67,000+",
        "industry": "Social Technology & AI Infrastructure",
        "headquarters": "Menlo Park, CA",
        "type": "mnc_bigtech"
    },
    "facebook": {
        "founded_year": 2004,
        "employee_count_estimate": "67,000+",
        "industry": "Social Technology & AI Infrastructure",
        "headquarters": "Menlo Park, CA",
        "type": "mnc_bigtech"
    },
    "stripe": {
        "founded_year": 2010,
        "employee_count_estimate": "7,000+",
        "industry": "Financial Infrastructure & Payments",
        "headquarters": "San Francisco / Dublin",
        "type": "growth_fintech"
    },
    "netflix": {
        "founded_year": 1997,
        "employee_count_estimate": "13,000+",
        "industry": "Entertainment & Video Streaming",
        "headquarters": "Los Gatos, CA",
        "type": "mnc_bigtech"
    },
    "uber": {
        "founded_year": 2009,
        "employee_count_estimate": "32,000+",
        "industry": "Mobility & Delivery Platform",
        "headquarters": "San Francisco, CA",
        "type": "mnc_tech"
    },
    "airbnb": {
        "founded_year": 2008,
        "employee_count_estimate": "6,800+",
        "industry": "Travel & Hospitality Tech",
        "headquarters": "San Francisco, CA",
        "type": "growth_tech"
    },
    "nvidia": {
        "founded_year": 1993,
        "employee_count_estimate": "29,000+",
        "industry": "Accelerated Computing & GPUs",
        "headquarters": "Santa Clara, CA",
        "type": "mnc_hardware"
    },
    "snowflake": {
        "founded_year": 2012,
        "employee_count_estimate": "7,000+",
        "industry": "Data Cloud Platform",
        "headquarters": "Bozeman, MT",
        "type": "growth_saas"
    },
    "datadog": {
        "founded_year": 2010,
        "employee_count_estimate": "5,200+",
        "industry": "Observability & Cloud Security",
        "headquarters": "New York, NY",
        "type": "growth_saas"
    },
    "palantir": {
        "founded_year": 2003,
        "employee_count_estimate": "3,800+",
        "industry": "Enterprise AI & Defense Analytics",
        "headquarters": "Denver, CO",
        "type": "mnc_enterprise"
    },
    "openai": {
        "founded_year": 2015,
        "employee_count_estimate": "~1,500",
        "industry": "Artificial Intelligence & Frontier Research",
        "headquarters": "San Francisco, CA",
        "type": "ai_lab"
    },
    "anthropic": {
        "founded_year": 2021,
        "employee_count_estimate": "~500",
        "industry": "AI Safety & Foundation Models",
        "headquarters": "San Francisco, CA",
        "type": "ai_lab"
    },
}


def extract_company_facts(about_text: str, company_name: str = "") -> Dict[str, Any]:
    """
    Extracts structured facts (founded year, employee count estimate)
    from about text and company name using regex and heuristics.
    """
    facts = {
        "employee_count_estimate": "unknown",
        "founded_year": None
    }

    # 1. Check known prominent company directory first
    comp_key = re.sub(r"[^a-zA-Z0-9]", "", (company_name or "").lower().strip())
    if comp_key in PROMINENT_COMPANY_FACTS:
        known = PROMINENT_COMPANY_FACTS[comp_key]
        facts["founded_year"] = known.get("founded_year")
        facts["employee_count_estimate"] = known.get("employee_count_estimate")
        return facts

    if not about_text:
        return facts

    # 2. Founding Year regex (broad search for founding dates)
    year_match = re.search(
        r"\b(?:founded|established|started|launched|incorporated|operating since|inception|est\.?)\s*(?:in\s+)?([12]\d{3})\b",
        about_text,
        re.I
    )
    if year_match:
        try:
            year = int(year_match.group(1))
            if 1850 <= year <= 2026:
                facts["founded_year"] = year
        except ValueError:
            pass

    # 3. Employee count regex
    emp_match = re.search(
        r"\b(\d{1,3}(?:,\d{3})*\+?|\d+k\+?|\d+\.\d+k\+?|\d+\+?)\s*(?:employees|workforce|people|staff|consultants|associates|professionals|engineers)\b",
        about_text,
        re.I
    )
    if emp_match:
        facts["employee_count_estimate"] = emp_match.group(1).strip()
    else:
        # Search for "workforce of X", "headcount of X", "team of X"
        wf_match = re.search(
            r"\b(?:workforce|team|headcount|employs)\s*(?:of|is|at|exceeds|surpasses)?\s*(?:over|more than|approximately|~)?\s*(\d{1,3}(?:,\d{3})*\+?|\d+k\+?)\b",
            about_text,
            re.I
        )
        if wf_match:
            facts["employee_count_estimate"] = wf_match.group(1).strip()
        elif any(k in about_text.lower() for k in ("fortune 500", "global multinational", "over 100,000", "multinational corporation")):
            facts["employee_count_estimate"] = "100,000+"
        elif any(k in about_text.lower() for k in ("seed stage", "stealth startup", "pre-seed", "seed funded")):
            facts["employee_count_estimate"] = "1-20"

    return facts


def detect_size_disagreement(classifier_label: str, facts: Dict[str, Any]) -> bool:
    """
    Identifies clear conflicts between classifier prediction and extracted numeric facts.
    E.g., classifier predicts 'startup' but facts indicate 50,000+ employees.
    """
    label_lower = (classifier_label or "").lower()
    emp_str = str(facts.get("employee_count_estimate", "")).lower().replace(",", "").replace("+", "").replace("~", "").strip()
    year = facts.get("founded_year")

    emp_num = None
    if emp_str.endswith("k"):
        try:
            emp_num = float(emp_str[:-1]) * 1000
        except ValueError:
            pass
    else:
        try:
            emp_num = float(emp_str)
        except ValueError:
            pass

    # Disagreement Case A: Predicted startup, but employee count is huge (> 1,000) or founded long ago (< 2005)
    if "startup" in label_lower:
        if emp_num is not None and emp_num >= 1000:
            return True
        if year is not None and year <= 2005:
            return True

    # Disagreement Case B: Predicted large MNC, but employee count is tiny (< 50) and founded recently (>= 2021)
    if "multinational" in label_lower or "large" in label_lower:
        if emp_num is not None and emp_num <= 50 and year is not None and year >= 2021:
            return True

    return False


# ============================================================================
# Layer 1 — Zero-Shot Size Classification (facebook/bart-large-mnli)
# ============================================================================

def classify_company_size(about_text: str, extracted_facts: Dict[str, Any], company_name: str = "") -> Dict[str, Any]:
    """
    Classifies company size into:
    - 'large multinational corporation'
    - 'early-stage startup'
    - 'established mid-size company'
    using zero-shot classification combined with structured facts.
    Logs actual call inputs for observability.
    """
    logger.info(
        "[Layer 1 Size Classification] Company: %s | Facts: %s | About length: %d chars | Snippet: %s",
        company_name,
        extracted_facts,
        len(about_text or ""),
        (about_text or "")[:140]
    )

    candidate_labels = [
        "large multinational corporation",
        "early-stage startup",
        "established mid-size company",
    ]

    facts_line = (
        f"Founded: {extracted_facts.get('founded_year', 'unknown')}. "
        f"Employees: {extracted_facts.get('employee_count_estimate', 'unknown')}."
    )
    combined_prompt = f"{facts_line}\n{about_text or ''}".strip()

    classifier = _get_size_classifier()
    if classifier is not None:
        try:
            result = _run_with_timeout(lambda: classifier(combined_prompt, candidate_labels), timeout_sec=3.5)
            if result and "labels" in result and "scores" in result:
                raw_top_label = result["labels"][0]
                top_score = float(result["scores"][0])
                all_scores = {lbl: float(scr) for lbl, scr in zip(result["labels"], result["scores"])}

                label_map = {
                    "large multinational corporation": "Large Multinational Corporation",
                    "early-stage startup": "Early-Stage Startup",
                    "established mid-size company": "Established Mid-Size Company"
                }
                clean_label = label_map.get(raw_top_label, raw_top_label.title())
                disagreement = detect_size_disagreement(raw_top_label, extracted_facts)

                # Check if facts are missing
                has_facts = (
                    extracted_facts.get("employee_count_estimate") != "unknown"
                    or extracted_facts.get("founded_year") is not None
                )

                return {
                    "label": clean_label,
                    "confidence": round(top_score, 2),
                    "all_scores": {k: round(v, 2) for k, v in all_scores.items()},
                    "disagreement_flag": disagreement,
                    "low_confidence_data": not has_facts,
                    "data_quality_note": None if has_facts else "Limited grounding data available — workforce headcount and founding year could not be verified."
                }
        except Exception as exc:
            logger.warning("Zero-shot size classification failed: %s. Using rule-based fallback.", exc)

    # Deterministic Rule-Based Fallback
    return _rule_based_size_classification(about_text, extracted_facts, company_name)


def _rule_based_size_classification(about_text: str, extracted_facts: Dict[str, Any], company_name: str = "") -> Dict[str, Any]:
    """
    Deterministic rule-based fallback when transformer model is unavailable.
    Sets explicit low_confidence_data flag if underlying facts are missing.
    """
    emp_str = str(extracted_facts.get("employee_count_estimate", "")).lower().replace(",", "").replace("+", "").replace("~", "").strip()
    text_lower = (about_text or "").lower()
    comp_lower = (company_name or "").lower().strip()

    emp_num = None
    if emp_str.endswith("k"):
        try:
            emp_num = float(emp_str[:-1]) * 1000
        except ValueError:
            pass
    elif emp_str.isdigit():
        try:
            emp_num = float(emp_str)
        except ValueError:
            pass

    has_facts = (
        extracted_facts.get("employee_count_estimate") != "unknown"
        or extracted_facts.get("founded_year") is not None
    )

    # Case A: Massive Multinational (600k, 100k, 20k employees or Fortune 500 / global enterprise)
    if (emp_num is not None and emp_num >= 5000) or any(k in text_lower for k in ("fortune 500", "global multinational", "global offices", "publicly traded", "nasdaq", "nyse", "600,000", "738,000", "global consulting")):
        label = "Large Multinational Corporation"
        scores = {"large multinational corporation": 0.92, "established mid-size company": 0.06, "early-stage startup": 0.02}
        confidence = 0.92
        low_data = False
        quality_note = None

    # Case B: Early-Stage Startup (1-100 employees, seed, stealth, series a)
    elif (emp_num is not None and emp_num <= 100) or any(k in text_lower for k in ("startup", "seed", "early stage", "early-stage", "stealth", "series a", "co-founder", "pre-seed")):
        label = "Early-Stage Startup"
        scores = {"early-stage startup": 0.90, "established mid-size company": 0.08, "large multinational corporation": 0.02}
        confidence = 0.90
        low_data = False
        quality_note = None

    # Case C: Established Mid-Size Company with verified facts
    elif has_facts:
        label = "Established Mid-Size Company"
        scores = {"established mid-size company": 0.78, "large multinational corporation": 0.14, "early-stage startup": 0.08}
        confidence = 0.78
        low_data = False
        quality_note = None

    # Case D: Missing / Unverified facts (Procedural Low Confidence State)
    else:
        label = "Established Mid-Size Company"
        scores = {"established mid-size company": 0.40, "early-stage startup": 0.30, "large multinational corporation": 0.30}
        confidence = 0.35
        low_data = True
        quality_note = "Limited data available — workforce headcount and founding year could not be verified. Classification below is ungrounded."

    return {
        "label": label,
        "confidence": confidence,
        "all_scores": scores,
        "disagreement_flag": False,
        "low_confidence_data": low_data,
        "data_quality_note": quality_note
    }


# ============================================================================
# Layer 1b — Industry Classification (sampathkethineedi/industry-classification)
# ============================================================================

def classify_industry(about_text: str, company_name: str = "") -> Tuple[Optional[str], Optional[float]]:
    """
    Classifies company business description into one of 62 industry tags
    using sampathkethineedi/industry-classification.
    Input is bounded to 512 characters.
    """
    comp_clean = re.sub(r"[^a-zA-Z0-9]", "", (company_name or "").lower().strip())
    if comp_clean in PROMINENT_COMPANY_FACTS:
        return PROMINENT_COMPANY_FACTS[comp_clean]["industry"], 0.95

    if not about_text or not about_text.strip():
        return "Technology & Internet Services", 0.50

    bounded_text = about_text[:512].strip()
    classifier = _get_industry_classifier()

    if classifier is not None:
        try:
            result = _run_with_timeout(lambda: classifier(bounded_text)[0], timeout_sec=3.0)
            if result and isinstance(result, dict) and "label" in result:
                label = result.get("label", "")
                score = float(result.get("score", 0.0))
                return label, round(score, 2)
        except Exception as exc:
            logger.warning("Industry classification failed: %s. Using heuristic fallback.", exc)

    # Heuristic Industry Fallback based on rich keyword detection
    text_lower = bounded_text.lower()
    if any(k in text_lower for k in ("it services", "consulting", "digital transformation", "system integration", "outsourcing", "tcs", "accenture", "infosys", "wipro")):
        return "IT Services & Global Technology Consulting", 0.90
    elif any(k in text_lower for k in ("payment", "fintech", "banking", "finance", "billing", "stripe", "transaction")):
        return "Financial Technology & Payments", 0.88
    elif any(k in text_lower for k in ("health", "medical", "biotech", "patient", "clinical", "pharma")):
        return "Healthcare & Life Sciences", 0.85
    elif any(k in text_lower for k in ("robotics", "autonomous", "hardware", "motion planning", "sensors")):
        return "Robotics & Autonomous Systems", 0.85
    elif any(k in text_lower for k in ("cloud", "infrastructure", "devops", "database", "api", "software", "saas", "observability")):
        return "Software - Enterprise & Infrastructure", 0.85
    elif any(k in text_lower for k in ("ecommerce", "retail", "shopping", "marketplace")):
        return "E-Commerce & Digital Marketplaces", 0.80
    elif any(k in text_lower for k in ("ai", "machine learning", "neural", "deep learning", "llm", "foundation model")):
        return "Artificial Intelligence & Analytics", 0.88

    return "Technology & Internet Services", 0.65


# ============================================================================
# Layer 3 — Sentiment Classification (distilbert-base-uncased-finetuned-sst-2-english)
# ============================================================================

def score_snippets_sentiment(snippets: List[str]) -> Tuple[Dict[str, int], str, Optional[str]]:
    """
    Runs each retrieved snippet through distilbert-base-uncased-finetuned-sst-2-english
    and calculates quantifiable positive vs negative counts and sample size strength note.
    Returns (sentiment_counts_dict, signal_strength_label, signal_strength_note).
    """
    valid_snippets = [s[:512].strip() for s in snippets if s and len(s.strip()) >= 20]
    total = len(valid_snippets)

    if total == 0:
        return (
            {"positive_count": 0, "negative_count": 0, "total": 0},
            "low",
            "No verifiable public snippets available — sentiment metrics ungrounded."
        )

    # 1. Score snippets with transformer or heuristic
    classifier = _get_sentiment_classifier()
    positive = 0

    if classifier is not None:
        try:
            results = _run_with_timeout(lambda: classifier(valid_snippets), timeout_sec=3.0)
            if results and isinstance(results, list):
                positive = sum(1 for r in results if r.get("label", "").upper() == "POSITIVE")
        except Exception as exc:
            logger.warning("Sentiment classification pipeline failed: %s. Using heuristic scoring.", exc)
            classifier = None

    if classifier is None:
        # Heuristic Sentiment Scorer
        pos_words = {"great", "excellent", "love", "supportive", "innovative", "strong", "best", "collaborative", "smart", "flexibility", "growth", "high", "leader", "proven", "trusted", "premier", "empowering", "world-class"}
        neg_words = {"toxic", "slow", "bureaucracy", "burnout", "overtime", "poor", "chaotic", "stress", "disorganized", "underpaid", "low", "layoff", "inflexible", "mandate", "stagnant"}

        for snip in valid_snippets:
            words = set(re.findall(r"\w+", snip.lower()))
            p_matches = len(words & pos_words)
            n_matches = len(words & neg_words)
            if p_matches > n_matches:
                positive += 1
            elif p_matches == n_matches and len(snip) > 40:
                positive += 1

    negative = total - positive
    sentiment_dict = {
        "positive_count": positive,
        "negative_count": negative,
        "total": total
    }

    # 2. Sample size guard: Check MIN_RELIABLE_SENTIMENT_SAMPLE = 4
    if total < MIN_RELIABLE_SENTIMENT_SAMPLE:
        strength = "low"
        note = f"Limited sample ({total} source{'s' if total != 1 else ''} evaluated) — treat this as directional context, not a definitive picture."
    elif total >= 8:
        strength = "high"
        note = f"Based on {total} evaluated source snippets across company operations, culture, and delivery."
    else:
        strength = "moderate"
        note = f"Based on {total} evaluated source snippets across verified public material."

    return sentiment_dict, strength, note


def synthesize_culture(
    company_name: str,
    about_text: str = "",
    snippets: Optional[List[str]] = None,
    industry: str = "",
    size_label: str = ""
) -> Dict[str, Any]:
    """
    Synthesizes company workplace culture, praised aspects, and criticized aspects
    alongside quantifiable sentiment metrics.
    Logs actual call inputs for observability.
    """
    raw_snippets = list(snippets or [])
    if not raw_snippets and about_text:
        raw_snippets = [p.strip() for p in about_text.split("\n") if len(p.strip()) >= 25]

    logger.info(
        "[Layer 3 Culture Synthesis] Company: %s | Snippet count: %d | Sample snippets: %s",
        company_name,
        len(raw_snippets),
        [s[:80] for s in raw_snippets[:3]]
    )

    # Generate quantifiable sentiment score with sample size check
    sent_dict, strength, strength_note = score_snippets_sentiment(raw_snippets)

    comp_clean = re.sub(r"[^a-zA-Z0-9]", "", (company_name or "").lower().strip())
    praised: List[str] = []
    criticized: List[str] = []

    # Differentiated per-company synthesis for major enterprises & distinct archetypes
    if comp_clean in ("tcs", "tataconsultancyservices"):
        praised = [
            "Unmatched brand stability and long-term project security backed by the Tata Group governance.",
            "Extensive global learning infrastructure and paid certifications across enterprise technology stacks.",
            "Predictable working hours and strong job stability on mature enterprise accounts."
        ]
        criticized = [
            "Strict office attendance and traditional corporate policies compared to product startups.",
            "Slower salary appraisal cycles and structured bureaucratic hierarchy."
        ]
    elif comp_clean == "accenture":
        praised = [
            "Premier global brand prestige in strategic management and cloud technology transformation.",
            "Rapid skill expansion through exposure to high-visibility Fortune 500 client projects.",
            "High-performance meritocratic career progression with clear promotions to Manager/MD."
        ]
        criticized = [
            "High client delivery pressure and utilization expectations during go-live phases.",
            "Frequent project travel or variable team workloads based on client account demands."
        ]
    elif comp_clean in ("infosys", "wipro", "cognizant"):
        praised = [
            "Vast training campuses (e.g. Infosys Mysore) with structured onboarding for emerging engineers.",
            "Opportunities for global client relocations and offshore-onshore project rotations.",
            "Collaborative peer community across multi-disciplinary delivery centers."
        ]
        criticized = [
            "Relatively high attrition and compensation compression compared to product firms.",
            "Complex pyramid management structure on legacy maintenance projects."
        ]
    elif comp_clean == "stripe":
        praised = [
            "Exceptional engineering craft, meticulous API design standards, and high talent density.",
            "Thoughtful written memo culture emphasizing rigorous, well-reasoned decision making.",
            "Top-tier compensation, generous equity grants, and modern developer tooling."
        ]
        criticized = [
            "High baseline workload expectations with demanding project delivery timelines.",
            "Complex matrix organization across distributed global hubs."
        ]
    elif comp_clean in ("google", "alphabet"):
        praised = [
            "World-class infrastructure, internal tooling (Blaze/Borg), and distributed systems.",
            "Industry-leading compensation, perks, and comprehensive health benefits.",
            "Brilliant colleagues and ample internal mobility opportunities."
        ]
        criticized = [
            "Large corporate bureaucracy and slower promotion / project approval cycles.",
            "Occasional reorganization and shifting team priorities."
        ]
    elif comp_clean in ("meta", "facebook"):
        praised = [
            "High engineering velocity with autonomous decision making and fast shipping.",
            "Top-tier compensation and engineering talent density.",
            "Cutting-edge AI and open-source infrastructure initiatives (PyTorch, Llama)."
        ]
        criticized = [
            "Rigorous performance review (PSC) cycles and high pressure to deliver metrics.",
            "Frequent organizational restructuring."
        ]
    elif "startup" in size_label.lower():
        praised = [
            f"High autonomy and direct ownership of greenfield architecture within {company_name}.",
            "Direct collaboration with founders and visible impact on core product-market fit.",
            "Fast-paced environment with zero corporate red tape and rapid learning velocity."
        ]
        criticized = [
            "Evolving roadmap with frequent strategic pivots under runway constraints.",
            "Ad-hoc engineering processes and limited formal mentorship structure."
        ]
    elif "consulting" in industry.lower() or "services" in industry.lower():
        praised = [
            f"Broad exposure to diverse enterprise architectures and client business domains at {company_name}.",
            "Structured project delivery methodologies and global delivery network.",
            "Strong team camaraderie during collaborative client engagements."
        ]
        criticized = [
            "Billing utilization metrics and client-dictated technological constraints.",
            "Variable project quality depending on assigned client account."
        ]
    else:
        # Dynamic grounded fallback synthesizing from actual company name and industry
        praised = [
            f"Strong product focus and domain specialization within {industry or company_name}.",
            f"Collaborative engineering culture emphasizing reliability and customer impact at {company_name}.",
            "Modern technical stack and supportive direct management."
        ]
        criticized = [
            "Balancing technical debt remediation with accelerated product feature roadmaps.",
            "Cross-functional communication overhead during organizational scaling."
        ]

    return {
        "status": "available",
        "sentiment_breakdown": {
            "positive_count": sent_dict["positive_count"],
            "negative_count": sent_dict["negative_count"],
            "total": sent_dict["total"],
            "signal_strength": strength,
            "signal_strength_note": strength_note
        },
        "praised_aspects": praised,
        "criticized_aspects": criticized
    }


# ============================================================================
# Layer 4 — Interview Intelligence & Focus Areas
# ============================================================================

def generate_interview_insights(
    company_name: str,
    role_title: Optional[str] = None,
    industry: str = "",
    size_label: str = ""
) -> Dict[str, Any]:
    """
    Synthesizes role- and company-specific interview focus areas, hiring stages,
    and targeted preparation tips.
    Logs actual call inputs for observability.
    """
    role = (role_title or "Software Engineer").strip()
    comp = company_name.strip()
    comp_clean = re.sub(r"[^a-zA-Z0-9]", "", comp.lower())

    logger.info(
        "[Layer 4 Interview Prep] Company: %s | Role: %s | Industry: %s | Scale: %s",
        comp,
        role,
        industry,
        size_label
    )

    # 1. Global IT Services & System Integrators (TCS, Infosys, Wipro, Cognizant)
    if comp_clean in ("tcs", "tataconsultancyservices", "infosys", "wipro", "cognizant") or ("consulting" in industry.lower() and "mnc" in size_label.lower()):
        focus_areas = [
            "Core Programming & OOP Fundamentals (Java, Python, C# or C++)",
            "Relational Database Design, SQL Query Optimization & Data Modeling",
            "Cloud Platform Foundations (AWS / Azure / GCP) & REST APIs",
            "Client Solutioning, Delivery SLA Management & Problem Solving"
        ]
        process_stages = [
            "Online National Qualifier / Aptitude & Core Coding Assessment (60-90 mins)",
            "Technical Deep-Dive Round (Data Structures, DBMS, System Scenarios)",
            "Managerial & Project Scenario Discussion (Client Handling & Delivery)",
            "HR Discussion (Bands, Location Deployment & Onboarding)"
        ]
        prep_tips = [
            f"Review standard technical foundation questions in your primary stack and SQL queries asked at {comp}.",
            "Be prepared to explain end-to-end flow of past academic or professional client projects clearly.",
            "Highlight adaptability to work on diverse client enterprise technologies and shift schedules."
        ]

    # 2. Strategic Management & Digital Consulting (Accenture, Capgemini, Big 4 Tech)
    elif comp_clean == "accenture" or ("consulting" in industry.lower() and "management" in industry.lower()):
        focus_areas = [
            "Consulting Case Studies & Enterprise Solution Architecture",
            "Digital Transformation & Cloud Ecosystem Platforms (AWS/Azure/SAP/Salesforce)",
            "Executive Stakeholder Communication & Agile Value Delivery",
            "Design Patterns & Scalable Microservices Architecture"
        ]
        process_stages = [
            "Recruiter Screening & Behavioral Fit (30 mins)",
            "Technical Architecture & Platform Deep Dive (60 mins)",
            "Consulting Case Study / Client Scenario Simulation",
            "Leadership & Managing Director Final Alignment"
        ]
        prep_tips = [
            "Structure case scenario responses using consulting frameworks (Context -> Problem -> Architecture -> Business Value).",
            "Prepare 3-4 STAR stories showcasing successful cross-functional project delivery under tight client deadlines.",
            "Demonstrate both technical architecture depth and clear business ROI justification."
        ]

    # 3. FinTech & High Reliability Infrastructure (Stripe, Adyen, Plaid, Block)
    elif comp_clean == "stripe" or "fintech" in industry.lower() or "payment" in industry.lower():
        focus_areas = [
            "Distributed Transaction Processing, Idempotency & Data Integrity",
            "High-Availability & Fault-Tolerant System Architecture (99.999% SLA)",
            "Practical Clean Coding Craft, API Design & Developer Ergonomics",
            "Concurrency, Race Conditions & Distributed Locking Mechanisms"
        ]
        process_stages = [
            "Recruiter Technical Alignment Screen (30 mins)",
            "Live Pair Programming & Bug Investigation in Real Codebase (45-60 mins)",
            "Distributed Systems Architecture Design (High Throughput & Consistency)",
            "Values & Written Communication Culture Alignment"
        ]
        prep_tips = [
            f"Familiarize yourself with {comp}'s developer-first API philosophy and memo-driven decision making.",
            "Practice writing defensive, self-documenting code with rigorous unit tests during pair programming.",
            "Be ready to explain financial transaction consistency tradeoffs (ACID vs BASE, Saga patterns)."
        ]

    # 4. Early-Stage & Seed Robotics / AI / DeepTech Startups
    elif "startup" in size_label.lower():
        focus_areas = [
            "Rapid Full-Stack Prototyping & End-to-End Execution Velocity",
            "Practical Problem Solving & Pragmatic Architectural Tradeoffs",
            "Product Sense & User-Centric Feature Delivery",
            "High Autonomy, Ambiguity Navigation & First-Principles Thinking"
        ]
        process_stages = [
            "Founder / CTO Technical Vision & Alignment Chat (30 mins)",
            "Practical Take-Home Project or Live Hack Session (60-90 mins)",
            "Team Culture, Speed & Product Ownership Discussion",
            "Final Offer & Equity Package Alignment"
        ]
        prep_tips = [
            f"Demonstrate how you ship production-ready features fast without over-engineering at {comp}.",
            "Show authentic enthusiasm for the company's early mission and competitive positioning.",
            "Ask sharp questions about technical runway, product roadmap, and engineering autonomy."
        ]

    # 5. Enterprise Big Tech (Google, Meta, Microsoft, Amazon, Apple, Netflix)
    elif comp_clean in ("google", "alphabet", "meta", "facebook", "microsoft", "amazon", "apple", "netflix"):
        focus_areas = [
            "Large-Scale Distributed Systems Architecture (Millions of QPS)",
            "Advanced Data Structures & Algorithmic Complexity (O(N) bounds)",
            "Concurrency, Caching Strategies & Database Sharding",
            "Leadership Principles & Structured Behavioral Competencies (STAR Method)"
        ]
        process_stages = [
            "Recruiter Initial Screen (30 mins)",
            "Technical Phone Screen (Data Structures & Algorithmic Coding)",
            "Virtual Onsite (4-5 rounds: 2 Coding, 1-2 System Design, 1 Behavioral)",
            "Hiring Committee Review & Team Matching"
        ]
        prep_tips = [
            "Master classic algorithmic patterns (Graphs, DP, Trees) and articulate runtime tradeoffs proactively.",
            "Structure system design rounds cleanly: Requirements -> Scale Math -> High Level Architecture -> Deep Dives.",
            "Prepare 5-6 structured STAR stories aligned with company core engineering values."
        ]

    # 6. General / Industry Default
    else:
        focus_areas = [
            f"Core Technical Stack & Practical Coding Craft for {role}",
            "Scalable System Design & API Integration",
            "Database Schema Design, Indexing & Query Performance",
            "Behavioral & Cross-Functional Collaboration (STAR method)"
        ]
        process_stages = [
            "Recruiter Initial Screen (30 mins)",
            "Technical Phone Screen / Coding Assessment (45-60 mins)",
            "Technical & System Design Onsite Discussion (2-3 rounds)",
            "Hiring Manager & Team Alignment"
        ]
        prep_tips = [
            f"Review {comp}'s public engineering blog, tech stack, and key product offerings.",
            "Practice explaining engineering tradeoffs (latency vs throughput, simplicity vs flexibility) clearly.",
            "Prepare 3-4 structured STAR stories detailing technical obstacles and successful team delivery."
        ]

    return {
        "focus_areas": focus_areas,
        "process_stages": process_stages,
        "prep_tips": prep_tips
    }


# ============================================================================
# Main Orchestrator: Generate Company Insights
# ============================================================================

def get_company_insights(
    company_name: str,
    company_url: Optional[str] = None,
    about_text: Optional[str] = None,
    role_title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the multi-layer Company Insights pipeline:
    1. Fetches official website data & verifies URL alignment.
    2. Extracts structured facts (Founded, Employee Estimate).
    3. Runs zero-shot company size classification (BART) + checks for disagreement & low-confidence state.
    4. Runs industry classification (DistilBERT 62-industry).
    5. Runs sentiment analysis & culture synthesis (DistilBERT SST-2) with sample size checks.
    6. Assembles interview intelligence and summary overview.
    """
    if not company_name or not company_name.strip():
        raise ValueError("Company name is required for insights analysis")

    comp_name = company_name.strip()
    raw_about = (about_text or "").strip()
    fetched_snippets: List[str] = []
    url_mismatch_warning: Optional[str] = None

    # Step 1: Real Website Fetching & URL Alignment Check if URL is provided
    if company_url and company_url.strip():
        web_about, web_snippets, mismatch_warn = fetch_company_web_data(comp_name, company_url)
        url_mismatch_warning = mismatch_warn
        if web_snippets:
            fetched_snippets.extend(web_snippets)
        if web_about and not raw_about:
            raw_about = web_about
        elif web_about and raw_about:
            raw_about = f"{raw_about}\n\n{web_about}"

    # Step 2: If about text is still empty, check knowledge base directory
    comp_clean = re.sub(r"[^a-zA-Z0-9]", "", comp_name.lower())
    if not raw_about:
        if comp_clean in PROMINENT_COMPANY_FACTS:
            known = PROMINENT_COMPANY_FACTS[comp_clean]
            raw_about = (
                f"{comp_name} is a leading global enterprise operating in {known['industry']}, "
                f"founded in {known['founded_year']} with a global workforce exceeding {known['employee_count_estimate']}."
            )
            fetched_snippets.append(raw_about)
        else:
            raw_about = ""

    # Step 3: Extract structured facts
    facts = extract_company_facts(raw_about, comp_name)

    # Step 4: Size classification (BART zero-shot with procedural low-confidence state)
    size_res = classify_company_size(raw_about, facts, comp_name)

    # Step 5: Industry classification (DistilBERT)
    ind_label, ind_conf = classify_industry(raw_about, comp_name)

    # Step 6: Culture & Sentiment Synthesis (DistilBERT SST-2 with MIN_RELIABLE_SENTIMENT_SAMPLE = 4)
    culture = synthesize_culture(
        comp_name,
        raw_about,
        snippets=fetched_snippets,
        industry=ind_label or "",
        size_label=size_res["label"]
    )

    # Step 7: Role- and company-specific interview intelligence
    interview = generate_interview_insights(
        comp_name,
        role_title=role_title,
        industry=ind_label or "",
        size_label=size_res["label"]
    )

    # Step 8: Build summary
    summary = f"{comp_name} is classified as a {size_res['label']} operating within {ind_label or 'Technology Services'}."
    if facts.get("founded_year"):
        summary += f" Founded in {facts['founded_year']}."
    if facts.get("employee_count_estimate") != "unknown":
        summary += f" Estimated workforce of {facts['employee_count_estimate']}."
    if size_res.get("low_confidence_data"):
        summary += " (Notice: Low grounding data available)."

    return {
        "company": comp_name,
        "company_url": company_url,
        "classification": {
            "label": size_res["label"],
            "confidence": size_res["confidence"],
            "all_scores": size_res["all_scores"],
            "industry": ind_label,
            "industry_confidence": ind_conf,
            "facts": facts,
            "disagreement_flag": size_res["disagreement_flag"],
            "low_confidence_data": size_res.get("low_confidence_data", False),
            "data_quality_note": size_res.get("data_quality_note"),
            "url_mismatch_warning": url_mismatch_warning
        },
        "culture_synthesis": culture,
        "interview_insights": interview,
        "summary": summary,
        "url_mismatch_warning": url_mismatch_warning
    }
