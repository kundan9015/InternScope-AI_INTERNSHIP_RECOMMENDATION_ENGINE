from typing import Dict, List


ROLE_SKILL_WEIGHTS = {
    "AI Engineer": {
        "machine learning": 1.4,
        "deep learning": 1.5,
        "tensorflow": 1.5,
        "pytorch": 1.5,
        "nlp": 1.2,
        "computer vision": 1.2,
        "python": 1.1,
    },
    "Machine Learning Engineer": {
        "machine learning": 1.5,
        "scikit-learn": 1.4,
        "python": 1.2,
        "mlops": 1.2,
        "pandas": 1.0,
        "numpy": 1.0,
        "sql": 0.9,
    },
    "Data Scientist": {
        "python": 1.2,
        "sql": 1.4,
        "statistics": 1.3,
        "pandas": 1.3,
        "numpy": 1.2,
        "tableau": 0.9,
        "power bi": 0.9,
        "machine learning": 1.1,
    },
    "Data Analyst": {
        "sql": 1.5,
        "excel": 1.2,
        "power bi": 1.3,
        "tableau": 1.3,
        "python": 0.8,
        "pandas": 0.9,
    },
    "Backend Developer": {
        "python": 1.3,
        "flask": 1.2,
        "django": 1.1,
        "fastapi": 1.2,
        "sql": 1.1,
        "mongodb": 1.0,
        "docker": 1.0,
        "git": 0.9,
    },
}


def _normalize_skill(skill: str) -> str:
    return str(skill or "").strip().lower()


def _project_bonus(projects: List[str], role: str) -> float:
    role_keywords = {
        "AI Engineer": ["ai", "deep", "vision", "nlp"],
        "Machine Learning Engineer": ["model", "ml", "prediction", "classification"],
        "Data Scientist": ["analysis", "forecast", "dashboard", "insight"],
        "Data Analyst": ["dashboard", "report", "analytics", "excel"],
        "Backend Developer": ["api", "backend", "server", "database"],
    }

    bonus = 0.0
    terms = role_keywords.get(role, [])
    for project in projects:
        lowered = str(project or "").lower()
        if any(term in lowered for term in terms):
            bonus += 0.2
    return min(1.0, bonus)


def predict_career_paths(parsed_data: Dict[str, object], top_k: int = 3) -> Dict[str, List[Dict[str, object]]]:
    skills = [_normalize_skill(skill) for skill in parsed_data.get("skills", [])]
    skill_set = set(skill for skill in skills if skill)

    projects_raw = parsed_data.get("projects", "")
    projects = [line.strip() for line in str(projects_raw).splitlines() if line.strip()]

    experience_years = float(parsed_data.get("experience_years", 0.0) or 0.0)
    education_text = str(parsed_data.get("education", "") or "").lower()

    raw_scores = {}
    for role, weights in ROLE_SKILL_WEIGHTS.items():
        score = 0.0
        for skill, weight in weights.items():
            if skill in skill_set:
                score += weight

        score += _project_bonus(projects, role)

        if experience_years >= 1:
            score += 0.35
        if any(token in education_text for token in ["b.tech", "bachelor", "master", "m.tech", "computer", "data"]):
            score += 0.3

        raw_scores[role] = score

    total = sum(max(0.001, value) for value in raw_scores.values())
    ranked = sorted(raw_scores.items(), key=lambda item: item[1], reverse=True)

    career_paths = [
        {"role": role, "score": round(max(0.01, value) / total, 3)}
        for role, value in ranked[: max(1, top_k)]
    ]

    return {"career_paths": career_paths}
