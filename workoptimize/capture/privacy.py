"""Privacy filter applied to captures before analysis or storage."""

import hashlib
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PrivacyRule:
    """A rule that determines whether a capture should be blocked or modified."""
    name: str
    rule_type: str  # "block_app", "block_url", "block_title"
    pattern: str  # Case-insensitive substring match


class PrivacyFilter:
    """Applies privacy rules to determine if a capture should proceed.

    This is the first gate — before any screenshot is analyzed or stored,
    the privacy filter checks whether the active context matches any
    exclusion rules.
    """

    # Default rules to protect obviously sensitive contexts
    DEFAULT_RULES = [
        PrivacyRule("password_managers", "block_app", "1password"),
        PrivacyRule("password_managers", "block_app", "lastpass"),
        PrivacyRule("password_managers", "block_app", "bitwarden"),
        PrivacyRule("password_managers", "block_app", "keepass"),
        PrivacyRule("banking_urls", "block_title", "bank"),
        PrivacyRule("banking_urls", "block_title", "banking"),
        PrivacyRule("auth_screens", "block_title", "sign in"),
        PrivacyRule("auth_screens", "block_title", "log in"),
        PrivacyRule("auth_screens", "block_title", "password"),
        PrivacyRule("private_browsing", "block_title", "incognito"),
        PrivacyRule("private_browsing", "block_title", "private browsing"),
    ]

    def __init__(self, custom_rules: list[PrivacyRule] | None = None):
        self._rules = list(self.DEFAULT_RULES)
        if custom_rules:
            self._rules.extend(custom_rules)

    def should_capture(self, app_name: str, window_title: str) -> bool:
        """Returns True if the current context is safe to capture."""
        app_lower = app_name.lower()
        title_lower = window_title.lower()

        for rule in self._rules:
            pattern = rule.pattern.lower()
            if rule.rule_type == "block_app" and pattern in app_lower:
                logger.info("Privacy filter blocked capture — rule: %s", rule.name)
                return False
            if rule.rule_type == "block_title" and pattern in title_lower:
                logger.info("Privacy filter blocked capture — rule: %s", rule.name)
                return False

        return True

    def add_rule(self, rule: PrivacyRule) -> None:
        """Add a custom privacy rule."""
        self._rules.append(rule)

    def remove_rule(self, name: str) -> None:
        """Remove all rules with the given name."""
        self._rules = [r for r in self._rules if r.name != name]

    @property
    def rules(self) -> list[PrivacyRule]:
        return list(self._rules)
