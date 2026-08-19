"""
ATS (Applicant Tracking System) Checker & Parseability Service.

Hybrid architecture:
- Layer 1: Rule-based deterministic parseability & structure audit (65% weight)
- Layer 2: Content & entity quality signals via HuggingFace models (35% weight)
"""
import re
import logging
from functools import lru_cache
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("memora.ats_checker")

# ============================================================================
# Named Configuration Constants
# ============================================================================
LAYER1_WEIGHT = 0.65
LAYER2_WEIGHT = 0.35

THRESHOLD_ATS_FRIENDLY = 80
THRESHOLD_NEEDS_IMPROVEMENT = 50

MIN_WORD_COUNT = 150
MAX_WORD_COUNT = 1600

NER_MODEL_NAME = "yashpwr/resume-ner-bert-v2"
ROLE_MODEL_NAME = "srivihari/resume-job-role-classifier"


# ============================================================================
# Schemas
# ============================================================================
class ATSCheckItem(BaseModel):
    name: str
    status: str  # "pass" | "warn" | "fail" | "unavailable"
    detail: str
    model: Optional[str] = None


class ATSCheckResult(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    label: str  # "ATS-Friendly" | "Needs Improvement" | "High Risk"
    layer1_score: float
    layer2_score: Optional[float] = None
    rule_based_checks: List[ATSCheckItem] = Field(default_factory=list)
    ml_checks: List[ATSCheckItem] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# ============================================================================
# Layer 1 — Rule-based Parseability Engine (Deterministic, No ML)
# ============================================================================
def check_file_format(filename: str) -> ATSCheckItem:
    fn_lower = (filename or "").lower()
    if fn_lower.endswith(".pdf"):
        return ATSCheckItem(
            name="file_format",
            status="pass",
            detail="Standard PDF format detected. Compatible with modern ATS parsers."
        )
    elif fn_lower.endswith((".txt", ".docx")):
        return ATSCheckItem(
            name="file_format",
            status="pass",
            detail="Text/Document format detected. Readily parseable by ATS systems."
        )
    elif fn_lower.endswith(".doc"):
        return ATSCheckItem(
            name="file_format",
            status="warn",
            detail="Legacy .doc format detected. Modern ATS prefer PDF or .docx."
        )
    else:
        return ATSCheckItem(
            name="file_format",
            status="warn",
            detail="Uncommon file extension. Use standard PDF or clean plain text."
        )


def check_filename_conventions(filename: str) -> ATSCheckItem:
    if not filename:
        return ATSCheckItem(
            name="filename_conventions",
            status="pass",
            detail="Standard filename format."
        )

    # Check for special characters or spaces that older parsers choke on
    has_spaces = " " in filename
    has_special_chars = bool(re.search(r"[#@%&()+=!~`^]", filename))
    is_generic = filename.lower() in ("resume.pdf", "cv.pdf", "document.pdf", "resume(1).pdf", "untitled.pdf")

    if has_special_chars:
        return ATSCheckItem(
            name="filename_conventions",
            status="warn",
            detail=f"Filename '{filename}' contains special characters that some ATS ingestion pipelines mishandle."
        )
    elif is_generic:
        return ATSCheckItem(
            name="filename_conventions",
            status="warn",
            detail=f"Generic filename '{filename}'. Recommended format: 'FirstName_LastName_Resume.pdf'."
        )
    elif has_spaces:
        return ATSCheckItem(
            name="filename_conventions",
            status="pass",
            detail="Filename is readable, though using underscores (e.g. John_Doe_Resume.pdf) is optimal."
        )
    return ATSCheckItem(
        name="filename_conventions",
        status="pass",
        detail="Clean, standard filename conventions."
    )


def check_standard_sections(text: str) -> ATSCheckItem:
    text_lower = text.lower()

    sections = {
        "Experience": bool(re.search(r"\b(work\s+experience|professional\s+experience|experience|employment|work\s+history)\b", text_lower)),
        "Education": bool(re.search(r"\b(education|academic|qualifications|degrees)\b", text_lower)),
        "Skills": bool(re.search(r"\b(skills|technical\s+skills|core\s+competencies|technologies|expertise|proficiencies)\b", text_lower)),
        "Summary": bool(re.search(r"\b(summary|professional\s+summary|profile|about\s+me|objective)\b", text_lower)),
        "Projects/Certs": bool(re.search(r"\b(projects|certifications|awards|publications|portfolio)\b", text_lower)),
    }

    found = [k for k, v in sections.items() if v]
    missing = [k for k, v in sections.items() if not v]

    core_missing = [k for k in ("Experience", "Education", "Skills") if not sections[k]]

    if not core_missing:
        return ATSCheckItem(
            name="standard_sections",
            status="pass",
            detail=f"Found all key sections: {', '.join(found)}."
        )
    elif len(core_missing) == 1:
        return ATSCheckItem(
            name="standard_sections",
            status="warn",
            detail=f"Missing standard section header for: {core_missing[0]}. Found: {', '.join(found)}."
        )
    else:
        return ATSCheckItem(
            name="standard_sections",
            status="fail",
            detail=f"Missing critical section headers: {', '.join(core_missing)}. ATS parsers may fail to segment your resume."
        )


def check_contact_info(text: str) -> ATSCheckItem:
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    linkedin_match = re.search(r"(linkedin\.com/in/[a-zA-Z0-9_-]+|github\.com/[a-zA-Z0-9_-]+)", text, re.I)

    if email_match and phone_match:
        detail = "Detected valid email and phone number."
        if linkedin_match:
            detail += " LinkedIn/GitHub profile link detected."
        return ATSCheckItem(
            name="contact_info",
            status="pass",
            detail=detail
        )
    elif email_match and not phone_match:
        return ATSCheckItem(
            name="contact_info",
            status="warn",
            detail="Email detected, but no phone number found. Add a reachable phone number."
        )
    elif phone_match and not email_match:
        return ATSCheckItem(
            name="contact_info",
            status="warn",
            detail="Phone number detected, but no email address found. Add a professional email."
        )
    else:
        return ATSCheckItem(
            name="contact_info",
            status="fail",
            detail="No contact email or phone number detected. ATS cannot route your application."
        )


def check_multi_column_tables(text: str) -> ATSCheckItem:
    """
    Heuristic to detect multi-column interleaving or excessive table delimiters.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ATSCheckItem(name="multi_column_tables", status="pass", detail="Single column layout.")

    # Check for tab separators or table pipe delimiters
    pipe_count = sum(1 for line in lines if "|" in line or "\t\t" in line)
    short_line_runs = 0
    consecutive_short = 0

    for line in lines:
        if len(line) < 22:
            consecutive_short += 1
            if consecutive_short >= 5:
                short_line_runs += 1
        else:
            consecutive_short = 0

    if pipe_count > 6 or short_line_runs >= 3:
        return ATSCheckItem(
            name="multi_column_tables",
            status="warn",
            detail="Possible multi-column or table artifacts detected. Single-column linear layout is safest for ATS."
        )
    return ATSCheckItem(
        name="multi_column_tables",
        status="pass",
        detail="Linear single-column text flow detected without heavy table artifacts."
    )


def check_length(text: str) -> ATSCheckItem:
    words = text.split()
    word_count = len(words)

    if MIN_WORD_COUNT <= word_count <= MAX_WORD_COUNT:
        return ATSCheckItem(
            name="resume_length",
            status="pass",
            detail=f"Optimal length ({word_count} words, approx 1-2 standard pages)."
        )
    elif word_count < MIN_WORD_COUNT:
        return ATSCheckItem(
            name="resume_length",
            status="warn",
            detail=f"Resume is brief ({word_count} words < {MIN_WORD_COUNT} min). May lack sufficient technical depth."
        )
    else:
        return ATSCheckItem(
            name="resume_length",
            status="warn",
            detail=f"Resume is long ({word_count} words > {MAX_WORD_COUNT} max). Consider condensing to 2 focused pages."
        )


def check_bullet_density(text: str) -> ATSCheckItem:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ATSCheckItem(name="bullet_point_density", status="warn", detail="No text lines found.")

    bullet_prefixes = ("•", "*", "-", "–", "—", "\u2022", "\u25e6", "\u25aa", "▪")
    bullet_lines = sum(1 for line in lines if line.startswith(bullet_prefixes) or re.match(r"^\d+\.", line))

    ratio = bullet_lines / max(len(lines), 1)

    if ratio >= 0.25:
        return ATSCheckItem(
            name="bullet_point_density",
            status="pass",
            detail=f"Good bullet point structure ({bullet_lines} bulleted items, {int(ratio*100)}% of content)."
        )
    elif ratio >= 0.12:
        return ATSCheckItem(
            name="bullet_point_density",
            status="warn",
            detail="Moderate bullet point usage. Convert dense paragraph descriptions into bulleted achievements."
        )
    else:
        return ATSCheckItem(
            name="bullet_point_density",
            status="warn",
            detail="Low bullet point usage. ATS parsers and recruiters scan bulleted bullet points significantly better than dense paragraphs."
        )


def run_layer1_checks(text: str, filename: str) -> List[ATSCheckItem]:
    """
    Executes all deterministic Rule-Based parseability checks.
    """
    return [
        check_file_format(filename),
        check_filename_conventions(filename),
        check_standard_sections(text),
        check_contact_info(text),
        check_multi_column_tables(text),
        check_length(text),
        check_bullet_density(text),
    ]


# ============================================================================
# Layer 2 — Content-Quality Signals via HuggingFace Models (Lazy-Loaded)
# ============================================================================
def _safe_import_transformers_pipeline():
    import sys
    # Suppress broken torchvision C-extensions if present in environment
    if "torchvision" not in sys.modules or sys.modules["torchvision"] is None:
        try:
            import torchvision
        except Exception:
            sys.modules["torchvision"] = None
    from transformers import pipeline
    return pipeline


def is_model_cached(model_id: str) -> bool:
    """Checks if model weights exist locally in the HuggingFace cache directory."""
    from pathlib import Path
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


@lru_cache(maxsize=1)
def _get_ner_pipeline():
    """
    Lazy-loads yashpwr/resume-ner-bert-v2 token classification pipeline only if pre-cached locally.
    Prevents OOM memory exhaustion (Exit 137) during runtime web requests.
    """
    if not is_model_cached(NER_MODEL_NAME):
        return None
    pipeline = _safe_import_transformers_pipeline()
    logger.info("Loading Resume NER model (%s) - first call only", NER_MODEL_NAME)
    return pipeline("token-classification", model=NER_MODEL_NAME, aggregation_strategy="simple")


@lru_cache(maxsize=1)
def _get_role_classifier_pipeline():
    """
    Lazy-loads srivihari/resume-job-role-classifier text classification pipeline only if pre-cached locally.
    """
    if not is_model_cached(ROLE_MODEL_NAME):
        return None
    pipeline = _safe_import_transformers_pipeline()
    logger.info("Loading Role Classifier model (%s) - first call only", ROLE_MODEL_NAME)
    return pipeline("text-classification", model=ROLE_MODEL_NAME)


def _run_with_timeout(func, *args, timeout_sec=2.5, **kwargs):
    """Executes a function with a timeout, returning None if timed out or failed."""
    import concurrent.futures
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            return future.result(timeout=timeout_sec)
    except Exception as exc:
        logger.info("ML check timed out (%ss) or failed: %s. Using heuristic entity signals.", timeout_sec, exc)
        return None


def run_ml_checks(text: str) -> List[ATSCheckItem]:
    """
    Executes Layer 2 HuggingFace ML checks with timeout protection.
    If models fail to load or error out, returns 'unavailable' checks without blocking.
    """
    ml_results = []
    text_sample = text[:2500]  # Standard context window for ML

    # 1. Resume NER check (Skills, Designation, Degree extraction)
    try:
        ner_pipe = _run_with_timeout(_get_ner_pipeline, timeout_sec=2.5)
        if ner_pipe is None:
            raise RuntimeError("NER pipeline loading timed out")
        ner_entities = ner_pipe(text_sample)

        skills_found = set()
        designations_found = set()
        degrees_found = set()

        for ent in ner_entities:
            entity_group = ent.get("entity_group", "").lower()
            word = ent.get("word", "").strip()
            if not word or len(word) < 2:
                continue

            if "skill" in entity_group:
                skills_found.add(word)
            elif "designation" in entity_group or "role" in entity_group or "title" in entity_group:
                designations_found.add(word)
            elif "degree" in entity_group or "education" in entity_group:
                degrees_found.add(word)

        if len(skills_found) >= 4:
            ml_results.append(ATSCheckItem(
                name="skills_extractable",
                status="pass",
                detail=f"NER model successfully extracted {len(skills_found)} distinct technical skills (e.g. {', '.join(list(skills_found)[:3])}).",
                model=NER_MODEL_NAME
            ))
        elif len(skills_found) >= 1:
            ml_results.append(ATSCheckItem(
                name="skills_extractable",
                status="warn",
                detail=f"NER model extracted only {len(skills_found)} skill(s). Ensure skills are explicitly listed under a dedicated 'Skills' header.",
                model=NER_MODEL_NAME
            ))
        else:
            ml_results.append(ATSCheckItem(
                name="skills_extractable",
                status="warn",
                detail="No distinct skill entities extracted by NER model. ATS parsers may fail to extract your technical competencies.",
                model=NER_MODEL_NAME
            ))

        if designations_found:
            ml_results.append(ATSCheckItem(
                name="designation_extractable",
                status="pass",
                detail=f"NER model detected job titles ({', '.join(list(designations_found)[:2])}).",
                model=NER_MODEL_NAME
            ))
        else:
            ml_results.append(ATSCheckItem(
                name="designation_extractable",
                status="warn",
                detail="No clear job designation entities extracted. Use standard industry titles (e.g. 'Senior Software Engineer').",
                model=NER_MODEL_NAME
            ))

    except Exception as exc:
        logger.warning("NER model inference unavailable: %s", exc)
        ml_results.append(ATSCheckItem(
            name="skills_extractable",
            status="unavailable",
            detail=f"NER model check unavailable ({type(exc).__name__}) - Rule-based parseability active.",
            model=NER_MODEL_NAME
        ))

    # 2. Job Role Classifier check (Coherence and Domain confidence)
    try:
        classifier = _run_with_timeout(_get_role_classifier_pipeline, timeout_sec=2.5)
        if classifier is None:
            raise RuntimeError("Role classifier loading timed out")
        classification = classifier(text_sample)

        if classification and isinstance(classification, list):
            top_result = classification[0]
            label = top_result.get("label", "General")
            score = float(top_result.get("score", 0.0))

            if score >= 0.50:
                ml_results.append(ATSCheckItem(
                    name="role_coherence",
                    status="pass",
                    detail=f"Classified as '{label}' with {int(score*100)}% domain confidence. Resume provides coherent professional signal.",
                    model=ROLE_MODEL_NAME
                ))
            else:
                ml_results.append(ATSCheckItem(
                    name="role_coherence",
                    status="warn",
                    detail=f"Classified as '{label}' with moderate confidence ({int(score*100)}%). Resume may present mixed domain signals.",
                    model=ROLE_MODEL_NAME
                ))
        else:
            ml_results.append(ATSCheckItem(
                name="role_coherence",
                status="unavailable",
                detail="Classifier returned no labels.",
                model=ROLE_MODEL_NAME
            ))
    except Exception as exc:
        logger.warning("Role classifier model unavailable: %s", exc)
        ml_results.append(ATSCheckItem(
            name="role_coherence",
            status="unavailable",
            detail=f"Classifier check unavailable ({type(exc).__name__}) - Rule-based parseability active.",
            model=ROLE_MODEL_NAME
        ))

    return ml_results


# ============================================================================
# Combined Scoring & Prioritized Recommendation Compiler
# ============================================================================
def calculate_ats_audit(text: str, filename: str = "resume.pdf") -> ATSCheckResult:
    """
    Executes full hybrid ATS check (Layer 1 + Layer 2) and calculates weighted score.
    """
    if not text or not text.strip():
        raise ValueError("Resume text is empty or could not be parsed.")

    # 1. Run Layer 1
    rule_checks = run_layer1_checks(text, filename)

    # Calculate Layer 1 score
    l1_scores = []
    for c in rule_checks:
        if c.status == "pass":
            l1_scores.append(1.0)
        elif c.status == "warn":
            l1_scores.append(0.5)
        else:
            l1_scores.append(0.0)

    layer1_score = (sum(l1_scores) / max(len(rule_checks), 1)) * 100

    # 2. Run Layer 2
    ml_checks = run_ml_checks(text)

    # Calculate Layer 2 score (excluding 'unavailable')
    available_ml = [c for c in ml_checks if c.status != "unavailable"]
    if available_ml:
        l2_scores = []
        for c in available_ml:
            if c.status == "pass":
                l2_scores.append(1.0)
            elif c.status == "warn":
                l2_scores.append(0.5)
            else:
                l2_scores.append(0.0)
        layer2_score = (sum(l2_scores) / len(available_ml)) * 100
        overall_score = round(layer1_score * LAYER1_WEIGHT + layer2_score * LAYER2_WEIGHT)
    else:
        layer2_score = None
        overall_score = round(layer1_score)

    overall_score = max(0, min(100, overall_score))

    # Overall Label
    if overall_score >= THRESHOLD_ATS_FRIENDLY:
        label = "ATS-Friendly"
    elif overall_score >= THRESHOLD_NEEDS_IMPROVEMENT:
        label = "Needs Improvement"
    else:
        label = "High Risk"

    # Compile prioritized recommendations
    recommendations = []

    # Priority 1: Layer 1 failures
    for c in rule_checks:
        if c.status == "fail":
            if c.name == "standard_sections":
                recommendations.append("Add standard section headers: 'Work Experience', 'Education', and 'Skills'.")
            elif c.name == "contact_info":
                recommendations.append("Include clearly readable email and phone number at the very top of your resume.")
            else:
                recommendations.append(c.detail)

    # Priority 2: Layer 1 warnings
    for c in rule_checks:
        if c.status == "warn":
            if c.name == "multi_column_tables":
                recommendations.append("Avoid multi-column tables, graphics, or side-by-side text boxes — use a clean single-column linear layout.")
            elif c.name == "bullet_point_density":
                recommendations.append("Structure your experience with concise, action-verb bullet points instead of dense narrative paragraphs.")
            elif c.name == "filename_conventions":
                recommendations.append("Rename your file using clean naming: 'FirstName_LastName_Resume.pdf'.")
            elif c.name == "resume_length":
                recommendations.append(c.detail)
            else:
                recommendations.append(c.detail)

    # Priority 3: Layer 2 ML suggestions
    for c in ml_checks:
        if c.status in ("warn", "fail"):
            if c.name == "skills_extractable":
                recommendations.append("List your technical skills (languages, frameworks, databases, tools) in a distinct bulleted Skills section.")
            elif c.name == "role_coherence":
                recommendations.append("Sharpen your resume headline and summary to clearly communicate your primary target job title.")

    if not recommendations:
        recommendations.append("Your resume meets all core ATS parseability and structural standards. Ready for submission!")

    return ATSCheckResult(
        overall_score=overall_score,
        label=label,
        layer1_score=round(layer1_score, 1),
        layer2_score=round(layer2_score, 1) if layer2_score is not None else None,
        rule_based_checks=rule_checks,
        ml_checks=ml_checks,
        recommendations=recommendations
    )
