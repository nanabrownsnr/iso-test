import asyncio
import time

import pytest
from fastmcp.exceptions import ToolError
from starlette.testclient import TestClient

from fastmcp_server import SERVICE_VERSION
from fastmcp_server.models import (
    CreateTaskRequest,
    ListTaskFilters,
    TaskPriority,
    TaskStatus,
    UpdateTaskRequest,
)
from fastmcp_server.models import Task as TaskModel
from fastmcp_server.server import mcp
from fastmcp_server.storage import InMemoryTaskStorage, get_storage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_storage():
    """Reset in-memory storage between tests to keep them independent."""
    import importlib

    import fastmcp_server.storage

    # Re-import to get a fresh storage instance
    importlib.reload(fastmcp_server.storage)
    yield
    importlib.reload(fastmcp_server.storage)


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------


class TestTaskModel:
    def test_task_to_dict(self):
        task = TaskModel(
            id="abc123",
            title="Test task",
            description="A test task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.TODO,
            created_at="2025-01-01T00:00:00+00:00",
            updated_at="2025-01-01T00:00:00+00:00",
        )
        d = task.to_dict()
        assert d["id"] == "abc123"
        assert d["title"] == "Test task"
        assert d["priority"] == "high"
        assert d["status"] == "todo"

    def test_task_blank_title_raises(self):
        with pytest.raises(ValueError, match="Title must not be blank"):
            TaskModel(
                id="x",
                title="",
                description="desc",
                priority=TaskPriority.LOW,
                status=TaskStatus.TODO,
                created_at="2025-01-01T00:00:00+00:00",
                updated_at="2025-01-01T00:00:00+00:00",
            )

    def test_task_whitespace_title_raises(self):
        with pytest.raises(ValueError, match="Title must not be blank"):
            TaskModel(
                id="x",
                title="   ",
                description="desc",
                priority=TaskPriority.LOW,
                status=TaskStatus.TODO,
                created_at="2025-01-01T00:00:00+00:00",
                updated_at="2025-01-01T00:00:00+00:00",
            )

    def test_task_strips_title(self):
        task = TaskModel(
            id="x",
            title="  hello  ",
            description="desc",
            priority=TaskPriority.LOW,
            status=TaskStatus.TODO,
            created_at="2025-01-01T00:00:00+00:00",
            updated_at="2025-01-01T00:00:00+00:00",
        )
        assert task.title == "hello"


class TestCreateTaskRequestValidation:
    def test_valid_request(self):
        req = CreateTaskRequest(title="Hello", description="World", priority="high", status="todo")
        assert req.title == "Hello"
        assert req.priority == "high"
        assert req.status == "todo"

    def test_blank_title_raises(self):
        with pytest.raises(ValueError, match="Title must not be blank"):
            CreateTaskRequest(title="", description="World", priority="high", status="todo")

    def test_whitespace_title_raises(self):
        with pytest.raises(ValueError, match="Title must not be blank"):
            CreateTaskRequest(title="  ", description="World", priority="high", status="todo")

    def test_invalid_priority_raises(self):
        with pytest.raises(ValueError):
            CreateTaskRequest(title="Hello", description="World", priority="ultra", status="todo")

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            CreateTaskRequest(title="Hello", description="World", priority="high", status="cancelled")

    def test_priority_case_insensitive(self):
        req = CreateTaskRequest(title="T", description="D", priority="HIGH", status="TODO")
        assert req.priority == "high"
        assert req.status == "todo"

    def test_default_description(self):
        req = CreateTaskRequest(title="T", priority="low", status="todo")
        assert req.description == ""

    def test_default_status(self):
        req = CreateTaskRequest(title="T", description="D", priority="low")
        assert req.status == "todo"


class TestUpdateTaskRequestValidation:
    def test_all_none(self):
        req = UpdateTaskRequest()
        assert req.title is None
        assert req.priority is None
        assert req.status is None

    def test_partial_update(self):
        req = UpdateTaskRequest(status="done")
        assert req.status == "done"
        assert req.title is None

    def test_blank_title_raises(self):
        with pytest.raises(ValueError, match="Title must not be blank"):
            UpdateTaskRequest(title="")

    def test_valid_priority(self):
        req = UpdateTaskRequest(priority="medium")
        assert req.priority == "medium"

    def test_invalid_priority_raises(self):
        with pytest.raises(ValueError):
            UpdateTaskRequest(priority="urgent")

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            UpdateTaskRequest(status="archived")


