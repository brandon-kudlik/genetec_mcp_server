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

    def test_returns_guid_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"guid": "11111111-1111-1111-1111-111111111111", "message": "Mercury LP1502 'Mercury-01' added"}}
            )
            result = conn.add_mercury_controller(
                unit_guid="00000000-0000-0000-0000-000000000001",
                name="Mercury-01",
                controller_type="LP1502",
                ip_address="192.168.1.50",
            )
        assert result == "11111111-1111-1111-1111-111111111111"
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

    def test_returns_guid_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"guid": "22222222-2222-2222-2222-222222222222", "message": "MR50 'Board-01' added to controller"}}
            )
            result = conn.add_interface_module(
                unit_guid="00000000-0000-0000-0000-000000000001",
                controller_guid="00000000-0000-0000-0000-000000000002",
                name="Board-01",
                board_type="MR50",
            )
        assert result == "22222222-2222-2222-2222-222222222222"
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


class TestQueryCloudlinks:
    """Tests for querying Cloudlink units."""

    def test_returns_cloudlinks_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"cloudlinks": [
                    {"guid": "cl-guid-1", "name": "Cloudlink-01", "isOnline": True},
                    {"guid": "cl-guid-2", "name": "Cloudlink-02", "isOnline": False},
                ]}}
            )
            result = conn.query_cloudlinks()
        assert len(result) == 2
        assert result[0]["guid"] == "cl-guid-1"
        assert result[1]["name"] == "Cloudlink-02"
        conn.dispose()

    def test_returns_empty_list_when_none_found(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"cloudlinks": []}}
            )
            result = conn.query_cloudlinks()
        assert result == []
        conn.dispose()

    def test_calls_correct_endpoint(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"cloudlinks": []}}
            )
            conn.query_cloudlinks()
            mock_get.assert_called_once_with("/api/units/cloudlinks")
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": False, "error": "Not connected to Security Center."}
            )
            with pytest.raises(RuntimeError, match="Not connected"):
                conn.query_cloudlinks()
        conn.dispose()


class TestAddEventToAction:
    """Tests for adding event-to-action mappings."""

    def test_returns_result_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {
                    "message": "Added 2 event-to-action(s).",
                    "addedCount": 2,
                    "results": [
                        {"entityGuid": "door-1", "eventType": "DoorHeldTooLong", "status": "Added"},
                        {"entityGuid": "door-1", "eventType": "DoorForcedOpen", "status": "Added"},
                    ],
                }}
            )
            result = conn.add_event_to_action(mappings=[
                {
                    "entityGuid": "door-1",
                    "eventType": "DoorHeldTooLong",
                    "actionType": "TriggerAlarm",
                    "alarmGuid": "alarm-1",
                },
                {
                    "entityGuid": "door-1",
                    "eventType": "DoorForcedOpen",
                    "actionType": "TriggerAlarm",
                    "alarmGuid": "alarm-1",
                },
            ])
        assert result["addedCount"] == 2
        assert len(result["results"]) == 2
        conn.dispose()

    def test_requires_non_empty_mappings(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="mappings.*cannot be empty"):
            conn.add_event_to_action(mappings=[])
        conn.dispose()

    def test_requires_entity_guid(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="entityGuid"):
            conn.add_event_to_action(mappings=[{
                "eventType": "DoorHeldTooLong",
                "actionType": "TriggerAlarm",
                "alarmGuid": "alarm-1",
            }])
        conn.dispose()

    def test_requires_event_type(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="eventType"):
            conn.add_event_to_action(mappings=[{
                "entityGuid": "door-1",
                "actionType": "TriggerAlarm",
                "alarmGuid": "alarm-1",
            }])
        conn.dispose()

    def test_requires_action_type(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="actionType"):
            conn.add_event_to_action(mappings=[{
                "entityGuid": "door-1",
                "eventType": "DoorHeldTooLong",
                "alarmGuid": "alarm-1",
            }])
        conn.dispose()

    def test_sends_correct_post_body(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"message": "OK", "addedCount": 1, "results": []}}
            )
            mappings = [{
                "entityGuid": "door-1",
                "eventType": "DoorForcedOpen",
                "actionType": "TriggerAlarm",
                "alarmGuid": "alarm-1",
            }]
            conn.add_event_to_action(mappings=mappings)
            mock_post.assert_called_once_with(
                "/api/event-to-actions",
                json={"mappings": mappings},
            )
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": False, "error": "Entity not found."}
            )
            with pytest.raises(RuntimeError, match="Entity not found"):
                conn.add_event_to_action(mappings=[{
                    "entityGuid": "door-1",
                    "eventType": "DoorHeldTooLong",
                    "actionType": "TriggerAlarm",
                    "alarmGuid": "alarm-1",
                }])
        conn.dispose()


