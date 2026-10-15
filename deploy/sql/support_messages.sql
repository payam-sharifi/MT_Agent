-- Paste this in Supabase → SQL Editor → Run.
-- Two-way support chat between the admin dashboard and Telegram/WhatsApp users.

create table if not exists public.support_messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  website_id uuid references public.websites (id) on delete set null,
  sender text not null check (sender in ('admin', 'user')),
  body text not null,
  channels text[] not null default '{}'::text[],
  platform text,
  created_at timestamptz not null default now()
);

create index if not exists support_messages_user_id_created_at_idx
  on public.support_messages (user_id, created_at desc);

alter table public.support_messages enable row level security;

drop policy if exists "support_messages insert" on public.support_messages;
create policy "support_messages insert"
  on public.support_messages for insert
  to anon, authenticated
  with check (true);

drop policy if exists "support_messages select" on public.support_messages;
create policy "support_messages select"
  on public.support_messages for select
  to anon, authenticated
  using (true);
