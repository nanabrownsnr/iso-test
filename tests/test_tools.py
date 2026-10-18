import asyncio

import pytest
from fastmcp import FastMCP
from starlette.testclient import TestClient

from fastmcp_server import SERVICE_VERSION
from fastmcp_server.server import mcp


@pytest.fixture
def client():
    """Create a test client for the MCP server."""
    return TestClient(mcp.http_app())


@pytest.fixture
def mcp_server():
    """Create a fresh MCP server instance for testing."""
    server = FastMCP(name="test-server")

    @server.tool()
    async def health_check() -> dict:
        """Return the health status of the server."""
        return {"status": "ok", "version": SERVICE_VERSION}

    @server.tool()
    async def echo(message: str) -> dict:
        """Echo back the provided message."""
        return {"echo": message}

    return server


class TestHealthCheckTool:
    def test_health_check_returns_ok(self, mcp_server):
        """Test health_check tool returns status ok."""
        result = asyncio.run(mcp_server.call_tool("health_check", {}))
        assert result.structured_content["status"] == "ok"

    def test_health_check_includes_version(self, mcp_server):
        """Test health_check tool includes a stable service version."""
        result = asyncio.run(mcp_server.call_tool("health_check", {}))
        body = result.structured_content
        assert "version" in body
        assert body["version"] == SERVICE_VERSION

    def test_health_check_version_matches_constant(self, mcp_server):
        """Test health_check tool version matches the package SERVICE_VERSION."""
        result = asyncio.run(mcp_server.call_tool("health_check", {}))
        body = result.structured_content
        assert body["version"] == SERVICE_VERSION

    def test_health_check_still_returns_status_ok(self, mcp_server):
        """Test health_check tool preserves existing status field."""
        result = asyncio.run(mcp_server.call_tool("health_check", {}))
        body = result.structured_content
        assert body["status"] == "ok"

    def test_health_check_tool_registered(self, mcp_server):
        """Test health_check tool is registered in the server."""
        tools = asyncio.run(mcp_server.list_tools())
        tool_names = [t.name for t in tools]
        assert "health_check" in tool_names

    def test_health_check_tool_description(self, mcp_server):
        """Test health_check tool has a description."""
        tool = asyncio.run(mcp_server.get_tool("health_check"))
        assert tool is not None
        assert tool.description == "Return the health status of the server."


class TestEchoTool:
    def test_echo_returns_message(self, mcp_server):
        """Test echo tool returns the provided message."""
        result = asyncio.run(mcp_server.call_tool("echo", {"message": "hello"}))
        assert result.structured_content == {"echo": "hello"}

    def test_echo_empty_message(self, mcp_server):
        """Test echo tool with empty string."""
        result = asyncio.run(mcp_server.call_tool("echo", {"message": ""}))
        assert result.structured_content == {"echo": ""}

    def test_echo_tool_registered(self, mcp_server):
        """Test echo tool is registered in the server."""
        tools = asyncio.run(mcp_server.list_tools())
        tool_names = [t.name for t in tools]
        assert "echo" in tool_names

    def test_echo_multibyte_message(self, mcp_server):
        """Test echo tool with unicode characters."""
        result = asyncio.run(mcp_server.call_tool("echo", {"message": "こんにちは"}))
        assert result.structured_content == {"echo": "こんにちは"}

    def test_echo_long_message(self, mcp_server):
        """Test echo tool with a long message."""
        long_message = "a" * 10000
        result = asyncio.run(mcp_server.call_tool("echo", {"message": long_message}))
        assert result.structured_content == {"echo": long_message}

    def test_echo_tool_description(self, mcp_server):
        """Test echo tool has a description."""
        tool = asyncio.run(mcp_server.get_tool("echo"))
        assert tool is not None
        assert tool.description == "Echo back the provided message."


class TestHTTPHealthEndpoint:
    def test_health_endpoint_returns_ok(self, client):
        """Test HTTP health endpoint returns status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["version"] == SERVICE_VERSION

    def test_health_endpoint_content_type(self, client):
        """Test HTTP health endpoint returns JSON content type."""
        response = client.get("/health")
        assert "application/json" in response.headers.get("content-type", "")

    def test_health_endpoint_only_get(self, client):
        """Test HTTP health endpoint only accepts GET method."""
        response = client.post("/health")
        assert response.status_code == 405

    def test_health_endpoint_not_found(self, client):
        """Test that unknown routes return 404."""
        response = client.get("/unknown")
        assert response.status_code == 404
