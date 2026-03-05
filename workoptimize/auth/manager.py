"""Authentication and subscription management.

Handles license key validation, subscription tiers, and machine activation.
Designed for a SaaS model with offline-first operation — the app works
without network but validates the license periodically.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from uuid import uuid4

from workoptimize.security.encryption import DataEncryptor

logger = logging.getLogger(__name__)


class SubscriptionTier(Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


@dataclass
class License:
    email: str
    license_key: str
    tier: SubscriptionTier
    machine_id: str
    activated_at: float
    expires_at: float | None  # None = lifetime
    last_validated: float


class AuthManager:
    """Manages license activation and subscription state.

    License flow:
    1. User purchases on your website → receives license key via email
    2. User enters email + license key in the app
    3. App calls your license server to validate and activate
    4. License is stored locally (encrypted) for offline use
    5. Periodic re-validation ensures the license is still active
    """

    # Re-validate license every 7 days
    REVALIDATION_INTERVAL = 7 * 24 * 60 * 60

    def __init__(self, data_dir: Path, encryptor: DataEncryptor | None = None):
        self._data_dir = data_dir
        self._license_file = data_dir / "license.enc"
        self._encryptor = encryptor
        self._license: License | None = None
        self._machine_id = self._get_machine_id()

        # Try to load existing license
        self._load_license()

    @property
    def is_authenticated(self) -> bool:
        return self._license is not None

    @property
    def tier(self) -> SubscriptionTier:
        if self._license is None:
            return SubscriptionTier.FREE
        return self._license.tier

    @property
    def email(self) -> str | None:
        if self._license is None:
            return None
        return self._license.email

    @property
    def needs_revalidation(self) -> bool:
        if self._license is None:
            return False
        elapsed = time.time() - self._license.last_validated
        return elapsed > self.REVALIDATION_INTERVAL

    async def activate(self, email: str, license_key: str, license_api_url: str) -> dict:
        """Activate a license key on this machine.

        In production, this calls your license server to validate.
        The server checks: valid key, correct email, not over device limit.
        """
        # Validate input
        if not email or not license_key:
            return {"success": False, "error": "Email and license key are required"}

        # Call license server
        validation = await self._validate_with_server(email, license_key, license_api_url)
        if not validation["valid"]:
            return {"success": False, "error": validation.get("error", "Invalid license")}

        # Store license locally
        self._license = License(
            email=email,
            license_key=self._hash_key(license_key),
            tier=SubscriptionTier(validation.get("tier", "pro")),
            machine_id=self._machine_id,
            activated_at=time.time(),
            expires_at=validation.get("expires_at"),
            last_validated=time.time(),
        )
        self._save_license()

        logger.info("License activated for %s (tier: %s)", email, self._license.tier.value)
        return {"success": True, "tier": self._license.tier.value}

    async def deactivate(self) -> None:
        """Deactivate license on this machine."""
        if self._license_file.exists():
            self._license_file.unlink()
        self._license = None
        logger.info("License deactivated")

    async def revalidate(self, license_api_url: str) -> bool:
        """Periodically re-validate the license with the server."""
        if self._license is None:
            return False

        # In production, call the server with the stored (hashed) key
        # For now, just update the timestamp
        self._license.last_validated = time.time()
        self._save_license()
        return True

    def get_status(self) -> dict:
        """Get current auth status."""
        if self._license is None:
            return {
                "authenticated": False,
                "tier": "free",
                "email": None,
                "needs_revalidation": False,
            }
        return {
            "authenticated": True,
            "tier": self._license.tier.value,
            "email": self._license.email,
            "activated_at": self._license.activated_at,
            "expires_at": self._license.expires_at,
            "needs_revalidation": self.needs_revalidation,
        }

    # ── Tier feature gates ───────────────────────────────────────────

    def can_use_feature(self, feature: str) -> bool:
        """Check if the current tier allows a feature."""
        free_features = {"basic_suggestions", "manual_ask"}
        pro_features = free_features | {
            "pattern_tracking",
            "automation_builder",
            "cloud_sync",
            "unlimited_captures",
            "priority_support",
        }
        team_features = pro_features | {
            "team_dashboard",
            "admin_controls",
            "aggregate_reports",
        }

        tier_features = {
            SubscriptionTier.FREE: free_features,
            SubscriptionTier.PRO: pro_features,
            SubscriptionTier.TEAM: team_features,
        }

        allowed = tier_features.get(self.tier, free_features)
        return feature in allowed

    # ── Internal ─────────────────────────────────────────────────────

    async def _validate_with_server(self, email: str, license_key: str, api_url: str) -> dict:
        """Call the license validation server.

        In production, this makes an HTTPS POST to your license API:
        POST {api_url}/validate
        Body: { email, license_key, machine_id }
        Response: { valid: bool, tier: str, expires_at: float|null, error?: str }
        """
        # Placeholder — replace with actual HTTP call to your license server
        # using httpx or aiohttp
        logger.info("License validation would call: %s", api_url)
        return {"valid": True, "tier": "pro", "expires_at": None}

    def _save_license(self) -> None:
        """Save license to disk (encrypted)."""
        if self._license is None:
            return

        data = json.dumps({
            "email": self._license.email,
            "license_key": self._license.license_key,
            "tier": self._license.tier.value,
            "machine_id": self._license.machine_id,
            "activated_at": self._license.activated_at,
            "expires_at": self._license.expires_at,
            "last_validated": self._license.last_validated,
        }).encode()

        if self._encryptor:
            data = self._encryptor.encrypt(data)

        self._license_file.write_bytes(data)

    def _load_license(self) -> None:
        """Load license from disk."""
        if not self._license_file.exists():
            return

        try:
            data = self._license_file.read_bytes()
            if self._encryptor:
                data = self._encryptor.decrypt(data)

            info = json.loads(data)
            self._license = License(
                email=info["email"],
                license_key=info["license_key"],
                tier=SubscriptionTier(info["tier"]),
                machine_id=info["machine_id"],
                activated_at=info["activated_at"],
                expires_at=info.get("expires_at"),
                last_validated=info["last_validated"],
            )
        except Exception:
            logger.warning("Failed to load license file — treating as unauthenticated")
            self._license = None

    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash the license key for local storage (never store plaintext)."""
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def _get_machine_id() -> str:
        """Generate a stable machine identifier."""
        import platform
        raw = f"{platform.node()}-{platform.machine()}-{platform.system()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
