from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv


def _mask_value(value: str) -> str:
    if len(value) <= 20:
        return value
    return f"{value[:20]}..."


def _parse_required_keys(env_example_path: Path) -> list[str]:
    keys: list[str] = []
    pattern = re.compile(r"^([A-Z0-9_]+)=(.*)$")
    for raw_line in env_example_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = pattern.match(line)
        if not match:
            continue
        keys.append(match.group(1))
    return keys


def _find_env_file(project_root: Path) -> Path | None:
    search_order = [
        project_root / "backend" / ".env",
        project_root / ".env",
        Path("backend/.env"),
        Path(".env"),
    ]

    for candidate in search_order:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


def _print_env_status(required_keys: list[str]) -> None:
    print("\n=== ENV VARIABLES ===")
    for key in required_keys:
        value = os.environ.get(key)
        if value is None:
            print(f"❌  {key} = NOT SET")
        elif value == "":
            print(f"⚠️  {key} = EMPTY STRING")
        else:
            print(f"✅  {key} = {_mask_value(value)}")


def _test_redis() -> None:
    print("\n=== REDIS TEST ===")
    url = os.environ.get("UPSTASH_REDIS_URL", "")
    if not url:
        print("❌ UPSTASH_REDIS_URL not set — skipping")
        return

    try:
        import redis as redis_lib
        r = redis_lib.from_url(
            url,
            ssl_cert_reqs=None,
            socket_connect_timeout=5,
        )
        r.ping()
        print("✅ Redis connection: OK")
    except Exception as e:  # noqa: BLE001
        print(f"❌ Redis connection FAILED: {e}")
        if not url.startswith("rediss://"):
            print("   ⚠️  URL must start with rediss:// for Upstash")
        if "rediss://:password" in url:
            print("   ⚠️  Missing username — use rediss://default:password@host")


def _test_supabase() -> None:
    print("\n=== SUPABASE TEST ===")
    supa_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not supa_url or not service_key:
        print("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set — skipping")
        return

    try:
        from supabase import create_client

        sb = create_client(supa_url, service_key)
        sb.table("profiles").select("id").limit(1).execute()
        print("✅ Supabase connection: OK")
        print("✅ profiles table: EXISTS")
    except Exception as e:  # noqa: BLE001
        err = str(e)
        print(f"❌ Supabase connection FAILED: {err}")
        if "profiles" in err and "does not exist" in err:
            print("   ⚠️  Table missing — run: python setup_supabase.py")
        if "Invalid API key" in err:
            print("   ⚠️  SUPABASE_SERVICE_ROLE_KEY is wrong — check Supabase dashboard → Settings → API")
        if service_key == anon_key:
            print("   ⚠️  SERVICE_ROLE_KEY and ANON_KEY are identical — you pasted the wrong key")


def _test_supabase_direct_db() -> None:
    print("\n=== SUPABASE DB DIRECT TEST ===")
    db_url = os.environ.get("SUPABASE_DB_URL", "")
    if not db_url:
        print("⚠️  SUPABASE_DB_URL not set — skipping direct DB test")
        return

    try:
        import psycopg2

        conn = psycopg2.connect(db_url, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        tables = [r[0] for r in cur.fetchall()]
        print("✅ Direct DB connection: OK")
        print(f"   Tables: {tables}")
        if "profiles" not in tables:
            print("   ⚠️  profiles table missing — run: python setup_supabase.py")
        if "share_tokens" not in tables:
            print("   ⚠️  share_tokens table missing — run: python setup_supabase.py")
        conn.close()
    except Exception as e:  # noqa: BLE001
        print(f"❌ Direct DB FAILED: {e}")


def _test_openai() -> None:
    print("\n=== OPENAI TEST ===")
    oai_key = os.environ.get("OPENAI_API_KEY", "")
    if not oai_key:
        print("❌ OPENAI_API_KEY not set — skipping")
    elif not oai_key.startswith("sk-"):
        print(f"⚠️  OPENAI_API_KEY doesn't start with sk- — value: {oai_key[:10]}...")
    else:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=oai_key)
            client.models.list()
            print("✅ OpenAI connection: OK")
        except Exception as e:  # noqa: BLE001
            print(f"❌ OpenAI FAILED: {e}")


def _test_github_oauth() -> None:
    print("\n=== GITHUB OAUTH TEST ===")
    gh_id = os.environ.get("GITHUB_CLIENT_ID", "")
    gh_secret = os.environ.get("GITHUB_CLIENT_SECRET", "")
    gh_redirect = os.environ.get("GITHUB_REDIRECT_URI", "")

    if not gh_id or not gh_secret:
        print("❌ GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET not set")
    else:
        print("✅ GitHub OAuth vars: set")
        print(f"   CLIENT_ID: {gh_id[:8]}...")
        print(f"   REDIRECT_URI: {gh_redirect}")
        if not gh_redirect:
            print("   ⚠️  GITHUB_REDIRECT_URI is empty")
        if "localhost" not in gh_redirect and "https" not in gh_redirect:
            print("   ⚠️  REDIRECT_URI looks wrong — should be http://localhost:8000/api/auth/callback")


def _test_secret_keys() -> None:
    print("\n=== SECRET KEYS TEST ===")
    secret_key = os.environ.get("SECRET_KEY", "")
    card_sign_secret = os.environ.get("CARD_SIGN_SECRET", "")

    if not secret_key:
        print("❌ SECRET_KEY not set")
    elif len(secret_key) < 32:
        print("⚠️  SECRET_KEY is short — use at least 32 chars")
    else:
        print("✅ SECRET_KEY: set")

    if not card_sign_secret:
        print("❌ CARD_SIGN_SECRET not set")
    elif len(card_sign_secret) < 32:
        print("⚠️  CARD_SIGN_SECRET is short — use at least 32 chars")
    else:
        print("✅ CARD_SIGN_SECRET: set")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env_example_path = project_root / ".env.example"

    if not env_example_path.exists():
        print(f"❌ Could not find required template: {env_example_path}")
        raise SystemExit(1)

    required_keys = _parse_required_keys(env_example_path)
    found_env = _find_env_file(project_root)

    print("=== ENV SOURCE ===")
    if found_env is None:
        print("❌ No .env file found in expected locations")
        print("   Searched: backend/.env, .env at project root, backend/.env (cwd), .env (cwd)")
        raise SystemExit(1)

    print(f"✅ Found .env file: {found_env}")
    load_dotenv(dotenv_path=found_env, override=True)

    _print_env_status(required_keys)
    _test_redis()
    _test_supabase()
    _test_supabase_direct_db()
    _test_openai()
    _test_github_oauth()
    _test_secret_keys()


if __name__ == "__main__":
    main()
