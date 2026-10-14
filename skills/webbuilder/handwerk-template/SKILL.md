---
name: handwerk-template
description: Premium website template for renovation, Sanierung, plumber and Handwerk companies. Show the full template first, then offer every change.
---

# Renovation template (handwerk-premium)

Sanierung, Umbau, Badsanierung, Maler, Trockenbau, Klempner / plumber and similar trades get the premium renovation template. Show the **complete page** with default starter content as soon as you know the trade — even if they only gave a company name.

Tools: `handwerk_template_overview`, `activate_handwerk_template`, `save_handwerk_section`, `remove_handwerk_section`, `set_site_image`, `record_preview_confirmation`. Hero text, hours, contact, and brand color still go through `update_website_content`.

## When to use

- They renovate homes, bathrooms, interiors, windows; they are a plumber / لوله‌کش / Klempner; or they only named a company in that field.
- Incomplete descriptions still get the **full** template. Do not wait for services, photos, or a long brief.
- If the template is not active, call `activate_handwerk_template` once. That turns on every section with defaults.
- If they chose another look on purpose, respect it.

## First paint (do this)

1. Call `activate_handwerk_template`.
2. Send `https://[slug].easywebbuilder.de`.
3. Explain in their language, in your own words:

> I put the full template online with starter content so you can see every part. You can change any of it. I can change colors, photos, texts, hours, the map, reviews, services, team, projects, and more. I can also remove a section or add one back. Tell me what you want.

4. Proactively list what you can change (from `changeable` on `handwerk_template_overview`). Do not wait for them to guess.
5. Wait for `تایید` / YES, then call `record_preview_confirmation(confirmed=true)`.

## What you can offer (always pitch these)

- Colors of the template
- Photos: logo, hero, services, projects, team, quality, materials
- Company name, phone, email, address, Google map
- Every section: hero, services, guarantees, projects, reviews, quality, team, before/after, financing, process, FAQ, contact, hours, materials, footer
- Remove a part they do not need
- Add a part back
- Replace starter sample text with their real facts

## Personalizing later

Starter sample content is allowed on first paint. When they ask to make a section *theirs*:

1. Write titles and descriptions yourself in German and English: `{"de": "...", "en": "..."}`.
2. Ask for facts you cannot know: real project names, real reviews, phone, address, team names.
3. Never invent extra reviews, ratings, or addresses on top of what they gave.
4. Pictures only from the customer via `set_site_image`.

## Confirm every change

After **every** save:

1. Send the preview URL.
2. Ask them to say `تایید` to approve, or `لغو` to cancel.
3. Only then call `record_preview_confirmation` with `confirmed=true` and a short `summary`.
4. Do not treat the original edit request as approval. Do not record confirmation in the same turn as the edit.

## Delete everything

If they ask to wipe their data: warn that the account, website, and subdomain will be gone and you will not know them afterwards. If they say yes, call `wipe_user_account(confirmed=true)`.

## How to save

`save_handwerk_section(identifier, platform, section, data)`.

Hours, phone, address: `update_website_content`.
Brand color: `update_website_content` with `primary_color` (`#c45c26`).
Remove a section: `remove_handwerk_section`.
Pictures: `set_site_image` (`logo`, `hero`, `quality`, `service`, `project`, `team`, `material`).
