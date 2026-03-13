from typing import Dict, List


BENCHMARK_SKILLS = [
    "python",
    "sql",
    "machine learning",
    "deep learning",
    "nlp",
    "pandas",
    "numpy",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "git",
    "flask",
]


def _skills_score(resume_skills: List[str], target_skills: List[str]) -> float:
    if not target_skills:
        return 0.0
    overlap = len(set(resume_skills) & set(target_skills))
    return (overlap / len(set(target_skills))) * 50.0


def _projects_score(project_text: str) -> float:
    if not project_text or project_text == "Not mentioned":
        return 0.0
    lines = [line for line in project_text.splitlines() if line.strip()]
    count = len(lines)
    return min(20.0, 6.0 + count * 3.5)


def _education_score(education_text: str) -> float:
    if not education_text or education_text == "Not mentioned":
        return 2.0

    lowered = education_text.lower()
    if any(token in lowered for token in ["b.tech", "b.e", "bachelor", "master", "m.tech", "phd"]):
        return 15.0
    return 8.0


def _experience_score(experience_text: str, years: float) -> float:
    if experience_text == "Not mentioned" and years == 0:
        return 4.0
    return min(15.0, 5.0 + years * 4.0)


def calculate_resume_score(parsed_resume: Dict[str, object], internships: List[Dict[str, object]]) -> Dict[str, object]:
    combined_required = []
    for item in internships:
        combined_required.extend(item.get("required_skills", []))

    # Keep score stable across repeated uploads of the same resume.
    target_skills = sorted(set(BENCHMARK_SKILLS + combined_required)) if combined_required else BENCHMARK_SKILLS

    skills_score = _skills_score(parsed_resume.get("skills", []), target_skills)
    projects_score = _projects_score(parsed_resume.get("projects", ""))
    education_score = _education_score(parsed_resume.get("education", ""))
    experience_score = _experience_score(
        parsed_resume.get("experience", ""),
        float(parsed_resume.get("experience_years", 0.0) or 0.0),
    )

    total = round(skills_score + projects_score + education_score + experience_score, 2)

    return {
        "score": min(100.0, total),
        "breakdown": {
            "skills_match": round(skills_score, 2),
            "projects": round(projects_score, 2),
            "education": round(education_score, 2),
            "experience": round(experience_score, 2),
        },
    }
