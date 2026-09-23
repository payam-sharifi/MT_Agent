"""Update easyWebBuilder site_data in Supabase for a Telegram/WhatsApp user."""

from __future__ import annotations

import json
import logging
from typing import Any

from tools.registry import registry

logger = logging.getLogger(__name__)

SUPABASE_URL = "https://rgqrpzsbblflxghyahnx.supabase.co"
# Publishable key (same as onboarding). RLS must allow SELECT/UPDATE on users + websites.
SUPABASE_KEY = "sb_publishable_nyxKnB8H3IhRj41DBzpw3w_64wl_dbZ"

_MESSAGING_PLATFORMS = {
    "telegram": "telegram",
    "whatsapp": "whatsapp",
    "whatsapp_cloud": "whatsapp",
}

_USER_ID_COLUMN = {
    "telegram": "telegram_id",
    "whatsapp": "phone",
}

try:
    from supabase import create_client

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as exc:  # pragma: no cover - missing extra in lean installs
    create_client = None  # type: ignore[assignment]
    supabase = None
    logger.warning("supabase client unavailable: %s", exc)


def _deep_merge(current: Any, update: Any) -> Any:
    """Merge dicts recursively; lists and scalars in *update* replace *current*."""
    if not isinstance(current, dict) or not isinstance(update, dict):
        return update
    merged = dict(current)
    for key, value in update.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _parse_site_data_update(site_data_update: Any) -> dict:
    if site_data_update is None:
        return {}
    if isinstance(site_data_update, str):
        text = site_data_update.strip()
        if not text:
            return {}
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("site_data_update JSON must be an object")
        return parsed
    if isinstance(site_data_update, dict):
        return site_data_update
    raise ValueError("site_data_update must be an object")


def _normalize_identifier(identifier: str, platform: str) -> str:
    value = str(identifier or "").strip()
    if platform == "whatsapp":
        value = value.lstrip("+").split(":", 1)[0].split("@", 1)[0]
    return value


_VALID_SECTION_TYPES = ("hero", "services", "working_hours", "faq")
_VALID_THEMES = ("clinical", "luxury", "zen", "corporate", "default")
_LIST_SECTION_TYPES = {"services", "faq"}
_ITEM_KEY_FIELDS = {
    "services": ("name", "id", "title"),
    "faq": ("question", "id"),
}


def _as_items(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item is not None]
    if isinstance(value, dict):
        return [value]
    return []


def _item_key(item: Any, fields: tuple[str, ...], fallback: str) -> str:
    if isinstance(item, dict):
        for field in fields:
            if item.get(field):
                return f"{field}:{item[field]}"
    return fallback


def _merge_item_list(existing: Any, incoming: Any, section_type: str) -> list:
    fields = _ITEM_KEY_FIELDS.get(section_type, ("id", "name", "title"))
    base = [item for item in _as_items(existing) if isinstance(item, dict) or item]
    patch = _as_items(incoming)
    keyed: dict[str, Any] = {}
    order: list[str] = []
    for index, item in enumerate(base):
        key = _item_key(item, fields, f"old:{index}")
        keyed[key] = item
        order.append(key)
    for index, item in enumerate(patch):
        key = _item_key(item, fields, f"new:{index}")
        if key in keyed:
            if isinstance(keyed[key], dict) and isinstance(item, dict):
                keyed[key] = _deep_merge(keyed[key], item)
            else:
                keyed[key] = item
        else:
            keyed[key] = item
            order.append(key)
    return [keyed[key] for key in order]


def _normalize_section(section: Any) -> dict | None:
    if not isinstance(section, dict):
        return None
    section_type = str(section.get("type") or "").strip().lower()
    if section_type not in _VALID_SECTION_TYPES:
        return None
    normalized = {key: value for key, value in section.items() if key != "type"}
    normalized["type"] = section_type
    if section_type in _LIST_SECTION_TYPES:
        items = section.get("items", section.get("services" if section_type == "services" else "faq"))
        normalized = {key: value for key, value in normalized.items() if key not in {"items", "services", "faq"}}
        normalized["type"] = section_type
        normalized["items"] = _as_items(items)
    return normalized


