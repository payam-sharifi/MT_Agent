"""Content rules for the "clinic-premium" website template (Lumera).

Pure functions only (no Supabase here) so the rules are easy to test.

The template renders a section only when it exists in `site_data` AND has enough
real content. That is why every writer here normalises the data to exactly the
shape the template reads and rejects items that lack the customer's own facts
(names, prices, addresses). Text that the agent can write itself (titles,
subtitles, descriptions) is never a reason to reject.

Texts may be a plain string or a `{"de": "...", "en": "..."}` map. The template
picks the visitor's language. Always send both when you can.
"""

from __future__ import annotations

import re
from typing import Any

CLINIC_THEME = "clinic-premium"

# Business types that should get the clinic template automatically.
_MEDICAL_WORDS = (
    "doctor", "dr.", "clinic", "klinik", "praxis", "arzt", "ärzt", "aerzt", "zahnarzt",
    "dentist", "dental", "zahnmed", "orthop", "physio", "medical", "medizin", "hautarzt", "dermatolog",
    "kinderarzt", "pediatric", "gynäkolog", "gynaekolog", "radiolog", "augenarzt", "ophthalm",
    "psychotherap", "heilpraktiker", "healthcare", "health care", "therap",
    "پزشک", "دکتر", "کلینیک", "مطب", "دندان", "درمانگاه", "بیمارستان", "فیزیوتراپ", "متخصص",
)

# Themes that a medical business may be silently upgraded from.
_UPGRADEABLE_THEMES = {"", "default", "clinical", "medical", "none"}

# Icon names the template knows (anything else falls back to a stethoscope).
ICONS = (
    "activity", "award", "baby", "bone", "brain", "cpu", "ear", "eye", "flower", "heart", "handshake",
    "heartpulse", "hospital", "languages", "microscope", "pill", "scan", "shieldcheck", "smile",
    "sparkles", "stethoscope", "syringe", "thermometer",
)

LANGS = ("de", "en")

# What the agent can tell the customer about each optional part of the template.
CATALOG: dict[str, dict[str, Any]] = {
    "hero": {
        "label": "Hero / Startbereich",
        "core": True,
        "pitch": "The big first screen: headline, short subtitle, appointment button. Optional extras: key figures, "
        "the lead doctor's name plate, a Google-rating card.",
        "needs": ["title (agent can write)", "subtitle (agent can write)", "cta_button (agent can write)"],
        "optional": ["badge", "stats [{value,label}] (real numbers only)", "chief {name,role,meta}",
                     "rating {score,reviews} (real rating only)", "promise {title,text}", "pill {value,text}"],
    },
    "services": {
        "label": "Leistungen / Services",
        "core": True,
        "pitch": "Cards for each treatment with price and a Book button. Visitors pick a service and book directly.",
        "needs": ["name (customer)", "price (customer)", "description (agent can write)"],
        "optional": ["tags", "icon", "bookable"],
    },
    "checkup": {
        "label": "Check-up-Pakete",
        "core": False,
        "pitch": "Two or three check-up packages side by side (for example Basic / Comfort / Premium), each with a "
        "price and a feature list. One can be highlighted as the recommendation.",
        "needs": ["plan name (customer)", "plan price (customer)", "features (agent drafts, customer confirms)"],
        "optional": ["old_price", "featured", "discount", "note"],
    },
    "about": {
        "label": "Über uns / Warum wir",
        "core": False,
        "pitch": "Why patients choose the practice: up to four value cards (for example modern equipment, short waiting "
        "times) and a strip with key figures (years of experience, patients, ...).",
        "needs": ["values (agent drafts from what the customer says)", "stats (customer, real numbers only)"],
        "optional": ["title", "subtitle"],
    },
    "doctors": {
        "label": "Ärzteteam",
        "core": False,
        "pitch": "Team cards with name and specialty, and a Book button per doctor. Without a photo a neat initials "
        "avatar is shown.",
        "needs": ["name (customer)", "specialty (customer)"],
        "optional": ["years", "rating (real only)"],
    },
    "locations": {
        "label": "Standorte / Karte",
        "core": False,
        "pitch": "Interactive list of branches with address, phone and opening hours. Good for several sites; for a "
        "single practice it works as a clear contact block.",
        "needs": ["name (customer)", "address (customer)"],
        "optional": ["phone", "hours"],
    },
    "faq": {
        "label": "FAQ / Häufige Fragen",
        "core": False,
        "pitch": "Collapsible questions and answers, for example insurance, first visit, languages, parking.",
        "needs": ["question", "answer (customer confirms facts such as insurance or prices)"],
        "optional": ["title", "subtitle"],
    },
    "footer": {
        "label": "Footer-Texte",
        "core": False,
        "pitch": "Short practice description and an emergency note in the footer. Phone, e-mail, address and opening "
        "hours come from the normal contact fields.",
        "needs": [],
        "optional": ["about", "emergency"],
    },
}

