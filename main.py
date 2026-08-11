import logging
import os
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db
from task_parser import parse_task_description

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Manager API", version="1.1.0")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Error handling
# ---------------------------------------------------------
def commit_or_raise(db: Session, duplicate_detail: str = "Database constraint violated") -> None:
    """Commit safely so a failed write never leaves a reused session invalid."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.info("Database constraint violation: %s", exc.orig)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=duplicate_detail) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database write failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database temporarily unavailable") from exc


# ---------------------------------------------------------
# CORS Configuration (HTTP + HTTPS local origins)
# ---------------------------------------------------------
origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()] or [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "https://127.0.0.1:8443",
    "https://localhost:8443",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://127.0.0.1:5500",
    "https://localhost:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
)


# ---------------------------------------------------------
# User Endpoints
# ---------------------------------------------------------
@app.post("/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = models.User(email=user.email, name=user.name)
    db.add(new_user)
    commit_or_raise(db, "Email already registered")
    db.refresh(new_user)
    return new_user


@app.get("/users", response_model=List[schemas.UserResponse], status_code=status.HTTP_200_OK)
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


# ---------------------------------------------------------
# Project Endpoints
# ---------------------------------------------------------
@app.post("/projects", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    owner = db.query(models.User).filter(models.User.id == project.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail=f"User {project.owner_id} not found")
    new_project = models.Project(name=project.name, owner_id=project.owner_id)
    db.add(new_project)
    commit_or_raise(db)
    db.refresh(new_project)
    return new_project


@app.get("/projects", response_model=List[schemas.ProjectResponse], status_code=status.HTTP_200_OK)
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()


# ---------------------------------------------------------
# Project Stats Aggregate Endpoint (Single SQLAlchemy query)
# ---------------------------------------------------------
@app.get(
    "/projects/{project_id}/stats",
    response_model=schemas.ProjectStatsResponse,
    status_code=status.HTTP_200_OK,
)
def get_project_stats(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    results = (
        db.query(
            models.Task.priority,
            models.Task.status,
            func.count(models.Task.id).label("task_count"),
        )
        .select_from(models.Project)
        .join(models.Task, models.Project.id == models.Task.project_id)
        .filter(models.Project.id == project_id)
        .group_by(models.Task.priority, models.Task.status)
        .all()
    )

    total_tasks = 0
    priority_counts = {"low": 0, "medium": 0, "high": 0}
    status_counts = {"pending": 0, "completed": 0}

    for priority, task_status, count in results:
        total_tasks += count
        if priority in priority_counts:
            priority_counts[priority] += count
        if task_status in status_counts:
            status_counts[task_status] += count

    return schemas.ProjectStatsResponse(
        project_id=project.id,
        project_name=project.name,
        total_tasks=total_tasks,
        priority_counts=schemas.PriorityStats(**priority_counts),
        status_counts=schemas.StatusStats(**status_counts),
    )


# ---------------------------------------------------------
# Quick-Add: free-text parse + create
# ---------------------------------------------------------
@app.post(
    "/tasks/parse",
    response_model=schemas.QuickAddParseResponse,
    status_code=status.HTTP_200_OK,
)
def parse_task(body: schemas.QuickAddParseRequest):
    """Parse a free-text description into title / priority / due_date_hint (no DB write)."""
    parsed = parse_task_description(body.description)
    return schemas.QuickAddParseResponse(**parsed)


@app.post(
    "/tasks/quick-add",
    response_model=schemas.TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def quick_add_task(body: schemas.QuickAddCreateRequest, db: Session = Depends(get_db)):
    """
    Parse free-text description and create a task in one step.

    Example description: "Finish the report next Friday, it's urgent"
    → title="Finish the report", priority="high", due_date="next friday"
    """
    project = db.query(models.Project).filter(models.Project.id == body.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {body.project_id} not found")

    parsed = parse_task_description(body.description)
    new_task = models.Task(
        title=parsed["title"],
        project_id=body.project_id,
        priority=parsed["priority"],
        due_date=parsed["due_date_hint"],
        status="pending",
    )
    db.add(new_task)
    commit_or_raise(db)
    db.refresh(new_task)
    return new_task


# ---------------------------------------------------------
# Task Endpoints (Full CRUD)
# ---------------------------------------------------------
@app.post("/tasks", response_model=schemas.TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == task.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {task.project_id} not found")
    new_task = models.Task(
        title=task.title,
        project_id=task.project_id,
        priority=task.priority,
        due_date=task.due_date,
        status=task.status,
    )
    db.add(new_task)
    commit_or_raise(db)
    db.refresh(new_task)
    return new_task


@app.get("/tasks", response_model=List[schemas.TaskResponse], status_code=status.HTTP_200_OK)
def list_tasks(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Task)
    if project_id is not None:
        query = query.filter(models.Task.project_id == project_id)
    return query.all()


@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse, status_code=status.HTTP_200_OK)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.put("/tasks/{task_id}", response_model=schemas.TaskResponse, status_code=status.HTTP_200_OK)
def update_task(task_id: int, task_update: schemas.TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    update_data = task_update.model_dump(exclude_unset=True)
    if "project_id" in update_data and update_data["project_id"] is not None:
        project = (
            db.query(models.Project)
            .filter(models.Project.id == update_data["project_id"])
            .first()
        )
        if not project:
            raise HTTPException(
                status_code=404,
                detail=f"Project {update_data['project_id']} not found",
            )

    for key, value in update_data.items():
        setattr(db_task, key, value)

    commit_or_raise(db)
    db.refresh(db_task)
    return db_task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    db.delete(db_task)
    commit_or_raise(db)
    return {"message": "Task deleted successfully", "id": task_id}


@app.get("/health", include_in_schema=False)
def health_check(db: Session = Depends(get_db)):
    """Deployment health probe that verifies database connectivity."""
    try:
        db.execute(select(func.now()))
    except SQLAlchemyError as exc:
        logger.exception("Health check database failure")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from exc
    return {"status": "ok"}


# ---------------------------------------------------------
# Static File Serving (Single-process web app mode)
# ---------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def read_root():
    return FileResponse("static/index.html")
