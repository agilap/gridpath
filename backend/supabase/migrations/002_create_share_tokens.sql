create table public.share_tokens (
  token       text primary key,
  username    text references public.profiles(username),
  card_url    text not null,
  created_at  timestamptz default now(),
  expires_at  timestamptz not null
);
create index on public.share_tokens (expires_at);
