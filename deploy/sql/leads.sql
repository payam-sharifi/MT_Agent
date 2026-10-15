-- Paste this in Supabase → SQL Editor → Run.
-- Stores each contact/quote/booking message for the business user + their website.

create table if not exists public.leads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  website_id uuid references public.websites (id) on delete set null,
  kind text not null,
  fields jsonb not null default '{}'::jsonb,
  message text not null,
  channels text[] not null default '{}'::text[],
  locale text,
  created_at timestamptz not null default now()
);

create index if not exists leads_user_id_created_at_idx
  on public.leads (user_id, created_at desc);

create index if not exists leads_website_id_created_at_idx
  on public.leads (website_id, created_at desc);

alter table public.leads enable row level security;

drop policy if exists "leads insert" on public.leads;
create policy "leads insert"
  on public.leads for insert
  to anon, authenticated
  with check (true);

drop policy if exists "leads select" on public.leads;
create policy "leads select"
  on public.leads for select
  to anon, authenticated
  using (true);
