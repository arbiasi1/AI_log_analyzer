# OpsCore AIOps Incident Platform

A full-stack AIOps incident management platform for service health, incidents, alerts, deployments, audit activity, and AI-assisted log intelligence. Users can upload or paste server, Docker, CI, Kubernetes, database, gateway, and application logs; the backend creates structured analysis with grouped errors, severity, root cause, service impact, ML anomaly signals, SLO risk, suggested fixes, runbook steps, and automatic incident creation.

This is not a chatbot or a simple analyzer demo. It behaves like an operations command center: services are tracked, high-risk analyses create incidents, alert rules are visible, deploy events are correlated, and AI is used as an incident reasoning layer.

## Tech Stack

- Frontend: React + Vite
- Backend: FastAPI
- AI/ML layer: Swappable OpenAI path plus deterministic local ML-style scoring in `backend/services/aiService.py`
- Database: PostgreSQL with SQLAlchemy, with memory fallback when `DATABASE_URL` is not set
- Upload support: `.log` and `.txt`
- Platform modules: services, environments, incidents, alert rules, deploy correlation, audit trail

## Project Structure

```text
.
|-- backend/
|   |-- controllers/logController.py
|   |-- db/database.py
|   |-- db/models.py
|   |-- models/schemas.py
|   |-- routes/logRoutes.py
|   |-- routes/platformRoutes.py
|   |-- services/aiService.py
|   |-- services/platformService.py
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

To force memory mode while a `.env` file exists:

```bash
set DISABLE_DATABASE=1
python -m uvicorn main:app --reload
```

## Backend Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

The API will run at `http://127.0.0.1:8000`.

Useful endpoints:

- `POST /auth/login` accepts JSON: `{ "email": "admin@devops.local", "password": "admin123" }`
- `GET /auth/me` returns the active user profile
- `POST /auth/logout` records logout activity
- `GET /auth/audit` returns recent security and analysis events
- `POST /upload-logs` accepts multipart form data with `file` and optional `text`
- `POST /analyze` accepts JSON: `{ "logs": "...", "source": "manual paste" }`
- `GET /history` returns saved analyses
- `GET /ops/overview` returns fleet-level analysis metrics, top services, and recurring patterns
- `GET /platform/overview` returns environments, services, incidents, alert rules, deploys, and copilot brief
- `GET /platform/incidents` returns the incident queue
- `POST /platform/incidents/{incident_id}/resolve` resolves an incident
- `GET /platform/alert-rules` returns configured alert rules
- `GET /sample-logs` returns sample logs
- `GET /health` returns service status and active storage mode

Open API docs:

```text
http://127.0.0.1:8000/docs
```

## Login

Default local credentials:

```text
Email: admin@devops.local
Password: admin123
```

Override them with environment variables:

```bash
set ADMIN_EMAIL=you@example.com
set ADMIN_PASSWORD=change-this
set ADMIN_NAME=Your Name
set ADMIN_TEAM=Platform Engineering
set AUTH_SECRET=use-a-long-random-secret
```

Analyzer, upload, history, overview, and audit endpoints require a Bearer token from `/auth/login`.

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

## Real AI Mode

The analyzer always creates a local deterministic baseline first. When `OPENAI_API_KEY` is set, it sends the logs plus that baseline to OpenAI so a real LLM can refine root-cause reasoning, SLO impact, service impact, incident timeline, and runbook guidance.

```bash
set OPENAI_API_KEY=your_key_here
set OPENAI_MODEL=gpt-4o-mini
```

If the OpenAI SDK is not installed, the API key is missing, or the API call fails, the backend falls back to local ML mode and marks the report with `ai_engine: local-ml`. When OpenAI succeeds, reports show `ai_engine: openai`, the active model, and `LLM-enhanced reasoning applied`.

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
  "overall_health": "good | warning | critical",
  "incident_score": 0,
  "ml_signals": [
    {
      "name": "Anomaly intensity",
      "score": 72,
      "confidence": 0.86,
      "trend": "stable | rising | falling | spiky",
      "explanation": "..."
    }
  ],
  "incident_timeline": [
    {
      "time": "T+00m",
      "phase": "detected | correlated | mitigating | resolved",
      "title": "...",
      "detail": "..."
    }
  ],
  "impacted_services": [
    {
      "service": "api-gateway",
      "impact_score": 68,
      "evidence": "..."
    }
  ],
  "runbook": [
    {
      "title": "...",
      "command": "kubectl logs deploy/<service> --since=30m",
      "rationale": "..."
    }
  ],
  "slo_impact": {
    "availability_risk": 80,
    "latency_risk": 54,
    "error_budget_burn": "normal | elevated | fast",
    "customer_impact": "..."
  },
  "next_best_actions": ["..."],
  "detection_notes": ["..."]
}
```

## UI Description

The app opens to an enterprise-style operations workspace with:

- Sidebar navigation and secure login/logout
- Command Center with service health, active incidents, risk KPIs, and AI command brief
- Service catalog with owners, dependencies, status, and risk scores
- Incident queue with automatic incident creation from critical analyses and resolve workflow
- Log Analyzer with drag-and-drop `.log` / `.txt` upload, pasted logs, sample loader, and export
- AI Intelligence workspace for anomaly signals, OpenAI/local engine status, runbooks, and fleet learning
- Alert Rules and Deploy Correlation views
- History and Settings pages with audit activity

## Sample Logs

```text
[ERROR] Database connection failed at 03:45
[WARN] High memory usage detected
[ERROR] Timeout connecting to auth service
[INFO] Server restarted successfully
```
