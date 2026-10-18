import asyncio

from fastmcp import FastMCP
from starlette.testclient import TestClient

from fastmcp_server import SERVICE_VERSION
from fastmcp_server.server import mcp
from fastmcp_server.version import SERVICE_VERSION as PACKAGE_VERSION


class TestServiceVersionMetadata:
    """Tests for the stable service version metadata."""

    def test_version_is_non_empty_string(self):
        """Test that SERVICE_VERSION is a non-empty string."""
        assert isinstance(SERVICE_VERSION, str)
        assert len(SERVICE_VERSION) > 0

    def test_version_matches_package_import(self):
        """Test that the exported version matches the version module."""
        assert SERVICE_VERSION == PACKAGE_VERSION

    def test_version_is_derived_from_metadata_not_hardcoded(self):
        """Test that version follows semver pattern (not a hardcoded placeholder)."""
        import re

        # Version should match semantic versioning pattern
        assert re.match(r"^\d+\.\d+\.\d+", SERVICE_VERSION), (
            f"Version '{SERVICE_VERSION}' does not follow semver format"
        )

    def test_version_in_health_http_response(self):
        """Test that the HTTP health endpoint returns the stable version."""
        client = TestClient(mcp.http_app())
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == SERVICE_VERSION

    def test_version_in_health_mcp_tool(self):
        """Test that the health_check MCP tool returns the stable version."""

        server = FastMCP(name="test-version")

        @server.tool()
        async def health_check() -> dict:
            """Return the health status of the server."""
            return {"status": "ok", "version": SERVICE_VERSION}

        result = asyncio.run(server.call_tool("health_check", {}))
        body = result.structured_content
        assert body["version"] == SERVICE_VERSION

    def test_version_is_stable_across_imports(self):
        """Test that SERVICE_VERSION is the same regardless of import path."""
        from fastmcp_server import SERVICE_VERSION as V1
        from fastmcp_server.server import SERVICE_VERSION as V3
        from fastmcp_server.version import SERVICE_VERSION as V2

        assert V1 == V2 == V3

    def test_health_http_version_is_stable_across_calls(self):
        """Test that the version is consistent across multiple HTTP health calls."""
        client = TestClient(mcp.http_app())
        versions = []
        for _ in range(3):
            response = client.get("/health")
            assert response.status_code == 200
            versions.append(response.json()["version"])
        assert len(set(versions)) == 1
        assert versions[0] == SERVICE_VERSION

    def test_health_response_has_exactly_status_and_version(self):
        """Test that health response contains exactly status and version keys."""
        client = TestClient(mcp.http_app())
        response = client.get("/health")
        body = response.json()
        assert set(body.keys()) == {"status", "version"}

    def test_health_http_and_mcp_tool_versions_match(self):
        """Test that HTTP health endpoint and MCP tool return the same version."""
        client = TestClient(mcp.http_app())
        http_response = client.get("/health")
        http_version = http_response.json()["version"]

        server = FastMCP(name="test-version-match")

        @server.tool()
        async def health_check() -> dict:
            """Return the health status of the server."""
            return {"status": "ok", "version": SERVICE_VERSION}

        tool_result = asyncio.run(server.call_tool("health_check", {}))
        tool_version = tool_result.structured_content["version"]

        assert http_version == tool_version == SERVICE_VERSION
