"""Audit logging for all data access and capture events."""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    """Append-only audit log tracking every capture, analysis, and data access event.

    Each entry records what happened, when, and what data was involved,
    giving the user full transparency into the app's behavior.
    """

    def __init__(self, log_dir: Path):
        self._log_dir = log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self._log_dir / "audit.jsonl"
        self._logger = logging.getLogger("workoptimize.audit")

    def log_event(
        self,
        event_type: str,
        details: dict[str, Any] | None = None,
        *,
        data_hash: str | None = None,
    ) -> None:
        """Record an auditable event."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "epoch": time.time(),
            "event": event_type,
            "details": details or {},
        }
        if data_hash:
            entry["data_hash"] = data_hash

        line = json.dumps(entry, separators=(",", ":"))
        with open(self._log_file, "a") as f:
            f.write(line + "\n")

        self._logger.debug("Audit: %s", event_type)

    def log_capture(self, capture_id: str, app_name: str, data_hash: str) -> None:
        """Log a screen capture event."""
        self.log_event(
            "screen_capture",
            {"capture_id": capture_id, "active_app": app_name},
            data_hash=data_hash,
        )

    def log_analysis(self, capture_id: str, model: str, tokens_used: int) -> None:
        """Log a Claude API analysis call."""
        self.log_event(
            "api_analysis",
            {"capture_id": capture_id, "model": model, "tokens_used": tokens_used},
        )

    def log_data_access(self, accessor: str, capture_id: str, reason: str) -> None:
        """Log when stored data is accessed."""
        self.log_event(
            "data_access",
            {"accessor": accessor, "capture_id": capture_id, "reason": reason},
        )

    def log_data_deletion(self, capture_id: str, reason: str) -> None:
        """Log when data is deleted (retention policy or user request)."""
        self.log_event(
            "data_deletion",
            {"capture_id": capture_id, "reason": reason},
        )

    def get_recent_events(self, count: int = 50) -> list[dict]:
        """Read the most recent audit entries."""
        if not self._log_file.exists():
            return []
        lines = self._log_file.read_text().strip().split("\n")
        return [json.loads(line) for line in lines[-count:]]
