"""Tests for the MCP server module."""

from unittest.mock import MagicMock, patch

import pytest


class TestServerModule:
    """Tests for server.py module structure."""

    def test_mcp_server_instance_exists(self):
        """The module should expose a FastMCP server instance named 'mcp'."""
        from genetec_mcp_server.server import mcp

        assert mcp is not None
        assert mcp.name == "Genetec Security Center"

    def test_get_system_version_tool_is_registered(self):
        """get_system_version should be registered as an MCP tool."""
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "get_system_version" in tool_names


class TestGetSystemVersionTool:
    """Tests for the get_system_version MCP tool function."""

    @pytest.mark.asyncio
    async def test_returns_version_when_connected(self):
        """Tool should return version string when connection is active."""
        from genetec_mcp_server.server import get_system_version

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.get_system_version.return_value = "5.13.3132.18"

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await get_system_version(mock_ctx)
        assert result == "5.13.3132.18"
        mock_conn.get_system_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        """Tool should return error message when not connected."""
        from genetec_mcp_server.server import get_system_version

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await get_system_version(mock_ctx)
        assert "not connected" in result.lower()


class TestCreateCardholderToolRegistration:
    """Tests for the create_cardholder MCP tool."""

    def test_create_cardholder_tool_is_registered(self):
        """create_cardholder should be registered as an MCP tool."""
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "create_cardholder" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        """Tool should return error message when not connected."""
        from genetec_mcp_server.server import create_cardholder

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_cardholder(mock_ctx, first_name="John", last_name="Doe")
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_guid_on_success(self):
        """Tool should return the new cardholder's GUID on success."""
        from genetec_mcp_server.server import create_cardholder

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_cardholder.return_value = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_cardholder(mock_ctx, first_name="John", last_name="Doe")
        assert "a1b2c3d4-e5f6-7890-abcd-ef1234567890" in result
        mock_conn.create_cardholder.assert_called_once_with(
            first_name="John",
            last_name="Doe",
            email=None,
            mobile_phone=None,
        )

    @pytest.mark.asyncio
    async def test_passes_optional_fields(self):
        """Tool should forward optional email and phone to connection."""
        from genetec_mcp_server.server import create_cardholder

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_cardholder.return_value = "guid-here"

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        await create_cardholder(
            mock_ctx,
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            mobile_phone="+15551234567",
        )
        mock_conn.create_cardholder.assert_called_once_with(
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            mobile_phone="+15551234567",
        )


