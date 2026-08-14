from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from app.models.fingerprint import CommitLabelDistribution, FingerprintDict

_USERNAME_RE = re.compile(r"^[A-Za-z0-9-]{1,39}$")
_BLOCKLIST = {"admin", "api", "gridpath"}


class AnalysisResult(BaseModel):
    """Full result payload returned from a completed analysis job.
    This is what gets cached in Redis and returned from GET /api/result/:job_id.
    """

    fingerprint: FingerprintDict
    narrative: str
    card_url: str
    share_token: str
    expires_at: str
    cached: bool = False
    commits_by_year: dict[str, CommitLabelDistribution] | None = None


class AnalyzeRequest(BaseModel):
    """Request body for POST /api/analyze."""

    username: str = Field(min_length=1, max_length=39)
    include_private: bool = False

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not _USERNAME_RE.fullmatch(value):
            raise ValueError("Username must match [a-zA-Z0-9-]{1,39}.")
        if value.startswith("-") or value.endswith("-"):
            raise ValueError("Username cannot start or end with a hyphen.")
        if value.lower() in _BLOCKLIST:
            raise ValueError("This username is reserved and cannot be analyzed.")
        return value


class AnalyzeResponse(BaseModel):
    """Response from POST /api/analyze when a job is enqueued."""

    job_id: str
    estimated_seconds: int
    status: str = "PENDING"
    result: AnalysisResult | None = None


class StatusResponse(BaseModel):
    """Response from GET /api/status/:job_id."""

    status: str
    progress_pct: int
    message: str
