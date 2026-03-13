import importlib
import re
from typing import Dict, List


FRAMEWORK_KEYWORDS = {"tensorflow", "pytorch", "keras", "jax"}
CERT_KEYWORDS = {"certified", "certificate", "coursera", "udemy", "edx", "aws certified", "google"}


def _safe_spacy_nlp():
    try:
        spacy = importlib.import_module("spacy")
    except Exception:
        return None

    for model_name in ["en_core_web_sm", "en_core_web_md"]:
        try:
            return spacy.load(model_name)
        except Exception:
            continue

    try:
        return spacy.blank("en")
    except Exception:
        return None


def _find_links(text: str) -> List[str]:
    pattern = r"https?://[^\s]+|www\.[^\s]+|github\.com/[^\s]+"
    return re.findall(pattern, text, flags=re.IGNORECASE)


def _extract_projects(text: str) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    project_lines = []
    in_project_section = False

    for line in lines:
        low = line.lower().strip(":")
        if low in {"projects", "project", "academic projects", "personal projects"}:
            in_project_section = True
            continue

        if in_project_section and low in {"experience", "education", "skills", "certifications", "summary"}:
            break

        if in_project_section:
            project_lines.append(line)

    return project_lines


def analyze_resume_text(resume_text: str) -> Dict[str, object]:
    text = str(resume_text or "")
    lowered = text.lower()

    nlp = _safe_spacy_nlp()
    technologies = set()

    if nlp is not None:
        doc = nlp(text)
        for token in doc:
            tok = token.text.strip().lower()
            if tok in FRAMEWORK_KEYWORDS or tok in {"python", "sql", "flask", "django", "fastapi", "pandas", "numpy"}:
                technologies.add(tok)
    else:
        for kw in FRAMEWORK_KEYWORDS | {"python", "sql", "flask", "django", "fastapi", "pandas", "numpy"}:
            if kw in lowered:
                technologies.add(kw)

    links = _find_links(text)
    github_links = [link for link in links if "github.com" in link.lower()]

    projects = _extract_projects(text)
    certifications = [kw for kw in CERT_KEYWORDS if kw in lowered]

    weak_points = []
    suggestions = []

    if not github_links:
        weak_points.append("No GitHub profile mentioned")
        suggestions.append("Add GitHub project links and portfolio repositories.")

    if len(projects) < 2:
        weak_points.append("Less than two projects listed")
        suggestions.append("Build and describe at least 2 practical machine learning or backend projects.")

    if not any(framework in technologies for framework in FRAMEWORK_KEYWORDS):
        weak_points.append("No deep learning frameworks mentioned")
        suggestions.append("Mention hands-on experience with TensorFlow or PyTorch.")

    if not certifications:
        weak_points.append("No relevant certifications found")
        suggestions.append("Consider adding an ML/AI certification (Coursera, AWS, Google, etc.).")

    if not weak_points:
        suggestions.append("Resume is well-structured. Tailor bullets per internship role for higher impact.")

    return {
        "weak_points": weak_points,
        "suggestions": suggestions,
        "detected": {
            "technologies": sorted(technologies),
            "projects": projects,
            "certifications": certifications,
            "github_links": github_links,
            "all_links": links,
        },
    }
