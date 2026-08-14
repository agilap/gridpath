alter table public.profiles enable row level security;
create policy "Public read" on public.profiles for select using (true);
create policy "Service role write" on public.profiles for all
  using (auth.role() = 'service_role');

alter table public.share_tokens enable row level security;
create policy "Public read" on public.share_tokens for select using (true);
create policy "Service role write" on public.share_tokens for all
  using (auth.role() = 'service_role');
