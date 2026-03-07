"""Configuration management for Genetec MCP Server."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SDK_PATH = os.getenv(
    "GENETEC_SDK_PATH",
    r"C:\Program Files (x86)\Genetec Security Center 5.13 SDK\net8.0-windows",
)
CONFIG_PATH = os.getenv(
    "GENETEC_CONFIG_PATH",
    r"C:\ProgramData\Genetec Security Center 5.13",
)
SERVER = os.getenv("GENETEC_SERVER", "localhost")
USERNAME = os.getenv("GENETEC_USERNAME", "")
PASSWORD = os.getenv("GENETEC_PASSWORD", "")
CLIENT_CERTIFICATE = os.getenv(
    "GENETEC_CLIENT_CERTIFICATE",
    # Development certificate from Genetec DAP
    "KxsD11z743Hf5Gq9mv3+5ekxzemlCiUXkTFY5ba1NOGcLCmGstt2n0zYE9NsNimv",
)


def validate_sdk_path() -> Path:
    """Validate that the SDK path exists and contains the core DLL.

    Returns:
        Path to the SDK directory.

    Raises:
        FileNotFoundError: If the SDK path or core DLL is missing.
    """
    sdk = Path(SDK_PATH)
    if not sdk.exists():
        raise FileNotFoundError(f"Genetec SDK not found at: {SDK_PATH}")
    core_dll = sdk / "Genetec.Sdk.dll"
    if not core_dll.exists():
        raise FileNotFoundError(f"Genetec.Sdk.dll not found in: {SDK_PATH}")
    return sdk
