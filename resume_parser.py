import re
import importlib
from pathlib import Path
from typing import Dict, List

SKILL_LEXICON = {
    "python",
    "java",
    "c++",
    "sql",
    "javascript",
    "typescript",
    "html",
    "css",
    "flask",
    "django",
    "fastapi",
    "react",
    "node.js",
    "machine learning",
    "deep learning",
    "nlp",
    "tensorflow",
    "pytorch",
    "scikit-learn",
    "pandas",
    "numpy",
    "power bi",
    "tableau",
    "git",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "mongodb",
}


SECTION_HEADERS = {
    "education": ["education", "academic background", "qualifications"],
    "projects": ["projects", "academic projects", "personal projects"],
    "experience": ["experience", "work experience", "internship experience"],
}


def extract_text_from_pdf(file_path: str) -> str:
    text_chunks: List[str] = []
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {file_path}")

    pdfplumber = importlib.import_module("pdfplumber")

    try:
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text_chunks.append(page.extract_text() or "")
    except Exception:
        # Fallback parser in case pdfplumber fails on scanned/odd PDFs.
        PdfReader = getattr(importlib.import_module("PyPDF2"), "PdfReader")
        reader = PdfReader(str(path))
        for page in reader.pages:
            text_chunks.append(page.extract_text() or "")

    return "\n".join(text_chunks).strip()


def _extract_email(text: str) -> str:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else "Not found"


def _extract_name(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:6]:
        if "@" in line or re.search(r"\d", line):
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(w.replace(".", "").isalpha() for w in words):
            return line
    return "Candidate"


def _section_blocks(text: str) -> Dict[str, str]:
    normalized_lines = [line.strip() for line in text.splitlines()]
    sections = {"education": [], "projects": [], "experience": []}
    current = None

    for line in normalized_lines:
        if not line:
            continue

        lower_line = line.lower().strip(":")
        switched = False
        for key, aliases in SECTION_HEADERS.items():
            if lower_line in aliases:
                current = key
                switched = True
                break

        if switched:
            continue

        if current:
            sections[current].append(line)

    return {k: "\n".join(v).strip() if v else "Not mentioned" for k, v in sections.items()}


def extract_skills(text: str) -> List[str]:
    lowered = text.lower()
    try:
        wordpunct_tokenize = getattr(importlib.import_module("nltk.tokenize"), "wordpunct_tokenize")
        tokens = set(wordpunct_tokenize(lowered))
    except Exception:
        tokens = set(re.findall(r"[a-zA-Z0-9.+#-]+", lowered))

    found = set()
    for skill in SKILL_LEXICON:
        if " " in skill:
            if skill in lowered:
                found.add(skill)
        else:
            if skill in tokens:
                found.add(skill)

    return sorted(found)


def extract_experience_years(text: str) -> float:
    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s+years?",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return float(match.group(1))
    return 0.0


def _normalize_url(url: str) -> str:
    cleaned = (url or "").strip().rstrip(".,);]\"'")
    if not cleaned:
        return ""
    if cleaned.startswith("www."):
        return f"https://{cleaned}"
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    if "linkedin.com" in cleaned.lower() or "github.com" in cleaned.lower():
        return f"https://{cleaned}"
    return cleaned


def extract_links(text: str) -> Dict[str, object]:
    text = text or ""
    url_pattern = r"((?:https?://|www\.)[^\s<>\"']+|(?:linkedin\.com|github\.com)/[^\s<>\"']+)"
    raw_urls = re.findall(url_pattern, text, flags=re.IGNORECASE)

    normalized_urls = []
    seen = set()
    for url in raw_urls:
        normalized = _normalize_url(url)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized_urls.append(normalized)

    linkedin = ""
    github = ""
    portfolio = ""

    for url in normalized_urls:
        lower_url = url.lower()
        if not linkedin and "linkedin.com/" in lower_url:
            linkedin = url
            continue
        if not github and "github.com/" in lower_url:
            github = url
            continue
        if not portfolio and ("linkedin.com/" not in lower_url and "github.com/" not in lower_url):
            portfolio = url

    return {
        "linkedin": linkedin,
        "github": github,
        "portfolio": portfolio,
        "all": normalized_urls,
    }


def parse_resume(text: str) -> Dict[str, object]:
    sections = _section_blocks(text)
    return {
        "name": _extract_name(text),
        "email": _extract_email(text),
        "links": extract_links(text),
        "skills": extract_skills(text),
        "education": sections["education"],
        "projects": sections["projects"],
        "experience": sections["experience"],
        "experience_years": extract_experience_years(text),
        "raw_text": text,
    }


def parse_resume_pdf(file_path: str) -> Dict[str, object]:
    text = extract_text_from_pdf(file_path)
    if not text:
        raise ValueError("Could not extract text from PDF resume.")
    return parse_resume(text)
