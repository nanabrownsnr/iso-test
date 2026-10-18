# FastMCP Server

A production-quality FastMCP server with task management, built with Python 3.12+, uv, and Docker.

## Tools

### Existing Tools (Backward Compatible)

- **`health_check`** – Returns the health status of the server (`{"status": "ok"}`).
- **`echo`** – Accepts a `message` string and returns it as `{"echo": "..."}`.

### Task Management Tools

#### `create_task(title, description, priority, status)`

Create a new task with a generated UUID and UTC timestamps.

| Argument      | Type   | Required | Valid Values                                  |
|---------------|--------|----------|-----------------------------------------------|
| `title`       | string | yes      | Must not be blank                             |
| `description` | string | no       | Free text (defaults to `""`)                  |
| `priority`    | string | yes      | `low`, `medium`, `high`                       |
| `status`      | string | yes      | `todo`, `in_progress`, `done`                 |

**Response schema:**

```json
{
  "id": "uuid-string",
  "title": "string",
  "description": "string",
  "priority": "low | medium | high",
  "status": "todo | in_progress | done",
  "created_at": "ISO 8601 UTC timestamp",
  "updated_at": "ISO 8601 UTC timestamp"
}
```

**Example call:**

```json
// create_task
{"title": "Fix login bug", "description": "Users can't log in with SSO", "priority": "high", "status": "todo"}
```

#### `get_task(task_id)`

Retrieve a single task by its ID.

| Argument  | Type   | Required | Description              |
|-----------|--------|----------|--------------------------|
| `task_id` | string | yes      | The unique task identifier |

**Response schema (found):**

```json
{
  "id": "uuid-string",
  "title": "string",
  "description": "string",
  "priority": "low | medium | high",
  "status": "todo | in_progress | done",
  "created_at": "ISO 8601 UTC timestamp",
  "updated_at": "ISO 8601 UTC timestamp"
}
```

**Response schema (not found):**

```json
{"error": "Task not found: <task_id>"}
```

**Example call:**

```json
// get_task
{"task_id": "550e8400-e29b-41d4-a716-446655440000"}
```

#### `list_tasks(status, priority, search)`

List tasks with optional filters and deterministic ordering (todo → in_progress → done, then by priority, then by creation time).

| Argument   | Type    | Required | Description                                                    |
|------------|---------|----------|----------------------------------------------------------------|
| `status`   | string? | no       | Filter by status: `todo`, `in_progress`, `done`                |
| `priority` | string? | no       | Filter by priority: `low`, `medium`, `high`                    |
| `search`   | string? | no       | Search by title or description (case-insensitive substring)    |

**Response schema:**

```json
{
  "tasks": [
    {
      "id": "uuid-string",
      "title": "string",
      "description": "string",
      "priority": "low | medium | high",
      "status": "todo | in_progress | done",
      "created_at": "ISO 8601 UTC timestamp",
      "updated_at": "ISO 8601 UTC timestamp"
    }
  ],
  "count": 42
}
```

**Example calls:**

```json
// list_tasks - all tasks
{}

// list_tasks - filter by status
{"status": "todo"}

// list_tasks - filter by priority and status
{"status": "in_progress", "priority": "high"}

// list_tasks - search by keyword
{"search": "login"}
```

#### `update_task(task_id, title, description, priority, status)`

Partially update a task and refresh its `updated_at` timestamp. Any field not provided is left unchanged.

| Argument      | Type    | Required | Valid Values                                    |
|---------------|---------|----------|-------------------------------------------------|
| `task_id`     | string  | yes      | The unique task identifier                      |
| `title`       | string? | no       | Must not be blank if provided                   |
| `description` | string? | no       | Free text                                       |
| `priority`    | string? | no       | `low`, `medium`, `high`                         |
| `status`      | string? | no       | `todo`, `in_progress`, `done`                   |

**Response schema (found):**

```json
{
  "id": "uuid-string",
  "title": "string",
  "description": "string",
  "priority": "low | medium | high",
  "status": "todo | in_progress | done",
  "created_at": "ISO 8601 UTC timestamp",
  "updated_at": "ISO 8601 UTC timestamp"
}
```

**Response schema (not found):**

```json
{"error": "Task not found: <task_id>"}
```

**Example call:**

```json
// update_task - partial update
{"task_id": "550e8400-e29b-41d4-a716-446655440000", "status": "done"}
```

#### `delete_task(task_id)`

Delete a task by its ID.

| Argument  | Type   | Required | Description              |
|-----------|--------|----------|--------------------------|
| `task_id` | string | yes      | The unique task identifier |

**Response schema (found):**

```json
{"deleted": "uuid-string"}
```

**Response schema (not found):**

```json
{"error": "Task not found: <task_id>"}
```

**Example call:**

```json
// delete_task
{"task_id": "550e8400-e29b-41d4-a716-446655440000"}
```

#### `task_summary()`

Return counts of tasks grouped by status and priority.

**Response schema:**

```json
{
  "total": 10,
  "by_status": {
    "todo": 3,
    "in_progress": 4,
    "done": 3
  },
  "by_priority": {
    "low": 2,
    "medium": 4,
    "high": 4
  }
}
```

**Example call:**

```json
// task_summary
{}
```

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

Connect your MCP-compatible client to the server. The server exposes eight tools:

```json
// health_check
{}

// echo
{"message": "hello world"}

// create_task
{"title": "Fix bug", "description": "Users can't login", "priority": "high", "status": "todo"}

// get_task
{"task_id": "<uuid>"}

// list_tasks
{"status": "todo"}

// update_task
{"task_id": "<uuid>", "status": "done"}

// delete_task
{"task_id": "<uuid>"}

// task_summary
{}
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
│       ├── server.py
│       ├── models.py
│       └── storage.py
├── tests/
│   ├── __init__.py
│   ├── test_tools.py
│   ├── test_http_endpoint.py
│   └── test_task_management.py
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── pyproject.toml
└── README.md
```
