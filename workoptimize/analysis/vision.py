"""Claude API integration for analyzing screenshots using vision capabilities."""

import json
import logging
import time
from dataclasses import dataclass

import anthropic

from workoptimize.analysis.prompts import PromptLibrary
from workoptimize.capture.screen import CaptureResult

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of analyzing a screenshot with Claude."""
    capture_id: str
    analysis_type: str
    response_text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    structured_data: dict | None = None


class VisionAnalyzer:
    """Sends screenshots to Claude's vision API for analysis.

    Uses appropriate prompts based on the detected application context.
    Implements rate limiting and cost tracking.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024,
    ):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def analyze(
        self,
        capture: CaptureResult,
        analysis_type: str = "auto",
        custom_prompt: str | None = None,
    ) -> AnalysisResult:
        """Analyze a screenshot using Claude's vision capabilities.

        Args:
            capture: The screen capture to analyze.
            analysis_type: "auto" selects prompt by app, or "quick", "deep", "workflow".
            custom_prompt: Override the prompt entirely.
        """
        if custom_prompt:
            user_prompt = custom_prompt
        elif analysis_type == "quick":
            user_prompt = PromptLibrary.QUICK_ANALYSIS
        elif analysis_type == "deep":
            user_prompt = PromptLibrary.DEEP_ANALYSIS
        elif analysis_type == "workflow":
            user_prompt = PromptLibrary.WORKFLOW_PATTERN_ANALYSIS
        else:
            user_prompt = PromptLibrary.get_prompt_for_app(capture.active_app)

        start_time = time.time()

        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=PromptLibrary.SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": capture.image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": user_prompt,
                        },
                    ],
                }
            ],
        )

        latency_ms = (time.time() - start_time) * 1000
        response_text = message.content[0].text

        self._total_input_tokens += message.usage.input_tokens
        self._total_output_tokens += message.usage.output_tokens

        # Try to parse structured data if the response looks like JSON
        structured = None
        if response_text.strip().startswith("{"):
            try:
                structured = json.loads(response_text)
            except json.JSONDecodeError:
                pass

        result = AnalysisResult(
            capture_id=capture.capture_id,
            analysis_type=analysis_type,
            response_text=response_text,
            model=self._model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            latency_ms=latency_ms,
            structured_data=structured,
        )

        logger.info(
            "Analysis complete: capture=%s model=%s tokens=%d+%d latency=%.0fms",
            capture.capture_id[:8],
            self._model,
            message.usage.input_tokens,
            message.usage.output_tokens,
            latency_ms,
        )

        return result

    def ask_about_screen(self, capture: CaptureResult, question: str) -> AnalysisResult:
        """Let the user ask a specific question about what's on screen."""
        prompt = f"""The user is asking about what they see on their screen.

Their question: {question}

Look at the screenshot and answer their question directly and helpfully. Be concise."""

        return self.analyze(capture, custom_prompt=prompt)

    @property
    def total_tokens_used(self) -> dict[str, int]:
        return {
            "input": self._total_input_tokens,
            "output": self._total_output_tokens,
            "total": self._total_input_tokens + self._total_output_tokens,
        }
