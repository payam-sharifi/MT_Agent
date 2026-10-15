"""Read contact-form enquiries stored in Supabase for a website owner."""

from __future__ import annotations

import json
import logging

from tools.registry import registry
from tools.website_store import list_website_leads, supabase

logger = logging.getLogger(__name__)


def _handle_list_website_leads(args: dict, **kwargs) -> str:
    del kwargs
    try:
        result = list_website_leads(
            sender_id=str(args.get("sender_id") or args.get("identifier") or ""),
            platform=str(args.get("platform") or ""),
            slug=str(args.get("slug") or ""),
            limit=args.get("limit") or 10,
        )
    except Exception as exc:
        logger.warning("list_website_leads failed: %s", exc, exc_info=True)
        result = {"error": str(exc)}
    return json.dumps(result, ensure_ascii=False)


def _supabase_available() -> bool:
    return supabase is not None


LIST_LEADS_SCHEMA = {
    "name": "list_website_leads",
    "description": (
        "List contact-form enquiries (Anfragen, پیام فرم تماس) submitted on this owner's "
        "website. Each row is a visitor request: name, phone, email, message. Use when they "
        "ask about new messages, leads, who contacted them, or form submissions. "
        "sender_id and platform come from the lookup line. Never invent them."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "sender_id": {
                "type": "string",
                "description": "Telegram numeric user ID or WhatsApp phone from the lookup line.",
            },
            "platform": {
                "type": "string",
                "enum": ["telegram", "whatsapp"],
            },
            "slug": {
                "type": "string",
                "description": "Optional website slug. Defaults to the active site, or all sites if none is selected.",
            },
            "limit": {
                "type": "integer",
                "description": "How many recent leads to return. Default 10, max 50.",
            },
        },
        "required": ["sender_id", "platform"],
    },
}

registry.register(
    name="list_website_leads",
    toolset="web",
    schema=LIST_LEADS_SCHEMA,
    handler=_handle_list_website_leads,
    check_fn=_supabase_available,
    emoji="📩",
)
