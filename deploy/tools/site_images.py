"""Change the pictures on a customer's website (logo, hero, services, doctors, locations, about).

The customer sends a photo in Telegram or WhatsApp. The gateway stores it in its image
cache and tells the agent the file path. `set_site_image` checks the file, uploads it to
the public Supabase Storage bucket `site-images`, and puts the public URL into the site
JSON. The clinic template then shows it. Run deploy/sql/site_images_bucket.sql once first.

An https image link works too: it is downloaded and re-hosted, so the site never depends
on someone else's server.
"""

from __future__ import annotations

import io
import json
import logging
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from tools.clinic_content import find_entry, plain
from tools.clinic_sections import (
    _open_website,
    _replace_entry,
    _result_base,
    _sections_of,
    _write,
)
from tools.registry import registry
from tools.website_store import _load_json_object, supabase

logger = logging.getLogger(__name__)

BUCKET = "site-images"
MAX_BYTES = 5 * 1024 * 1024  # bucket limit
RESIZE_ABOVE_BYTES = 1_500_000
MAX_SIDE = 2400

TARGETS = ("logo", "hero", "about", "service", "doctor", "location")
_NEEDS_ITEM = {"service": "services", "doctor": "doctors", "location": "locations"}
_ITEM_FIELD = {"service": "name", "doctor": "name", "location": "name"}


class ImageError(Exception):
    """Problem the agent should explain to the customer."""


# ------------------------------------------------------------------ file input


def _cache_dirs() -> list[Path]:
    try:
        from hermes_constants import get_hermes_home

        home = Path(get_hermes_home())
    except Exception:  # pragma: no cover - outside the gateway
        home = Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")
    names = ("cache/images", "image_cache", "cache/documents", "document_cache")
    return [(home / name).resolve() for name in names]


def _inside(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _read_local(file_path: str) -> bytes:
    """Only files the gateway cached from the customer's chat. Never arbitrary server files."""
    try:
        path = Path(file_path).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise ImageError(f"bad file path: {exc}") from exc
    if not _inside(path, _cache_dirs()):
        raise ImageError("file_path must be the image path from the chat message ('Image attached at: ...').")
    if not path.is_file():
        raise ImageError("the image file no longer exists. Ask the customer to send the photo again.")
    if path.stat().st_size > 25 * 1024 * 1024:
        raise ImageError("the image is too large (over 25 MB).")
    return path.read_bytes()


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        _check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ImageError("only https image links are accepted.")
    try:
        from tools.url_safety import is_safe_url

        if not is_safe_url(url):
            raise ImageError("that link points to a private or blocked address.")
    except ImportError:  # pragma: no cover - older agent without url_safety
        host = parsed.hostname.lower()
        if host in {"localhost"} or host.endswith((".local", ".internal")) or host.replace(".", "").isdigit():
            raise ImageError("that link is not allowed.")


def _download(url: str) -> bytes:
    _check_url(url)
    opener = urllib.request.build_opener(_SafeRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "easyWebBuilder/1.0", "Accept": "image/*"})
    try:
        with opener.open(request, timeout=12) as response:
            ctype = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype and not ctype.startswith("image/"):
                raise ImageError("that link is not an image.")
            data = response.read(25 * 1024 * 1024 + 1)
    except urllib.error.URLError as exc:
        raise ImageError(f"could not download the image: {exc.reason if hasattr(exc, 'reason') else exc}") from exc
    if len(data) > 25 * 1024 * 1024:
        raise ImageError("the image is too large (over 25 MB).")
    return data


# --------------------------------------------------------------- image checks


