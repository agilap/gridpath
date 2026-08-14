from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CommitLabel = Literal["FEATURE", "BUGFIX", "REFACTOR", "TEST", "DOCS", "CHORE", "ARCHITECTURE"]


class ASTSignals(BaseModel):
    fn_delta: int
    class_delta: int
    complexity_delta: float
    import_churn: int
    file_count_delta: int


class CommitRecord(BaseModel):
    sha: str
    label: CommitLabel
    confidence: float = Field(ge=0.0, le=1.0)
    ast_signals: ASTSignals
    repo: str
    date: datetime
    lines_added: int
    lines_deleted: int
    message: str
