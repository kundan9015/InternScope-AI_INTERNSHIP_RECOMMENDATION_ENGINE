import re
from typing import Dict, List
from urllib.parse import urlparse


KNOWN_FREE_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "proton.me"}
SUSPICIOUS_TERMS = ["instant join", "guaranteed", "quick money", "earn per day", "no interview"]


def detect_fake_internship(internship: Dict[str, object]) -> Dict[str, object]:
    risk_score = 0
    reasons: List[str] = []

    website = str(internship.get("company_website", "") or "").strip()
    if not website:
        risk_score += 25
        reasons.append("Company website is missing")
    else:
        parsed = urlparse(website if website.startswith("http") else f"https://{website}")
        domain = parsed.netloc.lower().replace("www.", "")
        if domain in KNOWN_FREE_DOMAINS:
            risk_score += 30
            reasons.append("Company uses free email/web domain")

    description = str(internship.get("description", "") or "").lower()
    if any(term in description for term in SUSPICIOUS_TERMS):
        risk_score += 25
        reasons.append("Suspicious wording in internship description")

    salary = str(internship.get("salary", "") or "").lower()
    salary_numbers = re.findall(r"\d+", salary)
    if salary_numbers:
        max_number = max(int(v) for v in salary_numbers)
        if max_number >= 200000:
            risk_score += 35
            reasons.append("Salary appears unrealistic for an internship")

    if not internship.get("apply_link"):
        risk_score += 20
        reasons.append("Application link is missing")

    if not internship.get("company_name"):
        risk_score += 20
        reasons.append("Company details are incomplete")

    risk_score = min(100, risk_score)
    label = "suspicious" if risk_score >= 50 else "low-risk"

    return {
        "risk_score": risk_score,
        "label": label,
        "reasons": reasons,
    }
