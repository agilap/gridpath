from itsdangerous import BadSignature, URLSafeTimedSerializer
from fastapi import Request

from app.config import settings


def _get_serializer() -> URLSafeTimedSerializer:
    # Separate salt scopes token signatures so state and session cookies cannot be swapped.
    return URLSafeTimedSerializer(secret_key=settings.SECRET_KEY or settings.CARD_SIGN_SECRET)


def get_github_token(request: Request) -> str | None:
    cookie_value = request.cookies.get("gh_session")
    if not cookie_value:
        return None

    serializer = _get_serializer()
    try:
        token = serializer.loads(cookie_value, salt="gh-session")
    except BadSignature:
        return None

    if not isinstance(token, str) or not token:
        return None

    return token
