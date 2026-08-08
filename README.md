# TaskFlow Pro — Full-Stack Task Manager (FastAPI + SQLAlchemy + Vanilla JS)

TaskFlow Pro is a production-grade full-stack task management application built with a **FastAPI** backend, **SQLAlchemy / SQLite** data layer, **Pydantic** schema validation, custom logging middleware, CORS, and a responsive **Vanilla HTML/CSS/JavaScript** frontend.

---

## 🌟 Key Features

1. **Database Layer (SQLAlchemy ORM)**:
   - `users`: User profiles with unique email enforcement.
   - `projects`: Project containers linked to owners (`ForeignKey("users.id")`).
   - `tasks`: Task items linked to projects (`ForeignKey("projects.id")`) with `priority` (`low`, `medium`, `high`) constrained via `CheckConstraint`, and nullable `due_date` stored as plain `String/Text` to handle both standard dates and AI-parsed phrases like `"next friday"`.
   - Dual-sided `relationship()` and `back_populates` for seamless object traversal.

2. **REST API & Aggregation**:
   - Full CRUD endpoints for Tasks (`POST`, `GET`, `GET /{id}`, `PUT`, `DELETE`).
   - Create & list endpoints for Users and Projects.
   - **SQL Aggregate Stats**: `GET /projects/{id}/stats` executes a single SQLAlchemy query (`COUNT` + `GROUP BY` across a `JOIN` of `projects` and `tasks`) computing total tasks, count-by-priority, and count-by-status without fetching raw rows into Python.
   - **Dependency Injection**: Reused `get_db` session provider across all endpoints.
   - **Custom Middleware**: Logs HTTP method, request path, and processing duration (ms) for every request.
   - **Explicit CORS**: Configured with allowed origins (`http://127.0.0.1:8000`, `http://localhost:8000`, `http://127.0.0.1:5500`, `http://localhost:5500`).

3. **Frontend (Vanilla HTML/CSS/JS)**:
   - Sticky header with persistent brand & user/project selection.
   - Deliberate box-model styling (visible padding, borders, margins, shadows) on list container and task items.
   - Dual `@media` responsive breakpoints (`max-width: 768px` and `max-width: 480px`).
   - Strict `document.createElement()` and `textContent` usage (XSS protected).
   - Client-side validation: Blocks empty/whitespace title submissions with an inline error message.
   - `localStorage` cache: Renders cached tasks instantly on page load before backend API syncs.

---

## 🚀 Setup & Installation (Clean Checkout)

### Prerequisites
- Python 3.10+ installed
- Git

### Step-by-Step Setup

```bash
# 1. Clone repository (or navigate to workspace root)
cd capston

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## 🏃 Run Commands

### Mode 1: Single-Process Mode (Recommended Default)
In single-process mode, FastAPI serves both the REST API and the static frontend assets from a single server.

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Open your browser and navigate to: **`http://127.0.0.1:8000/`**

---

### Mode 2: Two-Process Mode (Separate Static Server)
If you prefer running a separate static file server for `static/`:

**Process 1 (FastAPI Backend)**:
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Process 2 (Static Frontend Server)**:
```bash
# In a second terminal:
python -m http.server 5500 --directory static
```
Open your browser and navigate to: **`http://127.0.0.1:5500/`**

---

## 🧪 Running Automated Tests

To run the automated API test suite verifying all CRUD operations, status codes (201, 200, 404, 422), aggregate stats, and validation rules:

```bash
python test_api.py
```

---

## 📁 Repository & Database Schema Structure

```
capston/
├── database.py       # SQLAlchemy Engine, SessionLocal, Base, get_db dependency
├── models.py         # SQLAlchemy ORM Models (User, Project, Task) with relationships & constraints
├── schemas.py        # Pydantic Schemas with title whitespace validation & Literal priority constraint
├── main.py           # FastAPI Application, middleware, CORS, CRUD endpoints, SQL stats, static files
├── test_api.py       # Comprehensive API unit test suite
├── requirements.txt  # Project python dependencies
├── .gitignore        # Git ignore rules
├── static/
│   ├── index.html    # Semantic layout, sticky header, task form, stats card
│   ├── styles.css    # Box-model styling, glassmorphism theme, 2 media breakpoints (768px, 480px)
│   └── app.js        # Vanilla JS, createElement, textContent, fetch API, eventListeners, localStorage
└── tasks.db          # SQLite database (auto-generated)
```

---

## 🌿 Git Branch & Merge History

This repository followed a structured Git feature branch workflow:
1. Feature branch created: `feature/task-manager`
2. Commit 1: `feat(backend): implement SQLAlchemy ORM models, Pydantic schemas, and database session provider`
3. Commit 2: `feat(frontend/api): add REST API endpoints, middleware, CORS, responsive frontend UI, and test suite`
4. Commit 3: `docs: add comprehensive README with setup, single/two-process run modes, and API docs`
5. Branch merged into `main` with explicit merge commit.
