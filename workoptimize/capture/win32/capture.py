"""Windows-native screen capture using Win32 APIs.

Uses ctypes to call Windows APIs directly — no heavy dependencies.
Captures the active window, detects the foreground application,
and monitors the clipboard for copy-paste workflow detection.
"""

import ctypes
import ctypes.wintypes as wintypes
import io
import logging
import struct
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Win32 Constants ──────────────────────────────────────────────

SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
BI_RGB = 0
CF_TEXT = 1
CF_UNICODETEXT = 13
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
GMEM_MOVEABLE = 0x0002

# ── Win32 API Bindings ──────────────────────────────────────────

user32 = ctypes.windll.user32  # type: ignore[attr-defined]
kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
gdi32 = ctypes.windll.gdi32  # type: ignore[attr-defined]
psapi = ctypes.windll.psapi  # type: ignore[attr-defined]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


@dataclass
class WindowInfo:
    """Information about the active window."""
    hwnd: int
    title: str
    process_name: str
    process_id: int
    rect: tuple[int, int, int, int]  # left, top, right, bottom


@dataclass
class CaptureResult:
    """Result of a screen capture."""
    image_bytes: bytes  # Raw BMP data
    width: int
    height: int
    window: WindowInfo
    timestamp: float


class Win32ScreenCapture:
    """High-performance screen capture using Win32 GDI.

    Captures the active window (not full screen) to minimize data
    and focus analysis on what the user is actually looking at.
    """

    def __init__(self, capture_full_screen: bool = False):
        self._capture_full_screen = capture_full_screen

    def get_foreground_window(self) -> WindowInfo | None:
        """Get information about the currently focused window."""
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None

            # Window title
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

            # Process ID
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            # Process name
            process_name = self._get_process_name(pid.value)

            # Window rect
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))

            return WindowInfo(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                process_id=pid.value,
                rect=(rect.left, rect.top, rect.right, rect.bottom),
            )
        except Exception:
            logger.exception("Failed to get foreground window info")
            return None

    def capture(self) -> CaptureResult | None:
        """Capture the active window (or full screen) as BMP bytes."""
        try:
            window = self.get_foreground_window()
            if not window:
                return None

            if self._capture_full_screen:
                left, top = 0, 0
                width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
            else:
                left, top, right, bottom = window.rect
                width = right - left
                height = bottom - top

            if width <= 0 or height <= 0:
                return None

            # Get device contexts
            hwnd_dc = user32.GetDC(0)  # Full screen DC
            mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
            bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
            old_bitmap = gdi32.SelectObject(mem_dc, bitmap)

            # BitBlt the window content
            gdi32.BitBlt(mem_dc, 0, 0, width, height, hwnd_dc, left, top, SRCCOPY)

            # Get bitmap data
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = width
            bmi.bmiHeader.biHeight = -height  # Top-down
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 24
            bmi.bmiHeader.biCompression = BI_RGB

            # Calculate row size (must be DWORD-aligned)
            row_size = ((width * 3 + 3) // 4) * 4
            image_size = row_size * height

            buf = ctypes.create_string_buffer(image_size)
            gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), DIB_RGB_COLORS)

            # Build BMP file in memory
            bmp_data = self._build_bmp(buf.raw, width, height, row_size)

            # Cleanup GDI objects
            gdi32.SelectObject(mem_dc, old_bitmap)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(0, hwnd_dc)

            return CaptureResult(
                image_bytes=bmp_data,
                width=width,
                height=height,
                window=window,
                timestamp=time.time(),
            )
        except Exception:
            logger.exception("Screen capture failed")
            return None

    def capture_as_png(self) -> CaptureResult | None:
        """Capture and convert to PNG for efficient API transmission."""
        result = self.capture()
        if result is None:
            return None

        try:
            from PIL import Image
            img = Image.open(io.BytesIO(result.image_bytes))
            png_buffer = io.BytesIO()
            img.save(png_buffer, format="PNG", optimize=True)
            result.image_bytes = png_buffer.getvalue()
            return result
        except ImportError:
            # Fall back to BMP if Pillow not available
            return result

    @staticmethod
    def _get_process_name(pid: int) -> str:
        """Get the executable name for a process ID."""
        try:
            handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
            if not handle:
                return "unknown"

            buf = ctypes.create_unicode_buffer(260)
            psapi.GetModuleBaseNameW(handle, None, buf, 260)
            kernel32.CloseHandle(handle)
            return buf.value or "unknown"
        except Exception:
            return "unknown"

    @staticmethod
    def _build_bmp(pixel_data: bytes, width: int, height: int, row_size: int) -> bytes:
        """Build a complete BMP file from raw pixel data."""
        file_header_size = 14
        info_header_size = 40
        pixel_offset = file_header_size + info_header_size
        file_size = pixel_offset + len(pixel_data)

        # BMP file header
        file_header = struct.pack(
            "<2sIHHI",
            b"BM",
            file_size,
            0,
            0,
            pixel_offset,
        )

        # BMP info header
        info_header = struct.pack(
            "<IiiHHIIiiII",
            info_header_size,
            width,
            -height,  # Top-down
            1,  # planes
            24,  # bits per pixel
            BI_RGB,
            len(pixel_data),
            0,
            0,
            0,
            0,
        )

        return file_header + info_header + pixel_data


