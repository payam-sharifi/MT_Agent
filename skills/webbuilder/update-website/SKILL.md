---
name: update-website
description: Update site_data theme and sections in Supabase.
---

# Update Website

For **registered** Telegram/WhatsApp users, persist website edits with `update_website_data`. Content lives in `site_data.sections`. Visual style lives in root `site_data.theme`. Do not put hero/services/hours/FAQ or `theme` inside each other.

## When to Use

- User is already registered (`FOUND` / `lookup_user` `found=true`).
- They want to change prices, add or edit services, update working hours, hero text, FAQ, look/colors, or the site theme.
- After the first business details are known (name, activity, services), set `theme` if it is missing.
- Don't use for first-time registration (`check_and_register_user`).

## site_data shape

```json
{
  "theme": "zen",
  "sections": [
    { "type": "hero", "title": "...", "subtitle": "...", "image_url": "..." },
    { "type": "services", "items": [{ "name": "...", "description": "...", "price": "..." }] },
    { "type": "working_hours", "text": "..." },
    { "type": "faq", "items": [{ "question": "...", "answer": "..." }] }
  ]
}
```

`theme` is a root field (not a section). Allowed values only:

| theme | When | Look |
|---|---|---|
| `clinical` | Doctors, clinics, dentistry, medical / therapeutic services | White + blue, clean |
| `luxury` | Beauty salons, hair, jewelry, luxury brands | Black / gold / cream |
| `zen` | Massage, spa, yoga, calming wellness | Olive / earth / soft dark |
| `corporate` | Lawyers, consultants, real estate, service companies | Navy / gray, formal |
| `default` | Other jobs, or occupation unknown | Minimal white / gray |

Valid `type` values only:

| type | fields |
|---|---|
| `hero` | `title`, `subtitle`, `image_url` |
| `services` | `items`: `[{ name, description, price }]` |
| `working_hours` | `{ text }` **or** `{ open, close, days }` |
| `faq` | `items`: `[{ question, answer }]` |

One section per `type`. To add a new block (FAQ, hours, …), append a new object to `sections`. Never replace the whole array with only the new section.

## Procedure

1. Take `identifier` and `platform` from the inbound lookup (`sender_id` + `telegram` or `whatsapp`). Never invent them.
2. Infer or update `theme` (see below) and put it on the **root** of `site_data_update`.
3. Put **only the changed section(s)** in `site_data_update.sections`. The tool merges by `type`. A theme-only call may omit `sections`.
4. Call `update_website_data(identifier, platform, site_data_update)`.
5. If `status=success`, confirm in the user's language. If `error`, say so — do not claim the site was updated.

## Theme

Guess the occupation from the business name, activity, or services. Set `theme` on first content save and whenever the occupation becomes clearer. If the user asks for look or color, map that request — do not invent a new theme name.

| User / business cues | `theme` |
|---|---|
| پزشک، کلینیک، دندان‌پزشکی، درمان، سفید و آبی، تم پزشکی | `clinical` |
| سالن زیبایی، آرایشگاه، جواهر، لوکس، شیک، طلایی، مشکی | `luxury` |
| ماساژ، اسپا، یوگا، آرامش، سبز زیتونی، تم تیره ملایم | `zen` |
| وکیل، مشاور، املاک، شرکت خدماتی، رسمی، سرمه‌ای | `corporate` |
| نامشخص، ساده، مینیمال، سایر | `default` |

User look requests: «تم تیره/شیک» → `luxury` unless the business is clearly massage/spa (`zen`). «تم پزشکی» → `clinical`. «رسمی/شرکتی» → `corporate`.

## Mapping

| User says | `site_data_update` |
|---|---|
| عنوان / هیرو / زیرعنوان / عکس هیرو | `{ "sections": [{ "type": "hero", "title": "...", "subtitle": "...", "image_url": "..." }] }` |
| قیمت / خدمت جدید / ویرایش خدمت | `{ "sections": [{ "type": "services", "items": [{ "name": "...", "description": "...", "price": "..." }] }] }` |
| ساعت کاری | `{ "sections": [{ "type": "working_hours", "text": "..." }] }` or `{ "open", "close", "days" }` |
| سوالات متداول / FAQ / بخش جدید | `{ "sections": [{ "type": "faq", "items": [{ "question": "...", "answer": "..." }] }] }` |
| ظاهر / رنگ / تم سایت | `{ "theme": "luxury" }` (or clinical / zen / corporate / default) |

A single service/FAQ item is merged by `name` / `question` (update if it exists, otherwise append). A new `type` that is not in `sections` yet is appended.

## Examples

```
User: عنوان سایت بشه مرکز ماساژ محمد
→ update_website_data(..., site_data_update={
  "theme": "zen",
  "sections": [{ "type": "hero", "title": "مرکز ماساژ محمد" }]
})
```

```
User: سایتم تم تیره و شیک داشته باشه
→ update_website_data(..., site_data_update={ "theme": "luxury" })
```

```
User: قیمت ماساژ سنگ رو بذار ۳۵۰ هزار
→ update_website_data(..., site_data_update={
  "sections": [{ "type": "services", "items": [{ "name": "ماساژ سنگ", "price": "350000" }] }]
})
```

```
User: یک خدمت جدید اضافه کن: ماساژ صورت، ۴۰۰ هزار
→ update_website_data(..., site_data_update={
  "sections": [{ "type": "services", "items": [{ "name": "ماساژ صورت", "price": "400000" }] }]
})
```

```
User: ساعت کاری شنبه تا پنجشنبه ۱۰ تا ۲۰
→ update_website_data(..., site_data_update={
  "sections": [{ "type": "working_hours", "days": "شنبه تا پنجشنبه", "open": "10:00", "close": "20:00" }]
})
```

```
User: بخش سوالات متداول اضافه کن. سوال: نوبت چطور بگیرم؟ جواب: در واتساپ پیام بدهید.
→ update_website_data(..., site_data_update={
  "sections": [{
    "type": "faq",
    "items": [{ "question": "نوبت چطور بگیرم؟", "answer": "در واتساپ پیام بدهید." }]
  }]
})
```
