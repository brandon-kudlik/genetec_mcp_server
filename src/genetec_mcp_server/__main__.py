"""Entry point for the Genetec MCP Server."""

from genetec_mcp_server.server import mcp


def main() -> None:
    """Run the MCP server with SSE transport."""
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
