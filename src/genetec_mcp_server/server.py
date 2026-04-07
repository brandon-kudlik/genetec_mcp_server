"""MCP server for Genetec Security Center."""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from mcp.server.fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from genetec_mcp_server.config import HOST, LOG_DIR, PORT
from genetec_mcp_server.connection import GenetecConnection
from genetec_mcp_server.tool_logger import ToolCallLogger, ToolCallRecord, sanitize_args


@dataclass
class AppContext:
    """Lifespan context holding the Genetec connection and tool logger."""

    connection: GenetecConnection
    tool_logger: ToolCallLogger


_shared_connection: GenetecConnection | None = None
_shared_logger: ToolCallLogger | None = None


def _get_shared_connection() -> GenetecConnection:
    global _shared_connection
    if _shared_connection is None:
        _shared_connection = GenetecConnection()
        _shared_connection.connect()
    return _shared_connection


def _get_shared_logger() -> ToolCallLogger:
    global _shared_logger
    if _shared_logger is None:
        _shared_logger = ToolCallLogger(Path(LOG_DIR))
    return _shared_logger


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Provide shared GenetecConnection and ToolCallLogger to each session."""
    yield AppContext(connection=_get_shared_connection(), tool_logger=_get_shared_logger())


class LoggingFastMCP(FastMCP):
    """FastMCP subclass that logs every tool call to JSONL files."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Maps id(session) -> short 8-char hex session UID
        self._session_uids: dict[int, str] = {}

    def _get_session_uid(self, session: Any) -> str:
        key = id(session)
        if key not in self._session_uids:
            self._session_uids[key] = uuid.uuid4().hex[:8]
        return self._session_uids[key]

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> Sequence[Any] | dict[str, Any]:
        ctx = self.get_context()
        session_uid = "unknown"
        is_new_session = False
        try:
            session = ctx.session
            session_key = id(session)
            is_new_session = session_key not in self._session_uids
            session_uid = self._get_session_uid(session)
        except Exception:
            pass

        start = time.monotonic()
        result = None
        error = None
        try:
            result = await super().call_tool(name, arguments)
            return result
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            timestamp = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat()
            result_str = None
            if result is not None:
                raw = str(result)
                result_str = raw[:500] if len(raw) > 500 else raw

            record = ToolCallRecord(
                session_id=session_uid,
                tool_name=name,
                arguments=sanitize_args(arguments),
                result=result_str,
                error=error,
                timestamp=timestamp,
                duration_ms=round(duration_ms, 2),
            )

            try:
                tool_logger = ctx.request_context.lifespan_context.tool_logger
                tool_logger.log(record)
            except Exception:
                pass

            if is_new_session:
                try:
                    await ctx.info(f"Session ID: {session_uid}")
                except Exception:
                    pass


mcp = LoggingFastMCP("Genetec Security Center", host=HOST, port=PORT, lifespan=app_lifespan)


@mcp.custom_route("/health", methods=["GET"])
async def http_health_check(request: Request) -> JSONResponse:
    """Lightweight health check for ALB — does not create an MCP session."""
    conn = _get_shared_connection()
    try:
        connected = conn.is_connected
    except Exception:
        connected = False
    status_code = 200 if connected else 503
    return JSONResponse({"status": "ok" if connected else "unhealthy"}, status_code=status_code)


