"""Entry point for the Genetec MCP Server."""

import sys

from genetec_mcp_server.sdk_loader import get_sdk_version, load_sdk


def main() -> None:
    """Initialize and verify SDK connectivity."""
    print("Genetec MCP Server - Initializing...")

    try:
        load_sdk()
        version = get_sdk_version()
        print(f"Genetec SDK loaded successfully. Version: {version}")
    except Exception as e:
        print(f"ERROR: Failed to load Genetec SDK: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