class TestAddCloudlinkUnitTool:
    """Tests for the add_cloudlink_unit MCP tool."""

    def test_add_cloudlink_unit_tool_is_registered(self):
        """add_cloudlink_unit should be registered as an MCP tool."""
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "add_cloudlink_unit" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        """Tool should return error message when not connected."""
        from genetec_mcp_server.server import add_cloudlink_unit

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_cloudlink_unit(
            mock_ctx,
            name="Cloudlink-01",
            ip_address="192.168.1.100",
            username="admin",
            password="admin",
            access_manager_guid="00000000-0000-0000-0000-000000000001",
        )
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_guid_on_success(self):
        """Tool should return the new unit's GUID on success."""
        from genetec_mcp_server.server import add_cloudlink_unit

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.add_cloudlink_unit.return_value = "Cloudlink-01"

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_cloudlink_unit(
            mock_ctx,
            name="Cloudlink-01",
            ip_address="192.168.1.100",
            username="admin",
            password="admin",
            access_manager_guid="00000000-0000-0000-0000-000000000001",
        )
        assert "Cloudlink-01" in result
        assert "enrolled successfully" in result.lower()
        mock_conn.add_cloudlink_unit.assert_called_once_with(
            name="Cloudlink-01",
            ip_address="192.168.1.100",
            username="admin",
            password="admin",
            access_manager_guid="00000000-0000-0000-0000-000000000001",
        )

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        """Tool should return error message on RuntimeError."""
        from genetec_mcp_server.server import add_cloudlink_unit

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.add_cloudlink_unit.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_cloudlink_unit(
            mock_ctx,
            name="Cloudlink-01",
            ip_address="192.168.1.100",
            username="admin",
            password="admin",
            access_manager_guid="00000000-0000-0000-0000-000000000001",
        )
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestAddMercuryControllerTool:
    """Tests for the add_mercury_controller MCP tool."""

    def test_tool_is_registered(self):
        """add_mercury_controller should be registered as an MCP tool."""
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "add_mercury_controller" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        """Tool should return error message when not connected."""
        from genetec_mcp_server.server import add_mercury_controller

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_mercury_controller(
            mock_ctx,
            unit_guid="00000000-0000-0000-0000-000000000001",
            name="Mercury-01",
            controller_type="LP1502",
            ip_address="192.168.1.50",
        )
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_guid_on_success(self):
        """Tool should return the new controller's GUID on success."""
        from genetec_mcp_server.server import add_mercury_controller

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.add_mercury_controller.return_value = "11111111-1111-1111-1111-111111111111"

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_mercury_controller(
            mock_ctx,
            unit_guid="00000000-0000-0000-0000-000000000001",
            name="Mercury-01",
            controller_type="LP1502",
            ip_address="192.168.1.50",
        )
        assert "11111111-1111-1111-1111-111111111111" in result
        assert "GUID:" in result
        mock_conn.add_mercury_controller.assert_called_once_with(
            unit_guid="00000000-0000-0000-0000-000000000001",
            name="Mercury-01",
            controller_type="LP1502",
            ip_address="192.168.1.50",
            port=3001,
            channel=0,
        )

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        """Tool should return error message on RuntimeError."""
        from genetec_mcp_server.server import add_mercury_controller

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.add_mercury_controller.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_mercury_controller(
            mock_ctx,
            unit_guid="00000000-0000-0000-0000-000000000001",
            name="Mercury-01",
            controller_type="LP1502",
            ip_address="192.168.1.50",
        )
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestAddInterfaceModuleTool:
    """Tests for the add_interface_module MCP tool."""

    def test_tool_is_registered(self):
        """add_interface_module should be registered as an MCP tool."""
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "add_interface_module" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        """Tool should return error message when not connected."""
        from genetec_mcp_server.server import add_interface_module

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_interface_module(
            mock_ctx,
            unit_guid="00000000-0000-0000-0000-000000000001",
            controller_guid="00000000-0000-0000-0000-000000000002",
            name="Board-01",
            board_type="MR50",
        )
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_guid_on_success(self):
        """Tool should return the new interface module's GUID on success."""
        from genetec_mcp_server.server import add_interface_module

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.add_interface_module.return_value = "22222222-2222-2222-2222-222222222222"

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_interface_module(
            mock_ctx,
            unit_guid="00000000-0000-0000-0000-000000000001",
            controller_guid="00000000-0000-0000-0000-000000000002",
            name="Board-01",
            board_type="MR50",
        )
        assert "22222222-2222-2222-2222-222222222222" in result
        assert "GUID:" in result
        mock_conn.add_interface_module.assert_called_once_with(
            unit_guid="00000000-0000-0000-0000-000000000001",
            controller_guid="00000000-0000-0000-0000-000000000002",
            name="Board-01",
            board_type="MR50",
            address=0,
        )

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        """Tool should return error message on RuntimeError."""
        from genetec_mcp_server.server import add_interface_module

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.add_interface_module.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_interface_module(
            mock_ctx,
            unit_guid="00000000-0000-0000-0000-000000000001",
            controller_guid="00000000-0000-0000-0000-000000000002",
            name="Board-01",
            board_type="MR50",
        )
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestListIoDevicesTool:
    """Tests for the list_io_devices MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "list_io_devices" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import list_io_devices

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await list_io_devices(mock_ctx, interface_module_guid="im-guid-1")
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_formatted_device_list(self):
        from genetec_mcp_server.server import list_io_devices

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.list_io_devices.return_value = [
            {"guid": "dev-1", "name": "Input 1", "physicalName": "In1", "deviceType": "Input", "isOnline": True},
            {"guid": "dev-2", "name": "Reader 1", "physicalName": "Rdr1", "deviceType": "Reader", "isOnline": False},
        ]

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await list_io_devices(mock_ctx, interface_module_guid="im-guid-1")
        assert "dev-1" in result
        assert "Input 1" in result
        assert "Input" in result
        assert "dev-2" in result
        assert "Reader" in result
        mock_conn.list_io_devices.assert_called_once_with(interface_module_guid="im-guid-1")

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import list_io_devices

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.list_io_devices.side_effect = RuntimeError("Entity not found")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await list_io_devices(mock_ctx, interface_module_guid="im-guid-1")
        assert "error" in result.lower()
        assert "Entity not found" in result

    @pytest.mark.asyncio
    async def test_returns_no_devices_message(self):
        from genetec_mcp_server.server import list_io_devices

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.list_io_devices.return_value = []

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await list_io_devices(mock_ctx, interface_module_guid="im-guid-1")
        assert "no devices" in result.lower() or "0" in result


class TestConfigureIoDevicesTool:
    """Tests for the configure_io_devices MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "configure_io_devices" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import configure_io_devices

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await configure_io_devices(
            mock_ctx,
            interface_module_guid="im-guid-1",
            device_configs=[{"deviceGuid": "dev-1", "name": "Input 1"}],
        )
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_success_message(self):
        from genetec_mcp_server.server import configure_io_devices

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.configure_io_devices.return_value = {
            "message": "Configured 2 devices.",
            "configuredCount": 2,
        }

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await configure_io_devices(
            mock_ctx,
            interface_module_guid="im-guid-1",
            device_configs=[{"deviceGuid": "dev-1", "name": "Input 1"}],
        )
        assert "configured" in result.lower()
        mock_conn.configure_io_devices.assert_called_once_with(
            interface_module_guid="im-guid-1",
            device_configs=[{"deviceGuid": "dev-1", "name": "Input 1"}],
        )

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import configure_io_devices

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.configure_io_devices.side_effect = RuntimeError("Transaction failed")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await configure_io_devices(
            mock_ctx,
            interface_module_guid="im-guid-1",
            device_configs=[{"deviceGuid": "dev-1"}],
        )
        assert "error" in result.lower()
        assert "Transaction failed" in result


