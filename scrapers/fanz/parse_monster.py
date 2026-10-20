"""Parser de página de monstro do Fanz (/tools/mobs/data/mobdb/<Nome>.php).

Além do registro do monstro, devolve em `related` os mapas, spawns e drops encontrados.
Todo link para /itemdb/ na página de monstro é tratado como drop; o tipo (excellent etc.)
e a categoria vêm do título da seção, do cabeçalho da coluna ou do rótulo da linha.
"""
from __future__ import annotations

import re

from scrapers.common.html import Document, Link, PairIndex, clean
from scrapers.common.ids import slugify
from scrapers.common.model import ParseResult
from scrapers.common.parsing import (
    find_updated_date, parse_bool, parse_duration_seconds, parse_int, parse_range,
)
from scrapers.fanz import urls
from scrapers.fanz.parse_common import find_image, pick_name

LABELS = {
    "level": r"(?:mob |monster )?(?:level|lv|lvl)",
    "hp": r"(?:max |maximum )?(?:hp|life|health)(?: points)?",
    "atk_min": r"min(?:imum)? (?:atk|attack|dmg|damage)",
    "atk_max": r"max(?:imum)? (?:atk|attack|dmg|damage)",
    "atk": r"(?:atk|attack)(?: dmg| damage| power)?|damage|dmg",
    "atk_rate": r"(?:atk|attack) (?:rate|rating|success rate|success)",
    "def": r"(?:def|defense|defence)(?: power)?",
    "def_rate": r"(?:def|defense|defence) (?:rate|rating|success rate|success)",
    "respawn": r"(?:respawn|re spawn|regen|regeneration)(?: time| delay| rate)?|spawn (?:time|delay)",
    "map": r"(?:spawn |spawns |found |location |locations )?(?:map|maps|location|locations|spawn|spawns"
           r"|spawn location|spawn map|spawn maps|found in|appears in)",
    "normal_drop": r"(?:drops? )?normal items?(?: drop| drops)?",
}
NO_NORMAL = re.compile(
    r"(?:does not|doesn'?t|do not|don'?t|won'?t|will not|cannot|can'?t|no)\s+drops?\s+(?:any\s+)?normal", re.IGNORECASE
)
YES_NORMAL = re.compile(r"\bdrops?\s+(?:also\s+)?normal\s+items?", re.IGNORECASE)
DROP_KINDS = [("excellent", r"excellent|exc\b"), ("ancient", r"ancient"), ("socket", r"socket"), ("normal", r"normal")]
DROP_CATEGORIES = [
    ("magic_weapon", r"magic(?:al)? weapons?|staff|staves|sticks?|books?|scepters?"),
    ("weapon", r"(?:attack )?weapons?|swords?|axes?|maces?|spears?|bows?|crossbows?"),
    ("shield", r"shields?"),
    ("armor", r"armou?rs?|sets?|helms?|helmets?|pants|gloves|boots"),
    ("wings", r"wings?"),
    ("jewel", r"jewels?"),
    ("accessory", r"rings?|pendants?|accessor(?:y|ies)"),
]
SKIP_LINK_SECTION = re.compile(r"related|see also|similar", re.IGNORECASE)


def parse_monster(html: str, meta: dict) -> ParseResult:
    url = meta["url"]
    doc = Document(html, base_url=meta.get("final_url") or url)
    pairs = PairIndex(doc.pairs)
    warnings: list[str] = []
    name = pick_name(doc, urls.name_from_url(url), warnings)
    monster_id = slugify(name)

    def take_int(field: str) -> int | None:
        pair = pairs.take(LABELS[field])
        if pair is None:
            return None
        value = parse_int(pair.value)
        if value is None:
            warnings.append(f"{field}: valor não numérico {pair.value!r}")
        return value

    level = take_int("level")
    hp = take_int("hp")
    atk_min, atk_max = take_int("atk_min"), take_int("atk_max")
    atk_pair = pairs.take(LABELS["atk"])
    if atk_pair:
        low, high = parse_range(atk_pair.value)
        atk_min, atk_max = atk_min if atk_min is not None else low, atk_max if atk_max is not None else high
    atk_rate = take_int("atk_rate")
    defense = take_int("def")
    def_rate = take_int("def_rate")
    respawn_pair = pairs.take(LABELS["respawn"])

    provenance = {"season": None, "source": urls.SOURCE_ID, "source_url": url, "scraped_at": meta["fetched_at"]}
    maps = _maps(doc, pairs, warnings, provenance)
    drops = _drops(doc, pairs, monster_id, warnings, provenance)

    record = {
        "id": monster_id,
        "name": name,
        "level": level,
        "hp": hp,
        "atk_min": atk_min,
        "atk_max": atk_max,
        "atk_rate": atk_rate,
        "def": defense,
        "def_rate": def_rate,
        "respawn_seconds": parse_duration_seconds(respawn_pair.value) if respawn_pair else None,
        "respawn_raw": respawn_pair.value if respawn_pair else None,
        "drops_normal_items": _drops_normal_items(doc, pairs),
        "image_url": find_image(doc, name, urls.MOB_IMAGE_PREFIX),
        **provenance,
        "page_updated_at": find_updated_date(doc.text_lines),
    }
    spawns = [{"monster_id": monster_id, "map_id": m["id"], **provenance} for m in maps]
    return ParseResult(
        kind="monster",
        record=record,
        source_file=meta.get("file", ""),
        warnings=warnings,
        unmapped=pairs.unmapped(),
        headings=doc.headings,
        related={"maps": maps, "spawns": spawns, "drops": drops},
    )


