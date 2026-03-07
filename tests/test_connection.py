"""Tests for Genetec Security Center connection management."""

from genetec_mcp_server.sdk_loader import load_sdk


class TestEngineCreation:
    """Tests for Engine instantiation (requires config path override)."""

    def test_engine_can_be_instantiated(self):
        """Engine() constructor should succeed after SDK is loaded."""
        load_sdk()
        from Genetec.Sdk import Engine  # type: ignore[import-untyped]

        engine = Engine()
        assert engine is not None
        engine.Dispose()

    def test_engine_starts_disconnected(self):
        """A fresh Engine should not be connected."""
        load_sdk()
        from Genetec.Sdk import Engine  # type: ignore[import-untyped]

        engine = Engine()
        assert not engine.IsConnected
        engine.Dispose()


class TestGenetecConnection:
    """Tests for the GenetecConnection wrapper class."""

    def test_connection_can_be_created(self):
        """GenetecConnection should initialize without errors."""
        from genetec_mcp_server.connection import GenetecConnection

        conn = GenetecConnection()
        assert conn is not None
        conn.dispose()

    def test_connection_starts_disconnected(self):
        """A new GenetecConnection should not be connected."""
        from genetec_mcp_server.connection import GenetecConnection

        conn = GenetecConnection()
        assert not conn.is_connected
        conn.dispose()

    def test_connection_has_engine(self):
        """GenetecConnection should expose the underlying Engine."""
        from genetec_mcp_server.connection import GenetecConnection

        conn = GenetecConnection()
        assert conn.engine is not None
        conn.dispose()

    def test_connection_accepts_certificate(self):
        """GenetecConnection should accept a client certificate string."""
        from genetec_mcp_server.connection import GenetecConnection

        cert = "KxsD11z743Hf5Gq9mv3+5ekxzemlCiUXkTFY5ba1NOGcLCmGstt2n0zYE9NsNimv"
        conn = GenetecConnection(client_certificate=cert)
        assert conn is not None
        conn.dispose()

    def test_connection_handles_directory_cert_validation(self):
        """GenetecConnection should auto-accept directory certificates."""
        from genetec_mcp_server.connection import GenetecConnection

        conn = GenetecConnection()
        # The RequestDirectoryCertificateValidation handler should be registered
        assert conn.engine.LoginManager is not None
        conn.dispose()


class TestGetSystemVersion:
    """Tests for retrieving Security Center system version (requires live server)."""

    def test_get_system_version_returns_version_string(self):
        """get_system_version should return the SC version (e.g. '5.13.x.x')."""
        from genetec_mcp_server.connection import GenetecConnection

        conn = GenetecConnection()
        result = conn.connect()
        assert result == "Success", f"Connection failed: {conn.last_failure}"
        try:
            version = conn.get_system_version()
            assert isinstance(version, str)
            assert version.startswith("5.13"), f"Unexpected version: {version}"
        finally:
            conn.dispose()
