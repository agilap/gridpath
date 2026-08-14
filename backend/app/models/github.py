from datetime import datetime

from pydantic import BaseModel


class RepoInfo(BaseModel):
    name: str
    full_name: str
    language: str | None
    stargazers_count: int
    pushed_at: datetime | None


class CommitMeta(BaseModel):
    sha: str
    message: str
    date: datetime | None
    additions: int
    deletions: int