def _maps(doc: Document, pairs: PairIndex, warnings: list[str], provenance: dict) -> list[dict]:
    label = pairs.take(LABELS["map"])
    found: dict[str, dict] = {}
    for link in doc.links:
        if urls.classify(link.href) == "map":
            map_name = urls.name_from_url(link.href)
            found.setdefault(slugify(map_name), {"name": map_name, "url": link.href})
    if not found and label:
        warnings.append(f"mapas sem link, extraídos do texto: {label.value!r}")
        for map_name in filter(None, (clean(p) for p in re.split(r"[,;/|]", label.value))):
            found.setdefault(slugify(map_name), {"name": map_name, "url": None})
    return [
        {"id": map_id, "name": m["name"], **provenance, "source_url": m["url"] or provenance["source_url"]}
        for map_id, m in found.items() if map_id
    ]


def _drops_normal_items(doc: Document, pairs: PairIndex) -> bool | None:
    pair = pairs.take(LABELS["normal_drop"])
    if pair and parse_bool(pair.value) is not None:
        return parse_bool(pair.value)
    text = "\n".join(doc.text_lines)
    if NO_NORMAL.search(text):
        return False
    if YES_NORMAL.search(text):
        return True
    return None


def _classify(context: str, table: list[tuple[str, str]]) -> str | None:
    for value, pattern in table:
        if re.search(rf"\b(?:{pattern})", context, re.IGNORECASE):
            return value
    return None


def _drops(doc: Document, pairs: PairIndex, monster_id: str, warnings: list[str], provenance: dict) -> list[dict]:
    drops: dict[tuple, dict] = {}
    for section in doc.sections:
        if section.heading and SKIP_LINK_SECTION.search(section.heading):
            continue
        has_item_link = False
        for i, line in section.lines:
            item_links = [link for link in line.links if urls.classify(link.href) == "item"]
            if not item_links:
                continue
            has_item_link = True
            # Pares como "Excellent Armors: Dragon Armor, ..." são drops, não rótulos soltos.
            for pair in [p for p in pairs.unmapped() if p.line_index == i]:
                pairs.mark(pair)
            row_label = line.cells[0] if len(line.cells) >= 2 and line.cells[0] not in {l.text for l in item_links} else ""
            for link in item_links:
                _add_drop(drops, link, f"{link.column or ''} | {row_label}", section.heading or "", monster_id, provenance)
        if not has_item_link and section.heading and re.search(r"drop", section.heading, re.IGNORECASE):
            sample = [line.text for _, line in section.lines if line.text][:5]
            if sample:
                warnings.append(f"seção de drop {section.heading!r} sem links de item; linhas: {sample}")
    if drops and all(d["kind"] == "unknown" for d in drops.values()):
        warnings.append("drops encontrados, mas sem indicação de tipo (normal/excellent/...)")
    return list(drops.values())


def _add_drop(drops: dict, link: Link, near: str, heading: str, monster_id: str, provenance: dict) -> None:
    item_name = urls.name_from_url(link.href)
    item_id = slugify(item_name)
    if not item_id:
        return
    # O contexto mais próximo (coluna/linha) tem prioridade sobre o título da seção.
    kind = _classify(near, DROP_KINDS) or _classify(heading, DROP_KINDS) or "unknown"
    category = _classify(near, DROP_CATEGORIES) or _classify(heading, DROP_CATEGORIES)
    key = (item_id, kind, category)
    drops.setdefault(key, {
        "monster_id": monster_id,
        "item_id": item_id,
        "item_name": item_name,
        "kind": kind,
        "category": category,
        "rate": None,
        **provenance,
    })
