from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.api.deps import get_github_token
from app.config import settings
from app.exceptions import AuthRequiredError

logger = structlog.get_logger(__name__)
router = APIRouter()


def _is_secure(request: Request) -> bool:
    return request.url.scheme == "https" or settings.ENV == "production"


def _cookie_params(request: Request) -> dict:
    if settings.ENV == "production":
        return {"samesite": "none", "secure": True}
    return {"samesite": "lax", "secure": _is_secure(request)}


def _get_serializer() -> URLSafeTimedSerializer:
    secret = settings.SECRET_KEY or settings.CARD_SIGN_SECRET
    return URLSafeTimedSerializer(secret_key=secret)


def _build_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "repo read:user",
        "state": state,
    }
    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


def _clear_session_cookie(response: Response, request: Request) -> None:
    p = _cookie_params(request)
    response.delete_cookie("gh_session", path="/", secure=p["secure"], httponly=True, samesite=p["samesite"])


def _frontend_redirect(success: bool, reason: str | None = None) -> RedirectResponse:
    if success:
        return RedirectResponse(url=f"{settings.frontend_origin}/?auth=success", status_code=307)

    suffix = f"&reason={reason}" if reason else ""
    return RedirectResponse(url=f"{settings.frontend_origin}/?auth=error{suffix}", status_code=307)


@router.get("/github")
async def github_login(request: Request) -> RedirectResponse:
    serializer = _get_serializer()
    raw_state = secrets.token_urlsafe(32)
    signed_state = serializer.dumps(raw_state, salt="gh-oauth-state")
    authorize_url = _build_authorize_url(signed_state)

    response = RedirectResponse(url=authorize_url, status_code=307)
    p = _cookie_params(request)
    response.set_cookie(
        key="gh_oauth_state",
        value=signed_state,
        httponly=True,
        secure=p["secure"],
        samesite=p["samesite"],
        max_age=600,
        path="/",
    )
    return response


@router.get("/callback")
async def github_callback(request: Request, code: str | None = None, state: str | None = None) -> RedirectResponse:
    if not code or not state:
        logger.warning("oauth_callback_missing_params")
        return _frontend_redirect(False, "missing_params")

    state_cookie = request.cookies.get("gh_oauth_state")
    serializer = _get_serializer()

    try:
        serializer.loads(state, salt="gh-oauth-state", max_age=600)
    except BadSignature:
        logger.warning("oauth_callback_invalid_state_signature")
        return _frontend_redirect(False, "invalid_state")

    if not state_cookie or state_cookie != state:
        logger.warning("oauth_callback_state_mismatch")
        return _frontend_redirect(False, "state_mismatch")

    payload = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data=payload,
            headers={"Accept": "application/json"},
        )

    if token_response.status_code >= 400:
        logger.error(
            "oauth_token_exchange_failed",
            status_code=token_response.status_code,
            body=token_response.text,
        )
        return _frontend_redirect(False, "token_exchange_failed")

    token_data: dict[str, Any] = token_response.json()
    access_token = token_data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        logger.error("oauth_token_missing")
        return _frontend_redirect(False, "token_missing")

    encrypted_token = serializer.dumps(access_token, salt="gh-session")

    p = _cookie_params(request)
    response = _frontend_redirect(True)
    response.delete_cookie("gh_oauth_state", path="/", secure=p["secure"], httponly=True, samesite=p["samesite"])
    response.set_cookie(
        key="gh_session",
        value=encrypted_token,
        httponly=True,
        secure=p["secure"],
        samesite=p["samesite"],
        max_age=86400,
        path="/",
    )
    return response


@router.get("/status")
async def auth_status(request: Request) -> JSONResponse:
    token = get_github_token(request)
    if not token:
        return JSONResponse({"authenticated": False, "username": None, "avatar_url": None})

    async with httpx.AsyncClient(timeout=15.0) as client:
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )

    if user_response.status_code >= 400:
        logger.warning("auth_status_user_lookup_failed", status_code=user_response.status_code)
        response = JSONResponse({"authenticated": False, "username": None, "avatar_url": None})
        _clear_session_cookie(response, request)
        return response

    user_data: dict[str, Any] = user_response.json()
    username = user_data.get("login")
    avatar_url = user_data.get("avatar_url")

    return JSONResponse(
        {
            "authenticated": True,
            "username": username if isinstance(username, str) else None,
            "avatar_url": avatar_url if isinstance(avatar_url, str) else None,
        }
    )


@router.post("/logout")
async def auth_logout(request: Request) -> JSONResponse:
    p = _cookie_params(request)
    response = JSONResponse({"ok": True})
    _clear_session_cookie(response, request)
    response.delete_cookie("gh_oauth_state", path="/", secure=p["secure"], httponly=True, samesite=p["samesite"])
    return response


def require_github_token(request: Request) -> str:
    token = get_github_token(request)
    if not token:
        raise AuthRequiredError("GitHub authentication required")
    return token
