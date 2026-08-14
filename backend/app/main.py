import uuid

import structlog
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.api.routes.auth import router as auth_router
from app.api.routes.profile import router as profile_router
from app.api.routes.share import router as share_router
from app.config import settings
from app.exceptions import AuthRequiredError

app = FastAPI(title="gridpath API", version="0.1.0")
logger = structlog.get_logger(__name__)


def _allowed_origins() -> list[str]:
    origins = [origin.strip() for origin in settings.FRONTEND_URL.split(",") if origin.strip()]
    return origins or ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    bind_contextvars(request_id=request_id)
    try:
        response = await call_next(request)
    finally:
        clear_contextvars()
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(AuthRequiredError)
async def auth_required_exception_handler(_: Request, exc: AuthRequiredError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception("unhandled_exception", request_id=request_id, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(profile_router, prefix="/api", tags=["profile"])
app.include_router(share_router, prefix="/api", tags=["share"])


@app.get("/health")
async def health():
    status = {
        "status": "ok",
        "redis": False,
        "postgres": False,
        "celery": False,
        "version": "0.1.0"
    }

    # Redis check
    try:
        from app.db.redis_client import get_redis
        r = get_redis()
        r.ping()
        status["redis"] = True
    except Exception as e:
        import structlog
        structlog.get_logger().warning("health_redis_fail", error=str(e))

    # Supabase / postgres check
    try:
        from app.db.supabase_client import get_supabase
        sb = get_supabase()
        sb.table("profiles").select("id").limit(1).execute()
        status["postgres"] = True
    except Exception as e:
        import structlog
        structlog.get_logger().warning("health_postgres_fail", error=str(e))

    # Celery check
    try:
        from app.celery_app import celery_app
        insp = celery_app.control.inspect(timeout=2.0)
        workers = insp.ping()
        status["celery"] = bool(workers)
    except Exception as e:
        import structlog
        structlog.get_logger().warning("health_celery_fail", error=str(e))

    return status
