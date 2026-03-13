"""Tests for GenetecConnection HTTP client."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from genetec_mcp_server.connection import GenetecConnection


def _mock_response(json_data, status_code=200):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


class TestConnectionInit:
    """Tests for GenetecConnection initialization."""

    def test_connection_can_be_created(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        assert conn is not None
        conn.dispose()

    def test_default_base_url_from_config(self):
        conn = GenetecConnection()
        assert "localhost" in conn._base_url or "5100" in conn._base_url
        conn.dispose()


class TestConnect:
    """Tests for the connect method."""

    def test_connect_returns_success_when_healthy(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"isConnected": True, "serverVersion": "5.13.3132.18"}}
            )
            result = conn.connect()
        assert result == "Success"
        assert conn.is_connected is True
        assert conn.last_failure is None
        conn.dispose()

    def test_connect_returns_failed_when_not_connected(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"isConnected": False, "serverVersion": None}}
            )
            result = conn.connect()
        assert result == "Failed"
        assert conn.is_connected is False
        conn.dispose()

    def test_connect_returns_error_on_exception(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get", side_effect=httpx.ConnectError("refused")):
            result = conn.connect()
        assert "Error" in result
        assert conn.is_connected is False
        conn.dispose()


class TestGetSystemVersion:
    """Tests for get_system_version."""

    def test_returns_version_string(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"version": "5.13.3132.18"}}
            )
            version = conn.get_system_version()
        assert version == "5.13.3132.18"
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": False, "error": "Not connected to Security Center."}
            )
            with pytest.raises(RuntimeError, match="Not connected"):
                conn.get_system_version()
        conn.dispose()


class TestCreateCardholder:
    """Tests for creating cardholder entities."""

    def test_returns_guid_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}}
            )
            guid = conn.create_cardholder(first_name="John", last_name="Doe")
        assert guid == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        conn.dispose()

    def test_passes_optional_fields(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"guid": "guid-here"}}
            )
            conn.create_cardholder(
                first_name="Jane",
                last_name="Smith",
                email="jane@example.com",
                mobile_phone="+15551234567",
            )
            call_args = mock_post.call_args
            body = call_args.kwargs.get("json") or call_args[1].get("json")
            assert body["email"] == "jane@example.com"
            assert body["mobilePhone"] == "+15551234567"
        conn.dispose()

    def test_requires_first_name(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="first_name"):
            conn.create_cardholder(first_name="", last_name="Doe")
        conn.dispose()

    def test_requires_last_name(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="last_name"):
            conn.create_cardholder(first_name="John", last_name="")
        conn.dispose()


class TestAddCloudlinkUnit:
    """Tests for adding Cloudlink units."""

    def test_returns_name_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"name": "Cloudlink-01"}}
            )
            result = conn.add_cloudlink_unit(
                name="Cloudlink-01",
                ip_address="192.168.1.100",
                username="admin",
                password="admin",
                access_manager_guid="00000000-0000-0000-0000-000000000001",
            )
        assert result == "Cloudlink-01"
        conn.dispose()

    def test_requires_name(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="name"):
            conn.add_cloudlink_unit(
                name="",
                ip_address="192.168.1.100",
                username="admin",
                password="admin",
                access_manager_guid="00000000-0000-0000-0000-000000000001",
            )
        conn.dispose()

    def test_requires_ip_address(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="ip_address"):
            conn.add_cloudlink_unit(
                name="Cloudlink-01",
                ip_address="",
                username="admin",
                password="admin",
                access_manager_guid="00000000-0000-0000-0000-000000000001",
            )
        conn.dispose()

    def test_requires_access_manager_guid(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="access_manager_guid"):
            conn.add_cloudlink_unit(
                name="Cloudlink-01",
                ip_address="192.168.1.100",
                username="admin",
                password="admin",
                access_manager_guid="",
            )
        conn.dispose()


class TestAddMercuryController:
    """Tests for adding Mercury sub-controllers."""

    def test_returns_message_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"message": "Mercury LP1502 'Mercury-01' added"}}
            )
            result = conn.add_mercury_controller(
                unit_guid="00000000-0000-0000-0000-000000000001",
                name="Mercury-01",
                controller_type="LP1502",
                ip_address="192.168.1.50",
            )
        assert "Mercury" in result
        conn.dispose()

    def test_requires_unit_guid(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="unit_guid"):
            conn.add_mercury_controller(
                unit_guid="",
                name="Mercury-01",
                controller_type="LP1502",
                ip_address="192.168.1.50",
            )
        conn.dispose()

    def test_requires_name(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="name"):
            conn.add_mercury_controller(
                unit_guid="00000000-0000-0000-0000-000000000001",
                name="",
                controller_type="LP1502",
                ip_address="192.168.1.50",
            )
        conn.dispose()

    def test_requires_valid_controller_type(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="Unknown controller_type"):
            conn.add_mercury_controller(
                unit_guid="00000000-0000-0000-0000-000000000001",
                name="Mercury-01",
                controller_type="InvalidType",
                ip_address="192.168.1.50",
            )
        conn.dispose()

    def test_requires_ip_address(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="ip_address"):
            conn.add_mercury_controller(
                unit_guid="00000000-0000-0000-0000-000000000001",
                name="Mercury-01",
                controller_type="LP1502",
                ip_address="",
            )
        conn.dispose()


class TestAddInterfaceModule:
    """Tests for adding interface modules to Mercury controllers."""

    def test_returns_message_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"message": "MR50 'Board-01' added to controller"}}
            )
            result = conn.add_interface_module(
                controller_guid="00000000-0000-0000-0000-000000000001",
                name="Board-01",
                board_type="MR50",
            )
        assert "Board-01" in result
        conn.dispose()

    def test_requires_controller_guid(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="controller_guid"):
            conn.add_interface_module(
                controller_guid="",
                name="Board-01",
                board_type="MR50",
            )
        conn.dispose()

    def test_requires_name(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="name"):
            conn.add_interface_module(
                controller_guid="00000000-0000-0000-0000-000000000001",
                name="",
                board_type="MR50",
            )
        conn.dispose()

    def test_requires_valid_board_type(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="Unknown board_type"):
            conn.add_interface_module(
                controller_guid="00000000-0000-0000-0000-000000000001",
                name="Board-01",
                board_type="InvalidBoard",
            )
        conn.dispose()

    def test_requires_board_type(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="board_type"):
            conn.add_interface_module(
                controller_guid="00000000-0000-0000-0000-000000000001",
                name="Board-01",
                board_type="",
            )
        conn.dispose()