class TestCreateDoorsTool:
    """Tests for the create_doors MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "create_doors" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import create_doors

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_doors(
            mock_ctx,
            doors=[{"name": "Door 1"}],
        )
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_success_message(self):
        from genetec_mcp_server.server import create_doors

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_doors.return_value = {
            "results": [
                {"name": "Door 1", "guid": "door-guid-1", "status": "Created"},
            ],
            "createdCount": 1,
        }

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_doors(
            mock_ctx,
            doors=[{"name": "Door 1"}],
        )
        assert "1" in result
        assert "door-guid-1" in result
        mock_conn.create_doors.assert_called_once_with(
            doors=[{"name": "Door 1"}],
        )

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import create_doors

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_doors.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_doors(
            mock_ctx,
            doors=[{"name": "Door 1"}],
        )
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestConfigureDoorHardwareTool:
    """Tests for the configure_door_hardware MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "configure_door_hardware" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import configure_door_hardware

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await configure_door_hardware(
            mock_ctx,
            assignments=[{"doorGuid": "door-1", "hardware": {}}],
        )
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_success_message(self):
        from genetec_mcp_server.server import configure_door_hardware

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.configure_door_hardware.return_value = {
            "results": [
                {"doorGuid": "door-guid-1", "status": "Configured"},
            ],
            "configuredCount": 1,
        }

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await configure_door_hardware(
            mock_ctx,
            assignments=[{"doorGuid": "door-guid-1", "hardware": {"doorLockGuid": "lock-1"}}],
        )
        assert "1" in result
        mock_conn.configure_door_hardware.assert_called_once_with(
            assignments=[{"doorGuid": "door-guid-1", "hardware": {"doorLockGuid": "lock-1"}}],
        )

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import configure_door_hardware

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.configure_door_hardware.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await configure_door_hardware(
            mock_ctx,
            assignments=[{"doorGuid": "door-1", "hardware": {}}],
        )
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestCreateAlarmTool:
    """Tests for the create_alarm MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "create_alarm" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import create_alarm

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_alarm(mock_ctx, name="Fire Alarm")
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_guid_on_success(self):
        from genetec_mcp_server.server import create_alarm

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_alarm.return_value = "alarm-guid-123"

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_alarm(mock_ctx, name="Fire Alarm")
        assert "alarm-guid-123" in result
        mock_conn.create_alarm.assert_called_once_with(
            name="Fire Alarm",
            priority=None,
            reactivation_threshold=None,
        )

    @pytest.mark.asyncio
    async def test_passes_optional_fields(self):
        from genetec_mcp_server.server import create_alarm

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_alarm.return_value = "alarm-guid-456"

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        await create_alarm(mock_ctx, name="Intrusion", priority=3, reactivation_threshold=60)
        mock_conn.create_alarm.assert_called_once_with(
            name="Intrusion",
            priority=3,
            reactivation_threshold=60,
        )

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import create_alarm

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_alarm.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_alarm(mock_ctx, name="Fire Alarm")
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestQueryCloudlinkTool:
    """Tests for the query_cloudlink MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "query_cloudlink" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import query_cloudlink

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_cloudlink(mock_ctx)
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_formatted_cloudlink_list(self):
        from genetec_mcp_server.server import query_cloudlink

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.query_cloudlinks.return_value = [
            {"guid": "cl-guid-1", "name": "Cloudlink-01", "isOnline": True},
            {"guid": "cl-guid-2", "name": "Cloudlink-02", "isOnline": False},
        ]

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_cloudlink(mock_ctx)
        assert "cl-guid-1" in result
        assert "Cloudlink-01" in result
        assert "cl-guid-2" in result
        assert "Online" in result
        assert "Offline" in result
        mock_conn.query_cloudlinks.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_no_cloudlinks_message(self):
        from genetec_mcp_server.server import query_cloudlink

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.query_cloudlinks.return_value = []

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_cloudlink(mock_ctx)
        assert "no cloudlink" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import query_cloudlink

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.query_cloudlinks.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_cloudlink(mock_ctx)
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestAddEventToActionTool:
    """Tests for the add_event_to_action MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "add_event_to_action" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import add_event_to_action

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_event_to_action(mock_ctx, mappings=[{
            "entityGuid": "door-1",
            "eventType": "DoorHeldTooLong",
            "actionType": "TriggerAlarm",
            "alarmGuid": "alarm-1",
        }])
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_success_message(self):
        from genetec_mcp_server.server import add_event_to_action

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.add_event_to_action.return_value = {
            "results": [
                {"entityGuid": "door-1", "eventType": "DoorHeldTooLong", "status": "Added"},
                {"entityGuid": "door-1", "eventType": "DoorForcedOpen", "status": "Added"},
            ],
            "addedCount": 2,
        }

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_event_to_action(mock_ctx, mappings=[
            {"entityGuid": "door-1", "eventType": "DoorHeldTooLong", "actionType": "TriggerAlarm", "alarmGuid": "alarm-1"},
            {"entityGuid": "door-1", "eventType": "DoorForcedOpen", "actionType": "TriggerAlarm", "alarmGuid": "alarm-1"},
        ])
        assert "2" in result
        mock_conn.add_event_to_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import add_event_to_action

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.add_event_to_action.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_event_to_action(mock_ctx, mappings=[{
            "entityGuid": "door-1",
            "eventType": "DoorHeldTooLong",
            "actionType": "TriggerAlarm",
            "alarmGuid": "alarm-1",
        }])
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestCleanupDemoTool:
    """Tests for the cleanup_demo MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "cleanup_demo" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import cleanup_demo

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await cleanup_demo(mock_ctx)
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_summary_on_success(self):
        from genetec_mcp_server.server import cleanup_demo

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.cleanup_demo.return_value = {
            "results": [
                {"entityType": "AccessRule", "found": 2, "deleted": 2, "errors": []},
                {"entityType": "Door", "found": 3, "deleted": 3, "errors": []},
                {"entityType": "Cardholder", "found": 1, "deleted": 1, "errors": []},
            ],
            "totalDeleted": 6,
        }

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await cleanup_demo(mock_ctx)
        assert "6" in result
        assert "AccessRule" in result
        assert "Door" in result
        assert "Cardholder" in result
        mock_conn.cleanup_demo.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import cleanup_demo

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.cleanup_demo.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await cleanup_demo(mock_ctx)
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestAssignCredentialTool:
    """Tests for the assign_credential MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "assign_credential" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import assign_credential

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await assign_credential(
            mock_ctx,
            credential_guid="cred-guid-1",
            cardholder_guid="ch-guid-1",
        )
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_success_message(self):
        from genetec_mcp_server.server import assign_credential

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.assign_credential.return_value = {
            "credentialGuid": "cred-guid-1",
            "cardholderGuid": "ch-guid-1",
            "previousCardholderGuid": None,
        }

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await assign_credential(
            mock_ctx,
            credential_guid="cred-guid-1",
            cardholder_guid="ch-guid-1",
        )
        assert "cred-guid-1" in result
        assert "ch-guid-1" in result
        mock_conn.assign_credential.assert_called_once_with(
            credential_guid="cred-guid-1",
            cardholder_guid="ch-guid-1",
        )

    @pytest.mark.asyncio
    async def test_notes_reassignment(self):
        from genetec_mcp_server.server import assign_credential

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.assign_credential.return_value = {
            "credentialGuid": "cred-guid-1",
            "cardholderGuid": "ch-guid-2",
            "previousCardholderGuid": "ch-guid-1",
        }

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await assign_credential(
            mock_ctx,
            credential_guid="cred-guid-1",
            cardholder_guid="ch-guid-2",
        )
        assert "reassigned" in result.lower() or "previous" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import assign_credential

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.assign_credential.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await assign_credential(
            mock_ctx,
            credential_guid="cred-guid-1",
            cardholder_guid="ch-guid-1",
        )
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestQueryCardholdersTool:
    """Tests for the query_cardholders MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "query_cardholders" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import query_cardholders

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_cardholders(mock_ctx)
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_formatted_cardholder_list(self):
        from genetec_mcp_server.server import query_cardholders

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.query_cardholders.return_value = [
            {"guid": "ch-guid-1", "firstName": "John", "lastName": "Doe", "emailAddress": "john@example.com", "mobilePhone": None, "status": "Active"},
            {"guid": "ch-guid-2", "firstName": "Jane", "lastName": "Smith", "emailAddress": None, "mobilePhone": None, "status": "Inactive"},
        ]

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_cardholders(mock_ctx)
        assert "ch-guid-1" in result
        assert "John" in result
        assert "Doe" in result
        assert "john@example.com" in result
        assert "Active" in result
        assert "ch-guid-2" in result
        assert "Jane" in result
        assert "Inactive" in result
        mock_conn.query_cardholders.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_no_cardholders_message(self):
        from genetec_mcp_server.server import query_cardholders

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.query_cardholders.return_value = []

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_cardholders(mock_ctx)
        assert "no cardholder" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import query_cardholders

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.query_cardholders.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_cardholders(mock_ctx)
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestQueryCredentialsTool:
    """Tests for the query_credentials MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "query_credentials" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import query_credentials

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_credentials(mock_ctx)
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_formatted_credential_list(self):
        from genetec_mcp_server.server import query_credentials

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.query_credentials.return_value = [
            {"guid": "cred-guid-1", "name": "Badge-001", "formatType": "Standard 26 bit", "cardholderGuid": "ch-guid-1", "cardholderName": "John Doe", "status": "Active"},
            {"guid": "cred-guid-2", "name": "Badge-002", "formatType": "H10306", "cardholderGuid": None, "cardholderName": None, "status": "Active"},
        ]

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_credentials(mock_ctx)
        assert "cred-guid-1" in result
        assert "Badge-001" in result
        assert "Standard 26 bit" in result
        assert "John Doe" in result
        assert "cred-guid-2" in result
        assert "Badge-002" in result
        mock_conn.query_credentials.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_no_credentials_message(self):
        from genetec_mcp_server.server import query_credentials

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.query_credentials.return_value = []

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_credentials(mock_ctx)
        assert "no credential" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import query_credentials

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.query_credentials.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_credentials(mock_ctx)
        assert "error" in result.lower()
        assert "SDK failure" in result


class TestCreateCredentialTool:
    """Tests for the create_credential MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "create_credential" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import create_credential

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_credential(
            mock_ctx,
            name="Card-001",
            format_type="WiegandStandard26Bit",
            facility=100,
            card_id=12345,
        )
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_guid_on_success(self):
        from genetec_mcp_server.server import create_credential

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_credential.return_value = "cred-guid-123"

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_credential(
            mock_ctx,
            name="Card-001",
            format_type="WiegandStandard26Bit",
            facility=100,
            card_id=12345,
        )
        assert "cred-guid-123" in result
        mock_conn.create_credential.assert_called_once_with(
            name="Card-001",
            format_type="WiegandStandard26Bit",
            facility=100,
            card_id=12345,
            code=None,
            license_plate=None,
            raw_data=None,
            bit_length=None,
            cardholder_guid=None,
        )

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import create_credential

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_credential.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_credential(
            mock_ctx,
            name="Card-001",
            format_type="WiegandStandard26Bit",
        )
        assert "error" in result.lower()
        assert "SDK failure" in result

    @pytest.mark.asyncio
    async def test_passes_cardholder_guid(self):
        from genetec_mcp_server.server import create_credential

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_credential.return_value = "cred-guid-456"

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        await create_credential(
            mock_ctx,
            name="Card-002",
            format_type="WiegandStandard26Bit",
            facility=100,
            card_id=99999,
            cardholder_guid="ch-guid-1",
        )
        mock_conn.create_credential.assert_called_once_with(
            name="Card-002",
            format_type="WiegandStandard26Bit",
            facility=100,
            card_id=99999,
            code=None,
            license_plate=None,
            raw_data=None,
            bit_length=None,
            cardholder_guid="ch-guid-1",
        )


