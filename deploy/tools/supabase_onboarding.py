"""Telegram/WhatsApp identity for easyWebBuilder.

Every inbound message looks the sender up in Supabase. A missing user is
created immediately, together with a first website and a preview URL.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from tools.registry import registry
from tools.clinic_content import CLINIC_THEME, is_medical_business
from tools.website_store import (
    _theme_config,
    build_lookup_prefix,
    create_website,
    ensure_account,
    list_websites,
    normalize_identifier,
    normalize_platform,
    record_preview_confirmation,
    supabase,
    switch_website,
    update_legal_impressum,
    wipe_user_account,
)

logger = logging.getLogger(__name__)

_MESSAGING_PLATFORMS = {
    "telegram": "telegram",
    "whatsapp": "whatsapp",
    "whatsapp_cloud": "whatsapp",
}


def lookup_user(sender_id: str, platform: str) -> dict:
    """Read the sender. Creates the account when it does not exist yet."""
    platform = normalize_platform(platform)
    sender_id = normalize_identifier(sender_id, platform)
    account = ensure_account(sender_id, platform)
    if account.get("error"):
        return {"found": False, "sender_id": sender_id, "platform": platform, "error": account["error"]}
    return {
        "found": True,
        "created": bool(account.get("created")),
        "sender_id": sender_id,
        "platform": platform,
        "needs_choice": bool(account.get("needs_choice")),
        "preview_url": account.get("preview_url") or "",
        "websites": account.get("websites") or [],
    }


def _extract_sender(event: Any, source: Any = None) -> dict:
    source = source if source is not None else getattr(event, "source", None)
    if source is None:
        return {"skipped": True, "reason": "no source"}

    platform_raw = getattr(source, "platform", None)
    platform_value = str(getattr(platform_raw, "value", platform_raw) or "").strip().lower()
    mapped = _MESSAGING_PLATFORMS.get(platform_value)
    if not mapped:
        return {"skipped": True, "reason": f"unsupported platform {platform_value}"}

    sender_id = getattr(source, "user_id", None) or getattr(event, "user_id", None)
    if sender_id is None or str(sender_id).strip() == "":
        return {"skipped": True, "reason": "no sender_id"}
    sender_id = normalize_identifier(str(sender_id), mapped)
    if mapped == "whatsapp" and not sender_id:
        return {"skipped": True, "reason": "empty whatsapp phone"}
    return {"sender_id": sender_id, "platform": mapped}


def attach_inbound_sender_context(event: Any, source: Any = None) -> dict:
    """Identify the sender and make sure they have a website before the model replies."""
    try:
        extracted = _extract_sender(event, source)
        if extracted.get("skipped"):
            return extracted

        sender_id = str(extracted["sender_id"])
        platform = str(extracted["platform"])
        account = ensure_account(sender_id, platform)
        prefix = build_lookup_prefix(account)

        metadata = getattr(event, "metadata", None)
        if not isinstance(metadata, dict):
            try:
                event.metadata = {}
                metadata = event.metadata
            except Exception:
                metadata = None
        if isinstance(metadata, dict):
            if "supabase_original_text" not in metadata:
                metadata["supabase_original_text"] = event.text or ""
            metadata["supabase_sender"] = {
                "sender_id": sender_id,
                "platform": platform,
                "registered": not account.get("error"),
                "created": bool(account.get("created")),
                "preview_url": account.get("preview_url") or "",
                "lookup_prefix": prefix,
                "user": account.get("user"),
            }

        previous = getattr(event, "channel_prompt", None) or ""
        try:
            event.channel_prompt = f"{previous}\n{prefix}".strip() if previous else prefix
        except Exception:
            logger.debug("Could not attach sender context prompt", exc_info=True)

        _bind_skill(event, "supabase-onboarding")
        _bind_skill(event, "update-website")
        _bind_skill(event, "handwerk-template")
        website = account.get("website") or {}
        current_theme = str(_theme_config(website).get("theme") or "").strip().lower()
        if current_theme == CLINIC_THEME or is_medical_business(
            website.get("business_type"), website.get("business_name")
        ):
            _bind_skill(event, "clinic-template")
        logger.info(
            "Supabase sender context attached: %s/%s created=%s",
            platform,
            sender_id,
            bool(account.get("created")),
        )
        return {
            "sender_id": sender_id,
            "platform": platform,
            "registered": not account.get("error"),
            "created": bool(account.get("created")),
            "preview_url": account.get("preview_url") or "",
        }
    except Exception as exc:
        logger.warning("Supabase inbound sender context failed: %s", exc, exc_info=True)
        return {"error": str(exc)}


def _bind_skill(event: Any, skill_name: str) -> None:
    current = getattr(event, "auto_skill", None)
    try:
        if not current:
            event.auto_skill = skill_name
            return
        skills = list(current) if isinstance(current, list) else [current]
        if skill_name not in skills:
            skills.append(skill_name)
            event.auto_skill = skills
    except Exception:
        logger.debug("Could not bind %s skill", skill_name, exc_info=True)


def _dump(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False)


def _handle_lookup_user(args: dict, **kwargs) -> str:
    del kwargs
    return _dump(lookup_user(str(args.get("sender_id") or ""), str(args.get("platform") or "")))


def _handle_list_websites(args: dict, **kwargs) -> str:
    del kwargs
    return _dump(list_websites(str(args.get("sender_id") or ""), str(args.get("platform") or "")))


def _handle_create_website(args: dict, **kwargs) -> str:
    del kwargs
    return _dump(
        create_website(
            sender_id=str(args.get("sender_id") or ""),
            platform=str(args.get("platform") or ""),
            business_name=str(args.get("business_name") or ""),
            business_type=str(args.get("business_type") or ""),
        )
    )


def _handle_switch_website(args: dict, **kwargs) -> str:
    del kwargs
    return _dump(
        switch_website(
            sender_id=str(args.get("sender_id") or ""),
            platform=str(args.get("platform") or ""),
            slug=str(args.get("slug") or ""),
            business_name=str(args.get("business_name") or ""),
        )
    )


def _handle_update_legal(args: dict, **kwargs) -> str:
    del kwargs
    return _dump(
        update_legal_impressum(
            sender_id=str(args.get("sender_id") or ""),
            platform=str(args.get("platform") or ""),
            owner_name=str(args.get("owner_name") or ""),
            address=str(args.get("address") or ""),
            tax_number=str(args.get("tax_number") or ""),
            legal_form=str(args.get("legal_form") or ""),
        )
    )


def _handle_record_confirmation(args: dict, **kwargs) -> str:
    del kwargs
    return _dump(
        record_preview_confirmation(
            sender_id=str(args.get("sender_id") or args.get("identifier") or ""),
            platform=str(args.get("platform") or ""),
            confirmed=bool(args.get("confirmed")),
            summary=str(args.get("summary") or ""),
        )
    )


def _handle_wipe_account(args: dict, **kwargs) -> str:
    del kwargs
    return _dump(
        wipe_user_account(
            sender_id=str(args.get("sender_id") or args.get("identifier") or ""),
            platform=str(args.get("platform") or ""),
            confirmed=bool(args.get("confirmed")),
        )
    )


def _supabase_available() -> bool:
    return supabase is not None


_SENDER_PROPS = {
    "sender_id": {
        "type": "string",
        "description": "Telegram numeric user ID or WhatsApp phone from the lookup line. Never invent it.",
    },
    "platform": {
        "type": "string",
        "enum": ["telegram", "whatsapp"],
        "description": "Messaging platform from the lookup line.",
    },
}

LOOKUP_USER_SCHEMA = {
    "name": "lookup_user",
    "description": (
        "Load the easyWebBuilder account for this Telegram or WhatsApp sender, including "
        "their websites and the active preview URL. A missing user is created with a first website."
    ),
    "parameters": {
        "type": "object",
        "properties": _SENDER_PROPS,
        "required": ["sender_id", "platform"],
    },
}

LIST_WEBSITES_SCHEMA = {
    "name": "list_user_websites",
    "description": (
        "List every website owned by this sender with business name and "
        "https://[slug].easywebbuilder.de preview URL. Use when they ask to list or switch sites."
    ),
    "parameters": {
        "type": "object",
        "properties": _SENDER_PROPS,
        "required": ["sender_id", "platform"],
    },
}

CREATE_WEBSITE_SCHEMA = {
    "name": "create_website",
    "description": (
        "Create another website for this sender from a business name, make it the active site, "
        "and return https://[slug].easywebbuilder.de. The slug is sanitized and kept unique."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **_SENDER_PROPS,
            "business_name": {"type": "string", "description": "Name of the new business."},
            "business_type": {"type": "string", "description": "Optional type of activity, such as cafe or salon."},
        },
        "required": ["sender_id", "platform", "business_name"],
    },
}

SWITCH_WEBSITE_SCHEMA = {
    "name": "switch_active_website",
    "description": (
        "Set which of this sender's websites is being edited. Match by slug or business name. "
        "Returns the selected https://[slug].easywebbuilder.de link."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **_SENDER_PROPS,
            "slug": {"type": "string", "description": "Website slug, without the domain."},
            "business_name": {"type": "string", "description": "Business name, if the slug is unknown."},
        },
        "required": ["sender_id", "platform"],
    },
}

LEGAL_SCHEMA = {
    "name": "update_legal_impressum",
    "description": (
        "Save Impressum fields for the active website: owner name, address, tax ID / USt-IdNr, "
        "and legal form. Returns the preview URL. Pass only the fields the user provided."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **_SENDER_PROPS,
            "owner_name": {"type": "string"},
            "address": {"type": "string"},
            "tax_number": {"type": "string", "description": "Tax number or USt-IdNr."},
            "legal_form": {"type": "string", "description": "Legal form, such as GmbH or Einzelunternehmen."},
        },
        "required": ["sender_id", "platform"],
    },
}

registry.register(
    name="lookup_user",
    toolset="web",
    schema=LOOKUP_USER_SCHEMA,
    handler=_handle_lookup_user,
    check_fn=_supabase_available,
    emoji="🔎",
)
registry.register(
    name="list_user_websites",
    toolset="web",
    schema=LIST_WEBSITES_SCHEMA,
    handler=_handle_list_websites,
    check_fn=_supabase_available,
    emoji="📋",
)
registry.register(
    name="create_website",
    toolset="web",
    schema=CREATE_WEBSITE_SCHEMA,
    handler=_handle_create_website,
    check_fn=_supabase_available,
    emoji="🆕",
)
registry.register(
    name="switch_active_website",
    toolset="web",
    schema=SWITCH_WEBSITE_SCHEMA,
    handler=_handle_switch_website,
    check_fn=_supabase_available,
    emoji="🔀",
)
CONFIRM_SCHEMA = {
    "name": "record_preview_confirmation",
    "description": (
        "Store that the user explicitly approved the current preview. Call ONLY after they said "
        "تایید / بله / YES / ok. Pass confirmed=true. Never call this in the same turn as the edit."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **_SENDER_PROPS,
            "confirmed": {
                "type": "boolean",
                "description": "Must be true. Set only after the user explicitly confirmed the preview.",
            },
            "summary": {
                "type": "string",
                "description": "Short note of what they approved, in their words.",
            },
        },
        "required": ["sender_id", "platform", "confirmed"],
    },
}

WIPE_SCHEMA = {
    "name": "wipe_user_account",
    "description": (
        "Permanently delete this sender's account, every website, and the subdomain so Hermes no "
        "longer knows them. The next message creates a new empty account. First warn the user. "
        "Call with confirmed=true only after they clearly say yes. Irreversible."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **_SENDER_PROPS,
            "confirmed": {
                "type": "boolean",
                "description": "Must be true. Set only after the user confirmed they want everything deleted.",
            },
        },
        "required": ["sender_id", "platform", "confirmed"],
    },
}

registry.register(
    name="update_legal_impressum",
    toolset="web",
    schema=LEGAL_SCHEMA,
    handler=_handle_update_legal,
    check_fn=_supabase_available,
    emoji="⚖️",
)
registry.register(
    name="record_preview_confirmation",
    toolset="web",
    schema=CONFIRM_SCHEMA,
    handler=_handle_record_confirmation,
    check_fn=_supabase_available,
    emoji="✅",
)
registry.register(
    name="wipe_user_account",
    toolset="web",
    schema=WIPE_SCHEMA,
    handler=_handle_wipe_account,
    check_fn=_supabase_available,
    emoji="🗑️",
)