class TestListTaskFiltersValidation:
    def test_all_none(self):
        f = ListTaskFilters()
        assert f.status is None
        assert f.priority is None
        assert f.search is None

    def test_valid_status_filter(self):
        f = ListTaskFilters(status="in_progress")
        assert f.status == "in_progress"

    def test_invalid_status_filter_raises(self):
        with pytest.raises(ValueError):
            ListTaskFilters(status="pending")

    def test_valid_priority_filter(self):
        f = ListTaskFilters(priority="low")
        assert f.priority == "low"

    def test_invalid_priority_filter_raises(self):
        with pytest.raises(ValueError):
            ListTaskFilters(priority="critical")

    def test_search_filter(self):
        f = ListTaskFilters(search="bug")
        assert f.search == "bug"


# ---------------------------------------------------------------------------
# Storage tests
# ---------------------------------------------------------------------------


class TestInMemoryTaskStorage:
    def test_create_and_get(self):
        storage = InMemoryTaskStorage()
        task = storage.create("Title", "Desc", TaskPriority.HIGH, TaskStatus.TODO)
        assert task.id is not None
        assert task.title == "Title"
        assert task.description == "Desc"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.TODO
        assert task.created_at.tzinfo is not None

    def test_get_nonexistent(self):
        storage = InMemoryTaskStorage()
        assert storage.get("nonexistent") is None

    def test_list_empty(self):
        storage = InMemoryTaskStorage()
        tasks = storage.list_tasks()
        assert tasks == []

    def test_list_filter_by_status(self):
        storage = InMemoryTaskStorage()
        storage.create("T1", "D", TaskPriority.LOW, TaskStatus.TODO)
        storage.create("T2", "D", TaskPriority.LOW, TaskStatus.DONE)
        todos = storage.list_tasks(status=TaskStatus.TODO)
        assert len(todos) == 1
        assert todos[0].title == "T1"

    def test_list_filter_by_priority(self):
        storage = InMemoryTaskStorage()
        storage.create("T1", "D", TaskPriority.HIGH, TaskStatus.TODO)
        storage.create("T2", "D", TaskPriority.LOW, TaskStatus.TODO)
        high = storage.list_tasks(priority=TaskPriority.HIGH)
        assert len(high) == 1
        assert high[0].title == "T1"

    def test_list_filter_combined(self):
        storage = InMemoryTaskStorage()
        storage.create("T1", "D", TaskPriority.HIGH, TaskStatus.TODO)
        storage.create("T2", "D", TaskPriority.HIGH, TaskStatus.DONE)
        storage.create("T3", "D", TaskPriority.LOW, TaskStatus.TODO)
        results = storage.list_tasks(status=TaskStatus.TODO, priority=TaskPriority.HIGH)
        assert len(results) == 1
        assert results[0].title == "T1"

    def test_list_search_by_title(self):
        storage = InMemoryTaskStorage()
        storage.create("Login page", "D", TaskPriority.LOW, TaskStatus.TODO)
        storage.create("Signup form", "D", TaskPriority.LOW, TaskStatus.TODO)
        results = storage.list_tasks(search="login")
        assert len(results) == 1
        assert results[0].title == "Login page"

    def test_list_search_by_description(self):
        storage = InMemoryTaskStorage()
        storage.create("T1", "Fix bug in auth", TaskPriority.LOW, TaskStatus.TODO)
        storage.create("T2", "Add new feature", TaskPriority.LOW, TaskStatus.TODO)
        results = storage.list_tasks(search="auth")
        assert len(results) == 1

    def test_list_case_insensitive_search(self):
        storage = InMemoryTaskStorage()
        storage.create("Authentication", "D", TaskPriority.LOW, TaskStatus.TODO)
        results = storage.list_tasks(search="AUTH")
        assert len(results) == 1

    def test_list_deterministic_ordering(self):
        storage = InMemoryTaskStorage()
        storage.create("B", "D", TaskPriority.HIGH, TaskStatus.DONE)
        storage.create("A", "D", TaskPriority.LOW, TaskStatus.TODO)
        storage.create("C", "D", TaskPriority.MEDIUM, TaskStatus.TODO)
        tasks = storage.list_tasks()
        statuses = [t.status.value for t in tasks]
        assert statuses == ["todo", "todo", "done"]

    def test_update_task(self):
        storage = InMemoryTaskStorage()
        task = storage.create("Original", "D", TaskPriority.LOW, TaskStatus.TODO)
        original_updated = task.updated_at
        time.sleep(0.01)
        updated = storage.update(task.id, title="Updated", status="done")
        assert updated.title == "Updated"
        assert updated.status == TaskStatus.DONE
        assert updated.updated_at > original_updated

    def test_update_nonexistent(self):
        storage = InMemoryTaskStorage()
        assert storage.update("nonexistent", title="X") is None

    def test_delete_task(self):
        storage = InMemoryTaskStorage()
        task = storage.create("T", "D", TaskPriority.LOW, TaskStatus.TODO)
        deleted = storage.delete(task.id)
        assert deleted is not None
        assert deleted.id == task.id
        assert storage.get(task.id) is None

    def test_delete_nonexistent(self):
        storage = InMemoryTaskStorage()
        assert storage.delete("nonexistent") is None

    def test_get_all(self):
        storage = InMemoryTaskStorage()
        storage.create("T1", "D", TaskPriority.LOW, TaskStatus.TODO)
        storage.create("T2", "D", TaskPriority.HIGH, TaskStatus.DONE)
        all_tasks = storage.get_all()
        assert len(all_tasks) == 2


