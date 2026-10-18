from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class TaskStatus(str, Enum):
    """Valid task statuses."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(str, Enum):
    """Valid task priorities."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def from_str(cls, value: str) -> TaskPriority:
        """Convert a string to a TaskPriority enum value."""
        try:
            return cls(value.lower())
        except ValueError:
            valid = [v.value for v in cls]
            raise ValueError(
                f"Invalid priority '{value}'. Must be one of: {', '.join(valid)}"
            )


def _normalize_to_utc(value: datetime | str | None) -> datetime | None:
    """Normalize a datetime to UTC.

    - Naive datetimes (no tzinfo) are interpreted as UTC.
    - Timezone-aware datetimes are converted to UTC preserving the instant.
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class Task(BaseModel):
    """A task in the task management system."""

    id: str = Field(description="Unique task identifier")
    title: str = Field(description="Task title")
    description: str = Field(description="Task description")
    priority: TaskPriority = Field(description="Task priority level")
    status: TaskStatus = Field(description="Task status")
    created_at: datetime = Field(description="Task creation timestamp (UTC)")
    updated_at: datetime = Field(description="Task last update timestamp (UTC)")
    due_at: datetime | None = Field(default=None, description="Task due date (UTC)")

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title must not be blank")
        return v.strip()

    @field_validator("created_at", "updated_at", "due_at")
    @classmethod
    def due_at_normalize_utc(cls, v: datetime | str | None) -> datetime | None:
        return _normalize_to_utc(v)

    def to_dict(self) -> dict:
        """Convert task to a plain dict for JSON serialization."""
        result: dict = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if self.due_at is not None:
            result["due_at"] = self.due_at.isoformat()
        return result


class CreateTaskRequest(BaseModel):
    """Request model for creating a task."""

    title: str = Field(description="Task title (must not be blank)")
    description: str = Field(default="", description="Task description")
    priority: str = Field(description="Task priority: low, medium, or high")
    status: str = Field(default="todo", description="Task status: todo, in_progress, or done")
    due_at: str | None = Field(default=None, description="Task due date in ISO 8601 format (UTC)")

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title must not be blank")
        return v.strip()

    @field_validator("priority")
    @classmethod
    def priority_valid(cls, v: str) -> str:
        TaskPriority.from_str(v)
        return v.lower()

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        valid = [s.value for s in TaskStatus]
        if v.lower() not in valid:
            raise ValueError(f"Invalid status '{v}'. Must be one of: {', '.join(valid)}")
        return v.lower()


class UpdateTaskRequest(BaseModel):
    """Request model for updating a task."""

    title: str | None = Field(default=None, description="Updated title (must not be blank if provided)")
    description: str | None = Field(default=None, description="Updated description")
    priority: str | None = Field(default=None, description="Updated priority: low, medium, or high")
    status: str | None = Field(default=None, description="Updated status: todo, in_progress, or done")

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Title must not be blank")
        return v.strip() if v is not None else None

    @field_validator("priority")
    @classmethod
    def priority_valid(cls, v: str | None) -> str | None:
        if v is not None:
            TaskPriority.from_str(v)
            return v.lower()
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str | None) -> str | None:
        if v is not None:
            valid = [s.value for s in TaskStatus]
            if v.lower() not in valid:
                raise ValueError(f"Invalid status '{v}'. Must be one of: {', '.join(valid)}")
            return v.lower()
        return v


class ListTaskFilters(BaseModel):
    """Filters for listing tasks."""

    status: str | None = Field(default=None, description="Filter by status: todo, in_progress, or done")
    priority: str | None = Field(default=None, description="Filter by priority: low, medium, or high")
    search: str | None = Field(default=None, description="Search tasks by title or description (case-insensitive)")

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str | None) -> str | None:
        if v is not None:
            valid = [s.value for s in TaskStatus]
            if v.lower() not in valid:
                raise ValueError(f"Invalid status '{v}'. Must be one of: {', '.join(valid)}")
            return v.lower()
        return v

    @field_validator("priority")
    @classmethod
    def priority_valid(cls, v: str | None) -> str | None:
        if v is not None:
            TaskPriority.from_str(v)
            return v.lower()
        return v
