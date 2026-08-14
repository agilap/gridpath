from __future__ import annotations

import psycopg2

from app.config import settings

SQL_MIGRATIONS = """
-- 001 profiles
CREATE TABLE IF NOT EXISTS public.profiles (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username       text NOT NULL UNIQUE,
  fingerprint    jsonb NOT NULL,
  narrative      text NOT NULL,
  analyzed_at    timestamptz DEFAULT now(),
  repos_count    int,
  commits_count  int,
  top_languages  text[]
);
CREATE INDEX IF NOT EXISTS profiles_username_idx ON public.profiles (username);
CREATE INDEX IF NOT EXISTS profiles_analyzed_at_idx ON public.profiles (analyzed_at DESC);

-- 002 share_tokens
CREATE TABLE IF NOT EXISTS public.share_tokens (
  token       text PRIMARY KEY,
  username    text REFERENCES public.profiles(username),
  card_url    text NOT NULL,
  created_at  timestamptz DEFAULT now(),
  expires_at  timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS share_tokens_expires_at_idx ON public.share_tokens (expires_at);

-- 003 RLS policies
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read profiles" ON public.profiles;
CREATE POLICY "Public read profiles"
  ON public.profiles FOR SELECT USING (true);
DROP POLICY IF EXISTS "Service role write profiles" ON public.profiles;
CREATE POLICY "Service role write profiles"
  ON public.profiles FOR ALL USING (auth.role() = 'service_role');

ALTER TABLE public.share_tokens ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read share_tokens" ON public.share_tokens;
CREATE POLICY "Public read share_tokens"
  ON public.share_tokens FOR SELECT USING (true);
DROP POLICY IF EXISTS "Service role write share_tokens" ON public.share_tokens;
CREATE POLICY "Service role write share_tokens"
  ON public.share_tokens FOR ALL USING (auth.role() = 'service_role');
"""


def run_migrations() -> None:
    print("Connecting to Supabase PostgreSQL...")
    conn = psycopg2.connect(settings.SUPABASE_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    print("Running migrations...")
    cur.execute(SQL_MIGRATIONS)
    print("✅ Tables and RLS policies created successfully")

    # Verify
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    tables = [row[0] for row in cur.fetchall()]
    print(f"   Tables found: {tables}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    run_migrations()

# HOW TO RUN:
# 1. Add SUPABASE_DB_URL to your backend/.env
#    Get it from: Supabase dashboard → Settings → Database → Connection string → URI
#    It looks like: postgresql://postgres:yourpassword@db.abc123.supabase.co:5432/postgres
#
# 2. pip install psycopg2-binary
#
# 3. python setup_supabase.py
#    → Creates both tables + RLS policies
#
# 4. In terminal 1: uvicorn app.main:app --reload --port 8000
# 5. In terminal 2: celery -A app.celery_app worker --loglevel=info
# 6. curl http://localhost:8000/health
#    → Should return: {"status":"ok","redis":true,"postgres":true,"celery":true,"version":"0.1.0"}
