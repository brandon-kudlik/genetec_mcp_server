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
                unit_guid="00000000-0000-0000-0000-000000000001",
                controller_guid="00000000-0000-0000-0000-000000000002",
                name="Board-01",
                board_type="MR50",
            )
        assert "Board-01" in result
        conn.dispose()

    def test_requires_unit_guid(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="unit_guid"):
            conn.add_interface_module(
                unit_guid="",
                controller_guid="00000000-0000-0000-0000-000000000002",
                name="Board-01",
                board_type="MR50",
            )
        conn.dispose()

    def test_requires_controller_guid(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="controller_guid"):
            conn.add_interface_module(
                unit_guid="00000000-0000-0000-0000-000000000001",
                controller_guid="",
                name="Board-01",
                board_type="MR50",
            )
        conn.dispose()

    def test_requires_name(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="name"):
            conn.add_interface_module(
                unit_guid="00000000-0000-0000-0000-000000000001",
                controller_guid="00000000-0000-0000-0000-000000000002",
                name="",
                board_type="MR50",
            )
        conn.dispose()

    def test_requires_valid_board_type(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="Unknown board_type"):
            conn.add_interface_module(
                unit_guid="00000000-0000-0000-0000-000000000001",
                controller_guid="00000000-0000-0000-0000-000000000002",
                name="Board-01",
                board_type="InvalidBoard",
            )
        conn.dispose()

    def test_requires_board_type(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="board_type"):
            conn.add_interface_module(
                unit_guid="00000000-0000-0000-0000-000000000001",
                controller_guid="00000000-0000-0000-0000-000000000002",
                name="Board-01",
                board_type="",
            )
        conn.dispose()


class TestListIoDevices:
    """Tests for listing IO devices on an interface module."""

    def test_returns_devices_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"devices": [
                    {"guid": "dev-guid-1", "name": "Input 1", "physicalName": "In1", "deviceType": "Input", "isOnline": True},
                    {"guid": "dev-guid-2", "name": "Output 1", "physicalName": "Out1", "deviceType": "Output", "isOnline": False},
                ]}}
            )
            result = conn.list_io_devices(interface_module_guid="im-guid-1")
        assert len(result) == 2
        assert result[0]["guid"] == "dev-guid-1"
        assert result[1]["deviceType"] == "Output"
        conn.dispose()

    def test_requires_interface_module_guid(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="interface_module_guid"):
            conn.list_io_devices(interface_module_guid="")
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": False, "error": "Entity not found."}
            )
            with pytest.raises(RuntimeError, match="Entity not found"):
                conn.list_io_devices(interface_module_guid="im-guid-1")
        conn.dispose()

    def test_calls_correct_endpoint(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"devices": []}}
            )
            conn.list_io_devices(interface_module_guid="im-guid-1")
            mock_get.assert_called_once_with("/api/interface-modules/im-guid-1/devices")
        conn.dispose()


class TestConfigureIoDevices:
    """Tests for configuring IO devices on an interface module."""

    def test_returns_result_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"message": "Configured 2 devices.", "configuredCount": 2}}
            )
            result = conn.configure_io_devices(
                interface_module_guid="im-guid-1",
                device_configs=[{"deviceGuid": "dev-1", "name": "Input 1"}],
            )
        assert result["configuredCount"] == 2
        conn.dispose()

    def test_requires_interface_module_guid(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="interface_module_guid"):
            conn.configure_io_devices(
                interface_module_guid="",
                device_configs=[{"deviceGuid": "dev-1"}],
            )
        conn.dispose()

    def test_requires_non_empty_device_configs(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="device_configs"):
            conn.configure_io_devices(
                interface_module_guid="im-guid-1",
                device_configs=[],
            )
        conn.dispose()

    def test_requires_device_guid_in_each_config(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="deviceGuid"):
            conn.configure_io_devices(
                interface_module_guid="im-guid-1",
                device_configs=[{"name": "Input 1"}],
            )
        conn.dispose()

    def test_sends_correct_post_body(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"message": "OK", "configuredCount": 1}}
            )
            configs = [{"deviceGuid": "dev-1", "name": "Input 1", "inputContactType": "NormallyOpen"}]
            conn.configure_io_devices(
                interface_module_guid="im-guid-1",
                device_configs=configs,
            )
            call_args = mock_post.call_args
            body = call_args.kwargs.get("json") or call_args[1].get("json")
            assert body["deviceConfigs"] == configs
            mock_post.assert_called_once_with(
                "/api/interface-modules/im-guid-1/devices/configure",
                json={"deviceConfigs": configs},
            )
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": False, "error": "Device not found."}
            )
            with pytest.raises(RuntimeError, match="Device not found"):
                conn.configure_io_devices(
                    interface_module_guid="im-guid-1",
                    device_configs=[{"deviceGuid": "dev-1"}],
                )
        conn.dispose()


