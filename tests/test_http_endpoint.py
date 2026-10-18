import asyncio

import pytest
from starlette.testclient import TestClient

from fastmcp_server.server import mcp


@pytest.fixture(autouse=True)
def _reset_storage():
    """Reset in-memory storage between tests to keep them independent."""
    import importlib

    import fastmcp_server.storage

    importlib.reload(fastmcp_server.storage)
    yield
    importlib.reload(fastmcp_server.storage)


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
# Task summary HTTP endpoint tests
# ---------------------------------------------------------------------------


class TestTasksSummaryEndpoint:
    @pytest.fixture
    def client(self):
        return TestClient(mcp.http_app())

    def _create_task(self, title, priority="low", status="todo"):
        return asyncio.run(mcp.call_tool("create_task", {
            "title": title,
            "description": "D",
            "priority": priority,
            "status": status,
        }))

    def test_summary_endpoint_status_code(self, client):
        """Test /api/v1/tasks/summary returns 200."""
        response = client.get("/api/v1/tasks/summary")
        assert response.status_code == 200

    def test_summary_endpoint_content_type(self, client):
        """Test /api/v1/tasks/summary returns JSON content type."""
        response = client.get("/api/v1/tasks/summary")
        assert "application/json" in response.headers.get("content-type", "")

    def test_summary_endpoint_empty_storage(self, client):
        """Test /api/v1/tasks/summary returns zero counts when empty."""
        response = client.get("/api/v1/tasks/summary")
        data = response.json()
        assert data["total"] == 0
        assert data["by_status"] == {}
        assert data["by_priority"] == {}

    def test_summary_endpoint_total_count(self, client):
        """Test /api/v1/tasks/summary returns correct total count."""
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "high", "done")
        self._create_task("T3", "medium", "in_progress")
        response = client.get("/api/v1/tasks/summary")
        assert response.json()["total"] == 3

    def test_summary_endpoint_by_status_counts(self, client):
        """Test /api/v1/tasks/summary returns correct by_status counts."""
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "high", "todo")
        self._create_task("T3", "low", "done")
        data = client.get("/api/v1/tasks/summary").json()
        assert data["by_status"]["todo"] == 2
        assert data["by_status"]["done"] == 1

    def test_summary_endpoint_by_priority_counts(self, client):
        """Test /api/v1/tasks/summary returns correct by_priority counts."""
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "medium", "todo")
        self._create_task("T3", "high", "todo")
        data = client.get("/api/v1/tasks/summary").json()
        assert data["by_priority"]["low"] == 1
        assert data["by_priority"]["medium"] == 1
        assert data["by_priority"]["high"] == 1

    def test_summary_endpoint_response_schema(self, client):
        """Test /api/v1/tasks/summary response has required fields."""
        self._create_task("T", "low", "todo")
        data = client.get("/api/v1/tasks/summary").json()
        assert "total" in data
        assert "by_status" in data
        assert "by_priority" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["by_status"], dict)
        assert isinstance(data["by_priority"], dict)

    def test_summary_endpoint_rejects_post(self, client):
        """Test /api/v1/tasks/summary rejects non-GET methods."""
        response = client.post("/api/v1/tasks/summary")
        assert response.status_code == 405

    def test_summary_endpoint_includes_all_statuses(self, client):
        """Test /api/v1/tasks/summary includes all status categories present."""
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "low", "in_progress")
        self._create_task("T3", "low", "done")
        data = client.get("/api/v1/tasks/summary").json()
        assert "todo" in data["by_status"]
        assert "in_progress" in data["by_status"]
        assert "done" in data["by_status"]

    def test_summary_endpoint_includes_all_priorities(self, client):
        """Test /api/v1/tasks/summary includes all priority categories present."""
        self._create_task("T1", "low", "todo")
        self._create_task("T2", "medium", "todo")
        self._create_task("T3", "high", "todo")
        data = client.get("/api/v1/tasks/summary").json()
        assert "low" in data["by_priority"]
        assert "medium" in data["by_priority"]
        assert "high" in data["by_priority"]
