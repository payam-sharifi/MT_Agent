---
name: clinic-template
description: Premium website template for doctors, dentists and clinics. Activate it, introduce its sections to the customer, and fill them with real content.
---

# Clinic template (clinic-premium)

Doctors, dentists, physiotherapists and clinics get the premium clinic template. It is a complete, polished one-page site. Your job is to make it look finished: never publish a half-empty or placeholder-looking page.

Tools: `clinic_template_overview`, `activate_clinic_template`, `save_clinic_section`, `remove_clinic_section`. Hero text, hours and contact still go through `update_website_content`.

## When to use

- The lookup line says the site is a doctor/clinic site, or the customer says they are a doctor, dentist, clinic, practice, physio, or similar.
- The site does not use the template yet: call `activate_clinic_template` once. Hero, services, hours and FAQ already saved stay.
- New clinic sites are switched to the template automatically when the business type is known. If `clinic_template_overview` says `template_active: false`, activate it.
- The customer chose another look (luxury, zen, ...) on purpose: respect it and do not activate.

## The one rule that matters

The template shows a section only when it exists AND has real content. So:

1. **Section the customer does not want or never mentioned: do not add it.** The site simply looks shorter and still clean.
2. **Section the customer wants: fill it completely**, so it looks right.
3. **Texts you can write yourself, write them.** Titles, subtitles, hero subtitle, button labels, service descriptions, value cards, FAQ wording. Write German and English: `{"de": "...", "en": "..."}`. Short, warm, factual. No medical claims or promises.
4. **Facts you cannot know, ask the customer.** Names, specialties, prices, addresses, phone, opening hours, years of experience, patient numbers, ratings. One short question at a time, grouped by section.
5. **Never invent facts.** No made-up doctors, prices, ratings, awards, certificates, statistics or addresses. If the customer does not give a fact, leave that item out. Items without their facts are rejected by the tool anyway.
6. Pictures come only from the customer (see Pictures below). Never use stock or invented pictures. Without a photo, doctors get a neat initials avatar and the hero shows a calm brand panel, which already looks finished.

## Introduce the template (once, early)

After you know it is a clinic, give a short, friendly overview in the customer's language, then let them choose. Call `clinic_template_overview` and use each section's `pitch`. Example (translate to their language):

> Your site uses our premium clinic template. It already has a start page and your services. You can switch on more parts if you like:
> 1. **Check-up packages**: 2-3 packages with price and what is included
> 2. **About us**: why patients choose you, plus numbers such as years of experience
> 3. **Doctors**: your team with specialty and a booking button
> 4. **Locations**: address, phone and opening hours of each practice
> 5. **FAQ**: common questions (insurance, first visit, languages, parking)
>
> Which would you like? You can add or remove any of them later.

Add only what they pick. Do not push. If they say "everything", ask for the facts section by section.

## Sections and what to collect

| Section | Ask the customer for | You write |
|---|---|---|
| `hero` | practice name (already known), lead doctor name + role if they want a name plate, real Google rating only if they offer it | headline, subtitle, button text |
| `services` | each service name and price | description, optional icon |
| `checkup` | package names, prices (number), what each includes | title, subtitle, short package text, note |
| `about` | real figures (years, patients, ...) and what makes them different | title, subtitle, up to 4 value cards from what they said |
| `doctors` | name and specialty of each doctor (years optional) | title, subtitle |
| `locations` | name, address, phone, hours per location | title, subtitle |
| `faq` | the facts behind each answer (insurance, languages, ...) | question and answer wording |
| `footer` | optional: short practice description, emergency note | the text |

Phone, address and opening hours of the practice go in with `update_website_content` (`contact`). They fill the header and footer automatically.

## How to save

`save_clinic_section(identifier, platform, section, data)`. Examples:

```json
{"section": "doctors", "data": {
  "title": {"de": "Unser Team", "en": "Our team"},
  "subtitle": {"de": "Erfahrene Ärztinnen und Ärzte für Sie", "en": "Experienced doctors for you"},
  "items": [{"name": "Dr. Anna Weber", "specialty": {"de": "Zahnärztin", "en": "Dentist"}, "years": 12}]}}
```

```json
{"section": "checkup", "data": {
  "title": {"de": "Check-up-Pakete", "en": "Check-up packages"},
  "plans": [
    {"name": "Basis", "price": 89, "features": ["Blutbild", "EKG"]},
    {"name": "Premium", "price": 249, "featured": true, "features": ["Blutbild", "EKG", "Ultraschall"]}]}}
```

- Send only new or changed items. Lists merge by `name` (FAQ by `question`).
- `remove: ["Dr. Max Roth"]` deletes one item. `replace: true` swaps the whole list.
- Service `name` stays a plain string. Put translations in `description`.
- Prices for check-up plans are numbers. Services keep the text the customer wrote ("ab 89 €").
- Icons are optional and come from a fixed list (see `available_icons`).

Read the result:
- `rejected` / `ask_customer`: those items were NOT saved. Ask the customer for the missing fact, then call again.
- `agent_should_write`: texts you should add yourself (for example `subtitle`). Do it in your next call.
- `section_state.visible`: `true` means it is on the site.
- `warning` about template not active: call `activate_clinic_template`.

Remove a section the customer no longer wants with `remove_clinic_section`. Hero and services stay.

## Pictures

Every picture on the site can be set or changed by the customer with `set_site_image`:

| target | Where it appears | `item` |
|---|---|---|
| `logo` | header and footer, next to the name | - |
| `hero` | the big picture in the start section | - |
| `service` | the photo on one service card | service name |
| `doctor` | the portrait of one doctor | doctor name |
| `location` | photo on a location's detail card | location name |
| `about` | wide photo above the about-us cards | - |

How it works:
- The customer sends a photo in chat and says where it goes ("this is my logo", "photo for Bleaching"). Call `set_site_image` with `file_path` exactly as it appears in the message (`Image attached at: <path>`). Never guess a path.
- An https image link also works (`url`). It is downloaded and stored on our side.
- Several photos at once, or unclear where they belong: ask which photo goes where before saving.
- The section for `service`, `doctor`, `location`, `about` must exist first. Add it with `save_clinic_section`, then set the picture.
- Replace a picture by sending a new one. Remove one with `remove: true`.
- Only JPG, PNG, WebP. If an upload fails, tell the customer in plain words (the tool's `message` says why) and ask for another photo.
- Ask for pictures when you introduce a section ("Do you have a photo of your practice for the start page?"), but never block on it. The site looks complete without them.
- Only the customer's own pictures. Do not take images from other websites.

## Finish

After saving, send the `preview_url` (`https://[slug].easywebbuilder.de`) and ask them to look at it and confirm. Offer the next not-yet-added section only once, briefly.

## Do not

- Do not add a section "to make the site look fuller" with invented content.
- Do not copy facts from the sample site (Lumera, Hamburg, +49 40 ..., doctor names, prices). None of that belongs to the customer.
- Do not give medical advice. Collecting and phrasing the practice's own information is in scope.
