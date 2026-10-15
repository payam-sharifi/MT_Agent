"""Tools for the premium renovation template (theme "handwerk-premium")."""

from __future__ import annotations

import json
import logging
from typing import Any

from tools.handwerk_content import (
    CATALOG,
    HANDWERK_ONLY,
    HANDWERK_THEME,
    HOW_TO_INTRODUCE,
    ITEM_KEYS,
    SECTION_TYPES,
    find_entry,
    is_handwerk_business,
    merge_section,
    normalize_section,
    overview,
    section_status,
    seed_full_template,
    suggestions,
)
from tools.clinic_content import find_entry as _find
from tools.registry import registry
from tools.website_store import (
    _client,
    _filled,
    _load_json_object,
    _theme_config,
    ensure_account,
    preview_url,
    supabase,
)

logger = logging.getLogger(__name__)


def _open_website(sender_id: str, platform: str) -> tuple[dict | None, dict | None]:
    account = ensure_account(sender_id, platform)
    if account.get("error"):
        return None, account
    if account.get("needs_choice") or not account.get("website"):
        return None, {
            "error": "needs_website_choice",
            "websites": account.get("websites") or [],
            "message": "Ask the user which website to edit before changing content.",
        }
    return account["website"], None


def _sections_of(site_data: dict) -> list:
    return [s for s in site_data.get("sections") or [] if isinstance(s, dict)]


def _replace_entry(sections: list, section: str, entry: dict | None) -> list:
    out: list = []
    placed = False
    for current in sections:
        if str(current.get("type") or "").lower() == section:
            if not placed and entry is not None:
                out.append(entry)
            placed = True
            continue
        out.append(current)
    if not placed and entry is not None:
        out.append(entry)
    return out


def _is_active(website: dict) -> bool:
    return str(_theme_config(website).get("theme") or "").strip().lower() == HANDWERK_THEME


def _activation_update(website: dict, site_data: dict) -> dict:
    config = _theme_config(website)
    config["theme"] = HANDWERK_THEME
    config["template"] = HANDWERK_THEME
    site_data["theme"] = HANDWERK_THEME
    site_data["demo"] = True
    update: dict[str, Any] = {"theme_config": config}
    if not str(website.get("business_type") or "").strip():
        update["business_type"] = "handwerk"
    return update


def _ensure_hero(site_data: dict, website: dict) -> None:
    sections = _sections_of(site_data)
    if _find(sections, "hero") is None:
        name = str(website.get("business_name") or site_data.get("business_name") or "").strip()
        if name:
            sections.insert(0, {"type": "hero", "title": name})
    site_data["sections"] = sections


def _write(website: dict, site_data: dict, content_json: dict | None, extra: dict | None = None) -> None:
    update: dict[str, Any] = {"site_data": site_data, "is_published": True, "status": "published"}
    if content_json is not None:
        update["content_json"] = content_json
    update.update(extra or {})
    _client().table("websites").update(update).eq("id", website["id"]).execute()


def _result_base(website: dict) -> dict:
    slug = str(website.get("slug") or "")
    return {"slug": slug, "preview_url": preview_url(slug) if slug else ""}


def _state(site_data: dict) -> list:
    sections = _sections_of(site_data)
    return [
        {"section": name, "label": CATALOG[name]["label"], **section_status(name, find_entry(sections, name))}
        for name in SECTION_TYPES
    ]


def handwerk_overview(sender_id: str, platform: str) -> dict:
    website, error = _open_website(sender_id, platform)
    if error:
        return error
    site_data = _load_json_object(website.get("site_data"))
    result = overview(_sections_of(site_data))
    result.update(_result_base(website))
    result["template_active"] = _is_active(website)
    result["using_defaults"] = bool(site_data.get("demo"))
    result["business_name"] = website.get("business_name") or site_data.get("business_name") or ""
    result["how_to_introduce"] = HOW_TO_INTRODUCE
    return result


def activate_handwerk(sender_id: str, platform: str) -> dict:
    website, error = _open_website(sender_id, platform)
    if error:
        return error
    site_data = seed_full_template(
        _load_json_object(website.get("site_data")),
        str(website.get("business_name") or ""),
    )
    already = _is_active(website)
    extra = _activation_update(website, site_data)
    _ensure_hero(site_data, website)
    _write(website, site_data, None, extra)
    website = {**website, **extra}
    result = overview(_sections_of(site_data))
    result.update(_result_base(website))
    result.update(
        {
            "status": "success",
            "template_active": True,
            "was_active": already,
            "using_defaults": True,
            "ask_user": (
                "Send the preview URL. Explain that the FULL template is showing with starter content. "
                "List what you can change (colors, photos, every section). Wait for تایید, then "
                "call record_preview_confirmation with confirmed=true."
            ),
        }
    )
    return result


