"""End-to-end capture → analyze → suggest pipeline.

This is the brain of the application. Every capture cycle:
1. Captures the active window (Win32 native)
2. Checks privacy filters (skip sensitive apps)
3. Monitors clipboard for cross-app workflows
4. Detects the active application and classifies the activity
5. Sends the screenshot to Claude's vision API with app-specific prompts
6. Generates and ranks suggestions
7. Tracks patterns over time
8. Broadcasts to the frontend via WebSocket

The pipeline runs as an async loop, coordinated by the API state manager.
"""

import asyncio
import base64
import hashlib
import io
import logging
import platform
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the capture pipeline."""
    capture_interval: float = 5.0
    min_change_threshold: float = 0.05  # Minimum visual change to trigger analysis
    max_api_calls_per_minute: int = 6
    enable_clipboard_monitoring: bool = True
    enable_pattern_tracking: bool = True
    smart_capture: bool = True  # Only analyze when screen changes significantly


@dataclass
class CaptureFrame:
    """A single frame from the capture pipeline."""
    image_bytes: bytes
    image_base64: str
    width: int
    height: int
    app_name: str
    window_title: str
    process_id: int
    timestamp: float
    content_hash: str
    clipboard_event: dict | None = None


@dataclass
class AnalysisResult:
    """Result from the Claude vision analysis."""
    suggestions: list[dict]
    detected_activity: str
    context_summary: str
    app_category: str
    confidence: float
    raw_response: str


@dataclass
class PipelineMetrics:
    """Runtime metrics for the pipeline."""
    total_captures: int = 0
    total_analyses: int = 0
    total_suggestions: int = 0
    skipped_no_change: int = 0
    skipped_privacy: int = 0
    api_errors: int = 0
    avg_analysis_ms: float = 0.0
    _analysis_times: list[float] = field(default_factory=list)

    def record_analysis_time(self, ms: float) -> None:
        self._analysis_times.append(ms)
        if len(self._analysis_times) > 100:
            self._analysis_times = self._analysis_times[-50:]
        self.avg_analysis_ms = sum(self._analysis_times) / len(self._analysis_times)


class CapturePipeline:
    """Orchestrates the full capture → analysis → suggestion pipeline.

    This is designed to be platform-aware. On Windows, it uses Win32 native
    APIs. On other platforms, it falls back to cross-platform capture.
    """

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        self.metrics = PipelineMetrics()
        self._running = False
        self._paused = False
        self._last_content_hash: str = ""
        self._api_call_timestamps: list[float] = []
        self._listeners: list = []

        # Initialize platform-specific capture
        self._capturer = None
        self._clipboard = None
        self._privacy_filter = None
        self._analyzer = None
        self._pattern_tracker = None

    async def initialize(self, anthropic_api_key: str, data_dir: str) -> None:
        """Initialize all pipeline components."""
        from workoptimize.capture.privacy import PrivacyFilter
        from workoptimize.analysis.vision import ScreenAnalyzer

        self._privacy_filter = PrivacyFilter()

        # Initialize the Claude vision analyzer
        self._analyzer = ScreenAnalyzer(api_key=anthropic_api_key)

        # Platform-specific capture
        if platform.system() == "Windows":
            from workoptimize.capture.win32.capture import Win32ScreenCapture, ClipboardMonitor
            self._capturer = Win32ScreenCapture()
            if self.config.enable_clipboard_monitoring:
                self._clipboard = ClipboardMonitor()
        else:
            from workoptimize.capture.screen import ScreenCapture
            self._capturer = ScreenCapture()

        # Pattern tracking
        if self.config.enable_pattern_tracking:
            from workoptimize.patterns.store import PatternStore
            from workoptimize.patterns.tracker import PatternTracker
            from pathlib import Path
            store = PatternStore(Path(data_dir))
            self._pattern_tracker = PatternTracker(store)

        logger.info("Pipeline initialized (platform=%s)", platform.system())

    async def run(self) -> None:
        """Main pipeline loop."""
        self._running = True
        logger.info("Pipeline started (interval=%.1fs)", self.config.capture_interval)

        while self._running:
            if not self._paused:
                try:
                    await self._cycle()
                except Exception:
                    logger.exception("Pipeline cycle error")
                    self.metrics.api_errors += 1

            await asyncio.sleep(self.config.capture_interval)

    def stop(self) -> None:
        self._running = False

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def add_listener(self, callback) -> None:
        """Add a callback that receives pipeline events."""
        self._listeners.append(callback)

    async def _cycle(self) -> None:
        """Single capture cycle."""
        # Step 1: Capture
        frame = await self._capture()
        if frame is None:
            return

        self.metrics.total_captures += 1

        # Step 2: Privacy check
        if self._privacy_filter and not self._privacy_filter.should_capture(
            frame.app_name, frame.window_title
        ):
            self.metrics.skipped_privacy += 1
            await self._emit("capture_skipped", {"reason": "privacy", "app": frame.app_name})
            return

        # Step 3: Smart capture — skip if screen hasn't changed much
        if self.config.smart_capture and frame.content_hash == self._last_content_hash:
            self.metrics.skipped_no_change += 1
            return

        self._last_content_hash = frame.content_hash

        # Step 4: Rate limiting
        if not self._can_call_api():
            return

        # Step 5: Analyze with Claude
        start_ms = time.time() * 1000
        analysis = await self._analyze(frame)
        elapsed_ms = (time.time() * 1000) - start_ms

        if analysis is None:
            return

        self.metrics.total_analyses += 1
        self.metrics.record_analysis_time(elapsed_ms)

        # Step 6: Process suggestions
        for suggestion in analysis.suggestions:
            self.metrics.total_suggestions += 1
            await self._emit("new_suggestion", suggestion)

        # Step 7: Track patterns
        if self._pattern_tracker and analysis.detected_activity:
            await self._track_pattern(frame, analysis)

        # Step 8: Clipboard workflow detection
        if frame.clipboard_event:
            await self._emit("clipboard_event", frame.clipboard_event)

        # Step 9: Emit analysis summary
        await self._emit("analysis_complete", {
            "app": frame.app_name,
            "activity": analysis.detected_activity,
            "suggestions_count": len(analysis.suggestions),
            "elapsed_ms": elapsed_ms,
        })

    async def _capture(self) -> CaptureFrame | None:
        """Capture the current screen."""
        if self._capturer is None:
            return None

        # Platform-specific capture
        if platform.system() == "Windows":
            result = self._capturer.capture_as_png()
            if result is None:
                return None

            image_b64 = base64.b64encode(result.image_bytes).decode()
            content_hash = hashlib.md5(result.image_bytes[:4096]).hexdigest()

            # Check clipboard
            clipboard_event = None
            if self._clipboard:
                clipboard_event = self._clipboard.check_clipboard_change(result.window)

            return CaptureFrame(
                image_bytes=result.image_bytes,
                image_base64=image_b64,
                width=result.width,
                height=result.height,
                app_name=result.window.process_name,
                window_title=result.window.title,
                process_id=result.window.process_id,
                timestamp=result.timestamp,
                content_hash=content_hash,
                clipboard_event=clipboard_event,
            )
        else:
            # Cross-platform fallback
            result = self._capturer.capture()
            if result is None:
                return None
            image_b64 = base64.b64encode(result["image_bytes"]).decode()
            content_hash = hashlib.md5(result["image_bytes"][:4096]).hexdigest()

            return CaptureFrame(
                image_bytes=result["image_bytes"],
                image_base64=image_b64,
                width=result.get("width", 0),
                height=result.get("height", 0),
                app_name=result.get("app_name", "unknown"),
                window_title=result.get("window_title", ""),
                process_id=result.get("process_id", 0),
                timestamp=time.time(),
                content_hash=content_hash,
            )

    async def _analyze(self, frame: CaptureFrame) -> AnalysisResult | None:
        """Send frame to Claude vision API for analysis."""
        if self._analyzer is None:
            return None

        try:
            result = await asyncio.to_thread(
                self._analyzer.analyze_screenshot,
                image_base64=frame.image_base64,
                app_name=frame.app_name,
                window_title=frame.window_title,
            )

            if result is None:
                return None

            return AnalysisResult(
                suggestions=result.get("suggestions", []),
                detected_activity=result.get("activity", "unknown"),
                context_summary=result.get("summary", ""),
                app_category=result.get("category", "other"),
                confidence=result.get("confidence", 0.0),
                raw_response=result.get("raw", ""),
            )
        except Exception:
            logger.exception("Claude analysis failed")
            self.metrics.api_errors += 1
            return None

    async def _track_pattern(self, frame: CaptureFrame, analysis: AnalysisResult) -> None:
        """Record activity for pattern detection."""
        if self._pattern_tracker is None:
            return

        from workoptimize.context.classifier import Activity, ActivityType
        from workoptimize.context.detector import AppContext, AppCategory

        # Map analysis results to pattern tracking types
        activity_map = {
            "typing": ActivityType.DATA_ENTRY,
            "reading": ActivityType.READING,
            "browsing": ActivityType.BROWSING,
            "data_entry": ActivityType.DATA_ENTRY,
            "spreadsheet": ActivityType.DATA_ENTRY,
            "navigation": ActivityType.BROWSING,
        }

        activity_type = activity_map.get(
            analysis.detected_activity, ActivityType.OTHER
        )

        category_map = {
            "spreadsheet": AppCategory.SPREADSHEET,
            "word_processor": AppCategory.DOCUMENT,
            "presentation": AppCategory.PRESENTATION,
            "browser": AppCategory.BROWSER,
            "email": AppCategory.EMAIL,
            "accounting": AppCategory.ACCOUNTING,
        }

        app_category = category_map.get(
            analysis.app_category, AppCategory.OTHER
        )

        app_context = AppContext(
            app_name=frame.app_name,
            window_title=frame.window_title,
            category=app_category,
        )

        activity = Activity(
            app_context=app_context,
            activity_type=activity_type,
            description=analysis.context_summary,
            timestamp=frame.timestamp,
        )

        new_patterns = self._pattern_tracker.record_activity(activity)
        for pattern in new_patterns:
            await self._emit("pattern_detected", {
                "type": pattern.pattern_type,
                "description": pattern.description,
                "apps": pattern.apps_involved,
                "potential": pattern.automation_potential,
                "idea": pattern.automation_idea,
            })

    def _can_call_api(self) -> bool:
        """Rate limit API calls."""
        now = time.time()
        # Clean old timestamps
        self._api_call_timestamps = [t for t in self._api_call_timestamps if now - t < 60]

        if len(self._api_call_timestamps) >= self.config.max_api_calls_per_minute:
            return False

        self._api_call_timestamps.append(now)
        return True

    async def _emit(self, event: str, data: dict) -> None:
        """Emit an event to all listeners."""
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event, data)
                else:
                    listener(event, data)
            except Exception:
                logger.exception("Listener error for event: %s", event)

    # ── On-demand analysis ───────────────────────────────────────

    async def ask_about_screen(self, question: str) -> str:
        """Capture the current screen and answer a specific question."""
        frame = await self._capture()
        if frame is None:
            return "Unable to capture the screen right now."

        if self._analyzer is None:
            return "Analysis engine not initialized."

        try:
            result = await asyncio.to_thread(
                self._analyzer.ask_question,
                image_base64=frame.image_base64,
                question=question,
                app_name=frame.app_name,
                window_title=frame.window_title,
            )
            return result or "Could not generate an answer."
        except Exception:
            logger.exception("Ask question failed")
            return "Analysis failed. Please try again."
