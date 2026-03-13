import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from urllib.parse import quote_plus, urlparse

from bson import ObjectId
from flask import Flask, jsonify, redirect, render_template, request
import requests
from werkzeug.utils import secure_filename

from database import (
    get_internships,
    get_user_activity_summary,
    insert_user,
    internships_collection,
    log_user_activity,
    recommendations_collection,
    save_recommendation,
    upsert_internship,
    users_collection,
)
from recommendation_engine import personalized_feed, recommend_internships
from resume_parser import extract_text_from_pdf, parse_resume_pdf
from scoring_system import calculate_resume_score
from utils.live_internship_service import fetch_live_internships
from career_predictor import predict_career_paths
from success_predictor import predict_success_probability
from resume_analyzer import analyze_resume_text


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {"pdf"}


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

    ensure_live_only_dataset()
    register_routes(app)
    return app


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_live_only_dataset() -> None:
    # Remove legacy sample records so users only see live internships.
    internships_collection.delete_many({"source": {"$ne": "live-api"}})


def internship_to_dict(internship: Dict[str, object]) -> Dict[str, object]:
    raw_apply_link = str(internship.get("apply_link", "") or "").strip()
    apply_link = raw_apply_link
    if apply_link and not apply_link.startswith(("http://", "https://")):
        apply_link = f"https://{apply_link}"

    return {
        "id": str(internship.get("_id")),
        "company_name": internship.get("company", ""),
        "role": internship.get("role", ""),
        "description": internship.get("description", ""),
        "location": internship.get("location", ""),
        "apply_link": apply_link,
        "required_skills": internship.get("required_skills", []),
        "experience_level": internship.get("experience_level", "Beginner"),
        "salary": internship.get("salary", ""),
        "company_website": internship.get("company_website", ""),
    }


def serialize_user(doc: Dict[str, object]) -> Dict[str, object]:
    return {
        "analysis_id": str(doc.get("_id")),
        "resume_filename": doc.get("resume_file", ""),
        "resume_score": doc.get("resume_score", 0),
        "score_breakdown": doc.get("score_breakdown", {}),
        "parsed_data": doc.get("parsed_data", {}),
        "missing_skills": doc.get("missing_skills", []),
        "suggestions": doc.get("suggestions", []),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else "",
    }


def _resume_suggestions(parsed_resume: Dict[str, object], missing_skills: List[str]) -> List[str]:
    suggestions = []
    links = parsed_resume.get("links") or {}
    if len(parsed_resume.get("skills", [])) < 6:
        suggestions.append("Add a dedicated Technical Skills section with core tools and frameworks.")
    if parsed_resume.get("projects", "Not mentioned") == "Not mentioned":
        suggestions.append("Add at least 2 impact-focused projects with measurable outcomes.")
    if not links.get("github"):
        suggestions.append("Include your GitHub portfolio link and highlight active repositories.")

    high_impact = [skill for skill in missing_skills if skill in {"tensorflow", "pytorch", "nlp", "deep learning", "sql"}]
    if high_impact:
        suggestions.append(f"Consider learning and adding these in-demand skills: {', '.join(high_impact[:5])}.")

    if not suggestions:
        suggestions.append("Resume looks strong. Keep tailoring project bullets for each role.")

    return suggestions


def _query_from_resume(parsed_data: Dict[str, object]) -> str:
    skills = parsed_data.get("skills", []) or []
    if skills:
        return " ".join(str(skill) for skill in skills[:8]) + " internship"

    parts = [
        str(parsed_data.get("projects", "") or ""),
        str(parsed_data.get("experience", "") or ""),
        str(parsed_data.get("education", "") or ""),
    ]
    text = " ".join(parts).strip()
    return text[:120] if text else "ai intern machine learning data science internship"


