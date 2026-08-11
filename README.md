# TaskFlow Pro — Full-Stack Task Manager (FastAPI + SQLAlchemy + Vanilla JS)

TaskFlow Pro is a full-stack task management app with a **FastAPI** backend, **SQLAlchemy** data layer, request validation, CORS, **Quick-Add free-text parsing**, and a responsive **Vanilla HTML/CSS/JavaScript** frontend. Local **HTTPS** is supported via free self-signed certificates.

---

## Key Features

1. **Database Layer (SQLAlchemy ORM)**
   - `users`, `projects`, `tasks` with foreign keys, relationships, and priority/status check constraints
   - `due_date` stored as plain text so AI/parser phrases like `"next friday"` work alongside ISO dates

2. **REST API**
   - Full CRUD for tasks; create/list for users and projects
   - Aggregate stats: `GET /projects/{id}/stats` (single SQLAlchemy `COUNT` + `GROUP BY` join)
   - Database error handling with safe transaction rollback
   - Explicit CORS for local HTTP and HTTPS origins

3. **Quick-Add (free-text → structured task)**
   - Deterministic Python parser (no paid AI API required)
   - Priority: `urgent` / `asap` → high; `whenever` / `low priority` → low; else medium
   - Due-date hints: relative (`today`, `tomorrow`, `next week`), `next <weekday>`, bare weekdays
   - Endpoints:
     - `POST /tasks/parse` — preview only
     - `POST /tasks/quick-add` — parse + create

4. **Frontend**
   - Sticky header, user/project pickers, task form, stats card, Quick-Add panel
   - Box-model styling + two responsive breakpoints (`768px`, `480px`)
   - `document.createElement` / `textContent` (XSS-safe)
   - `localStorage` cache for instant first paint

5. **HTTPS (local, free)**
   - Self-signed cert generation (`cryptography` package)
   - `python run_https.py` → `https://127.0.0.1:8443/`

---

## Setup

```bash
cd capston
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Linux/macOS
# source .venv/bin/activate

pip install -r requirements-dev.txt
```

---

## Run

### HTTP (default)

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/**

### HTTPS (self-signed, free)

```bash
python generate_certs.py   # once
python run_https.py
```

Open **https://127.0.0.1:8443/**
Accept the browser warning for the local self-signed certificate.

### Two-process mode (optional)

```bash
# Terminal 1 — API
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — static only
python -m http.server 5500 --directory static
```

---

## Tests

```bash
python test_api.py
```

Covers CRUD, validation (201/200/404/422), project stats, Quick-Add parse/create, and static frontend serving.

---

## Deploy to Render

The included `render.yaml` deploys the FastAPI service and a managed PostgreSQL database. It uses the production dependency set and probes `GET /health` before routing traffic. The database plan in the file is `basic-256mb`, which is a paid Render plan; choose a plan that fits your retention and availability needs.

1. Push this repository (including `render.yaml`) to GitHub.
2. In the Render dashboard, select **New** → **Blueprint**, connect the repository, and approve the resources shown.
3. Render creates `taskflow-pro`, injects its PostgreSQL connection string as `DATABASE_URL`, installs dependencies, and starts the service.
4. Open the generated `onrender.com` URL, then confirm `<service-url>/health` returns `{"status":"ok"}`.

For local development, the app still defaults to `tasks.db`. To use PostgreSQL locally, set `DATABASE_URL` to a PostgreSQL connection string before starting Uvicorn.

---

## Quick-Add example

**Input**

```text
Finish the report next Friday, it's urgent
```

**Parsed output**

```json
{
  "title": "Finish the report",
  "priority": "high",
  "due_date_hint": "next friday"
}
```

**API**

```bash
# Preview
curl -X POST http://127.0.0.1:8000/tasks/parse \
  -H "Content-Type: application/json" \
  -d "{\"description\": \"Finish the report next Friday, it's urgent\"}"

# Create
curl -X POST http://127.0.0.1:8000/tasks/quick-add \
  -H "Content-Type: application/json" \
  -d "{\"description\": \"Finish the report next Friday, it's urgent\", \"project_id\": 1}"
```

---

## Project structure

```
capston/
├── database.py          # Engine, SessionLocal, get_db
├── models.py            # User, Project, Task ORM models
├── schemas.py           # Pydantic request/response models
├── task_parser.py       # Quick-Add free-text parser
├── main.py              # FastAPI app, middleware, routes, static files
├── generate_certs.py    # Free self-signed TLS certs for local HTTPS
├── run_https.py         # Launch uvicorn with SSL on port 8443
├── test_api.py          # API + parser test suite
├── requirements.txt     # Free/open-source Python deps
├── static/
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── certs/               # Generated locally (gitignored)
```

---

## Free / open-source stack

| Component        | Package / tool                         |
|------------------|----------------------------------------|
| API framework    | FastAPI                                |
| ASGI server      | Uvicorn                                |
| ORM / DB         | SQLAlchemy + SQLite                    |
| Validation       | Pydantic                               |
| TLS certs (dev)  | `cryptography` (self-signed)           |
| Frontend         | Vanilla HTML / CSS / JS                 |
| HTTP client tests (dev) | `httpx` (via FastAPI TestClient) |

No paid APIs or proprietary SDKs are required to run, test, or serve over HTTPS locally.
