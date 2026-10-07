-- Multiple websites per user, and a pointer to the one being edited.
-- Apply in the Supabase SQL editor. The publishable API key cannot run DDL.
-- Until this is applied, websites.user_id stays unique and each user has one site.

alter table public.users
  add column if not exists active_website_id uuid;

alter table public.websites
  drop constraint if exists websites_user_id_key;

update public.websites
set slug = subdomain
where coalesce(slug, '') = ''
  and coalesce(subdomain, '') <> '';

create unique index if not exists websites_slug_key
  on public.websites (slug);

alter table public.users
  drop constraint if exists users_active_website_id_fkey;

alter table public.users
  add constraint users_active_website_id_fkey
  foreign key (active_website_id) references public.websites (id)
  on delete set null;

update public.users as account
set active_website_id = website.id
from public.websites as website
where website.user_id = account.id
  and account.active_website_id is null;