SECTION_TYPES = tuple(CATALOG)
# Sections whose entries are lists of items, with the key used to merge by.
ITEM_KEYS = {
    "services": ("items", "name"),
    "checkup": ("plans", "name"),
    "doctors": ("items", "name"),
    "locations": ("items", "name"),
    "faq": ("items", "question"),
}
# Plain-string merge keys so updates match the same entry later.
_PLAIN_KEYS = {"services": "name", "checkup": "name", "doctors": "name", "locations": "name", "faq": "question"}

# ---------------------------------------------------------------- small helpers


def is_medical_business(business_type: Any, business_name: Any = "") -> bool:
    """True for doctors, dentists, clinics, ...

    The business type decides. The name is only a fallback when no type was given,
    so a bakery called "Zahnrad" is not mistaken for a practice.
    """
    haystack = str(business_type or "").strip() or str(business_name or "")
    haystack = haystack.lower()
    return any(word in haystack for word in _MEDICAL_WORDS)


def should_upgrade_theme(current_theme: Any) -> bool:
    return str(current_theme or "").strip().lower() in _UPGRADEABLE_THEMES


def text(value: Any, limit: int = 600) -> Any:
    """Plain string or {de,en} map; returns None when empty."""
    if isinstance(value, dict):
        cleaned = {}
        for lang in LANGS:
            raw = value.get(lang)
            if isinstance(raw, str) and raw.strip():
                cleaned[lang] = raw.strip()[:limit]
        return cleaned or None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str) and value.strip():
        return value.strip()[:limit]
    return None


def plain(value: Any) -> str:
    """One display string out of a text value (used for merge keys and messages)."""
    value = text(value)
    if isinstance(value, dict):
        return value.get("de") or value.get("en") or ""
    return value or ""


def number(value: Any) -> Any:
    """Number from 199, "199", "199,50 €", "ab 1.299 EUR". None when there is no number."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        return None
    match = re.search(r"\d[\d.,\s]*", value)
    if not match:
        return None
    raw = match.group(0).strip().replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    elif raw.count(".") > 1 or re.fullmatch(r"\d{1,3}\.\d{3}", raw):
        raw = raw.replace(".", "")
    try:
        parsed = float(raw)
    except ValueError:
        return None
    return int(parsed) if parsed.is_integer() else parsed


def price_text(value: Any) -> str:
    """Services show the price as text. Keep what the customer wrote ("ab 89 €")."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = f"{value:g}"
    return str(value).strip()[:40] if isinstance(value, str) or value is not None else ""


def string_list(value: Any, limit: int = 8) -> list:
    if isinstance(value, str):
        value = [part for part in re.split(r"[\n;]", value)]
    out: list = []
    if isinstance(value, list):
        for item in value:
            cleaned = text(item, 160)
            if cleaned:
                out.append(cleaned)
    return out[:limit]


def icon_name(value: Any) -> str:
    key = re.sub(r"[^a-z0-9]", "", str(value or "").lower())
    return key if key in ICONS else ""


