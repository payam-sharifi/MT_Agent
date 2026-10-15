"""Two-way support chat: customer messages go to the admin inbox."""

from __future__ import annotations

import json
import logging

from tools.registry import registry
from tools.website_store import (
    _websites_for_user,
    lookup_user_row,
    normalize_identifier,
    normalize_platform,
    pick_active_website,
    supabase,
)

logger = logging.getLogger(__name__)

MAX_BODY = 2000


def _rows(response) -> list:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def _public(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "sender": "admin" if row.get("sender") == "admin" else "user",
        "from": "support_team" if row.get("sender") == "admin" else "customer",
        "body": str(row.get("body") or ""),
        "channels": row.get("channels") or [],
        "platform": row.get("platform"),
        "created_at": row.get("created_at"),
    }


def record_support_message(sender_id: str, platform: str, message: str) -> dict:
    platform = normalize_platform(platform)
    sender_id = normalize_identifier(sender_id, platform)
    text = str(message or "").strip()
    if not text:
        return {"error": "message is empty"}
    user = lookup_user_row(sender_id, platform)
    if not user:
        return {"error": "user_not_found"}
    if supabase is None:
        return {"error": "database_unavailable"}

    websites = _websites_for_user(str(user.get("id") or ""))
    active, _needs = pick_active_website(user, websites)
    try:
        response = (
            supabase.table("support_messages")
            .insert(
                {
                    "user_id": user["id"],
                    "website_id": (active or {}).get("id"),
                    "sender": "user",
                    "body": text[:MAX_BODY],
                    "channels": [platform],
                    "platform": platform,
                }
            )
            .execute()
        )
    except Exception as exc:
        logger.warning("record_support_message failed: %s", exc)
        return {"error": str(exc)}

    rows = _rows(response)
    return {
        "status": "success",
        "message": "The support team received this message. It is now in the admin inbox.",
        "saved": _public(rows[0]) if rows else {"body": text[:MAX_BODY], "sender": "user"},
    }


def list_support_thread(sender_id: str, platform: str, limit: int = 10) -> dict:
    platform = normalize_platform(platform)
    sender_id = normalize_identifier(sender_id, platform)
    user = lookup_user_row(sender_id, platform)
    if not user:
        return {"error": "user_not_found"}
    if supabase is None:
        return {"error": "database_unavailable"}
    try:
        cap = max(1, min(int(limit or 10), 50))
    except (TypeError, ValueError):
        cap = 10
    try:
        response = (
            supabase.table("support_messages")
            .select("id, sender, body, channels, platform, created_at")
            .eq("user_id", user["id"])
            .order("created_at", desc=True)
            .limit(cap)
            .execute()
        )
    except Exception as exc:
        logger.warning("list_support_thread failed: %s", exc)
        return {"error": str(exc)}

    messages = [_public(row) for row in _rows(response)]
    messages.reverse()
    last_admin = next((item for item in reversed(messages) if item["sender"] == "admin"), None)
    return {
        "status": "success",
        "count": len(messages),
        "open": bool(messages),
        "awaiting_reply": bool(last_admin and (not messages or messages[-1]["sender"] == "admin")),
        "messages": messages,
    }


def _handle_record(args: dict, **kwargs) -> str:
    del kwargs
    try:
        result = record_support_message(
            sender_id=str(args.get("identifier") or args.get("sender_id") or ""),
            platform=str(args.get("platform") or ""),
            message=str(args.get("message") or ""),
        )
    except Exception as exc:
        logger.warning("record_support_message failed: %s", exc, exc_info=True)
        result = {"error": str(exc)}
    return json.dumps(result, ensure_ascii=False)


def _handle_list(args: dict, **kwargs) -> str:
    del kwargs
    try:
        result = list_support_thread(
            sender_id=str(args.get("identifier") or args.get("sender_id") or ""),
            platform=str(args.get("platform") or ""),
            limit=args.get("limit") or 10,
        )
    except Exception as exc:
        logger.warning("list_support_thread failed: %s", exc, exc_info=True)
        result = {"error": str(exc)}
    return json.dumps(result, ensure_ascii=False)


def _available() -> bool:
    return supabase is not None


_IDENTITY = {
    "identifier": {
        "type": "string",
        "description": "Telegram numeric user ID or WhatsApp phone (sender_id) from the lookup line. Never invent it.",
    },
    "platform": {"type": "string", "enum": ["telegram", "whatsapp"]},
}

registry.register(
    name="record_support_message",
    toolset="web",
    schema={
        "name": "record_support_message",
        "description": (
            "Save a customer message for the human support team so it appears in the admin inbox. "
            "Use when they ask to talk to support / پشتیبانی / Support-Team, or when they are answering "
            "a message that came from the support team. Do not treat it as a website edit."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                **_IDENTITY,
                "message": {
                    "type": "string",
                    "description": "The customer's words for the support team, in their language.",
                },
            },
            "required": ["identifier", "platform", "message"],
        },
    },
    handler=_handle_record,
    check_fn=_available,
    emoji="💬",
)

registry.register(
    name="list_support_thread",
    toolset="web",
    schema={
        "name": "list_support_thread",
        "description": (
            "Read this customer's support-team conversation. Use it when they mention a message from "
            "support, or to see if a human already wrote to them."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                **_IDENTITY,
                "limit": {"type": "integer", "description": "How many recent messages. Default 10."},
            },
            "required": ["identifier", "platform"],
        },
    },
    handler=_handle_list,
    check_fn=_available,
    emoji="💬",
)