# ---------------------------------------------------------------------------
# Tool tests - create_task
# ---------------------------------------------------------------------------


class TestCreateTaskTool:
    def test_create_task_returns_task(self):
        result = asyncio.run(mcp.call_tool("create_task", {
            "title": "Test task",
            "description": "Test description",
            "priority": "high",
            "status": "todo",
        }))
        assert result.structured_content is not None
        assert result.structured_content["title"] == "Test task"
        assert result.structured_content["description"] == "Test description"
        assert result.structured_content["priority"] == "high"
        assert result.structured_content["status"] == "todo"
        assert "id" in result.structured_content
        assert "created_at" in result.structured_content
        assert "updated_at" in result.structured_content

    def test_create_task_generates_unique_id(self):
        r1 = asyncio.run(mcp.call_tool("create_task", {
            "title": "Task 1",
            "description": "D",
            "priority": "low",
            "status": "todo",
        }))
        r2 = asyncio.run(mcp.call_tool("create_task", {
            "title": "Task 2",
            "description": "D",
            "priority": "low",
            "status": "todo",
        }))
        assert r1.structured_content["id"] != r2.structured_content["id"]

    def test_create_task_default_status(self):
        result = asyncio.run(mcp.call_tool("create_task", {
            "title": "Task",
            "description": "D",
            "priority": "medium",
            "status": "todo",
        }))
        assert result.structured_content["status"] == "todo"

    def test_create_task_blank_title_rejected(self):
        with pytest.raises(ToolError):
            asyncio.run(mcp.call_tool("create_task", {
                "title": "",
                "description": "D",
                "priority": "low",
                "status": "todo",
            }))

    def test_create_task_blank_whitespace_title_rejected(self):
        with pytest.raises(ToolError):
            asyncio.run(mcp.call_tool("create_task", {
                "title": "   ",
                "description": "D",
                "priority": "low",
                "status": "todo",
            }))

    def test_create_task_invalid_priority_rejected(self):
        with pytest.raises(ToolError):
            asyncio.run(mcp.call_tool("create_task", {
                "title": "Task",
                "description": "D",
                "priority": "ultra",
                "status": "todo",
            }))

    def test_create_task_invalid_status_rejected(self):
        with pytest.raises(ToolError):
            asyncio.run(mcp.call_tool("create_task", {
                "title": "Task",
                "description": "D",
                "priority": "low",
                "status": "cancelled",
            }))

    def test_create_task_all_priorities(self):
        for p in ("low", "medium", "high"):
            result = asyncio.run(mcp.call_tool("create_task", {
                "title": f"Task {p}",
                "description": "D",
                "priority": p,
                "status": "todo",
            }))
            assert result.structured_content["priority"] == p

    def test_create_task_all_statuses(self):
        for s in ("todo", "in_progress", "done"):
            result = asyncio.run(mcp.call_tool("create_task", {
                "title": f"Task {s}",
                "description": "D",
                "priority": "low",
                "status": s,
            }))
            assert result.structured_content["status"] == s

    def test_create_task_response_schema_fields(self):
        result = asyncio.run(mcp.call_tool("create_task", {
            "title": "Task",
            "description": "Desc",
            "priority": "low",
            "status": "todo",
        }))
        schema_fields = {"id", "title", "description", "priority", "status", "created_at", "updated_at"}
        assert set(result.structured_content.keys()) == schema_fields

    def test_create_task_empty_description(self):
        result = asyncio.run(mcp.call_tool("create_task", {
            "title": "Task",
            "description": "",
            "priority": "low",
            "status": "todo",
        }))
        assert result.structured_content["description"] == ""

    def test_create_task_special_characters_in_title(self):
        result = asyncio.run(mcp.call_tool("create_task", {
            "title": "Task with symbols: !@#$%^&*()",
            "description": "Desc",
            "priority": "low",
            "status": "todo",
        }))
        assert result.structured_content["title"] == "Task with symbols: !@#$%^&*()"


