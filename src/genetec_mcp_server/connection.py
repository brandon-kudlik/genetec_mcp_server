"""HTTP client for the Genetec SDK Service."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from genetec_mcp_server.config import SDK_SERVICE_URL


class GenetecConnection:
    """HTTP client that communicates with the C# Genetec SDK Service.

    Replaces the previous pythonnet-based connection with REST calls
    to the C# SDK service running on localhost.
    """

    def __init__(self, base_url: Optional[str] = None) -> None:
        self._base_url = (base_url or SDK_SERVICE_URL).rstrip("/")
        self._client = httpx.Client(base_url=self._base_url, timeout=60.0)
        self._connected: Optional[bool] = None
        self._last_failure: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        """Check if the SDK service is connected to Security Center."""
        if self._connected is not None:
            return self._connected
        try:
            data = self._get("/api/health")
            self._connected = data.get("isConnected", False)
            return self._connected
        except Exception:
            return False

    @property
    def last_failure(self) -> Optional[str]:
        """Get the last connection failure message, if any."""
        return self._last_failure

    def connect(self) -> str:
        """Check connection status via the SDK service health endpoint.

        Returns:
            "Success" if the SDK service is connected, or an error string.
        """
        try:
            data = self._get("/api/health")
            if data.get("isConnected"):
                self._connected = True
                self._last_failure = None
                return "Success"
            self._connected = False
            self._last_failure = "SDK service not connected to Security Center."
            return "Failed"
        except Exception as e:
            self._connected = False
            self._last_failure = str(e)
            return f"Error: {e}"

    def get_system_version(self) -> str:
        """Get the Security Center version from the SDK service.

        Returns:
            Version string (e.g. '5.13.3132.18').

        Raises:
            RuntimeError: If not connected or query fails.
        """
        data = self._get("/api/system/version")
        return data["version"]

    def create_cardholder(
        self,
        first_name: str,
        last_name: str,
        email: Optional[str] = None,
        mobile_phone: Optional[str] = None,
    ) -> str:
        """Create a new cardholder entity via the SDK service.

        Args:
            first_name: Cardholder's first name (required).
            last_name: Cardholder's last name (required).
            email: Email address (optional).
            mobile_phone: Mobile phone number (optional).

        Returns:
            The GUID string of the newly created cardholder.

        Raises:
            ValueError: If first_name or last_name is empty.
            RuntimeError: If the SDK service returns an error.
        """
        if not first_name:
            raise ValueError("first_name is required and cannot be empty.")
        if not last_name:
            raise ValueError("last_name is required and cannot be empty.")

        body: dict[str, Any] = {"firstName": first_name, "lastName": last_name}
        if email:
            body["email"] = email
        if mobile_phone:
            body["mobilePhone"] = mobile_phone

        data = self._post("/api/cardholders", body)
        return data["guid"]

    def add_cloudlink_unit(
        self,
        name: str,
        ip_address: str,
        username: str,
        password: str,
        access_manager_guid: str,
    ) -> str:
        """Enroll a Synergis Cloudlink unit via the SDK service.

        Args:
            name: Display name for the unit.
            ip_address: IP address or hostname of the Cloudlink device.
            username: Admin username for the Cloudlink unit.
            password: Admin password for the Cloudlink unit.
            access_manager_guid: GUID of the Access Manager role.

        Returns:
            The name of the enrolled unit.

        Raises:
            ValueError: If any required parameter is empty.
            RuntimeError: If the SDK service returns an error.
        """
        if not name:
            raise ValueError("name is required and cannot be empty.")
        if not ip_address:
            raise ValueError("ip_address is required and cannot be empty.")
        if not access_manager_guid:
            raise ValueError("access_manager_guid is required and cannot be empty.")

        data = self._post("/api/units/cloudlink", {
            "name": name,
            "ipAddress": ip_address,
            "username": username,
            "password": password,
            "accessManagerGuid": access_manager_guid,
        })
        return data["name"]

    INTERFACE_BOARD_TYPES = {
        "MR50", "MR51e", "MR52", "MR62e", "MR16In", "MR16Out",
        "MSACS", "MSI8S", "MSR8S",
        "M516Do", "M516Dor", "M520In", "M52K", "M52RP", "M52SRP", "M58RP",
    }

    MERCURY_CONTROLLER_TYPES = {
        "EP1501", "EP1501WithExpansion", "EP1502", "EP2500", "EP4502",
        "LP1501", "LP1501WithExpansion", "LP1502", "LP2500", "LP4502",
        "MP1501", "MP1501WithExpansion", "MP1502", "MP2500", "MP4502",
        "M5IC", "MSICS",
    }

    def add_mercury_controller(
        self,
        unit_guid: str,
        name: str,
        controller_type: str,
        ip_address: str,
        port: int = 3001,
        channel: int = 0,
    ) -> str:
        """Add a Mercury sub-controller via the SDK service.

        Args:
            unit_guid: GUID of the parent Cloudlink unit.
            name: Display name for the interface module.
            controller_type: Mercury model (e.g. 'LP1502').
            ip_address: IP address of the Mercury controller.
            port: TCP port (default 3001).
            channel: Channel number (default 0).

        Returns:
            The GUID string of the newly created Mercury controller.

        Raises:
            ValueError: If any required parameter is empty or type is invalid.
            RuntimeError: If the SDK service returns an error.
        """
        if not unit_guid:
            raise ValueError("unit_guid is required and cannot be empty.")
        if not name:
            raise ValueError("name is required and cannot be empty.")
        if not controller_type:
            raise ValueError("controller_type is required and cannot be empty.")
        if controller_type not in self.MERCURY_CONTROLLER_TYPES:
            raise ValueError(
                f"Unknown controller_type '{controller_type}'. "
                f"Valid types: {sorted(self.MERCURY_CONTROLLER_TYPES)}"
            )
        if not ip_address:
            raise ValueError("ip_address is required and cannot be empty.")

        data = self._post(f"/api/units/{unit_guid}/mercury", {
            "name": name,
            "controllerType": controller_type,
            "ipAddress": ip_address,
            "port": port,
            "channel": channel,
        })
        return data["guid"]

    def add_interface_module(
        self,
        unit_guid: str,
        controller_guid: str,
        name: str,
        board_type: str,
        address: int = 0,
    ) -> str:
        """Add an interface module (MR50, MR52, etc.) to a Mercury controller.

        Args:
            unit_guid: GUID of the parent Cloudlink unit.
            controller_guid: GUID of the parent Mercury controller.
            name: Display name for the interface board.
            board_type: Board model (e.g. 'MR50', 'MR52', 'MR16In', 'MR16Out').
            address: SIO bus address (default 0).

        Returns:
            The GUID string of the newly created interface module.

        Raises:
            ValueError: If any required parameter is empty or type is invalid.
            RuntimeError: If the SDK service returns an error.
        """
        if not unit_guid:
            raise ValueError("unit_guid is required and cannot be empty.")
        if not controller_guid:
            raise ValueError("controller_guid is required and cannot be empty.")
        if not name:
            raise ValueError("name is required and cannot be empty.")
        if not board_type:
            raise ValueError("board_type is required and cannot be empty.")
        if board_type not in self.INTERFACE_BOARD_TYPES:
            raise ValueError(
                f"Unknown board_type '{board_type}'. "
                f"Valid types: {sorted(self.INTERFACE_BOARD_TYPES)}"
            )

        data = self._post(f"/api/units/{unit_guid}/controllers/{controller_guid}/interface-modules", {
            "name": name,
            "boardType": board_type,
            "address": address,
        })
        return data["guid"]

    def list_io_devices(self, interface_module_guid: str) -> list[dict[str, Any]]:
        """List IO devices on an interface module.

        Args:
            interface_module_guid: GUID of the interface module.

        Returns:
            List of device dicts with guid, name, physicalName, deviceType, isOnline.

        Raises:
            ValueError: If interface_module_guid is empty.
            RuntimeError: If the SDK service returns an error.
        """
        if not interface_module_guid:
            raise ValueError("interface_module_guid is required and cannot be empty.")

        data = self._get(f"/api/interface-modules/{interface_module_guid}/devices")
        return data.get("devices", [])

    def configure_io_devices(
        self,
        interface_module_guid: str,
        device_configs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Configure IO devices on an interface module.

        Args:
            interface_module_guid: GUID of the interface module.
            device_configs: List of device configuration dicts. Each must contain
                'deviceGuid' and optionally 'name', 'inputContactType', 'debounce',
                'shunted', 'outputContactType'.

        Returns:
            Response dict with message and configuredCount.

        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If the SDK service returns an error.
        """
        if not interface_module_guid:
            raise ValueError("interface_module_guid is required and cannot be empty.")
        if not device_configs:
            raise ValueError("device_configs is required and cannot be empty.")
        for config in device_configs:
            if not config.get("deviceGuid"):
                raise ValueError("Each device config must contain a 'deviceGuid'.")

        return self._post(
            f"/api/interface-modules/{interface_module_guid}/devices/configure",
            {"deviceConfigs": device_configs},
        )

    def create_doors(self, doors: list[dict[str, Any]]) -> dict[str, Any]:
        """Batch create door entities via the SDK service.

        Args:
            doors: List of door dicts. Each must contain 'name' and optionally
                'properties' with timing/event settings.

        Returns:
            Response dict with 'results' list and 'createdCount'.

        Raises:
            ValueError: If doors list is empty or a door is missing 'name'.
            RuntimeError: If the SDK service returns an error.
        """
        if not doors:
            raise ValueError("doors is required and cannot be empty.")
        for door in doors:
            if not door.get("name"):
                raise ValueError("Each door must contain a 'name'.")

        return self._post("/api/doors/batch", {"doors": doors})

    def configure_door_hardware(self, assignments: list[dict[str, Any]]) -> dict[str, Any]:
        """Batch configure door hardware associations via the SDK service.

        Args:
            assignments: List of assignment dicts. Each must contain 'doorGuid'
                and 'hardware' with entrySide/exitSide/doorLockGuid.

        Returns:
            Response dict with 'results' list and 'configuredCount'.

        Raises:
            ValueError: If assignments list is empty or missing 'doorGuid'.
            RuntimeError: If the SDK service returns an error.
        """
        if not assignments:
            raise ValueError("assignments is required and cannot be empty.")
        for assignment in assignments:
            if not assignment.get("doorGuid"):
                raise ValueError("Each assignment must contain a 'doorGuid'.")

        return self._post("/api/doors/hardware/batch", {"assignments": assignments})

    def create_alarm(
        self,
        name: str,
        priority: Optional[int] = None,
        reactivation_threshold: Optional[int] = None,
    ) -> str:
        """Create an alarm entity via the SDK service.

        Args:
            name: Display name for the alarm (required).
            priority: Alarm priority level 1-255 (optional). Lower values = higher priority.
            reactivation_threshold: Seconds before the alarm can re-trigger (optional).

        Returns:
            The GUID string of the newly created alarm.

        Raises:
            ValueError: If name is empty.
            RuntimeError: If the SDK service returns an error.
        """
        if not name:
            raise ValueError("name is required and cannot be empty.")

        body: dict[str, Any] = {"name": name}
        if priority is not None:
            body["priority"] = priority
        if reactivation_threshold is not None:
            body["reactivationThreshold"] = reactivation_threshold

        data = self._post("/api/alarms", body)
        return data["guid"]

    def create_access_rules(self, access_rules: list[dict[str, Any]]) -> dict[str, Any]:
        """Batch create access rules and assign doors via the SDK service.

        Args:
            access_rules: List of access rule dicts. Each must contain 'name'
                and optionally 'doorGuids' (list of door GUID strings) and
                'side' ('Both', 'In', or 'Out').

        Returns:
            Response dict with 'results' list and 'createdCount'.

        Raises:
            ValueError: If access_rules list is empty or a rule is missing 'name'.
            RuntimeError: If the SDK service returns an error.
        """
        if not access_rules:
            raise ValueError("access_rules is required and cannot be empty.")
        for rule in access_rules:
            if not rule.get("name"):
                raise ValueError("Each access rule must contain a 'name'.")

        return self._post("/api/access-rules/batch", {"accessRules": access_rules})

    def query_cloudlinks(self) -> list[dict[str, Any]]:
        """Query all Cloudlink access control units in Security Center.

        Returns:
            List of Cloudlink dicts with guid, name, isOnline.

        Raises:
            RuntimeError: If the SDK service returns an error.
        """
        data = self._get("/api/units/cloudlinks")
        return data.get("cloudlinks", [])

    def add_event_to_action(self, mappings: list[dict[str, Any]]) -> dict[str, Any]:
        """Add event-to-action mappings to entities via the SDK service.

        Args:
            mappings: List of mapping dicts. Each must contain:
                - entityGuid (str): GUID of the source entity (e.g. door).
                - eventType (str): Event type name (e.g. 'DoorHeldTooLong', 'DoorForcedOpen').
                - actionType (str): Action type name (e.g. 'TriggerAlarm').
                - alarmGuid (str, optional): GUID of the alarm to trigger (for TriggerAlarm actions).

        Returns:
            Response dict with 'results' list and 'addedCount'.

        Raises:
            ValueError: If mappings are invalid.
            RuntimeError: If the SDK service returns an error.
        """
        if not mappings:
            raise ValueError("mappings is required and cannot be empty.")
        for m in mappings:
            if not m.get("entityGuid"):
                raise ValueError("Each mapping must contain an 'entityGuid'.")
            if not m.get("eventType"):
                raise ValueError("Each mapping must contain an 'eventType'.")
            if not m.get("actionType"):
                raise ValueError("Each mapping must contain an 'actionType'.")

        return self._post("/api/event-to-actions", {"mappings": mappings})

    CREDENTIAL_FORMAT_TYPES = {
        "WiegandStandard26Bit", "WiegandH10306", "WiegandH10304",
        "WiegandH10302", "WiegandCsn32", "WiegandCorporate1000",
        "Wiegand48BitCorporate1000", "Keypad", "LicensePlate", "RawCard",
    }

    def create_credential(
        self,
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
        """Create a credential entity via the SDK service.

        Args:
            name: Display name for the credential (required).
            format_type: Credential format type (required). Valid types:
                WiegandStandard26Bit, WiegandH10306, WiegandH10304,
                WiegandH10302, WiegandCsn32, WiegandCorporate1000,
                Wiegand48BitCorporate1000, Keypad, LicensePlate, RawCard.
            facility: Facility code (for Wiegand formats).
            card_id: Card ID number (for Wiegand formats).
            code: PIN code (for Keypad format).
            license_plate: License plate string (for LicensePlate format).
            raw_data: Raw hex data string (for RawCard format).
            bit_length: Bit length (for RawCard format).
            cardholder_guid: GUID of cardholder to assign credential to (optional).

        Returns:
            The GUID string of the newly created credential.

        Raises:
            ValueError: If required parameters are missing or format_type is invalid.
            RuntimeError: If the SDK service returns an error.
        """
        if not name:
            raise ValueError("name is required and cannot be empty.")
        if not format_type:
            raise ValueError("format_type is required and cannot be empty.")
        if format_type not in self.CREDENTIAL_FORMAT_TYPES:
            raise ValueError(
                f"Unknown format_type '{format_type}'. "
                f"Valid types: {sorted(self.CREDENTIAL_FORMAT_TYPES)}"
            )

        body: dict[str, Any] = {"name": name, "formatType": format_type}
        if facility is not None:
            body["facility"] = facility
        if card_id is not None:
            body["cardId"] = card_id
        if code is not None:
            body["code"] = code
        if license_plate is not None:
            body["licensePlate"] = license_plate
        if raw_data is not None:
            body["rawData"] = raw_data
        if bit_length is not None:
            body["bitLength"] = bit_length
        if cardholder_guid is not None:
            body["cardholderGuid"] = cardholder_guid

        data = self._post("/api/credentials", body)
        return data["guid"]

    def cleanup_demo(self) -> dict[str, Any]:
        """Delete all demo entities (cardholders, doors, alarms, access rules, etc.)
        while preserving enrolled Cloudlink units.

        Returns:
            Response dict with 'results' (per-type counts) and 'totalDeleted'.

        Raises:
            RuntimeError: If the SDK service returns an error.
        """
        return self._delete("/api/cleanup/demo")

    def disconnect(self) -> None:
        """No-op; the SDK service manages its own connection."""

    def dispose(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def _get(self, path: str) -> dict[str, Any]:
        """Make a GET request and return the data field."""
        resp = self._client.get(path)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            error = body.get("error", "Unknown error from SDK service.")
            raise RuntimeError(error)
        return body.get("data", {})

    def _delete(self, path: str) -> dict[str, Any]:
        """Make a DELETE request and return the data field."""
        resp = self._client.delete(path, timeout=300.0)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            error = body.get("error", "Unknown error from SDK service.")
            raise RuntimeError(error)
        return body.get("data", {})

    def _post(self, path: str, json_body: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request and return the data field."""
        resp = self._client.post(path, json=json_body)
        if resp.status_code == 400:
            body = resp.json()
            raise ValueError(body.get("error", "Bad request."))
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            error = body.get("error", "Unknown error from SDK service.")
            raise RuntimeError(error)
        return body.get("data", {})
