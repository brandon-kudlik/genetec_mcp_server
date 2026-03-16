"""Tests for access rule creation (connection + server tool)."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from genetec_mcp_server.connection import GenetecConnection


def _mock_response(json_data, status_code=200):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# --- Connection tests ---


class TestCreateAccessRules:
    """Tests for GenetecConnection.create_access_rules."""

    def test_returns_results_on_success(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {
                    "results": [
                        {"name": "Rule 1", "guid": "rule-guid-1", "doorsAssigned": 2, "status": "Created"},
                        {"name": "Rule 2", "guid": "rule-guid-2", "doorsAssigned": 1, "status": "Created"},
                    ],
                    "createdCount": 2,
                }}
            )
            result = conn.create_access_rules(access_rules=[
                {"name": "Rule 1", "doorGuids": ["door-1", "door-2"]},
                {"name": "Rule 2", "doorGuids": ["door-3"], "side": "Entry"},
            ])
        assert result["createdCount"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["guid"] == "rule-guid-1"
        assert result["results"][0]["doorsAssigned"] == 2
        conn.dispose()

    def test_requires_non_empty_list(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="access_rules.*cannot be empty"):
            conn.create_access_rules(access_rules=[])
        conn.dispose()

    def test_requires_name_in_each_rule(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with pytest.raises(ValueError, match="name"):
            conn.create_access_rules(access_rules=[{"doorGuids": ["door-1"]}])
        conn.dispose()

    def test_sends_correct_post_body(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": True, "data": {"results": [], "createdCount": 0}}
            )
            rules = [{"name": "Rule 1", "doorGuids": ["door-1"], "side": "Both"}]
            conn.create_access_rules(access_rules=rules)
            mock_post.assert_called_once_with(
                "/api/access-rules/batch",
                json={"accessRules": rules},
            )
        conn.dispose()

    def test_raises_on_error_response(self):
        conn = GenetecConnection(base_url="http://localhost:5100")
        with patch.object(conn._client, "post") as mock_post:
            mock_post.return_value = _mock_response(
                {"success": False, "error": "Failed to create access rules."}
            )
            with pytest.raises(RuntimeError, match="Failed to create"):
                conn.create_access_rules(access_rules=[{"name": "Rule 1"}])
        conn.dispose()


# --- Server tool tests ---


class TestCreateAccessRulesTool:
    """Tests for the create_access_rules MCP tool."""

    def test_tool_is_registered(self):
        from genetec_mcp_server.server import mcp

        tool_names = list(mcp._tool_manager._tools.keys())
        assert "create_access_rules" in tool_names

    @pytest.mark.asyncio
    async def test_returns_error_when_not_connected(self):
        from genetec_mcp_server.server import create_access_rules

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_access_rules(
            mock_ctx,
            access_rules=[{"name": "Rule 1"}],
        )
        assert "not connected" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_success_message(self):
        from genetec_mcp_server.server import create_access_rules

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_access_rules.return_value = {
            "results": [
                {"name": "Rule 1", "guid": "rule-guid-1", "doorsAssigned": 2, "status": "Created"},
            ],
            "createdCount": 1,
        }

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_access_rules(
            mock_ctx,
            access_rules=[{"name": "Rule 1", "doorGuids": ["d1", "d2"]}],
        )
        assert "1" in result
        assert "rule-guid-1" in result
        assert "2 door(s) assigned" in result
        mock_conn.create_access_rules.assert_called_once_with(
            access_rules=[{"name": "Rule 1", "doorGuids": ["d1", "d2"]}],
        )

    @pytest.mark.asyncio
    async def test_returns_error_on_runtime_error(self):
        from genetec_mcp_server.server import create_access_rules

        mock_conn = MagicMock()
        mock_conn.is_connected = True
        mock_conn.create_access_rules.side_effect = RuntimeError("SDK failure")

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.connection = mock_conn

        result = await create_access_rules(
            mock_ctx,
            access_rules=[{"name": "Rule 1"}],
        )
        assert "Error" in result
        assert "SDK failure" in result
