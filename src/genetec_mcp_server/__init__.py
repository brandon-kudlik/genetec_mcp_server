"""Genetec MCP Server - Python interface to Genetec Security Center SDK."""

__version__ = "0.1.0"


def main() -> None:
    """CLI entry point."""
    from genetec_mcp_server.__main__ import main as _main

    _main()
