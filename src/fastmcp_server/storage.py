from __future__ import annotations

import uuid
from datetime import UTC, datetime

from .models import Task, TaskPriority, TaskStatus, _normalize_to_utc


class InMemoryTaskStorage:
    """In-memory storage for tasks with thread-safe operations."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create(
        self,
        title: str,
        description: str,
        priority: TaskPriority,
        status: TaskStatus,
        due_at: datetime | None = None,
    ) -> Task:
        now = datetime.now(UTC)
        normalized_due_at = _normalize_to_utc(due_at) if due_at is not None else None
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            priority=priority,
            status=status,
            created_at=now,
            updated_at=now,
            due_at=normalized_due_at,
        )
        self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        search: str | None = None,
    ) -> list[Task]:
        tasks = list(self._tasks.values())

        if status is not None:
            tasks = [t for t in tasks if t.status == status]

        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]

        if search is not None:
            search_lower = search.lower()
            tasks = [
                t
                for t in tasks
                if search_lower in t.title.lower() or search_lower in t.description.lower()
            ]

        _STATUS_ORDER = {"todo": 0, "in_progress": 1, "done": 2}
        _PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2}
        tasks.sort(key=lambda t: (_STATUS_ORDER.get(t.status.value, 99), _PRIORITY_ORDER.get(t.priority.value, 99), t.created_at))
        return tasks

    def update(
        self,
        task_id: str,
        title: str | None = None,
        description: str | None = None,
        priority: TaskPriority | None = None,
        status: TaskStatus | None = None,
    ) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if status is not None:
            task.status = status
        task.updated_at = datetime.now(UTC)
        return task

    def delete(self, task_id: str) -> Task | None:
        return self._tasks.pop(task_id, None)

    def get_all(self) -> dict[str, Task]:
        return dict(self._tasks)


_default_storage = InMemoryTaskStorage()


def get_storage() -> InMemoryTaskStorage:
    """Return the default task storage instance."""
    return _default_storage
