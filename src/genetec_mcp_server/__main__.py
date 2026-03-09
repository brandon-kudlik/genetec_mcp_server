"""Entry point for the Genetec MCP Server."""

from genetec_mcp_server.server import mcp


def main() -> None:
    """Run the MCP server with streamable HTTP transport."""
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
