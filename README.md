# WorkOptimize AI

A secure, AI-powered work optimization assistant that observes your screen activity and provides real-time suggestions, process improvement recommendations, and automation opportunities.

## Overview

WorkOptimize AI sits alongside you as you work — watching your screen (with your explicit consent), understanding context across any application, and providing intelligent suggestions to improve your efficiency. Over time, it identifies repetitive patterns and recommends automations.

## Key Features

- **Real-Time Screen Analysis** — Captures and analyzes your screen using Claude's vision capabilities
- **Cross-Application Context** — Works with Excel, Word, PowerPoint, QuickBooks, web browsers, and more
- **Intelligent Suggestions** — Provides contextual help, tips, and recommendations as you work
- **Workflow Pattern Detection** — Tracks repetitive tasks over days/weeks and identifies automation opportunities
- **Automation Builder** — Helps you build out automations for identified manual processes
- **Security-First Design** — All data encrypted at rest, local-only storage, no cloud sync without consent

## Architecture

```
workoptimize/
├── capture/          # Screen capture with security controls
├── analysis/         # Claude API integration for vision analysis
├── context/          # Application detection and activity classification
├── suggestions/      # Suggestion engine and optimization recommendations
├── patterns/         # Long-term workflow pattern tracking
├── automation/       # Automation builder for identified improvements
├── security/         # Encryption, privacy controls, data lifecycle
├── ui/               # Desktop overlay / popup interface
└── config/           # User preferences and configuration
```

## Security Model

- Screenshots are encrypted immediately after capture using AES-256
- All data stays local by default — nothing leaves your machine without explicit opt-in
- Configurable capture exclusion zones (e.g., password managers, banking sites)
- Automatic redaction of sensitive fields (credit cards, SSNs, passwords)
- Data retention policies with automatic cleanup
- Full audit log of what data was captured and when

## Requirements

- Python 3.10+
- Anthropic API key (Claude API with vision support)
- Platform: Windows, macOS, or Linux (with X11/Wayland)

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set your API key
export ANTHROPIC_API_KEY="your-key-here"

# Run the app
workoptimize
```

## Configuration

Copy `config.example.yaml` to `config.yaml` and customize:

```yaml
capture:
  interval_seconds: 5          # How often to capture screen
  excluded_apps: []             # Apps to never capture
  excluded_urls: []             # URLs to never capture
  blur_sensitive: true          # Auto-blur detected sensitive content

analysis:
  model: "claude-sonnet-4-20250514"
  max_tokens: 1024

security:
  encrypt_at_rest: true
  retention_days: 30
  audit_logging: true

ui:
  overlay_position: "bottom-right"
  theme: "auto"
```

## License

Proprietary — All rights reserved.
