from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, field_validator


def _clean_required_text(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty or blank")
    return value


# User Schemas
class UserBase(BaseModel):
    email: str
    name: Optional[str] = None


class UserCreate(UserBase):
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        value = _clean_required_text(v, "Email")
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Email must contain a local part and domain")
        return value.lower()


class UserResponse(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Project Schemas
class ProjectBase(BaseModel):
    name: str
    owner_id: int


class ProjectCreate(ProjectBase):
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _clean_required_text(v, "Project name")


class ProjectResponse(ProjectBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Task Schemas
PriorityType = Literal["low", "medium", "high"]
StatusType = Literal["pending", "completed"]


class TaskBase(BaseModel):
    title: str
    project_id: int
    priority: PriorityType = "medium"
    due_date: Optional[str] = None
    status: StatusType = "pending"


class TaskCreate(TaskBase):
    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return _clean_required_text(v, "Task title")


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[PriorityType] = None
    due_date: Optional[str] = None
    status: Optional[StatusType] = None
    project_id: Optional[int] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _clean_required_text(v, "Task title")
        return v


class TaskResponse(TaskBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Quick-Add Schemas (free-text → structured task)
class QuickAddParseRequest(BaseModel):
    description: str

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        return _clean_required_text(v, "Description")


class QuickAddParseResponse(BaseModel):
    title: str
    priority: PriorityType
    due_date_hint: Optional[str] = None


class QuickAddCreateRequest(BaseModel):
    description: str
    project_id: int

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        return _clean_required_text(v, "Description")


# Stats Schemas
class PriorityStats(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0


class StatusStats(BaseModel):
    pending: int = 0
    completed: int = 0


class ProjectStatsResponse(BaseModel):
    project_id: int
    project_name: str
    total_tasks: int
    priority_counts: PriorityStats
    status_counts: StatusStats