def _put(target: dict, key: str, value: Any) -> None:
    if value not in (None, "", [], {}):
        target[key] = value


def item_key(section: str, item: dict) -> str:
    field = _PLAIN_KEYS.get(section, "name")
    return plain(item.get(field)).casefold()


# ------------------------------------------------------------- item normalisers
# Each returns (clean_item | None, missing_customer_facts | reasons).


def _service(raw: dict) -> tuple:
    out: dict = {}
    name = plain(raw.get("name") or raw.get("title"))
    if not name:
        return None, ["name"]
    out["name"] = name  # services merge by a plain-string name
    title = text(raw.get("title")) if isinstance(raw.get("title"), dict) else None
    _put(out, "title", title)
    _put(out, "description", text(raw.get("description") or raw.get("desc")))
    price = raw.get("price")
    if price not in (None, ""):
        out["price"] = price_text(price)
    _put(out, "tags", string_list(raw.get("tags"), 5))
    _put(out, "icon", icon_name(raw.get("icon")))
    if isinstance(raw.get("bookable"), bool):
        out["bookable"] = raw["bookable"]
    missing = [] if out.get("price") else ["price"]
    return out, missing


def _plan(raw: dict) -> tuple:
    name = text(raw.get("name") or raw.get("title"))
    if not name:
        return None, ["name"]
    price = number(raw.get("price"))
    if price is None:
        return None, ["price"]
    out: dict = {"name": plain(name) if not isinstance(name, dict) else name, "price": price}
    _put(out, "desc", text(raw.get("desc") or raw.get("description")))
    old = number(raw.get("old_price") if raw.get("old_price") is not None else raw.get("oldPrice"))
    _put(out, "oldPrice", old)
    features = string_list(raw.get("features"))
    _put(out, "features", features)
    if isinstance(raw.get("featured"), bool):
        out["featured"] = raw["featured"]
    _put(out, "icon", icon_name(raw.get("icon")))
    return out, [] if features else ["features"]


def _value(raw: dict) -> dict | None:
    title = text(raw.get("title") or raw.get("name"))
    if not title:
        return None
    out: dict = {"title": title}
    _put(out, "desc", text(raw.get("desc") or raw.get("description")))
    _put(out, "icon", icon_name(raw.get("icon")))
    return out


def _stat(raw: dict) -> dict | None:
    value = number(raw.get("value"))
    label = text(raw.get("label"))
    if value is None or not label:
        return None
    out: dict = {"value": value, "label": label}
    suffix = raw.get("suffix")
    if isinstance(suffix, str) and suffix.strip():
        out["suffix"] = suffix.strip()[:6]
    return out


def _doctor(raw: dict) -> tuple:
    name = plain(raw.get("name") or raw.get("title"))
    if not name:
        return None, ["name"]
    specialty = text(raw.get("specialty") or raw.get("spec") or raw.get("role"))
    if not specialty:
        return None, ["specialty"]
    out: dict = {"name": name, "specialty": specialty}
    years = number(raw.get("years"))
    _put(out, "years", years)
    rating = number(raw.get("rating"))
    if rating is not None and 0 < rating <= 5:
        out["rating"] = rating
    return out, []


def _branch(raw: dict) -> tuple:
    name = text(raw.get("name") or raw.get("title"), 120)
    if not name:
        return None, ["name"]
    address = text(raw.get("address"))
    if not address:
        return None, ["address"]
    out: dict = {"name": name, "address": address}
    _put(out, "phone", text(raw.get("phone"), 40))
    _put(out, "hours", text(raw.get("hours")))
    return out, []


def _faq_item(raw: dict) -> tuple:
    question = text(raw.get("question") or raw.get("q"), 300)
    answer = text(raw.get("answer") or raw.get("a"), 1200)
    if not question:
        return None, ["question"]
    if not answer:
        return None, ["answer"]
    return {"question": question, "answer": answer}, []


