from __future__ import annotations

import json
from typing import Any

import httpx
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.deps import get_github_token
from app.celery_app import celery_app
from app.config import settings
from app.db.redis_client import get_redis
from app.exceptions import AuthRequiredError, RateLimitError
from app.models.profile import AnalyzeRequest, AnalyzeResponse, AnalysisResult, StatusResponse
from app.tasks.analyze import run_analysis

router = APIRouter()


def _redis_client() -> Any:
    return get_redis()


def _enforce_rate_limit(r: Any, client_ip: str) -> None:
    key = f"ratelimit:{client_ip}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, 86400)
    if count > settings.ANALYSIS_DAILY_LIMIT_PER_USER:
        raise RateLimitError("Daily analysis limit reached")


async def _get_github_login(token: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            )
            if resp.status_code == 200:
                login = resp.json().get("login")
                return login if isinstance(login, str) else None
    except Exception:
        pass
    return None


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: Request, body: AnalyzeRequest, token: str | None = Depends(get_github_token)) -> AnalyzeResponse:
    if body.include_private and not token:
        raise AuthRequiredError("GitHub authentication required for private repositories")

    # include_private is only valid when the token owner matches the requested username.
    # Analyzing someone else's username with private=True would fetch the token owner's
    # own repos (via /user/repos) and attribute them to the wrong person.
    include_private = False
    if body.include_private and token:
        authed_login = await _get_github_login(token)
        if authed_login and authed_login.lower() == body.username.lower():
            include_private = True

    r = _redis_client()

    # Never serve cached results for private analyses — the cache key is username-only
    # and a private run's data must not be visible to other users.
    if not include_private:
        cached_raw = r.get(f"profile:{body.username}")
        if cached_raw:
            cached_text = cached_raw.decode("utf-8") if isinstance(cached_raw, bytes) else str(cached_raw)
            full_result = AnalysisResult.model_validate(json.loads(cached_text))
            return AnalyzeResponse(
                job_id="cached",
                status="SUCCESS",
                result=full_result,
                estimated_seconds=0,
            )

    # Rate limit only applies to actual job enqueues, not cache hits.
    client_ip = request.client.host if request.client else "unknown"
    try:
        _enforce_rate_limit(r, client_ip)
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    job = run_analysis.delay(body.username, token, include_private)
    return AnalyzeResponse(job_id=job.id, estimated_seconds=90, status="PENDING")


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str) -> StatusResponse:
    result = AsyncResult(job_id, app=celery_app)
    try:
        info = result.info
        if isinstance(info, dict):
            meta = info
        elif info is not None:
            meta = {"message": str(info)}
        else:
            meta = {}
    except Exception:
        # Transient backend error (Redis blip, serialisation issue). Return PENDING
        # so the frontend keeps polling rather than aborting a healthy job.
        return StatusResponse(
            status="PENDING",
            progress_pct=0,
            message="Waiting for task status…",
        )
    return StatusResponse(
        status=result.status,
        progress_pct=int(meta.get("progress", 0)),
        message=str(meta.get("message", "")),
    )


@router.get("/result/{job_id}")
async def get_result(job_id: str) -> Any:
    result = AsyncResult(job_id, app=celery_app)

    if result.status == "SUCCESS":
        return result.result

    if result.status == "PROGRESS":
        meta = result.info if isinstance(result.info, dict) else {}
        return JSONResponse(
            status_code=202,
            content={
                "status": "PROGRESS",
                "progress_pct": int(meta.get("progress", 0)),
                "message": str(meta.get("message", "")),
            },
        )

    if result.status == "FAILURE":
        raise HTTPException(status_code=404, detail="Analysis failed")

    return JSONResponse(
        status_code=202,
        content={"status": result.status, "progress_pct": 0, "message": "Queued"},
    )