def _section_from_legacy(section_type: str, value: Any) -> dict | None:
    if section_type not in _VALID_SECTION_TYPES or value is None:
        return None
    if section_type == "hero" and isinstance(value, dict):
        return {"type": "hero", **value}
    if section_type == "working_hours":
        if isinstance(value, str):
            return {"type": "working_hours", "text": value}
        if isinstance(value, dict):
            return {"type": "working_hours", **value}
        return None
    if section_type in _LIST_SECTION_TYPES:
        return {"type": section_type, "items": _as_items(value)}
    return None


def _sections_from_patch(patch: dict) -> list[dict]:
    """Accept `{sections: [...]}` or legacy top-level hero/services/hours/faq keys."""
    sections: list[dict] = []
    seen: set[str] = set()

    def _add(section: dict | None) -> None:
        if not section:
            return
        section_type = section["type"]
        if section_type in seen:
            existing = next(item for item in sections if item["type"] == section_type)
            merged = _merge_section(existing, section)
            sections[sections.index(existing)] = merged
            return
        seen.add(section_type)
        sections.append(section)

    raw_sections = patch.get("sections")
    if isinstance(raw_sections, dict):
        raw_sections = [raw_sections]
    if isinstance(raw_sections, list):
        for item in raw_sections:
            _add(_normalize_section(item))
    elif isinstance(patch.get("type"), str):
        _add(_normalize_section(patch))
    for section_type in _VALID_SECTION_TYPES:
        if section_type in patch and section_type != "sections":
            _add(_section_from_legacy(section_type, patch.get(section_type)))
    return sections


def _merge_section(current: dict, incoming: dict) -> dict:
    section_type = incoming.get("type") or current.get("type")
    merged = _deep_merge(
        {key: value for key, value in current.items() if key != "items"},
        {key: value for key, value in incoming.items() if key != "items"},
    )
    merged["type"] = section_type
    if section_type in _LIST_SECTION_TYPES:
        merged["items"] = _merge_item_list(current.get("items"), incoming.get("items"), section_type)
    return merged


def _merge_site_data(current_data: dict, patch: dict) -> dict:
    current_sections = []
    raw_current = current_data.get("sections")
    if isinstance(raw_current, list):
        current_sections = [section for section in (_normalize_section(item) for item in raw_current) if section]
    elif not raw_current:
        for section_type in _VALID_SECTION_TYPES:
            legacy = _section_from_legacy(section_type, current_data.get(section_type))
            if legacy:
                current_sections.append(legacy)

    incoming_sections = _sections_from_patch(patch)
    by_type = {section["type"]: section for section in current_sections}
    order = [section["type"] for section in current_sections]
    for section in incoming_sections:
        section_type = section["type"]
        if section_type in by_type:
            by_type[section_type] = _merge_section(by_type[section_type], section)
        else:
            by_type[section_type] = section
            order.append(section_type)

    extra = {key: value for key, value in current_data.items() if key not in _VALID_SECTION_TYPES and key != "sections"}
    extra.update({key: value for key, value in patch.items() if key not in _VALID_SECTION_TYPES and key != "sections" and key != "type"})
    return {**extra, "sections": [by_type[section_type] for section_type in order]}


def _normalize_theme(value: Any) -> str | None:
    if value is None or value == "":
        return None
    theme = str(value).strip().lower()
    if theme not in _VALID_THEMES:
        raise ValueError(
            "theme must be one of: clinical, luxury, zen, corporate, default"
        )
    return theme


