"""Tests for Genetec Security Center connection management."""

import pytest

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


class TestCreateCardholder:
    """Tests for creating cardholder entities."""

    def test_create_cardholder_raises_when_not_connected(self):
        """create_cardholder should raise RuntimeError if not connected."""
        from genetec_mcp_server.connection import GenetecConnection

        conn = GenetecConnection()
        try:
            with pytest.raises(RuntimeError, match="Not connected"):
                conn.create_cardholder(first_name="John", last_name="Doe")
        finally:
            conn.dispose()

    def test_create_cardholder_requires_first_and_last_name(self):
        """create_cardholder should raise ValueError if names are empty."""
        from genetec_mcp_server.connection import GenetecConnection

        conn = GenetecConnection()
        try:
            with pytest.raises(ValueError, match="first_name"):
                conn.create_cardholder(first_name="", last_name="Doe")
            with pytest.raises(ValueError, match="last_name"):
                conn.create_cardholder(first_name="John", last_name="")
        finally:
            conn.dispose()


class TestAddCloudlinkUnit:
    """Tests for adding Cloudlink units to an Access Manager role."""

    def test_add_cloudlink_unit_raises_when_not_connected(self):
        """add_cloudlink_unit should raise RuntimeError if not connected."""
        from genetec_mcp_server.connection import GenetecConnection

        conn = GenetecConnection()
        try:
            with pytest.raises(RuntimeError, match="Not connected"):
                conn.add_cloudlink_unit(
                    name="Cloudlink-01",
                    ip_address="192.168.1.100",
                    username="admin",
                    password="admin",
                    access_manager_guid="00000000-0000-0000-0000-000000000001",
                )
        finally:
            conn.dispose()

    def test_add_cloudlink_unit_requires_name(self):
        """add_cloudlink_unit should raise ValueError if name is empty."""
        from genetec_mcp_server.connection import GenetecConnection

        conn = GenetecConnection()
        try:
            with pytest.raises(ValueError, match="name"):
                conn.add_cloudlink_unit(
                    name="",
                    ip_address="192.168.1.100",
                    username="admin",
                    password="admin",
                    access_manager_guid="00000000-0000-0000-0000-000000000001",
                )
        finally:
            conn.dispose()

    def test_add_cloudlink_unit_requires_ip_address(self):
        """add_cloudlink_unit should raise ValueError if ip_address is empty."""
        from genetec_mcp_server.connection import GenetecConnection

        conn = GenetecConnection()
        try:
            with pytest.raises(ValueError, match="ip_address"):
                conn.add_cloudlink_unit(
                    name="Cloudlink-01",
                    ip_address="",
                    username="admin",
                    password="admin",
                    access_manager_guid="00000000-0000-0000-0000-000000000001",
                )
        finally:
            conn.dispose()

    def test_add_cloudlink_unit_requires_access_manager_guid(self):
        """add_cloudlink_unit should raise ValueError if access_manager_guid is empty."""
        from genetec_mcp_server.connection import GenetecConnection

        conn = GenetecConnection()
        try:
            with pytest.raises(ValueError, match="access_manager_guid"):
                conn.add_cloudlink_unit(
                    name="Cloudlink-01",
                    ip_address="192.168.1.100",
                    username="admin",
                    password="admin",
                    access_manager_guid="",
                )
        finally:
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
