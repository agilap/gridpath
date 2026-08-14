from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}
        self.expiry: dict[str, int] = {}

    def get(self, key: str) -> Any:
        return self.values.get(key)

    def setex(self, key: str | None = None, _ttl: int | None = None, value: str | None = None, **kwargs: Any) -> bool:
        name = key if key is not None else kwargs.get("name")
        ttl = _ttl if _ttl is not None else kwargs.get("time")
        data = value if value is not None else kwargs.get("value")
        if name is None or data is None:
            raise ValueError("Missing key/value for setex")
        self.values[name] = data
        if ttl is not None:
            self.expiry[name] = int(ttl)
        return True

    def incr(self, key: str) -> int:
        current = int(self.values.get(key, 0)) + 1
        self.values[key] = current
        return current

    def expire(self, key: str, ttl: int) -> bool:
        self.expiry[key] = ttl
        return True


class DummyJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_redis_with_full_result(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    fake_redis = FakeRedis()
    fake_redis.values["profile:torvalds"] = json.dumps(
        {
            "fingerprint": {
                "username": "torvalds",
                "total_commits_analyzed": 10,
                "repos_analyzed": 2,
                "date_range": "2024-01 to 2024-12",
                "axes": {
                    "shipping_velocity": 7.2,
                    "bugfix_ratio": 3.1,
                    "refactor_habit": 4.0,
                    "test_coverage_signal": 2.2,
                    "architecture_churn": 1.8,
                    "consistency_score": 8.4,
                },
                "top_languages": ["C", "Python"],
                "commit_label_distribution": {
                    "FEATURE": 5,
                    "BUGFIX": 2,
                    "REFACTOR": 1,
                    "TEST": 1,
                    "DOCS": 0,
                    "CHORE": 1,
                    "ARCHITECTURE": 0,
                },
                "peak_activity_year": "2024",
                "style_evolution": "shipping_focused -> quality_focused",
                "raw_axis_values": {
                    "shipping_velocity": 2.16,
                    "bugfix_ratio": 0.31,
                    "refactor_habit": 0.1,
                    "test_coverage_signal": 0.2,
                    "architecture_churn": 0.0,
                    "consistency_cv": 0.16,
                },
            },
            "narrative": "Narrative text.",
            "card_url": "https://cdn.example/cards/token.png",
            "share_token": "token",
            "expires_at": "2030-01-01T00:00:00",
            "cached": True,
        }
    )
    monkeypatch.setattr("app.api.routes.profile._redis_client", lambda: fake_redis)
    return fake_redis


@pytest.fixture
def mock_celery_result(monkeypatch: pytest.MonkeyPatch):
    class FakeAsyncResult:
        status = "SUCCESS"
        result = {
            "fingerprint": {
                "username": "octocat",
                "total_commits_analyzed": 12,
                "repos_analyzed": 3,
                "date_range": "2024-01 to 2024-12",
                "axes": {
                    "shipping_velocity": 5.0,
                    "bugfix_ratio": 4.0,
                    "refactor_habit": 3.0,
                    "test_coverage_signal": 2.0,
                    "architecture_churn": 1.0,
                    "consistency_score": 8.0,
                },
                "top_languages": ["Python"],
                "commit_label_distribution": {
                    "FEATURE": 6,
                    "BUGFIX": 2,
                    "REFACTOR": 2,
                    "TEST": 1,
                    "DOCS": 0,
                    "CHORE": 1,
                    "ARCHITECTURE": 0,
                },
                "peak_activity_year": "2024",
                "style_evolution": "shipping_focused -> shipping_focused",
                "raw_axis_values": {
                    "shipping_velocity": 1.0,
                    "bugfix_ratio": 0.25,
                    "refactor_habit": 0.2,
                    "test_coverage_signal": 0.16,
                    "architecture_churn": 0.0,
                    "consistency_cv": 0.2,
                },
            },
            "narrative": "Narrative",
            "card_url": "https://cdn.example/cards/share.png",
            "share_token": "sharetoken",
            "expires_at": "2030-01-01T00:00:00",
            "cached": False,
        }

    monkeypatch.setattr("app.api.routes.share.AsyncResult", lambda _job_id, app=None: FakeAsyncResult())


def test_post_analyze_enqueues_job(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    fake_redis = FakeRedis()

    monkeypatch.setattr("app.api.routes.profile._redis_client", lambda: fake_redis)

    def fake_delay(username: str, token: str | None, include_private: bool) -> DummyJob:
        assert username == "octocat"
        assert token is None
        assert include_private is False
        return DummyJob("job-123")

    monkeypatch.setattr("app.api.routes.profile.run_analysis.delay", fake_delay)

    response = client.post("/api/analyze", json={"username": "octocat", "include_private": False})

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-123"
    assert response.headers.get("X-Request-ID")


def test_get_status_with_mocked_async_result(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    class FakeResult:
        status = "PROGRESS"
        info = {"progress": 44, "message": "Reading commits"}

    monkeypatch.setattr("app.api.routes.profile.AsyncResult", lambda _job_id, app=None: FakeResult())

    response = client.get("/api/status/job-1")

    assert response.status_code == 200
    assert response.json() == {"status": "PROGRESS", "progress_pct": 44, "message": "Reading commits"}


def test_rate_limit_sixth_request_returns_429(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    fake_redis = FakeRedis()
    monkeypatch.setattr("app.api.routes.profile._redis_client", lambda: fake_redis)
    monkeypatch.setattr("app.api.routes.profile.run_analysis.delay", lambda *_args, **_kwargs: DummyJob("job-ok"))

    payload = {"username": "octocat", "include_private": False}

    for _ in range(5):
        response = client.post("/api/analyze", json=payload)
        assert response.status_code == 200

    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 429
    assert "Daily analysis limit" in response.json()["detail"]


@pytest.mark.parametrize(
    "username, expected_message",
    [
        ("-octocat", "cannot start or end with a hyphen"),
        ("octocat-", "cannot start or end with a hyphen"),
        ("octo cat", "must match"),
        ("admin", "reserved"),
        ("api", "reserved"),
        ("gridpath", "reserved"),
    ],
)
def test_username_validation_invalid_inputs(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    username: str,
    expected_message: str,
) -> None:
    fake_redis = FakeRedis()
    monkeypatch.setattr("app.api.routes.profile._redis_client", lambda: fake_redis)

    response = client.post("/api/analyze", json={"username": username, "include_private": False})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(expected_message in str(item.get("msg", "")) for item in detail)


def test_cached_result_includes_narrative(client: TestClient, mock_redis_with_full_result: FakeRedis) -> None:
    """Cache hit must return narrative, not just fingerprint."""
    response = client.post("/api/analyze", json={"username": "torvalds"})
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "cached"
    assert "narrative" in data["result"]
    assert "card_url" in data["result"]
    assert "share_token" in data["result"]


def test_rate_limit_applies_to_cached_requests(client: TestClient, mock_redis_with_full_result: FakeRedis) -> None:
    """Rate limit counter must increment even when serving from cache."""
    for _ in range(5):
        response = client.post("/api/analyze", json={"username": "torvalds"})
        assert response.status_code == 200

    response = client.post("/api/analyze", json={"username": "torvalds"})
    assert response.status_code == 429


def test_share_url_uses_frontend_origin(client: TestClient, mock_celery_result, monkeypatch: pytest.MonkeyPatch) -> None:
    """Share URL must be built from FRONTEND_URL, not hardcoded domain."""
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:5173")

    response = client.post("/api/share", json={"job_id": "test-job-id"})
    assert response.status_code == 200
    data = response.json()
    assert "github.com/agilap/gridpath" not in data["url"], "URL must not be hardcoded to production domain"
    assert data["url"].startswith(settings.frontend_origin)
    assert "/shared/" in data["url"]
