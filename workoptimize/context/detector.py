"""Detects what application and context the user is working in."""

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AppCategory(Enum):
    """High-level categories of applications."""
    SPREADSHEET = "spreadsheet"
    WORD_PROCESSOR = "word_processor"
    PRESENTATION = "presentation"
    BROWSER = "browser"
    EMAIL = "email"
    ACCOUNTING = "accounting"
    IDE = "ide"
    TERMINAL = "terminal"
    FILE_MANAGER = "file_manager"
    COMMUNICATION = "communication"
    OTHER = "other"


@dataclass
class AppContext:
    """Detected application context."""
    app_name: str
    window_title: str
    category: AppCategory
    document_name: str | None = None
    url: str | None = None


# Maps known app names/patterns to categories
APP_SIGNATURES: dict[str, AppCategory] = {
    "excel": AppCategory.SPREADSHEET,
    "sheets": AppCategory.SPREADSHEET,
    "libreoffice calc": AppCategory.SPREADSHEET,
    "numbers": AppCategory.SPREADSHEET,
    "word": AppCategory.WORD_PROCESSOR,
    "docs": AppCategory.WORD_PROCESSOR,
    "libreoffice writer": AppCategory.WORD_PROCESSOR,
    "pages": AppCategory.WORD_PROCESSOR,
    "powerpoint": AppCategory.PRESENTATION,
    "slides": AppCategory.PRESENTATION,
    "libreoffice impress": AppCategory.PRESENTATION,
    "keynote": AppCategory.PRESENTATION,
    "chrome": AppCategory.BROWSER,
    "firefox": AppCategory.BROWSER,
    "safari": AppCategory.BROWSER,
    "edge": AppCategory.BROWSER,
    "brave": AppCategory.BROWSER,
    "outlook": AppCategory.EMAIL,
    "thunderbird": AppCategory.EMAIL,
    "mail": AppCategory.EMAIL,
    "quickbooks": AppCategory.ACCOUNTING,
    "xero": AppCategory.ACCOUNTING,
    "freshbooks": AppCategory.ACCOUNTING,
    "vscode": AppCategory.IDE,
    "code": AppCategory.IDE,
    "intellij": AppCategory.IDE,
    "pycharm": AppCategory.IDE,
    "terminal": AppCategory.TERMINAL,
    "iterm": AppCategory.TERMINAL,
    "cmd": AppCategory.TERMINAL,
    "powershell": AppCategory.TERMINAL,
    "slack": AppCategory.COMMUNICATION,
    "teams": AppCategory.COMMUNICATION,
    "zoom": AppCategory.COMMUNICATION,
    "discord": AppCategory.COMMUNICATION,
}


class AppDetector:
    """Classifies the active application and extracts context from window titles."""

    def detect(self, app_name: str, window_title: str) -> AppContext:
        """Detect app category and extract context from available info."""
        category = self._classify_app(app_name, window_title)
        document_name = self._extract_document_name(window_title, category)
        url = self._extract_url(window_title) if category == AppCategory.BROWSER else None

        return AppContext(
            app_name=app_name,
            window_title=window_title,
            category=category,
            document_name=document_name,
            url=url,
        )

    def _classify_app(self, app_name: str, window_title: str) -> AppCategory:
        """Match app name or title against known signatures."""
        combined = f"{app_name} {window_title}".lower()

        for signature, category in APP_SIGNATURES.items():
            if signature in combined:
                return category

        return AppCategory.OTHER

    def _extract_document_name(self, title: str, category: AppCategory) -> str | None:
        """Try to extract the document/file name from the window title."""
        if category in (
            AppCategory.SPREADSHEET,
            AppCategory.WORD_PROCESSOR,
            AppCategory.PRESENTATION,
        ):
            # Common patterns: "Document.docx - Microsoft Word"
            # or "Microsoft Excel - Book1.xlsx"
            parts = re.split(r"\s*[-–—]\s*", title)
            for part in parts:
                part = part.strip()
                if re.search(r"\.\w{2,5}$", part):
                    return part
            # Return first part as fallback
            if parts:
                return parts[0].strip()
        return None

    def _extract_url(self, title: str) -> str | None:
        """Try to extract URL from browser window title (best effort)."""
        # Some browsers show the URL in the title
        url_match = re.search(r"https?://\S+", title)
        if url_match:
            return url_match.group()
        return None
