"""Desktop overlay window for displaying suggestions and status."""

import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class OverlayMessage:
    """A message to display in the overlay."""
    title: str
    body: str
    category: str = "info"  # "info", "suggestion", "warning", "pattern"
    duration_ms: int = 8000
    actions: list[tuple[str, Callable]] | None = None  # (label, callback) pairs


class OverlayWindow:
    """Floating overlay window that shows suggestions and status.

    Runs in its own thread to avoid blocking the main capture/analysis loop.
    The overlay appears as a small popup in the corner of the screen.
    """

    COLORS = {
        "info": "#2196F3",
        "suggestion": "#4CAF50",
        "warning": "#FF9800",
        "pattern": "#9C27B0",
    }

    def __init__(
        self,
        position: str = "bottom-right",
        width: int = 380,
        opacity: float = 0.92,
        theme: str = "dark",
    ):
        self._position = position
        self._width = width
        self._opacity = opacity
        self._theme = theme
        self._message_queue: queue.Queue[OverlayMessage | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._root: tk.Tk | None = None
        self._is_running = False
        self._is_paused = False
        self._on_dismiss: Callable[[str], None] | None = None
        self._on_ask_question: Callable[[str], None] | None = None

    def start(self) -> None:
        """Start the overlay window in a background thread."""
        if self._is_running:
            return
        self._is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Overlay window started (position=%s)", self._position)

    def stop(self) -> None:
        """Stop the overlay window."""
        self._is_running = False
        self._message_queue.put(None)  # Signal to exit
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass

    def show_message(self, message: OverlayMessage) -> None:
        """Queue a message to be displayed in the overlay."""
        if self._is_paused:
            return
        self._message_queue.put(message)

    def show_suggestion(self, title: str, body: str, suggestion_id: str = "") -> None:
        """Convenience method to show a suggestion."""
        self.show_message(OverlayMessage(
            title=title,
            body=body,
            category="suggestion",
            duration_ms=10000,
        ))

    def show_pattern_alert(self, description: str, automation_idea: str) -> None:
        """Show an alert about a detected workflow pattern."""
        self.show_message(OverlayMessage(
            title="Workflow Pattern Detected",
            body=f"{description}\n\nSuggestion: {automation_idea}",
            category="pattern",
            duration_ms=15000,
        ))

    def show_status(self, status: str) -> None:
        """Show a brief status message."""
        self.show_message(OverlayMessage(
            title="WorkOptimize",
            body=status,
            category="info",
            duration_ms=3000,
        ))

    def pause(self) -> None:
        """Pause showing messages (user wants focus)."""
        self._is_paused = True

    def resume(self) -> None:
        """Resume showing messages."""
        self._is_paused = False

    def set_callbacks(
        self,
        on_dismiss: Callable[[str], None] | None = None,
        on_ask_question: Callable[[str], None] | None = None,
    ) -> None:
        """Set callback functions for user interactions."""
        self._on_dismiss = on_dismiss
        self._on_ask_question = on_ask_question

    def _run(self) -> None:
        """Main loop for the overlay window (runs in background thread)."""
        try:
            self._root = tk.Tk()
            self._root.title("WorkOptimize AI")
            self._root.overrideredirect(True)  # Remove window decorations
            self._root.attributes("-topmost", True)
            try:
                self._root.attributes("-alpha", self._opacity)
            except tk.TclError:
                pass  # Alpha not supported on all platforms

            # Configure dark theme
            bg_color = "#1E1E1E" if self._theme == "dark" else "#FFFFFF"
            fg_color = "#FFFFFF" if self._theme == "dark" else "#333333"

            self._root.configure(bg=bg_color)

            # Position the window
            screen_w = self._root.winfo_screenwidth()
            screen_h = self._root.winfo_screenheight()
            x, y = self._calculate_position(screen_w, screen_h)
            self._root.geometry(f"{self._width}x200+{x}+{y}")

            # Main frame
            self._frame = tk.Frame(self._root, bg=bg_color, padx=12, pady=8)
            self._frame.pack(fill=tk.BOTH, expand=True)

            # Status indicator
            self._status_bar = tk.Frame(self._frame, bg="#4CAF50", height=3)
            self._status_bar.pack(fill=tk.X, pady=(0, 8))

            # Title
            self._title_label = tk.Label(
                self._frame, text="WorkOptimize AI", font=("Helvetica", 12, "bold"),
                bg=bg_color, fg=fg_color, anchor="w",
            )
            self._title_label.pack(fill=tk.X)

            # Body
            self._body_label = tk.Label(
                self._frame, text="Watching your workflow...", font=("Helvetica", 10),
                bg=bg_color, fg=fg_color, anchor="w", justify=tk.LEFT, wraplength=self._width - 30,
            )
            self._body_label.pack(fill=tk.X, pady=(4, 0))

            # Buttons frame
            self._buttons_frame = tk.Frame(self._frame, bg=bg_color)
            self._buttons_frame.pack(fill=tk.X, pady=(8, 0))

            # Initially hide until first message
            self._root.withdraw()

            # Poll for messages
            self._poll_messages()

            self._root.mainloop()
        except Exception as e:
            logger.error("Overlay window error: %s", e)
            self._is_running = False

    def _poll_messages(self) -> None:
        """Check for new messages from the queue."""
        if not self._is_running:
            return

        try:
            message = self._message_queue.get_nowait()
            if message is None:
                self._root.destroy()  # type: ignore[union-attr]
                return
            self._display_message(message)
        except queue.Empty:
            pass

        if self._root:
            self._root.after(200, self._poll_messages)

    def _display_message(self, message: OverlayMessage) -> None:
        """Update the overlay with a new message."""
        if not self._root:
            return

        color = self.COLORS.get(message.category, self.COLORS["info"])

        self._status_bar.configure(bg=color)
        self._title_label.configure(text=message.title)
        self._body_label.configure(text=message.body)

        # Show the window
        self._root.deiconify()

        # Reposition (in case screen changed)
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x, y = self._calculate_position(screen_w, screen_h)
        # Adjust height based on content
        self._root.geometry(f"{self._width}x200+{x}+{y}")

        # Auto-hide after duration
        self._root.after(message.duration_ms, self._root.withdraw)

    def _calculate_position(self, screen_w: int, screen_h: int) -> tuple[int, int]:
        """Calculate window position based on configured corner."""
        margin = 20
        h = 200

        positions = {
            "bottom-right": (screen_w - self._width - margin, screen_h - h - margin - 40),
            "bottom-left": (margin, screen_h - h - margin - 40),
            "top-right": (screen_w - self._width - margin, margin),
            "top-left": (margin, margin),
        }
        return positions.get(self._position, positions["bottom-right"])
