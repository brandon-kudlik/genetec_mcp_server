"""Configuration management for Genetec MCP Server."""

import os

from dotenv import load_dotenv

load_dotenv()

SDK_SERVICE_URL = os.getenv("GENETEC_SDK_SERVICE_URL", "http://localhost:5100")
HOST = os.getenv("GENETEC_MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("GENETEC_MCP_PORT", "8000"))
