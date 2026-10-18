# FastMCP Server

A minimal production-quality FastMCP server built with Python 3.12+, uv, and Docker.

## Tools

- **`health_check`** – Returns the health status of the server (`{"status": "ok"}`).
- **`echo`** – Accepts a `message` string and returns it as `{"echo": "..."}`.

## HTTP Endpoints

- **`GET /health`** – Health check endpoint returning `{"status": "ok"}`.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) – Python package manager
- [Docker](https://www.docker.com/) (optional, for containerized runs)

## Local Development

```bash
# Install dependencies
uv sync

# Install dev/test dependencies
uv sync --all-extras

# Run tests
uv run pytest tests/ -v

# Run linting
uv run ruff check .
uv run mypy src/

# Build the package
uv build

# Run the server
uv run python -m fastmcp_server.server
```

## Docker

```bash
# Build the Docker image
docker compose build

# Run the server
docker compose up

# Run with health check
docker compose up -d

# Check container logs
docker compose logs -f fastmcp-server

# Stop the server
docker compose down
```

## API Usage

### MCP Tools

Connect your MCP-compatible client to the server. The server exposes two tools:

```json
// health_check
{}

// echo
{"message": "hello world"}
```

### HTTP Health Check

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## Project Structure

```
.
├── src/
│   └── fastmcp_server/
│       ├── __init__.py
│       └── server.py
├── tests/
│   ├── __init__.py
│   ├── test_tools.py
│   └── test_http_endpoint.py
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── pyproject.toml
└── README.md
```
