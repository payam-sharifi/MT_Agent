---
name: website-leads
description: Read visitor contact-form messages (Anfragen, پیام فرم تماس, leads) stored in Supabase for this business owner. Use when they ask who wrote, new enquiries, or form submissions.
---

# Website contact-form leads

The website backend already pushes every form submit to this owner’s Telegram or WhatsApp **immediately** (same bot chat they use with Hermes). Hermes does not send that visitor message again. This tool is only if they later ask to list or reread those Anfragen.

Tool: `list_website_leads`.

## When to use

Call the tool when they ask things like:

- "پیام جدید دارم؟" / "کسی فرم پر کرده؟" / "آخرین درخواست"
- "Anfragen" / "wer hat geschrieben" / "neue Nachricht vom Formular"
- "leads" / "contact form" / "who contacted me"

Do **not** treat a visitor lead as a request to edit the website. Do **not** call `update_website_content` for these.

## Procedure

1. Read `sender_id` and `platform` from `[easyWebBuilder lookup]`. Never invent them.
2. Call `list_website_leads(sender_id, platform)`. Optionally pass `slug` if they named a site, and `limit` if they asked for more.
3. If `count` is 0, say there are no form messages yet.
4. Otherwise reply in their language with the newest first. For each lead include:
   - name
   - phone
   - email
   - message
   - when (`created_at`)
   - which site (`business_name` / `website_slug`) when they have more than one
5. They can call or email the visitor themselves. Hermes cannot message the visitor.

## Example

```
User: پیام جدید از سایتم دارم؟
→ list_website_leads(sender_id, platform)
→ "بله، یک درخواست تماس:
   Anna Meier
   +49 170 …
   anna@…
   Bad in Harvestehude sanieren
   امروز 12:03"
```
