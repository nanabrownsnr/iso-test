import pytest
from starlette.testclient import TestClient

from fastmcp_server.server import mcp
from fastmcp_server.storage import get_storage


@pytest.fixture
def client():
    """Create a test client for the MCP server HTTP endpoints."""
    return TestClient(mcp.http_app())


class TestHTTPHealthEndpoint:
    def test_health_endpoint_status_code(self, client):
        """Test HTTP health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_response_body(self, client):
        """Test HTTP health endpoint returns correct JSON body."""
        response = client.get("/health")
        assert response.json() == {"status": "ok"}

    def test_health_endpoint_content_type(self, client):
        """Test HTTP health endpoint returns application/json content type."""
        response = client.get("/health")
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_health_endpoint_method_not_allowed(self, client):
        """Test HTTP health endpoint rejects non-GET methods."""
        response = client.post("/health")
        assert response.status_code == 405

    def test_health_endpoint_put_method_not_allowed(self, client):
        """Test HTTP health endpoint rejects PUT method."""
        response = client.put("/health")
        assert response.status_code == 405

    def test_health_endpoint_delete_method_not_allowed(self, client):
        """Test HTTP health endpoint rejects DELETE method."""
        response = client.delete("/health")
        assert response.status_code == 405

    def test_unknown_route_returns_404(self, client):
        """Test that unknown routes return 404."""
        response = client.get("/unknown")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Task count endpoint tests
# ---------------------------------------------------------------------------


class TestTaskCountEndpoint:
    @pytest.fixture
    def client(self):
        return TestClient(mcp.http_app())

    def _clear_storage(self):
        get_storage()._tasks.clear()

    def test_count_empty(self, client):
        """Test count endpoint returns 0 when no tasks exist."""
        self._clear_storage()
        response = client.get("/api/v1/tasks/count")
        assert response.status_code == 200
        assert response.json() == {"count": 0}

    def test_count_returns_int(self, client):
        """Test count endpoint returns an integer value."""
        self._clear_storage()
        response = client.get("/api/v1/tasks/count")
        assert isinstance(response.json()["count"], int)

    def test_count_with_one_task(self, client):
        """Test count endpoint returns 1 after creating one task."""
        self._clear_storage()
        from fastmcp_server.models import TaskPriority, TaskStatus
        get_storage().create("Task 1", "Description", TaskPriority.LOW, TaskStatus.TODO)
        response = client.get("/api/v1/tasks/count")
        assert response.status_code == 200
        assert response.json() == {"count": 1}

    def test_count_with_multiple_tasks(self, client):
        """Test count endpoint returns correct count with multiple tasks."""
        self._clear_storage()
        from fastmcp_server.models import TaskPriority, TaskStatus
        get_storage().create("Task 1", "D1", TaskPriority.LOW, TaskStatus.TODO)
        get_storage().create("Task 2", "D2", TaskPriority.HIGH, TaskStatus.DONE)
        get_storage().create("Task 3", "D3", TaskPriority.MEDIUM, TaskStatus.IN_PROGRESS)
        response = client.get("/api/v1/tasks/count")
        assert response.status_code == 200
        assert response.json() == {"count": 3}

    def test_count_reflects_deletions(self, client):
        """Test count decreases after deleting tasks."""
        self._clear_storage()
        from fastmcp_server.models import TaskPriority, TaskStatus
        get_storage().create("Task 1", "D1", TaskPriority.LOW, TaskStatus.TODO)
        get_storage().create("Task 2", "D2", TaskPriority.HIGH, TaskStatus.DONE)
        response = client.get("/api/v1/tasks/count")
        assert response.json()["count"] == 2
        get_storage().delete(next(iter(get_storage()._tasks.keys())))
        response = client.get("/api/v1/tasks/count")
        assert response.json()["count"] == 1

    def test_count_content_type(self, client):
        """Test count endpoint returns application/json content type."""
        self._clear_storage()
        response = client.get("/api/v1/tasks/count")
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_count_rejects_non_get(self, client):
        """Test count endpoint rejects non-GET methods."""
        self._clear_storage()
        response = client.post("/api/v1/tasks/count")
        assert response.status_code == 405

    def test_count_response_schema(self, client):
        """Test count endpoint returns only the count field."""
        self._clear_storage()
        response = client.get("/api/v1/tasks/count")
        body = response.json()
        assert set(body.keys()) == {"count"}
