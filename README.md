# AI Log Analyzer for DevOps

A full-stack DevOps diagnostic dashboard for uploading or pasting server, Docker, CI, and application logs. The backend returns structured AI-style analysis with grouped errors, severity, likely root cause, suggested fixes, and an overall health signal.

This is not a chatbot. It behaves like a lightweight monitoring assistant: users provide logs, the system analyzes them, and the dashboard renders operational findings.

## Tech Stack

- Frontend: React + Vite
- Backend: FastAPI
- AI layer: Swappable service in `backend/services/aiService.py`
- Database: PostgreSQL with SQLAlchemy, with memory fallback when `DATABASE_URL` is not set
- Upload support: `.log` and `.txt`

## Project Structure

```text
.
|-- backend/
|   |-- controllers/logController.py
|   |-- db/database.py
|   |-- db/models.py
|   |-- models/schemas.py
|   |-- routes/logRoutes.py
|   |-- services/aiService.py
|   |-- services/storageService.py
|   `-- main.py
|-- frontend/
|   |-- src/api.js
|   |-- src/main.jsx
|   `-- src/styles.css
|-- sample_logs/sample.log
|-- docker-compose.yml
|-- .env.example
|-- main.py
|-- requirements.txt
`-- README.md
```

## PostgreSQL Setup

If Docker is installed, start PostgreSQL:

```bash
docker compose up -d postgres
```

Create `.env` from the example:

```bash
copy .env.example .env
```

Default database URL:

```text
DATABASE_URL=postgresql+psycopg://devops:devops123@127.0.0.1:5433/log_analyzer
```

Tables are created automatically when FastAPI starts.

You can also create the tables manually:

```bash
python -m backend.db.init_db
```

If you do not create `.env`, the app still runs, but history is saved only in memory.

## Backend Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

The API will run at `http://127.0.0.1:8000`.

Useful endpoints:

- `POST /upload-logs` accepts multipart form data with `file` and optional `text`
- `POST /analyze` accepts JSON: `{ "logs": "...", "source": "manual paste" }`
- `GET /history` returns saved analyses
- `GET /sample-logs` returns sample logs
- `GET /health` returns service status and active storage mode

Open API docs:

```text
http://127.0.0.1:8000/docs
```

## Frontend Setup

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The UI will run at `http://127.0.0.1:5173`.

If the backend is on a different URL, create `frontend/.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Optional OpenAI Mode

The analyzer uses the deterministic mock DevOps analyzer by default. To enable the OpenAI path, set:

```bash
set OPENAI_API_KEY=your_key_here
set OPENAI_MODEL=gpt-4o-mini
```

If the OpenAI SDK is not installed or the API call fails, the backend falls back to the local mock analyzer.

## Expected AI JSON Shape

```json
{
  "summary": "...",
  "errors_found": [
    {
      "error": "...",
      "frequency": 2,
      "severity": "low | medium | high",
      "possible_cause": "...",
      "suggested_fix": "..."
    }
  ],
  "root_cause_analysis": "...",
  "overall_health": "good | warning | critical"
}
```

## UI Description

The app opens to a SaaS-style diagnostics dashboard with:

- A drag-and-drop `.log` / `.txt` upload zone
- A textarea for pasted logs
- A sample log loader
- A structured results view with summary, health indicator, metrics, severity table, repeated-error highlighting, and root cause analysis
- A browser print workflow for exporting reports as PDF
- A history page for previous analyses saved in PostgreSQL or memory

## Sample Logs

```text
[ERROR] Database connection failed at 03:45
[WARN] High memory usage detected
[ERROR] Timeout connecting to auth service
[INFO] Server restarted successfully
```