class TestCreateDoors:
    """Tests for batch door creation."""

    def test_returns_results_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {
                    "results": [
                        {"name": "Door 1", "guid": "door-guid-1", "status": "Created"},
                        {"name": "Door 2", "guid": "door-guid-2", "status": "Created"},
                    ],
                    "createdCount": 2,
                }}
            )
            result = conn.create_doors(doors=[
                {"name": "Door 1"},
                {"name": "Door 2", "properties": {"relockDelayInSeconds": 5}},
            ])
        assert result["createdCount"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["guid"] == "door-guid-1"
        conn.dispose()

    def test_requires_non_empty_list(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="doors.*cannot be empty"):
            conn.create_doors(doors=[])
        conn.dispose()

    def test_requires_name_in_each_door(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="name"):
            conn.create_doors(doors=[{"properties": {}}])
        conn.dispose()

    def test_sends_correct_post_body(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"results": [], "createdCount": 0}}
            )
            doors = [{"name": "Door 1", "properties": {"relockDelayInSeconds": 5}}]
            conn.create_doors(doors=doors)
            call_args = mock_post.call_args
            body = call_args.kwargs.get("json") or call_args[1].get("json")
            assert body == {"doors": doors}
            mock_post.assert_called_once_with(
                "/api/doors/batch",
                json={"doors": doors},
            )
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": False, "error": "Failed to create doors."}
            )
            with pytest.raises(RuntimeError, match="Failed to create"):
                conn.create_doors(doors=[{"name": "Door 1"}])
        conn.dispose()


class TestConfigureDoorHardware:
    """Tests for batch door hardware configuration."""

    def test_returns_results_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {
                    "results": [
                        {"doorGuid": "door-guid-1", "status": "Configured"},
                    ],
                    "configuredCount": 1,
                }}
            )
            result = conn.configure_door_hardware(assignments=[
                {
                    "doorGuid": "door-guid-1",
                    "hardware": {
                        "entrySide": {"readerGuid": "reader-1"},
                        "doorLockGuid": "lock-1",
                    },
                },
            ])
        assert result["configuredCount"] == 1
        conn.dispose()

    def test_requires_non_empty_list(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="assignments.*cannot be empty"):
            conn.configure_door_hardware(assignments=[])
        conn.dispose()

    def test_requires_door_guid_in_each_assignment(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="doorGuid"):
            conn.configure_door_hardware(assignments=[{"hardware": {}}])
        conn.dispose()

    def test_sends_correct_post_body(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"results": [], "configuredCount": 0}}
            )
            assignments = [{"doorGuid": "door-1", "hardware": {"doorLockGuid": "lock-1"}}]
            conn.configure_door_hardware(assignments=assignments)
            mock_post.assert_called_once_with(
                "/api/doors/hardware/batch",
                json={"assignments": assignments},
            )
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": False, "error": "Door not found."}
            )
            with pytest.raises(RuntimeError, match="Door not found"):
                conn.configure_door_hardware(assignments=[{"doorGuid": "door-1", "hardware": {}}])
        conn.dispose()


class TestCreateAlarm:
    """Tests for creating alarms."""

    def test_returns_guid_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"guid": "alarm-guid-123"}}
            )
            guid = conn.create_alarm(name="Fire Alarm")
        assert guid == "alarm-guid-123"
        conn.dispose()

    def test_requires_name(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="name"):
            conn.create_alarm(name="")
        conn.dispose()

    def test_sends_correct_post_body(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"guid": "alarm-guid-123"}}
            )
            conn.create_alarm(name="Fire Alarm", priority=5, reactivation_threshold=30)
            call_args = mock_post.call_args
            body = call_args.kwargs.get("json") or call_args[1].get("json")
            assert body["name"] == "Fire Alarm"
            assert body["priority"] == 5
            assert body["reactivationThreshold"] == 30
            mock_post.assert_called_once_with(
                "/api/alarms",
                json=body,
            )
        conn.dispose()

    def test_sends_only_name_when_no_optionals(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"guid": "alarm-guid-123"}}
            )
            conn.create_alarm(name="Door Forced")
            call_args = mock_post.call_args
            body = call_args.kwargs.get("json") or call_args[1].get("json")
            assert body == {"name": "Door Forced"}
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": False, "error": "Failed to create alarm."}
            )
            with pytest.raises(RuntimeError, match="Failed to create alarm"):
                conn.create_alarm(name="Fire Alarm")
        conn.dispose()
