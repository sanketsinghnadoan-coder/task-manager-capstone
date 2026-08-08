from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True)

    # Relationships
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    priority = Column(String, nullable=False, default="medium")
    due_date = Column(String, nullable=True)  # Plain String/Text column accepting typed dates or phrases
    status = Column(String, nullable=False, default="pending")  # "pending" or "completed"

    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="check_task_priority"),
        CheckConstraint("status IN ('pending', 'completed')", name="check_task_status"),
    )

    # Relationships
    project = relationship("Project", back_populates="tasks")
