"""Tests for tool_logger module: ToolCallLogger, ToolCallRecord, sanitize_args."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from genetec_mcp_server.tool_logger import (
    ToolCallLogger,
    ToolCallRecord,
    sanitize_args,
)


def make_record(
    session_id: str = "abc123",
    tool_name: str = "get_system_version",
    arguments: dict | None = None,
    result: str | None = "5.13",
    error: str | None = None,
    timestamp: str | None = None,
    duration_ms: float = 42.0,
) -> ToolCallRecord:
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    return ToolCallRecord(
        session_id=session_id,
        tool_name=tool_name,
        arguments=arguments or {},
        result=result,
        error=error,
        timestamp=timestamp,
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# sanitize_args
# ---------------------------------------------------------------------------


class TestSanitizeArgs:
    def test_redacts_password_field(self):
        result = sanitize_args({"password": "s3cr3t", "username": "admin"})
        assert result["password"] == "[REDACTED]"
        assert result["username"] == "admin"

    def test_redacts_secret_field(self):
        result = sanitize_args({"api_secret": "xyz"})
        assert result["api_secret"] == "[REDACTED]"

    def test_redacts_token_field(self):
        result = sanitize_args({"access_token": "tok123"})
        assert result["access_token"] == "[REDACTED]"

    def test_case_insensitive(self):
        result = sanitize_args({"Password": "x", "TOKEN": "y"})
        assert result["Password"] == "[REDACTED]"
        assert result["TOKEN"] == "[REDACTED]"

    def test_non_sensitive_fields_pass_through(self):
        result = sanitize_args({"name": "Alice", "guid": "abc-123"})
        assert result == {"name": "Alice", "guid": "abc-123"}

    def test_empty_dict(self):
        assert sanitize_args({}) == {}


# ---------------------------------------------------------------------------
# ToolCallLogger.log() and get_session_logs()
# ---------------------------------------------------------------------------


class TestToolCallLoggerLog:
    def test_log_writes_jsonl_line_to_file(self, tmp_path: Path):
        logger = ToolCallLogger(tmp_path)
        record = make_record(session_id="sess1", tool_name="ping")
        logger.log(record)
        logger.close()

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = tmp_path / f"genetec-mcp-{today}.jsonl"
        assert log_file.exists()
        lines = [l for l in log_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["session_id"] == "sess1"
        assert data["tool_name"] == "ping"

    def test_log_appears_in_get_session_logs(self, tmp_path: Path):
        logger = ToolCallLogger(tmp_path)
        record = make_record(session_id="sess2", tool_name="create_cardholder")
        logger.log(record)

        logs = logger.get_session_logs("sess2")
        assert len(logs) == 1
        assert logs[0].tool_name == "create_cardholder"
        logger.close()

    def test_unknown_session_returns_empty_list(self, tmp_path: Path):
        logger = ToolCallLogger(tmp_path)
        result = logger.get_session_logs("no-such-session")
        assert result == []
        logger.close()

    def test_multiple_records_same_session(self, tmp_path: Path):
        logger = ToolCallLogger(tmp_path)
        for i in range(3):
            logger.log(make_record(session_id="s1", tool_name=f"tool_{i}"))

        logs = logger.get_session_logs("s1")
        assert len(logs) == 3
        assert [r.tool_name for r in logs] == ["tool_0", "tool_1", "tool_2"]
        logger.close()


# ---------------------------------------------------------------------------
# get_sessions()
# ---------------------------------------------------------------------------


class TestGetSessions:
    def test_returns_sessions_summary(self, tmp_path: Path):
        logger = ToolCallLogger(tmp_path)
        logger.log(make_record(session_id="A", tool_name="t1"))
        logger.log(make_record(session_id="B", tool_name="t2"))
        logger.log(make_record(session_id="A", tool_name="t3"))

        sessions = logger.get_sessions()
        session_ids = {s["session_id"] for s in sessions}
        assert session_ids == {"A", "B"}

        a = next(s for s in sessions if s["session_id"] == "A")
        assert a["call_count"] == 2
        logger.close()

    def test_empty_when_no_logs(self, tmp_path: Path):
        logger = ToolCallLogger(tmp_path)
        assert logger.get_sessions() == []
        logger.close()


# ---------------------------------------------------------------------------
# TTL pruning
# ---------------------------------------------------------------------------


class TestTTLPruning:
    def test_prune_removes_expired_records(self, tmp_path: Path):
        logger = ToolCallLogger(tmp_path, ttl_hours=1)

        old_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        old_record = make_record(session_id="old_sess", timestamp=old_ts)
        # Add directly to index without writing to file (simulates stale records)
        logger._session_index["old_sess"] = [old_record]
        logger._records.append(old_record)

        # Trigger pruning via query
        result = logger.get_session_logs("old_sess")
        assert result == []
        assert "old_sess" not in logger._session_index
        logger.close()

    def test_fresh_records_survive_prune(self, tmp_path: Path):
        logger = ToolCallLogger(tmp_path, ttl_hours=1)
        record = make_record(session_id="fresh_sess")
        logger.log(record)

        result = logger.get_session_logs("fresh_sess")
        assert len(result) == 1
        logger.close()


# ---------------------------------------------------------------------------
# maxlen eviction
# ---------------------------------------------------------------------------


class TestMaxlenEviction:
    def test_maxlen_evicts_oldest_record(self, tmp_path: Path):
        logger = ToolCallLogger(tmp_path, maxlen=3)

        for i in range(4):
            logger.log(make_record(session_id="s1", tool_name=f"tool_{i}"))

        # Only 3 records should be in the deque (oldest evicted)
        assert len(logger._records) == 3
        assert logger._records[0].tool_name == "tool_1"
        logger.close()

    def test_eviction_updates_session_index(self, tmp_path: Path):
        logger = ToolCallLogger(tmp_path, maxlen=2)

        logger.log(make_record(session_id="early", tool_name="first"))
        logger.log(make_record(session_id="s2", tool_name="second"))
        # This should evict "early/first"
        logger.log(make_record(session_id="s3", tool_name="third"))

        assert logger.get_session_logs("early") == []
        logger.close()


# ---------------------------------------------------------------------------
# _load_recent()
# ---------------------------------------------------------------------------


class TestLoadRecent:
    def test_hydrates_from_existing_jsonl(self, tmp_path: Path):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = tmp_path / f"genetec-mcp-{today}.jsonl"

        record = make_record(session_id="restored", tool_name="loaded_tool")
        import dataclasses

        log_file.write_text(json.dumps(dataclasses.asdict(record)) + "\n")

        logger = ToolCallLogger(tmp_path)
        logs = logger.get_session_logs("restored")
        assert len(logs) == 1
        assert logs[0].tool_name == "loaded_tool"
        logger.close()

    def test_skips_expired_records_on_load(self, tmp_path: Path):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = tmp_path / f"genetec-mcp-{today}.jsonl"

        old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        record = make_record(session_id="stale", timestamp=old_ts)
        import dataclasses

        log_file.write_text(json.dumps(dataclasses.asdict(record)) + "\n")

        logger = ToolCallLogger(tmp_path, ttl_hours=24)
        assert logger.get_session_logs("stale") == []
        logger.close()

    def test_handles_missing_file_gracefully(self, tmp_path: Path):
        logger = ToolCallLogger(tmp_path)  # no JSONL file exists
        assert logger.get_sessions() == []
        logger.close()

    def test_skips_malformed_lines(self, tmp_path: Path):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = tmp_path / f"genetec-mcp-{today}.jsonl"
        log_file.write_text("not-json\n{}\n")

        logger = ToolCallLogger(tmp_path)  # should not raise
        assert logger.get_sessions() == []
        logger.close()


# ---------------------------------------------------------------------------
# MCP tool functions: list_sessions, get_session_logs
# ---------------------------------------------------------------------------


class TestListSessionsTool:
    @pytest.mark.asyncio
    async def test_returns_no_sessions_message_when_empty(self):
        from genetec_mcp_server.server import list_sessions

        mock_logger = MagicMock()
        mock_logger.get_sessions.return_value = []
        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.tool_logger = mock_logger

        result = await list_sessions(mock_ctx)
        assert "no active sessions" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_formatted_session_list(self):
        from genetec_mcp_server.server import list_sessions

        mock_logger = MagicMock()
        mock_logger.get_sessions.return_value = [
            {
                "session_id": "abc12345",
                "call_count": 3,
                "first_activity": "2026-03-18T10:00:00+00:00",
                "last_activity": "2026-03-18T10:05:00+00:00",
            }
        ]
        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.tool_logger = mock_logger

        result = await list_sessions(mock_ctx)
        assert "abc12345" in result
        assert "3" in result


class TestGetSessionLogsTool:
    @pytest.mark.asyncio
    async def test_returns_no_records_message_for_unknown_session(self):
        from genetec_mcp_server.server import get_session_logs

        mock_logger = MagicMock()
        mock_logger.get_session_logs.return_value = []
        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.tool_logger = mock_logger

        result = await get_session_logs(mock_ctx, session_id="unknown123")
        assert "no records" in result.lower()
        assert "unknown123" in result

    @pytest.mark.asyncio
    async def test_returns_formatted_records(self):
        from genetec_mcp_server.server import get_session_logs

        ts = datetime.now(timezone.utc).isoformat()
        record = ToolCallRecord(
            session_id="abc12345",
            tool_name="create_cardholder",
            arguments={"first_name": "Alice"},
            result="Cardholder created",
            error=None,
            timestamp=ts,
            duration_ms=55.5,
        )
        mock_logger = MagicMock()
        mock_logger.get_session_logs.return_value = [record]
        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.tool_logger = mock_logger

        result = await get_session_logs(mock_ctx, session_id="abc12345")
        assert "create_cardholder" in result
        assert "Alice" in result
        assert "Cardholder created" in result

    @pytest.mark.asyncio
    async def test_shows_error_when_record_has_error(self):
        from genetec_mcp_server.server import get_session_logs

        ts = datetime.now(timezone.utc).isoformat()
        record = ToolCallRecord(
            session_id="sess1",
            tool_name="create_alarm",
            arguments={},
            result=None,
            error="Connection refused",
            timestamp=ts,
            duration_ms=10.0,
        )
        mock_logger = MagicMock()
        mock_logger.get_session_logs.return_value = [record]
        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.tool_logger = mock_logger

        result = await get_session_logs(mock_ctx, session_id="sess1")
        assert "Connection refused" in result
        assert "ERROR" in result
