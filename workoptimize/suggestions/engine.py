"""Suggestion engine that generates and manages optimization recommendations."""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from workoptimize.analysis.vision import AnalysisResult
from workoptimize.context.classifier import Activity, ActivityType

logger = logging.getLogger(__name__)


class SuggestionPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SuggestionCategory(Enum):
    KEYBOARD_SHORTCUT = "keyboard_shortcut"
    FEATURE_TIP = "feature_tip"
    AUTOMATION_OPPORTUNITY = "automation_opportunity"
    PROCESS_IMPROVEMENT = "process_improvement"
    TOOL_RECOMMENDATION = "tool_recommendation"
    DATA_ORGANIZATION = "data_organization"
    GENERAL_TIP = "general_tip"


@dataclass
class Suggestion:
    """A single optimization suggestion."""
    suggestion_id: str
    title: str
    description: str
    category: SuggestionCategory
    priority: SuggestionPriority
    source_capture_id: str
    activity_type: ActivityType
    timestamp: datetime
    dismissed: bool = False
    implemented: bool = False
    time_savings_estimate: str | None = None  # e.g., "~5 min/day"


@dataclass
class SuggestionBatch:
    """A group of suggestions generated from a single analysis."""
    suggestions: list[Suggestion]
    analysis_summary: str
    generated_at: datetime


class SuggestionEngine:
    """Generates, prioritizes, and manages optimization suggestions.

    Takes analysis results and activities, generates suggestions,
    deduplicates against previous suggestions, and ranks by priority.
    """

    def __init__(self, max_active_suggestions: int = 10):
        self._max_active = max_active_suggestions
        self._suggestion_history: list[Suggestion] = []
        self._dismissed_titles: set[str] = set()
        self._counter = 0

    def generate_suggestions(
        self,
        analysis: AnalysisResult,
        activity: Activity,
    ) -> SuggestionBatch:
        """Parse analysis results and generate structured suggestions."""
        suggestions = []
        text = analysis.response_text

        # Parse suggestions from the analysis text
        lines = text.split("\n")
        current_section = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect section headers
            if line.startswith("**") and line.endswith("**"):
                current_section = line.strip("* ").lower()
                continue

            # Extract actionable items (lines starting with - or numbered)
            if line.startswith(("-", "•")) or (len(line) > 2 and line[0].isdigit() and line[1] in ".)"):
                suggestion_text = line.lstrip("-•0123456789.) ").strip()
                if not suggestion_text or len(suggestion_text) < 10:
                    continue

                category = self._classify_suggestion(suggestion_text, current_section)
                priority = self._assess_priority(suggestion_text, activity)

                # Skip if we've already suggested something very similar
                if self._is_duplicate(suggestion_text):
                    continue

                self._counter += 1
                suggestion = Suggestion(
                    suggestion_id=f"sug-{self._counter:06d}",
                    title=suggestion_text[:80],
                    description=suggestion_text,
                    category=category,
                    priority=priority,
                    source_capture_id=analysis.capture_id,
                    activity_type=activity.activity_type,
                    timestamp=datetime.now(timezone.utc),
                    time_savings_estimate=self._estimate_time_savings(category),
                )
                suggestions.append(suggestion)

        # Sort by priority
        priority_order = {
            SuggestionPriority.CRITICAL: 0,
            SuggestionPriority.HIGH: 1,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 3,
        }
        suggestions.sort(key=lambda s: priority_order[s.priority])

        # Limit active suggestions
        suggestions = suggestions[: self._max_active]
        self._suggestion_history.extend(suggestions)

        return SuggestionBatch(
            suggestions=suggestions,
            analysis_summary=text[:300],
            generated_at=datetime.now(timezone.utc),
        )

    def dismiss_suggestion(self, suggestion_id: str) -> None:
        """Mark a suggestion as dismissed (won't show similar ones)."""
        for s in self._suggestion_history:
            if s.suggestion_id == suggestion_id:
                s.dismissed = True
                self._dismissed_titles.add(s.title.lower())
                break

    def mark_implemented(self, suggestion_id: str) -> None:
        """Mark a suggestion as implemented by the user."""
        for s in self._suggestion_history:
            if s.suggestion_id == suggestion_id:
                s.implemented = True
                break

    def get_active_suggestions(self) -> list[Suggestion]:
        """Return current non-dismissed suggestions."""
        return [
            s for s in self._suggestion_history
            if not s.dismissed and not s.implemented
        ][-self._max_active:]

    def _classify_suggestion(self, text: str, section: str) -> SuggestionCategory:
        """Classify a suggestion into a category."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ("ctrl+", "cmd+", "shortcut", "alt+")):
            return SuggestionCategory.KEYBOARD_SHORTCUT
        if any(kw in text_lower for kw in ("automat", "script", "macro", "bot")):
            return SuggestionCategory.AUTOMATION_OPPORTUNITY
        if any(kw in text_lower for kw in ("tool", "extension", "plugin", "app")):
            return SuggestionCategory.TOOL_RECOMMENDATION
        if any(kw in text_lower for kw in ("organiz", "structur", "format", "layout")):
            return SuggestionCategory.DATA_ORGANIZATION
        if "process" in section or "workflow" in section:
            return SuggestionCategory.PROCESS_IMPROVEMENT
        if "feature" in section or "tip" in section:
            return SuggestionCategory.FEATURE_TIP
        return SuggestionCategory.GENERAL_TIP

    def _assess_priority(self, text: str, activity: Activity) -> SuggestionPriority:
        """Assess priority of a suggestion."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ("automat", "save hours", "significant")):
            return SuggestionPriority.HIGH
        if any(kw in text_lower for kw in ("repetitive", "manual", "tedious")):
            return SuggestionPriority.HIGH
        if any(kw in text_lower for kw in ("could", "consider", "might")):
            return SuggestionPriority.LOW
        return SuggestionPriority.MEDIUM

    def _is_duplicate(self, text: str) -> bool:
        """Check if a similar suggestion was already generated."""
        text_lower = text.lower()
        if text_lower in self._dismissed_titles:
            return True
        for existing in self._suggestion_history[-50:]:
            if text_lower == existing.title.lower():
                return True
        return False

    def _estimate_time_savings(self, category: SuggestionCategory) -> str | None:
        """Rough time savings estimate based on category."""
        estimates = {
            SuggestionCategory.AUTOMATION_OPPORTUNITY: "~15-30 min/day",
            SuggestionCategory.KEYBOARD_SHORTCUT: "~5 min/day",
            SuggestionCategory.PROCESS_IMPROVEMENT: "~10-20 min/day",
            SuggestionCategory.TOOL_RECOMMENDATION: "~10 min/day",
            SuggestionCategory.DATA_ORGANIZATION: "~5-10 min/day",
        }
        return estimates.get(category)
