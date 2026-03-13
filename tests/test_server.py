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
    async def test_returns_result_on_success(self):
        """Tool should return success message on successful enrollment."""
        from genetec_mcp_server.server import add_mercury_controller

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.add_mercury_controller.return_value = (
            "Mercury LP1502 'Mercury-01' added at 192.168.1.50 to unit 00000000-0000-0000-0000-000000000001"
        )

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await add_mercury_controller(
            mock_ctx,
            unit_guid="00000000-0000-0000-0000-000000000001",
            name="Mercury-01",
            controller_type="LP1502",
            ip_address="192.168.1.50",
        )
        assert "mercury" in result.lower()
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


class TestInspectSdkApiTool:
    """Tests for the inspect_sdk_api MCP tool."""

    def test_tool_is_registered(self):
        """inspect_sdk_api should be registered as an MCP tool."""
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "inspect_sdk_api" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        """Tool should return error message when not connected."""
        from genetec_mcp_server.server import inspect_sdk_api

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await inspect_sdk_api(mock_ctx)
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_json_on_success(self):
        """Tool should return JSON introspection data on success."""
        from genetec_mcp_server.server import inspect_sdk_api

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.get_sdk_introspection.return_value = {
            "relevantTypes": ["MercuryLP1502"],
            "runtimeManagerMethods": [],
        }

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await inspect_sdk_api(mock_ctx)
        import json
        parsed = json.loads(result)
        assert "relevantTypes" in parsed
        mock_conn.get_sdk_introspection.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        """Tool should return error message on RuntimeError."""
        from genetec_mcp_server.server import inspect_sdk_api

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.get_sdk_introspection.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await inspect_sdk_api(mock_ctx)
        assert "error" in result.lower()
        assert "SDK failure" in result


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