def update_website_data(identifier: str, platform: str, site_data_update: dict) -> dict:
    """
    Updates websites.site_data for a user (telegram_id or phone).
    site_data is stored as {"theme": "...", "sections": [ {type, ...}, ... ]}.
    Sections merge by type. Root theme is clinical | luxury | zen | corporate | default.
    """
    try:
        if supabase is None:
            return {"error": "supabase package is not installed in the Hermes environment"}

        platform = _MESSAGING_PLATFORMS.get(str(platform or "").strip().lower(), "")
        if platform not in _USER_ID_COLUMN:
            return {"error": "platform must be 'telegram' or 'whatsapp'"}

        identifier = _normalize_identifier(identifier, platform)
        if not identifier:
            return {"error": "identifier is required"}

        try:
            patch = _parse_site_data_update(site_data_update)
        except (ValueError, json.JSONDecodeError) as exc:
            return {"error": f"invalid site_data_update: {exc}"}
        if not patch:
            return {"error": "site_data_update must not be empty"}

        try:
            theme = _normalize_theme(patch["theme"]) if "theme" in patch else None
        except ValueError as exc:
            return {"error": str(exc)}
        if theme is not None:
            patch["theme"] = theme

        incoming_sections = _sections_from_patch(patch)
        if not incoming_sections and theme is None:
            return {
                "error": (
                    "site_data_update must include theme and/or sections with a valid type: "
                    "hero, services, working_hours, or faq"
                )
            }

        col = _USER_ID_COLUMN[platform]
        user_res = supabase.table("users").select("id").eq(col, str(identifier)).execute()

        if not user_res.data:
            return {"error": "User not found"}

        user_id = user_res.data[0]["id"]

        site_res = (
            supabase.table("websites").select("id, site_data").eq("user_id", user_id).execute()
        )
        if not site_res.data:
            return {"error": "Website not found"}

        current_data = site_res.data[0].get("site_data") or {}
        if isinstance(current_data, str):
            current_data = json.loads(current_data) if current_data.strip() else {}
        if not isinstance(current_data, dict):
            current_data = {}

        updated_site_data = _merge_site_data(current_data, patch)

        supabase.table("websites").update({
            "site_data": updated_site_data,
            "status": "published",
        }).eq("user_id", user_id).execute()

        print(
            f"[update_website] user_id={user_id!r} platform={platform!r} "
            f"identifier={identifier!r} theme={updated_site_data.get('theme')!r} "
            f"types={[s.get('type') for s in incoming_sections]!r}",
            flush=True,
        )
        return {"status": "success", "updated_data": updated_site_data}
    except Exception as e:
        logger.warning("update_website_data failed: %s", e, exc_info=True)
        return {"error": str(e)}


def _handle_update_website_data(args: dict, **kwargs) -> str:
    del kwargs
    result = update_website_data(
        identifier=str(args.get("identifier") or ""),
        platform=str(args.get("platform") or ""),
        site_data_update=args.get("site_data_update") or {},
    )
    return json.dumps(result, ensure_ascii=False)


def _supabase_available() -> bool:
    return supabase is not None


UPDATE_WEBSITE_DATA_SCHEMA = {
    "name": "update_website_data",
    "description": (
        "Update a registered easyWebBuilder user's site_data in Supabase. "
        "Root theme is clinical | luxury | zen | corporate | default "
        "(infer from occupation, or from look/color requests). "
        "site_data.sections types: hero, services, working_hours, faq. "
        "Pass only changed fields; sections merge by type. Theme-only updates are allowed. "
        "identifier is the Telegram numeric ID or WhatsApp phone; platform is telegram or whatsapp."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "identifier": {
                "type": "string",
                "description": "Telegram numeric user ID or WhatsApp phone number (sender_id).",
            },
            "platform": {
                "type": "string",
                "enum": ["telegram", "whatsapp"],
                "description": "Messaging platform the identifier belongs to.",
            },
            "site_data_update": {
                "type": "object",
                "description": (
                    "Root theme (clinical, luxury, zen, corporate, default) plus optional "
                    "sections: an array of {type, ...fields}. "
                    "Types: hero {title, subtitle, image_url}, "
                    "services {items: [{name, description, price}]}, "
                    "working_hours {text} or {open, close, days}, "
                    "faq {items: [{question, answer}]}. "
                    "Theme-only updates are valid. Changed sections merge by type; a new type is appended."
                ),
                "additionalProperties": True,
            },
        },
        "required": ["identifier", "platform", "site_data_update"],
    },
}

registry.register(
    name="update_website_data",
    toolset="web",
    schema=UPDATE_WEBSITE_DATA_SCHEMA,
    handler=_handle_update_website_data,
    check_fn=_supabase_available,
    emoji="🌐",
)
