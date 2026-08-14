from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.api.routes.auth import _get_serializer
from app.config import settings
from app.main import app


def _configure_oauth_settings() -> None:
    settings.GITHUB_CLIENT_ID = "test-client-id"
    settings.GITHUB_CLIENT_SECRET = "test-client-secret"
    settings.GITHUB_REDIRECT_URI = "http://localhost:8000/api/auth/callback"
    settings.SECRET_KEY = "test-secret-key"
    settings.CARD_SIGN_SECRET = "test-card-sign-secret"
    settings.FRONTEND_URL = "http://localhost:5173"
    settings.ENV = "development"


@pytest.fixture
def client() -> TestClient:
    _configure_oauth_settings()
    return TestClient(app, base_url="http://testserver")


@pytest.fixture
def https_client() -> TestClient:
    _configure_oauth_settings()
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def mock_github(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://github.com/login/oauth/access_token",
        json={"access_token": "gho_test_token", "token_type": "bearer"},
    )
    return httpx_mock


def _login_and_get_state(client: TestClient) -> str:
    login_response = client.get("/api/auth/github", follow_redirects=False)
    location = login_response.headers["location"]
    return parse_qs(urlparse(location).query)["state"][0]


def test_github_login_redirect_sets_signed_state_cookie(client: TestClient) -> None:
    response = client.get("/api/auth/github", follow_redirects=False)

    assert response.status_code == 307
    assert "gh_oauth_state" in response.cookies

    location = response.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "github.com"
    assert parsed.path == "/login/oauth/authorize"
    assert query["client_id"] == [settings.GITHUB_CLIENT_ID]
    assert query["redirect_uri"] == [settings.GITHUB_REDIRECT_URI]
    assert query["scope"] == ["repo read:user"]

    signed_state = query["state"][0]
    serializer = _get_serializer()
    decoded_state = serializer.loads(signed_state, salt="gh-oauth-state")
    assert isinstance(decoded_state, str)
    assert len(decoded_state) > 10


def test_callback_exchanges_code_and_sets_session_cookie(client: TestClient, mock_github) -> None:
    state = _login_and_get_state(client)

    callback_response = client.get(
        "/api/auth/callback",
        params={"code": "test-code", "state": state},
        follow_redirects=False,
    )

    assert callback_response.status_code == 307
    assert callback_response.headers["location"].startswith("http://localhost:5173/?auth=success")
    assert "gh_session" in callback_response.cookies


def test_callback_redirects_to_absolute_frontend_url(client: TestClient, mock_github) -> None:
    """Redirect must be absolute using FRONTEND_URL, not a relative path."""
    state = _login_and_get_state(client)
    response = client.get(
        "/api/auth/callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )
    location = response.headers.get("location", "")
    assert location.startswith("http"), f"Redirect must be absolute, got: {location}"
    assert "localhost:5173" in location or "github.com/agilap/gridpath" in location


def test_cookie_not_secure_on_http_localhost(client: TestClient, mock_github) -> None:
    """Cookie secure flag must be False when scheme is http."""
    state = _login_and_get_state(client)
    response = client.get(
        "/api/auth/callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )
    for header_val in response.headers.get_list("set-cookie"):
        if "gh_session" in header_val:
            assert "secure" not in header_val.lower(), "Cookie must not be secure on http"


def test_cookie_secure_on_https(https_client: TestClient, mock_github) -> None:
    """Cookie secure flag must be True when scheme is https."""
    state = _login_and_get_state(https_client)
    response = https_client.get(
        "/api/auth/callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )
    for header_val in response.headers.get_list("set-cookie"):
        if "gh_session" in header_val:
            assert "secure" in header_val.lower(), "Cookie must be secure on https"


def test_auth_status_returns_false_when_no_cookie(client: TestClient) -> None:
    response = client.get("/api/auth/status")

    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "username": None, "avatar_url": None}


def test_auth_status_returns_user_when_cookie_valid(client: TestClient, httpx_mock) -> None:
    serializer = _get_serializer()
    encrypted = serializer.dumps("gho_valid_token", salt="gh-session")
    client.cookies.set("gh_session", encrypted)

    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/user",
        json={"login": "octocat", "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4"},
    )

    response = client.get("/api/auth/status")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "username": "octocat",
        "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
    }


def test_logout_clears_session_cookie(client: TestClient) -> None:
    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert "gh_session=" in response.headers.get("set-cookie", "")
