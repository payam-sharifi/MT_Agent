"""Content rules for the handwerk-premium renovation template (VELORA).

Pure functions. A section is shown only when it exists in site_data and has
real customer facts. Never invent project names, prices, ratings or addresses.
"""

from __future__ import annotations

from typing import Any

from tools.clinic_content import (
    find_entry,
    plain,
    text,
)

HANDWERK_THEME = "handwerk-premium"

_HANDWERK_WORDS = (
    "handwerk", "sanierung", "renovierung", "umbau", "trockenbau", "badsanierung",
    "maler", "fliesen", "innenausbau", "wohnbau", "bauunternehmen", "renovation",
    "remodel", "construction", "drywall", "painter", "tiler", "hausrenovierung",
    "altbau", "modernisierung", "fenster", "türen", "tueren",
    "بازسازی", "نوسازی", "ساختمان", "نقاشی",
)

_UPGRADEABLE_THEMES = {"", "default", "services", "handwerk", "zen", "none"}

CATALOG: dict[str, dict[str, Any]] = {
    "hero": {
        "label": "Hero / Startbereich",
        "core": True,
        "pitch": "The first screen: headline, short promise, consultation button, optional figures.",
        "needs": ["title (agent can write)", "subtitle (agent can write)", "cta_button (agent can write)"],
        "optional": ["badge", "bullets", "stats [{value,label}] (real numbers only)"],
    },
    "services": {
        "label": "Leistungen",
        "core": True,
        "pitch": "Cards for each trade (bathroom, full renovation, windows, 3D, funding). Customer can change names, texts and photos.",
        "needs": ["name (customer)", "description (agent can write)"],
        "optional": ["price", "image"],
    },
    "guarantees": {
        "label": "Garantien / Versprechen",
        "core": False,
        "pitch": "Six (or fewer) promise cards: fixed price, start date, one project lead, funding help.",
        "needs": ["title (agent drafts from what they promise)", "description (agent)"],
        "optional": ["icon"],
    },
    "projects": {
        "label": "Referenzen / Projekte",
        "core": False,
        "pitch": "Completed jobs with photo, area, duration and city. Only real projects.",
        "needs": ["title (customer)", "city or area (customer)"],
        "optional": ["duration", "kind", "image"],
    },
    "reviews": {
        "label": "Kundenstimmen",
        "core": False,
        "pitch": "Real client quotes. Never invent reviews or star ratings.",
        "needs": ["name (customer)", "text (customer)"],
        "optional": ["rating (real only)", "source"],
    },
    "quality": {
        "label": "Hinter den Kulissen",
        "core": False,
        "pitch": "A short quality / site-progress block with an optional photo.",
        "needs": ["title (agent)", "subtitle (agent)"],
        "optional": ["image"],
    },
    "team": {
        "label": "Team",
        "core": False,
        "pitch": "People cards with name and role. Photos optional; initials if none.",
        "needs": ["name (customer)", "role (customer)"],
        "optional": ["image"],
    },
    "before_after": {
        "label": "Vorher–Nachher",
        "core": False,
        "pitch": "Before and after photos of real jobs, with area and city.",
        "needs": ["title (customer)"],
        "optional": ["beforeImage", "afterImage", "area", "duration", "city"],
    },
    "financing": {
        "label": "Finanzierungsrechner",
        "core": False,
        "pitch": "A simple monthly-rate calculator. Labels only — no bank partner required.",
        "needs": [],
        "optional": ["title", "subtitle"],
    },
    "process": {
        "label": "Ablauf / 4 Schritte",
        "core": False,
        "pitch": "How a project runs: consult, 3D offer, start, handover. Agent writes the steps.",
        "needs": ["step title", "step description"],
        "optional": [],
    },
    "faq": {
        "label": "FAQ",
        "core": False,
        "pitch": "Collapsible questions: duration, living on site, funding, fixed price.",
        "needs": ["question", "answer (customer confirms facts)"],
        "optional": ["title"],
    },
    "contact": {
        "label": "Kontakt & Standorte",
        "core": False,
        "pitch": "Coverage, headquarters and branch addresses.",
        "needs": ["name (customer)", "address (customer)"],
        "optional": ["phone", "coverage", "hqAddress"],
    },
    "footer": {
        "label": "Footer-Texte",
        "core": False,
        "pitch": "Short company line in the footer. Phone and email come from contact fields.",
        "needs": [],
        "optional": ["about"],
    },
}

