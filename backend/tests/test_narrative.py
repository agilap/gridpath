from __future__ import annotations

from datetime import timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.narrative import FALLBACK_NARRATIVE, generate_narrative
from app.models.fingerprint import AxisScores, CommitLabelDistribution, FingerprintDict

UTC = timezone.utc


def _fingerprint() -> FingerprintDict:
    return FingerprintDict(
        username="octocat",
        total_commits_analyzed=100,
        repos_analyzed=8,
        date_range="2022-01 to 2026-03",
        axes=AxisScores(
            shipping_velocity=7.1,
            bugfix_ratio=3.8,
            refactor_habit=6.2,
            test_coverage_signal=5.9,
            architecture_churn=4.1,
            consistency_score=7.8,
        ),
        top_languages=["Python", "TypeScript", "Go"],
        commit_label_distribution=CommitLabelDistribution(
            FEATURE=35,
            BUGFIX=20,
            REFACTOR=18,
            TEST=12,
            DOCS=7,
            CHORE=5,
            ARCHITECTURE=3,
        ),
        peak_activity_year="2025",
        style_evolution="shipping_focused → refactor_heavy",
        raw_axis_values={"shipping_velocity": 2.1},
    )


@pytest.mark.asyncio
async def test_generate_narrative_with_mocked_openai_response() -> None:
    text = (
        "Your commit history shows strong momentum in shipping features while preserving quality. "
        "You consistently return to refactoring to keep complexity in check. "
        "That balance makes your delivery pace sustainable over time. "
        "The numbers suggest you are most effective when iterating quickly with clear follow-through.\n\n"
        "Over the years, your style evolves from shipping_focused into refactor_heavy habits. "
        "You maintain a healthy bug-fix ratio and stable cadence across active weeks. "
        "This pattern indicates an engineer who treats maintainability as part of product delivery. "
        "Your profile reads like someone who can scale both code and team trust."
    )

    mocked_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=110, total_tokens=230),
    )

    with patch("app.core.narrative.AsyncOpenAI") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=mocked_response)

        result = await generate_narrative(_fingerprint())

        assert result == text
        mock_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_narrative_fallback_on_openai_exception() -> None:
    with patch("app.core.narrative.AsyncOpenAI") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("OpenAI down"))

        result = await generate_narrative(_fingerprint())

        assert result == FALLBACK_NARRATIVE
        mock_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_narrative_makes_exactly_one_api_call_per_invocation() -> None:
    mocked_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="a\n\nb"))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=10, total_tokens=20),
    )

    with patch("app.core.narrative.AsyncOpenAI") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=mocked_response)

        await generate_narrative(_fingerprint())

        assert mock_client.chat.completions.create.await_count == 1
