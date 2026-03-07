"""Test that the Genetec SDK can be loaded."""

from genetec_mcp_server.config import validate_sdk_path
from genetec_mcp_server.sdk_loader import get_sdk_version, load_sdk


def test_config_validates_sdk_path():
    """SDK path should point to a valid directory with Genetec.Sdk.dll."""
    path = validate_sdk_path()
    assert path.exists()
    assert (path / "Genetec.Sdk.dll").exists()


def test_sdk_loads_successfully():
    """Genetec.Sdk.dll should load without errors."""
    load_sdk()


def test_sdk_version():
    """SDK version should be 5.13.x."""
    load_sdk()
    version = get_sdk_version()
    assert version.startswith("5.13"), f"Unexpected SDK version: {version}"


def test_engine_class_is_importable():
    """Engine class should be importable after SDK is loaded."""
    load_sdk()
    from Genetec.Sdk import Engine  # type: ignore[import-untyped]

    assert Engine is not None
