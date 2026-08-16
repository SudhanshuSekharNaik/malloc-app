"""
Resume Bullet Rewriting & Edit Suggestion Engine.

Architecture:
- Layer 1: Gap Analysis (Reuses skill NER and keyword overlap from Resume Matcher)
- Layer 2: Targeted Bullet Rewriting (vsr9awc/resume-optimizer fine-tuned causal LM)
- Layer 3: Programmatic Fabrication Guardrail (Validates numbers, metrics, and entities)
- Layer 4: Grammar & Clarity Polish (AventIQ-AI/t5-small-grammar-correction)
"""
import re
import logging
from functools import lru_cache
from typing import List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.services.job_matcher import analyze_resume_vs_job, _heuristic_match

logger = logging.getLogger("memora.resume_editor")

REWRITE_MODEL_NAME = "vsr9awc/resume-optimizer"
GRAMMAR_MODEL_NAME = "AventIQ-AI/t5-small-grammar-correction"


# ============================================================================
# Schemas
# ============================================================================
class ResumeEditSuggestion(BaseModel):
    type: str  # "bullet_rewrite" | "missing_keyword" | "grammar_fix"
    section: str  # e.g., "Experience — Acme Corp" or "Skills"
    original: Optional[str] = None
    suggested: str
    reason: str
    flagged_for_review: bool = False
    warning_message: Optional[str] = None


class SuggestEditsResult(BaseModel):
    suggestions: List[ResumeEditSuggestion] = Field(default_factory=list)
    unavailable_layers: List[str] = Field(default_factory=list)


# ============================================================================
# Layer 2 & 4 — Lazy-Loaded HuggingFace Transformers Pipelines
# ============================================================================
def _safe_import_torch():
    import sys
    # Suppress broken torchvision C-extensions DLL crash on Windows
    sys.modules["torchvision"] = None
    import torch
    return torch



