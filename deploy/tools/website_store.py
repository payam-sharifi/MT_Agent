"""Supabase storage for easyWebBuilder sites on appventuregmbh.com.

Live URLs are always https://[slug].appventuregmbh.com.
users.active_website_id is used after deploy/sql/multi_tenant_websites.sql.
Until that migration, each user has one website (websites.user_id is unique).
"""

from __future__ import annotations

import json
import logging
import random
import re
import unicodedata
from typing import Any, Optional

from tools.clinic_content import CLINIC_THEME, is_medical_business, should_upgrade_theme

logger = logging.getLogger(__name__)

SUPABASE_URL = "https://rgqrpzsbblflxghyahnx.supabase.co"
SUPABASE_KEY = "sb_publishable_nyxKnB8H3IhRj41DBzpw3w_64wl_dbZ"
PREVIEW_DOMAIN = "appventuregmbh.com"

_UMLAUTS = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ä": "ae",
        "Ö": "oe",
        "Ü": "ue",
    }
)
_PLACEHOLDER_SLUG = re.compile(r"^site(?:-\d+)+$")

try:
    from supabase import create_client

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as exc:  # pragma: no cover - missing extra in lean installs
    create_client = None  # type: ignore[assignment]
    supabase = None
    logger.warning("supabase client unavailable: %s", exc)

_HAS_ACTIVE_COLUMN: Optional[bool] = None


def preview_url(slug: str) -> str:
    return f"https://{slug}.{PREVIEW_DOMAIN}"


def sanitize_slug(value: str) -> str:
    """Lowercase ASCII slug. Umlauts become ae/oe/ue/ss. Other marks are stripped."""
    text = str(value or "").strip().translate(_UMLAUTS)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return re.sub(r"-{2,}", "-", text)


def normalize_platform(platform: str) -> str:
    value = str(platform or "").strip().lower()
    if value == "whatsapp_cloud":
        return "whatsapp"
    return value


def normalize_identifier(identifier: str, platform: str) -> str:
    value = str(identifier or "").strip()
    if platform == "whatsapp":
        value = value.lstrip("+").split(":", 1)[0].split("@", 1)[0]
    return value


def is_placeholder_slug(slug: str) -> bool:
    return bool(_PLACEHOLDER_SLUG.fullmatch(str(slug or "").strip()))


def empty_content() -> dict:
    return {
        "hero": {"title": "", "subtitle": "", "cta_button": ""},
        "services": [],
        "contact": {"address": "", "phone": "", "opening_hours": ""},
    }


def _client():
    if supabase is None:
        raise RuntimeError("supabase package is not installed in the Hermes environment")
    return supabase


def _error_text(exc: Exception) -> str:
    return str(exc)


def _is_missing_column(exc: Exception, column: str) -> bool:
    text = _error_text(exc)
    return "42703" in text or column in text


def _is_unique_violation(exc: Exception, constraint: str = "") -> bool:
    text = _error_text(exc)
    if "23505" not in text and "duplicate key" not in text.lower():
        return False
    return not constraint or constraint in text


def active_column_available() -> bool:
    global _HAS_ACTIVE_COLUMN
    if _HAS_ACTIVE_COLUMN is not None:
        return _HAS_ACTIVE_COLUMN
    try:
        _client().table("users").select("active_website_id").limit(1).execute()
        _HAS_ACTIVE_COLUMN = True
    except Exception as exc:
        if not _is_missing_column(exc, "active_website_id"):
            raise
        _HAS_ACTIVE_COLUMN = False
        logger.info("users.active_website_id is not available; one website per user")
    return _HAS_ACTIVE_COLUMN


def _rows(response: Any) -> list:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def lookup_user_row(sender_id: str, platform: str) -> Optional[dict]:
    sender_id = normalize_identifier(sender_id, platform)
    if not sender_id:
        return None
    query = _client().table("users").select("*").limit(1)
    if platform == "telegram":
        response = query.eq("telegram_id", sender_id).execute()
    elif platform == "whatsapp":
        response = query.eq("whatsapp_phone", sender_id).execute()
        if not _rows(response):
            response = (
                _client().table("users").select("*").eq("phone_number", sender_id).limit(1).execute()
            )
    else:
        return None
    rows = _rows(response)
    return rows[0] if rows else None


