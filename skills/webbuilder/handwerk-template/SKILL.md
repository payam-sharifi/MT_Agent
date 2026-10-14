---
name: handwerk-template
description: Premium website template for renovation, Sanierung and Handwerk companies in Germany. Activate it, introduce its sections, and fill them with real content.
---

# Renovation template (handwerk-premium)

Sanierung, Umbau, Badsanierung, Maler, Trockenbau and similar German trades get the premium renovation template. It is a complete one-page site. Never publish a half-empty page.

Tools: `handwerk_template_overview`, `activate_handwerk_template`, `save_handwerk_section`, `remove_handwerk_section`. Hero text, hours and contact still go through `update_website_content`.

## When to use

- The lookup says renovation / Sanierung / Handwerk, or the customer says they renovate homes, bathrooms, interiors, windows, or similar in Germany.
- The site does not use the template yet: call `activate_handwerk_template` once. Hero, services, hours and FAQ already saved stay.
- If `handwerk_template_overview` says `template_active: false`, activate it.
- The customer chose another look on purpose: respect it and do not activate.

## The one rule that matters

The template shows a section only when it exists AND has real content.

1. **Section the customer does not want: do not add it.**
2. **Section they want: fill it completely.**
3. **Texts you can write, write them** in German and English: `{"de": "...", "en": "..."}`.
4. **Facts you cannot know, ask.** Project cities, team names, real reviews, phone, address.
5. **Never invent facts.** No made-up projects, Google reviews, ratings, funding percentages or addresses. Do not copy the sample site (VELORA Wohnbau, Hamburg demo numbers).
6. Pictures come only from the customer via `set_site_image`.

## Introduce the template (once, early)

> Your site uses our renovation template. It already has a start page and your services. You can switch on more parts:
> 1. **Guarantees**: fixed price, start date, one project lead
> 2. **Projects**: real completed jobs
> 3. **Reviews**: only quotes the customer actually has
> 4. **Team**: names and roles
> 5. **Before / after**
> 6. **Financing calculator**
> 7. **Process** (consult → 3D offer → start → handover)
> 8. **FAQ** and **contact / locations**
>
> Which would you like?

## How to save

`save_handwerk_section(identifier, platform, section, data)`.

Pictures: logo, hero, service, project, team, before_after, quality — same `set_site_image` flow as the clinic template.

After saving, send `https://[slug].easywebbuilder.de` and ask them to confirm.
