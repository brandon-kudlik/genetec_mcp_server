"""MCP server for Genetec Security Center."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP

from genetec_mcp_server.config import HOST, PORT
from genetec_mcp_server.connection import GenetecConnection


@dataclass
class AppContext:
    """Lifespan context holding the Genetec connection."""

    connection: GenetecConnection


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage GenetecConnection lifecycle.

    Connects to Security Center on startup and disposes on shutdown.
    """
    conn = GenetecConnection()
    conn.connect()
    try:
        yield AppContext(connection=conn)
    finally:
        conn.dispose()


mcp = FastMCP("Genetec Security Center", host=HOST, port=PORT, lifespan=app_lifespan)


@mcp.tool()
async def get_system_version(ctx: Context) -> str:
    """Get the Security Center version from the directory server.

    Returns the version string (e.g. '5.13.3132.18') or an error message
    if the server is not connected.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        return connection.get_system_version()
    except RuntimeError as e:
        return f"Error: {e}"
