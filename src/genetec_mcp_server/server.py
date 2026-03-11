"""MCP server for Genetec Security Center."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

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


@mcp.tool()
async def create_cardholder(
    ctx: Context,
    first_name: str,
    last_name: str,
    email: Optional[str] = None,
    mobile_phone: Optional[str] = None,
) -> str:
    """Create a new cardholder in Genetec Security Center.

    Args:
        first_name: Cardholder's first name.
        last_name: Cardholder's last name.
        email: Email address (optional).
        mobile_phone: Mobile phone number (optional).

    Returns:
        The GUID of the newly created cardholder, or an error message.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        guid = connection.create_cardholder(
            first_name=first_name,
            last_name=last_name,
            email=email,
            mobile_phone=mobile_phone,
        )
        return f"Cardholder created: {first_name} {last_name} (GUID: {guid})"
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def add_cloudlink_unit(
    ctx: Context,
    name: str,
    ip_address: str,
    username: str,
    password: str,
    access_manager_guid: str,
) -> str:
    """Enroll a Synergis Cloudlink access control unit into a Security Center Access Manager role.

    Args:
        name: Display name for the unit.
        ip_address: IP address or hostname of the Cloudlink device.
        username: Admin username for the Cloudlink unit.
        password: Admin password for the Cloudlink unit.
        access_manager_guid: GUID of the Access Manager role to assign the unit to.

    Returns:
        The GUID of the newly created unit, or an error message.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        guid = connection.add_cloudlink_unit(
            name=name,
            ip_address=ip_address,
            username=username,
            password=password,
            access_manager_guid=access_manager_guid,
        )
        return f"Cloudlink unit enrolled: {name} at {ip_address} (GUID: {guid})"
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"