class TestLifespan:
    """Tests for the server lifespan (connection lifecycle)."""

    @pytest.mark.asyncio
    async def test_lifespan_connects_and_disposes(self):
        """Lifespan should connect on startup and dispose on shutdown."""
        from genetec_mcp_server.server import app_lifespan

        mock_server = MagicMock()

        with patch("genetec_mcp_server.server.GenetecConnection") as MockConn:
            mock_instance = MagicMock()
            mock_instance.connect.return_value = "Success"
            MockConn.return_value = mock_instance

            async with app_lifespan(mock_server) as context:
                assert context.connection is mock_instance
                mock_instance.connect.assert_called_once()

            mock_instance.dispose.assert_called_once()


class TestQueryAccessRulesTool:
    """Tests for the query_access_rules MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "query_access_rules" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import query_access_rules

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_access_rules(mock_ctx)
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_formatted_list(self):
        from genetec_mcp_server.server import query_access_rules

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.query_access_rules.return_value = [
            {"guid": "rule-guid-1", "name": "All Access"},
            {"guid": "rule-guid-2", "name": "Main Entrance"},
        ]

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_access_rules(mock_ctx)
        assert "All Access" in result
        assert "rule-guid-1" in result
        assert "Main Entrance" in result
        assert "rule-guid-2" in result

    @pytest.mark.asyncio
    async def test_returns_no_rules_message_when_empty(self):
        from genetec_mcp_server.server import query_access_rules

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.query_access_rules.return_value = []

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await query_access_rules(mock_ctx)
        assert "no access rules" in result.lower()


class TestAssignAccessRulesTool:
    """Tests for the assign_access_rules MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "assign_access_rules" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import assign_access_rules

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await assign_access_rules(mock_ctx, access_rule_guids=["rule-1"], cardholder_guids=["ch-1"])
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_assignment_results_on_success(self):
        from genetec_mcp_server.server import assign_access_rules

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.assign_access_rules.return_value = {
            "assignments": [
                {"accessRuleGuid": "rule-1", "cardholderGuid": "ch-1", "status": "Assigned", "error": None},
                {"accessRuleGuid": "rule-1", "cardholderGuid": "ch-2", "status": "Assigned", "error": None},
            ]
        }

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await assign_access_rules(
            mock_ctx,
            access_rule_guids=["rule-1"],
            cardholder_guids=["ch-1", "ch-2"],
        )
        assert "rule-1" in result
        assert "ch-1" in result
        assert "Assigned" in result
        mock_conn.assign_access_rules.assert_called_once_with(
            access_rule_guids=["rule-1"],
            cardholder_guids=["ch-1", "ch-2"],
        )

    @pytest.mark.asyncio
    async def test_shows_failures_in_output(self):
        from genetec_mcp_server.server import assign_access_rules

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.assign_access_rules.return_value = {
            "assignments": [
                {"accessRuleGuid": "rule-1", "cardholderGuid": "ch-1", "status": "Assigned", "error": None},
                {"accessRuleGuid": "rule-1", "cardholderGuid": "ch-bad", "status": "Failed", "error": "entity not found"},
            ]
        }

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await assign_access_rules(
            mock_ctx,
            access_rule_guids=["rule-1"],
            cardholder_guids=["ch-1", "ch-bad"],
        )
        assert "Failed" in result
        assert "entity not found" in result
        assert "Assigned" in result
