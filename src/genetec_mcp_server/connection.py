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

    def disconnect(self) -> None:
        """Disconnect from Security Center."""
        if self.is_connected:
            self._engine.LoginManager.LogOff()

    def dispose(self) -> None:
        """Dispose of the engine resources."""
        self.disconnect()
        self._engine.Dispose()
