---
name: supabase-onboarding
description: Welcome a Telegram/WhatsApp sender and switch or create their websites.
---

# Websites on easywebbuilder.de

The gateway already searched Supabase. A missing user now has an account and a first website. Do not call a registration tool.

## When to Use

- The lookup says **NEW ACCOUNT**. Welcome them and send the preview link.
- They ask to list sites, switch site, or create another website.
- The lookup says no active website is selected.

## Procedure

1. Read `sender_id` and `platform` from `[easyWebBuilder lookup]`. Never invent them.
2. **NEW ACCOUNT:** greet in the user's language. Send the preview URL from the lookup. Ask for the business name, services, or changes. Stop there.
3. **List or switch:** call `list_user_websites(sender_id, platform)`. Show each business name with `https://[slug].easywebbuilder.de`. After they choose, call `switch_active_website` with the slug or business name and confirm that preview URL.
4. **Another website:** if the current slug is still `site-####` and has no business name, the first name belongs on that site via `update_website_content`, not a second site. If they already have a named site and want another, ask for the new business name, then call `create_website(sender_id, platform, business_name)`.
5. If `create_website` returns `only_one_website`, keep editing the current site and send its preview URL. Do not invent a second link.

Preview links are only `https://[slug].easywebbuilder.de`.
