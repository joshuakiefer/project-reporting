"""Classifies user activities into work categories for pattern tracking."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from workoptimize.context.detector import AppContext, AppCategory

logger = logging.getLogger(__name__)


class ActivityType(Enum):
    """Types of work activities detected."""
    DATA_ENTRY = "data_entry"
    DATA_ANALYSIS = "data_analysis"
    WRITING = "writing"
    COMMUNICATION = "communication"
    RESEARCH = "research"
    DESIGN = "design"
    CODING = "coding"
    ADMINISTRATION = "administration"
    FILE_MANAGEMENT = "file_management"
    UNKNOWN = "unknown"


@dataclass
class Activity:
    """A classified work activity."""
    activity_type: ActivityType
    app_context: AppContext
    description: str
    timestamp: datetime
    confidence: float  # 0.0 to 1.0


# Map app categories to likely activity types
CATEGORY_ACTIVITY_MAP: dict[AppCategory, ActivityType] = {
    AppCategory.SPREADSHEET: ActivityType.DATA_ANALYSIS,
    AppCategory.WORD_PROCESSOR: ActivityType.WRITING,
    AppCategory.PRESENTATION: ActivityType.DESIGN,
    AppCategory.BROWSER: ActivityType.RESEARCH,
    AppCategory.EMAIL: ActivityType.COMMUNICATION,
    AppCategory.ACCOUNTING: ActivityType.ADMINISTRATION,
    AppCategory.IDE: ActivityType.CODING,
    AppCategory.TERMINAL: ActivityType.CODING,
    AppCategory.FILE_MANAGER: ActivityType.FILE_MANAGEMENT,
    AppCategory.COMMUNICATION: ActivityType.COMMUNICATION,
}


class ActivityClassifier:
    """Classifies what the user is doing based on app context and analysis results.

    Uses a combination of rule-based classification (from app detection)
    and AI-enhanced classification (from Claude analysis results).
    """

    def classify_from_context(self, app_context: AppContext) -> Activity:
        """Quick classification based on app context alone (no API call)."""
        activity_type = CATEGORY_ACTIVITY_MAP.get(
            app_context.category, ActivityType.UNKNOWN
        )

        description = f"Working in {app_context.app_name}"
        if app_context.document_name:
            description += f" on {app_context.document_name}"

        return Activity(
            activity_type=activity_type,
            app_context=app_context,
            description=description,
            timestamp=datetime.now(timezone.utc),
            confidence=0.6,  # Rule-based = moderate confidence
        )

    def classify_from_analysis(
        self, app_context: AppContext, analysis_text: str
    ) -> Activity:
        """Enhanced classification using Claude's analysis of the screenshot."""
        # Start with rule-based type
        activity_type = CATEGORY_ACTIVITY_MAP.get(
            app_context.category, ActivityType.UNKNOWN
        )

        # Refine based on analysis keywords
        analysis_lower = analysis_text.lower()

        if any(kw in analysis_lower for kw in ("typing", "entering data", "filling", "form")):
            activity_type = ActivityType.DATA_ENTRY
        elif any(kw in analysis_lower for kw in ("chart", "pivot", "formula", "calculating")):
            activity_type = ActivityType.DATA_ANALYSIS
        elif any(kw in analysis_lower for kw in ("searching", "browsing", "reading article", "researching")):
            activity_type = ActivityType.RESEARCH
        elif any(kw in analysis_lower for kw in ("email", "message", "chat", "replying")):
            activity_type = ActivityType.COMMUNICATION

        # Use the analysis text as a richer description
        description = analysis_text[:200] if len(analysis_text) > 200 else analysis_text

        return Activity(
            activity_type=activity_type,
            app_context=app_context,
            description=description,
            timestamp=datetime.now(timezone.utc),
            confidence=0.85,  # AI-enhanced = higher confidence
        )