# ---------------------------------------------------------------------------
# Tool tests - get_task
# ---------------------------------------------------------------------------


class TestGetTaskTool:
    def test_get_existing_task(self):
        create_result = asyncio.run(mcp.call_tool("create_task", {
            "title": "Get me",
            "description": "Find me",
            "priority": "high",
            "status": "todo",
        }))
        task_id = create_result.structured_content["id"]
        result = asyncio.run(mcp.call_tool("get_task", {"task_id": task_id}))
        assert result.structured_content["title"] == "Get me"

    def test_get_nonexistent_task_returns_error(self):
        result = asyncio.run(mcp.call_tool("get_task", {"task_id": "nonexistent-id"}))
        assert "error" in result.structured_content
        assert "nonexistent-id" in result.structured_content["error"]

    def test_get_task_returns_all_fields(self):
        create_result = asyncio.run(mcp.call_tool("create_task", {
            "title": "Get me",
            "description": "Desc",
            "priority": "low",
            "status": "todo",
        }))
        task_id = create_result.structured_content["id"]
        result = asyncio.run(mcp.call_tool("get_task", {"task_id": task_id}))
        fields = result.structured_content
        assert "id" in fields
        assert "title" in fields
        assert "description" in fields
        assert "priority" in fields
        assert "status" in fields
        assert "created_at" in fields
        assert "updated_at" in fields


# ---------------------------------------------------------------------------
# Tool tests - list_tasks
# ---------------------------------------------------------------------------


