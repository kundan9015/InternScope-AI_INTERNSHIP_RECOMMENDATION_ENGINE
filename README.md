# AI Internship Recommendation Engine

A Flask + ML web app for resume analysis and internship recommendations using MongoDB Atlas cloud database.

## Features

- PDF resume upload and NLP parsing
- Resume field extraction: name, email, skills, education, projects, experience
- Resume scoring (0 to 100) using weighted factors
- Internship recommendation engine with TF-IDF + cosine similarity
- Skill gap analyzer and resume improvement suggestions
- Basic fake internship detection
- Internship ranking score and dashboard visualization
- MongoDB Atlas collections for users, internships, and recommendations
- Live internship-only fetch from public job API with on-demand re-ranking
- AI Career Path Prediction (top 3 roles with confidence)
- Internship Success Probability Predictor
- Personalized Internship Recommendation Feed (content + interaction aware)
- AI Resume Improvement Analyzer

## Tech Stack

- Backend: Python, Flask, PyMongo
- ML/NLP: nltk, pdfplumber, PyPDF2
- Frontend: HTML, CSS, JavaScript, Chart.js
- Database: MongoDB Atlas

## Project Structure

project/
- app.py
- requirements.txt
- models/
- utils/
- dataset/
- templates/
- static/
  - css/
  - js/
- resume_parser.py
- recommendation_engine.py
- scoring_system.py
- fake_internship_detector.py

## Setup and Run

1. Create and activate a virtual environment.

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Create `.env` from `.env.example` and set Atlas credentials.

```text
# Option 1
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/internship_db?retryWrites=true&w=majority

# Option 2
MONGO_USERNAME=<username>
MONGO_PASSWORD=<password>
MONGO_CLUSTER=cluster0.xxxxx.mongodb.net
MONGO_DATABASE=internship_db
```

3. Install dependencies.

```powershell
pip install -r requirements.txt
```

4. Start the Flask app.

```powershell
python app.py
```

5. Open in browser.

```text
http://127.0.0.1:5000
```

## GitHub and Render Deployment Ready

This project includes deployment files:

- `Procfile` for process startup (`gunicorn --workers 2 --threads 4 --timeout 120 --worker-tmp-dir /dev/shm wsgi:app`)
- `wsgi.py` as production entrypoint
- `runtime.txt` to pin Python version
- `render.yaml` for one-click Render blueprint setup
- `GET /healthz` endpoint for health checks

## Push to GitHub

Run these commands from the `project/` folder:

```powershell
git init
git add .
git commit -m "Final production-ready version"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

If repo is already initialized:

```powershell
git add .
git commit -m "Final touch-up before Render deploy"
git push
```

### Deploy on Render

1. Go to Render dashboard and click `New +` -> `Web Service`.
2. Connect your GitHub repo.
3. Render auto-detects config from `render.yaml` (or set manually):

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn wsgi:app
Health Check Path: /healthz
```

4. Set environment variables in Render dashboard:

```text
MONGO_USERNAME=<your-atlas-username>
MONGO_PASSWORD=<your-atlas-password>
MONGO_CLUSTER=<your-cluster-host>
MONGO_DATABASE=internship_db
```

Or set a single variable:

```text
MONGO_URI=mongodb+srv://<username>:<password>@<cluster-host>/internship_db?retryWrites=true&w=majority
```

Optional live job API overrides:

```text
LIVE_JOBS_API_URL=https://remotive.com/api/remote-jobs
SECONDARY_LIVE_JOBS_API_URL=https://www.arbeitnow.com/api/job-board-api
THIRD_LIVE_JOBS_API_URL=https://www.themuse.com/api/public/jobs
MIN_LIVE_RESULTS=10
```

5. Build command:

```text
pip install -r requirements.txt
```

6. Start command:

```text
gunicorn wsgi:app
```

7. After first deploy, open:

```text
https://<your-render-service>.onrender.com/healthz
```

If this returns `{ "status": "ok" }`, deployment is healthy.

## Optional Dependencies

- `scikit-learn` and `spacy` are optional in this project.
- The app has fallback logic, so deployment works even without these heavy packages.

## API Endpoints

- `POST /api/upload-resume` : Upload and analyze resume PDF
- `GET /api/analysis/<analysis_id>` : Get analysis results for dashboard
- `GET /api/recommendations/<analysis_id>` : Get ranked recommendations
- `GET /api/recommendations/live/<analysis_id>?q=ai%20intern` : Fetch and rank live internships
- `GET /api/recommendations/matched/<analysis_id>` : Resume-matched internships for new matched page
- `GET /api/internship/<internship_id>` : Get internship details
- `GET /api/internships` : List internships
- `POST /predict-career` : Predict top career paths from resume profile
- `POST /predict-success` : Estimate selection probability for a specific internship
- `GET /personalized-feed?analysis_id=<id>&interests=ai,ml` : Personalized recommendation feed
- `POST /resume-analysis` : AI resume improvement analysis
- `POST /api/activity` : Log user events (`viewed`, `applied`)

## API Testing

- Import `postman_collection.json` from the project root into Postman.
- Set `baseUrl` to `http://127.0.0.1:5000`.
- After running upload-resume, copy `analysis_id` into collection variable `analysisId`.

## Notes

- Uploaded resumes are stored in `uploads/`.
- Internships are fetched from live APIs and upserted into MongoDB collection `internships`.
- Resume analysis snapshots are stored in `users` collection.
- Ranked recommendation entries are stored in `recommendations` collection.
- User interaction history is stored in `user_activity` collection.