def _slug_taken(slug: str, exclude_id: str = "") -> bool:
    response = _client().table("websites").select("id, slug, subdomain").or_(
        f"slug.eq.{slug},subdomain.eq.{slug}"
    ).execute()
    for row in _rows(response):
        if exclude_id and row.get("id") == exclude_id:
            continue
        return True
    return False


def allocate_slug(business_name: str, exclude_id: str = "") -> str:
    base = sanitize_slug(business_name) or f"site-{random.randint(1000, 9999)}"
    if not _slug_taken(base, exclude_id):
        return base
    for number in range(1, 100):
        candidate = f"{base}-{number}"
        if not _slug_taken(candidate, exclude_id):
            return candidate
    return f"{base}-{random.randint(1000, 9999)}"


def _websites_for_user(user_id: str) -> list:
    response = (
        _client()
        .table("websites")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )
    return _rows(response)


def _theme_config(row: dict) -> dict:
    config = row.get("theme_config") or {}
    return dict(config) if isinstance(config, dict) else {}


def pick_active_website(user: dict, websites: list) -> tuple[Optional[dict], bool]:
    """Return (active website, needs_choice). needs_choice is true when several sites and none is active."""
    if not websites:
        return None, False
    if active_column_available():
        active_id = user.get("active_website_id")
        if active_id:
            for website in websites:
                if website.get("id") == active_id:
                    return website, False
        if len(websites) == 1:
            return websites[0], False
        return None, True
    if len(websites) == 1:
        return websites[0], False
    marked = [website for website in websites if _theme_config(website).get("active") is True]
    if len(marked) == 1:
        return marked[0], False
    return None, True


def set_active_website(user_id: str, website_id: str, websites: list) -> None:
    if active_column_available():
        _client().table("users").update({"active_website_id": website_id}).eq("id", user_id).execute()
        return
    for website in websites:
        config = _theme_config(website)
        config["active"] = website.get("id") == website_id
        _client().table("websites").update({"theme_config": config}).eq("id", website["id"]).execute()
        website["theme_config"] = config


def _insert_user(sender_id: str, platform: str) -> dict:
    payload: dict[str, Any] = {"language": "de"}
    if platform == "telegram":
        payload["telegram_id"] = sender_id
    else:
        payload["whatsapp_phone"] = sender_id
        payload["phone_number"] = sender_id
    try:
        response = _client().table("users").insert(payload).execute()
    except Exception as exc:
        if not _is_unique_violation(exc):
            raise
        existing = lookup_user_row(sender_id, platform)
        if existing:
            return existing
        raise
    rows = _rows(response)
    if not rows:
        raise RuntimeError("user insert returned no row")
    return rows[0]


def _insert_website(user_id: str, slug: str, business_name: str = "", business_type: str = "") -> dict:
    content = empty_content()
    if business_name:
        content["hero"]["title"] = business_name
    site_data: dict[str, Any] = {}
    if business_name:
        site_data["business_name"] = business_name
        site_data["sections"] = [{"type": "hero", "title": business_name}]
    theme_config: dict[str, Any] = {"active": True}
    if is_medical_business(business_type, business_name):
        # Doctors and clinics get the premium clinic template from the start.
        theme_config["theme"] = CLINIC_THEME
        site_data["theme"] = CLINIC_THEME
    payload = {
        "user_id": user_id,
        "slug": slug,
        "subdomain": slug,
        "business_name": business_name or None,
        "business_type": business_type or None,
        "content_json": content,
        "theme_config": theme_config,
        "is_published": True,
        "status": "published",
        "site_data": site_data,
    }
    response = _client().table("websites").insert(payload).execute()
    rows = _rows(response)
    if not rows:
        raise RuntimeError("website insert returned no row")
    return rows[0]


def _backfill_slug(website: dict) -> dict:
    slug = str(website.get("slug") or "").strip()
    if slug:
        return website
    source = website.get("subdomain") or website.get("business_name") or ""
    slug = sanitize_slug(str(source))
    if not slug or _slug_taken(slug, exclude_id=str(website.get("id") or "")):
        slug = allocate_slug(str(source or "site"), exclude_id=str(website.get("id") or ""))
    update = {"slug": slug}
    if not str(website.get("subdomain") or "").strip():
        update["subdomain"] = slug
    _client().table("websites").update(update).eq("id", website["id"]).execute()
    website.update(update)
    return website


