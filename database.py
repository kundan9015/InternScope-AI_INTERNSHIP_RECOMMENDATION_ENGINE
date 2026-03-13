import os
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    mongo_username = os.getenv("MONGO_USERNAME")
    mongo_password = os.getenv("MONGO_PASSWORD")
    mongo_cluster = os.getenv("MONGO_CLUSTER", "cluster0.xxxxx.mongodb.net")
    mongo_database = os.getenv("MONGO_DATABASE", "internship_db")

    if mongo_username and mongo_password:
        encoded_username = quote_plus(mongo_username)
        encoded_password = quote_plus(mongo_password)
        MONGO_URI = (
            f"mongodb+srv://{encoded_username}:{encoded_password}@{mongo_cluster}/"
            f"{mongo_database}?retryWrites=true&w=majority"
        )

if not MONGO_URI:
    raise RuntimeError(
        "MongoDB settings missing. Set MONGO_URI or MONGO_USERNAME + MONGO_PASSWORD in .env."
    )


client = MongoClient(MONGO_URI)
db_name = os.getenv("MONGO_DATABASE", "internship_db")
db: Database = client[db_name]

users_collection: Collection = db["users"]
internships_collection: Collection = db["internships"]
recommendations_collection: Collection = db["recommendations"]
user_activity_collection: Collection = db["user_activity"]

internships_collection.create_index([("source", 1), ("external_id", 1)], unique=True, sparse=True)
recommendations_collection.create_index([("user_id", 1), ("internship_id", 1), ("source", 1)])
user_activity_collection.create_index([("user_id", 1), ("internship_id", 1), ("event", 1), ("created_at", -1)])


def insert_user(user_data: Dict[str, Any]) -> str:
    payload = {
        "name": user_data.get("name", "Candidate"),
        "email": user_data.get("email", "Not found"),
        "skills": user_data.get("skills", []),
        "resume_score": user_data.get("resume_score", 0),
        "resume_file": user_data.get("resume_file", ""),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    # Keep additional analysis metadata for dashboard retrieval.
    for key in ["parsed_data", "score_breakdown", "missing_skills", "suggestions"]:
        if key in user_data:
            payload[key] = user_data[key]

    result = users_collection.insert_one(payload)
    return str(result.inserted_id)


def insert_internship(internship_data: Dict[str, Any]) -> str:
    payload = {
        "company": internship_data.get("company", ""),
        "role": internship_data.get("role", ""),
        "required_skills": internship_data.get("required_skills", []),
        "location": internship_data.get("location", "Remote"),
        "description": internship_data.get("description", ""),
        "apply_link": internship_data.get("apply_link", ""),
        "experience_level": internship_data.get("experience_level", "Beginner"),
        "salary": internship_data.get("salary", ""),
        "company_website": internship_data.get("company_website", ""),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = internships_collection.insert_one(payload)
    return str(result.inserted_id)


def get_internships(include_non_live: bool = False) -> List[Dict[str, Any]]:
    if include_non_live:
        return list(internships_collection.find({}))
    return list(internships_collection.find({"source": "live-api"}))


def upsert_internship(internship_data: Dict[str, Any]) -> str:
    source = internship_data.get("source")
    external_id = internship_data.get("external_id")

    if source and external_id:
        filter_doc = {"source": source, "external_id": external_id}
        update_doc = {
            "$set": {
                "company": internship_data.get("company", ""),
                "role": internship_data.get("role", ""),
                "required_skills": internship_data.get("required_skills", []),
                "location": internship_data.get("location", "Remote"),
                "description": internship_data.get("description", ""),
                "apply_link": internship_data.get("apply_link", ""),
                "experience_level": internship_data.get("experience_level", "Beginner"),
                "salary": internship_data.get("salary", ""),
                "company_website": internship_data.get("company_website", ""),
                "updated_at": datetime.utcnow(),
            },
            "$setOnInsert": {
                "source": source,
                "external_id": external_id,
                "created_at": datetime.utcnow(),
            },
        }
        internships_collection.update_one(filter_doc, update_doc, upsert=True)
        doc = internships_collection.find_one(filter_doc)
        return str(doc["_id"])

    return insert_internship(internship_data)


def save_recommendation(recommendation_data: Dict[str, Any]) -> str:
    payload = {
        "user_id": recommendation_data.get("user_id"),
        "internship_id": recommendation_data.get("internship_id"),
        "match_score": recommendation_data.get("match_score", 0),
        "ranking_score": recommendation_data.get("ranking_score", 0),
        "semantic_similarity": recommendation_data.get("semantic_similarity", 0),
        "fake_detection": recommendation_data.get("fake_detection", {}),
        "source": recommendation_data.get("source", "cached"),
        "created_at": datetime.utcnow(),
    }
    result = recommendations_collection.insert_one(payload)
    return str(result.inserted_id)


def log_user_activity(user_id: str, internship_id: str, event: str) -> str:
    payload = {
        "user_id": user_id,
        "internship_id": internship_id,
        "event": event,
        "created_at": datetime.utcnow(),
    }
    result = user_activity_collection.insert_one(payload)
    return str(result.inserted_id)


def get_user_activity_summary(user_id: str) -> Dict[str, List[str]]:
    rows = list(user_activity_collection.find({"user_id": user_id}).sort("created_at", -1))

    viewed = []
    applied = []
    for row in rows:
        internship_id = str(row.get("internship_id", ""))
        event = str(row.get("event", "")).lower()
        if not internship_id:
            continue
        if event == "viewed":
            viewed.append(internship_id)
        if event == "applied":
            applied.append(internship_id)

    # preserve latest-first with unique IDs
    def _unique(items: List[str]) -> List[str]:
        seen = set()
        out = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out

    return {
        "viewed_ids": _unique(viewed),
        "applied_ids": _unique(applied),
    }
