import os
import re
from typing import Dict, List
from urllib.parse import quote_plus

import requests

from resume_parser import extract_skills


DEFAULT_LIVE_JOBS_API = "https://remotive.com/api/remote-jobs"
SECONDARY_LIVE_JOBS_API = "https://www.arbeitnow.com/api/job-board-api"
THIRD_LIVE_JOBS_API = "https://www.themuse.com/api/public/jobs"
ENTRY_LEVEL_TERMS = ("intern", "internship", "trainee", "apprentice", "graduate", "junior")


def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_jobs(jobs: List[Dict[str, object]], limit: int) -> List[Dict[str, object]]:
    normalized: List[Dict[str, object]] = []
    seen = set()

    for job in jobs:
        title = str(job.get("title", "")).strip()
        if not title:
            continue

        # Wider entry-level filter to avoid empty results.
        title_lower = title.lower()
        if not any(term in title_lower for term in ENTRY_LEVEL_TERMS):
            continue

        description = _clean_html(str(job.get("description", "")))
        company = str(job.get("company_name", "Unknown Company")).strip()
        location = str(job.get("candidate_required_location", "Remote")).strip() or "Remote"
        apply_link = str(job.get("url", "")).strip()

        unique_key = (str(job.get("id", "")), title.lower(), company.lower())
        if unique_key in seen:
            continue
        seen.add(unique_key)

        skills = extract_skills(f"{title} {description}")

        normalized.append(
            {
                "source": "live-api",
                "external_id": str(job.get("id", "")),
                "company": company,
                "role": title,
                "required_skills": skills,
                "location": location,
                "description": description or "No description provided.",
                "apply_link": apply_link,
                "experience_level": "Beginner",
                "salary": str(job.get("salary", "")).strip(),
                "company_website": str(job.get("company_website", "")).strip(),
            }
        )

        if len(normalized) >= max(1, limit):
            break

    return normalized


def _normalize_arbeitnow_jobs(jobs: List[Dict[str, object]], limit: int) -> List[Dict[str, object]]:
    normalized: List[Dict[str, object]] = []
    seen = set()

    for job in jobs:
        title = str(job.get("title", "")).strip()
        if not title:
            continue

        title_lower = title.lower()
        if not any(term in title_lower for term in ENTRY_LEVEL_TERMS):
            continue

        description = _clean_html(str(job.get("description", "")))
        company = str(job.get("company_name", "Unknown Company")).strip()
        location = "Remote" if bool(job.get("remote", False)) else "Global"
        apply_link = str(job.get("url", "")).strip()

        unique_key = (str(job.get("slug", "")), title.lower(), company.lower())
        if unique_key in seen:
            continue
        seen.add(unique_key)

        skills = extract_skills(f"{title} {description} {' '.join(job.get('tags', []))}")

        normalized.append(
            {
                "source": "live-api",
                "external_id": str(job.get("slug", "")) or apply_link,
                "company": company,
                "role": title,
                "required_skills": skills,
                "location": location,
                "description": description or "No description provided.",
                "apply_link": apply_link,
                "experience_level": "Beginner",
                "salary": "",
                "company_website": "",
            }
        )

        if len(normalized) >= max(1, limit):
            break

    return normalized


def _normalize_muse_jobs(jobs: List[Dict[str, object]], limit: int) -> List[Dict[str, object]]:
    normalized: List[Dict[str, object]] = []
    seen = set()

    for job in jobs:
        title = str(job.get("name", "")).strip()
        if not title:
            continue

        title_lower = title.lower()
        if not any(term in title_lower for term in ENTRY_LEVEL_TERMS):
            continue

        company_info = job.get("company", {}) or {}
        company = str(company_info.get("name", "Unknown Company")).strip()

        locations = job.get("locations", []) or []
        location = str(locations[0].get("name", "Remote")).strip() if locations else "Remote"

        refs = job.get("refs", {}) or {}
        apply_link = str(refs.get("landing_page", "")).strip()
        description = _clean_html(str(job.get("contents", "")))

        categories = job.get("categories", []) or []
        tags = [str(cat.get("name", "")) for cat in categories if isinstance(cat, dict)]
        skills = extract_skills(f"{title} {description} {' '.join(tags)}")

        unique_key = (str(job.get("id", "")), title.lower(), company.lower())
        if unique_key in seen:
            continue
        seen.add(unique_key)

        normalized.append(
            {
                "source": "live-api",
                "external_id": str(job.get("id", "")) or apply_link,
                "company": company,
                "role": title,
                "required_skills": skills,
                "location": location,
                "description": description or "No description provided.",
                "apply_link": apply_link,
                "experience_level": "Beginner",
                "salary": "",
                "company_website": "",
            }
        )

        if len(normalized) >= max(1, limit):
            break

    return normalized