def ensure_account(sender_id: str, platform: str) -> dict:
    """Find the sender, or create the user and a first website."""
    platform = normalize_platform(platform)
    sender_id = normalize_identifier(sender_id, platform)
    if platform not in {"telegram", "whatsapp"}:
        return {"error": "platform must be 'telegram' or 'whatsapp'"}
    if not sender_id:
        return {"error": "sender_id is required"}

    created = False
    user = lookup_user_row(sender_id, platform)
    if not user:
        user = _insert_user(sender_id, platform)
        created = True

    websites = _websites_for_user(user["id"])
    if not websites:
        slug = allocate_slug(f"site-{random.randint(1000, 9999)}")
        website = _insert_website(user["id"], slug)
        websites = [website]
        created = True
        set_active_website(user["id"], website["id"], websites)
        user["active_website_id"] = website["id"]
    else:
        websites = [_backfill_slug(website) for website in websites]

    active, needs_choice = pick_active_website(user, websites)
    if active and active_column_available() and not user.get("active_website_id"):
        set_active_website(user["id"], active["id"], websites)
        user["active_website_id"] = active["id"]

    slug = str((active or {}).get("slug") or "")
    return {
        "created": created,
        "sender_id": sender_id,
        "platform": platform,
        "user": user,
        "website": active,
        "websites": _public_websites(websites, (active or {}).get("id")),
        "needs_choice": needs_choice,
        "preview_url": preview_url(slug) if slug else "",
    }


def _public_website(website: dict, active_id: Optional[str]) -> dict:
    slug = str(website.get("slug") or "")
    return {
        "id": website.get("id"),
        "business_name": website.get("business_name") or "",
        "business_type": website.get("business_type") or "",
        "slug": slug,
        "preview_url": preview_url(slug) if slug else "",
        "active": website.get("id") == active_id,
    }


def _public_websites(websites: list, active_id: Optional[str]) -> list:
    return [_public_website(website, active_id) for website in websites]


def list_websites(sender_id: str, platform: str) -> dict:
    account = ensure_account(sender_id, platform)
    if account.get("error"):
        return account
    return {
        "status": "success",
        "needs_choice": account["needs_choice"],
        "websites": account["websites"],
        "preview_url": account["preview_url"],
    }


def create_website(sender_id: str, platform: str, business_name: str, business_type: str = "") -> dict:
    account = ensure_account(sender_id, platform)
    if account.get("error"):
        return account
    business_name = str(business_name or "").strip()
    business_type = str(business_type or "").strip()
    if not business_name:
        return {"error": "business_name is required"}
    user_id = account["user"]["id"]
    existing = _websites_for_user(user_id)
    if len(existing) == 1:
        only = existing[0]
        if is_placeholder_slug(str(only.get("slug") or "")) and not str(only.get("business_name") or "").strip():
            return update_website_content(
                sender_id,
                platform,
                content={"hero": {"title": business_name}},
                business_name=business_name,
                business_type=business_type,
            )
    slug = allocate_slug(business_name)
    try:
        website = _insert_website(user_id, slug, business_name, str(business_type or "").strip())
    except Exception as exc:
        if _is_unique_violation(exc, "websites_user_id_key"):
            current = account.get("preview_url") or ""
            return {
                "error": "only_one_website",
                "preview_url": current,
                "message": (
                    "This account can only have one website until the multi-website "
                    "migration is applied. Keep editing the current website."
                ),
            }
        logger.warning("create_website failed: %s", exc, exc_info=True)
        return {"error": _error_text(exc)}
    websites = _websites_for_user(user_id)
    set_active_website(user_id, website["id"], websites)
    return {
        "status": "success",
        "created": True,
        "website": _public_website(website, website["id"]),
        "preview_url": preview_url(slug),
    }