class TestCleanupDemo:
    """Tests for the cleanup_demo method."""

    def test_cleanup_demo_calls_delete_endpoint(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "delete") as mock_delete:
            mock_delete.return_value = _mock_response(
                {"success": True, "data": {"results": [], "totalDeleted": 0}}
            )
            conn.cleanup_demo()
            mock_delete.assert_called_once()
            call_args = mock_delete.call_args
            assert call_args[0][0] == "/api/cleanup/demo"
        conn.dispose()

    def test_cleanup_demo_returns_results(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "delete") as mock_delete:
            mock_delete.return_value = _mock_response(
                {"success": True, "data": {
                    "results": [
                        {"entityType": "AccessRule", "found": 2, "deleted": 2, "errors": []},
                        {"entityType": "Door", "found": 3, "deleted": 3, "errors": []},
                    ],
                    "totalDeleted": 5,
                }}
            )
            result = conn.cleanup_demo()
        assert result["totalDeleted"] == 5
        assert len(result["results"]) == 2
        assert result["results"][0]["entityType"] == "AccessRule"
        conn.dispose()

    def test_cleanup_demo_raises_on_error(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "delete") as mock_delete:
            mock_delete.return_value = _mock_response(
                {"success": False, "error": "Not connected to Security Center."}
            )
            with pytest.raises(RuntimeError, match="Not connected"):
                conn.cleanup_demo()
        conn.dispose()

    def test_cleanup_demo_uses_long_timeout(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "delete") as mock_delete:
            mock_delete.return_value = _mock_response(
                {"success": True, "data": {"results": [], "totalDeleted": 0}}
            )
            conn.cleanup_demo()
            call_args = mock_delete.call_args
            timeout = call_args.kwargs.get("timeout")
            assert timeout == 300.0
        conn.dispose()


class TestAssignCredential:
    """Tests for assigning credentials to cardholders."""

    def test_returns_response_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {
                    "credentialGuid": "cred-guid-1",
                    "cardholderGuid": "ch-guid-1",
                    "previousCardholderGuid": None,
                }}
            )
            result = conn.assign_credential(
                credential_guid="cred-guid-1",
                cardholder_guid="ch-guid-1",
            )
        assert result["credentialGuid"] == "cred-guid-1"
        assert result["cardholderGuid"] == "ch-guid-1"
        assert result["previousCardholderGuid"] is None
        conn.dispose()

    def test_sends_correct_post_body(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {
                    "credentialGuid": "cred-guid-1",
                    "cardholderGuid": "ch-guid-1",
                    "previousCardholderGuid": None,
                }}
            )
            conn.assign_credential(
                credential_guid="cred-guid-1",
                cardholder_guid="ch-guid-1",
            )
            mock_post.assert_called_once_with(
                "/api/credentials/assign",
                json={"credentialGuid": "cred-guid-1", "cardholderGuid": "ch-guid-1"},
            )
        conn.dispose()

    def test_requires_credential_guid(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="credential_guid"):
            conn.assign_credential(credential_guid="", cardholder_guid="ch-guid-1")
        conn.dispose()

    def test_requires_cardholder_guid(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="cardholder_guid"):
            conn.assign_credential(credential_guid="cred-guid-1", cardholder_guid="")
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": False, "error": "Credential not found."}
            )
            with pytest.raises(RuntimeError, match="Credential not found"):
                conn.assign_credential(
                    credential_guid="cred-guid-1",
                    cardholder_guid="ch-guid-1",
                )
        conn.dispose()


class TestQueryCardholders:
    """Tests for querying cardholders."""

    def test_returns_cardholders_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"cardholders": [
                    {"guid": "ch-guid-1", "firstName": "John", "lastName": "Doe", "emailAddress": "john@example.com", "mobilePhone": None, "status": "Active"},
                    {"guid": "ch-guid-2", "firstName": "Jane", "lastName": "Smith", "emailAddress": None, "mobilePhone": "+15551234567", "status": "Active"},
                ]}}
            )
            result = conn.query_cardholders()
        assert len(result) == 2
        assert result[0]["guid"] == "ch-guid-1"
        assert result[1]["firstName"] == "Jane"
        conn.dispose()

    def test_returns_empty_list_when_none_found(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"cardholders": []}}
            )
            result = conn.query_cardholders()
        assert result == []
        conn.dispose()

    def test_calls_correct_endpoint(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"cardholders": []}}
            )
            conn.query_cardholders()
            mock_get.assert_called_once_with("/api/cardholders")
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": False, "error": "Not connected to Security Center."}
            )
            with pytest.raises(RuntimeError, match="Not connected"):
                conn.query_cardholders()
        conn.dispose()