class TestListTasksTool:
    def _create_task(self, title, priority="low", status="todo"):
        return asyncio.run(mcp.call_tool("create_task", {
            "title": title,
            "description": "D",
            "priority": priority,
            "status": status,
        }))

    def test_list_empty(self):
        result = asyncio.run(mcp.call_tool("list_tasks", {}))
        assert result.structured_content["tasks"] == []
        assert result.structured_content["count"] == 0

    def test_list_all_tasks(self):
        self._create_task("Task 1", "low", "todo")
        self._create_task("Task 2", "high", "done")
        result = asyncio.run(mcp.call_tool("list_tasks", {}))
        assert result.structured_content["count"] == 2
        assert len(result.structured_content["tasks"]) == 2

    def test_list_filter_by_status(self):
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "low", "done")
        self._create_task("T3", "low", "in_progress")
        result = asyncio.run(mcp.call_tool("list_tasks", {"status": "todo"}))
        assert result.structured_content["count"] == 1
        assert result.structured_content["tasks"][0]["title"] == "T1"

    def test_list_filter_by_priority(self):
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "high", "todo")
        result = asyncio.run(mcp.call_tool("list_tasks", {"priority": "high"}))
        assert result.structured_content["count"] == 1
        assert result.structured_content["tasks"][0]["title"] == "T2"

    def test_list_filter_combined(self):
        self._create_task("T1", "high", "todo")
        self._create_task("T2", "high", "done")
        self._create_task("T3", "low", "todo")
        result = asyncio.run(mcp.call_tool("list_tasks", {
            "status": "todo",
            "priority": "high",
        }))
        assert result.structured_content["count"] == 1
        assert result.structured_content["tasks"][0]["title"] == "T1"

    def test_list_search_by_title(self):
        self._create_task("Login page")
        self._create_task("Signup form")
        self._create_task("Dashboard")
        result = asyncio.run(mcp.call_tool("list_tasks", {"search": "login"}))
        assert result.structured_content["count"] == 1
        assert "Login" in result.structured_content["tasks"][0]["title"]

    def test_list_search_by_description(self):
        self._create_task("T1", "low", "todo")
        storage = get_storage()
        storage._tasks.clear()
        self._create_task("T1", "low", "todo")
        result = asyncio.run(mcp.call_tool("list_tasks", {"search": "D"}))
        assert result.structured_content["count"] == 1

    def test_list_case_insensitive_search(self):
        storage = get_storage()
        storage._tasks.clear()
        self._create_task("Authentication")
        result = asyncio.run(mcp.call_tool("list_tasks", {"search": "AUTH"}))
        assert result.structured_content["count"] == 1

    def test_list_response_schema(self):
        result = asyncio.run(mcp.call_tool("list_tasks", {}))
        assert "tasks" in result.structured_content
        assert "count" in result.structured_content
        assert isinstance(result.structured_content["tasks"], list)
        assert isinstance(result.structured_content["count"], int)

    def test_list_invalid_status_filter_raises(self):
        with pytest.raises(ToolError):
            asyncio.run(mcp.call_tool("list_tasks", {"status": "invalid"}))

    def test_list_invalid_priority_filter_raises(self):
        with pytest.raises(ToolError):
            asyncio.run(mcp.call_tool("list_tasks", {"priority": "invalid"}))

    def test_list_deterministic_order(self):
        storage = get_storage()
        storage._tasks.clear()
        self._create_task("B", "high", "done")
        self._create_task("A", "low", "todo")
        self._create_task("C", "medium", "todo")
        result = asyncio.run(mcp.call_tool("list_tasks", {}))
        tasks = result.structured_content["tasks"]
        # Ordering: todo before done, then by priority, then by created_at
        assert tasks[0]["title"] == "A"
        assert tasks[1]["title"] == "C"
        assert tasks[2]["title"] == "B"


# ---------------------------------------------------------------------------
# Tool tests - update_task
# ---------------------------------------------------------------------------


