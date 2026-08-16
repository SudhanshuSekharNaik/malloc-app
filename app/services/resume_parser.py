"""
Resume Parser Service.

Extracts structured and plain text from PDF and TXT resume files.
"""
import io
import logging
from pypdf import PdfReader

logger = logging.getLogger("memora.resume_parser")


class ResumeParseError(RuntimeError):
    """Raised when parsing resume file fails."""


def parse_pdf_resume(file_bytes: bytes) -> str:
    """
    Extracts text from PDF bytes using pypdf.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(text.strip())
        full_text = "\n\n".join(pages_text).strip()
        if not full_text:
            raise ResumeParseError("No readable text found in PDF. It may be a scanned image.")
        return full_text
    except Exception as exc:
        logger.exception("PDF parsing error")
        raise ResumeParseError(f"Failed to parse PDF resume: {exc}") from exc


def extract_resume_text(file_bytes: bytes, filename: str) -> str:
    """
    Dispatcher to extract text based on filename extension.
    """
    filename_lower = filename.lower()
    if filename_lower.endswith(".pdf"):
        return parse_pdf_resume(file_bytes)
    elif filename_lower.endswith((".txt", ".md", ".rtf")):
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="ignore")
    else:
        # Try UTF-8 first, fallback to PDF parser
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return parse_pdf_resume(file_bytes)