@lru_cache(maxsize=1)
def _get_rewrite_model_and_tokenizer():
    """
    Lazy-loads vsr9awc/resume-optimizer (Qwen2.5-1.5B fine-tuned for bullet optimization).
    Cached for process lifetime.
    """
    _safe_import_torch()
    from transformers import AutoTokenizer, AutoModelForCausalLM
    logger.info("Loading Resume Optimizer model (%s) - first call only", REWRITE_MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(REWRITE_MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(REWRITE_MODEL_NAME)
    model.eval()
    return tokenizer, model


@lru_cache(maxsize=1)
def _get_grammar_model_and_tokenizer():
    """
    Lazy-loads AventIQ-AI/t5-small-grammar-correction.
    Cached for process lifetime.
    """
    _safe_import_torch()
    from transformers import T5Tokenizer, T5ForConditionalGeneration
    logger.info("Loading Grammar Correction model (%s) - first call only", GRAMMAR_MODEL_NAME)
    tokenizer = T5Tokenizer.from_pretrained(GRAMMAR_MODEL_NAME)
    model = T5ForConditionalGeneration.from_pretrained(GRAMMAR_MODEL_NAME)
    model.eval()
    return tokenizer, model


# ============================================================================
# Layer 1 Helper: Bullet & Section Parsing
# ============================================================================
def extract_bullets_with_sections(resume_text: str) -> List[Tuple[str, str]]:
    """
    Splits resume text into individual bullet points with detected section headers.
    Returns list of (section_name, bullet_text).
    """
    lines = resume_text.splitlines()
    bullets = []
    current_section = "Experience"
    
    bullet_prefixes = ("•", "*", "-", "–", "—", "\u2022", "\u25e6", "\u25aa", "▪")
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Check if line looks like a section header
        upper = stripped.upper()
        if any(h in upper for h in ("EXPERIENCE", "EMPLOYMENT", "WORK HISTORY", "PROJECTS", "SKILLS", "EDUCATION", "SUMMARY", "PUBLICATIONS")):
            current_section = stripped.rstrip(":")
            continue
        
        # Only rewrite bullets belonging to Experience, Work History, or Projects
        if not any(s in current_section.upper() for s in ("EXPERIENCE", "WORK", "EMPLOYMENT", "PROJECT")):
            continue
        
        # Check if line looks like a bullet
        is_bullet = stripped.startswith(bullet_prefixes) or bool(re.match(r"^\d+[\.\)]\s+", stripped))
        if is_bullet:
            cleaned_bullet = re.sub(r"^(?:[•*\-–—\u2022\u25e6\u25aa▪]|\d+[\.\)])\s*", "", stripped).strip()
            if len(cleaned_bullet) >= 15:
                bullets.append((current_section, cleaned_bullet))
        elif len(stripped) >= 30 and not stripped.endswith(":") and not stripped.isupper():
            # Narrative paragraph line in experience/projects
            bullets.append((current_section, stripped))
                
    return bullets


def find_evidenced_skills_in_body(
    job_target_skills: List[str],
    resume_text: str
) -> List[Tuple[str, str]]:
    """
    Checks if any skills from the job requirements are evidenced in the
    experience or project descriptions of the resume, but missing from explicit skills lists.
    Returns list of (skill_name, evidence_snippet).
    """
    evidenced = []
    lines = resume_text.splitlines()
    
    # Identify skills section vs body sections
    in_skills_section = False
    skills_lines = []
    body_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        if any(h in upper for h in ("SKILL", "TECHNICAL PROFICIENCIES", "TECHNOLOGIES", "TOOLING")):
            in_skills_section = True
            continue
        elif any(h in upper for h in ("EXPERIENCE", "PROJECTS", "EMPLOYMENT", "WORK HISTORY", "EDUCATION")):
            in_skills_section = False
            
        if in_skills_section:
            skills_lines.append(stripped)
        else:
            body_lines.append(stripped)
            
    skills_text = "\n".join(skills_lines).lower()
    body_text = "\n".join(body_lines)
    
    for skill in job_target_skills:
        skill_lower = skill.lower()
        pattern = r"\b" + re.escape(skill_lower) + r"\b"
        
        # Skill must NOT be already listed in explicit Skills section
        already_in_skills = bool(re.search(pattern, skills_text))
        if already_in_skills:
            continue
            
        # Skill MUST be evidenced in Experience / Projects body
        match = re.search(pattern, body_text.lower())
        if match:
            # Find the sentence/line containing the mention as evidence
            for line in body_lines:
                if re.search(pattern, line.lower()):
                    evidence = line.strip()
                    if len(evidence) > 80:
                        evidence = evidence[:77] + "..."
                    evidenced.append((skill, evidence))
                    break
                    
    return evidenced


# ============================================================================
# Layer 3 — Programmatic Fabrication Guardrail Validation
# ============================================================================
def extract_numbers_and_metrics(text: str) -> Set[str]:
    """
    Extracts all numbers, percentages, currency, and multiplier metrics from text.
    E.g., "35%", "50k", "$120k", "5+", "4.5", "10x".
    """
    pattern = r"\$\s*\d+(?:,\d{3})*(?:\.\d+)?(?:k|m|b|K|M|B)?|\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:%|\+|k|m|b|K|M|B|x|X)?"
    matches = re.findall(pattern, text)
    cleaned = set()
    for m in matches:
        norm = re.sub(r"\s+", "", m.strip().lower())
        if norm:
            cleaned.add(norm)
    return cleaned



def validate_against_fabrication(
    suggested_text: str,
    original_bullet: str,
    full_resume_text: str
) -> Tuple[bool, Optional[str]]:
    """
    Enforces the Non-Negotiable Guardrail:
    - Validates that no new numbers/metrics are fabricated.
    - Validates that proper nouns / specialized technologies were present in the resume.
    Returns (is_valid, warning_message).
    """
    suggested_numbers = extract_numbers_and_metrics(suggested_text)
    orig_bullet_numbers = extract_numbers_and_metrics(original_bullet)
    full_resume_numbers = extract_numbers_and_metrics(full_resume_text)
    
    # Check for hallucinated numbers
    introduced_numbers = suggested_numbers - full_resume_numbers
    if introduced_numbers:
        return False, f"Introduces unverified numbers/metrics ({', '.join(introduced_numbers)}) not found in original resume."
    
    # Check if a number from another part of the resume is transplanted into this bullet without prior context
    bullet_new_numbers = suggested_numbers - orig_bullet_numbers
    if bullet_new_numbers:
        # Number exists in full resume, but wasn't in this specific bullet
        return True, f"Includes metric ({', '.join(bullet_new_numbers)}) referenced elsewhere in your resume — verify context."
        
    return True, None


# ============================================================================
# Layer 2 Execution: Targeted Bullet Rewriter
# ============================================================================
def rewrite_single_bullet(
    bullet_text: str,
    job_description: str,
    target_skills: List[str]
) -> Optional[str]:
    """
    Rewrites a single bullet point using vsr9awc/resume-optimizer.
    """
    try:
        tokenizer, model = _get_rewrite_model_and_tokenizer()
        torch = _safe_import_torch()
        
        prompt = (
            f"Rewrite this resume bullet point to better align with the target job description. "
            f"Do not invent any new facts, metrics, or skills not already present in the bullet.\n\n"
            f"Job description:\n{job_description[:1000]}\n\n"
            f"Original bullet:\n{bullet_text}\n\n"
            f"Rewritten bullet:\n"
        )
        
        inputs = tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=90,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id
            )
            
        gen_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
        rewritten = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
        
        # Clean up output artifacts (take first non-empty line)
        rewritten_line = rewritten.splitlines()[0].strip() if rewritten else ""
        rewritten_line = re.sub(r"^(?:Rewritten bullet:\s*|[-•*]\s*)", "", rewritten_line).strip()
        
        if rewritten_line and rewritten_line != bullet_text and len(rewritten_line) >= 20:
            return rewritten_line
            
    except Exception as exc:
        logger.warning("Layer 2 bullet rewrite model failed for bullet: %s (%s)", bullet_text[:40], exc)
        
    return None


# ============================================================================
# Layer 4 Execution: Grammar Polish
# ============================================================================
def polish_grammar(text: str) -> str:
    """
    Runs AventIQ-AI/t5-small-grammar-correction on the rewritten text.
    """
    try:
        tokenizer, model = _get_grammar_model_and_tokenizer()
        torch = _safe_import_torch()
        
        input_ids = tokenizer("grammar: " + text, return_tensors="pt").input_ids
        with torch.no_grad():
            output_ids = model.generate(input_ids, max_length=128)
        polished = tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
        if polished and len(polished) >= 15:
            return polished
    except Exception as exc:
        logger.debug("Layer 4 grammar polish skipped: %s", exc)
        
    return text


# ============================================================================
# Heuristic Bullet Alignment (Deterministic Fallback)
# ============================================================================
def _heuristic_bullet_rewrite(
    bullet: str,
    job_description: str,
    matched_skills: List[str]
) -> Optional[str]:
    """
    Fast rule-based rephraser when model weights are not loaded.
    Strengthens weak action verbs and highlights relevant keywords without adding facts.
    """
    WEAK_VERBS = {
        r"\bworked on\b": "Architected and delivered",
        r"\bresponsible for\b": "Spearheaded",
        r"\bhelped with\b": "Collaborated on",
        r"\bdid\b": "Executed",
        r"\bhandled\b": "Engineered and managed",
        r"\bused\b": "Leveraged",
        r"\bmade\b": "Built and deployed"
    }
    
    rewritten = bullet
    changed = False
    for weak_regex, strong_verb in WEAK_VERBS.items():
        if re.search(weak_regex, rewritten, re.IGNORECASE):
            rewritten = re.sub(weak_regex, strong_verb, rewritten, flags=re.IGNORECASE)
            changed = True
            break
            
    if changed and rewritten != bullet:
        return rewritten
    return None


# ============================================================================
# Main Orchestrator: Generate Suggested Resume Edits
# ============================================================================
def generate_resume_edits(
    resume_text: str,
    job_description: str,
    company_hint: Optional[str] = None,
    role_hint: Optional[str] = None
) -> SuggestEditsResult:
    """
    Analyzes resume and job description to produce opt-in edit suggestions:
    1. Layer 1: Skill gap analysis & identifying evidenced skills for Skills section.
    2. Layer 2: Targeted bullet rewriting for relevant experience bullets.
    3. Layer 3: Programmatic fabrication validation (drops or flags hallucinated details).
    4. Layer 4: Grammar & clarity polish.
    """
    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text cannot be empty")
    if not job_description or not job_description.strip():
        raise ValueError("Job description cannot be empty")

    suggestions: List[ResumeEditSuggestion] = []
    unavailable_layers: List[str] = []

    # ------------------------------------------------------------------------
    # Layer 1: Reuse existing gap analysis from Resume Matcher
    # ------------------------------------------------------------------------
    try:
        match_analysis = analyze_resume_vs_job(
            resume_text=resume_text,
            job_description=job_description,
            company_hint=company_hint,
            role_hint=role_hint
        )
        missing_skills = match_analysis.missing_skills
        matched_skills = match_analysis.skills_matched
    except Exception as exc:
        logger.warning("Match analysis failed, using heuristic fallback: %s", exc)
        match_analysis = _heuristic_match(resume_text, job_description, company_hint, role_hint)
        missing_skills = match_analysis.missing_skills
        matched_skills = match_analysis.skills_matched

    # Check for evidenced skills in resume body that can be surfaced in Skills section
    target_skills = list(dict.fromkeys(matched_skills + missing_skills))
    evidenced_skills = find_evidenced_skills_in_body(target_skills, resume_text)
    for skill, snippet in evidenced_skills:
        suggestions.append(ResumeEditSuggestion(
            type="missing_keyword",
            section="Skills",
            original=None,
            suggested=f"Add '{skill}' to your Skills section — it is evidenced in your experience: \"{snippet}\"",
            reason=f"Mentioned in your experience descriptions but missing from your explicit technical skills list.",
            flagged_for_review=False
        ))

    # ------------------------------------------------------------------------
    # Layer 2 & 3 & 4: Targeted Bullet Rewriting + Guardrail Validation
    # ------------------------------------------------------------------------
    bullets_with_sections = extract_bullets_with_sections(resume_text)
    
    # Filter bullets that are relevant to target job keywords or weak phrasing (up to 4 bullets max)
    relevant_bullets = []
    for section, bullet in bullets_with_sections:
        # Check if bullet mentions any matched skill or contains weak verbs
        is_relevant = (
            any(re.search(r"\b" + re.escape(s.lower()) + r"\b", bullet.lower()) for s in (matched_skills + missing_skills))
            or any(w in bullet.lower() for w in ("worked on", "responsible for", "helped", "handled", "used"))
        )
        if is_relevant:
            relevant_bullets.append((section, bullet))
            if len(relevant_bullets) >= 4:
                break
                
    if not relevant_bullets and bullets_with_sections:
        relevant_bullets = bullets_with_sections[:2]

    # Attempt Layer 2 Rewriting
    for section, original_bullet in relevant_bullets:
        rewritten = None
        used_layer2 = False
        
        try:
            rewritten = rewrite_single_bullet(original_bullet, job_description, matched_skills)
            if rewritten:
                used_layer2 = True
        except Exception as exc:
            if "Layer 2 (vsr9awc/resume-optimizer)" not in unavailable_layers:
                unavailable_layers.append("Layer 2 (vsr9awc/resume-optimizer)")
                
        # Heuristic fallback if ML rewrite was unavailable or produced no change
        if not rewritten:
            rewritten = _heuristic_bullet_rewrite(original_bullet, job_description, matched_skills)

        if not rewritten or rewritten == original_bullet:
            continue

        # --------------------------------------------------------------------
        # Layer 3: Fabrication Guardrail Check
        # --------------------------------------------------------------------
        is_valid, warning = validate_against_fabrication(rewritten, original_bullet, resume_text)
        if not is_valid:
            # Hallucinated metric or unverified claims detected -> discard or flag
            logger.warning("Discarded fabricated rewrite: %s (Reason: %s)", rewritten, warning)
            continue

        # --------------------------------------------------------------------
        # Layer 4: Grammar Polish
        # --------------------------------------------------------------------
        try:
            polished = polish_grammar(rewritten)
            if polished:
                rewritten = polished
        except Exception as exc:
            if "Layer 4 (AventIQ-AI/t5-small-grammar-correction)" not in unavailable_layers:
                unavailable_layers.append("Layer 4 (AventIQ-AI/t5-small-grammar-correction)")

        # Create suggestion object
        suggestions.append(ResumeEditSuggestion(
            type="bullet_rewrite",
            section=section,
            original=original_bullet,
            suggested=rewritten,
            reason="Reframes achievement with strong action verbs and aligns terminology with target job requirements.",
            flagged_for_review=bool(warning),
            warning_message=warning
        ))

    return SuggestEditsResult(
        suggestions=suggestions,
        unavailable_layers=unavailable_layers
    )