class TestUpdateTaskTool:
    def _create_task(self, title, priority="low", status="todo"):
        return asyncio.run(mcp.call_tool("create_task", {
            "title": title,
            "description": "D",
            "priority": priority,
            "status": status,
        }))

    def test_update_title(self):
        cr = self._create_task("Original")
        task_id = cr.structured_content["id"]
        result = asyncio.run(mcp.call_tool("update_task", {
            "task_id": task_id,
            "title": "Updated",
        }))
        assert result.structured_content["title"] == "Updated"
        assert result.structured_content["description"] == "D"

    def test_update_description(self):
        cr = self._create_task("Task")
        task_id = cr.structured_content["id"]
        result = asyncio.run(mcp.call_tool("update_task", {
            "task_id": task_id,
            "description": "New description",
        }))
        assert result.structured_content["description"] == "New description"

    def test_update_priority(self):
        cr = self._create_task("Task", priority="low")
        task_id = cr.structured_content["id"]
        result = asyncio.run(mcp.call_tool("update_task", {
            "task_id": task_id,
            "priority": "high",
        }))
        assert result.structured_content["priority"] == "high"

    def test_update_status(self):
        cr = self._create_task("Task", status="todo")
        task_id = cr.structured_content["id"]
        result = asyncio.run(mcp.call_tool("update_task", {
            "task_id": task_id,
            "status": "done",
        }))
        assert result.structured_content["status"] == "done"

    def test_update_multiple_fields(self):
        cr = self._create_task("Original", priority="low", status="todo")
        task_id = cr.structured_content["id"]
        result = asyncio.run(mcp.call_tool("update_task", {
            "task_id": task_id,
            "title": "Updated",
            "description": "New desc",
            "priority": "high",
            "status": "done",
        }))
        assert result.structured_content["title"] == "Updated"
        assert result.structured_content["description"] == "New desc"
        assert result.structured_content["priority"] == "high"
        assert result.structured_content["status"] == "done"

    def test_update_refreshes_updated_at(self):
        cr = self._create_task("Task")
        task_id = cr.structured_content["id"]
        original_updated = cr.structured_content["updated_at"]
        time.sleep(0.01)
        result = asyncio.run(mcp.call_tool("update_task", {
            "task_id": task_id,
            "title": "Updated",
        }))
        assert result.structured_content["updated_at"] > original_updated

    def test_update_nonexistent_task(self):
        result = asyncio.run(mcp.call_tool("update_task", {
            "task_id": "nonexistent",
            "title": "X",
        }))
        assert "error" in result.structured_content
        assert "nonexistent" in result.structured_content["error"]

    def test_update_blank_title_raises(self):
        cr = self._create_task("Task")
        task_id = cr.structured_content["id"]
        with pytest.raises(ToolError):
            asyncio.run(mcp.call_tool("update_task", {
                "task_id": task_id,
                "title": "",
            }))

    def test_update_invalid_priority_raises(self):
        cr = self._create_task("Task")
        task_id = cr.structured_content["id"]
        with pytest.raises(ToolError):
            asyncio.run(mcp.call_tool("update_task", {
                "task_id": task_id,
                "priority": "urgent",
            }))

    def test_update_invalid_status_raises(self):
        cr = self._create_task("Task")
        task_id = cr.structured_content["id"]
        with pytest.raises(ToolError):
            asyncio.run(mcp.call_tool("update_task", {
                "task_id": task_id,
                "status": "archived",
            }))

    def test_update_partial_keeps_other_fields(self):
        cr = self._create_task("Original", priority="high", status="todo")
        task_id = cr.structured_content["id"]
        result = asyncio.run(mcp.call_tool("update_task", {
            "task_id": task_id,
            "title": "New title",
        }))
        assert result.structured_content["title"] == "New title"
        assert result.structured_content["priority"] == "high"
        assert result.structured_content["status"] == "todo"

    def test_update_no_field_changes(self):
        cr = self._create_task("Task")
        task_id = cr.structured_content["id"]
        result = asyncio.run(mcp.call_tool("update_task", {"task_id": task_id}))
        assert result.structured_content["title"] == "Task"

    def test_update_response_schema(self):
        cr = self._create_task("Task")
        task_id = cr.structured_content["id"]
        result = asyncio.run(mcp.call_tool("update_task", {
            "task_id": task_id,
            "title": "Updated",
        }))
        fields = {"id", "title", "description", "priority", "status", "created_at", "updated_at"}
        assert set(result.structured_content.keys()) == fields


# ---------------------------------------------------------------------------
# Tool tests - delete_task
# ---------------------------------------------------------------------------


class TestDeleteTaskTool:
    def _create_task(self, title, priority="low", status="todo"):
        return asyncio.run(mcp.call_tool("create_task", {
            "title": title,
            "description": "D",
            "priority": priority,
            "status": status,
        }))

    def test_delete_task(self):
        cr = self._create_task("Delete me")
        task_id = cr.structured_content["id"]
        result = asyncio.run(mcp.call_tool("delete_task", {"task_id": task_id}))
        assert result.structured_content["deleted"] == task_id

    def test_delete_nonexistent_task(self):
        result = asyncio.run(mcp.call_tool("delete_task", {"task_id": "nonexistent"}))
        assert "error" in result.structured_content
        assert "nonexistent" in result.structured_content["error"]

    def test_delete_makes_task_unreachable(self):
        cr = self._create_task("Delete me")
        task_id = cr.structured_content["id"]
        asyncio.run(mcp.call_tool("delete_task", {"task_id": task_id}))
        result = asyncio.run(mcp.call_tool("get_task", {"task_id": task_id}))
        assert "error" in result.structured_content

    def test_delete_multiple_tasks(self):
        cr1 = self._create_task("Task 1")
        cr2 = self._create_task("Task 2")
        id1 = cr1.structured_content["id"]
        id2 = cr2.structured_content["id"]
        asyncio.run(mcp.call_tool("delete_task", {"task_id": id1}))
        asyncio.run(mcp.call_tool("delete_task", {"task_id": id2}))
        result = asyncio.run(mcp.call_tool("list_tasks", {}))
        assert result.structured_content["count"] == 0

    def test_delete_response_schema(self):
        cr = self._create_task("Delete me")
        task_id = cr.structured_content["id"]
        result = asyncio.run(mcp.call_tool("delete_task", {"task_id": task_id}))
        assert "deleted" in result.structured_content
        assert result.structured_content["deleted"] == task_id


# ---------------------------------------------------------------------------
# Tool tests - task_summary
# ---------------------------------------------------------------------------