class TestQueryCredentials:
    """Tests for querying credentials."""

    def test_returns_credentials_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"credentials": [
                    {"guid": "cred-guid-1", "name": "Badge-001", "formatType": "Standard 26 bit", "cardholderGuid": "ch-guid-1", "cardholderName": "John Doe", "status": "Active"},
                    {"guid": "cred-guid-2", "name": "Badge-002", "formatType": "H10306", "cardholderGuid": None, "cardholderName": None, "status": "Active"},
                ]}}
            )
            result = conn.query_credentials()
        assert len(result) == 2
        assert result[0]["guid"] == "cred-guid-1"
        assert result[1]["name"] == "Badge-002"
        conn.dispose()

    def test_returns_empty_list_when_none_found(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"credentials": []}}
            )
            result = conn.query_credentials()
        assert result == []
        conn.dispose()

    def test_calls_correct_endpoint(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": True, "data": {"credentials": []}}
            )
            conn.query_credentials()
            mock_get.assert_called_once_with("/api/credentials")
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "get") as mock_get:
            mock_get.return_value = _mock_response(
                {"success": False, "error": "Not connected to Security Center."}
            )
            with pytest.raises(RuntimeError, match="Not connected"):
                conn.query_credentials()
        conn.dispose()


class TestCreateCredential:
    """Tests for creating credentials."""

    def test_returns_guid_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"guid": "cred-guid-123"}}
            )
            guid = conn.create_credential(
                name="Card-001",
                format_type="WiegandStandard26Bit",
                facility=100,
                card_id=12345,
            )
        assert guid == "cred-guid-123"
        conn.dispose()

    def test_requires_name(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="name"):
            conn.create_credential(
                name="",
                format_type="WiegandStandard26Bit",
                facility=100,
                card_id=12345,
            )
        conn.dispose()

    def test_requires_format_type(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="format_type"):
            conn.create_credential(
                name="Card-001",
                format_type="",
                facility=100,
                card_id=12345,
            )
        conn.dispose()

    def test_requires_valid_format_type(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="Unknown format_type"):
            conn.create_credential(
                name="Card-001",
                format_type="InvalidFormat",
            )
        conn.dispose()

    def test_sends_correct_post_body_wiegand(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"guid": "cred-guid-123"}}
            )
            conn.create_credential(
                name="Card-001",
                format_type="WiegandStandard26Bit",
                facility=100,
                card_id=12345,
                cardholder_guid="ch-guid-1",
            )
            call_args = mock_post.call_args
            body = call_args.kwargs.get("json") or call_args[1].get("json")
            assert body["name"] == "Card-001"
            assert body["formatType"] == "WiegandStandard26Bit"
            assert body["facility"] == 100
            assert body["cardId"] == 12345
            assert body["cardholderGuid"] == "ch-guid-1"
            mock_post.assert_called_once_with(
                "/api/credentials",
                json=body,
            )
        conn.dispose()

    def test_sends_keypad_format(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"guid": "cred-guid-456"}}
            )
            conn.create_credential(
                name="PIN-001",
                format_type="Keypad",
                code=1234,
            )
            call_args = mock_post.call_args
            body = call_args.kwargs.get("json") or call_args[1].get("json")
            assert body["formatType"] == "Keypad"
            assert body["code"] == 1234
        conn.dispose()

    def test_sends_license_plate_format(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"guid": "cred-guid-789"}}
            )
            conn.create_credential(
                name="Plate-001",
                format_type="LicensePlate",
                license_plate="ABC1234",
            )
            call_args = mock_post.call_args
            body = call_args.kwargs.get("json") or call_args[1].get("json")
            assert body["formatType"] == "LicensePlate"
            assert body["licensePlate"] == "ABC1234"
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": False, "error": "Failed to create credential."}
            )
            with pytest.raises(RuntimeError, match="Failed to create credential"):
                conn.create_credential(
                    name="Card-001",
                    format_type="WiegandStandard26Bit",
                    facility=100,
                    card_id=12345,
                )
        conn.dispose()
