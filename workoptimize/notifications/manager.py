"""Smart notification manager with priority queuing and deduplication.

Prevents notification fatigue by:
- Queuing suggestions by priority and spacing them out
- Deduplicating similar suggestions within a time window
- Suppressing notifications during detected focus periods
- Batching low-priority items into periodic digests
- Adapting frequency based on user engagement
"""

import hashlib
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    CRITICAL = 1   # Security warning, error that needs attention
    HIGH = 2       # Direct answer to a user question
    MEDIUM = 3     # Useful tip for current task
    LOW = 4        # General optimization suggestion
    DIGEST = 5     # Batch into periodic digest


@dataclass
class Notification:
    """A queued notification."""
    id: str
    title: str
    body: str
    category: str
    priority: Priority
    created_at: float
    content_hash: str
    shown: bool = False
    dismissed: bool = False
    helpful: bool | None = None


@dataclass
class NotificationConfig:
    min_interval_seconds: float = 30.0     # Min time between notifications
    focus_mode_interval: float = 300.0     # 5 min between notifications during focus
    max_queue_size: int = 50
    dedup_window_seconds: float = 600.0    # 10 min dedup window
    digest_interval_seconds: float = 1800.0  # 30 min digest batches
    suppress_during_typing: bool = True     # Don't interrupt typing


class NotificationManager:
    """Manages notification delivery with smart queuing."""

    def __init__(self, config: NotificationConfig | None = None):
        self.config = config or NotificationConfig()
        self._queue: deque[Notification] = deque(maxlen=self.config.max_queue_size)
        self._shown_hashes: dict[str, float] = {}  # hash → timestamp
        self._last_shown_at: float = 0.0
        self._focus_mode = False
        self._user_typing = False
        self._dismissed_count = 0
        self._helpful_count = 0
        self._total_shown = 0

    def enqueue(self, title: str, body: str, category: str = "tip",
                priority: Priority = Priority.MEDIUM) -> Notification | None:
        """Add a notification to the queue. Returns None if deduplicated."""
        content_hash = hashlib.md5(f"{title}:{body}".encode()).hexdigest()[:12]

        # Dedup check
        if content_hash in self._shown_hashes:
            age = time.time() - self._shown_hashes[content_hash]
            if age < self.config.dedup_window_seconds:
                return None

        notification = Notification(
            id=f"n-{content_hash}-{int(time.time())}",
            title=title,
            body=body,
            category=category,
            priority=priority,
            created_at=time.time(),
            content_hash=content_hash,
        )

        # Insert by priority (higher priority = lower number = front of queue)
        inserted = False
        for i, existing in enumerate(self._queue):
            if notification.priority < existing.priority:
                self._queue.insert(i, notification)
                inserted = True
                break
        if not inserted:
            self._queue.append(notification)

        return notification

    def get_next(self) -> Notification | None:
        """Get the next notification to show, respecting timing rules."""
        if not self._queue:
            return None

        now = time.time()
        interval = (
            self.config.focus_mode_interval if self._focus_mode
            else self.config.min_interval_seconds
        )

        # Check timing
        if now - self._last_shown_at < interval:
            # Allow critical notifications through
            if self._queue[0].priority > Priority.CRITICAL:
                return None

        # Check typing suppression
        if self.config.suppress_during_typing and self._user_typing:
            if self._queue[0].priority > Priority.HIGH:
                return None

        notification = self._queue.popleft()
        notification.shown = True
        self._last_shown_at = now
        self._shown_hashes[notification.content_hash] = now
        self._total_shown += 1

        # Clean old hashes
        cutoff = now - self.config.dedup_window_seconds
        self._shown_hashes = {h: t for h, t in self._shown_hashes.items() if t > cutoff}

        return notification

    def get_digest(self) -> list[Notification]:
        """Get all low-priority notifications as a batch digest."""
        digest = []
        remaining = deque()
        for n in self._queue:
            if n.priority >= Priority.LOW:
                digest.append(n)
            else:
                remaining.append(n)
        self._queue = remaining
        return digest

    def record_feedback(self, notification_id: str, helpful: bool) -> None:
        """Record user feedback to adapt notification frequency."""
        if helpful:
            self._helpful_count += 1
        else:
            self._dismissed_count += 1

        # Adapt: if user dismisses a lot, slow down
        if self._total_shown > 10:
            dismiss_rate = self._dismissed_count / self._total_shown
            if dismiss_rate > 0.7:
                self.config.min_interval_seconds = min(
                    self.config.min_interval_seconds * 1.5, 120.0
                )
                logger.info(
                    "High dismiss rate (%.0f%%) — increasing interval to %.0fs",
                    dismiss_rate * 100, self.config.min_interval_seconds,
                )
            elif dismiss_rate < 0.3:
                self.config.min_interval_seconds = max(
                    self.config.min_interval_seconds * 0.8, 15.0
                )

    def set_focus_mode(self, enabled: bool) -> None:
        self._focus_mode = enabled

    def set_user_typing(self, typing: bool) -> None:
        self._user_typing = typing

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def engagement_rate(self) -> float:
        if self._total_shown == 0:
            return 0.0
        return self._helpful_count / self._total_shown
