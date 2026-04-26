import logging
import traceback
from dataclasses import dataclass, field
from typing import Optional

from .. import config
from ..core import catalog
from . import tools
from .llm_client import LLMClient
from .tools import ReasoningStep, ScoredSong

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    recommendations: list        # List[ScoredSong]
    response_text: str
    confidence: dict
    reasoning_steps: list        # List[ReasoningStep]
    preferences_extracted: dict
    error: Optional[str] = None


class AgentOrchestrator:
    def __init__(self) -> None:
        config.setup_logging()
        self.llm = LLMClient()
        try:
            catalog.load_catalog()
        except Exception as exc:
            logger.error("Failed to load catalog on startup: %s", exc)
            raise
        logger.info("TuneFit 2.0 agent initialized")

    def run(self, user_message: str) -> AgentResult:
        stripped = user_message.strip()
        if len(stripped) < 3 or not any(c.isalpha() for c in stripped):
            return AgentResult(
                recommendations=[],
                response_text="",
                confidence={},
                reasoning_steps=[],
                preferences_extracted={},
                error="Please describe what kind of music you're looking for.",
            )

        steps: list = []
        try:
            preferences = tools.extract_preferences(user_message, self.llm, steps)
            scored = tools.score_and_retrieve(preferences, steps)
            confidence = tools.evaluate_confidence(scored, preferences, steps)
            response = tools.format_response(scored, confidence, preferences, self.llm, steps)
        except Exception:
            logger.error("Agent run failed:\n%s", traceback.format_exc())
            return AgentResult(
                recommendations=[],
                response_text="",
                confidence={},
                reasoning_steps=steps,
                preferences_extracted={},
                error="Something went wrong. Please try again.",
            )

        return AgentResult(
            recommendations=scored,
            response_text=response,
            confidence=confidence,
            reasoning_steps=steps,
            preferences_extracted=preferences,
        )


if __name__ == "__main__":
    agent = AgentOrchestrator()
    result = agent.run("play me something chill for studying")
    print(result.response_text)
    for step in result.reasoning_steps:
        print(f"[{step.tool_name}] {step.output_summary}")
