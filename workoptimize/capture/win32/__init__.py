"""Windows-native capture module."""

from workoptimize.capture.win32.capture import (
    Win32ScreenCapture,
    ClipboardMonitor,
    WindowInfo,
    CaptureResult,
)

__all__ = ["Win32ScreenCapture", "ClipboardMonitor", "WindowInfo", "CaptureResult"]
