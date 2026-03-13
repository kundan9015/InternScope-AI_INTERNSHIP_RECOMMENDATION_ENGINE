# InternScope: AI Internship Recommendation Engine

InternScope is an end-to-end Flask application that evaluates resumes and recommends high-fit internships using NLP, ranking logic, and live market data.

It is designed as a practical AI product: upload a resume, get skill-gap insights, see ranked opportunities, and track recommendation quality through user interaction signals.

## What This Project Delivers

- Resume parsing from PDF with extraction of profile entities (skills, education, projects, experience, links)
- Resume scoring system with interpretable breakdown and actionable suggestions
- Internship ranking using TF-IDF style text similarity plus rule-based weighting
- Live internship aggregation from public job APIs and on-demand re-ranking
- Career path prediction with confidence-based top-role output
- Internship success probability estimation for profile-opportunity fit
- Personalized recommendation feed based on content and activity signals
- Fake internship heuristics to reduce low-quality listings
- Dashboard-ready APIs for analysis, recommendations, and interaction tracking

## Product Snapshot

### Core User Flow

1. Candidate uploads resume PDF.
2. System parses and scores the profile.
3. Engine fetches and ranks internship opportunities.
4. Candidate reviews matched roles and improvement suggestions.
5. User interactions are logged to support personalization.

### Key Modules

- [app.py](app.py): Flask routes, orchestration, health check, API layer
- [resume_parser.py](resume_parser.py): PDF text extraction and structured resume parsing
- [scoring_system.py](scoring_system.py): Resume score and component-wise scoring logic
- [recommendation_engine.py](recommendation_engine.py): Ranking and recommendation logic
- [career_predictor.py](career_predictor.py): Career path prediction engine
- [success_predictor.py](success_predictor.py): Selection probability estimation
- [fake_internship_detector.py](fake_internship_detector.py): Listing quality risk checks
- [database.py](database.py): MongoDB connection and persistence helpers
- [utils/live_internship_service.py](utils/live_internship_service.py): Live API fetch and normalization

## Tech Stack

- Backend: Flask, Python
- Data and NLP: nltk, pdfplumber, PyPDF2
- Storage: MongoDB Atlas
- Frontend: HTML, CSS, JavaScript, Chart.js
- Deployment-ready runtime: Gunicorn + WSGI

## API Surface

- POST /api/upload-resume
- GET /api/analysis/<analysis_id>
- GET /api/recommendations/<analysis_id>
- GET /api/recommendations/live/<analysis_id>?q=ai%20intern
- GET /api/recommendations/matched/<analysis_id>
- GET /api/internship/<internship_id>
- GET /api/internships
- POST /predict-career
- POST /predict-success
- GET /personalized-feed?analysis_id=<id>&interests=ai,ml
- POST /resume-analysis
- POST /api/activity
- GET /healthz

## Deployment Readiness

This repository includes production files for cloud deployment:

- [Procfile](Procfile)
- [wsgi.py](wsgi.py)
- [runtime.txt](runtime.txt)
- [render.yaml](render.yaml)

## Data and Persistence

- Resume analysis snapshots are stored in the users collection.
- Live and normalized internship records are stored in the internships collection.
- Ranked results are stored in the recommendations collection.
- Interaction logs are stored in the user_activity collection.

## Why This Stands Out

- Combines classic NLP with practical ranking signals for real-world recommendations.
- Avoids static demo data by integrating live internship sources.
- Keeps recommendations explainable with transparent scoring and skill-gap feedback.
- Structured as a deployable product, not just a notebook prototype.
