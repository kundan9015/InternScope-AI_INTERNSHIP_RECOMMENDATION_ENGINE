from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    analyses = db.relationship("ResumeAnalysis", backref="user", lazy=True)


class ResumeAnalysis(db.Model):
    __tablename__ = "resume_analyses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resume_filename = db.Column(db.String(255), nullable=False)
    extracted_data = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float, nullable=False)
    score_breakdown = db.Column(db.Text, nullable=False)
    recommendations = db.Column(db.Text, nullable=False)
    skill_gaps = db.Column(db.Text, nullable=False)
    suggestions = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Internship(db.Model):
    __tablename__ = "internships"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(120), nullable=False)
    apply_link = db.Column(db.String(500), nullable=False)
    required_skills = db.Column(db.String(600), nullable=False)
    experience_level = db.Column(db.String(50), nullable=False, default="Beginner")
    salary = db.Column(db.String(120), nullable=True)
    company_website = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