def switch_website(sender_id: str, platform: str, slug: str = "", business_name: str = "") -> dict:
    account = ensure_account(sender_id, platform)
    if account.get("error"):
        return account
    websites = _websites_for_user(account["user"]["id"])
    needle_slug = sanitize_slug(slug) if slug else ""
    needle_name = str(business_name or "").strip().lower()
    match = None
    for website in websites:
        if needle_slug and str(website.get("slug") or "") == needle_slug:
            match = website
            break
        name = str(website.get("business_name") or "").strip().lower()
        if needle_name and name == needle_name:
            match = website
            break
    if match is None:
        return {
            "error": "website_not_found",
            "websites": _public_websites(websites, (account.get("website") or {}).get("id")),
        }
    set_active_website(account["user"]["id"], match["id"], websites)
    public = _public_website(match, match["id"])
    return {"status": "success", "website": public, "preview_url": public["preview_url"]}


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("JSON value must be an object")
        return parsed
    return {}


def _filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _merge_named_items(current: Any, incoming: Any, key: str) -> list:
    items = [dict(item) for item in current if isinstance(item, dict)] if isinstance(current, list) else []
    incoming_items = incoming if isinstance(incoming, list) else [incoming]
    for raw in incoming_items:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get(key) or "").strip()
        if not name:
            items.append(raw)
            continue
        replaced = False
        for index, item in enumerate(items):
            if str(item.get(key) or "").strip() == name:
                merged = dict(item)
                merged.update({field: value for field, value in raw.items() if _filled(value)})
                items[index] = merged
                replaced = True
                break
        if not replaced:
            items.append(raw)
    return items


def merge_content(current: dict, patch: dict) -> dict:
    """Deep-merge hero and contact. Services and FAQ merge by name or question."""
    base = empty_content()
    if isinstance(current, dict):
        hero = current.get("hero")
        contact = current.get("contact")
        if isinstance(hero, dict):
            base["hero"].update(hero)
        if isinstance(contact, dict):
            base["contact"].update(contact)
        if isinstance(current.get("services"), list):
            base["services"] = list(current["services"])
        if "faq" in current:
            base["faq"] = current["faq"]
        for key, value in current.items():
            if key not in base:
                base[key] = value
    if not isinstance(patch, dict):
        return base
    hero_patch = patch.get("hero")
    if isinstance(hero_patch, dict):
        base["hero"].update({key: value for key, value in hero_patch.items() if _filled(value)})
    contact_patch = patch.get("contact")
    if isinstance(contact_patch, dict):
        base["contact"].update({key: value for key, value in contact_patch.items() if _filled(value)})
    if "services" in patch:
        base["services"] = _merge_named_items(base.get("services"), patch.get("services"), "name")
    if "faq" in patch:
        incoming_faq = patch.get("faq")
        if isinstance(incoming_faq, dict):
            incoming_faq = incoming_faq.get("items")
        base["faq"] = _merge_named_items(base.get("faq"), incoming_faq, "question")
    return base


def content_from_site_data(site_data: Any) -> dict:
    content = empty_content()
    if not isinstance(site_data, dict):
        return content
    if site_data.get("business_name") and not content["hero"]["title"]:
        content["hero"]["title"] = site_data["business_name"]
    sections = site_data.get("sections")
    if not isinstance(sections, list):
        return content
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_type = section.get("type")
        if section_type == "hero":
            for field in ("title", "subtitle", "cta_button"):
                if _filled(section.get(field)):
                    content["hero"][field] = section[field]
        elif section_type == "services" and isinstance(section.get("items"), list):
            content["services"] = section["items"]
        elif section_type == "working_hours":
            hours = section.get("text")
            if not _filled(hours):
                parts = [str(section.get(field) or "").strip() for field in ("days", "open", "close")]
                hours = " ".join(part for part in parts if part)
            if _filled(hours):
                content["contact"]["opening_hours"] = hours
        elif section_type == "faq" and isinstance(section.get("items"), list):
            content["faq"] = section["items"]
    address = site_data.get("address")
    phone = site_data.get("phone")
    if _filled(address):
        content["contact"]["address"] = address
    if _filled(phone):
        content["contact"]["phone"] = phone
    return content


