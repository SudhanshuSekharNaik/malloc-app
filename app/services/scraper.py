"""
Job Posting URL Scraper & Content Extractor.

Extracts job title, company name, and full description text from LinkedIn,
Indeed, Greenhouse, Lever, Workday, and generic career postings.
"""
import re
import logging
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("memora.scraper")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class ScrapedJob(BaseModel):
    url: str
    company: str = ""
    role_title: str = ""
    description: str = ""
    success: bool = True
    message: str = ""


def clean_text(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    # Remove script, style, nav, footer, header tags
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Clean excessive whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def parse_job_html(url: str, html_content: str) -> ScrapedJob:
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Meta / OpenGraph detection
    og_title = ""
    og_desc = ""
    og_site = ""

    tag = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "title"})
    if tag and tag.get("content"):
        og_title = tag["content"].strip()

    tag = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
    if tag and tag.get("content"):
        og_desc = tag["content"].strip()

    tag = soup.find("meta", property="og:site_name")
    if tag and tag.get("content"):
        og_site = tag["content"].strip()

    page_title = soup.title.string.strip() if soup.title and soup.title.string else ""

    # Heuristic parsing for role and company from title (e.g. "Software Engineer at Google" or "Google - Software Engineer")
    title_to_parse = og_title or page_title
    role_title = ""
    company = og_site

    if title_to_parse:
        # Common title patterns: "Role at Company", "Company - Role", "Role | Company"
        match = re.search(r"^(.*?)\s+(?:at|@)\s+(.*?)(?:\s*[-|•·].*)?$", title_to_parse, re.IGNORECASE)
        if match:
            role_title = match.group(1).strip()
            if not company:
                company = match.group(2).strip()
        else:
            parts = re.split(r"\s*[-|•·]\s*", title_to_parse)
            if len(parts) >= 2:
                # E.g. "Google - Senior AI Engineer" or "Senior AI Engineer - Google"
                role_title = parts[0].strip()
                if not company:
                    company = parts[1].strip()
            else:
                role_title = title_to_parse

    # 2. Extract main job content
    # Target specific known job boards containers if present
    content_container = (
        soup.find("div", class_=re.compile(r"description|job-details|job-description|posting-requirements", re.I))
        or soup.find("section", class_=re.compile(r"description|job-details|job-description", re.I))
        or soup.find("main")
        or soup.find("article")
        or soup.body
    )

    if content_container:
        for tag in content_container(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        description = content_container.get_text(separator="\n").strip()
        description = "\n".join([line.strip() for line in description.splitlines() if line.strip()])
    else:
        description = clean_text(html_content)

    # Fallback to meta description if content is too short
    if len(description) < 100 and og_desc:
        description = f"{og_title}\n\n{og_desc}"

    # Trim to reasonable context length for LLM (e.g., 10,000 chars)
    if len(description) > 10000:
        description = description[:10000] + "\n...[truncated]"

    return ScrapedJob(
        url=url,
        company=company or "Unknown Company",
        role_title=role_title or "Job Position",
        description=description,
        success=bool(description and len(description) >= 50),
        message="Successfully extracted job posting" if len(description) >= 50 else "Limited text extracted. You can paste the description manually below."
    )


def fetch_job_from_url(url: str) -> ScrapedJob:
    """
    Fetches job details from a given URL via HTTP.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return parse_job_html(url, resp.text)
    except Exception as exc:
        logger.warning("Scraping failed for %s: %s", url, exc)
        return ScrapedJob(
            url=url,
            company="",
            role_title="",
            description="",
            success=False,
            message=f"Could not automatically fetch page ({type(exc).__name__}). Please paste the job description text manually below."
        )


def fetch_url_content(url: str) -> str:
    """
    Convenience function that fetches URL and returns formatted text content.
    """
    job = fetch_job_from_url(url)
    if job.description:
        prefix = f"🏢 Company: {job.company}\n💼 Role: {job.role_title}\n\n" if job.company else ""
        return f"{prefix}{job.description}".strip()
    return ""

