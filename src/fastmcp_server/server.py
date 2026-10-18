from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .models import (
    CreateTaskRequest,
    ListTaskFilters,
    TaskPriority,
    TaskStatus,
    UpdateTaskRequest,
)
from .storage import get_storage

mcp = FastMCP(name="fastmcp-server")


# ---------------------------------------------------------------------------
# Existing tools (preserved for backward compatibility)
# ---------------------------------------------------------------------------

@mcp.tool()
async def health_check() -> dict:
    """Return the health status of the server."""
    return {"status": "ok"}


@mcp.tool()
async def echo(message: str) -> dict:
    """Echo back the provided message."""
    return {"echo": message}


# ---------------------------------------------------------------------------
# HTTP health check endpoint
# ---------------------------------------------------------------------------

@mcp.custom_route("/health", methods=["GET"])
async def health_endpoint(request: Request) -> JSONResponse:
    """HTTP health check endpoint."""
    return JSONResponse(content={"status": "ok"})


# ---------------------------------------------------------------------------
# Task management tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def create_task(title: str, description: str, priority: str, status: str) -> dict:
    """Create a new task with the given title, description, priority, and status.

    Args:
        title: Task title (must not be blank).
        description: Task description.
        priority: Task priority – one of ``low``, ``medium``, ``high``.
        status: Task status – one of ``todo``, ``in_progress``, ``done``.

    Returns:
        The created task with all fields including generated ``id`` and timestamps.
    """
    # Validate via Pydantic model
    request = CreateTaskRequest(title=title, description=description, priority=priority, status=status)

    storage = get_storage()
    task = storage.create(
        title=request.title,
        description=request.description,
        priority=TaskPriority(request.priority),
        status=TaskStatus(request.status),
    )
    return task.to_dict()


@mcp.tool()
async def get_task(task_id: str) -> dict:
    """Retrieve a single task by its ID.

    Args:
        task_id: The unique identifier of the task.

    Returns:
        The task details or an error if not found.
    """
    storage = get_storage()
    task = storage.get(task_id)
    if task is None:
        return {"error": f"Task not found: {task_id}"}
    return task.to_dict()


@mcp.tool()
async def list_tasks(status: str | None = None, priority: str | None = None, search: str | None = None) -> dict:
    """List tasks with optional filtering and deterministic ordering.

    Args:
        status: Filter by status (todo, in_progress, done).
        priority: Filter by priority (low, medium, high).
        search: Search by title or description (case-insensitive).

    Returns:
        A dict with ``tasks`` (list) and ``count`` (int).
    """
    filters = ListTaskFilters(status=status, priority=priority, search=search)

    status_filter = TaskStatus(filters.status) if filters.status else None
    priority_filter = TaskPriority(filters.priority) if filters.priority else None

    storage = get_storage()
    tasks = storage.list_tasks(
        status=status_filter,
        priority=priority_filter,
        search=filters.search,
    )
    return {
        "tasks": [t.to_dict() for t in tasks],
        "count": len(tasks),
    }


@mcp.tool()
async def update_task(
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> dict:
    """Partially update a task and refresh its ``updated_at`` timestamp.

    Args:
        task_id: The unique identifier of the task.
        title: Updated title (must not be blank if provided).
        description: Updated description.
        priority: Updated priority (low, medium, high).
        status: Updated status (todo, in_progress, done).

    Returns:
        The updated task, or an error if not found.
    """
    # Validate optional fields via Pydantic model
    update = UpdateTaskRequest(
        title=title,
        description=description,
        priority=priority,
        status=status,
    )

    storage = get_storage()
    task = storage.get(task_id)
    if task is None:
        return {"error": f"Task not found: {task_id}"}

    updated = storage.update(
        task_id=task_id,
        title=update.title if update.title is not None else None,
        description=update.description if update.description is not None else None,
        priority=TaskPriority(update.priority) if update.priority is not None else None,
        status=TaskStatus(update.status) if update.status is not None else None,
    )

    if updated is None:
        return {"error": f"Task not found: {task_id}"}
    return updated.to_dict()


@mcp.tool()
async def delete_task(task_id: str) -> dict:
    """Delete a task by its ID.

    Args:
        task_id: The unique identifier of the task.

    Returns:
        The deleted task ID, or an error if not found.
    """
    storage = get_storage()
    task = storage.delete(task_id)
    if task is None:
        return {"error": f"Task not found: {task_id}"}
    return {"deleted": task_id}


@mcp.tool()
async def task_summary() -> dict:
    """Return counts of tasks grouped by status and priority.

    Returns:
        A dict with ``by_status`` and ``by_priority`` counts, plus ``total``.
    """
    storage = get_storage()
    all_tasks = storage.get_all()

    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}

    for task in all_tasks.values():
        status_key = task.status.value
        priority_key = task.priority.value
        by_status[status_key] = by_status.get(status_key, 0) + 1
        by_priority[priority_key] = by_priority.get(priority_key, 0) + 1

    return {
        "total": len(all_tasks),
        "by_status": by_status,
        "by_priority": by_priority,
    }


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

def main() -> None:
    mcp.run(transport="http")


if __name__ == "__main__":
    main()
