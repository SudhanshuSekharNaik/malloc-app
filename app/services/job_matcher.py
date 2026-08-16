"""
LLM Comparative Job Matching & Resume Scoring Service.

Compares resume text against job description and produces structured scoring,
skill breakdown, gaps, recommendations, and application pitch.
"""
import json
import logging
import re
from typing import List, Optional
from pydantic import BaseModel, Field

from app.llm import call_llm, LLMError

logger = logging.getLogger("memora.matcher")

MATCHER_SYSTEM_PROMPT = """You are an expert AI Technical Recruiter and Career Coach.
Your task is to analyze a candidate's Resume against a specific Job Description.

Perform a rigorous, fair, and constructive evaluation:
1. Calculate an accurate Overall Match Score between 0 and 100 based on technical skills, domain experience, seniority, and tooling.
2. Determine Verdict: "Strong Match" (80-100), "Good Match" (65-79), "Moderate Match" (50-64), or "Low Match" (<50).
3. Identify Matching Skills and Missing/Gap Skills.
4. Provide concrete, actionable recommendations on how to tailor the resume for this exact role.
5. Write a concise, compelling 2-3 sentence tailored pitch for a cover letter or LinkedIn outreach to the hiring manager.

You MUST reply ONLY with a valid JSON object strictly adhering to this schema:
{
  "match_score": 85,
  "verdict": "Strong Match",
  "company": "Company Name",
  "role_title": "Job Title",
  "summary": "2-3 sentences summarizing the fit and core overlap.",
  "skills_matched": ["Python", "FastAPI", "PostgreSQL", "Docker"],
  "missing_skills": ["Kubernetes", "AWS Lambda"],
  "experience_fit": "Candidate has 5+ years matching the required 4+ years for Senior Engineer.",
  "key_strengths": [
    "Strong backend engineering background with Python and modern async frameworks",
    "Direct experience in API design and database optimization"
  ],
  "recommendations": [
    "Highlight experience with container orchestration or cloud services in the summary.",
    "Add quantitative metrics to recent project achievements."
  ],
  "tailored_pitch": "With 5+ years building scalable Python/FastAPI microservices and RAG architectures, I have direct experience delivering the high-throughput systems your team is looking for. I would love to bring my expertise in backend engineering to this role."
}

Do not include any conversational preamble or markdown code fences other than the raw JSON object.
"""


class MatchAnalysisResult(BaseModel):
    match_score: int = Field(..., ge=0, le=100)
    verdict: str
    company: Optional[str] = None
    role_title: Optional[str] = None
    summary: str
    skills_matched: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    experience_fit: str
    key_strengths: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    tailored_pitch: str


class MatcherError(RuntimeError):
    """Raised when match analysis fails."""


