"""Structured Output Enforcement — result.output is always the typed object.

Demonstrates:
- Output(MyModel): agent always returns typed Pydantic instance
- result.output vs result.content: typed object vs raw string
- validation_retries: retry if LLM returns malformed JSON
- OutputValidationError: raised when all retries exhausted
- Hook.OUTPUT_VALIDATION_RETRY: observe retry attempts
- Strict field validation: wrong types are caught before reaching your code

Run:
    python examples/02_tasks/structured_output_enforcement.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pydantic import BaseModel, Field, field_validator  # noqa: E402

from syrin import Agent, Model, Output  # noqa: E402
from syrin.enums import Hook  # noqa: E402
from syrin.exceptions import OutputValidationError  # noqa: E402

# ---------------------------------------------------------------------------
# Pydantic models — these are what result.output will always be
# ---------------------------------------------------------------------------


class SentimentAnalysis(BaseModel):
    """Structured sentiment analysis result."""

    sentiment: Literal["positive", "negative", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0.0–1.0")
    key_phrases: list[str] = Field(description="Top 3 phrases driving sentiment")
    summary: str = Field(max_length=200, description="One-sentence summary")

    @field_validator("key_phrases")
    @classmethod
    def must_have_phrases(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("key_phrases must not be empty")
        return v


class TrendReport(BaseModel):
    """Market trend report."""

    title: str
    score: int = Field(ge=1, le=10, description="Relevance score 1–10")
    sectors: list[str] = Field(min_length=1)
    summary: str


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

# Almock with fixed JSON response so structured output parsing works
_sentiment_json = (
    '{"sentiment": "positive", "confidence": 0.95, '
    '"key_phrases": ["fantastic", "huge improvements", "new features"], '
    '"summary": "The Python release is extremely well received by the community."}'
)
_trend_json = (
    '{"title": "AI Chip Boom", "score": 9, '
    '"sectors": ["semiconductors", "cloud", "AI infra"], '
    '"summary": "AI chips are driving massive investment across the tech sector."}'
)

sentiment_model = Model.Almock(
    response_mode="custom",
    custom_response=_sentiment_json,
)
trend_model = Model.Almock(
    response_mode="custom",
    custom_response=_trend_json,
)


class SentimentAgent(Agent):
    _agent_name = "sentiment_agent"
    model = sentiment_model
    system_prompt = (
        "You perform sentiment analysis. Always respond with structured JSON "
        "matching the requested schema exactly."
    )
    output = Output(SentimentAnalysis, validation_retries=2)


class TrendAgent(Agent):
    _agent_name = "trend_agent"
    model = trend_model
    system_prompt = "You analyze market trends. Respond with structured JSON."
    output = Output(TrendReport, validation_retries=3)


def main() -> None:
    print("=" * 60)
    print("Structured Output Enforcement")
    print("result.output is ALWAYS the typed Pydantic model")
    print("=" * 60)

    # --- 1. Basic structured output ---
    print("\n1. Sentiment analysis")
    agent = SentimentAgent()

    # Observe validation retries
    retry_count = 0

    def on_retry(ctx: object) -> None:
        nonlocal retry_count
        retry_count += 1
        attempt = getattr(ctx, "attempt", "?")
        error = getattr(ctx, "error", "?")
        print(f"   [RETRY {attempt}] Validation failed: {str(error)[:80]}")

    agent.events.on(Hook.OUTPUT_VALIDATION_RETRY, on_retry)

    result = agent.run(
        "Analyze the sentiment of: 'The new Python release is fantastic! "
        "Performance improvements are huge and the new features are exactly what we needed.'"
    )

    # result.output is always SentimentAnalysis — never dict, never str
    analysis: SentimentAnalysis = result.output  # type: ignore[assignment]

    print(f"   sentiment:   {analysis.sentiment}")
    print(f"   confidence:  {analysis.confidence:.0%}")
    print(f"   key_phrases: {analysis.key_phrases}")
    print(f"   summary:     {analysis.summary}")
    print(f"   cost:        ${result.cost:.4f}")
    print(f"   retries:     {retry_count}")

    # result.content is always the raw LLM string
    print(f"\n   result.content (raw): {result.content[:120]}")

    # --- 2. Type safety ---
    print("\n2. Type safety — static type checkers know the exact type")
    # analysis is SentimentAnalysis, not Any — IDE and mypy know it
    _confidence: float = analysis.confidence  # type-safe access, no cast needed
    _ = _confidence

    # --- 3. TrendReport ---
    print("\n3. Market trend report")
    trend_agent = TrendAgent()
    trend_result = trend_agent.run("Report on AI chip trends in Q4 2026 for investment purposes.")
    report: TrendReport = trend_result.output  # type: ignore[assignment]
    print(f"   title:   {report.title}")
    print(f"   score:   {report.score}/10")
    print(f"   sectors: {report.sectors}")
    print(f"   summary: {report.summary[:120]}")

    # --- 4. OutputValidationError ---
    print("\n4. OutputValidationError — raised when all retries exhausted")

    class StrictAgent(Agent):
        model = Model.Almock()  # Returns lorem ipsum — invalid for SentimentAnalysis
        system_prompt = "Always output a valid JSON with 'value' field."
        output = Output(SentimentAnalysis, validation_retries=0)  # No retries

    strict = StrictAgent()
    try:
        strict.run("Return invalid output intentionally")
        print("   (no error — model returned valid output)")
    except OutputValidationError as exc:
        print(f"   OutputValidationError caught: {str(exc)[:100]}")
    except Exception as exc:
        print(f"   Other error: {type(exc).__name__}: {str(exc)[:80]}")

    print("\nDone. result.output is always the typed model — never a dict or string.")


if __name__ == "__main__":
    main()