def save_section(
    sender_id: str,
    platform: str,
    section: str,
    data: Any,
    replace: bool = False,
    remove: Any = None,
) -> dict:
    section = str(section or "").strip().lower().replace("-", "_")
    if section not in CATALOG:
        return {"error": f"unknown section '{section}'", "sections": list(SECTION_TYPES)}
    if isinstance(data, str) and data.strip():
        try:
            data = json.loads(data)
        except json.JSONDecodeError as exc:
            return {"error": f"data is not valid JSON: {exc}"}
    if not isinstance(data, (dict, list)):
        data = {}
    remove_list = [remove] if isinstance(remove, str) else [r for r in (remove or []) if isinstance(r, str)]

    website, error = _open_website(sender_id, platform)
    if error:
        return error

    normalized = normalize_section(section, data)
    clean, rejected, ask = normalized["clean"], normalized["rejected"], normalized["ask_customer"]
    has_new = any(_filled(value) for key, value in clean.items() if key not in ("eyebrow", "title", "subtitle")) or (
        section in ITEM_KEYS and bool(clean.get(ITEM_KEYS[section][0]))
    )
    texts_only = any(clean.get(k) for k in ("eyebrow", "title", "subtitle"))
    if not has_new and not texts_only and not remove_list:
        return {
            "error": "nothing_to_save",
            "section": section,
            "rejected": rejected,
            "ask_customer": ask,
            "message": "No complete item. Ask the customer for the missing facts, then call again. Nothing was saved.",
            "needs": CATALOG[section]["needs"],
        }

    site_data = _load_json_object(website.get("site_data"))
    content_json = _load_json_object(website.get("content_json"))
    sections = _sections_of(site_data)
    current = find_entry(sections, section)
    merged = merge_section(section, current, clean, replace=replace, remove=remove_list)
    merged.pop("enabled", None)
    merged.pop("active", None)

    if merged is not None and not section_status(section, merged)["visible"]:
        merged = None
        sections = _replace_entry(sections, section, None)
    if merged is not None:
        sections = _replace_entry(sections, section, merged)
    site_data["sections"] = sections

    if section in ("services", "faq"):
        content_json[section] = merged.get("items", []) if merged else []
    elif section == "hero" and merged:
        hero = dict(content_json.get("hero") or {})
        for field in ("title", "subtitle", "cta_button"):
            if _filled(merged.get(field)) and isinstance(merged.get(field), str):
                hero[field] = merged[field]
        content_json["hero"] = hero
    elif section == "contact" and merged:
        contact = dict(content_json.get("contact") or {})
        if _filled(merged.get("phone")):
            site_data["phone"] = merged["phone"]
            contact["phone"] = merged["phone"]
        if _filled(merged.get("email")):
            site_data["email"] = merged["email"]
            contact["email"] = merged["email"]
        if _filled(merged.get("hqAddress")):
            site_data["address"] = merged["hqAddress"]
            contact["address"] = merged["hqAddress"]
        content_json["contact"] = contact

    extra: dict[str, Any] = {}
    activated = False
    kind = website.get("business_type")
    if not _is_active(website) and merged is not None and (
        section in HANDWERK_ONLY and is_handwerk_business(kind, "" if kind else website.get("business_name"))
    ):
        site_data = seed_full_template(site_data, str(website.get("business_name") or ""))
        extra = _activation_update(website, site_data)
        activated = True
    _ensure_hero(site_data, website)
    _write(website, site_data, content_json, extra)

    final_entry = find_entry(_sections_of(site_data), section)
    result: dict[str, Any] = {
        "status": "success",
        "section": section,
        "section_state": section_status(section, final_entry),
        **_result_base(website),
        "template_active": _is_active(website) or activated,
        "rejected": rejected,
        "ask_customer": ask,
        "agent_should_write": suggestions(section, final_entry),
        "sections": _state(site_data),
        "ask_user": (
            "Send the preview URL. Do not treat this save as approved. Wait for explicit "
            "تایید / YES, then call record_preview_confirmation with confirmed=true."
        ),
    }
    if activated:
        result["activated_template"] = True
    if rejected:
        result["note"] = "Rejected items were NOT saved. Ask the customer for the missing facts and call again."
    return result


def remove_section(sender_id: str, platform: str, section: str) -> dict:
    section = str(section or "").strip().lower().replace("-", "_")
    if section not in CATALOG:
        return {"error": f"unknown section '{section}'", "sections": list(SECTION_TYPES)}
    if CATALOG[section]["core"]:
        return {
            "error": "core_section",
            "message": f"'{section}' is part of every site. Edit it with save_handwerk_section instead of removing it.",
        }
    website, error = _open_website(sender_id, platform)
    if error:
        return error
    site_data = _load_json_object(website.get("site_data"))
    sections = _sections_of(site_data)
    existed = find_entry(sections, section) is not None
    site_data["sections"] = _replace_entry(sections, section, None)
    _write(website, site_data, None)
    return {
        "status": "success",
        "section": section,
        "removed": existed,
        **_result_base(website),
        "sections": _state(site_data),
    }


def _available() -> bool:
    return supabase is not None


