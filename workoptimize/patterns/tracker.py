"""Tracks workflow patterns over time to identify automation opportunities."""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from workoptimize.context.classifier import Activity, ActivityType
from workoptimize.context.detector import AppContext
from workoptimize.patterns.store import PatternStore

logger = logging.getLogger(__name__)


@dataclass
class DetectedPattern:
    """A pattern detected in the user's workflow."""
    pattern_type: str
    description: str
    apps_involved: list[str]
    occurrence_count: int
    automation_potential: str  # "none", "low", "medium", "high"
    automation_idea: str | None


class PatternTracker:
    """Analyzes activity history to detect repetitive workflow patterns.

    Tracks sequences of activities across applications to identify:
    - Copy-paste workflows between apps (data entry from one source to another)
    - Repetitive navigation patterns
    - Manual processes that could be automated
    - Time spent on different activity types
    """

    # Minimum times a sequence must repeat to be flagged
    MIN_PATTERN_OCCURRENCES = 3

    def __init__(self, store: PatternStore):
        self._store = store
        # Track recent app transitions as a sliding window
        self._recent_transitions: list[tuple[str, str]] = []
        self._activity_sequence: list[Activity] = []
        self._app_switch_counts: dict[tuple[str, str], int] = defaultdict(int)

    def record_activity(self, activity: Activity) -> list[DetectedPattern]:
        """Record an activity and check for new patterns.

        Returns any newly detected patterns.
        """
        self._activity_sequence.append(activity)

        # Keep a manageable window
        if len(self._activity_sequence) > 500:
            self._activity_sequence = self._activity_sequence[-250:]

        # Record in persistent store
        self._store.record_activity(
            app_name=activity.app_context.app_name,
            app_category=activity.app_context.category.value,
            activity_type=activity.activity_type.value,
            description=activity.description,
        )

        # Detect patterns
        new_patterns = []

        # 1. App-switching patterns (e.g., constantly switching between Excel and browser)
        app_pattern = self._detect_app_switching_pattern(activity)
        if app_pattern:
            new_patterns.append(app_pattern)

        # 2. Data transfer patterns (copy from one app, paste in another)
        transfer_pattern = self._detect_data_transfer_pattern()
        if transfer_pattern:
            new_patterns.append(transfer_pattern)

        # 3. Repetitive task sequences
        sequence_pattern = self._detect_repetitive_sequence()
        if sequence_pattern:
            new_patterns.append(sequence_pattern)

        return new_patterns

    def _detect_app_switching_pattern(self, activity: Activity) -> DetectedPattern | None:
        """Detect frequent switching between specific apps."""
        if len(self._activity_sequence) < 2:
            return None

        prev = self._activity_sequence[-2]
        current = activity

        if prev.app_context.app_name != current.app_context.app_name:
            pair = (prev.app_context.app_name, current.app_context.app_name)
            self._app_switch_counts[pair] += 1

            count = self._app_switch_counts[pair]
            if count == self.MIN_PATTERN_OCCURRENCES:
                pattern = DetectedPattern(
                    pattern_type="frequent_app_switch",
                    description=(
                        f"Frequently switching between {pair[0]} and {pair[1]}. "
                        f"This may indicate a manual data transfer workflow."
                    ),
                    apps_involved=list(pair),
                    occurrence_count=count,
                    automation_potential="medium",
                    automation_idea=(
                        f"Consider using an integration or script to connect "
                        f"{pair[0]} and {pair[1]} directly, eliminating manual switching."
                    ),
                )
                self._store.record_pattern(
                    pattern_type=pattern.pattern_type,
                    description=pattern.description,
                    apps_involved=pattern.apps_involved,
                    automation_potential=pattern.automation_potential,
                    automation_description=pattern.automation_idea,
                )
                return pattern
        return None

    def _detect_data_transfer_pattern(self) -> DetectedPattern | None:
        """Detect manual data entry patterns (reading from one app, typing in another)."""
        if len(self._activity_sequence) < 4:
            return None

        recent = self._activity_sequence[-4:]
        # Look for: read in App A -> switch -> type in App B -> switch back to App A
        apps = [a.app_context.app_name for a in recent]
        types = [a.activity_type for a in recent]

        if (
            len(set(apps)) == 2
            and apps[0] == apps[2]
            and apps[1] == apps[3]
            and ActivityType.DATA_ENTRY in types
        ):
            return DetectedPattern(
                pattern_type="manual_data_transfer",
                description=(
                    f"Manual data transfer detected: reading from {apps[0]} "
                    f"and entering data in {apps[1]}."
                ),
                apps_involved=list(set(apps)),
                occurrence_count=1,
                automation_potential="high",
                automation_idea=(
                    f"This copy-paste workflow between {apps[0]} and {apps[1]} "
                    f"could be automated with a data pipeline, API integration, "
                    f"or a simple script."
                ),
            )
        return None

    def _detect_repetitive_sequence(self) -> DetectedPattern | None:
        """Detect repeated sequences of activities."""
        if len(self._activity_sequence) < 6:
            return None

        # Check for 3-step repeating sequences in the last 12 activities
        recent = self._activity_sequence[-12:]
        for seq_len in (3, 4):
            if len(recent) < seq_len * 2:
                continue

            # Extract sequences of (app, activity_type) tuples
            seq = [(a.app_context.app_name, a.activity_type.value) for a in recent]

            for start in range(len(seq) - seq_len * 2 + 1):
                pattern_seq = seq[start : start + seq_len]
                match_count = 0
                for check_start in range(start + seq_len, len(seq) - seq_len + 1):
                    if seq[check_start : check_start + seq_len] == pattern_seq:
                        match_count += 1

                if match_count >= 2:
                    apps = list(set(s[0] for s in pattern_seq))
                    return DetectedPattern(
                        pattern_type="repetitive_sequence",
                        description=(
                            f"Repetitive {seq_len}-step workflow detected involving "
                            f"{', '.join(apps)}. This sequence has repeated {match_count + 1} times."
                        ),
                        apps_involved=apps,
                        occurrence_count=match_count + 1,
                        automation_potential="high",
                        automation_idea=(
                            f"This {seq_len}-step repeating workflow could be automated "
                            f"with a macro or script."
                        ),
                    )
        return None

    def get_optimization_report(self) -> dict:
        """Generate a summary report of detected patterns and suggestions."""
        frequent_patterns = self._store.get_frequent_patterns()
        activity_summary = self._store.get_activity_summary()

        high_value = [p for p in frequent_patterns if p["automation_potential"] in ("high", "medium")]

        return {
            "total_observations": activity_summary.get("total_observations", 0),
            "activity_breakdown": activity_summary.get("by_category", []),
            "patterns_detected": len(frequent_patterns),
            "high_value_automations": len(high_value),
            "patterns": frequent_patterns,
            "top_recommendations": [
                {
                    "description": p["description"],
                    "potential": p["automation_potential"],
                    "suggestion": p["automation_description"],
                    "occurrences": p["occurrence_count"],
                }
                for p in high_value[:5]
            ],
        }
