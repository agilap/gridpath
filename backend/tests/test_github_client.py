from __future__ import annotations

import asyncio

import pytest

from app.core.github_client import GitHubClient


@pytest.mark.asyncio
async def test_fetch_repos_public_skips_forks_and_limits_30(httpx_mock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/users/octocat/repos?per_page=100&page=1&sort=pushed&direction=desc",
        json=[
            {
                "name": "repo-a",
                "full_name": "octocat/repo-a",
                "language": "Python",
                "stargazers_count": 10,
                "pushed_at": "2026-03-20T10:00:00Z",
                "fork": False,
            },
            {
                "name": "repo-fork",
                "full_name": "octocat/repo-fork",
                "language": "Python",
                "stargazers_count": 0,
                "pushed_at": "2026-03-20T10:00:00Z",
                "fork": True,
            },
        ],
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/users/octocat/repos?per_page=100&page=2&sort=pushed&direction=desc",
        json=[
            {
                "name": f"repo-{i}",
                "full_name": f"octocat/repo-{i}",
                "language": "TypeScript",
                "stargazers_count": i,
                "pushed_at": "2026-03-20T10:00:00Z",
                "fork": False,
            }
            for i in range(1, 40)
        ],
    )

    async with GitHubClient() as client:
        repos = await client.fetch_repos("octocat", include_private=False)

    assert len(repos) == 30
    assert all(repo.full_name != "octocat/repo-fork" for repo in repos)


@pytest.mark.asyncio
async def test_fetch_repos_private_uses_user_endpoint(httpx_mock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/user/repos?per_page=100&page=1&sort=pushed&direction=desc",
        json=[
            {
                "name": "private-repo",
                "full_name": "octocat/private-repo",
                "language": "Go",
                "stargazers_count": 1,
                "pushed_at": "2026-03-20T10:00:00Z",
                "fork": False,
            }
        ],
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/user/repos?per_page=100&page=2&sort=pushed&direction=desc",
        json=[],
    )

    async with GitHubClient(token="gho_test") as client:
        repos = await client.fetch_repos("octocat", include_private=True)

    assert len(repos) == 1
    assert repos[0].full_name == "octocat/private-repo"


@pytest.mark.asyncio
async def test_fetch_commits_collects_stats(httpx_mock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/repos/octocat/repo/commits?per_page=100&page=1",
        json=[{"sha": "abc123"}, {"sha": "def456"}],
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/repos/octocat/repo/commits/abc123",
        json={
            "commit": {"message": "feat: add api", "author": {"date": "2026-03-20T10:00:00Z"}},
            "stats": {"additions": 12, "deletions": 3},
        },
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/repos/octocat/repo/commits/def456",
        json={
            "commit": {"message": "fix: patch", "author": {"date": "2026-03-21T11:00:00Z"}},
            "stats": {"additions": 4, "deletions": 1},
        },
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/repos/octocat/repo/commits?per_page=100&page=2",
        json=[],
    )

    async with GitHubClient(token="gho_test") as client:
        commits = await client.fetch_commits("octocat/repo", max_count=10)

    assert [c.sha for c in commits] == ["abc123", "def456"]
    assert commits[0].additions == 12
    assert commits[0].deletions == 3
    assert commits[1].message == "fix: patch"


@pytest.mark.asyncio
async def test_fetch_diff_returns_empty_on_404(httpx_mock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/repos/octocat/repo/commits/missing",
        status_code=404,
    )

    async with GitHubClient(token="gho_test") as client:
        diff = await client.fetch_diff("octocat/repo", "missing")

    assert diff == ""


@pytest.mark.asyncio
async def test_rate_limit_backoff_and_retry_after(httpx_mock, monkeypatch) -> None:
    sleep_calls: list[int] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(int(seconds))

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/repos/octocat/repo/commits/abc123",
        status_code=403,
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/repos/octocat/repo/commits/abc123",
        status_code=429,
        headers={"Retry-After": "7"},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/repos/octocat/repo/commits/abc123",
        status_code=200,
        text="diff content",
        headers={"X-RateLimit-Remaining": "500"},
    )

    async with GitHubClient(token="gho_test") as client:
        client._last_rate_remaining = 50
        diff = await client.fetch_diff("octocat/repo", "abc123")

    assert diff == "diff content"
    assert sleep_calls == [60, 15, 7]
