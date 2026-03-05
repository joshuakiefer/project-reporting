"""Cross-platform screen capture with privacy controls."""

import base64
import hashlib
import io
import logging
import platform
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CaptureResult:
    """A single screen capture with metadata."""
    capture_id: str
    timestamp: datetime
    image_bytes: bytes
    image_base64: str
    width: int
    height: int
    active_app: str
    active_window_title: str
    data_hash: str
    metadata: dict = field(default_factory=dict)


class ScreenCapture:
    """Captures the screen at configurable intervals with privacy safeguards.

    Supports Windows (win32), macOS (Quartz), and Linux (X11/Wayland via PIL).
    Screenshots are taken only when capture is explicitly enabled by the user.
    """

    def __init__(
        self,
        capture_interval: float = 5.0,
        excluded_apps: list[str] | None = None,
        excluded_window_titles: list[str] | None = None,
    ):
        self._interval = capture_interval
        self._excluded_apps = set(a.lower() for a in (excluded_apps or []))
        self._excluded_titles = set(t.lower() for t in (excluded_window_titles or []))
        self._is_capturing = False
        self._last_capture_time = 0.0
        self._system = platform.system()

    @property
    def is_capturing(self) -> bool:
        return self._is_capturing

    def start(self) -> None:
        """Enable screen capture."""
        self._is_capturing = True
        logger.info("Screen capture started (interval=%.1fs)", self._interval)

    def stop(self) -> None:
        """Disable screen capture."""
        self._is_capturing = False
        logger.info("Screen capture stopped")

    def capture(self) -> CaptureResult | None:
        """Take a single screenshot if capture is enabled and interval has elapsed.

        Returns None if:
        - Capture is disabled
        - Interval hasn't elapsed since last capture
        - Active application is in the exclusion list
        """
        if not self._is_capturing:
            return None

        now = time.time()
        if now - self._last_capture_time < self._interval:
            return None

        active_app, window_title = self._get_active_window_info()

        # Check exclusion lists
        if active_app.lower() in self._excluded_apps:
            logger.debug("Skipping capture — excluded app: %s", active_app)
            return None
        if any(exc in window_title.lower() for exc in self._excluded_titles):
            logger.debug("Skipping capture — excluded title: %s", window_title)
            return None

        image_bytes, width, height = self._take_screenshot()
        self._last_capture_time = now

        data_hash = hashlib.sha256(image_bytes).hexdigest()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")

        return CaptureResult(
            capture_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            image_bytes=image_bytes,
            image_base64=image_b64,
            width=width,
            height=height,
            active_app=active_app,
            active_window_title=window_title,
            data_hash=data_hash,
        )

    def _take_screenshot(self) -> tuple[bytes, int, int]:
        """Platform-specific screenshot. Returns (png_bytes, width, height)."""
        try:
            from PIL import ImageGrab

            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue(), img.width, img.height
        except ImportError:
            raise RuntimeError(
                "Pillow is required for screen capture. Install with: pip install Pillow"
            )

    def _get_active_window_info(self) -> tuple[str, str]:
        """Get the active application name and window title.

        Returns (app_name, window_title). Falls back to ("unknown", "unknown")
        if platform detection is unavailable.
        """
        try:
            if self._system == "Windows":
                return self._get_active_window_windows()
            elif self._system == "Darwin":
                return self._get_active_window_macos()
            else:
                return self._get_active_window_linux()
        except Exception as e:
            logger.warning("Could not detect active window: %s", e)
            return ("unknown", "unknown")

    def _get_active_window_windows(self) -> tuple[str, str]:
        """Windows: Use win32gui to get foreground window info."""
        import ctypes
        import ctypes.wintypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        hwnd = user32.GetForegroundWindow()

        # Window title
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value

        # Process name
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        try:
            import psutil
            proc = psutil.Process(pid.value)
            app_name = proc.name()
        except Exception:
            app_name = "unknown"

        return (app_name, title)

    def _get_active_window_macos(self) -> tuple[str, str]:
        """macOS: Use AppKit/Quartz to detect active window."""
        try:
            from AppKit import NSWorkspace
            active_app = NSWorkspace.sharedWorkspace().activeApplication()
            app_name = active_app.get("NSApplicationName", "unknown")
            # Window title requires accessibility permissions
            return (app_name, app_name)
        except ImportError:
            return ("unknown", "unknown")

    def _get_active_window_linux(self) -> tuple[str, str]:
        """Linux: Use xdotool or similar to detect active window."""
        import subprocess

        try:
            window_id = subprocess.check_output(
                ["xdotool", "getactivewindow"], text=True
            ).strip()
            title = subprocess.check_output(
                ["xdotool", "getactivewindow", "getwindowname"], text=True
            ).strip()
            wm_class = subprocess.check_output(
                ["xprop", "-id", window_id, "WM_CLASS"],
                text=True,
            ).strip()
            # Parse WM_CLASS = "app", "App"
            parts = wm_class.split('"')
            app_name = parts[3] if len(parts) > 3 else parts[1] if len(parts) > 1 else "unknown"
            return (app_name, title)
        except Exception:
            return ("unknown", "unknown")