class ClipboardMonitor:
    """Monitors the Windows clipboard for copy-paste workflow detection.

    Tracks clipboard changes to detect when users copy from one app
    and paste into another — a key signal for automation opportunities.
    """

    def __init__(self):
        self._last_content_hash: int = 0
        self._last_sequence: int = 0
        self._copy_source: WindowInfo | None = None
        self._copy_timestamp: float = 0.0

    def check_clipboard_change(self, current_window: WindowInfo | None) -> dict | None:
        """Check if clipboard content changed. Returns change info or None."""
        try:
            sequence = user32.GetClipboardSequenceNumber()
            if sequence == self._last_sequence:
                return None

            self._last_sequence = sequence

            # Record where the copy happened
            old_source = self._copy_source
            self._copy_source = current_window
            self._copy_timestamp = time.time()

            # Get clipboard text (if any)
            text_preview = self._get_clipboard_text()
            content_hash = hash(text_preview) if text_preview else 0

            if content_hash == self._last_content_hash:
                return None

            self._last_content_hash = content_hash

            return {
                "event": "clipboard_change",
                "source_app": current_window.process_name if current_window else "unknown",
                "source_title": current_window.title if current_window else "",
                "has_text": text_preview is not None,
                "text_length": len(text_preview) if text_preview else 0,
                "timestamp": self._copy_timestamp,
                "previous_source": old_source.process_name if old_source else None,
            }
        except Exception:
            return None

    def detect_paste_workflow(self, current_window: WindowInfo | None) -> dict | None:
        """Detect if the user is pasting content from a different app.

        Call this when you detect a Ctrl+V or typing activity in a new app.
        Returns workflow info if a cross-app paste is detected.
        """
        if self._copy_source is None or current_window is None:
            return None

        # Cross-app paste detected
        if self._copy_source.process_name != current_window.process_name:
            elapsed = time.time() - self._copy_timestamp
            if elapsed < 300:  # Within 5 minutes
                return {
                    "event": "cross_app_paste",
                    "source_app": self._copy_source.process_name,
                    "source_title": self._copy_source.title,
                    "target_app": current_window.process_name,
                    "target_title": current_window.title,
                    "elapsed_seconds": elapsed,
                }
        return None

    @staticmethod
    def _get_clipboard_text() -> str | None:
        """Read text from the clipboard."""
        try:
            if not user32.OpenClipboard(0):
                return None

            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                user32.CloseClipboard()
                return None

            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                user32.CloseClipboard()
                return None

            text = ctypes.wstring_at(ptr)
            kernel32.GlobalUnlock(handle)
            user32.CloseClipboard()

            # Return truncated preview (never store full clipboard content)
            return text[:200] if text else None
        except Exception:
            try:
                user32.CloseClipboard()
            except Exception:
                pass
            return None