def _upsert_section(sections: list, section: dict) -> list:
    section_type = section.get("type")
    kept = []
    replaced = False
    for current in sections:
        if isinstance(current, dict) and current.get("type") == section_type:
            if not replaced:
                merged = dict(current)
                for key, value in section.items():
                    if key == "items" or _filled(value):
                        merged[key] = value
                kept.append(merged)
                replaced = True
        else:
            kept.append(current)
    if not replaced:
        kept.append(section)
    return kept


def apply_content_to_site_data(site_data: Any, content: dict, business_name: str = "") -> dict:
    data = dict(site_data) if isinstance(site_data, dict) else {}
    sections = [section for section in data.get("sections") or [] if isinstance(section, dict)]
    hero = content.get("hero") or {}
    if any(_filled(hero.get(field)) for field in ("title", "subtitle", "cta_button")):
        sections = _upsert_section(
            sections,
            {
                "type": "hero",
                "title": hero.get("title") or "",
                "subtitle": hero.get("subtitle") or "",
                "cta_button": hero.get("cta_button") or "",
            },
        )
    if content.get("services"):
        sections = _upsert_section(sections, {"type": "services", "items": content["services"]})
    hours = (content.get("contact") or {}).get("opening_hours")
    if _filled(hours):
        sections = _upsert_section(sections, {"type": "working_hours", "text": hours})
    faq = content.get("faq")
    if isinstance(faq, list) and faq:
        sections = _upsert_section(sections, {"type": "faq", "items": faq})
    contact = content.get("contact") or {}
    if _filled(contact.get("address")):
        data["address"] = contact["address"]
    if _filled(contact.get("phone")):
        data["phone"] = contact["phone"]
    if business_name:
        data["business_name"] = business_name
    data["sections"] = sections
    return data