def _heuristic_match(
    resume_text: str,
    job_description: str,
    company_hint: Optional[str],
    role_hint: Optional[str]
) -> MatchAnalysisResult:
    """
    Intelligent rule-based fallback when LLM API key is not yet configured.
    Ensures users can test the matcher without getting blocked.
    """
    COMMON_SKILLS = [
        "Python", "JavaScript", "TypeScript", "React", "Node.js", "Next.js", "FastAPI",
        "Django", "Flask", "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker",
        "Kubernetes", "AWS", "GCP", "Azure", "Git", "CI/CD", "REST", "GraphQL",
        "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "LLMs", "LangChain",
        "Vector Search", "FAISS", "NLP", "Linux", "Java", "C++", "Golang", "Rust",
        "TailwindCSS", "HTML", "CSS", "Microservices", "System Design", "Agile", "Scrum"
    ]

    jd_lower = job_description.lower()
    resume_lower = resume_text.lower()

    # Find skills mentioned in JD
    jd_skills = [s for s in COMMON_SKILLS if re.search(r'\b' + re.escape(s.lower()) + r'\b', jd_lower)]
    if not jd_skills:
        jd_skills = ["Software Engineering", "API Design", "Problem Solving", "Collaboration"]

    matched_skills = [s for s in jd_skills if re.search(r'\b' + re.escape(s.lower()) + r'\b', resume_lower)]
    missing_skills = [s for s in jd_skills if s not in matched_skills]

    # Calculate match score based on skill overlap
    overlap_ratio = len(matched_skills) / max(len(jd_skills), 1)
    base_score = int(40 + (overlap_ratio * 55))
    score = min(max(base_score, 30), 96)

    if score >= 80:
        verdict = "Strong Match"
    elif score >= 65:
        verdict = "Good Match"
    elif score >= 50:
        verdict = "Moderate Match"
    else:
        verdict = "Low Match"

    company = company_hint or "Target Company"
    role = role_hint or "Target Role"

    summary = (
        f"Matched {len(matched_skills)} of {len(jd_skills)} target core requirements. "
        f"Candidate exhibits relevant background in {', '.join(matched_skills[:3]) if matched_skills else 'core fundamentals'}. "
        f"[Heuristic Mode — Add your free GROQ_API_KEY in Settings for AI deep analysis]"
    )

    key_strengths = [
        f"Demonstrated proficiency in {s}" for s in matched_skills[:4]
    ] or ["Solid foundation in core software engineering principles"]

    recommendations = []
    if missing_skills:
        recommendations.append(f"Incorporate project examples highlighting experience with {', '.join(missing_skills[:3])}.")
    recommendations.append("Quantify business outcomes and performance metrics in recent work experience.")
    recommendations.append("Align resume summary keywords directly with the job description terminology.")

    tailored_pitch = (
        f"With direct experience in {', '.join(matched_skills[:3]) if matched_skills else 'software development'}, "
        f"I am well-equipped to contribute to the {role} role at {company}. "
        f"I look forward to discussing how my skills align with your team's objectives."
    )

    return MatchAnalysisResult(
        match_score=score,
        verdict=verdict,
        company=company,
        role_title=role,
        summary=summary,
        skills_matched=matched_skills,
        missing_skills=missing_skills,
        experience_fit=f"Alignment across {len(matched_skills)} core technical domain areas.",
        key_strengths=key_strengths,
        recommendations=recommendations,
        tailored_pitch=tailored_pitch
    )


def analyze_resume_vs_job(
    resume_text: str,
    job_description: str,
    company_hint: Optional[str] = None,
    role_hint: Optional[str] = None,
) -> MatchAnalysisResult:
    """
    Calls LLM to compare resume against job description.
    Falls back gracefully to heuristic matching if no LLM API key is configured.
    """
    if not resume_text.strip():
        raise MatcherError("Resume text is empty")
    if not job_description.strip():
        raise MatcherError("Job description is empty")

    prompt = f"""### CANDIDATE RESUME:
{resume_text[:6000]}

### JOB POSTING (Company: {company_hint or 'Not specified'}, Role: {role_hint or 'Not specified'}):
{job_description[:6000]}

Analyze and return the comparison JSON object now:"""

    messages = [{"role": "user", "content": prompt}]

    try:
        raw_response = call_llm(messages, system=MATCHER_SYSTEM_PROMPT)
    except LLMError as exc:
        err_msg = str(exc)
        logger.warning("LLM call failed (%s), utilizing heuristic matcher fallback", err_msg)
        if "API_KEY is not configured" in err_msg or "not configured" in err_msg:
            return _heuristic_match(resume_text, job_description, company_hint, role_hint)
        raise MatcherError(f"LLM analysis failed: {exc}") from exc

    # Clean potential markdown wrapping
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        # Ensure company and role are filled if hints provided
        if not data.get("company") and company_hint:
            data["company"] = company_hint
        if not data.get("role_title") and role_hint:
            data["role_title"] = role_hint
        return MatchAnalysisResult.model_validate(data)
    except Exception as exc:
        logger.error("Failed to parse LLM matcher output: %s\nRaw output: %s", exc, raw_response)
        return _heuristic_match(resume_text, job_description, company_hint, role_hint)