_ITEM_NORMALISERS = {
    "services": _service,
    "checkup": _plan,
    "doctors": _doctor,
    "locations": _branch,
    "faq": _faq_item,
}


def _as_list(value: Any) -> list:
    if isinstance(value, dict):
        value = value.get("items")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


# ------------------------------------------------------------------- sections


def normalize_section(section: str, data: Any) -> dict:
    """Clean `data` for one section.

    Returns {"clean": {...}, "rejected": [{item, missing}], "ask_customer": [...],
             "agent_can_write": [...]}.
    `clean` only holds fields present in `data` (a partial update).
    """
    if section not in CATALOG:
        raise ValueError(f"unknown section: {section}")
    data = data if isinstance(data, dict) else {"items": data} if isinstance(data, list) else {}
    clean: dict = {}
    rejected: list = []
    ask: list = []

    for field in ("eyebrow", "title", "subtitle"):
        _put(clean, field, text(data.get(field), 160))

    if section == "hero":
        for field in ("subtitle", "badge", "cta_button"):
            _put(clean, field, text(data.get(field) or (data.get("cta") if field == "cta_button" else None), 160))
        stats = [s for s in (_stat_hero(x) for x in _as_list(data.get("stats"))) if s]
        _put(clean, "stats", stats[:4])
        for nested, fields in (
            ("chief", ("name", "role", "meta", "available")),
            ("rating", ("score", "reviews")),
            ("promise", ("title", "text")),
            ("pill", ("value", "text")),
        ):
            source = data.get(nested)
            if isinstance(source, dict):
                block = {f: text(source.get(f), 160) for f in fields if text(source.get(f), 160)}
                _put(clean, nested, block)
    elif section == "about":
        values = [v for v in (_value(x) for x in _as_list(data.get("values") or data.get("items"))) if v]
        stats = [s for s in (_stat(x) for x in _as_list(data.get("stats"))) if s]
        _put(clean, "values", values[:4])
        _put(clean, "stats", stats[:4])
    elif section == "footer":
        for field in ("about", "emergency"):
            _put(clean, field, text(data.get(field), 400))
    else:
        list_key, _ = ITEM_KEYS[section]
        incoming = _as_list(data.get(list_key) if data.get(list_key) is not None else data.get("items"))
        if section == "faq" and not incoming and isinstance(data.get("faq"), list):
            incoming = _as_list(data.get("faq"))
        normaliser = _ITEM_NORMALISERS[section]
        items = []
        for raw in incoming:
            item, missing = normaliser(raw)
            label = plain(raw.get("name") or raw.get("title") or raw.get("question") or raw.get("q")) or "?"
            if item is None:
                rejected.append({"item": label, "missing": missing})
                ask.extend(f"{label}: {m}" for m in missing)
                continue
            if missing:  # kept, but worth a follow-up
                ask.extend(f"{label}: {m}" for m in missing)
            items.append(item)
        clean[list_key] = items
        if section == "checkup":
            for field in ("discount", "note", "featuredLabel"):
                _put(clean, field, text(data.get(field), 200))
            if isinstance(data.get("currency"), str) and data["currency"].strip():
                clean["currency"] = data["currency"].strip()[:4]

    return {"clean": clean, "rejected": rejected, "ask_customer": ask}


def _stat_hero(raw: dict) -> dict | None:
    value = text(raw.get("value"), 24)
    label = text(raw.get("label"), 60)
    if not value or not label:
        return None
    return {"value": plain(value), "label": label}


def merge_items(section: str, current: list, incoming: list, replace: bool = False, remove: list | None = None) -> list:
    """Merge `incoming` into `current` by the section's key (name or question)."""
    items = [] if replace else [dict(x) for x in current if isinstance(x, dict)]
    for item in incoming:
        key = item_key(section, item)
        for index, existing in enumerate(items):
            if key and item_key(section, existing) == key:
                merged = dict(existing)
                merged.update(item)
                items[index] = merged
                break
        else:
            items.append(item)
    wanted = {str(r).strip().casefold() for r in (remove or []) if str(r).strip()}
    if wanted:
        items = [x for x in items if item_key(section, x) not in wanted]
    return items