def _load_json_object(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    return {}


def update_website_content(
    sender_id: str,
    platform: str,
    content: Any = None,
    business_name: str = "",
    business_type: str = "",
    theme: str = "",
) -> dict:
    account = ensure_account(sender_id, platform)
    if account.get("error"):
        return account
    if account.get("needs_choice") or not account.get("website"):
        return {
            "error": "needs_website_choice",
            "websites": account.get("websites") or [],
            "message": "Ask the user which website to edit before changing content.",
        }
    try:
        patch = _as_dict(content)
    except (ValueError, json.JSONDecodeError) as exc:
        return {"error": f"invalid content: {exc}"}

    business_name = str(business_name or "").strip()
    business_type = str(business_type or "").strip()
    theme = str(theme or "").strip().lower()
    website = account["website"]
    if not business_name:
        hero_title = str((patch.get("hero") or {}).get("title") or "").strip()
        if hero_title and not str(website.get("business_name") or "").strip():
            business_name = hero_title
    if not patch and not business_name and not business_type and not theme:
        return {"error": "content is empty"}

    # Doctors and clinics get the clinic template unless the customer picked another look.
    kind = business_type or str(website.get("business_type") or "")
    if is_medical_business(kind, "" if kind else (business_name or website.get("business_name"))):
        chosen = theme or str(_theme_config(website).get("theme") or "").strip().lower()
        if should_upgrade_theme(chosen):
            theme = CLINIC_THEME

    current = _load_json_object(website.get("content_json"))
    if not any(_filled(current.get(key)) for key in ("hero", "services", "contact", "faq")):
        current = content_from_site_data(website.get("site_data"))
    else:
        current = merge_content(content_from_site_data(website.get("site_data")), current)
    updated = merge_content(current, patch)
    if business_name and not _filled(updated["hero"].get("title")):
        updated["hero"]["title"] = business_name

    slug = str(website.get("slug") or "")
    update: dict[str, Any] = {
        "content_json": updated,
        "site_data": apply_content_to_site_data(website.get("site_data"), updated, business_name),
        "is_published": True,
        "status": "published",
    }
    if business_name:
        update["business_name"] = business_name
        if not slug or is_placeholder_slug(slug):
            slug = allocate_slug(business_name, exclude_id=str(website.get("id") or ""))
            update["slug"] = slug
            update["subdomain"] = slug
    if business_type:
        update["business_type"] = business_type
    if theme:
        config = _theme_config(website)
        config["theme"] = theme
        update["theme_config"] = config
        update["site_data"]["theme"] = theme

    _client().table("websites").update(update).eq("id", website["id"]).execute()
    return {
        "status": "success",
        "slug": slug,
        "preview_url": preview_url(slug) if slug else "",
        "business_name": business_name or website.get("business_name") or "",
        "content_json": updated,
    }


def update_legal_impressum(
    sender_id: str,
    platform: str,
    owner_name: str = "",
    address: str = "",
    tax_number: str = "",
    legal_form: str = "",
) -> dict:
    account = ensure_account(sender_id, platform)
    if account.get("error"):
        return account
    if account.get("needs_choice") or not account.get("website"):
        return {
            "error": "needs_website_choice",
            "websites": account.get("websites") or [],
            "message": "Ask the user which website to edit before saving legal details.",
        }
    fields = {
        "owner_name": str(owner_name or "").strip(),
        "address": str(address or "").strip(),
        "tax_number": str(tax_number or "").strip(),
        "legal_form": str(legal_form or "").strip(),
    }
    payload = {key: value for key, value in fields.items() if value}
    if not payload:
        return {"error": "owner_name, address, tax_number, or legal_form is required"}

    website_id = account["website"]["id"]
    existing = (
        _client().table("legal_impressum").select("id").eq("website_id", website_id).limit(1).execute()
    )
    payload["website_id"] = website_id
    rows = _rows(existing)
    if rows:
        _client().table("legal_impressum").update(payload).eq("id", rows[0]["id"]).execute()
    else:
        _client().table("legal_impressum").insert(payload).execute()

    slug = str(account["website"].get("slug") or "")
    return {
        "status": "success",
        "preview_url": preview_url(slug) if slug else "",
        "legal": payload,
    }


def build_lookup_prefix(account: dict) -> str:
    sender_id = account.get("sender_id") or ""
    platform = account.get("platform") or ""
    url = account.get("preview_url") or ""
    parts = [f"[easyWebBuilder lookup] platform={platform} sender_id={sender_id}."]
    if account.get("error"):
        parts.append(f"Lookup failed: {account['error']}. Tell the user you could not open their website.")
        return " ".join(parts)
    if account.get("created"):
        parts.append(
            "NEW ACCOUNT. A website was just created. Welcome the user in their language. "
            f"Include this preview link: {url}. "
            "Ask for the business name, services, or any changes. Do not create the account again."
        )
    else:
        parts.append("FOUND. Do not create another account.")
        if account.get("needs_choice"):
            parts.append(
                "No active website is selected. Call list_user_websites and ask which site to edit. "
                "Do not change content until they choose."
            )
        else:
            website = account.get("website") or {}
            name = website.get("business_name") or website.get("slug") or "website"
            parts.append(f"Active website: {name}. Preview: {url}. Edit this website only.")
    website = account.get("website") or {}
    current_theme = str(_theme_config(website).get("theme") or "").strip().lower()
    if current_theme == CLINIC_THEME or is_medical_business(
        website.get("business_type"), "" if website.get("business_type") else website.get("business_name")
    ):
        parts.append(
            "This looks like a doctor, dentist or clinic. It uses the premium clinic template (theme clinic-premium). "
            "Follow the skill clinic-template: introduce the template's optional sections to the customer "
            "(check-up packages, about us, doctors, locations, FAQ) and let them choose. "
            "Use clinic_template_overview to see what is active, save_clinic_section to add or change a section, "
            "remove_clinic_section for ones they do not want, and activate_clinic_template if the site does not use "
            "the template yet. Write titles and descriptions yourself in German and English. Ask the customer only for "
            "facts (names, prices, addresses, phone, hours). Never invent facts."
        )
    parts.append(
        "Use update_website_content for hero, services, prices, hours, contact, and FAQ. "
        "Use update_legal_impressum for owner name, address, tax ID / USt-IdNr, and legal form. "
        "Use list_user_websites, switch_active_website, and create_website to manage several sites. "
        "Pass this sender_id and platform. Never invent them. "
        "After every create or edit, send the https://[slug].appventuregmbh.com link and ask the user to confirm. "
        "Reply in the user's language. Never use another domain."
    )
    return " ".join(parts)
