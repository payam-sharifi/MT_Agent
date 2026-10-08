---
name: update-website
description: Update the active website content and Impressum in Supabase.
---

# Update the active website

For a sender who already has a website, save edits with `update_website_content`. Legal details use `update_legal_impressum`. The live page is `https://[slug].easywebbuilder.de`.

## When to Use

- The lookup says **FOUND** and an active website is set.
- They give a business name, hero text, services, prices, hours, FAQ, contact details, or a look/theme.
- They give owner name, address, tax ID / USt-IdNr, or legal form.

Do not use this to create an additional website (`create_website`).

## content shape

Pass only the fields they changed. The tool merges. Services merge by `name`. FAQ items merge by `question`.

```json
{
  "hero": { "title": "", "subtitle": "", "cta_button": "" },
  "services": [{ "name": "", "price": "", "description": "" }],
  "contact": { "address": "", "phone": "", "opening_hours": "" },
  "faq": [{ "question": "", "answer": "" }]
}
```

`business_name` is a separate argument. On a placeholder slug (`site-1234`) it also sets the public slug. An existing named slug stays put.

## Procedure

1. Take `identifier` and `platform` from the lookup (`sender_id`, `telegram` or `whatsapp`). Never invent them.
2. If the lookup says to choose a website first, do that before any save.
3. Call `update_website_content(identifier, platform, content, business_name)`.
4. For legal details, call `update_legal_impressum(sender_id, platform, owner_name, address, tax_number, legal_form)` with only the fields they gave.
5. If `status` is `success`, reply in the user's language with the tool's `preview_url` and ask them to confirm. If `error`, say it was not saved.

## Mapping

| User says | Call |
|---|---|
| Business name on the current site | `business_name`, and `content.hero.title` when they are naming the page |
| Headline, subtitle, button | `content.hero` |
| Price or service | `content.services` item `{name, price, description}` |
| Address, phone | `content.contact` |
| Opening hours | `content.contact.opening_hours` |
| FAQ | `content.faq` item `{question, answer}` |
| A photo or image link, a logo | `set_site_image` (skill clinic-template, Pictures) |
| Owner, address, tax ID, legal form | `update_legal_impressum` |
| Look or color | `theme`: `luxury` (beauty, dark, gold), `zen` (spa, massage), `corporate` (formal), `default` (otherwise). Doctors, dentists and clinics use the premium clinic template: `clinic-premium` (see the clinic-template skill; it is set automatically for medical sites) |
| Doctors, check-up packages, about us, locations, extra FAQ on a clinic site | `save_clinic_section` (skill clinic-template) |

## Clinic sites

If the site is for a doctor, dentist or clinic, follow the `clinic-template` skill. Introduce the optional template sections to the customer, add only the ones they choose, fill them fully, and never invent facts.