def _fallback_cards(search_query: str, needed: int) -> List[Dict[str, object]]:
    query = (search_query or "internship").strip()
    role_seed = [
        "Machine Learning Intern",
        "Data Science Intern",
        "Python Developer Intern",
        "AI Engineer Intern",
        "NLP Intern",
        "Backend Intern",
    ]

    cards: List[Dict[str, object]] = []
    for idx in range(max(0, needed)):
        role = role_seed[idx % len(role_seed)]
        company = f"LiveSource Partner {idx + 1}"
        apply = (
            "https://www.linkedin.com/jobs/search/?"
            f"keywords={quote_plus(role + ' ' + query)}&location={quote_plus('India')}"
        )

        cards.append(
            {
                "source": "live-fallback",
                "external_id": f"fallback-{idx + 1}-{quote_plus(query)}",
                "company": company,
                "role": role,
                "required_skills": extract_skills(role + " " + query),
                "location": "India / Remote",
                "description": "Fallback live listing generated from current search intent.",
                "apply_link": apply,
                "experience_level": "Beginner",
                "salary": "",
                "company_website": "",
            }
        )

    return cards


def fetch_live_internships(search_query: str, limit: int = 25) -> List[Dict[str, object]]:
    api_url = os.getenv("LIVE_JOBS_API_URL", DEFAULT_LIVE_JOBS_API)
    second_api_url = os.getenv("SECONDARY_LIVE_JOBS_API_URL", SECONDARY_LIVE_JOBS_API)
    third_api_url = os.getenv("THIRD_LIVE_JOBS_API_URL", THIRD_LIVE_JOBS_API)
    min_live_results = int(os.getenv("MIN_LIVE_RESULTS", "10"))
    queries = [
        (search_query or "").strip(),
        "machine learning intern",
        "data science intern",
        "python intern",
        "software engineer intern",
        "intern",
    ]

    seen_queries = []
    for q in queries:
        if q and q not in seen_queries:
            seen_queries.append(q)

    collected: List[Dict[str, object]] = []
    for query in seen_queries:
        try:
            response = requests.get(api_url, params={"search": query}, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            continue

        jobs = payload.get("jobs", [])
        normalized = _normalize_jobs(jobs, limit=limit)
        collected.extend(normalized)

        if len(collected) >= limit:
            break

    # Secondary source pass (broad feed) if primary results are low.
    if len(collected) < max(5, limit // 2):
        try:
            second_response = requests.get(second_api_url, timeout=15)
            second_response.raise_for_status()
            second_payload = second_response.json()
            second_jobs = second_payload.get("data", [])
            second_normalized = _normalize_arbeitnow_jobs(second_jobs, limit=limit)
            collected.extend(second_normalized)
        except Exception:
            pass

    # Third source pass (The Muse) for additional coverage.
    if len(collected) < max(7, limit // 2):
        try:
            third_response = requests.get(third_api_url, params={"page": 1}, timeout=15)
            third_response.raise_for_status()
            third_payload = third_response.json()
            third_jobs = third_payload.get("results", [])
            third_normalized = _normalize_muse_jobs(third_jobs, limit=limit)
            collected.extend(third_normalized)
        except Exception:
            pass

    # Final dedupe across multiple query passes.
    deduped = []
    seen_ids = set()
    for item in collected:
        key = (item.get("external_id"), item.get("role"), item.get("company"))
        if key in seen_ids:
            continue
        seen_ids.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break

    # Guarantee minimum display count by adding robust fallback links.
    target_min = min(max(1, min_live_results), limit)
    if len(deduped) < target_min:
        deduped.extend(_fallback_cards(search_query, target_min - len(deduped)))

    return deduped
