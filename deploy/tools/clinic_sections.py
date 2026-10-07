"""Tools for the premium clinic template (theme "clinic-premium").

The template shows a section only when it exists in the site JSON and has real
content, so a half-filled site never goes live. These tools write exactly the
shape the template reads (see clinic_content.py).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from tools.clinic_content import (
    CATALOG,
    CLINIC_THEME,
    ITEM_KEYS,
    SECTION_TYPES,
    find_entry,
    is_medical_business,
    merge_section,
    normalize_section,
    overview,
    plain,
    section_status,
    suggestions,
)
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

# Sections that only exist in the clinic template. Under another theme they would stay invisible.
_CLINIC_ONLY = {"checkup", "about", "doctors", "locations", "footer"}


# ------------------------------------------------------------------- helpers


def _open_website(sender_id: str, platform: str) -> tuple[dict | None, dict | None]:
    """Returns (website, error_result)."""
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
    """Put `entry` where the first section of that type was. None removes it."""
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


def _is_clinic_active(website: dict) -> bool:
    return str(_theme_config(website).get("theme") or "").strip().lower() == CLINIC_THEME


def _activation_update(website: dict, site_data: dict) -> dict:
    """Row fields that switch the site to the clinic template."""
    config = _theme_config(website)
    config["theme"] = CLINIC_THEME
    site_data["theme"] = CLINIC_THEME
    site_data.pop("demo", None)  # real customer: never show the Lumera sample content
    update: dict[str, Any] = {"theme_config": config}
    if not str(website.get("business_type") or "").strip():
        update["business_type"] = "clinic"
    return update


def _ensure_hero(site_data: dict, website: dict) -> None:
    sections = _sections_of(site_data)
    if find_entry(sections, "hero") is None:
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


# ----------------------------------------------------------------- operations


def clinic_overview(sender_id: str, platform: str) -> dict:
    website, error = _open_website(sender_id, platform)
    if error:
        return error
    site_data = _load_json_object(website.get("site_data"))
    result = overview(_sections_of(site_data))
    result.update(_result_base(website))
    result["template_active"] = _is_clinic_active(website)
    result["business_name"] = website.get("business_name") or site_data.get("business_name") or ""
    result["contact_known"] = {
        "phone": bool(_filled(site_data.get("phone"))),
        "address": bool(_filled(site_data.get("address"))),
        "opening_hours": bool(find_entry(_sections_of(site_data), "working_hours")),
    }
    result["how_to_introduce"] = (
        "Tell the customer in their language what each optional section does (use `pitch`), then ask which ones "
        "they want. Add only the ones they choose. For chosen sections ask for the facts in "
        "`customer_facts_needed` and write all titles and descriptions yourself."
    )
    return result


def activate_clinic(sender_id: str, platform: str) -> dict:
    website, error = _open_website(sender_id, platform)
    if error:
        return error
    site_data = _load_json_object(website.get("site_data"))
    already = _is_clinic_active(website)
    extra = _activation_update(website, site_data)
    _ensure_hero(site_data, website)
    _write(website, site_data, None, extra)
    website = {**website, **extra}
    result = overview(_sections_of(site_data))
    result.update(_result_base(website))
    result.update({"status": "success", "template_active": True, "was_active": already})
    return result


def save_section(
    sender_id: str,
    platform: str,
    section: str,
    data: Any,
    replace: bool = False,
    remove: Any = None,
) -> dict:
    section = str(section or "").strip().lower()
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
        # Everything was removed, or only texts were sent for a section without items: no empty shells.
        merged = None
        sections = _replace_entry(sections, section, None)
    if merged is not None:
        sections = _replace_entry(sections, section, merged)
    site_data["sections"] = sections

    # Keep the older content_json mirror in sync so update_website_content cannot resurrect removed items.
    if section in ("services", "faq"):
        content_json[section] = merged.get("items", []) if merged else []
    elif section == "hero" and merged:
        hero = dict(content_json.get("hero") or {})
        for field in ("title", "subtitle", "cta_button"):
            if _filled(merged.get(field)) and isinstance(merged.get(field), str):
                hero[field] = merged[field]
        content_json["hero"] = hero

    extra: dict[str, Any] = {}
    activated = False
    kind = website.get("business_type")
    if not _is_clinic_active(website) and merged is not None and (
        section in _CLINIC_ONLY and is_medical_business(kind, "" if kind else website.get("business_name"))
    ):
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
        "template_active": _is_clinic_active(website) or activated,
        "rejected": rejected,
        "ask_customer": ask,
        "agent_should_write": suggestions(section, final_entry),
        "sections": _state(site_data),
    }
    if activated:
        result["activated_template"] = True
    if not result["template_active"] and section in _CLINIC_ONLY:
        result["warning"] = (
            "This section is saved but the site does not use the clinic template yet, so it is not visible. "
            "Call activate_clinic_template if the customer is a doctor or clinic."
        )
    if rejected:
        result["note"] = "Rejected items were NOT saved. Ask the customer for the missing facts and call again."
    if final_entry is None and not rejected:
        result["note"] = (
            "The section has no content, so it is not on the site. Send its items together with any titles."
        )
    return result


def remove_section(sender_id: str, platform: str, section: str) -> dict:
    section = str(section or "").strip().lower()
    if section not in CATALOG:
        return {"error": f"unknown section '{section}'", "sections": list(SECTION_TYPES)}
    if CATALOG[section]["core"]:
        return {
            "error": "core_section",
            "message": f"'{section}' is part of every site. Edit it with save_clinic_section instead of removing it.",
        }
    website, error = _open_website(sender_id, platform)
    if error:
        return error
    site_data = _load_json_object(website.get("site_data"))
    sections = _sections_of(site_data)
    existed = find_entry(sections, section) is not None
    site_data["sections"] = _replace_entry(sections, section, None)
    # Direct top-level keys also count for the template, so clear those too.
    for key in (section, f"{section}s"):
        if key in site_data and key != "sections":
            site_data.pop(key, None)
    _write(website, site_data, None)
    return {
        "status": "success",
        "section": section,
        "removed": existed,
        **_result_base(website),
        "sections": _state(site_data),
    }


# ----------------------------------------------------------------- tool glue


def _available() -> bool:
    return supabase is not None


def _run(fn, args: dict) -> str:
    try:
        result = fn(args)
    except Exception as exc:  # the agent must see the failure
        logger.warning("%s failed: %s", fn.__name__, exc, exc_info=True)
        result = {"error": str(exc)}
    return json.dumps(result, ensure_ascii=False, default=str)


def _ids(args: dict) -> tuple[str, str]:
    return str(args.get("identifier") or args.get("sender_id") or ""), str(args.get("platform") or "")


def _handle_overview(args: dict, **kwargs) -> str:
    del kwargs
    return _run(lambda a: clinic_overview(*_ids(a)), args)


def _handle_activate(args: dict, **kwargs) -> str:
    del kwargs
    return _run(lambda a: activate_clinic(*_ids(a)), args)


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
    "name": "clinic_template_overview",
    "description": (
        "Doctor/clinic template: list every section (hero, services, checkup, about, doctors, locations, faq, footer) "
        "with a one-line pitch, the customer facts it needs, and whether it is active on the customer's site. "
        "Use it to introduce the optional sections to the customer and to see what is still missing."
    ),
    "parameters": {"type": "object", "properties": dict(_IDENTITY), "required": ["identifier", "platform"]},
}

ACTIVATE_SCHEMA = {
    "name": "activate_clinic_template",
    "description": (
        "Switch the active website to the premium clinic template (theme clinic-premium). Use it when the customer is a "
        "doctor, dentist or clinic and the site does not use the template yet. Existing hero, services, hours and FAQ "
        "stay. Returns the section overview."
    ),
    "parameters": {"type": "object", "properties": dict(_IDENTITY), "required": ["identifier", "platform"]},
}

SAVE_SCHEMA = {
    "name": "save_clinic_section",
    "description": (
        "Add or change one section of the clinic template and publish it. Lists merge by key (name or question), so send "
        "only new or changed items. Items without the customer's facts (no price, no address, ...) are rejected, not "
        "saved: ask the customer, then call again. Write titles, subtitles and descriptions yourself, preferably as "
        "{\"de\": \"...\", \"en\": \"...\"}. Never invent names, prices, ratings, credentials, or numbers.\n"
        "data shape per section:\n"
        "- hero: {title, subtitle, cta_button, badge, stats:[{value,label}], chief:{name,role,meta}, "
        "rating:{score,reviews}, promise:{title,text}}\n"
        "- services: {items:[{name (plain string), price, description, tags:[...], icon}]}\n"
        "- checkup: {title, subtitle, plans:[{name, price (number), old_price, desc, features:[...], featured, icon}], "
        "discount, note}\n"
        "- about: {title, subtitle, values:[{title, desc, icon}] (max 4), stats:[{value (number), suffix, label}] (max 4)}\n"
        "- doctors: {title, subtitle, items:[{name, specialty, years, rating}]}\n"
        "- locations: {title, subtitle, items:[{name, address, phone, hours}]}\n"
        "- faq: {title, subtitle, items:[{question, answer}]}\n"
        "- footer: {about, emergency}\n"
        "Icons: activity award baby bone brain cpu ear eye flower heart handshake heartpulse hospital languages "
        "microscope pill scan shieldcheck smile sparkles stethoscope syringe thermometer."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **_IDENTITY,
            "section": {"type": "string", "enum": list(SECTION_TYPES)},
            "data": {"type": "object", "additionalProperties": True, "description": "Section data, see the tool description."},
            "replace": {
                "type": "boolean",
                "description": "Replace the whole item list (or stats/values) instead of merging. Default false.",
            },
            "remove": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Names (or FAQ questions, value titles, stat labels) to delete from this section.",
            },
        },
        "required": ["identifier", "platform", "section"],
    },
}

REMOVE_SCHEMA = {
    "name": "remove_clinic_section",
    "description": (
        "Remove an optional section (checkup, about, doctors, locations, faq, footer) from the site because the customer "
        "does not want it. Hero and services cannot be removed."
    ),
    "parameters": {
        "type": "object",
        "properties": {**_IDENTITY, "section": {"type": "string", "enum": [s for s in SECTION_TYPES if not CATALOG[s]["core"]]}},
        "required": ["identifier", "platform", "section"],
    },
}

for _schema, _handler, _emoji in (
    (OVERVIEW_SCHEMA, _handle_overview, "🩺"),
    (ACTIVATE_SCHEMA, _handle_activate, "🩺"),
    (SAVE_SCHEMA, _handle_save, "🩺"),
    (REMOVE_SCHEMA, _handle_remove, "🩺"),
):
    registry.register(
        name=_schema["name"],
        toolset="web",
        schema=_schema,
        handler=_handler,
        check_fn=_available,
        emoji=_emoji,
    )
