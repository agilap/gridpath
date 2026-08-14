from __future__ import annotations

from openai import AsyncOpenAI
import structlog

from app.config import settings
from app.models.fingerprint import FingerprintDict

PROMPT_TEMPLATE = """
You are writing a developer profile card in the style of Spotify Wrapped.
Given this developer fingerprint computed from their GitHub commit history, write exactly
2 paragraphs (4-5 sentences each) describing their coding personality and career arc.

Be specific, warm, and insightful. Reference actual numbers. Avoid generic praise.
Use second person ("Your commit history shows...").
Do not make up facts not present in the fingerprint.

Fingerprint:
{fingerprint_json}

Output: exactly 2 paragraphs, plain text, no headers, no bullet points.
"""

FALLBACK_NARRATIVE = (
    "Your commit history tells the story of a developer who ships with purpose. "
    "The patterns in your contributions reveal a thoughtful engineer who balances "
    "feature work with code quality.\n\n"
    "Over time, your fingerprint shows a consistent approach to problem-solving, "
    "with a clear emphasis on the areas that matter most to your projects. "
    "Your work reflects both technical depth and a steady, professional cadence."
)

logger = structlog.get_logger(__name__)


async def generate_narrative(fingerprint: FingerprintDict) -> str:
    prompt = PROMPT_TEMPLATE.format(fingerprint_json=fingerprint.model_dump_json(indent=2))

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or None)
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            max_tokens=250,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.choices[0].message.content if response.choices else ""
        narrative = (content or "").strip()

        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0

        logger.bind(event="narrative_generated").info(
            "narrative_generated",
            username=fingerprint.username,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        if not narrative:
            return FALLBACK_NARRATIVE
        return narrative
    except Exception:
        logger.exception("narrative_generation_failed", username=fingerprint.username)
        return FALLBACK_NARRATIVE
