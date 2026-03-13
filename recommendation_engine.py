import math
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from fake_internship_detector import detect_fake_internship

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9+#.-]+", text.lower())


def _cosine_from_counters(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    shared = set(a.keys()) & set(b.keys())
    dot = sum(a[token] * b[token] for token in shared)
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _tfidf_similarities(corpus: List[str]) -> List[float]:
    if SKLEARN_AVAILABLE:
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform(corpus)
        return cosine_similarity(matrix[0:1], matrix[1:]).flatten().tolist()

    tokenized = [_tokenize(doc) for doc in corpus]
    total_docs = len(tokenized)

    df_counter = Counter()
    for tokens in tokenized:
        df_counter.update(set(tokens))

    tfidf_docs: List[Counter] = []
    for tokens in tokenized:
        tf_counter = Counter(tokens)
        token_count = len(tokens) or 1
        weighted = Counter()
        for token, freq in tf_counter.items():
            tf = freq / token_count
            idf = math.log((1 + total_docs) / (1 + df_counter[token])) + 1
            weighted[token] = tf * idf
        tfidf_docs.append(weighted)

    resume_vec = tfidf_docs[0]
    return [_cosine_from_counters(resume_vec, doc_vec) for doc_vec in tfidf_docs[1:]]


def _internship_text(item: Dict[str, object]) -> str:
    skills = " ".join(item.get("required_skills", []))
    return f"{item.get('role', '')} {item.get('description', '')} {skills}".strip().lower()


def _skill_overlap(resume_skills: List[str], required_skills: List[str]) -> float:
    if not required_skills:
        return 0.0
    overlap = len(set(resume_skills) & set(required_skills))
    return (overlap / len(set(required_skills))) * 100.0


def recommend_internships(
    parsed_resume: Dict[str, object],
    internships: List[Dict[str, object]],
    location_preference: Optional[str] = None,
    top_k: int = 8,
) -> Tuple[List[Dict[str, object]], List[str]]:
    if not internships:
        return [], []

    resume_skills = parsed_resume.get("skills", [])
    resume_text = " ".join(resume_skills).lower()

    corpus = [resume_text] + [_internship_text(item) for item in internships]
    similarities = _tfidf_similarities(corpus)

    ranked = []
    all_required = set()
    for idx, item in enumerate(internships):
        required = item.get("required_skills", [])
        all_required.update(required)
        matched_skills = sorted(list(set(resume_skills) & set(required)))
        missing_required = sorted(list(set(required) - set(resume_skills)))

        semantic_match = float(similarities[idx] * 100)
        skill_match = _skill_overlap(resume_skills, required)

        location_bonus = 0.0
        if location_preference:
            if location_preference.lower() in str(item.get("location", "")).lower():
                location_bonus = 10.0

        experience_level = str(item.get("experience_level", "Beginner")).lower()
        exp_years = float(parsed_resume.get("experience_years", 0.0) or 0.0)
        experience_bonus = 8.0 if experience_level == "beginner" and exp_years <= 1.5 else 0.0

        ranking_score = (0.55 * semantic_match) + (0.3 * skill_match) + location_bonus + experience_bonus

        fraud_signal = detect_fake_internship(item)
        adjusted_score = max(0.0, ranking_score - (fraud_signal["risk_score"] * 0.15))

        ranked_item = {
            **item,
            "match_score": round(skill_match, 2),
            "semantic_similarity": round(semantic_match, 2),
            "ranking_score": round(min(100.0, adjusted_score), 2),
            "matched_skills": matched_skills,
            "missing_required_skills": missing_required,
            "fake_detection": fraud_signal,
        }
        ranked.append(ranked_item)

    ranked.sort(key=lambda x: x["ranking_score"], reverse=True)

    missing_skills = sorted(list(all_required - set(resume_skills)))
    return ranked[:top_k], missing_skills


def personalized_feed(
    user_profile: Dict[str, object],
    internships: List[Dict[str, object]],
    top_k: int = 10,
) -> List[Dict[str, object]]:
    if not internships:
        return []

    skills = user_profile.get("skills", []) or []
    interests = user_profile.get("interests", []) or []
    viewed = set(user_profile.get("viewed_ids", []) or [])
    applied = set(user_profile.get("applied_ids", []) or [])

    user_text = " ".join([*map(str, skills), *map(str, interests)]).lower().strip()
    if not user_text:
        user_text = "internship python machine learning data"

    corpus = [user_text] + [_internship_text(item) for item in internships]
    similarities = _tfidf_similarities(corpus)

    ranked = []
    for idx, internship in enumerate(internships):
        base_score = float(similarities[idx])

        # Behavioral boosts for personalization.
        behavior_boost = 0.0
        internship_id = str(internship.get("id", ""))
        if internship_id in viewed:
            behavior_boost += 0.05
        if internship_id in applied:
            behavior_boost -= 0.1

        skill_score = _skill_overlap(skills, internship.get("required_skills", [])) / 100.0
        final_score = max(0.0, min(1.0, 0.65 * base_score + 0.3 * skill_score + behavior_boost))

        ranked.append(
            {
                **internship,
                "match_score": round(final_score, 3),
            }
        )

    ranked.sort(key=lambda item: item["match_score"], reverse=True)
    return ranked[: max(1, top_k)]
