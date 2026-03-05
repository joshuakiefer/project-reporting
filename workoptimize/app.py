"""Main application orchestrator — ties all modules together."""

import hashlib
import logging
import signal
import sys
import time
from pathlib import Path

from workoptimize.analysis.vision import VisionAnalyzer
from workoptimize.automation.builder import AutomationBuilder
from workoptimize.capture.privacy import PrivacyFilter, PrivacyRule
from workoptimize.capture.screen import ScreenCapture
from workoptimize.config.settings import Settings
from workoptimize.context.classifier import ActivityClassifier
from workoptimize.context.detector import AppDetector
from workoptimize.patterns.store import PatternStore
from workoptimize.patterns.tracker import PatternTracker
from workoptimize.security.audit import AuditLogger
from workoptimize.security.encryption import DataEncryptor
from workoptimize.security.redaction import SensitiveDataRedactor
from workoptimize.suggestions.engine import SuggestionEngine
from workoptimize.ui.overlay import OverlayWindow

logger = logging.getLogger(__name__)


class WorkOptimizeApp:
    """Main application that orchestrates screen capture, analysis, and suggestions.

    Lifecycle:
    1. Load configuration
    2. Initialize all modules (security first)
    3. Start capture loop
    4. For each capture: detect context -> analyze -> generate suggestions -> display
    5. Track patterns over time
    6. Clean shutdown with data cleanup
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or Settings.load()
        self._running = False
        self._setup_logging()
        self._initialize_modules()

    def _setup_logging(self) -> None:
        log_dir = self._settings.data_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.FileHandler(log_dir / "workoptimize.log"),
                logging.StreamHandler(),
            ],
        )

    def _initialize_modules(self) -> None:
        """Initialize all application modules."""
        s = self._settings

        # Security (initialized first)
        self._encryptor = DataEncryptor(s.data_dir / "encrypted")
        self._audit = AuditLogger(s.data_dir / "audit")
        self._redactor = SensitiveDataRedactor(
            extra_patterns=s.security.extra_redaction_patterns or None
        )

        # Privacy filter
        custom_rules = []
        for app in s.capture.excluded_apps:
            custom_rules.append(PrivacyRule(f"user_excluded_{app}", "block_app", app))
        for title in s.capture.excluded_window_titles:
            custom_rules.append(PrivacyRule(f"user_excluded_{title}", "block_title", title))
        self._privacy_filter = PrivacyFilter(custom_rules=custom_rules)

        # Screen capture
        self._capture = ScreenCapture(
            capture_interval=s.capture.interval_seconds,
            excluded_apps=s.capture.excluded_apps,
        )

        # Analysis
        self._analyzer = VisionAnalyzer(
            api_key=s.api_key or None,
            model=s.analysis.model,
            max_tokens=s.analysis.max_tokens,
        )

        # Context detection
        self._app_detector = AppDetector()
        self._activity_classifier = ActivityClassifier()

        # Suggestions
        self._suggestion_engine = SuggestionEngine()

        # Pattern tracking
        self._pattern_store = PatternStore(s.data_dir / "patterns.db")
        self._pattern_tracker = PatternTracker(self._pattern_store)

        # Automation builder
        self._automation_builder = AutomationBuilder(
            api_key=s.api_key or None,
            model=s.analysis.model,
        )

        # UI
        self._overlay = OverlayWindow(
            position=s.ui.overlay_position,
            width=s.ui.width,
            opacity=s.ui.opacity,
            theme=s.ui.theme,
        )

        logger.info("All modules initialized")

    def run(self) -> None:
        """Start the application main loop."""
        if not self._settings.api_key:
            logger.error(
                "No API key found. Set ANTHROPIC_API_KEY environment variable "
                "or add api_key to config.yaml"
            )
            print("\nError: No Anthropic API key configured.")
            print("Set the ANTHROPIC_API_KEY environment variable or add it to config.yaml")
            sys.exit(1)

        # Initialize encryption if enabled
        if self._settings.security.encrypt_at_rest:
            import getpass
            passphrase = getpass.getpass("Enter encryption passphrase (for local data): ")
            self._encryptor.initialize(passphrase)
            logger.info("Encryption initialized")

        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Start UI overlay
        self._overlay.start()
        self._overlay.show_status("WorkOptimize AI is now watching your workflow...")

        # Start capture
        self._capture.start()
        self._running = True
        self._audit.log_event("app_started", {"config": str(self._settings.data_dir)})

        logger.info("WorkOptimize AI started — press Ctrl+C to stop")
        print("\nWorkOptimize AI is running. Press Ctrl+C to stop.\n")

        try:
            self._main_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown()

    def _main_loop(self) -> None:
        """Main capture-analyze-suggest loop."""
        analysis_count = 0

        while self._running:
            # Capture screen
            capture = self._capture.capture()
            if capture is None:
                time.sleep(0.5)
                continue

            # Privacy check
            if not self._privacy_filter.should_capture(
                capture.active_app, capture.active_window_title
            ):
                continue

            # Audit the capture
            if self._settings.security.audit_logging:
                self._audit.log_capture(
                    capture.capture_id, capture.active_app, capture.data_hash
                )

            # Detect context
            app_context = self._app_detector.detect(
                capture.active_app, capture.active_window_title
            )

            # Classify activity (quick, no API call)
            activity = self._activity_classifier.classify_from_context(app_context)

            # Analyze with Claude (every Nth capture or on context change)
            analysis_count += 1
            should_analyze = analysis_count % 3 == 0  # Analyze every 3rd capture to manage costs

            if should_analyze:
                try:
                    analysis = self._analyzer.analyze(capture)

                    # Audit the API call
                    if self._settings.security.audit_logging:
                        self._audit.log_analysis(
                            capture.capture_id,
                            analysis.model,
                            analysis.input_tokens + analysis.output_tokens,
                        )

                    # Enhance activity classification with AI analysis
                    activity = self._activity_classifier.classify_from_analysis(
                        app_context, analysis.response_text
                    )

                    # Generate suggestions
                    batch = self._suggestion_engine.generate_suggestions(analysis, activity)
                    for suggestion in batch.suggestions[:2]:  # Show top 2
                        self._overlay.show_suggestion(
                            suggestion.title, suggestion.description
                        )

                except Exception as e:
                    logger.error("Analysis failed: %s", e)

            # Track patterns
            if self._settings.analysis.enable_workflow_tracking:
                new_patterns = self._pattern_tracker.record_activity(activity)
                for pattern in new_patterns:
                    self._overlay.show_pattern_alert(
                        pattern.description,
                        pattern.automation_idea or "Review this workflow for optimization.",
                    )

            # Encrypt captured data if enabled
            if self._settings.security.encrypt_at_rest:
                encrypted = self._encryptor.encrypt(capture.image_bytes)
                # Store encrypted capture (optional persistence)
                capture_path = self._settings.data_dir / "captures" / f"{capture.capture_id}.enc"
                capture_path.parent.mkdir(parents=True, exist_ok=True)
                capture_path.write_bytes(encrypted)

            # Data retention cleanup (periodic)
            if analysis_count % 100 == 0:
                deleted = self._pattern_store.cleanup_old_data(
                    self._settings.security.retention_days
                )
                if deleted:
                    logger.info("Cleaned up %d old records", deleted)

    def get_optimization_report(self) -> dict:
        """Generate a report of detected patterns and recommendations."""
        return self._pattern_tracker.get_optimization_report()

    def ask_question(self, question: str) -> str:
        """Let the user ask a question about their current screen."""
        capture = self._capture.capture()
        if capture is None:
            return "No screen capture available. Make sure capture is running."

        result = self._analyzer.ask_about_screen(capture, question)
        return result.response_text

    def build_automation(self, pattern_index: int = 0) -> str:
        """Build an automation for the most impactful detected pattern."""
        patterns = self._pattern_store.get_frequent_patterns()
        if not patterns:
            return "No patterns detected yet. Keep working and I'll identify opportunities."

        from workoptimize.patterns.tracker import DetectedPattern

        p = patterns[min(pattern_index, len(patterns) - 1)]
        import json
        pattern = DetectedPattern(
            pattern_type=p["pattern_type"],
            description=p["description"],
            apps_involved=json.loads(p["apps_involved"]),
            occurrence_count=p["occurrence_count"],
            automation_potential=p["automation_potential"],
            automation_idea=p["automation_description"],
        )

        blueprint = self._automation_builder.build_automation(pattern)
        return (
            f"## {blueprint.title}\n\n"
            f"{blueprint.description}\n\n"
            f"### Code\n```\n{blueprint.implementation_code}\n```\n\n"
            f"### Setup\n{blueprint.setup_instructions}\n\n"
            f"Estimated time saved: {blueprint.estimated_time_saved}"
        )

    def _handle_shutdown(self, signum, frame) -> None:
        """Handle shutdown signals gracefully."""
        self._running = False

    def _shutdown(self) -> None:
        """Clean shutdown of all modules."""
        logger.info("Shutting down WorkOptimize AI...")
        self._capture.stop()
        self._overlay.stop()
        self._pattern_store.close()
        self._audit.log_event("app_stopped")
        logger.info("Shutdown complete")
        print("\nWorkOptimize AI stopped. Goodbye!")
