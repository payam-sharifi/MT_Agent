"""Update the active easyWebBuilder website in Supabase."""

from __future__ import annotations

import json
import logging

from tools.registry import registry
from tools.website_store import supabase, update_website_content

logger = logging.getLogger(__name__)


def _handle_update_website_content(args: dict, **kwargs) -> str:
    del kwargs
    try:
        result = update_website_content(
            sender_id=str(args.get("identifier") or args.get("sender_id") or ""),
            platform=str(args.get("platform") or ""),
            content=args.get("content") or {},
            business_name=str(args.get("business_name") or ""),
            business_type=str(args.get("business_type") or ""),
            theme=str(args.get("theme") or ""),
        )
    except Exception as exc:
        logger.warning("update_website_content failed: %s", exc, exc_info=True)
        result = {"error": str(exc)}
    return json.dumps(result, ensure_ascii=False)


def _supabase_available() -> bool:
    return supabase is not None


UPDATE_WEBSITE_CONTENT_SCHEMA = {
    "name": "update_website_content",
    "description": (
        "Merge edits into the active website's content and publish them. "
        "Preserves fields you do not send. Returns https://[slug].easywebbuilder.de. "
        "identifier is the Telegram ID or WhatsApp phone from the lookup line."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "identifier": {
                "type": "string",
                "description": "Telegram numeric user ID or WhatsApp phone (sender_id). Never invent it.",
            },
            "platform": {
                "type": "string",
                "enum": ["telegram", "whatsapp"],
            },
            "business_name": {
                "type": "string",
                "description": "Business name. On a new placeholder site this also sets the public slug.",
            },
            "business_type": {
                "type": "string",
                "description": "Type of activity, such as cafe, salon, or clinic.",
            },
            "theme": {
                "type": "string",
                "description": "Visual theme: clinic-premium (doctors, dentists, clinics), luxury, zen, corporate, or default. Medical sites get clinic-premium automatically.",
            },
            "content": {
                "type": "object",
                "description": (
                    "Partial content merge. hero {title, subtitle, cta_button}; "
                    "services [{name, price, description}] merged by name; "
                    "contact {address, phone, opening_hours}; "
                    "faq [{question, answer}] merged by question."
                ),
                "additionalProperties": True,
            },
        },
        "required": ["identifier", "platform", "content"],
    },
}

registry.register(
    name="update_website_content",
    toolset="web",
    schema=UPDATE_WEBSITE_CONTENT_SCHEMA,
    handler=_handle_update_website_content,
    check_fn=_supabase_available,
    emoji="🌐",
)
