from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx
import structlog

from app.exceptions import CommitFetchError, RateLimitError
from app.models.github import CommitMeta, RepoInfo

logger = structlog.get_logger(__name__)

REQUEST_TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=30.0,
    write=10.0,
    pool=5.0,
)


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self._token = token
        self._last_rate_remaining: int | None = None

        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.close()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        allow_404: bool = False,
    ) -> httpx.Response:
        backoff_schedule = [15, 30, 60]
        attempt = 0

        if self._last_rate_remaining is not None and self._last_rate_remaining <= 50:
            await asyncio.sleep(60)
            self._last_rate_remaining = None

        while True:
            try:
                response = await self._client.request(method, url, params=params, headers=headers)
            except httpx.TimeoutException as exc:
                logger.warning(
                    "github_api_timeout",
                    method=method,
                    url=url,
                    error=str(exc),
                )
                raise CommitFetchError(f"GitHub API timeout on {url}") from exc

            logger.debug(
                "github_api_call",
                method=method,
                url=str(response.request.url),
                status_code=response.status_code,
            )

            remaining_header = response.headers.get("X-RateLimit-Remaining")
            if remaining_header is not None:
                try:
                    self._last_rate_remaining = int(remaining_header)
                except ValueError:
                    self._last_rate_remaining = None

            if response.status_code == 429:
                retry_after_header = response.headers.get("Retry-After", "60")
                try:
                    retry_after = int(retry_after_header)
                except ValueError:
                    retry_after = 60
                await asyncio.sleep(max(retry_after, 1))
                continue

            if response.status_code == 403 and attempt < len(backoff_schedule):
                await asyncio.sleep(backoff_schedule[attempt])
                attempt += 1
                continue

            if allow_404 and response.status_code == 404:
                return response

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 403:
                    remaining = exc.response.headers.get("X-RateLimit-Remaining", "?")
                    reset = exc.response.headers.get("X-RateLimit-Reset", "?")
                    raise RateLimitError(
                        f"GitHub rate limit hit. Remaining: {remaining}. Reset: {reset}"
                    ) from exc
                if exc.response.status_code == 404 and allow_404:
                    return response
                raise CommitFetchError(f"GitHub API error {exc.response.status_code}") from exc
            return response

    async def fetch_repos(self, username: str, include_private: bool) -> list[RepoInfo]:
        repos: list[RepoInfo] = []
        page = 1

        endpoint = f"/users/{username}/repos"
        if include_private and self._token:
            endpoint = "/user/repos"

        while len(repos) < 30:
            response = await self._request(
                "GET",
                endpoint,
                params={"per_page": 100, "page": page, "sort": "pushed", "direction": "desc"},
            )
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                break

            for item in payload:
                if not isinstance(item, dict):
                    continue
                if item.get("fork"):
                    continue

                repo = RepoInfo(
                    name=str(item.get("name", "")),
                    full_name=str(item.get("full_name", "")),
                    language=item.get("language") if isinstance(item.get("language"), str) else None,
                    stargazers_count=int(item.get("stargazers_count", 0) or 0),
                    pushed_at=item.get("pushed_at"),
                )
                repos.append(repo)
                if len(repos) >= 30:
                    break

            page += 1

        return repos

    async def fetch_commits(self, repo_full_name: str, max_count: int = 500) -> list[CommitMeta]:
        commits: list[CommitMeta] = []
        page = 1

        while len(commits) < max_count:
            response = await self._request(
                "GET",
                f"/repos/{repo_full_name}/commits",
                params={"per_page": 100, "page": page},
            )
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                break

            for item in payload:
                if len(commits) >= max_count:
                    break
                if not isinstance(item, dict):
                    continue

                sha = item.get("sha")
                if not isinstance(sha, str) or not sha:
                    continue

                detail_response = await self._request(
                    "GET",
                    f"/repos/{repo_full_name}/commits/{sha}",
                    allow_404=True,
                )
                if detail_response.status_code == 404:
                    continue

                detail = detail_response.json()
                if not isinstance(detail, dict):
                    continue

                commit_block = detail.get("commit") if isinstance(detail.get("commit"), dict) else {}
                message = commit_block.get("message") if isinstance(commit_block.get("message"), str) else ""

                author_block = commit_block.get("author") if isinstance(commit_block.get("author"), dict) else {}
                date = author_block.get("date") if isinstance(author_block.get("date"), str) else None

                stats = detail.get("stats") if isinstance(detail.get("stats"), dict) else {}
                additions = int(stats.get("additions", 0) or 0)
                deletions = int(stats.get("deletions", 0) or 0)

                commits.append(
                    CommitMeta(
                        sha=sha,
                        message=message,
                        date=date,
                        additions=additions,
                        deletions=deletions,
                    )
                )

            page += 1

        return commits

    async def fetch_diff(self, repo_full_name: str, sha: str) -> str:
        response = await self._request(
            "GET",
            f"/repos/{repo_full_name}/commits/{sha}",
            headers={"Accept": "application/vnd.github.diff"},
            allow_404=True,
        )
        if response.status_code == 404:
            return ""
        return response.text