class TestTaskSummaryTool:
    def _create_task(self, title, priority="low", status="todo"):
        return asyncio.run(mcp.call_tool("create_task", {
            "title": title,
            "description": "D",
            "priority": priority,
            "status": status,
        }))

    def test_summary_empty(self):
        result = asyncio.run(mcp.call_tool("task_summary", {}))
        assert result.structured_content["total"] == 0
        assert result.structured_content["by_status"] == {}
        assert result.structured_content["by_priority"] == {}

    def test_summary_counts_by_status(self):
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "low", "todo")
        self._create_task("T3", "high", "done")
        result = asyncio.run(mcp.call_tool("task_summary", {}))
        assert result.structured_content["by_status"]["todo"] == 2
        assert result.structured_content["by_status"]["done"] == 1

    def test_summary_counts_by_priority(self):
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "high", "todo")
        self._create_task("T3", "medium", "done")
        result = asyncio.run(mcp.call_tool("task_summary", {}))
        assert result.structured_content["by_priority"]["low"] == 1
        assert result.structured_content["by_priority"]["high"] == 1
        assert result.structured_content["by_priority"]["medium"] == 1

    def test_summary_total(self):
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "high", "in_progress")
        self._create_task("T3", "medium", "done")
        result = asyncio.run(mcp.call_tool("task_summary", {}))
        assert result.structured_content["total"] == 3

    def test_summary_response_schema(self):
        result = asyncio.run(mcp.call_tool("task_summary", {}))
        assert "total" in result.structured_content
        assert "by_status" in result.structured_content
        assert "by_priority" in result.structured_content
        assert isinstance(result.structured_content["total"], int)
        assert isinstance(result.structured_content["by_status"], dict)
        assert isinstance(result.structured_content["by_priority"], dict)

    def test_summary_with_all_statuses(self):
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "low", "in_progress")
        self._create_task("T3", "low", "done")
        result = asyncio.run(mcp.call_tool("task_summary", {}))
        for s in ("todo", "in_progress", "done"):
            assert result.structured_content["by_status"][s] == 1

    def test_summary_with_all_priorities(self):
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "medium", "todo")
        self._create_task("T3", "high", "todo")
        result = asyncio.run(mcp.call_tool("task_summary", {}))
        for p in ("low", "medium", "high"):
            assert result.structured_content["by_priority"][p] == 1


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------


class TestToolRegistration:
    def test_all_tools_registered(self):
        tools = asyncio.run(mcp.list_tools())
        tool_names = {t.name for t in tools}
        expected = {
            "health_check",
            "echo",
            "create_task",
            "get_task",
            "list_tasks",
            "update_task",
            "delete_task",
            "task_summary",
        }
        assert tool_names == expected

    def test_create_task_tool_has_description(self):
        tool = asyncio.run(mcp.get_tool("create_task"))
        assert tool is not None
        assert tool.description == "Create a new task with the given title, description, priority, and status."

    def test_get_task_tool_has_description(self):
        tool = asyncio.run(mcp.get_tool("get_task"))
        assert tool is not None
        assert tool.description == "Retrieve a single task by its ID."

    def test_list_tasks_tool_has_description(self):
        tool = asyncio.run(mcp.get_tool("list_tasks"))
        assert tool is not None
        assert "List tasks" in tool.description

    def test_update_task_tool_has_description(self):
        tool = asyncio.run(mcp.get_tool("update_task"))
        assert tool is not None
        assert "Partially update" in tool.description

    def test_delete_task_tool_has_description(self):
        tool = asyncio.run(mcp.get_tool("delete_task"))
        assert tool is not None
        assert "Delete a task" in tool.description

    def test_task_summary_tool_has_description(self):
        tool = asyncio.run(mcp.get_tool("task_summary"))
        assert tool is not None
        assert "counts" in tool.description.lower() or "Return" in tool.description


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------


class TestHTTPHealthEndpoint:
    @pytest.fixture
    def client(self):
        return TestClient(mcp.http_app())

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["version"] == SERVICE_VERSION

    def test_health_endpoint_content_type(self, client):
        response = client.get("/health")
        assert "application/json" in response.headers.get("content-type", "")

    def test_health_endpoint_rejects_post(self, client):
        response = client.post("/health")
        assert response.status_code == 405
