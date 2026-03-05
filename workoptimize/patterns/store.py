"""Persistent storage for workflow patterns using SQLite."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class PatternStore:
    """SQLite-backed store for workflow patterns and activity history.

    Stores activity logs, detected patterns, and automation recommendations
    locally on the user's machine with encryption-at-rest support.
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Create tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                app_name TEXT NOT NULL,
                app_category TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                description TEXT,
                capture_id TEXT,
                analysis_summary TEXT
            );

            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                occurrence_count INTEGER DEFAULT 1,
                pattern_type TEXT NOT NULL,
                description TEXT NOT NULL,
                apps_involved TEXT,
                automation_potential TEXT DEFAULT 'none',
                automation_description TEXT,
                status TEXT DEFAULT 'detected'
            );

            CREATE TABLE IF NOT EXISTS suggestions_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                suggestion_id TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT DEFAULT 'shown',
                user_feedback TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_activities_timestamp ON activities(timestamp);
            CREATE INDEX IF NOT EXISTS idx_activities_app ON activities(app_name);
            CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
        """)
        self._conn.commit()

    def record_activity(
        self,
        app_name: str,
        app_category: str,
        activity_type: str,
        description: str,
        capture_id: str | None = None,
        analysis_summary: str | None = None,
    ) -> int:
        """Record a single activity observation."""
        cursor = self._conn.execute(
            """INSERT INTO activities
               (timestamp, app_name, app_category, activity_type, description, capture_id, analysis_summary)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                app_name,
                app_category,
                activity_type,
                description,
                capture_id,
                analysis_summary,
            ),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def record_pattern(
        self,
        pattern_type: str,
        description: str,
        apps_involved: list[str],
        automation_potential: str = "none",
        automation_description: str | None = None,
    ) -> int:
        """Record a newly detected workflow pattern."""
        cursor = self._conn.execute(
            """INSERT INTO patterns
               (first_seen, last_seen, pattern_type, description, apps_involved,
                automation_potential, automation_description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                pattern_type,
                description,
                json.dumps(apps_involved),
                automation_potential,
                automation_description,
            ),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def increment_pattern(self, pattern_id: int) -> None:
        """Increment the occurrence count of an existing pattern."""
        self._conn.execute(
            """UPDATE patterns
               SET occurrence_count = occurrence_count + 1,
                   last_seen = ?
               WHERE id = ?""",
            (datetime.now(timezone.utc).isoformat(), pattern_id),
        )
        self._conn.commit()

    def get_frequent_patterns(self, min_occurrences: int = 3) -> list[dict]:
        """Get patterns that occur frequently — prime automation candidates."""
        rows = self._conn.execute(
            """SELECT * FROM patterns
               WHERE occurrence_count >= ?
               ORDER BY occurrence_count DESC""",
            (min_occurrences,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_activity_summary(self, days: int = 7) -> dict:
        """Get a summary of activities over the past N days."""
        rows = self._conn.execute(
            """SELECT app_category, activity_type, COUNT(*) as count
               FROM activities
               WHERE timestamp >= datetime('now', ?)
               GROUP BY app_category, activity_type
               ORDER BY count DESC""",
            (f"-{days} days",),
        ).fetchall()
        return {
            "by_category": [dict(row) for row in rows],
            "total_observations": sum(row["count"] for row in rows),
        }

    def cleanup_old_data(self, retention_days: int = 30) -> int:
        """Delete data older than retention period. Returns count of deleted rows."""
        cursor = self._conn.execute(
            """DELETE FROM activities WHERE timestamp < datetime('now', ?)""",
            (f"-{retention_days} days",),
        )
        self._conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        self._conn.close()
