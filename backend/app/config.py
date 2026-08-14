from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    FRONTEND_URL: str = "http://localhost:5173"
    # Comma-separated origins allowed, e.g. "http://localhost:5173,https://github.com/agilap/gridpath"

    API_BASE_URL: str = ""
    # Public base URL of this API (e.g. https://api.railway.app). Used to build OG share URLs.
    # Leave empty in dev — falls back to frontend-domain share URLs.

    ENV: str = "development"
    # Set to "production" in Railway

    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:8001/api/auth/callback"
    GITHUB_API_TOKEN: str = ""

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_DB_URL: str = ""
    SUPABASE_STORAGE_BUCKET: str = "cards"

    UPSTASH_REDIS_URL: str = ""

    SECRET_KEY: str = ""
    CARD_SIGN_SECRET: str = ""

    GITHUB_API_MAX_COMMITS_PER_REPO: int = 500
    GITHUB_API_MAX_REPOS: int = 30
    CELERY_CONCURRENCY: int = 4
    PROFILE_CACHE_TTL_SECONDS: int = 86400
    ANALYSIS_DAILY_LIMIT_PER_USER: int = 5

    @property
    def frontend_origin(self) -> str:
        """Returns the first origin from FRONTEND_URL for use in redirects."""
        return self.FRONTEND_URL.split(",")[0].strip().rstrip("/")

    @property
    def og_base_url(self) -> str:
        """Base URL for constructing OG share links (backend URL if set, else frontend)."""
        if self.API_BASE_URL:
            return self.API_BASE_URL.rstrip("/")
        return self.frontend_origin


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