SECTION_TYPES = tuple(CATALOG)
ITEM_KEYS = {
    "services": ("items", "name"),
    "guarantees": ("items", "title"),
    "projects": ("items", "title"),
    "reviews": ("items", "name"),
    "team": ("items", "name"),
    "before_after": ("items", "title"),
    "process": ("items", "title"),
    "faq": ("items", "question"),
    "contact": ("items", "name"),
}

HANDWERK_ONLY = {
    "guarantees", "projects", "reviews", "quality", "team",
    "before_after", "financing", "process", "contact", "footer",
}


def is_handwerk_business(business_type: Any, business_name: Any = "") -> bool:
    haystack = str(business_type or "").strip() or str(business_name or "")
    haystack = haystack.lower()
    return any(word in haystack for word in _HANDWERK_WORDS)


def should_upgrade_handwerk_theme(current_theme: Any) -> bool:
    return str(current_theme or "").strip().lower() in _UPGRADEABLE_THEMES


def _put(target: dict, key: str, value: Any) -> None:
    if value not in (None, "", [], {}):
        target[key] = value


def _as_list(value: Any) -> list:
    if isinstance(value, dict):
        value = value.get("items")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _named(raw: dict, *keys: str) -> tuple:
    for key in keys:
        value = text(raw.get(key))
        if value:
            return value, []
    return None, [keys[0]]


def _service(raw: dict) -> tuple:
    name = plain(raw.get("name") or raw.get("title"))
    if not name:
        return None, ["name"]
    out = {"name": name}
    _put(out, "description", text(raw.get("description") or raw.get("desc")))
    _put(out, "price", text(raw.get("price"), 40))
    return out, []


def _titled(raw: dict, desc_keys: tuple[str, ...] = ("description", "desc")) -> tuple:
    title = text(raw.get("title") or raw.get("name"))
    if not title:
        return None, ["title"]
    out = {"title": title}
    for key in desc_keys:
        _put(out, "description", text(raw.get(key)))
        if out.get("description"):
            break
    return out, []


def _project(raw: dict) -> tuple:
    title = text(raw.get("title") or raw.get("name"))
    if not title:
        return None, ["title"]
    out = {"title": title}
    for key in ("area", "duration", "kind", "city", "description"):
        _put(out, key, text(raw.get(key), 80))
    return out, [] if (out.get("city") or out.get("area")) else ["city or area"]


def _review(raw: dict) -> tuple:
    name = plain(raw.get("name") or raw.get("author"))
    quote = text(raw.get("text") or raw.get("review") or raw.get("quote"), 600)
    if not name:
        return None, ["name"]
    if not quote:
        return None, ["text"]
    out = {"name": name, "text": quote}
    rating = raw.get("rating")
    if isinstance(rating, (int, float)) and 0 < rating <= 5:
        out["rating"] = rating
    _put(out, "source", text(raw.get("source"), 40))
    return out, []


def _member(raw: dict) -> tuple:
    name = plain(raw.get("name"))
    role = text(raw.get("role") or raw.get("specialty"))
    if not name:
        return None, ["name"]
    if not role:
        return None, ["role"]
    return {"name": name, "role": role}, []


def _before(raw: dict) -> tuple:
    title = text(raw.get("title") or raw.get("name"))
    if not title:
        return None, ["title"]
    out = {"title": title}
    for key in ("area", "duration", "kind", "city"):
        _put(out, key, text(raw.get(key), 80))
    return out, []


def _faq(raw: dict) -> tuple:
    question = text(raw.get("question") or raw.get("q"), 300)
    answer = text(raw.get("answer") or raw.get("a"), 1200)
    if not question:
        return None, ["question"]
    if not answer:
        return None, ["answer"]
    return {"question": question, "answer": answer}, []


def _branch(raw: dict) -> tuple:
    name = text(raw.get("name") or raw.get("title"), 120)
    address = text(raw.get("address"))
    if not name:
        return None, ["name"]
    if not address:
        return None, ["address"]
    out = {"name": name, "address": address}
    _put(out, "phone", text(raw.get("phone"), 40))
    return out, []


_ITEM_NORMALISERS = {
    "services": _service,
    "guarantees": _titled,
    "projects": _project,
    "reviews": _review,
    "team": _member,
    "before_after": _before,
    "process": _titled,
    "faq": _faq,
    "contact": _branch,
}


