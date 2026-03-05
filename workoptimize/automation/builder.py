"""Automation builder that helps users create scripts from detected patterns."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import anthropic

from workoptimize.analysis.prompts import PromptLibrary
from workoptimize.patterns.tracker import DetectedPattern

logger = logging.getLogger(__name__)


@dataclass
class AutomationBlueprint:
    """A generated automation plan with implementation code."""
    pattern_description: str
    automation_type: str  # "python_script", "excel_macro", "power_automate", "shell_script"
    title: str
    description: str
    implementation_code: str
    setup_instructions: str
    estimated_time_saved: str
    created_at: datetime


class AutomationBuilder:
    """Uses Claude to generate automation scripts from detected patterns.

    When the pattern tracker identifies a repetitive workflow, this module
    can generate actual implementation code to automate it.
    """

    AUTOMATION_PROMPT = """You are an automation expert. A user has a repetitive workflow pattern that needs to be automated.

Pattern detected: {pattern_description}
Apps involved: {apps_involved}
Frequency: Observed {occurrence_count} times

Generate a practical automation solution:

1. **Automation Type**: What technology should be used? (Python script, Excel macro/VBA, PowerShell, Power Automate, shell script, etc.)
2. **Title**: Short name for this automation
3. **Description**: What the automation does in 2-3 sentences
4. **Implementation**: Working code that implements the automation. Include comments.
5. **Setup Instructions**: Step-by-step instructions the user needs to follow to set this up.
6. **Time Saved Estimate**: How much time this saves per day/week.

Provide complete, ready-to-use code. Prefer simple solutions over complex ones.
Format your response as:

AUTOMATION_TYPE: <type>
TITLE: <title>
DESCRIPTION: <description>

```<language>
<code>
```

SETUP:
<numbered steps>

TIME_SAVED: <estimate>"""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def build_automation(self, pattern: DetectedPattern) -> AutomationBlueprint:
        """Generate an automation blueprint from a detected pattern."""
        prompt = self.AUTOMATION_PROMPT.format(
            pattern_description=pattern.description,
            apps_involved=", ".join(pattern.apps_involved),
            occurrence_count=pattern.occurrence_count,
        )

        message = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system="You are a work automation expert. Generate practical, working automation solutions.",
            messages=[{"role": "user", "content": prompt}],
        )

        response = message.content[0].text
        parsed = self._parse_response(response, pattern)

        logger.info("Generated automation: %s", parsed.title)
        return parsed

    def _parse_response(self, response: str, pattern: DetectedPattern) -> AutomationBlueprint:
        """Parse Claude's response into a structured blueprint."""
        lines = response.split("\n")

        automation_type = "python_script"
        title = "Workflow Automation"
        description = ""
        code_lines: list[str] = []
        setup_lines: list[str] = []
        time_saved = "~10-15 min/day"
        in_code = False
        in_setup = False

        for line in lines:
            if line.startswith("AUTOMATION_TYPE:"):
                automation_type = line.split(":", 1)[1].strip().lower().replace(" ", "_")
            elif line.startswith("TITLE:"):
                title = line.split(":", 1)[1].strip()
            elif line.startswith("DESCRIPTION:"):
                description = line.split(":", 1)[1].strip()
            elif line.startswith("```") and not in_code:
                in_code = True
                in_setup = False
            elif line.startswith("```") and in_code:
                in_code = False
            elif in_code:
                code_lines.append(line)
            elif line.startswith("SETUP:"):
                in_setup = True
                in_code = False
            elif line.startswith("TIME_SAVED:"):
                time_saved = line.split(":", 1)[1].strip()
                in_setup = False
            elif in_setup and line.strip():
                setup_lines.append(line.strip())

        return AutomationBlueprint(
            pattern_description=pattern.description,
            automation_type=automation_type,
            title=title,
            description=description or pattern.description,
            implementation_code="\n".join(code_lines),
            setup_instructions="\n".join(setup_lines),
            estimated_time_saved=time_saved,
            created_at=datetime.now(timezone.utc),
        )