def _run(fn, args: dict) -> str:
    try:
        result = fn(args)
    except Exception as exc:
        logger.warning("%s failed: %s", fn.__name__, exc, exc_info=True)
        result = {"error": str(exc)}
    return json.dumps(result, ensure_ascii=False, default=str)


def _ids(args: dict) -> tuple[str, str]:
    return str(args.get("identifier") or args.get("sender_id") or ""), str(args.get("platform") or "")


def _handle_overview(args: dict, **kwargs) -> str:
    del kwargs
    return _run(lambda a: handwerk_overview(*_ids(a)), args)


def _handle_activate(args: dict, **kwargs) -> str:
    del kwargs
    return _run(lambda a: activate_handwerk(*_ids(a)), args)


def _handle_save(args: dict, **kwargs) -> str:
    del kwargs
    return _run(
        lambda a: save_section(
            *_ids(a),
            section=str(a.get("section") or ""),
            data=a.get("data"),
            replace=bool(a.get("replace")),
            remove=a.get("remove"),
        ),
        args,
    )


def _handle_remove(args: dict, **kwargs) -> str:
    del kwargs
    return _run(lambda a: remove_section(*_ids(a), section=str(a.get("section") or "")), args)


_IDENTITY = {
    "identifier": {
        "type": "string",
        "description": "Telegram numeric user ID or WhatsApp phone (sender_id) from the lookup line. Never invent it.",
    },
    "platform": {"type": "string", "enum": ["telegram", "whatsapp"]},
}

OVERVIEW_SCHEMA = {
    "name": "handwerk_template_overview",
    "description": (
        "Renovation / plumber template: list every section and every thing you can change "
        "(colors, photos, hours, map, reviews, each block). Use it after activating so you can "
        "pitch the full page and offer edits."
    ),
    "parameters": {"type": "object", "properties": dict(_IDENTITY), "required": ["identifier", "platform"]},
}

ACTIVATE_SCHEMA = {
    "name": "activate_handwerk_template",
    "description": (
        "Switch the site to the premium renovation template and show EVERY section with default "
        "starter content. Use it as soon as the customer is renovation, Sanierung, plumber / Klempner, "
        "or even if they only gave a company name for that trade. Incomplete descriptions still get "
        "the full template. Then send the preview and list what you can change."
    ),
    "parameters": {"type": "object", "properties": dict(_IDENTITY), "required": ["identifier", "platform"]},
}

SAVE_SCHEMA = {
    "name": "save_handwerk_section",
    "description": (
        "Add or change one section of the renovation template and publish it. Lists merge by name/title/question. "
        "hero.stats merge by label — send only the changed row, e.g. [{value:'6 Jahre', label:'Gewährleistung'}]; "
        "the other figures stay. Never invent project names, reviews, prices or addresses. Write titles and "
        "descriptions yourself as {\"de\": \"...\", \"en\": \"...\"}.\n"
        "data shape:\n"
        "- hero: {title, subtitle, cta_button, badge, bullets:[], stats:[{value,label}]}\n"
        "- services: {items:[{name, description, price}]}\n"
        "- guarantees: {title, items:[{title, description}]}\n"
        "- projects: {items:[{title, area, duration, kind, city}]}\n"
        "- reviews: {items:[{name, text, rating}]}\n"
        "- quality: {title, subtitle}\n"
        "- team: {items:[{name, role}]}\n"
        "- before_after: {items:[{title, area, duration, city}]}\n"
        "- financing: {title, subtitle}\n"
        "- process: {items:[{title, description}]}\n"
        "- faq: {items:[{question, answer}]}\n"
        "- contact: {coverage, hqAddress, phone, email, items:[{name, address, phone}]}\n"
        "- footer: {about}\n"
        "- materials: {title, items:[{title, spec}]}\n"
        "- working_hours: {text} or {items:[{days, hours}]}"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **_IDENTITY,
            "section": {"type": "string", "enum": list(SECTION_TYPES)},
            "data": {"type": "object", "additionalProperties": True},
            "replace": {"type": "boolean"},
            "remove": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["identifier", "platform", "section"],
    },
}

REMOVE_SCHEMA = {
    "name": "remove_handwerk_section",
    "description": "Remove an optional renovation-template section the customer does not want. Hero and services stay.",
    "parameters": {
        "type": "object",
        "properties": {
            **_IDENTITY,
            "section": {"type": "string", "enum": [s for s in SECTION_TYPES if not CATALOG[s]["core"]]},
        },
        "required": ["identifier", "platform", "section"],
    },
}

for _schema, _handler, _emoji in (
    (OVERVIEW_SCHEMA, _handle_overview, "🏠"),
    (ACTIVATE_SCHEMA, _handle_activate, "🏠"),
    (SAVE_SCHEMA, _handle_save, "🏠"),
    (REMOVE_SCHEMA, _handle_remove, "🏠"),
):
    registry.register(
        name=_schema["name"],
        toolset="web",
        schema=_schema,
        handler=_handler,
        check_fn=_available,
        emoji=_emoji,
    )