def merge_section(section: str, current: dict | None, update: dict, replace: bool = False, remove: list | None = None) -> dict:
    """Combine an existing sections[] entry with a cleaned update. Scalars overwrite, lists merge by key."""
    base = dict(current) if isinstance(current, dict) else {}
    base["type"] = section
    base.pop("data", None)
    for key, value in update.items():
        if section in ITEM_KEYS and key == ITEM_KEYS[section][0]:
            continue
        if isinstance(value, dict) and isinstance(base.get(key), dict) and key in ("chief", "rating", "promise", "pill"):
            base[key] = {**base[key], **value}
        elif key in ("stats", "values"):
            base[key] = value if replace else _merge_plain_lists(base.get(key), value)
        else:
            base[key] = value
    if section in ITEM_KEYS:
        list_key = ITEM_KEYS[section][0]
        base[list_key] = merge_items(
            section, base.get(list_key) or [], update.get(list_key) or [], replace=replace, remove=remove
        )
    elif remove:
        for key in ("values", "stats"):
            if isinstance(base.get(key), list):
                wanted = {str(r).strip().casefold() for r in remove}
                base[key] = [x for x in base[key] if plain(x.get("title") or x.get("label")).casefold() not in wanted]
    return base


def _merge_plain_lists(current: Any, incoming: list) -> list:
    out = [dict(x) for x in current if isinstance(x, dict)] if isinstance(current, list) else []
    for item in incoming:
        key = plain(item.get("title") or item.get("label")).casefold()
        for index, existing in enumerate(out):
            if key and plain(existing.get("title") or existing.get("label")).casefold() == key:
                out[index] = {**existing, **item}
                break
        else:
            out.append(item)
    return out[:4]


def section_status(section: str, entry: dict | None) -> dict:
    """Would the template render this section? Mirrors the website's own check."""
    if entry is None:
        return {"state": "not_added", "visible": False}
    if entry.get("enabled") is False or entry.get("active") is False:
        return {"state": "disabled", "visible": False}
    if section == "hero":
        return {"state": "active", "visible": True}
    if section == "about":
        visible = bool(entry.get("values") or entry.get("stats"))
    elif section == "footer":
        visible = bool(entry.get("about") or entry.get("emergency"))
    else:
        visible = bool(entry.get(ITEM_KEYS[section][0]))
    return {"state": "active" if visible else "empty", "visible": visible}


def find_entry(sections: list, section: str) -> dict | None:
    for entry in sections or []:
        if isinstance(entry, dict) and str(entry.get("type") or "").lower() == section:
            return entry
    return None


def suggestions(section: str, entry: dict | None) -> list:
    """Copy the agent should write itself (never facts)."""
    if entry is None:
        return []
    out = []
    if section not in ("hero", "services", "footer") and not entry.get("title"):
        out.append("title")
    if section not in ("hero", "services", "footer") and not entry.get("subtitle"):
        out.append("subtitle")
    if section == "hero" and not entry.get("subtitle"):
        out.append("subtitle")
    if section == "services":
        for item in entry.get("items") or []:
            if not item.get("description"):
                out.append(f"description for {plain(item.get('name'))}")
    return out


def overview(sections: list) -> dict:
    """Catalog + current state, for introducing the template to the customer."""
    parts = []
    for section, info in CATALOG.items():
        entry = find_entry(sections, section)
        status = section_status(section, entry)
        parts.append(
            {
                "section": section,
                "label": info["label"],
                "core": info["core"],
                "pitch": info["pitch"],
                "customer_facts_needed": info["needs"],
                "optional": info["optional"],
                **status,
                "agent_should_write": suggestions(section, entry),
            }
        )
    return {
        "template": CLINIC_THEME,
        "sections": parts,
        "available_icons": list(ICONS),
    }
