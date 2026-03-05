"""FastAPI local service that the Tauri frontend communicates with.

This runs as a background process on the user's machine. The Tauri app
sends requests to localhost to control the capture engine, retrieve
suggestions, and manage settings.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from workoptimize.api.state import AppState

logger = logging.getLogger(__name__)


class CaptureSettingsUpdate(BaseModel):
    interval_seconds: int | None = None
    excluded_apps: list[str] | None = None
    excluded_window_titles: list[str] | None = None
    blur_sensitive: bool | None = None


class AskRequest(BaseModel):
    question: str


class AutomateRequest(BaseModel):
    pattern_type: str | None = None


class AuthLoginRequest(BaseModel):
    email: str
    license_key: str


class SyncSettings(BaseModel):
    enabled: bool
    sync_reports: bool = True
    sync_patterns: bool = True
    sync_screenshots: bool = False  # Never recommended


def create_app(data_dir: Path | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    state = AppState(data_dir=data_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await state.startup()
        yield
        await state.shutdown()

    app = FastAPI(
        title="WorkOptimize AI",
        version="0.1.0",
        docs_url="/api/docs",
        lifespan=lifespan,
    )

    # Allow Tauri frontend to connect
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["tauri://localhost", "http://localhost:1420", "https://tauri.localhost"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Status & Control ─────────────────────────────────────────────

    @app.get("/api/status")
    async def get_status():
        """Current engine status."""
        return {
            "running": state.is_running,
            "uptime_seconds": state.uptime_seconds,
            "total_captures": state.total_captures,
            "total_suggestions": state.total_suggestions,
            "active_app": state.current_app,
            "subscription": state.subscription_status,
        }

    @app.post("/api/start")
    async def start_capture():
        """Start the screen capture and analysis loop."""
        if state.is_running:
            return {"status": "already_running"}
        await state.start()
        return {"status": "started"}

    @app.post("/api/stop")
    async def stop_capture():
        """Stop the screen capture loop."""
        if not state.is_running:
            return {"status": "already_stopped"}
        await state.stop()
        return {"status": "stopped"}

    @app.post("/api/pause")
    async def pause_capture():
        """Temporarily pause capture."""
        state.paused = True
        return {"status": "paused"}

    @app.post("/api/resume")
    async def resume_capture():
        """Resume after pause."""
        state.paused = False
        return {"status": "resumed"}

    # ── Suggestions ──────────────────────────────────────────────────

    @app.get("/api/suggestions")
    async def get_suggestions(limit: int = 10):
        """Get recent suggestions."""
        return {"suggestions": state.get_recent_suggestions(limit)}

    @app.post("/api/suggestions/{suggestion_id}/dismiss")
    async def dismiss_suggestion(suggestion_id: str):
        """Dismiss a suggestion so it won't show again."""
        state.dismiss_suggestion(suggestion_id)
        return {"status": "dismissed"}

    @app.post("/api/suggestions/{suggestion_id}/helpful")
    async def mark_helpful(suggestion_id: str):
        """Mark a suggestion as helpful (improves future relevance)."""
        state.mark_suggestion_helpful(suggestion_id)
        return {"status": "marked_helpful"}

    # ── Ask (on-demand question about current screen) ────────────────

    @app.post("/api/ask")
    async def ask_question(req: AskRequest):
        """Ask a question about what's currently on screen."""
        if not req.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        answer = await state.ask_about_screen(req.question)
        return {"answer": answer}

    # ── Patterns & Optimization ──────────────────────────────────────

    @app.get("/api/patterns")
    async def get_patterns():
        """Get detected workflow patterns."""
        return {"patterns": state.get_patterns()}

    @app.get("/api/report")
    async def get_optimization_report():
        """Get full optimization report."""
        return state.get_optimization_report()

    @app.post("/api/automate")
    async def generate_automation(req: AutomateRequest):
        """Generate an automation script for a detected pattern."""
        script = await state.generate_automation(req.pattern_type)
        return {"script": script}

    # ── Settings ─────────────────────────────────────────────────────

    @app.get("/api/settings")
    async def get_settings():
        """Get current settings."""
        return state.get_settings()

    @app.put("/api/settings/capture")
    async def update_capture_settings(settings: CaptureSettingsUpdate):
        """Update capture settings."""
        state.update_capture_settings(settings.model_dump(exclude_none=True))
        return {"status": "updated"}

    # ── Auth & Subscription ──────────────────────────────────────────

    @app.post("/api/auth/login")
    async def login(req: AuthLoginRequest):
        """Activate license."""
        result = await state.auth_login(req.email, req.license_key)
        if not result["success"]:
            raise HTTPException(status_code=401, detail=result["error"])
        return result

    @app.post("/api/auth/logout")
    async def logout():
        """Deactivate license on this machine."""
        await state.auth_logout()
        return {"status": "logged_out"}

    @app.get("/api/auth/status")
    async def auth_status():
        """Current auth/subscription status."""
        return state.get_auth_status()

    # ── Cloud Sync ───────────────────────────────────────────────────

    @app.get("/api/sync/status")
    async def sync_status():
        """Get cloud sync status."""
        return state.get_sync_status()

    @app.put("/api/sync/settings")
    async def update_sync_settings(settings: SyncSettings):
        """Update cloud sync preferences."""
        state.update_sync_settings(settings.model_dump())
        return {"status": "updated"}

    @app.post("/api/sync/now")
    async def sync_now():
        """Trigger an immediate sync."""
        result = await state.sync_now()
        return result

    # ── Analytics ─────────────────────────────────────────────────────

    @app.get("/api/analytics/focus")
    async def get_focus_score(period: str = "today"):
        """Get focus score for a time period."""
        return state.get_focus_score(period)

    @app.get("/api/analytics/apps")
    async def get_app_usage(period: str = "today"):
        """Get app usage breakdown."""
        return {"apps": state.get_app_usage(period)}

    @app.get("/api/analytics/timeline")
    async def get_timeline(period: str = "today"):
        """Get activity timeline for visualization."""
        return {"timeline": state.get_timeline(period)}

    @app.get("/api/analytics/trends")
    async def get_trends(days: int = 7):
        """Get focus score trends."""
        return {"trends": state.get_trends(days)}

    # ── Billing ──────────────────────────────────────────────────────

    @app.get("/api/billing/plans")
    async def get_plans():
        """Get available subscription plans."""
        return {"plans": state.get_plans()}

    @app.post("/api/billing/checkout")
    async def create_checkout(plan_id: str, annual: bool = False):
        """Create a Stripe checkout URL."""
        url = await state.create_checkout_url(plan_id, annual)
        return {"checkout_url": url}

    @app.get("/api/billing/portal")
    async def billing_portal():
        """Get Stripe customer portal URL."""
        url = await state.get_billing_portal_url()
        return {"portal_url": url}

    # ── Notifications ────────────────────────────────────────────────

    @app.get("/api/notifications")
    async def get_next_notification():
        """Get the next notification to display."""
        notification = state.get_next_notification()
        return {"notification": notification}

    @app.get("/api/notifications/digest")
    async def get_digest():
        """Get batched low-priority notifications."""
        return {"notifications": state.get_notification_digest()}

    @app.post("/api/notifications/{notification_id}/feedback")
    async def notification_feedback(notification_id: str, helpful: bool = True):
        """Record feedback on a notification."""
        state.record_notification_feedback(notification_id, helpful)
        return {"status": "recorded"}

    # ── Pipeline Metrics ─────────────────────────────────────────────

    @app.get("/api/metrics")
    async def get_metrics():
        """Get pipeline performance metrics."""
        return state.get_pipeline_metrics()

    # ── Onboarding ───────────────────────────────────────────────────

    @app.get("/api/onboarding/status")
    async def onboarding_status():
        """Check if onboarding has been completed."""
        return {"completed": state.onboarding_completed}

    @app.post("/api/onboarding/complete")
    async def complete_onboarding():
        """Mark onboarding as complete."""
        state.onboarding_completed = True
        return {"status": "completed"}

    # ── WebSocket for real-time updates ──────────────────────────────

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        """Real-time suggestion stream to the Tauri frontend."""
        await ws.accept()
        state.add_ws_client(ws)
        try:
            while True:
                # Keep connection alive; client can also send commands
                data = await ws.receive_text()
                if data == "ping":
                    await ws.send_text("pong")
        except WebSocketDisconnect:
            state.remove_ws_client(ws)

    return app
