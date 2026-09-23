"""Supabase onboarding for Telegram and WhatsApp senders.

Inbound messages only identify the sender. Registration happens later, after
the agent has collected business_name, owner_name, and subdomain in chat.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

SUPABASE_URL = "https://rgqrpzsbblflxghyahnx.supabase.co"
SUPABASE_KEY = "sb_publishable_nyxKnB8H3IhRj41DBzpw3w_64wl_dbZ"

_MESSAGING_PLATFORMS = {
    "telegram": "telegram",
    "whatsapp": "whatsapp",
    "whatsapp_cloud": "whatsapp",
}

try:
    from supabase import create_client

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as exc:  # pragma: no cover - missing extra in lean installs
    create_client = None  # type: ignore[assignment]
    supabase = None
    logger.warning("supabase client unavailable: %s", exc)


def check_and_register_user(
    sender_id: str,
    platform: str,
    business_name: str,
    owner_name: str,
    subdomain: str,
) -> dict:
    """
    Register a Telegram/WhatsApp user in Supabase after business details are known.
    Creates the user and website record via handle_user_onboarding.
    """
    sender_id = str(sender_id)
    platform = str(platform or "").strip().lower()
    business_name = str(business_name or "").strip()
    owner_name = str(owner_name or "").strip()
    subdomain = str(subdomain or "").strip().lower().replace(" ", "-")

    if platform not in {"telegram", "whatsapp"}:
        return {"error": "platform must be 'telegram' or 'whatsapp'"}
    if not sender_id.strip():
        return {"error": "sender_id is required"}
    if not business_name or not owner_name or not subdomain:
        return {
            "error": "business_name, owner_name, and subdomain are required before registration",
        }

    phone = str(sender_id) if platform == "whatsapp" else None
    telegram_id = str(sender_id) if platform == "telegram" else None
    params = {
        "p_phone": phone,
        "p_telegram_id": telegram_id,
        "p_name": owner_name,
        "p_business_name": business_name,
        "p_subdomain": subdomain,
    }
    print(
        f"[supabase_onboarding] p_telegram_id={params['p_telegram_id']!r} "
        f"p_phone={params['p_phone']!r} p_name={params['p_name']!r} "
        f"p_business_name={params['p_business_name']!r} p_subdomain={params['p_subdomain']!r}",
        flush=True,
    )

    try:
        if supabase is None:
            return {"error": "supabase package is not installed in the Hermes environment"}

        response = supabase.rpc("handle_user_onboarding", params).execute()

        if response.data:
            return response.data[0] if isinstance(response.data, list) else response.data
        return {"error": "No data returned from database"}
    except Exception as e:
        return {"error": str(e)}


def lookup_user(sender_id: str, platform: str) -> dict:
    """Search public.users by Telegram ID or WhatsApp phone. Never inserts."""
    sender_id = str(sender_id)
    platform = str(platform or "").strip().lower()
    row = lookup_messaging_user(sender_id, platform)
    found = bool(row)
    print(
        f"[supabase_onboarding] lookup platform={platform!r} sender_id={sender_id!r} found={found}",
        flush=True,
    )
    if found:
        return {
            "found": True,
            "sender_id": sender_id,
            "platform": platform,
            "user": row,
        }
    return {
        "found": False,
        "sender_id": sender_id,
        "platform": platform,
        "user": None,
    }


def lookup_messaging_user(sender_id: str, platform: str) -> Optional[dict]:
    """Read-only lookup in public.users. Returns the row or None. Never inserts."""
    if supabase is None:
        return None
    sender_id = str(sender_id)
    platform = str(platform or "").strip().lower()
    try:
        query = supabase.table("users").select("*").limit(1)
        if platform == "telegram":
            query = query.eq("telegram_id", sender_id)
        elif platform == "whatsapp":
            query = query.eq("phone", sender_id)
        else:
            return None
        response = query.execute()
        if response.data:
            return response.data[0]
    except Exception as exc:
        logger.warning("Supabase user lookup failed: %s", exc)
    return None


def _normalize_whatsapp_phone(sender_id: str) -> str:
    """Strip JID/LID/device suffixes down to the bare phone digits."""
    return str(sender_id or "").strip().lstrip("+").split(":", 1)[0].split("@", 1)[0]


def _extract_sender(event: Any, source: Any = None) -> dict:
    """Resolve platform + sender_id from a gateway MessageEvent. Never registers."""
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
    sender_id = str(sender_id)
    if mapped == "whatsapp":
        sender_id = _normalize_whatsapp_phone(sender_id)
        if not sender_id:
            return {"skipped": True, "reason": "empty whatsapp phone"}

    sender_name = str(getattr(source, "user_name", None) or getattr(event, "user_name", None) or "")
    return {
        "sender_id": str(sender_id),
        "platform": str(mapped),
        "sender_name": sender_name,
    }


def attach_inbound_sender_context(event: Any, source: Any = None) -> dict:
    """Identify the Telegram/WhatsApp sender and tell the agent whether they are new.

    Does **not** call handle_user_onboarding. Registration is the agent's job after
    it has collected business details in conversation.
    """
    try:
        extracted = _extract_sender(event, source)
        if extracted.get("skipped"):
            return extracted

        sender_id = str(extracted["sender_id"])
        platform = str(extracted["platform"])
        lookup = lookup_user(sender_id, platform)
        existing = lookup.get("user")
        registered = bool(lookup.get("found"))

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
                "registered": registered,
                "user": existing,
            }

        if registered:
            note = (
                f"easyWebBuilder sender: platform={platform}, sender_id={sender_id}. "
                "This user is already registered in Supabase. Skip onboarding. "
                "Help them with their existing website. To change prices, add services, "
                "edit working hours, FAQ, or site copy, call update_website_data "
                f"with identifier={sender_id}, platform={platform}, and site_data_update. "
                "Store content in site_data.sections (hero, services, working_hours, faq). "
                "Set root site_data.theme from occupation or look/color "
                "(clinical, luxury, zen, corporate, default)."
            )
        else:
            note = (
                f"easyWebBuilder sender: platform={platform}, sender_id={sender_id}. "
                "This user is NOT registered yet. Do NOT call check_and_register_user "
                "on this first message. Greet them, then ask in conversation for: "
                "business/website name (business_name), owner full name (owner_name), "
                "and type of activity. Suggest a subdomain from the business name, "
                "confirm it, then call check_and_register_user with sender_id, platform, "
                "business_name, owner_name, and subdomain. After registration, infer theme "
                "(clinical, luxury, zen, corporate, default) and call update_website_data "
                "with {theme} on the root of site_data."
            )
        previous = getattr(event, "channel_prompt", None) or ""
        try:
            event.channel_prompt = f"{previous}\n{note}".strip() if previous else note
        except Exception:
            logger.debug("Could not attach sender context prompt", exc_info=True)

        if registered:
            _bind_skill(event, "update-website")
        else:
            _bind_skill(event, "supabase-onboarding")
        logger.info(
            "Supabase sender context attached: %s/%s registered=%s",
            platform, sender_id, registered,
        )
        return {
            "sender_id": sender_id,
            "platform": platform,
            "registered": registered,
        }
    except Exception as exc:
        logger.warning("Supabase inbound sender context failed: %s", exc, exc_info=True)
        return {"error": str(exc)}


def _bind_skill(event: Any, skill_name: str) -> None:
    """Load a webbuilder skill on new Telegram/WhatsApp sessions."""
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


def _handle_check_and_register(args: dict, **kwargs) -> str:
    del kwargs
    result = check_and_register_user(
        sender_id=str(args.get("sender_id") or ""),
        platform=str(args.get("platform") or ""),
        business_name=str(args.get("business_name") or ""),
        owner_name=str(args.get("owner_name") or ""),
        subdomain=str(args.get("subdomain") or ""),
    )
    return json.dumps(result, ensure_ascii=False)


def _handle_lookup_user(args: dict, **kwargs) -> str:
    del kwargs
    result = lookup_user(
        sender_id=str(args.get("sender_id") or ""),
        platform=str(args.get("platform") or ""),
    )
    return json.dumps(result, ensure_ascii=False)


def _supabase_available() -> bool:
    return supabase is not None


LOOKUP_USER_SCHEMA = {
    "name": "lookup_user",
    "description": (
        "Search the easyWebBuilder Supabase users table by Telegram ID or WhatsApp phone. "
        "Call this first on Telegram/WhatsApp chats. If found=false, greet the user and "
        "collect business details before calling check_and_register_user. Never inserts."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "sender_id": {
                "type": "string",
                "description": "Telegram numeric user ID or WhatsApp phone number.",
            },
            "platform": {
                "type": "string",
                "enum": ["telegram", "whatsapp"],
                "description": "Messaging platform the sender_id belongs to.",
            },
        },
        "required": ["sender_id", "platform"],
    },
}

CHECK_AND_REGISTER_SCHEMA = {
    "name": "check_and_register_user",
    "description": (
        "Register a Telegram or WhatsApp user and their website in the easyWebBuilder "
        "Supabase database. Call ONLY after the user has given business_name, owner_name, "
        "and a confirmed subdomain. Never call on the first greeting message. "
        "sender_id is the Telegram numeric ID or WhatsApp phone; platform is telegram or whatsapp."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "sender_id": {
                "type": "string",
                "description": "Telegram numeric user ID or WhatsApp phone number.",
            },
            "platform": {
                "type": "string",
                "enum": ["telegram", "whatsapp"],
                "description": "Messaging platform the sender_id belongs to.",
            },
            "business_name": {
                "type": "string",
                "description": "Business / website name collected from the user.",
            },
            "owner_name": {
                "type": "string",
                "description": "Owner's full name (first and last name).",
            },
            "subdomain": {
                "type": "string",
                "description": "Suggested (and user-confirmed) website subdomain slug.",
            },
        },
        "required": ["sender_id", "platform", "business_name", "owner_name", "subdomain"],
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
    name="check_and_register_user",
    toolset="web",
    schema=CHECK_AND_REGISTER_SCHEMA,
    handler=_handle_check_and_register,
    check_fn=_supabase_available,
    emoji="🧾",
)
