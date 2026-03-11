"""Manage connection to Genetec Security Center."""

from __future__ import annotations

import threading
from typing import Optional

from genetec_mcp_server.config import CLIENT_CERTIFICATE, PASSWORD, SERVER, USERNAME
from genetec_mcp_server.sdk_loader import load_sdk


class GenetecConnection:
    """Manages an SDK Engine connection to Security Center.

    Handles Engine lifecycle, certificate configuration, directory
    certificate validation, and login/logout operations.
    """

    def __init__(
        self,
        client_certificate: Optional[str] = None,
    ) -> None:
        load_sdk()

        from Genetec.Sdk import Engine  # type: ignore[import-untyped]

        self._engine = Engine()
        self._last_failure: Optional[str] = None

        # Set SDK client certificate for authentication
        cert = client_certificate or CLIENT_CERTIFICATE
        if cert:
            self._engine.ClientCertificate = cert

        # Auto-accept directory TLS certificates (Security Center 5.4+)
        self._engine.LoginManager.RequestDirectoryCertificateValidation += (
            self._on_directory_certificate_validation
        )

    @staticmethod
    def _on_directory_certificate_validation(sender, e) -> None:  # type: ignore[no-untyped-def]
        """Accept the directory server's TLS certificate."""
        e.AcceptDirectory = True

    @property
    def engine(self):  # type: ignore[no-untyped-def]
        """Get the underlying SDK Engine instance."""
        return self._engine

    @property
    def is_connected(self) -> bool:
        """Check if connected to Security Center."""
        return bool(self._engine.IsConnected)

    @property
    def last_failure(self) -> Optional[str]:
        """Get the last connection failure message, if any."""
        return self._last_failure

    def connect(
        self,
        server: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 30.0,
    ) -> str:
        """Connect to Security Center.

        Uses BeginLogOn with event callbacks to avoid the deadlock that
        occurs when calling LogOnAsync().Result from Python's main thread.

        Args:
            server: Directory server address. Defaults to config.
            username: Username. Defaults to config. Empty = Windows auth.
            password: Password. Defaults to config.
            timeout: Max seconds to wait for connection. Default 30.

        Returns:
            "Success" if connected, or the failure code/message.
        """
        server = server or SERVER
        username = username or USERNAME
        password = password or PASSWORD

        login_manager = self._engine.LoginManager
        login_manager.ConnectionRetry = 1

        done = threading.Event()
        result_holder: list[str] = []

        def on_logged_on(sender, e):  # type: ignore[no-untyped-def]
            self._last_failure = None
            result_holder.append("Success")
            done.set()

        def on_failed(sender, e):  # type: ignore[no-untyped-def]
            msg = str(e.FormattedErrorMessage)
            self._last_failure = msg
            result_holder.append(str(e.FailureCode))
            done.set()

        login_manager.LoggedOn += on_logged_on
        login_manager.LogonFailed += on_failed

        try:
            if username:
                login_manager.BeginLogOn(server, username, password)
            else:
                login_manager.BeginLogOnUsingWindowsCredential(server)

            if done.wait(timeout=timeout):
                return result_holder[0] if result_holder else "Unknown"
            return "Timeout"
        finally:
            login_manager.LoggedOn -= on_logged_on
            login_manager.LogonFailed -= on_failed

    def get_system_version(self) -> str:
        """Get the Security Center version from the directory server.

        Returns:
            Version string (e.g. '5.13.3132.18').

        Raises:
            RuntimeError: If not connected or no server entity found.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Security Center.")

        from Genetec.Sdk import EntityType, ReportType  # type: ignore[import-untyped]

        query = self._engine.ReportManager.CreateReportQuery(
            ReportType.EntityConfiguration
        )
        query.EntityTypeFilter.Add(EntityType.Server)
        results = query.Query()

        import System  # type: ignore[import-untyped]

        for row in results.Data.Rows:
            guid = System.Guid(str(row["Guid"]))
            server = self._engine.GetEntity(guid)
            if server is not None:
                return str(server.Version)

        raise RuntimeError("No server entity found in Security Center.")

    def create_cardholder(
        self,
        first_name: str,
        last_name: str,
        email: Optional[str] = None,
        mobile_phone: Optional[str] = None,
    ) -> str:
        """Create a new cardholder entity in Security Center.

        Args:
            first_name: Cardholder's first name (required).
            last_name: Cardholder's last name (required).
            email: Email address (optional).
            mobile_phone: Mobile phone number (optional).

        Returns:
            The GUID string of the newly created cardholder.

        Raises:
            RuntimeError: If not connected to Security Center.
            ValueError: If first_name or last_name is empty.
        """
        if not first_name:
            raise ValueError("first_name is required and cannot be empty.")
        if not last_name:
            raise ValueError("last_name is required and cannot be empty.")
        if not self.is_connected:
            raise RuntimeError("Not connected to Security Center.")

        from Genetec.Sdk import EntityType  # type: ignore[import-untyped]

        entity_name = f"{first_name} {last_name}"
        cardholder = self._engine.CreateEntity(entity_name, EntityType.Cardholder)

        cardholder.FirstName = first_name
        cardholder.LastName = last_name

        if email:
            cardholder.EmailAddress = email
        if mobile_phone:
            cardholder.MobilePhoneNumber = mobile_phone

        return str(cardholder.Guid)

    def add_cloudlink_unit(
        self,
        name: str,
        ip_address: str,
        username: str,
        password: str,
        access_manager_guid: str,
    ) -> str:
        """Enroll a Synergis Cloudlink unit into an Access Manager role.

        Args:
            name: Display name for the unit.
            ip_address: IP address or hostname of the Cloudlink device.
            username: Admin username for the Cloudlink unit.
            password: Admin password for the Cloudlink unit.
            access_manager_guid: GUID of the Access Manager role to assign to.

        Returns:
            The GUID string of the newly created unit entity.

        Raises:
            RuntimeError: If not connected to Security Center.
            ValueError: If any required parameter is empty.
        """
        if not name:
            raise ValueError("name is required and cannot be empty.")
        if not ip_address:
            raise ValueError("ip_address is required and cannot be empty.")
        if not access_manager_guid:
            raise ValueError("access_manager_guid is required and cannot be empty.")
        if not self.is_connected:
            raise RuntimeError("Not connected to Security Center.")

        from Genetec.Sdk import EntityType  # type: ignore[import-untyped]

        import System  # type: ignore[import-untyped]

        # Find UnitExtensionType enum via reflection — namespace varies by SDK version
        unit_ext_type_cls = None
        for asm in System.AppDomain.CurrentDomain.GetAssemblies():
            for t in asm.GetTypes():
                if t.Name == "UnitExtensionType" and t.IsEnum:
                    unit_ext_type_cls = t
                    break
            if unit_ext_type_cls is not None:
                break

        if unit_ext_type_cls is None:
            raise RuntimeError(
                "Could not find UnitExtensionType enum in loaded SDK assemblies."
            )

        cloudlink_value = System.Enum.Parse(unit_ext_type_cls, "CloudLink")

        # Create the unit entity
        unit = self._engine.CreateEntity(name, EntityType.Unit)
        unit.IPAddress = ip_address
        unit.UnitExtensionType = cloudlink_value

        # Set credentials for the unit
        unit.SetCredentials(username, password)

        # Assign the unit to the Access Manager role
        role_guid = System.Guid(access_manager_guid)
        unit_guid = unit.Guid
        self._engine.ActionManager.MoveAccessControlUnit(unit_guid, role_guid)

        return str(unit_guid)

    def disconnect(self) -> None:
        """Disconnect from Security Center."""
        if self.is_connected:
            self._engine.LoginManager.LogOff()

    def dispose(self) -> None:
        """Dispose of the engine resources."""
        self.disconnect()
        self._engine.Dispose()