def _rank_live_for_analysis(analysis_id: str, parsed_data: Dict[str, object], query: str, location: str = "", limit: int = 15):
    live_items = fetch_live_internships(query, limit=limit)
    if not live_items:
        # fallback to already available live records in DB
        cached = [internship_to_dict(row) for row in get_internships()][:limit]
        if not cached:
            return []
        ranked_cached, _ = recommend_internships(
            parsed_data,
            cached,
            location_preference=location,
            top_k=min(10, len(cached)),
        )
        return ranked_cached

    stored_live_items = []
    for item in live_items:
        internship_id = upsert_internship(item)
        doc = internships_collection.find_one({"_id": ObjectId(internship_id)})
        if doc:
            stored_live_items.append(internship_to_dict(doc))

    ranked, _ = recommend_internships(
        parsed_data,
        stored_live_items,
        location_preference=location,
        top_k=min(10, len(stored_live_items)),
    )

    for recommendation in ranked:
        save_recommendation(
            {
                "user_id": analysis_id,
                "internship_id": recommendation.get("id"),
                "match_score": recommendation.get("match_score", 0),
                "ranking_score": recommendation.get("ranking_score", 0),
                "semantic_similarity": recommendation.get("semantic_similarity", 0),
                "fake_detection": recommendation.get("fake_detection", {}),
                "source": "live",
            }
        )

    return ranked