@mcp.custom_route("/api/logs/sessions", methods=["GET"])
async def http_list_sessions(request: Request) -> JSONResponse:
    """Return active sessions as JSON — useful for curl/browser access."""
    try:
        app_state = mcp._lifespan_context  # type: ignore[attr-defined]
        sessions = app_state.tool_logger.get_sessions()
    except Exception:
        sessions = []
    return JSONResponse(sessions)


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
        channel: Channel ID for this Mercury controller. Must be unique among
            controllers on the same Cloudlink unit (0, 1, 2, ...). Default 0.

    Returns:
        The GUID of the newly created Mercury controller, or an error message.
        Use this GUID as controller_guid when calling add_interface_module.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        guid = connection.add_mercury_controller(
            unit_guid=unit_guid,
            name=name,
            controller_type=controller_type,
            ip_address=ip_address,
            port=port,
            channel=channel,
        )
        return f"Mercury {controller_type} controller '{name}' created (GUID: {guid})"
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
        The GUID of the newly created interface module, or an error message.
        Use this GUID with list_io_devices and configure_io_devices.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        guid = connection.add_interface_module(
            unit_guid=unit_guid,
            controller_guid=controller_guid,
            name=name,
            board_type=board_type,
            address=address,
        )
        return f"Interface module '{name}' ({board_type}) created (GUID: {guid})"
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
              Values: 'Both' (default), 'In', 'Out'.

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
async def query_cloudlink(ctx: Context) -> str:
    """Query all Cloudlink access control units enrolled in Security Center.

    Returns a list of Cloudlink units with their GUIDs, names, and online status.
    Use the returned GUIDs with other tools that require a Cloudlink unit GUID
    (e.g. add_mercury_controller, add_interface_module).
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        cloudlinks = connection.query_cloudlinks()
        if not cloudlinks:
            return "No Cloudlink units found in Security Center."
        lines = [f"Found {len(cloudlinks)} Cloudlink unit(s):\n"]
        for cl in cloudlinks:
            status = "Online" if cl.get("isOnline") else "Offline"
            lines.append(
                f"- {cl.get('name', 'Unnamed')} | GUID: {cl.get('guid', '')} | {status}"
            )
        return "\n".join(lines)
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def query_cardholders(ctx: Context) -> str:
    """Query all cardholders in Genetec Security Center.

    Returns a list of cardholders with their names, email, status, and GUIDs.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        cardholders = connection.query_cardholders()
        if not cardholders:
            return "No cardholders found in Security Center."
        lines = [f"Found {len(cardholders)} cardholder(s):\n"]
        for ch in cardholders:
            first = ch.get("firstName", "")
            last = ch.get("lastName", "")
            email = ch.get("emailAddress") or ""
            status = ch.get("status", "Unknown")
            guid = ch.get("guid", "")
            parts = [f"{first} {last}".strip()]
            if email:
                parts.append(f"Email: {email}")
            parts.append(f"Status: {status}")
            parts.append(f"GUID: {guid}")
            lines.append(f"- {' | '.join(parts)}")
        return "\n".join(lines)
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def query_credentials(ctx: Context) -> str:
    """Query all credentials in Genetec Security Center.

    Returns a list of credentials with their names, format, assigned cardholder,
    status, and GUIDs.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        credentials = connection.query_credentials()
        if not credentials:
            return "No credentials found in Security Center."
        lines = [f"Found {len(credentials)} credential(s):\n"]
        for cred in credentials:
            name = cred.get("name", "Unnamed")
            fmt = cred.get("formatType", "Unknown")
            ch_name = cred.get("cardholderName")
            status = cred.get("status", "Unknown")
            guid = cred.get("guid", "")
            parts = [name, f"Format: {fmt}"]
            if ch_name:
                parts.append(f"Cardholder: {ch_name}")
            else:
                parts.append("Cardholder: (unassigned)")
            parts.append(f"Status: {status}")
            parts.append(f"GUID: {guid}")
            lines.append(f"- {' | '.join(parts)}")
        return "\n".join(lines)
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def assign_credential(
    ctx: Context,
    credential_guid: str,
    cardholder_guid: str,
) -> str:
    """Assign an existing credential to a cardholder in Genetec Security Center.

    Links a credential (card, PIN, license plate) to a cardholder so they can
    use it for access control. If the credential is already assigned to a
    different cardholder, it will be reassigned.

    Args:
        credential_guid: GUID of the credential to assign.
        cardholder_guid: GUID of the cardholder to assign the credential to.

    Returns:
        A success message, or an error message.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        result = connection.assign_credential(
            credential_guid=credential_guid,
            cardholder_guid=cardholder_guid,
        )
        prev = result.get("previousCardholderGuid")
        msg = f"Credential {result['credentialGuid']} assigned to cardholder {result['cardholderGuid']}"
        if prev:
            msg += f" (reassigned from previous cardholder {prev})"
        return msg
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def create_credential(
    ctx: Context,
    name: str,
    format_type: str,
    facility: Optional[int] = None,
    card_id: Optional[int] = None,
    code: Optional[int] = None,
    license_plate: Optional[str] = None,
    raw_data: Optional[str] = None,
    bit_length: Optional[int] = None,
    cardholder_guid: Optional[str] = None,
) -> str:
    """Create a credential (card, PIN, license plate) in Genetec Security Center.

    Credentials are identification tokens used for access control. They can
    be assigned to cardholders to grant access through doors.

    Args:
        name: Display name for the credential (e.g. 'Card-001').
        format_type: Credential format type. Valid types:
            - WiegandStandard26Bit: Standard 26-bit Wiegand (requires facility + card_id)
            - WiegandH10306: HID H10306 34-bit (requires facility + card_id)
            - WiegandH10304: HID H10304 37-bit (requires facility + card_id)
            - WiegandH10302: HID H10302 37-bit (requires card_id only)
            - WiegandCsn32: 32-bit CSN (requires card_id only)
            - WiegandCorporate1000: Corporate 1000 35-bit (requires facility + card_id)
            - Wiegand48BitCorporate1000: 48-bit Corporate 1000 (requires facility + card_id)
            - Keypad: PIN code (requires code)
            - LicensePlate: License plate recognition (requires license_plate)
            - RawCard: Raw hex data (requires raw_data + bit_length)
        facility: Facility code (for Wiegand formats that require it).
        card_id: Card ID number (for Wiegand formats).
        code: PIN code integer (for Keypad format).
        license_plate: License plate string (for LicensePlate format).
        raw_data: Raw hex data string (for RawCard format).
        bit_length: Bit length of raw data (for RawCard format).
        cardholder_guid: GUID of a cardholder to assign this credential to (optional).

    Returns:
        The GUID of the newly created credential, or an error message.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        guid = connection.create_credential(
            name=name,
            format_type=format_type,
            facility=facility,
            card_id=card_id,
            code=code,
            license_plate=license_plate,
            raw_data=raw_data,
            bit_length=bit_length,
            cardholder_guid=cardholder_guid,
        )
        return f"Credential created: {name} ({format_type}) (GUID: {guid})"
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def query_access_rules(ctx: Context) -> str:
    """Query all access rules in Genetec Security Center.

    Returns a list of access rules with their names and GUIDs.
    Use the returned GUIDs with assign_access_rules to assign rules to cardholders.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        rules = connection.query_access_rules()
        if not rules:
            return "No access rules found."
        lines = [f"Found {len(rules)} access rule(s):\n"]
        for rule in rules:
            lines.append(f"- {rule.get('name', 'Unnamed')} (GUID: {rule.get('guid', '')})")
        return "\n".join(lines)
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def assign_access_rules(
    ctx: Context,
    access_rule_guids: list[str],
    cardholder_guids: list[str],
) -> str:
    """Assign access rules to cardholders in Genetec Security Center.

    Assigns each access rule to each cardholder (many-to-many). Use
    query_access_rules to find access rule GUIDs and query_cardholders to
    find cardholder GUIDs.

    Args:
        access_rule_guids: List of access rule GUIDs to assign.
        cardholder_guids: List of cardholder GUIDs to assign rules to.

    Returns:
        A summary of assignment results, or an error message.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        result = connection.assign_access_rules(
            access_rule_guids=access_rule_guids,
            cardholder_guids=cardholder_guids,
        )
        assignments = result.get("assignments", [])
        lines = ["Access Rule Assignment Results:"]
        for a in assignments:
            rule_guid = a.get("accessRuleGuid", "")
            ch_guid = a.get("cardholderGuid", "")
            status = a.get("status", "")
            error = a.get("error")
            line = f"- Access rule {rule_guid} → cardholder {ch_guid}: {status}"
            if error:
                line += f" ({error})"
            lines.append(line)
        return "\n".join(lines)
    except (RuntimeError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
async def cleanup_demo(ctx: Context) -> str:
    """Delete all demo entities from Security Center while preserving Cloudlink units.

    Deletes entities in dependency-safe order: access rules, alarms, doors,
    cardholders, credentials, and interface modules (Mercury controllers + boards).
    Cloudlink units are preserved.

    Returns:
        A summary of deleted entity counts per type, or an error message.
    """
    connection: GenetecConnection = ctx.request_context.lifespan_context.connection
    if not connection.is_connected:
        return "Error: Not connected to Security Center."
    try:
        result = connection.cleanup_demo()
        total = result.get("totalDeleted", 0)
        lines = [f"Demo cleanup complete. Deleted {total} entity(ies):\n"]
        for r in result.get("results", []):
            entity_type = r.get("entityType", "Unknown")
            found = r.get("found", 0)
            deleted = r.get("deleted", 0)
            errors = r.get("errors", [])
            line = f"- {entity_type}: {deleted}/{found} deleted"
            if errors:
                line += f" ({len(errors)} error(s))"
            lines.append(line)
        return "\n".join(lines)
    except RuntimeError as e:
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


@mcp.tool()
async def list_sessions(ctx: Context) -> str:
    """List active MCP sessions with tool call statistics.

    Returns session IDs, first/last activity timestamps, and call counts.
    Session data is kept in memory for up to 24 hours and is reloaded from
    today's log file on server restart.

    Returns:
        A formatted list of active sessions, or a message if no sessions exist.
    """
    tool_logger: ToolCallLogger = ctx.request_context.lifespan_context.tool_logger
    sessions = tool_logger.get_sessions()
    if not sessions:
        return "No active sessions found."
    lines = [f"Found {len(sessions)} session(s):\n"]
    for s in sessions:
        lines.append(
            f"- {s['session_id']} | calls: {s['call_count']} | "
            f"first: {s['first_activity']} | last: {s['last_activity']}"
        )
    return "\n".join(lines)


@mcp.tool()
async def get_session_logs(ctx: Context, session_id: str) -> str:
    """Get tool call log records for a specific session.

    Args:
        session_id: The 8-character session UID shown when the session started.

    Returns:
        A formatted list of tool call records (tool name, args, result, duration).
    """
    tool_logger: ToolCallLogger = ctx.request_context.lifespan_context.tool_logger
    records = tool_logger.get_session_logs(session_id)
    if not records:
        return f"No records found for session '{session_id}'."
    lines = [f"Found {len(records)} record(s) for session '{session_id}':\n"]
    for r in records:
        status = f"ERROR: {r.error}" if r.error else (r.result or "")
        lines.append(
            f"- [{r.timestamp}] {r.tool_name} ({r.duration_ms}ms)\n"
            f"  args: {r.arguments}\n"
            f"  result: {status}"
        )
    return "\n".join(lines)
