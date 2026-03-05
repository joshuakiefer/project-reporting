"""Productivity analytics — focus scoring, time tracking, app usage breakdown.

Tracks how the user spends their time across applications and provides
actionable insights: focus score, context-switch frequency, time-on-task,
and productivity trends over days/weeks.
"""

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AppSession:
    """A continuous period of using a single application."""
    app_name: str
    window_title: str
    category: str
    started_at: float
    ended_at: float | None = None

    @property
    def duration_seconds(self) -> float:
        end = self.ended_at or time.time()
        return end - self.started_at


@dataclass
class FocusScore:
    """Focus score for a time period (0-100)."""
    score: int
    deep_work_minutes: float
    shallow_work_minutes: float
    context_switches: int
    longest_focus_streak_minutes: float
    top_distraction: str | None
    period_label: str


class ProductivityTracker:
    """Tracks productivity metrics and generates insights.

    Scoring methodology:
    - Deep work: Sustained focus (>5 min) in a productive app → high score
    - Context switching: Frequent app switches → lower score
    - Distraction: Time in non-work apps (social media, entertainment) → lower score
    - Consistency: Maintaining focus patterns over days → bonus
    """

    # Apps considered "deep work" by default
    PRODUCTIVE_APPS = {
        "excel", "word", "powerpoint", "code", "visual studio",
        "pycharm", "webstorm", "sublime", "notepad++", "quickbooks",
        "outlook", "teams", "slack", "terminal", "cmd", "powershell",
    }

    # Apps considered "distraction" by default
    DISTRACTION_APPS = {
        "facebook", "twitter", "instagram", "tiktok", "reddit",
        "youtube", "netflix", "twitch", "discord", "spotify",
    }

    # Minimum seconds in an app to count as a session
    MIN_SESSION_SECONDS = 3

    # Seconds of sustained focus to qualify as "deep work"
    DEEP_WORK_THRESHOLD = 300  # 5 minutes

    def __init__(self, data_dir: Path):
        self._db_path = data_dir / "analytics.db"
        self._current_session: AppSession | None = None
        self._context_switches_today = 0
        self._daily_sessions: list[AppSession] = []
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT NOT NULL,
                    window_title TEXT,
                    category TEXT,
                    started_at REAL NOT NULL,
                    ended_at REAL,
                    duration_seconds REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_scores (
                    date TEXT PRIMARY KEY,
                    score INTEGER,
                    deep_work_minutes REAL,
                    shallow_work_minutes REAL,
                    context_switches INTEGER,
                    longest_streak_minutes REAL,
                    data_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_started
                ON sessions(started_at)
            """)

    def record_app_change(self, app_name: str, window_title: str, category: str) -> None:
        """Record when the user switches to a different application."""
        now = time.time()

        # Close current session
        if self._current_session:
            self._current_session.ended_at = now
            if self._current_session.duration_seconds >= self.MIN_SESSION_SECONDS:
                self._save_session(self._current_session)
                self._daily_sessions.append(self._current_session)

            # Count context switch
            if self._current_session.app_name.lower() != app_name.lower():
                self._context_switches_today += 1

        # Start new session
        self._current_session = AppSession(
            app_name=app_name,
            window_title=window_title,
            category=category,
            started_at=now,
        )

    def get_focus_score(self, period: str = "today") -> FocusScore:
        """Calculate focus score for a time period."""
        now = time.time()

        if period == "today":
            start = self._start_of_day(now)
            label = "Today"
        elif period == "yesterday":
            start = self._start_of_day(now) - 86400
            label = "Yesterday"
        elif period == "week":
            start = self._start_of_day(now) - (86400 * 7)
            label = "This Week"
        else:
            start = self._start_of_day(now)
            label = period

        sessions = self._get_sessions(start, now)
        return self._calculate_focus_score(sessions, label)

    def get_app_usage(self, period: str = "today") -> list[dict]:
        """Get time spent in each application."""
        now = time.time()
        start = self._start_of_day(now) if period == "today" else now - (86400 * 7)

        sessions = self._get_sessions(start, now)
        usage: dict[str, float] = {}
        for s in sessions:
            key = s["app_name"]
            usage[key] = usage.get(key, 0) + s["duration_seconds"]

        total = sum(usage.values()) or 1
        result = []
        for app, seconds in sorted(usage.items(), key=lambda x: -x[1]):
            result.append({
                "app": app,
                "minutes": round(seconds / 60, 1),
                "percentage": round((seconds / total) * 100, 1),
            })
        return result

    def get_timeline(self, period: str = "today") -> list[dict]:
        """Get a timeline of app sessions for visualization."""
        now = time.time()
        start = self._start_of_day(now)
        sessions = self._get_sessions(start, now)

        return [
            {
                "app": s["app_name"],
                "category": s["category"],
                "start": s["started_at"],
                "end": s["ended_at"] or now,
                "duration_minutes": round(s["duration_seconds"] / 60, 1),
            }
            for s in sessions
        ]

    def get_trends(self, days: int = 7) -> list[dict]:
        """Get focus score trends over the past N days."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT date, score, deep_work_minutes, context_switches "
                "FROM daily_scores ORDER BY date DESC LIMIT ?",
                (days,),
            ).fetchall()

        return [
            {
                "date": row[0],
                "score": row[1],
                "deep_work_minutes": row[2],
                "context_switches": row[3],
            }
            for row in reversed(rows)
        ]

    def save_daily_score(self) -> None:
        """Calculate and persist today's focus score."""
        score = self.get_focus_score("today")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO daily_scores "
                "(date, score, deep_work_minutes, shallow_work_minutes, "
                "context_switches, longest_streak_minutes, data_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    today,
                    score.score,
                    score.deep_work_minutes,
                    score.shallow_work_minutes,
                    score.context_switches,
                    score.longest_focus_streak_minutes,
                    json.dumps({"top_distraction": score.top_distraction}),
                ),
            )

    def _calculate_focus_score(self, sessions: list[dict], label: str) -> FocusScore:
        """Calculate a focus score from a list of sessions."""
        if not sessions:
            return FocusScore(
                score=0, deep_work_minutes=0, shallow_work_minutes=0,
                context_switches=0, longest_focus_streak_minutes=0,
                top_distraction=None, period_label=label,
            )

        deep_work = 0.0
        shallow_work = 0.0
        distraction_time: dict[str, float] = {}
        streaks: list[float] = []
        current_streak = 0.0
        context_switches = 0
        prev_app = None

        for s in sessions:
            dur = s["duration_seconds"]
            app = s["app_name"].lower()

            # Classify
            is_productive = any(p in app for p in self.PRODUCTIVE_APPS)
            is_distraction = any(d in app for d in self.DISTRACTION_APPS)

            if is_productive:
                if dur >= self.DEEP_WORK_THRESHOLD:
                    deep_work += dur
                else:
                    shallow_work += dur

                current_streak += dur
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                    current_streak = 0
                shallow_work += dur

            if is_distraction:
                distraction_time[app] = distraction_time.get(app, 0) + dur

            if prev_app and prev_app != app:
                context_switches += 1
            prev_app = app

        if current_streak > 0:
            streaks.append(current_streak)

        total_time = deep_work + shallow_work
        longest_streak = max(streaks) if streaks else 0
        total_distraction = sum(distraction_time.values())
        top_distraction = max(distraction_time, key=distraction_time.get) if distraction_time else None

        # Score calculation (0-100)
        # 40% deep work ratio, 30% low context switches, 20% focus streaks, 10% low distraction
        deep_ratio = min(deep_work / max(total_time, 1), 1.0)
        switch_penalty = min(context_switches / 100, 1.0)
        streak_bonus = min(longest_streak / 3600, 1.0)  # Up to 1 hour
        distraction_penalty = min(total_distraction / max(total_time, 1), 1.0)

        score = int(
            (deep_ratio * 40)
            + ((1 - switch_penalty) * 30)
            + (streak_bonus * 20)
            + ((1 - distraction_penalty) * 10)
        )
        score = max(0, min(100, score))

        return FocusScore(
            score=score,
            deep_work_minutes=round(deep_work / 60, 1),
            shallow_work_minutes=round(shallow_work / 60, 1),
            context_switches=context_switches,
            longest_focus_streak_minutes=round(longest_streak / 60, 1),
            top_distraction=top_distraction,
            period_label=label,
        )

    def _save_session(self, session: AppSession) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (app_name, window_title, category, "
                "started_at, ended_at, duration_seconds) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session.app_name,
                    session.window_title,
                    session.category,
                    session.started_at,
                    session.ended_at,
                    session.duration_seconds,
                ),
            )

    def _get_sessions(self, start: float, end: float) -> list[dict]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM sessions WHERE started_at >= ? AND started_at <= ? "
                "ORDER BY started_at",
                (start, end),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def _start_of_day(ts: float) -> float:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return dt.timestamp()