def normalize_section(section: str, data: Any) -> dict:
    if section not in CATALOG:
        raise ValueError(f"unknown section: {section}")
    data = data if isinstance(data, dict) else {"items": data} if isinstance(data, list) else {}
    clean: dict = {}
    rejected: list = []
    ask: list = []
    for field in ("eyebrow", "title", "subtitle"):
        _put(clean, field, text(data.get(field), 200))

    if section == "hero":
        for field in ("subtitle", "badge", "cta_button", "ctaPrimary", "ctaSecondary"):
            _put(clean, field, text(data.get(field) or (data.get("cta") if field == "cta_button" else None), 220))
        bullets = data.get("bullets") or data.get("highlights")
        if isinstance(bullets, list):
            _put(clean, "bullets", [plain(x) for x in bullets if plain(x)][:6])
        stats = []
        for raw in _as_list(data.get("stats")):
            value, label = text(raw.get("value"), 24), text(raw.get("label"), 60)
            if value and label:
                stats.append({"value": plain(value), "label": label})
        _put(clean, "stats", stats[:4])
    elif section in ("quality", "financing", "footer"):
        for field in ("subtitle", "about", "coverage", "hqAddress", "formNote"):
            _put(clean, field, text(data.get(field), 400))
    elif section in ITEM_KEYS:
        list_key, _ = ITEM_KEYS[section]
        incoming = _as_list(data.get(list_key) if data.get(list_key) is not None else data.get("items"))
        items = []
        normaliser = _ITEM_NORMALISERS[section]
        for raw in incoming:
            item, missing = normaliser(raw)
            label = plain(raw.get("name") or raw.get("title") or raw.get("question") or "?")
            if item is None:
                rejected.append({"item": label, "missing": missing})
                ask.extend(f"{label}: {m}" for m in missing)
                continue
            if missing:
                ask.extend(f"{label}: {m}" for m in missing)
            items.append(item)
        clean[list_key] = items
        if section == "contact":
            for field in ("coverage", "hqAddress", "formNote"):
                _put(clean, field, text(data.get(field), 200))

    return {"clean": clean, "rejected": rejected, "ask_customer": ask}


def merge_section(section: str, current: dict | None, update: dict, replace: bool = False, remove: list | None = None) -> dict:
    """Same merge rules as clinic: lists merge by name/title/question."""
    # Temporarily point clinic ITEM_KEYS lookup via local keys by inlining.
    base = dict(current) if isinstance(current, dict) else {}
    base["type"] = section
    base.pop("data", None)
    for key, value in update.items():
        if section in ITEM_KEYS and key == ITEM_KEYS[section][0]:
            continue
        else:
            base[key] = value
    if section in ITEM_KEYS:
        list_key = ITEM_KEYS[section][0]
        # reuse clinic merge_items which reads clinic ITEM_KEYS — so call with a
        # section it knows, or duplicate a tiny merge here.
        current_list = base.get(list_key) or []
        incoming = update.get(list_key) or []
        items = [] if replace else [dict(x) for x in current_list if isinstance(x, dict)]
        field = ITEM_KEYS[section][1]
        def key_of(item: dict) -> str:
            return plain(item.get(field) or item.get("name") or item.get("title") or item.get("question")).casefold()
        for item in incoming:
            key = key_of(item)
            for index, existing in enumerate(items):
                if key and key_of(existing) == key:
                    items[index] = {**existing, **item}
                    break
            else:
                items.append(item)
        wanted = {str(r).strip().casefold() for r in (remove or []) if str(r).strip()}
        if wanted:
            items = [x for x in items if key_of(x) not in wanted]
        base[list_key] = items
    return base


def section_status(section: str, entry: dict | None) -> dict:
    if entry is None:
        return {"state": "not_added", "visible": False}
    if entry.get("enabled") is False or entry.get("active") is False:
        return {"state": "disabled", "visible": False}
    if section in ("hero", "financing", "quality"):
        return {"state": "active", "visible": True}
    if section == "footer":
        visible = bool(entry.get("about"))
    elif section in ITEM_KEYS:
        visible = bool(entry.get(ITEM_KEYS[section][0]))
    else:
        visible = True
    return {"state": "active" if visible else "empty", "visible": visible}


def suggestions(section: str, entry: dict | None) -> list:
    if entry is None:
        return []
    out = []
    if section not in ("hero", "services", "footer") and not entry.get("title"):
        out.append("title")
    if section == "services":
        for item in entry.get("items") or []:
            if not item.get("description"):
                out.append(f"description for {plain(item.get('name'))}")
    return out


def overview(sections: list) -> dict:
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
    return {"template": HANDWERK_THEME, "sections": parts}