def _safe_apply_target(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return url
    return ""


def _build_apply_fallback(internship: Dict[str, object]) -> str:
    keywords = f"{internship.get('role', '')} {internship.get('company_name', '')} internship".strip()
    location = str(internship.get("location", "Remote") or "Remote")
    return (
        "https://www.linkedin.com/jobs/search/?"
        f"keywords={quote_plus(keywords)}&location={quote_plus(location)}"
    )


def _is_probably_bad_host(url: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    return (
        host.endswith(".example.com")
        or host.endswith(".example")
        or host in {"example.com", "localhost", "127.0.0.1", "0.0.0.0"}
    )


def register_routes(app: Flask) -> None:
    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"}), 200

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.get("/dashboard")
    def dashboard_page():
        return render_template("dashboard.html")

    @app.get("/recommendations")
    def recommendations_page():
        return render_template("recommendations.html")

    @app.get("/matched-internships")
    def matched_internships_page():
        return render_template("matched_internships.html")

    @app.get("/internship/<internship_id>")
    def internship_details_page(internship_id: str):
        return render_template("internship_details.html", internship_id=internship_id)

    @app.post("/api/activity")
    def add_activity():
        payload = request.get_json(silent=True) or {}
        analysis_id = str(payload.get("analysis_id", "")).strip()
        internship_id = str(payload.get("internship_id", "")).strip()
        event = str(payload.get("event", "viewed")).strip().lower()

        if not analysis_id or not internship_id or event not in {"viewed", "applied"}:
            return jsonify({"error": "analysis_id, internship_id and valid event are required"}), 400

        activity_id = log_user_activity(analysis_id, internship_id, event)
        return jsonify({"activity_id": activity_id, "status": "ok"})

    @app.get("/apply/<internship_id>")
    def apply_internship(internship_id: str):
        analysis_id = (request.args.get("analysis_id") or "").strip()
        try:
            doc = internships_collection.find_one({"_id": ObjectId(internship_id)})
        except Exception:
            doc = None

        if not doc:
            return jsonify({"error": "Internship not found"}), 404

        internship = internship_to_dict(doc)

        if analysis_id:
            try:
                log_user_activity(analysis_id, internship_id, "applied")
            except Exception:
                pass

        target = _safe_apply_target(str(internship.get("apply_link", "")))
        if not target or _is_probably_bad_host(target):
            return redirect(_build_apply_fallback(internship), code=302)

        # Quick availability check to avoid user landing on dead/forbidden links.
        try:
            response = requests.get(target, timeout=5, allow_redirects=True)
            if response.status_code >= 400:
                return redirect(_build_apply_fallback(internship), code=302)
        except Exception:
            return redirect(_build_apply_fallback(internship), code=302)

        return redirect(target, code=302)

    @app.post("/api/upload-resume")
    def upload_resume():
        if "resume" not in request.files:
            return jsonify({"error": "No resume file uploaded"}), 400

        file = request.files["resume"]
        if not file or file.filename == "":
            return jsonify({"error": "Empty file upload"}), 400
        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF resumes are supported"}), 400

        UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        safe_name = secure_filename(file.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        stored_filename = f"{timestamp}_{safe_name}"
        destination = UPLOAD_FOLDER / stored_filename
        file.save(str(destination))

        parsed_resume = parse_resume_pdf(str(destination))

        live_query = _query_from_resume(parsed_resume)
        live_items = fetch_live_internships(live_query, limit=20)

        internships = []
        for item in live_items:
            internship_id = upsert_internship(item)
            doc = internships_collection.find_one({"_id": ObjectId(internship_id)})
            if doc:
                internships.append(internship_to_dict(doc))

        if not internships:
            internships = [internship_to_dict(row) for row in get_internships()]

        recommendations, missing_skills = recommend_internships(
            parsed_resume,
            internships,
            location_preference=request.form.get("location_preference"),
            top_k=10,
        )

        score_payload = calculate_resume_score(parsed_resume, internships)
        suggestions = _resume_suggestions(parsed_resume, missing_skills)

        parsed_snapshot = {
            key: parsed_resume.get(key)
            for key in ["name", "email", "links", "skills", "education", "projects", "experience", "experience_years"]
        }

        analysis_id = insert_user(
            {
                "name": parsed_resume.get("name", "Candidate"),
                "email": parsed_resume.get("email", "Not found"),
                "skills": parsed_resume.get("skills", []),
                "resume_score": score_payload["score"],
                "resume_file": stored_filename,
                "parsed_data": parsed_snapshot,
                "score_breakdown": score_payload["breakdown"],
                "missing_skills": missing_skills,
                "suggestions": suggestions,
            }
        )

        for recommendation in recommendations:
            save_recommendation(
                {
                    "user_id": analysis_id,
                    "internship_id": recommendation.get("id"),
                    "match_score": recommendation.get("match_score", 0),
                    "ranking_score": recommendation.get("ranking_score", 0),
                    "semantic_similarity": recommendation.get("semantic_similarity", 0),
                    "fake_detection": recommendation.get("fake_detection", {}),
                    "source": "live",
                }
            )

        response = {
            "analysis_id": analysis_id,
            "candidate_name": parsed_resume.get("name", "Candidate"),
            "resume_score": score_payload["score"],
            "score_breakdown": score_payload["breakdown"],
            "parsed_data": parsed_snapshot,
            "missing_skills": missing_skills,
            "suggestions": suggestions,
            "recommendations": recommendations[:5],
        }
        return jsonify(response)

    @app.get("/api/analysis/<analysis_id>")
    def get_analysis(analysis_id: str):
        try:
            doc = users_collection.find_one({"_id": ObjectId(analysis_id)})
        except Exception:
            doc = None

        if not doc:
            return jsonify({"error": "Analysis not found"}), 404

        return jsonify(serialize_user(doc))

    @app.get("/api/recommendations/<analysis_id>")
    def get_recommendations(analysis_id: str):
        rec_docs = list(recommendations_collection.find({"user_id": analysis_id}))

        internship_ids = []
        for item in rec_docs:
            internship_id = item.get("internship_id")
            if internship_id:
                try:
                    internship_ids.append(ObjectId(internship_id))
                except Exception:
                    continue

        internships_map = {
            str(doc["_id"]): internship_to_dict(doc)
            for doc in internships_collection.find({"_id": {"$in": internship_ids}})
        }

        response_rows = []
        for rec in rec_docs:
            internship = internships_map.get(rec.get("internship_id"), {})
            if not internship:
                continue
            response_rows.append(
                {
                    **internship,
                    "match_score": rec.get("match_score", 0),
                    "ranking_score": rec.get("ranking_score", 0),
                    "semantic_similarity": rec.get("semantic_similarity", 0),
                    "fake_detection": rec.get("fake_detection", {}),
                    "source": rec.get("source", "cached"),
                }
            )

        response_rows.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)
        return jsonify({"analysis_id": analysis_id, "recommendations": response_rows})

    @app.get("/api/internship/<internship_id>")
    def get_internship(internship_id: str):
        analysis_id = (request.args.get("analysis_id") or "").strip()
        try:
            doc = internships_collection.find_one({"_id": ObjectId(internship_id)})
        except Exception:
            doc = None

        if not doc:
            return jsonify({"error": "Internship not found"}), 404

        if analysis_id:
            try:
                log_user_activity(analysis_id, internship_id, "viewed")
            except Exception:
                pass

        return jsonify(internship_to_dict(doc))

    @app.get("/api/internships")
    def list_internships():
        rows = [internship_to_dict(internship) for internship in get_internships()]
        return jsonify({"count": len(rows), "internships": rows})

    @app.get("/api/recommendations/live/<analysis_id>")
    def get_live_recommendations(analysis_id: str):
        try:
            user_doc = users_collection.find_one({"_id": ObjectId(analysis_id)})
        except Exception:
            user_doc = None

        if not user_doc:
            return jsonify({"error": "Analysis not found"}), 404

        parsed_data = user_doc.get("parsed_data", {})
        if not parsed_data:
            return jsonify({"error": "Parsed resume data not found"}), 404

        query = (request.args.get("q") or "").strip() or _query_from_resume(parsed_data)
        limit = int(request.args.get("limit", "15"))

        try:
            ranked = _rank_live_for_analysis(
                analysis_id,
                parsed_data,
                query=query,
                location=request.args.get("location", ""),
                limit=limit,
            )
        except Exception as exc:
            return jsonify({"error": f"Live internship fetch failed: {exc}"}), 502

        return jsonify({"analysis_id": analysis_id, "source": "live", "recommendations": ranked})

    @app.get("/api/recommendations/matched/<analysis_id>")
    def get_matched_recommendations(analysis_id: str):
        try:
            user_doc = users_collection.find_one({"_id": ObjectId(analysis_id)})
        except Exception:
            user_doc = None

        if not user_doc:
            return jsonify({"error": "Analysis not found"}), 404

        parsed_data = user_doc.get("parsed_data", {})
        if not parsed_data:
            return jsonify({"error": "Parsed resume data not found"}), 404

        manual_query = (request.args.get("q") or "").strip()
        query = manual_query or _query_from_resume(parsed_data)
        limit = int(request.args.get("limit", "15"))

        try:
            ranked = _rank_live_for_analysis(
                analysis_id,
                parsed_data,
                query=query,
                location=request.args.get("location", ""),
                limit=limit,
            )
        except Exception as exc:
            return jsonify({"error": f"Matched internship fetch failed: {exc}"}), 502

        return jsonify({"analysis_id": analysis_id, "source": "matched", "query": query, "recommendations": ranked})

    @app.post("/predict-career")
    def predict_career():
        payload = request.get_json(silent=True) or {}

        if not payload:
            return jsonify({"error": "Request body is required"}), 400

        result = predict_career_paths(payload, top_k=3)
        return jsonify(result)

    @app.post("/predict-success")
    def predict_success():
        payload = request.get_json(silent=True) or {}
        if not payload:
            return jsonify({"error": "Request body is required"}), 400

        result = predict_success_probability(payload)
        return jsonify(result)

    @app.get("/personalized-feed")
    def get_personalized_feed():
        analysis_id = (request.args.get("analysis_id") or "").strip()
        if not analysis_id:
            return jsonify({"error": "analysis_id is required"}), 400

        try:
            user_doc = users_collection.find_one({"_id": ObjectId(analysis_id)})
        except Exception:
            user_doc = None

        if not user_doc:
            return jsonify({"error": "Analysis not found"}), 404

        parsed_data = user_doc.get("parsed_data", {}) or {}
        activity = get_user_activity_summary(analysis_id)

        interests = request.args.get("interests", "")
        interest_list = [item.strip() for item in interests.split(",") if item.strip()]

        profile = {
            "skills": parsed_data.get("skills", []),
            "interests": interest_list,
            "viewed_ids": activity.get("viewed_ids", []),
            "applied_ids": activity.get("applied_ids", []),
        }

        internships = [internship_to_dict(item) for item in get_internships(include_non_live=True)]
        ranked = personalized_feed(profile, internships, top_k=10)

        return jsonify({"analysis_id": analysis_id, "recommendations": ranked})

    @app.post("/resume-analysis")
    def resume_analysis():
        payload = request.get_json(silent=True) or {}
        analysis_id = str(payload.get("analysis_id", "") or "").strip()
        resume_text = str(payload.get("resume_text", "") or "").strip()

        if not resume_text and analysis_id:
            try:
                user_doc = users_collection.find_one({"_id": ObjectId(analysis_id)})
            except Exception:
                user_doc = None

            if user_doc:
                parsed = user_doc.get("parsed_data", {}) or {}
                resume_text = "\n".join(
                    [
                        str(parsed.get("education", "")),
                        str(parsed.get("projects", "")),
                        str(parsed.get("experience", "")),
                        "Skills: " + ", ".join(parsed.get("skills", [])),
                    ]
                ).strip()

                resume_file = str(user_doc.get("resume_file", "") or "").strip()
                if resume_file:
                    pdf_path = UPLOAD_FOLDER / resume_file
                    if pdf_path.exists():
                        try:
                            resume_text = extract_text_from_pdf(str(pdf_path))
                        except Exception:
                            pass

        if not resume_text:
            return jsonify({"error": "Provide resume_text or valid analysis_id"}), 400

        result = analyze_resume_text(resume_text)
        return jsonify(result)


app = create_app()


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
