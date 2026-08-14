create table public.profiles (
  id             uuid primary key default gen_random_uuid(),
  username       text not null unique,
  fingerprint    jsonb not null,
  narrative      text not null,
  analyzed_at    timestamptz default now(),
  repos_count    int,
  commits_count  int,
  top_languages  text[]
);
create index on public.profiles (username);
