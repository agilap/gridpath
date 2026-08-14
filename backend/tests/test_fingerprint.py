from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.fingerprint import (
    _architecture_churn,
    _bugfix_ratio,
    _consistency_score,
    _refactor_habit,
    _shipping_velocity,
    _style_evolution,
    _test_coverage_signal,
    compute_fingerprint,
)
from app.models.commit import ASTSignals, CommitRecord
from app.models.github import RepoInfo

UTC = timezone.utc


def _commit(idx: int, label: str, dt: datetime) -> CommitRecord:
    return CommitRecord(
        sha=f"sha-{idx}",
        label=label,
        confidence=0.9,
        ast_signals=ASTSignals(
            fn_delta=0,
            class_delta=0,
            complexity_delta=0.0,
            import_churn=0,
            file_count_delta=0,
        ),
        repo="octocat/repo",
        date=dt,
        lines_added=10,
        lines_deleted=3,
        message=f"msg-{idx}",
    )


def _repos() -> list[RepoInfo]:
    return [
        RepoInfo(
            name="repo1",
            full_name="octocat/repo1",
            language="Python",
            stargazers_count=3,
            pushed_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        RepoInfo(
            name="repo2",
            full_name="octocat/repo2",
            language="TypeScript",
            stargazers_count=2,
            pushed_at=datetime(2026, 1, 2, tzinfo=UTC),
        ),
    ]


def test_shipping_velocity_formula() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    commits = [_commit(i, "FEATURE", start + timedelta(days=i * 7)) for i in range(4)]

    score, raw = _shipping_velocity(commits)

    assert raw == pytest.approx(4 / 3)
    assert score == pytest.approx((4 / 3) / 3 * 10)


def test_bugfix_ratio_formula() -> None:
    d = datetime(2026, 1, 1, tzinfo=UTC)
    commits = [
        _commit(1, "FEATURE", d),
        _commit(2, "FEATURE", d),
        _commit(3, "BUGFIX", d),
    ]

    score, raw = _bugfix_ratio(commits)

    assert raw == pytest.approx(1 / 3)
    assert score == pytest.approx((1 / 3) * 10)


def test_refactor_habit_formula() -> None:
    d = datetime(2026, 1, 1, tzinfo=UTC)
    commits = [_commit(1, "REFACTOR", d), _commit(2, "FEATURE", d), _commit(3, "CHORE", d)]

    score, raw = _refactor_habit(commits)

    assert raw == pytest.approx(1 / 3)
    assert score == pytest.approx((1 / 3) * 10)


def test_test_coverage_signal_formula() -> None:
    d = datetime(2026, 1, 1, tzinfo=UTC)
    commits = [_commit(1, "FEATURE", d), _commit(2, "TEST", d), _commit(3, "TEST", d)]

    score, raw = _test_coverage_signal(commits)

    assert raw == pytest.approx(2.0)
    assert score == 10.0


def test_architecture_churn_formula() -> None:
    d = datetime(2026, 1, 1, tzinfo=UTC)
    commits = [_commit(i, "ARCHITECTURE", d) for i in range(1, 3)] + [_commit(3, "CHORE", d)]

    score, raw = _architecture_churn(commits)

    assert raw == pytest.approx(2 / 3)
    assert score == pytest.approx((2 / 3) * 10)


def test_axis_scores_never_exceed_10() -> None:
    d = datetime(2026, 1, 1, tzinfo=UTC)
    refactor_commits = [_commit(i, "REFACTOR", d) for i in range(100)]
    architecture_commits = [_commit(i, "ARCHITECTURE", d) for i in range(100)]

    assert _refactor_habit(refactor_commits)[0] <= 10.0
    assert _architecture_churn(architecture_commits)[0] <= 10.0


def test_consistency_score_formula() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    commits = []
    counts = [1, 2, 4, 2]
    idx = 0
    for week, count in enumerate(counts):
        for _ in range(count):
            idx += 1
            commits.append(_commit(idx, "FEATURE", start + timedelta(days=7 * week)))

    score, cv = _consistency_score(commits)

    assert cv > 0
    assert 0 <= score <= 10


def test_edge_case_zero_commits() -> None:
    result = compute_fingerprint("octocat", [], [], ["Python"])

    assert result.total_commits_analyzed == 0
    assert result.repos_analyzed == 0
    assert result.date_range == "N/A"
    assert result.peak_activity_year == "N/A"
    assert result.axes.bugfix_ratio == 5.0
    assert result.axes.test_coverage_signal == 5.0


def test_edge_case_all_same_label() -> None:
    d = datetime(2026, 1, 1, tzinfo=UTC)
    commits = [_commit(i, "FEATURE", d + timedelta(days=i)) for i in range(20)]

    result = compute_fingerprint("octocat", commits, _repos(), ["Python", "Go", "Rust", "TS"])

    assert result.commit_label_distribution.FEATURE == 20
    assert result.commit_label_distribution.BUGFIX == 0
    assert result.top_languages == ["Python", "Go", "Rust"]


def test_edge_case_single_week_consistency_default() -> None:
    d = datetime(2026, 1, 1, tzinfo=UTC)
    commits = [_commit(i, "CHORE", d + timedelta(days=1)) for i in range(3)]

    score, cv = _consistency_score(commits)

    assert score == 8.0
    assert cv == 0.0


def test_style_evolution_same_dominant() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    commits = [_commit(i, "REFACTOR", start + timedelta(days=i)) for i in range(8)]

    assert _style_evolution(commits) == "consistent refactor_heavy"


def test_style_evolution_different_dominant() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    commits = []
    for i in range(5):
        commits.append(_commit(i, "FEATURE", start + timedelta(days=i)))
    for i in range(5, 10):
        commits.append(_commit(i, "ARCHITECTURE", start + timedelta(days=i)))

    assert _style_evolution(commits) == "shipping_focused → architecture_heavy"


def test_compute_fingerprint_integration_100_commits() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    labels = (
        ["FEATURE"] * 30
        + ["BUGFIX"] * 20
        + ["REFACTOR"] * 15
        + ["TEST"] * 15
        + ["DOCS"] * 10
        + ["CHORE"] * 5
        + ["ARCHITECTURE"] * 5
    )
    commits = [_commit(i, labels[i], start + timedelta(days=i * 3)) for i in range(100)]

    repos = [
        RepoInfo(
            name=f"repo-{i}",
            full_name=f"octocat/repo-{i}",
            language="Python" if i % 2 == 0 else "TypeScript",
            stargazers_count=i,
            pushed_at=start + timedelta(days=i),
        )
        for i in range(10)
    ]

    result = compute_fingerprint(
        username="octocat",
        commits=commits,
        repos=repos,
        top_languages=["Python", "TypeScript", "Go", "Rust"],
    )

    assert result.username == "octocat"
    assert result.total_commits_analyzed == 100
    assert result.repos_analyzed == 10
    assert result.date_range.startswith("2024-01")
    assert result.commit_label_distribution.FEATURE == 30
    assert result.commit_label_distribution.ARCHITECTURE == 5
    assert len(result.top_languages) == 3
    assert 0 <= result.axes.shipping_velocity <= 10
    assert 0 <= result.axes.bugfix_ratio <= 10
    assert 0 <= result.axes.refactor_habit <= 10
    assert 0 <= result.axes.test_coverage_signal <= 10
    assert 0 <= result.axes.architecture_churn <= 10
    assert 0 <= result.axes.consistency_score <= 10
    assert "shipping_velocity" in result.raw_axis_values
    assert "bugfix_ratio" in result.raw_axis_values
