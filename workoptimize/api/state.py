"""Application state management for the FastAPI service.

Manages the lifecycle of the capture engine, analysis pipeline, pattern
tracker, and subscription state. Acts as the coordinator between the
API endpoints and the core engine.
"""

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path

from fastapi import WebSocket

from workoptimize.config.settings import Settings

logger = logging.getLogger(__name__)


class AppState:
    """Central state for the running WorkOptimize service."""

    def __init__(self, data_dir: Path | None = None):
        self._settings = Settings(data_dir=data_dir)
        self._running = False
        self._paused = False
        self._start_time: float | None = None
        self._capture_task: asyncio.Task | None = None
        self._ws_clients: list[WebSocket] = []

        # Counters
        self._total_captures = 0
        self._total_suggestions = 0
        self._current_app = ""

        # In-memory suggestion buffer
        self._suggestions: list[dict] = []
        self._dismissed: set[str] = set()

        # Pattern data
        self._patterns: list[dict] = []

        # Auth state
        self._auth: dict = {"authenticated": False, "email": None, "plan": "free"}

        # Sync state
        self._sync: dict = {"enabled": False, "last_sync": None, "sync_reports": True, "sync_patterns": True}

    # ── Lifecycle ────────────────────────────────────────────────────

    async def startup(self) -> None:
        """Initialize on app startup."""
        logger.info("WorkOptimize service starting up")
        self._settings.ensure_data_dirs()

    async def shutdown(self) -> None:
        """Clean up on app shutdown."""
        logger.info("WorkOptimize service shutting down")
        if self._capture_task and not self._capture_task.done():
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass

    async def start(self) -> None:
        """Start the capture loop."""
        self._running = True
        self._paused = False
        self._start_time = time.time()
        self._capture_task = asyncio.create_task(self._capture_loop())
        logger.info("Capture loop started")

    async def stop(self) -> None:
        """Stop the capture loop."""
        self._running = False
        if self._capture_task and not self._capture_task.done():
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
        logger.info("Capture loop stopped")

    # ── Capture loop ─────────────────────────────────────────────────

    async def _capture_loop(self) -> None:
        """Main capture → analyze → suggest loop."""
        interval = self._settings.capture_interval
        while self._running:
            if not self._paused:
                try:
                    await self._run_capture_cycle()
                except Exception:
                    logger.exception("Error in capture cycle")
            await asyncio.sleep(interval)

    async def _run_capture_cycle(self) -> None:
        """Single capture cycle: screenshot → detect app → analyze → suggest."""
        # This is where the real engine connects. For now, we simulate
        # the pipeline structure. Each step will be wired to the actual
        # modules as they mature.

        self._total_captures += 1

        # Step 1: Capture screen (workoptimize.capture.screen)
        # Step 2: Check privacy filter (workoptimize.capture.privacy)
        # Step 3: Detect active app (workoptimize.context.detector)
        # Step 4: Classify activity (workoptimize.context.classifier)
        # Step 5: Analyze with Claude vision (workoptimize.analysis.vision)
        # Step 6: Generate suggestions (workoptimize.suggestions.engine)
        # Step 7: Track patterns (workoptimize.patterns.tracker)
        # Step 8: Broadcast to connected clients

        # Placeholder: in the real pipeline, suggestions come from the
        # analysis engine. This structure shows the data flow.
        logger.debug("Capture cycle %d completed", self._total_captures)

    # ── WebSocket management ─────────────────────────────────────────

    def add_ws_client(self, ws: WebSocket) -> None:
        self._ws_clients.append(ws)

    def remove_ws_client(self, ws: WebSocket) -> None:
        self._ws_clients = [c for c in self._ws_clients if c != ws]

    async def _broadcast(self, event: str, data: dict) -> None:
        """Send an event to all connected WebSocket clients."""
        message = json.dumps({"event": event, "data": data})
        dead = []
        for ws in self._ws_clients:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.remove_ws_client(ws)

    # ── Properties ───────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def paused(self) -> bool:
        return self._paused

    @paused.setter
    def paused(self, value: bool) -> None:
        self._paused = value

    @property
    def uptime_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    @property
    def total_captures(self) -> int:
        return self._total_captures

    @property
    def total_suggestions(self) -> int:
        return self._total_suggestions

    @property
    def current_app(self) -> str:
        return self._current_app

    @property
    def subscription_status(self) -> str:
        return self._auth.get("plan", "free")

    # ── Suggestions ──────────────────────────────────────────────────

    def get_recent_suggestions(self, limit: int = 10) -> list[dict]:
        active = [s for s in self._suggestions if s["id"] not in self._dismissed]
        return active[-limit:]

    def dismiss_suggestion(self, suggestion_id: str) -> None:
        self._dismissed.add(suggestion_id)

    def mark_suggestion_helpful(self, suggestion_id: str) -> None:
        for s in self._suggestions:
            if s["id"] == suggestion_id:
                s["helpful"] = True
                break

    def _add_suggestion(self, category: str, title: str, body: str, priority: int = 5) -> dict:
        suggestion = {
            "id": str(uuid.uuid4()),
            "category": category,
            "title": title,
            "body": body,
            "priority": priority,
            "timestamp": time.time(),
            "helpful": None,
        }
        self._suggestions.append(suggestion)
        self._total_suggestions += 1
        # Keep buffer manageable
        if len(self._suggestions) > 200:
            self._suggestions = self._suggestions[-100:]
        return suggestion

    # ── Ask ───────────────────────────────────────────────────────────

    async def ask_about_screen(self, question: str) -> str:
        """Capture the current screen and answer a user question about it."""
        # Will integrate with analysis.vision.ScreenAnalyzer
        return (
            "Screen analysis is initializing. The answer to your question "
            f"'{question}' will be available once the capture engine is fully connected."
        )

    # ── Patterns & Reports ───────────────────────────────────────────

    def get_patterns(self) -> list[dict]:
        return self._patterns

    def get_optimization_report(self) -> dict:
        return {
            "total_observations": self._total_captures,
            "patterns_detected": len(self._patterns),
            "high_value_automations": 0,
            "top_recommendations": [],
        }

    async def generate_automation(self, pattern_type: str | None) -> dict:
        """Generate an automation script for a detected pattern."""
        return {
            "language": "python",
            "description": "Automation generation will be connected to the automation builder module.",
            "script": "# Automation script will be generated here",
        }

    # ── Settings ─────────────────────────────────────────────────────

    def get_settings(self) -> dict:
        return self._settings.to_dict()

    def update_capture_settings(self, updates: dict) -> None:
        self._settings.update_capture(updates)

    # ── Auth ─────────────────────────────────────────────────────────

    async def auth_login(self, email: str, license_key: str) -> dict:
        """Validate license key and activate."""
        # Will connect to auth.manager.AuthManager
        self._auth = {"authenticated": True, "email": email, "plan": "pro"}
        return {"success": True, "plan": "pro"}

    async def auth_logout(self) -> None:
        self._auth = {"authenticated": False, "email": None, "plan": "free"}

    def get_auth_status(self) -> dict:
        return dict(self._auth)

    # ── Sync ─────────────────────────────────────────────────────────

    def get_sync_status(self) -> dict:
        return dict(self._sync)

    def update_sync_settings(self, settings: dict) -> None:
        self._sync.update(settings)

    async def sync_now(self) -> dict:
        """Trigger immediate cloud sync."""
        if not self._auth.get("authenticated"):
            return {"success": False, "error": "Not authenticated"}
        if not self._sync.get("enabled"):
            return {"success": False, "error": "Sync not enabled"}
        self._sync["last_sync"] = time.time()
        return {"success": True, "synced_items": 0}

    # ── Analytics ─────────────────────────────────────────────────

    def get_focus_score(self, period: str = "today") -> dict:
        return {
            "score": 0,
            "deep_work_minutes": 0,
            "shallow_work_minutes": 0,
            "context_switches": 0,
            "longest_focus_streak_minutes": 0,
            "top_distraction": None,
            "period_label": period,
        }

    def get_app_usage(self, period: str = "today") -> list[dict]:
        return []

    def get_timeline(self, period: str = "today") -> list[dict]:
        return []

    def get_trends(self, days: int = 7) -> list[dict]:
        return []

    # ── Billing ──────────────────────────────────────────────────

    def get_plans(self) -> list[dict]:
        from workoptimize.cloud.billing import BillingManager
        return BillingManager.get_plans()

    async def create_checkout_url(self, plan_id: str, annual: bool) -> str:
        return f"https://checkout.stripe.com/placeholder/{plan_id}"

    async def get_billing_portal_url(self) -> str:
        return "https://billing.stripe.com/placeholder/portal"

    # ── Notifications ────────────────────────────────────────────

    def get_next_notification(self) -> dict | None:
        return None

    def get_notification_digest(self) -> list[dict]:
        return []

    def record_notification_feedback(self, notification_id: str, helpful: bool) -> None:
        pass

    # ── Pipeline Metrics ─────────────────────────────────────────

    def get_pipeline_metrics(self) -> dict:
        return {
            "total_captures": self._total_captures,
            "total_suggestions": self._total_suggestions,
            "api_errors": 0,
            "avg_analysis_ms": 0,
            "skipped_no_change": 0,
            "skipped_privacy": 0,
        }

    # ── Onboarding ───────────────────────────────────────────────

    @property
    def onboarding_completed(self) -> bool:
        return self._settings.get("onboarding_completed", False)

    @onboarding_completed.setter
    def onboarding_completed(self, value: bool) -> None:
        self._settings.set("onboarding_completed", value)
