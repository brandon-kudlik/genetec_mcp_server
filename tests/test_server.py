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
