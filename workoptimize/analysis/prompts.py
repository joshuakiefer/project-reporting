"""Prompt templates for Claude API screen analysis."""


class PromptLibrary:
    """Centralized prompt templates for different analysis scenarios.

    Each prompt is designed to extract specific information from a screenshot
    while being mindful of token usage and response quality.
    """

    SYSTEM_PROMPT = """You are WorkOptimize AI, a work efficiency assistant. You analyze screenshots of a user's desktop to understand what they're doing and provide helpful optimization suggestions.

Rules:
- Be concise and actionable in your responses
- Focus on practical improvements, not theoretical ones
- If you see sensitive data (passwords, financial info, personal data), DO NOT mention or repeat it — just note that sensitive content is present
- Prioritize suggestions that save the most time
- Be specific to the application and task you observe"""

    QUICK_ANALYSIS = """Analyze this screenshot and provide:

1. **Active Application**: What app is the user working in?
2. **Current Task**: What specific task are they performing?
3. **Quick Tip**: One immediate suggestion to help with what they're doing right now.

Keep your response under 100 words. Be direct and helpful."""

    DEEP_ANALYSIS = """Analyze this screenshot thoroughly:

1. **Application**: What application is being used?
2. **Task Description**: What is the user doing? Be specific.
3. **Efficiency Assessment**: Rate the current approach (1-5 stars).
4. **Suggestions**: List 1-3 specific improvements, keyboard shortcuts, or better approaches.
5. **Automation Potential**: Could any part of what you see be automated? If yes, describe how.

Focus on actionable, practical advice specific to what you observe."""

    EXCEL_ANALYSIS = """You're looking at a spreadsheet. Analyze it and provide:

1. **What's Being Done**: Describe the spreadsheet work happening.
2. **Formula Suggestions**: Any formulas that could replace manual work?
3. **Data Organization**: Could the data be structured better?
4. **Automation Ideas**: Could macros, pivot tables, or Power Query help?
5. **Specific Tip**: One concrete improvement they can make right now.

Be specific — reference cell ranges, column names, or visible data patterns."""

    WORD_ANALYSIS = """You're looking at a word processing document. Analyze it and provide:

1. **Document Type**: What kind of document is being written?
2. **Writing Suggestions**: Any improvements to clarity, structure, or formatting?
3. **Tool Tips**: Are there Word/Docs features that could help (styles, templates, etc.)?
4. **Efficiency Tips**: Keyboard shortcuts or features to speed up their work.

Be brief and practical."""

    POWERPOINT_ANALYSIS = """You're looking at a presentation. Analyze it and provide:

1. **Slide Assessment**: What's on the current slide?
2. **Design Suggestions**: Any improvements to layout, readability, or visual impact?
3. **Content Tips**: Could the messaging be more concise or impactful?
4. **Tool Tips**: PowerPoint features that could help (SmartArt, animations, templates).

Keep suggestions visual and actionable."""

    BROWSER_ANALYSIS = """You're looking at a web browser. Analyze it and provide:

1. **What They're Doing**: Browsing, researching, filling forms, etc.?
2. **Search Tips**: If searching, could they refine their query?
3. **Tool Suggestions**: Browser extensions or shortcuts that could help?
4. **Efficiency Note**: Any faster way to accomplish what they're doing?

Be concise — one or two key tips maximum."""

    WORKFLOW_PATTERN_ANALYSIS = """You are reviewing a series of screenshots taken over time to identify workflow patterns.

Previous context: {previous_context}

Current screenshot analysis needed:
1. **Continuity**: Is this part of the same task as before, or a new task?
2. **Pattern Detection**: Are you seeing repetitive actions (copy-paste between apps, manual data entry, repeated navigation)?
3. **Time Sink**: Does this step seem like it takes longer than necessary?
4. **Automation Flag**: Could this step be automated or streamlined?

Respond in JSON format:
{{
    "same_task": true/false,
    "task_category": "string",
    "repetitive_pattern": true/false,
    "pattern_description": "string or null",
    "automation_potential": "none|low|medium|high",
    "automation_idea": "string or null",
    "time_efficiency": 1-5,
    "suggestion": "string"
}}"""

    @classmethod
    def get_prompt_for_app(cls, app_name: str) -> str:
        """Select the best analysis prompt based on the active application."""
        app_lower = app_name.lower()

        if any(kw in app_lower for kw in ("excel", "sheets", "calc", "numbers")):
            return cls.EXCEL_ANALYSIS
        if any(kw in app_lower for kw in ("word", "docs", "writer", "pages")):
            return cls.WORD_ANALYSIS
        if any(kw in app_lower for kw in ("powerpoint", "slides", "impress", "keynote")):
            return cls.POWERPOINT_ANALYSIS
        if any(kw in app_lower for kw in ("chrome", "firefox", "safari", "edge", "brave", "browser")):
            return cls.BROWSER_ANALYSIS

        return cls.DEEP_ANALYSIS
