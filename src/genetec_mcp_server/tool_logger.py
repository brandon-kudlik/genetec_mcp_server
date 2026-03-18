"""Tool call logging for Genetec MCP Server."""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Optional


def sanitize_args(args: dict) -> dict:
    """Redact fields whose keys contain 'password', 'secret', or 'token'."""
    sensitive = {"password", "secret", "token"}
    return {
        k: "[REDACTED]" if any(s in k.lower() for s in sensitive) else v
        for k, v in args.items()
    }


@dataclass
class ToolCallRecord:
    session_id: str
    tool_name: str
    arguments: dict
    result: Optional[str]
    error: Optional[str]
    timestamp: str
    duration_ms: float


class ToolCallLogger:
    """Logs tool calls to JSONL files with an in-memory index for fast queries."""

    def __init__(self, log_dir: Path, ttl_hours: int = 24, maxlen: int = 10_000):
        self._log_dir = log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._ttl_hours = ttl_hours
        self._maxlen = maxlen

        self._records: deque[ToolCallRecord] = deque(maxlen=maxlen)
        self._session_index: dict[str, list[ToolCallRecord]] = {}

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._active_log_file = log_dir / f"genetec-mcp-{today}.jsonl"

        file_logger = logging.getLogger(f"genetec_mcp_tool_calls.{id(self)}")
        file_logger.setLevel(logging.INFO)
        file_logger.propagate = False
        handler = TimedRotatingFileHandler(
            str(self._active_log_file), when="midnight", backupCount=7
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        file_logger.addHandler(handler)
        self._file_logger = file_logger
        self._handler = handler

        self._load_recent()

    def log(self, record: ToolCallRecord) -> None:
        """Append a record to the JSONL file and update the in-memory index."""
        # When the deque is at capacity, evict the oldest record from the index too.
        if len(self._records) == self._maxlen and self._records:
            self._remove_from_index(self._records[0])

        self._records.append(record)
        self._session_index.setdefault(record.session_id, []).append(record)
        self._file_logger.info(json.dumps(asdict(record)))

    def get_sessions(self) -> list[dict[str, Any]]:
        """Return a summary of all sessions currently in the in-memory index."""
        self._prune_ttl()
        sessions = []
        for session_id, records in self._session_index.items():
            if records:
                sessions.append(
                    {
                        "session_id": session_id,
                        "first_activity": records[0].timestamp,
                        "last_activity": records[-1].timestamp,
                        "call_count": len(records),
                    }
                )
        return sessions

    def get_session_logs(self, session_id: str) -> list[ToolCallRecord]:
        """Return all in-memory records for a session (empty list if unknown)."""
        self._prune_ttl()
        return list(self._session_index.get(session_id, []))

    def close(self) -> None:
        self._handler.flush()
        self._handler.close()
        self._file_logger.removeHandler(self._handler)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _remove_from_index(self, record: ToolCallRecord) -> None:
        sid = record.session_id
        if sid in self._session_index:
            try:
                self._session_index[sid].remove(record)
            except ValueError:
                pass
            if not self._session_index[sid]:
                del self._session_index[sid]

    def _is_fresh(self, record: ToolCallRecord) -> bool:
        ts = datetime.fromisoformat(record.timestamp)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - ts <= timedelta(hours=self._ttl_hours)

    def _prune_ttl(self) -> None:
        """Remove stale entries from the session index."""
        to_delete = []
        for session_id, records in self._session_index.items():
            fresh = [r for r in records if self._is_fresh(r)]
            if fresh:
                self._session_index[session_id] = fresh
            else:
                to_delete.append(session_id)
        for sid in to_delete:
            del self._session_index[sid]

    def _load_recent(self) -> None:
        """Hydrate the in-memory index from today's JSONL file on startup."""
        if not self._active_log_file.exists():
            return
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._ttl_hours)
        with open(self._active_log_file) as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    ts = datetime.fromisoformat(data["timestamp"])
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts < cutoff:
                        continue
                    record = ToolCallRecord(**data)
                    if len(self._records) == self._maxlen and self._records:
                        self._remove_from_index(self._records[0])
                    self._records.append(record)
                    self._session_index.setdefault(record.session_id, []).append(record)
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
