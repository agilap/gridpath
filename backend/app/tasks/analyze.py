from __future__ import annotations

import asyncio
import json
import secrets
from datetime import datetime, timedelta, timezone

import httpx
import structlog
from celery.exceptions import SoftTimeLimitExceeded
from app.card.generator import generate_card
from storage3.utils import StorageException

from app.celery_app import celery_app
from app.config import settings
from app.core.classifier import classify_commit
from app.core.fingerprint import compute_commits_by_year, compute_fingerprint
from app.core.github_client import GitHubClient
from app.core.narrative import generate_narrative
from app.db.redis_client import get_redis
from app.db.supabase_client import get_supabase
from app.exceptions import AuthRequiredError, CommitFetchError, RateLimitError
from app.models.commit import CommitRecord
from app.models.github import RepoInfo

logger = structlog.get_logger(__name__)


async def _run_analysis_async(self, username: str, github_token: str | None, include_private: bool) -> dict:
    effective_token = github_token or settings.GITHUB_API_TOKEN or None

    # Quick connectivity check to fail fast before expensive work.
    self.update_state(state="PROGRESS", meta={"progress": 2, "message": "Checking GitHub API..."})
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as probe:
            probe_headers = {"Accept": "application/vnd.github+json"}
            if effective_token:
                probe_headers["Authorization"] = f"Bearer {effective_token}"
            resp = await probe.get(f"https://api.github.com/users/{username}", headers=probe_headers)
            if resp.status_code == 404:
                raise CommitFetchError(f"GitHub user '{username}' not found")
            if resp.status_code == 401:
                raise AuthRequiredError("GitHub token is invalid or expired")
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 403:
                    remaining = exc.response.headers.get("X-RateLimit-Remaining", "?")
                    reset = exc.response.headers.get("X-RateLimit-Reset", "?")
                    raise RateLimitError(
                        f"GitHub rate limit hit. Remaining: {remaining}. Reset: {reset}"
                    ) from exc
                raise CommitFetchError(f"GitHub API error {exc.response.status_code}") from exc
    except httpx.TimeoutException as exc:
        raise CommitFetchError("Cannot reach GitHub API - connection timed out") from exc

    self.update_state(state="PROGRESS", meta={"progress": 5, "message": "Starting analysis..."})
    self.update_state(state="PROGRESS", meta={"progress": 10, "message": "Fetching repositories..."})

    async with GitHubClient(token=effective_token) as github:
        repos: list[RepoInfo] = await github.fetch_repos(username=username, include_private=include_private)
        if not repos:
            raise CommitFetchError(f"No repositories found for {username}")

        # Keep request volume small when running without a token.
        if not effective_token:
            repos = repos[:2]
            max_commits_per_repo = min(settings.GITHUB_API_MAX_COMMITS_PER_REPO, 3)
        else:
            max_commits_per_repo = min(settings.GITHUB_API_MAX_COMMITS_PER_REPO, 10)

        self.update_state(
            state="PROGRESS",
            meta={"progress": 20, "message": f"Found {len(repos)} repos. Reading commits..."},
        )
        all_commits: list[CommitRecord] = []
        total_repos = max(len(repos), 1)
        for idx, repo in enumerate(repos, start=1):
            progress = 20 + int((idx / total_repos) * 40)
            self.update_state(
                state="PROGRESS",
                meta={"progress": progress, "message": f"Reading {repo.name} ({idx}/{total_repos})..."},
            )

            commit_metas = await github.fetch_commits(
                repo_full_name=repo.full_name,
                max_count=max_commits_per_repo,
            )

            for meta in commit_metas:
                diff = await github.fetch_diff(repo.full_name, meta.sha)
                commit_date = meta.date or datetime.now(timezone.utc)
                commit = classify_commit(
                    sha=meta.sha,
                    message=meta.message,
                    diff=diff,
                    repo=repo.full_name,
                    date=commit_date,
                    lines_added=meta.additions,
                    lines_deleted=meta.deletions,
                )
                all_commits.append(commit)

    self.update_state(state="PROGRESS", meta={"progress": 60, "message": f"Classifying {len(all_commits)} commits..."})

    repo_language_counts: dict[str, int] = {}
    for repo in repos:
        if repo.language:
            repo_language_counts[repo.language] = repo_language_counts.get(repo.language, 0) + 1
    top_languages = [lang for lang, _ in sorted(repo_language_counts.items(), key=lambda item: item[1], reverse=True)[:3]]

    self.update_state(state="PROGRESS", meta={"progress": 75, "message": "Computing fingerprint..."})
    fingerprint = compute_fingerprint(
        username=username,
        commits=all_commits,
        repos=repos,
        top_languages=top_languages,
    )

    commits_by_year = compute_commits_by_year(all_commits)

    self.update_state(state="PROGRESS", meta={"progress": 85, "message": "Writing your career narrative..."})
    narrative = await generate_narrative(fingerprint)

    self.update_state(state="PROGRESS", meta={"progress": 90, "message": "Generating share card..."})
    supabase = get_supabase()
    token = secrets.token_urlsafe(16)
    card_path = f"cards/{token}.png"
    png_bytes = generate_card(fingerprint, narrative)

    try:
        supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
            card_path,
            png_bytes,
            {"content-type": "image/png", "cache-control": "604800"},
        )
    except StorageException as exc:
        if "Bucket not found" not in str(exc):
            raise
        logger.warning("storage_bucket_missing_creating", bucket=settings.SUPABASE_STORAGE_BUCKET)
        supabase.storage.create_bucket(
            settings.SUPABASE_STORAGE_BUCKET,
            options={"public": True},
        )
        supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
            card_path,
            png_bytes,
            {"content-type": "image/png", "cache-control": "604800"},
        )
    card_url = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).get_public_url(card_path)

    self.update_state(state="PROGRESS", meta={"progress": 95, "message": "Saving results..."})
    supabase.table("profiles").upsert(
        {
            "username": username,
            "fingerprint": fingerprint.model_dump(),
            "narrative": narrative,
            "repos_count": fingerprint.repos_analyzed,
            "commits_count": fingerprint.total_commits_analyzed,
            "top_languages": fingerprint.top_languages,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="username",
    ).execute()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    supabase.table("share_tokens").insert(
        {
            "token": token,
            "username": username,
            "card_url": card_url,
            "expires_at": expires_at,
        }
    ).execute()

    full_result = {
        "fingerprint": fingerprint.model_dump(),
        "narrative": narrative,
        "card_url": card_url,
        "share_token": token,
        "expires_at": expires_at,
        "cached": True,
        "commits_by_year": {year: dist.model_dump() for year, dist in commits_by_year.items()},
    }

    # Never cache private-analysis results — the cache key is username-only
    # and would leak private-derived fingerprints to anonymous requests.
    if not include_private:
        r = get_redis()
        r.setex(
            name=f"profile:{username}",
            time=settings.PROFILE_CACHE_TTL_SECONDS,
            value=json.dumps(full_result),
        )

    return full_result


@celery_app.task(
    bind=True,
    max_retries=3,
    time_limit=300,
    soft_time_limit=270,
    name="app.tasks.analyze.run_analysis",
)
def run_analysis(self, username: str, github_token: str | None, include_private: bool) -> dict:
    try:
        return asyncio.run(_run_analysis_async(self, username, github_token, include_private))
    except SoftTimeLimitExceeded:
        logger.error("analysis_task_timeout", username=username)
        raise
    except RateLimitError as exc:
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 2,
                "message": f"Rate limited by GitHub, retrying in 60s: {exc}",
            },
        )
        raise self.retry(exc=exc, countdown=60)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 503:
            raise self.retry(exc=exc, countdown=30)
        logger.exception("analysis_failed_http", username=username, status_code=exc.response.status_code)
        raise
    except Exception as exc:
        logger.error(
            "analysis_task_failed",
            username=username,
            error=str(exc),
            exc_info=True,
        )
        raise
