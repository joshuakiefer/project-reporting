"""Automatic redaction of sensitive data from captured screenshots."""

import re
from dataclasses import dataclass


@dataclass
class RedactionMatch:
    """A region of text identified as sensitive."""
    pattern_name: str
    matched_text: str
    start: int
    end: int


class SensitiveDataRedactor:
    """Detects and redacts sensitive information from OCR'd text and metadata.

    Before any captured text is sent to the Claude API or stored, this module
    scans for patterns like credit card numbers, SSNs, API keys, and passwords,
    replacing them with redaction placeholders.
    """

    # Patterns that indicate sensitive data in extracted text
    PATTERNS: dict[str, re.Pattern] = {
        "credit_card": re.compile(
            r"\b(?:\d[ -]*?){13,19}\b"
        ),
        "ssn": re.compile(
            r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"
        ),
        "api_key": re.compile(
            r"\b(?:sk|pk|api|key|token|secret)[-_]?[A-Za-z0-9]{20,}\b",
            re.IGNORECASE,
        ),
        "email": re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        ),
        "password_field": re.compile(
            r"(?:password|passwd|pwd)\s*[:=]\s*\S+",
            re.IGNORECASE,
        ),
        "ip_address": re.compile(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
        ),
    }

    REDACTION_PLACEHOLDER = "[REDACTED]"

    def __init__(self, extra_patterns: dict[str, str] | None = None):
        self._patterns = dict(self.PATTERNS)
        if extra_patterns:
            for name, pat in extra_patterns.items():
                self._patterns[name] = re.compile(pat)

    def scan(self, text: str) -> list[RedactionMatch]:
        """Scan text and return all sensitive matches found."""
        matches = []
        for name, pattern in self._patterns.items():
            for m in pattern.finditer(text):
                matches.append(
                    RedactionMatch(
                        pattern_name=name,
                        matched_text=m.group(),
                        start=m.start(),
                        end=m.end(),
                    )
                )
        return matches

    def redact(self, text: str) -> str:
        """Return text with all sensitive data replaced by placeholders."""
        matches = sorted(self.scan(text), key=lambda m: m.start, reverse=True)
        result = text
        for match in matches:
            result = (
                result[: match.start]
                + self.REDACTION_PLACEHOLDER
                + result[match.end :]
            )
        return result

    def has_sensitive_data(self, text: str) -> bool:
        """Quick check if text contains any sensitive patterns."""
        return len(self.scan(text)) > 0
