from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean, stdev

from app.models.commit import CommitLabel, CommitRecord
from app.models.fingerprint import AxisScores, CommitLabelDistribution, FingerprintDict
from app.models.github import RepoInfo

LABELS: tuple[CommitLabel, ...] = (
    "FEATURE",
    "BUGFIX",
    "REFACTOR",
    "TEST",
    "DOCS",
    "CHORE",
    "ARCHITECTURE",
)


def _label_counts(commits: list[CommitRecord]) -> Counter[CommitLabel]:
    counts: Counter[CommitLabel] = Counter()
    for commit in commits:
        counts[commit.label] += 1
    for label in LABELS:
        counts[label] += 0
    return counts


def _shipping_velocity(commits: list[CommitRecord]) -> tuple[float, float]:
    if not commits:
        return 0.0, 0.0

    min_date = min(c.date for c in commits)
    max_date = max(c.date for c in commits)
    weeks_active = (max_date - min_date).days / 7

    feature_count = sum(1 for c in commits if c.label == "FEATURE")
    raw = feature_count / max(weeks_active, 1)
    normalized = min(max(raw / 3 * 10, 0.0), 10.0)
    return normalized, raw


def _bugfix_ratio(commits: list[CommitRecord]) -> tuple[float, float]:
    counts = _label_counts(commits)
    denominator = counts["FEATURE"] + counts["BUGFIX"]
    if denominator == 0:
        return 5.0, 0.5
    raw = counts["BUGFIX"] / denominator
    return raw * 10, raw


def _refactor_habit(commits: list[CommitRecord]) -> tuple[float, float]:
    total = len(commits)
    raw = _label_counts(commits)["REFACTOR"] / max(total, 1)
    return min(raw * 10, 10.0), raw


def _test_coverage_signal(commits: list[CommitRecord]) -> tuple[float, float]:
    counts = _label_counts(commits)
    feature_count = counts["FEATURE"]
    if feature_count == 0:
        return 5.0, 0.5

    raw = counts["TEST"] / feature_count
    return min(raw * 10, 10.0), raw


def _architecture_churn(commits: list[CommitRecord]) -> tuple[float, float]:
    total = len(commits)
    raw = _label_counts(commits)["ARCHITECTURE"] / max(total, 1)
    return min(raw * 10, 10.0), raw


def _consistency_score(commits: list[CommitRecord]) -> tuple[float, float]:
    if not commits:
        return 8.0, 0.0

    weekly: dict[tuple[int, int], int] = defaultdict(int)
    for commit in commits:
        year, week, _ = commit.date.isocalendar()
        weekly[(year, week)] += 1

    weekly_counts = list(weekly.values())
    weekly_mean = mean(weekly_counts)
    if weekly_mean == 0:
        return 8.0, 0.0

    if len(weekly_counts) == 1:
        return 8.0, 0.0

    weekly_stdev = stdev(weekly_counts)
    if weekly_stdev == 0:
        return 8.0, 0.0

    cv = weekly_stdev / weekly_mean
    score = max(0.0, min(10.0, (1 - cv) * 10))
    return score, cv


def _style_name(label: CommitLabel) -> str:
    mapping: dict[CommitLabel, str] = {
        "ARCHITECTURE": "architecture_heavy",
        "REFACTOR": "refactor_heavy",
        "FEATURE": "shipping_focused",
        "BUGFIX": "maintenance_mode",
        "TEST": "quality_focused",
        "DOCS": "docs_focused",
        "CHORE": "ops_focused",
    }
    return mapping[label]


def _dominant_non_chore(commits: list[CommitRecord]) -> CommitLabel:
    labels = [c.label for c in commits if c.label != "CHORE"]
    if not labels:
        labels = [c.label for c in commits]

    if not labels:
        return "CHORE"

    counts = Counter(labels)
    return max(counts, key=counts.get)


def _style_evolution(commits: list[CommitRecord]) -> str:
    if not commits:
        return "consistent ops_focused"

    ordered = sorted(commits, key=lambda c: c.date)
    mid = len(ordered) // 2
    first_half = ordered[:mid] or ordered
    second_half = ordered[mid:] or ordered

    first_label = _dominant_non_chore(first_half)
    second_label = _dominant_non_chore(second_half)

    first_name = _style_name(first_label)
    second_name = _style_name(second_label)

    if first_name == second_name:
        return f"consistent {first_name}"
    return f"{first_name} → {second_name}"


def _peak_activity_year(commits: list[CommitRecord]) -> str:
    if not commits:
        return "N/A"

    counts = Counter(str(c.date.year) for c in commits)
    return max(counts, key=counts.get)


def _date_range(commits: list[CommitRecord]) -> str:
    if not commits:
        return "N/A"

    min_date = min(c.date for c in commits)
    max_date = max(c.date for c in commits)
    return f"{min_date:%Y-%m} to {max_date:%Y-%m}"


def compute_commits_by_year(commits: list[CommitRecord]) -> dict[str, CommitLabelDistribution]:
    yearly: dict[str, dict[str, int]] = {}
    for commit in commits:
        year = str(commit.date.year)
        if year not in yearly:
            yearly[year] = {label: 0 for label in LABELS}
        yearly[year][commit.label] += 1
    return {
        year: CommitLabelDistribution(**counts)
        for year, counts in sorted(yearly.items())
    }


def compute_fingerprint(
    username: str,
    commits: list[CommitRecord],
    repos: list[RepoInfo],
    top_languages: list[str],
) -> FingerprintDict:
    shipping_velocity, raw_shipping_velocity = _shipping_velocity(commits)
    bugfix_ratio, raw_bugfix_ratio = _bugfix_ratio(commits)
    refactor_habit, raw_refactor_habit = _refactor_habit(commits)
    test_coverage_signal, raw_test_coverage_signal = _test_coverage_signal(commits)
    architecture_churn, raw_architecture_churn = _architecture_churn(commits)
    consistency_score, raw_consistency = _consistency_score(commits)

    counts = _label_counts(commits)

    axes = AxisScores(
        shipping_velocity=shipping_velocity,
        bugfix_ratio=bugfix_ratio,
        refactor_habit=refactor_habit,
        test_coverage_signal=test_coverage_signal,
        architecture_churn=architecture_churn,
        consistency_score=consistency_score,
    )

    distribution = CommitLabelDistribution(
        FEATURE=counts["FEATURE"],
        BUGFIX=counts["BUGFIX"],
        REFACTOR=counts["REFACTOR"],
        TEST=counts["TEST"],
        DOCS=counts["DOCS"],
        CHORE=counts["CHORE"],
        ARCHITECTURE=counts["ARCHITECTURE"],
    )

    return FingerprintDict(
        username=username,
        total_commits_analyzed=len(commits),
        repos_analyzed=len({repo.full_name for repo in repos}),
        date_range=_date_range(commits),
        axes=axes,
        top_languages=top_languages[:3],
        commit_label_distribution=distribution,
        peak_activity_year=_peak_activity_year(commits),
        style_evolution=_style_evolution(commits),
        raw_axis_values={
            "shipping_velocity": raw_shipping_velocity,
            "bugfix_ratio": raw_bugfix_ratio,
            "refactor_habit": raw_refactor_habit,
            "test_coverage_signal": raw_test_coverage_signal,
            "architecture_churn": raw_architecture_churn,
            "consistency_cv": raw_consistency,
        },
    )
