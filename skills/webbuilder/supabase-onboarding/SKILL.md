---
name: supabase-onboarding
description: Look up Telegram/WhatsApp users in Supabase, then register if new.
---

# Supabase Onboarding

Every Telegram/WhatsApp turn already searches `public.users` by `telegram_id` or `phone`.
If the current message says **NOT FOUND**, start registration. Do not wait.

## When to Use

- Telegram/WhatsApp chat.
- The lookup prefix or `lookup_user` tool says `found=false`.
- Don't use for later content edits (`update-website` / `update_website_data`).

## Procedure

1. Trust the inbound lookup (`[easyWebBuilder lookup] ...`). You may also call `lookup_user(sender_id, platform)`.
2. If **FOUND**: skip onboarding, help with their site.
3. If **NOT FOUND**:
   - Greet in the user's language.
   - Ask for business/website name (`business_name`), owner full name (`owner_name`), and type of activity.
   - Suggest a `subdomain` (lowercase ASCII, hyphens) and confirm it.
   - Call `check_and_register_user(sender_id, platform, business_name, owner_name, subdomain)`.
   - Infer `theme` from the business name / activity (`clinical`, `luxury`, `zen`, `corporate`, or `default`) and call `update_website_data` with `{ "theme": "..." }` on the root of `site_data`.
4. Confirm registration in chat.

Use `sender_id` and `platform` from the lookup line. Never invent them.
Do not register on the greeting turn before you have the three business fields.
