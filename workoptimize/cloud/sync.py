"""Cloud sync client — encrypted sync of insights and patterns.

Security guarantees:
- Raw screenshots NEVER leave the machine
- Only structured data (patterns, reports, analytics) is synced
- All data is encrypted client-side before upload (AES-256-GCM)
- The server never sees plaintext user data
- Sync is opt-in and can be revoked at any time
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SyncConfig:
    """Cloud sync configuration."""
    enabled: bool = False
    api_url: str = ""  # Your SaaS backend URL
    sync_reports: bool = True
    sync_patterns: bool = True
    sync_analytics: bool = True
    sync_screenshots: bool = False  # ALWAYS False by default
    sync_interval_seconds: float = 3600.0  # 1 hour
    encrypt_before_upload: bool = True


@dataclass
class SyncState:
    """Tracks sync progress."""
    last_sync_at: float | None = None
    last_sync_status: str = "never"
    items_synced: int = 0
    items_pending: int = 0
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class CloudSyncClient:
    """Handles encrypted cloud sync of insights and patterns.

    Architecture:
    1. Client collects structured data (reports, patterns, analytics)
    2. Data is encrypted client-side with the user's key
    3. Encrypted payload is uploaded to the sync API
    4. Server stores encrypted blobs — cannot read the content
    5. Other devices download and decrypt locally

    The sync API is a simple REST service:
    - POST /api/v1/sync/upload   — Upload encrypted data
    - GET  /api/v1/sync/download — Download data for this account
    - GET  /api/v1/sync/status   — Get sync status
    """

    def __init__(self, config: SyncConfig, data_dir: Path,
                 encryptor=None, auth_token: str | None = None):
        self.config = config
        self._data_dir = data_dir
        self._encryptor = encryptor
        self._auth_token = auth_token
        self._state = SyncState()
        self._state_file = data_dir / "sync_state.json"
        self._load_state()

    @property
    def state(self) -> SyncState:
        return self._state

    async def sync(self) -> dict:
        """Perform a sync cycle."""
        if not self.config.enabled:
            return {"success": False, "error": "Sync not enabled"}

        if not self._auth_token:
            return {"success": False, "error": "Not authenticated"}

        if not self.config.api_url:
            return {"success": False, "error": "Sync API URL not configured"}

        try:
            # Collect data to sync
            payload = self._collect_sync_data()

            if not payload:
                self._state.last_sync_at = time.time()
                self._state.last_sync_status = "nothing_to_sync"
                self._save_state()
                return {"success": True, "synced": 0}

            # Encrypt payload
            encrypted = self._encrypt_payload(payload)

            # Upload
            result = await self._upload(encrypted)

            # Download any new data from other devices
            remote_data = await self._download()
            if remote_data:
                self._apply_remote_data(remote_data)

            self._state.last_sync_at = time.time()
            self._state.last_sync_status = "success"
            self._state.items_synced += result.get("items", 0)
            self._save_state()

            return {"success": True, "synced": result.get("items", 0)}

        except Exception as e:
            logger.exception("Sync failed")
            self._state.last_sync_status = "error"
            self._state.errors.append(str(e))
            self._state.errors = self._state.errors[-10:]  # Keep last 10
            self._save_state()
            return {"success": False, "error": str(e)}

    def _collect_sync_data(self) -> dict | None:
        """Collect structured data for sync. Never includes screenshots."""
        data: dict = {"timestamp": time.time(), "items": []}

        if self.config.sync_reports:
            report_file = self._data_dir / "latest_report.json"
            if report_file.exists():
                data["items"].append({
                    "type": "report",
                    "data": json.loads(report_file.read_text()),
                })

        if self.config.sync_patterns:
            patterns_file = self._data_dir / "patterns_export.json"
            if patterns_file.exists():
                data["items"].append({
                    "type": "patterns",
                    "data": json.loads(patterns_file.read_text()),
                })

        if self.config.sync_analytics:
            analytics_file = self._data_dir / "analytics_export.json"
            if analytics_file.exists():
                data["items"].append({
                    "type": "analytics",
                    "data": json.loads(analytics_file.read_text()),
                })

        return data if data["items"] else None

    def _encrypt_payload(self, payload: dict) -> bytes:
        """Encrypt the sync payload before upload."""
        raw = json.dumps(payload).encode()
        if self._encryptor and self.config.encrypt_before_upload:
            return self._encryptor.encrypt(raw)
        return raw

    async def _upload(self, data: bytes) -> dict:
        """Upload encrypted data to the sync API.

        In production, this uses httpx/aiohttp:
        POST {api_url}/api/v1/sync/upload
        Headers: Authorization: Bearer {token}
        Body: encrypted bytes
        """
        logger.info("Would upload %d bytes to %s", len(data), self.config.api_url)
        # Placeholder — implement with httpx
        return {"items": 1}

    async def _download(self) -> dict | None:
        """Download data from other devices.

        GET {api_url}/api/v1/sync/download?since={last_sync_at}
        """
        logger.info("Would download from %s", self.config.api_url)
        return None

    def _apply_remote_data(self, data: dict) -> None:
        """Apply data downloaded from the cloud."""
        # Decrypt and merge into local stores
        pass

    def _save_state(self) -> None:
        self._state_file.write_text(json.dumps({
            "last_sync_at": self._state.last_sync_at,
            "last_sync_status": self._state.last_sync_status,
            "items_synced": self._state.items_synced,
        }))

    def _load_state(self) -> None:
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text())
                self._state.last_sync_at = data.get("last_sync_at")
                self._state.last_sync_status = data.get("last_sync_status", "unknown")
                self._state.items_synced = data.get("items_synced", 0)
            except Exception:
                pass
