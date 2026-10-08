-- Public bucket for customer pictures (logo, hero, services, doctors, ...).
-- Run once in the Supabase SQL editor.
--
-- Anyone may READ (the websites are public). The Hermes agent uploads with the
-- publishable (anon) key, so INSERT is allowed for anon. There is no UPDATE or DELETE
-- policy: files cannot be overwritten or removed with that key. The bucket itself
-- restricts size (5 MB) and type (JPG, PNG, WebP).

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('site-images', 'site-images', true, 5242880, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update
  set public = true,
      file_size_limit = 5242880,
      allowed_mime_types = array['image/jpeg', 'image/png', 'image/webp'];

drop policy if exists "site-images public read" on storage.objects;
create policy "site-images public read"
  on storage.objects for select
  using (bucket_id = 'site-images');

drop policy if exists "site-images anon upload" on storage.objects;
create policy "site-images anon upload"
  on storage.objects for insert
  to anon, authenticated
  with check (bucket_id = 'site-images');
