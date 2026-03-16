"""MCP server for Genetec Security Center."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Optional

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
        result = connection.add_cloudlink_unit(
            name=name,
            ip_address=ip_address,
            username=username,
            password=password,
            access_manager_guid=access_manager_guid,
        )
        return f"Cloudlink unit enrolled successfully: {result} at {ip_address}"
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def add_mercury_controller(
    ctx: Context,
    unit_guid: str,
    name: str,
    controller_type: str,
    ip_address: str,
    port: int = 3001,
    channel: int = 0,
) -> str:
    """Add a Mercury EP/LP/MP sub-controller to an enrolled Synergis Cloudlink unit.

    This adds a Mercury interface module as a bus peripheral under an existing
    Cloudlink access control unit.

    Args:
        unit_guid: GUID of the parent Cloudlink unit.
        name: Display name for the interface module.
        controller_type: Mercury model. Valid types: EP1501, EP1501WithExpansion,
            EP1502, EP2500, EP4502, LP1501, LP1501WithExpansion, LP1502, LP2500,
            LP4502, MP1501, MP1501WithExpansion, MP1502, MP2500, MP4502, M5IC, MSICS.
        ip_address: IP address of the Mercury controller.
        port: TCP port (default 3001).
        channel: Channel number (default 0).

    Returns:
        A success message or an error description.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        result = connection.add_mercury_controller(
            unit_guid=unit_guid,
            name=name,
            controller_type=controller_type,
            ip_address=ip_address,
            port=port,
            channel=channel,
        )
        return f"Mercury controller enrolled successfully: {result}"
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def add_interface_module(
    ctx: Context,
    unit_guid: str,
    controller_guid: str,
    name: str,
    board_type: str,
    address: int = 0,
) -> str:
    """Add an interface board to a Mercury controller.

    Interface boards connect to Mercury controllers via the SIO bus. The entity
    hierarchy is: Cloudlink Unit → Mercury Controller → Interface Board.

    Args:
        unit_guid: GUID of the parent Cloudlink unit.
        controller_guid: GUID of the parent Mercury controller.
        name: Display name for the interface board.
        board_type: Board model. Valid types: MR50, MR51e, MR52, MR62e, MR16In,
            MR16Out, MSACS, MSI8S, MSR8S, M516Do, M516Dor, M520In, M52K, M52RP,
            M52SRP, M58RP.
        address: SIO bus address (default 0).

    Returns:
        A success message or an error description.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        result = connection.add_interface_module(
            unit_guid=unit_guid,
            controller_guid=controller_guid,
            name=name,
            board_type=board_type,
            address=address,
        )
        return f"Interface module added successfully: {result}"
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def list_io_devices(ctx: Context, interface_module_guid: str) -> str:
    """List all IO devices (inputs, outputs, readers) on an interface module.

    Use this to discover devices on an interface board after adding it to a
    Mercury controller. Returns device GUIDs needed for configure_io_devices.

    Args:
        interface_module_guid: GUID of the interface module to query.

    Returns:
        A formatted list of devices with their GUIDs, names, types, and status.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        devices = connection.list_io_devices(interface_module_guid=interface_module_guid)
        if not devices:
            return f"No devices found on interface module {interface_module_guid}."
        lines = [f"Found {len(devices)} device(s) on interface module {interface_module_guid}:\n"]
        for d in devices:
            status = "Online" if d.get("isOnline") else "Offline"
            lines.append(
                f"- {d.get('deviceType', 'Unknown')} | {d.get('name', 'Unnamed')} "
                f"({d.get('physicalName', '')}) | GUID: {d.get('guid', '')} | {status}"
            )
        return "\n".join(lines)
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def create_doors(
    ctx: Context,
    doors: list[dict[str, Any]],
) -> str:
    """Batch create door entities in Genetec Security Center.

    Creates door entities only. Use configure_door_hardware to assign a lock
    device, set timing properties, and link readers/sensors.

    Args:
        doors: List of door definitions. Each dict must contain:
            - name (str, required): Display name for the door.

    Returns:
        A summary of created doors with their GUIDs.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        result = connection.create_doors(doors=doors)
        count = result.get("createdCount", 0)
        lines = [f"Created {count} door(s):"]
        for door in result.get("results", []):
            lines.append(f"- {door.get('name', 'Unknown')}: {door.get('guid', 'N/A')} ({door.get('status', '')})")
        return "\n".join(lines)
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def configure_door_hardware(
    ctx: Context,
    assignments: list[dict[str, Any]],
) -> str:
    """Assign hardware devices (lock, readers, REX, sensors) to doors in Genetec Security Center.

    Uses AddConnection to link IO devices from Mercury controller interface boards
    to door access points. Each device can only be assigned to one door at a time.

    Args:
        assignments: List of hardware assignments. Each dict must contain:
            - doorGuid (str, required): GUID of the door to configure.
            - hardware (dict, required): Hardware configuration with:
              - doorLockGuid (str, optional): GUID of the output device for the door lock.
              - doorSensorGuid (str, optional): GUID of the door contact sensor input
                device (AccessPointType.DoorSensor). Detects physical open/closed state.
                Required for DoorForcedOpen events.
              - entrySide (dict, optional): Entry side hardware:
                - readerGuid (str): GUID of the reader device.
                - rexGuid (str): GUID of the REX (request-to-exit) input device.
              - exitSide (dict, optional): Exit side hardware (same fields as entrySide).

    Returns:
        A summary of configured doors.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        result = connection.configure_door_hardware(assignments=assignments)
        count = result.get("configuredCount", 0)
        lines = [f"Configured hardware for {count} door(s):"]
        for door in result.get("results", []):
            lines.append(f"- {door.get('doorGuid', 'Unknown')}: {door.get('status', '')}")
        return "\n".join(lines)
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def configure_io_devices(
    ctx: Context,
    interface_module_guid: str,
    device_configs: list[dict[str, Any]],
) -> str:
    """Configure IO devices (name, input/output settings) on an interface module.

    Applies all changes in a single transaction. Use list_io_devices first to
    discover device GUIDs.

    Args:
        interface_module_guid: GUID of the interface module.
        device_configs: List of device configurations. Each dict must contain:
            - deviceGuid (str, required): GUID of the device to configure.
            - name (str, optional): New display name for the device.
            - inputContactType (str, optional): For inputs only. Values:
              'NormallyOpenNotSupervised', 'NormallyClosedNotSupervised',
              'NormallyOpenSupervised', 'NormallyClosedSupervised',
              'Custom1', 'Custom2', 'Custom3', 'Custom4'.
            - debounce (float, optional): For numbered inputs only (not Tamper,
              PowerMonitor, etc.). Debounce time in ms (e.g. 33.4).
            - shunted (bool, optional): For inputs only.
            - supervised (str, optional): For inputs only. Values:
              'E_STATE_NONE', 'E_STATE_3STATE', 'E_STATE_4STATE'.
            - outputContactType (str, optional): For outputs only. Values:
              'Normal', 'Inverted'.

    Returns:
        A success message or an error description.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        result = connection.configure_io_devices(
            interface_module_guid=interface_module_guid,
            device_configs=device_configs,
        )
        return f"Configured {result.get('configuredCount', 0)} device(s): {result.get('message', 'OK')}"
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def create_alarm(
    ctx: Context,
    name: str,
    priority: Optional[int] = None,
    reactivation_threshold: Optional[int] = None,
) -> str:
    """Create an alarm entity in Genetec Security Center.

    Args:
        name: Display name for the alarm.
        priority: Alarm priority level 1-255 (optional). Lower values = higher priority.
        reactivation_threshold: Seconds before the alarm can re-trigger (optional).

    Returns:
        The GUID of the newly created alarm, or an error message.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        guid = connection.create_alarm(
            name=name,
            priority=priority,
            reactivation_threshold=reactivation_threshold,
        )
        return f"Alarm created: {name} (GUID: {guid})"
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def create_access_rules(
    ctx: Context,
    access_rules: list[dict[str, Any]],
) -> str:
    """Batch create access rules (access levels) in Genetec Security Center and assign doors.

    Creates permanent access rules and optionally assigns doors to each rule.
    Access rules control which cardholders can access which doors.

    Args:
        access_rules: List of access rule definitions. Each dict must contain:
            - name (str, required): Display name for the access rule.
            - doorGuids (list[str], optional): GUIDs of doors to assign to this rule.
            - side (str, optional): Which side of the door the rule applies to.
              Values: 'Both' (default), 'Entry', 'Exit'.

    Returns:
        A summary of created access rules with their GUIDs and door assignment counts.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        result = connection.create_access_rules(access_rules=access_rules)
        count = result.get("createdCount", 0)
        lines = [f"Created {count} access rule(s):"]
        for r in result.get("results", []):
            doors = r.get("doorsAssigned", 0)
            lines.append(
                f"- {r.get('name', 'Unknown')}: {r.get('guid', 'N/A')} "
                f"({doors} door(s) assigned) ({r.get('status', '')})"
            )
        return "\n".join(lines)
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def add_event_to_action(
    ctx: Context,
    mappings: list[dict[str, Any]],
) -> str:
    """Add event-to-action mappings to entities in Genetec Security Center.

    Links entity events (e.g. door held, door forced) to actions (e.g. trigger alarm).
    This is how you configure a door to trigger an alarm when a specific event occurs.

    Args:
        mappings: List of event-to-action definitions. Each dict must contain:
            - entityGuid (str, required): GUID of the source entity (e.g. a door).
            - eventType (str, required): Event type name. Common door events:
              'DoorOpenWhileLockSecure' (door forced open), 'DoorOpenedForTooLong'
              (door held), 'DoorOpen', 'DoorClose', 'DoorLock', 'DoorUnlock',
              'AccessGranted', 'AccessRefused'.
            - actionType (str, required): Action type name. Currently supported:
              'TriggerAlarm'.
            - alarmGuid (str, optional): GUID of the alarm to trigger
              (required when actionType is 'TriggerAlarm').

    Returns:
        A summary of added event-to-action mappings.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        result = connection.add_event_to_action(mappings=mappings)
        count = result.get("addedCount", 0)
        lines = [f"Added {count} event-to-action mapping(s):"]
        for r in result.get("results", []):
            lines.append(
                f"- {r.get('entityGuid', 'Unknown')} | {r.get('eventType', '')} → "
                f"{r.get('actionType', '')} | {r.get('status', '')}"
            )
        return "\n".join(lines)
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"
