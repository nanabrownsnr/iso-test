from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

mcp = FastMCP(name="fastmcp-server")


@mcp.tool()
async def health_check() -> dict:
    """Return the health status of the server."""
    return {"status": "ok"}


@mcp.tool()
async def echo(message: str) -> dict:
    """Echo back the provided message."""
    return {"echo": message}


@mcp.custom_route("/health", methods=["GET"])
async def health_endpoint(request: Request) -> JSONResponse:
    """HTTP health check endpoint."""
    return JSONResponse(content={"status": "ok"})


def main() -> None:
    mcp.run(transport="http")


if __name__ == "__main__":
    main()
