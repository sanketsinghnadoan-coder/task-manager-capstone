from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# User Schemas
class UserBase(BaseModel):
    email: str
    name: Optional[str] = None


class UserCreate(UserBase):
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Email cannot be empty or blank")
        return v.strip()


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
        if not v.strip():
            raise ValueError("Project name cannot be empty or blank")
        return v.strip()


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
        if not v or not v.strip():
            raise ValueError("Task title cannot be empty or blank")
        return v.strip()


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
            if not v.strip():
                raise ValueError("Task title cannot be empty or blank")
            return v.strip()
        return v


class TaskResponse(TaskBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


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