def _sniff(data: bytes) -> tuple[str, str]:
    """(mime, ext) from the file's first bytes. The file name is never trusted."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    raise ImageError("unsupported image type. Use JPG, PNG or WebP (iPhone HEIC photos: send as a normal photo).")


def prepare_image(data: bytes) -> tuple[bytes, str, str]:
    """Validate, and shrink big photos. Returns (bytes, mime, ext)."""
    if not data:
        raise ImageError("the image is empty.")
    mime, ext = _sniff(data)
    try:
        from PIL import Image
    except ImportError:
        if len(data) > MAX_BYTES:
            raise ImageError("the image is over 5 MB. Ask for a smaller one.")
        return data, mime, ext

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception as exc:
        raise ImageError("the file is not a readable image.") from exc

    big = len(data) > RESIZE_ABOVE_BYTES or max(image.size) > MAX_SIDE
    if not big:
        return data, mime, ext
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    if has_alpha:
        image.convert("RGBA").save(out, format="PNG", optimize=True)
        result, mime, ext = out.getvalue(), "image/png", "png"
    else:
        image.convert("RGB").save(out, format="JPEG", quality=85, optimize=True)
        result, mime, ext = out.getvalue(), "image/jpeg", "jpg"
    if len(result) > MAX_BYTES:
        raise ImageError("the image is still over 5 MB after shrinking. Ask for a smaller one.")
    return result, mime, ext


# ---------------------------------------------------------------------- upload


def _upload(website_id: str, target: str, data: bytes, mime: str, ext: str) -> str:
    name = f"{website_id}/{target}-{uuid.uuid4().hex[:12]}.{ext}"
    bucket = supabase.storage.from_(BUCKET)
    try:
        bucket.upload(name, data, {"content-type": mime, "cache-control": "31536000"})
    except Exception as exc:
        text = str(exc)
        if "not found" in text.lower() or "bucket" in text.lower():
            raise ImageError(
                f"storage bucket '{BUCKET}' is not ready. Run deploy/sql/site_images_bucket.sql in Supabase once."
            ) from exc
        if "row-level security" in text.lower() or "unauthorized" in text.lower() or "403" in text:
            raise ImageError("uploads are not allowed yet. Run deploy/sql/site_images_bucket.sql in Supabase.") from exc
        raise ImageError(f"upload failed: {text}") from exc
    url = bucket.get_public_url(name)
    return str(url).rstrip("?")


# ------------------------------------------------------------ site JSON update


def _find_item(items: list, wanted: str, field: str) -> Optional[dict]:
    wanted = wanted.strip().casefold()
    if not wanted:
        return None
    for item in items:
        if isinstance(item, dict) and plain(item.get(field)).casefold() == wanted:
            return item
    matches = [
        item for item in items
        if isinstance(item, dict) and wanted in plain(item.get(field)).casefold()
    ]
    return matches[0] if len(matches) == 1 else None


def _set(entry: dict, url: str) -> None:
    if url:
        entry["image"] = url
    else:
        entry.pop("image", None)


def _apply(site_data: dict, content_json: dict, target: str, item: str, url: str) -> None:
    """Writes `url` ("" removes) into the right place. Raises ImageError when the place does not exist."""
    sections = _sections_of(site_data)
    if target == "logo":
        if url:
            site_data["logo"] = url
        else:
            site_data.pop("logo", None)
            site_data.pop("logo_url", None)
        return

    section_type = {"hero": "hero", "about": "about"}.get(target) or _NEEDS_ITEM[target]
    entry = find_entry(sections, section_type)
    if entry is None:
        if target == "hero":
            entry = {"type": "hero"}
            sections.insert(0, entry)
        else:
            raise ImageError(
                f"the {section_type} section does not exist yet. Add it with save_clinic_section first, "
                "then set the picture."
            )
    entry = dict(entry)

    if target in ("hero", "about"):
        _set(entry, url)
    else:
        items = [dict(x) for x in entry.get("items") or [] if isinstance(x, dict)]
        found = _find_item(items, item, _ITEM_FIELD[target])
        if found is None:
            names = [plain(x.get(_ITEM_FIELD[target])) for x in items]
            raise ImageError(f"no {target} named '{item}'. Existing: {', '.join(n for n in names if n) or 'none'}.")
        _set(found, url)
        entry["items"] = items
        if target == "service":
            content_json["services"] = items  # keep the older mirror in sync
    site_data["sections"] = _replace_entry(sections, section_type, entry)


def set_image(
    sender_id: str,
    platform: str,
    target: str,
    item: str = "",
    file_path: str = "",
    url: str = "",
    remove: bool = False,
) -> dict:
    target = str(target or "").strip().lower()
    if target not in TARGETS:
        return {"error": f"unknown target '{target}'", "targets": list(TARGETS)}
    item = str(item or "").strip()
    if target in _NEEDS_ITEM and not item:
        return {"error": f"item is required for target '{target}' (the {_ITEM_FIELD[target]} it belongs to)"}

    website, error = _open_website(sender_id, platform)
    if error:
        return error
    site_data = _load_json_object(website.get("site_data"))
    content_json = _load_json_object(website.get("content_json"))

    try:
        if remove:
            public_url = ""
        else:
            if bool(file_path) == bool(url):
                return {"error": "give exactly one of file_path (photo from the chat) or url (https image link)"}
            # Check that the place exists before uploading anything.
            _apply(json.loads(json.dumps(site_data)), json.loads(json.dumps(content_json)), target, item, "x")
            data = _read_local(file_path) if file_path else _download(url)
            data, mime, ext = prepare_image(data)
            public_url = _upload(str(website["id"]), target, data, mime, ext)
        _apply(site_data, content_json, target, item, public_url)
    except ImageError as exc:
        return {"error": "image_not_saved", "message": str(exc)}

    _write(website, site_data, content_json)
    return {
        "status": "success",
        "target": target,
        "item": item,
        "removed": bool(remove),
        "image_url": public_url,
        **_result_base(website),
    }


# ------------------------------------------------------------------- tool glue


def _available() -> bool:
    return supabase is not None


def _handle(args: dict, **kwargs) -> str:
    del kwargs
    try:
        result = set_image(
            sender_id=str(args.get("identifier") or args.get("sender_id") or ""),
            platform=str(args.get("platform") or ""),
            target=str(args.get("target") or ""),
            item=str(args.get("item") or ""),
            file_path=str(args.get("file_path") or ""),
            url=str(args.get("url") or ""),
            remove=bool(args.get("remove")),
        )
    except Exception as exc:
        logger.warning("set_site_image failed: %s", exc, exc_info=True)
        result = {"error": str(exc)}
    return json.dumps(result, ensure_ascii=False, default=str)


SET_SITE_IMAGE_SCHEMA = {
    "name": "set_site_image",
    "description": (
        "Put a picture on the customer's website, or remove one. Use it when the customer sends a photo or an image "
        "link and says where it goes. The photo is checked, stored, and published; the tool returns the preview link.\n"
        "target: logo (header and footer), hero (big picture in the start section), about (photo above the "
        "about-us cards), service (one service card, item = service name), doctor (item = doctor name), "
        "location (item = location name).\n"
        "For a photo sent in chat, pass file_path exactly as shown in the message ('Image attached at: <path>'). "
        "Never guess a path. If several photos arrive, ask which one goes where. Section for service/doctor/location/"
        "about must exist already (save_clinic_section first). Only JPG, PNG and WebP."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "identifier": {
                "type": "string",
                "description": "Telegram numeric user ID or WhatsApp phone (sender_id) from the lookup line. Never invent it.",
            },
            "platform": {"type": "string", "enum": ["telegram", "whatsapp"]},
            "target": {"type": "string", "enum": list(TARGETS)},
            "item": {
                "type": "string",
                "description": "Name of the service, doctor or location (required for those targets).",
            },
            "file_path": {"type": "string", "description": "Path of the photo from the chat message."},
            "url": {"type": "string", "description": "https link to an image (it is downloaded and re-hosted)."},
            "remove": {"type": "boolean", "description": "Remove the picture from that place instead of setting one."},
        },
        "required": ["identifier", "platform", "target"],
    },
}

registry.register(
    name="set_site_image",
    toolset="web",
    schema=SET_SITE_IMAGE_SCHEMA,
    handler=_handle,
    check_fn=_available,
    emoji="🖼️",
)
