import pytest
from starlette.testclient import TestClient

from fastmcp_server import SERVICE_VERSION
from fastmcp_server.server import mcp


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
        body = response.json()
        assert body["status"] == "ok"
        assert body["version"] == SERVICE_VERSION

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

    def test_health_endpoint_includes_version(self, client):
        """Test HTTP health endpoint includes a stable service version."""
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert "version" in body
        assert body["version"] == SERVICE_VERSION

    def test_health_version_is_stable_string(self, client):
        """Test that the version field is a non-empty string."""
        response = client.get("/health")
        body = response.json()
        assert isinstance(body["version"], str)
        assert len(body["version"]) > 0

    def test_health_version_matches_package_version(self, client):
        """Test that the version matches the SERVICE_VERSION constant."""
        response = client.get("/health")
        body = response.json()
        assert body["version"] == SERVICE_VERSION

    def test_health_endpoint_preserves_status_field(self, client):
        """Test that the health endpoint still returns status: ok."""
        response = client.get("/health")
        body = response.json()
        assert body["status"] == "ok"
