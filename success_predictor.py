import math
from typing import Dict, List


try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    import numpy as np

    SKLEARN_READY = True
except Exception:
    SKLEARN_READY = False


_MODEL = None


def _skill_match(user_skills: List[str], required_skills: List[str]) -> float:
    user = {str(s).strip().lower() for s in user_skills if str(s).strip()}
    req = {str(s).strip().lower() for s in required_skills if str(s).strip()}
    if not req:
        return 0.0
    return len(user & req) / len(req)


def _experience_score(experience_years: float) -> float:
    if experience_years <= 0:
        return 0.2
    if experience_years <= 1:
        return 0.55
    if experience_years <= 2:
        return 0.75
    return 0.9


def _build_training_data():
    # Synthetic but structured training set for internship selection probability.
    rows = []
    labels = []

    for skill_match in [0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0]:
        for resume_score in [40, 55, 65, 75, 85, 95]:
            for projects in [0, 1, 2, 3, 4]:
                for exp in [0.2, 0.5, 0.75, 0.9]:
                    score = (0.45 * skill_match) + (0.3 * (resume_score / 100.0)) + (0.15 * min(1.0, projects / 3.0)) + (0.1 * exp)
                    rows.append([skill_match, resume_score / 100.0, min(1.0, projects / 5.0), exp])
                    labels.append(1 if score >= 0.58 else 0)

    return rows, labels


def _fit_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    if not SKLEARN_READY:
        return None

    X, y = _build_training_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LogisticRegression(random_state=42, max_iter=500)
    model.fit(X_train, y_train)

    _ = accuracy_score(y_test, model.predict(X_test))
    _MODEL = model
    return _MODEL


def predict_success_probability(payload: Dict[str, object]) -> Dict[str, object]:
    user_skills = payload.get("user_skills", []) or []
    required_skills = payload.get("required_skills", []) or []
    resume_score = float(payload.get("resume_score", 0.0) or 0.0)
    num_projects = int(payload.get("num_projects", 0) or 0)
    experience_years = float(payload.get("experience_years", 0.0) or 0.0)

    skill_match = _skill_match(user_skills, required_skills)
    exp_feature = _experience_score(experience_years)

    if SKLEARN_READY and _fit_model() is not None:
        model = _fit_model()
        features = [[skill_match, resume_score / 100.0, min(1.0, num_projects / 5.0), exp_feature]]
        probability = float(model.predict_proba(features)[0][1])
    else:
        # Heuristic sigmoid fallback if sklearn is unavailable.
        linear = (2.4 * skill_match) + (1.6 * (resume_score / 100.0)) + (0.9 * min(1.0, num_projects / 4.0)) + (0.7 * exp_feature) - 2.2
        probability = 1 / (1 + math.exp(-linear))

    return {
        "internship": payload.get("internship", "Internship"),
        "success_probability": round(max(0.01, min(0.99, probability)), 3),
        "feature_breakdown": {
            "skill_match_percentage": round(skill_match * 100, 2),
            "resume_score": round(resume_score, 2),
            "num_projects": num_projects,
            "experience_feature": round(exp_feature, 2),
        },
    }
