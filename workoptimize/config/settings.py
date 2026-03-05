"""Configuration management for WorkOptimize AI."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class CaptureSettings:
    interval_seconds: float = 5.0
    excluded_apps: list[str] = field(default_factory=list)
    excluded_urls: list[str] = field(default_factory=list)
    excluded_window_titles: list[str] = field(default_factory=list)
    blur_sensitive: bool = True


@dataclass
class AnalysisSettings:
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024
    analysis_mode: str = "auto"  # "auto", "quick", "deep"
    enable_workflow_tracking: bool = True


@dataclass
class SecuritySettings:
    encrypt_at_rest: bool = True
    retention_days: int = 30
    audit_logging: bool = True
    redact_sensitive: bool = True
    extra_redaction_patterns: dict[str, str] = field(default_factory=dict)


@dataclass
class UISettings:
    overlay_position: str = "bottom-right"
    theme: str = "dark"
    opacity: float = 0.92
    width: int = 380
    show_on_startup: bool = True


@dataclass
class Settings:
    """Top-level application settings."""
    capture: CaptureSettings = field(default_factory=CaptureSettings)
    analysis: AnalysisSettings = field(default_factory=AnalysisSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    ui: UISettings = field(default_factory=UISettings)
    data_dir: Path = field(default_factory=lambda: Path.home() / ".workoptimize")
    api_key: str = ""

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Settings":
        """Load settings from YAML file, falling back to defaults."""
        settings = cls()

        # Check for API key in environment
        settings.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if config_path is None:
            config_path = Path("config.yaml")

        if not config_path.exists():
            # Also check user home directory
            home_config = Path.home() / ".workoptimize" / "config.yaml"
            if home_config.exists():
                config_path = home_config
            else:
                return settings

        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        if "capture" in data:
            for key, val in data["capture"].items():
                if hasattr(settings.capture, key):
                    setattr(settings.capture, key, val)

        if "analysis" in data:
            for key, val in data["analysis"].items():
                if hasattr(settings.analysis, key):
                    setattr(settings.analysis, key, val)

        if "security" in data:
            for key, val in data["security"].items():
                if hasattr(settings.security, key):
                    setattr(settings.security, key, val)

        if "ui" in data:
            for key, val in data["ui"].items():
                if hasattr(settings.ui, key):
                    setattr(settings.ui, key, val)

        if "data_dir" in data:
            settings.data_dir = Path(data["data_dir"])

        if "api_key" in data and not settings.api_key:
            settings.api_key = data["api_key"]

        return settings

    def save(self, config_path: Path) -> None:
        """Save current settings to YAML file."""
        data = {
            "capture": {
                "interval_seconds": self.capture.interval_seconds,
                "excluded_apps": self.capture.excluded_apps,
                "excluded_urls": self.capture.excluded_urls,
                "excluded_window_titles": self.capture.excluded_window_titles,
                "blur_sensitive": self.capture.blur_sensitive,
            },
            "analysis": {
                "model": self.analysis.model,
                "max_tokens": self.analysis.max_tokens,
                "analysis_mode": self.analysis.analysis_mode,
                "enable_workflow_tracking": self.analysis.enable_workflow_tracking,
            },
            "security": {
                "encrypt_at_rest": self.security.encrypt_at_rest,
                "retention_days": self.security.retention_days,
                "audit_logging": self.security.audit_logging,
                "redact_sensitive": self.security.redact_sensitive,
            },
            "ui": {
                "overlay_position": self.ui.overlay_position,
                "theme": self.ui.theme,
                "opacity": self.ui.opacity,
                "width": self.ui.width,
                "show_on_startup": self.ui.show_on_startup,
            },
            "data_dir": str(self.data_dir),
        }

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
