from __future__ import annotations

from pydantic import BaseModel


class AxisScores(BaseModel):
    shipping_velocity: float
    bugfix_ratio: float
    refactor_habit: float
    test_coverage_signal: float
    architecture_churn: float
    consistency_score: float


class CommitLabelDistribution(BaseModel):
    FEATURE: int
    BUGFIX: int
    REFACTOR: int
    TEST: int
    DOCS: int
    CHORE: int
    ARCHITECTURE: int


class FingerprintDict(BaseModel):
    username: str
    total_commits_analyzed: int
    repos_analyzed: int
    date_range: str
    axes: AxisScores
    top_languages: list[str]
    commit_label_distribution: CommitLabelDistribution
    peak_activity_year: str
    style_evolution: str
    raw_axis_values: dict[str, float]
