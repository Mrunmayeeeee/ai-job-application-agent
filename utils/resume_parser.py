"""
Resume Parser – extracts text from PDF and DOCX files.
Supports structured extraction of skills, experience, and education.
"""

import os
import re
from PyPDF2 import PdfReader
from docx import Document


def extract_text_from_pdf(filepath: str) -> str:
    """Extract all text content from a PDF file."""
    reader = PdfReader(filepath)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def extract_text_from_docx(filepath: str) -> str:
    """Extract all text content from a DOCX file."""
    doc = Document(filepath)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def parse_resume(filepath: str) -> dict:
    """
    Parse a resume file and return structured data.

    Returns:
        dict with keys: raw_text, skills, file_name, file_type
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        raw_text = extract_text_from_pdf(filepath)
    elif ext in (".docx", ".doc"):
        raw_text = extract_text_from_docx(filepath)
    elif ext == ".txt":
        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    # Basic skill extraction using common patterns
    skills = extract_skills(raw_text)

    return {
        "raw_text": raw_text,
        "skills": skills,
        "file_name": os.path.basename(filepath),
        "file_type": ext,
    }


def extract_skills(text: str) -> list[str]:
    """
    Extract skills from resume text using keyword matching.
    This is a heuristic; the LLM does deeper analysis.
    """
    # Common tech skills to look for
    skill_patterns = [
        # Programming Languages
        r"\bPython\b", r"\bJavaScript\b", r"\bTypeScript\b", r"\bJava\b",
        r"\bC\+\+\b", r"\bC#\b", r"\bRuby\b", r"\bGo\b", r"\bRust\b",
        r"\bSwift\b", r"\bKotlin\b", r"\bPHP\b", r"\bScala\b", r"\bR\b",
        # Web Frameworks
        r"\bReact\b", r"\bAngular\b", r"\bVue\.?js\b", r"\bNode\.?js\b",
        r"\bDjango\b", r"\bFlask\b", r"\bSpring\b", r"\bExpress\b",
        r"\bNext\.?js\b", r"\bFastAPI\b",
        # Data / ML
        r"\bTensorFlow\b", r"\bPyTorch\b", r"\bScikit.?learn\b",
        r"\bPandas\b", r"\bNumPy\b", r"\bKeras\b", r"\bOpenCV\b",
        r"\bLangChain\b", r"\bLLM\b",
        # Cloud & DevOps
        r"\bAWS\b", r"\bAzure\b", r"\bGCP\b", r"\bDocker\b",
        r"\bKubernetes\b", r"\bCI/CD\b", r"\bTerraform\b", r"\bGit\b",
        # Databases
        r"\bSQL\b", r"\bPostgreSQL\b", r"\bMongoDB\b", r"\bRedis\b",
        r"\bMySQL\b", r"\bFirebase\b",
        # Soft Skills
        r"\bLeadership\b", r"\bCommunication\b", r"\bTeamwork\b",
        r"\bProblem.?solving\b", r"\bAgile\b", r"\bScrum\b",
    ]

    found = set()
    for pattern in skill_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            # Clean up the pattern to get the skill name
            skill = pattern.replace(r"\b", "").replace("\\", "").replace(".?", " ")
            # Capitalize properly
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                found.add(match.group())

    return sorted(found)
