"""Parser de página de monstro do Fanz (/tools/mobs/data/mobdb/<Nome>.php).

Estrutura real da página (conteúdo entre o menu e o rodapé):

    <Nome> [Difficulty: 1]            (o sufixo só existe em monstros com seletor de dificuldade)
    Monster details:
      Monster Level: Level 48 | Max HP: 3,000 | ATK DMG: 150 ~ 155 | ATK Rate | DEF | DEF Rate
      [Elemental DEF | Elemental DMG]  (monstros novos)
      Data updated May 03, 2019
      Spawns in Dungeon.              (com link para /tools/maps/data/mapdb/<Mapa>.php, quando existe)
    General Drop Table                (kind=normal)
      Armor items: / Weapons (attck-type): / Weapons (magic-type): / Shields: / Skill items: /
      Crafting items: / Miscellaneous: / Accessories:    -> category; abaixo, um item por linha (com link)
    Excellent Drop Table, Excellent <Set> Drop Table, Ancient Drop Table ...

Cada linha de item é um drop possível do monstro; o site não informa taxa. O Fanz não publica respawn.
"""
from __future__ import annotations

import re

from scrapers.common.html import Line, clean
from scrapers.common.ids import slugify
from scrapers.common.model import ParseResult, empty_map
from scrapers.common.parsing import find_updated_date, parse_duration_seconds, parse_int, parse_range
from scrapers.fanz import urls
from scrapers.fanz.parse_common import content_lines, find_image, open_document, page_title

_DETAILS = re.compile(r"^Monster details:?$", re.IGNORECASE)
_TABLE = re.compile(r"^(?P<title>.+?\bDrop Table)$", re.IGNORECASE)
_SUBSECTION = re.compile(r"^(?P<label>[A-Za-z][A-Za-z ()-]{2,40}):$")
_SPAWNS = re.compile(r"^Spawns in\s+(?P<where>.+?)\.?$", re.IGNORECASE)
_QUANTITY = re.compile(r"\s*\(x(?P<n>\d+)\)\s*$", re.IGNORECASE)
_UPDATED = re.compile(r"^Data updated", re.IGNORECASE)
_RESPAWN = re.compile(r"^Respawns after\s*(?P<rest>.*)$", re.IGNORECASE)
_UTC_TIME = re.compile(r"^\d{1,2}:\d{2} \(UTC\)$")
_NO_NORMAL = re.compile(r"does not drop 'normal grade' items", re.IGNORECASE)
COLON_PAIR = re.compile(r"^(?P<label>[^:]{1,40}):\s*(?P<value>.+)$")

DETAIL_LABELS = {
    "monster level": "level", "level": "level",
    "max hp": "hp", "hp": "hp",
    "atk dmg": "atk", "atk rate": "atk_rate",
    "def": "def", "def rate": "def_rate",
    "elemental def": "elemental_def", "elemental dmg": "elemental_dmg",
}
TABLE_KINDS = [("excellent", "excellent"), ("ancient", "ancient"), ("socket", "socket"), ("general", "normal")]
CATEGORIES = [
    (r"^weapons \(magic", "magic_weapon"), (r"^weapons", "weapon"), (r"^armor", "armor"), (r"^shield", "shield"),
    (r"^accessor", "accessory"), (r"^skill", "skill"), (r"^crafting", "crafting"), (r"^misc", "misc"),
    (r"^wings?", "wings"), (r"^jewel", "jewel"),
]


def _is_heading(line: Line) -> bool:
    return not line.links and bool(_DETAILS.match(line.text) or _TABLE.match(line.text))


def parse_monster(html: str, meta: dict) -> ParseResult:
    url = meta["url"]
    doc = open_document(html, url, _is_heading)
    url_name = urls.name_from_url(url)
    lines = content_lines(doc)
    warnings: list[str] = []
    unmapped: list[str] = []
    if not doc.trimmed:
        warnings.append("marcador '|||' do menu não encontrado: conteúdo não recortado")
    name, difficulty = page_title(lines, url_name, warnings)
    monster_id = slugify(name)
    provenance = {"season": None, "source": urls.SOURCE_ID, "source_url": url, "scraped_at": meta["fetched_at"]}

    details, tables = _split(lines)
    notes: list[str] = []
    stats = _details(details, unmapped, notes, warnings)
    respawn_seconds, respawn_raw = _respawn(details)
    maps = _maps(details, provenance, warnings)
    drops, table_names = _drops(tables, monster_id, provenance, notes, warnings)

    atk_min, atk_max = stats.get("atk", (None, None))
    el_min, el_max = stats.get("elemental_dmg", (None, None))
    record = {
        "id": monster_id,
        "name": name,
        "number": None,
        "level": stats.get("level"),
        "difficulty": difficulty,
        "hp": stats.get("hp"),
        "atk_min": atk_min,
        "atk_max": atk_max,
        "atk_rate": stats.get("atk_rate"),
        "def": stats.get("def"),
        "def_rate": stats.get("def_rate"),
        "elemental_def": stats.get("elemental_def"),
        "elemental_dmg_min": el_min,
        "elemental_dmg_max": el_max,
        "respawn_seconds": respawn_seconds,
        "respawn_raw": respawn_raw,
        "drops_normal_items": False if any(_NO_NORMAL.search(n) for n in notes)
        else (any(d["kind"] == "normal" for d in drops) or None),
        "notes": notes,
        "image_url": find_image(doc, urls.MOB_IMAGE_PREFIX),
        **provenance,
        "page_updated_at": find_updated_date([line.text for line in details]),
    }
    spawns = [{"monster_id": monster_id, "map_id": m["id"], "kind": None, "x": None, "y": None, "x2": None,
               "y2": None, "radius": None, "count": None, **provenance} for m in maps]
    return ParseResult(
        kind="monster",
        record=record,
        source_file=meta.get("file", ""),
        warnings=warnings,
        unmapped=unmapped,
        headings=["Monster details", *table_names],
        related={"maps": maps, "spawns": spawns, "drops": drops},
    )


def _split(lines: list[Line]) -> tuple[list[Line], list[tuple[str, list[Line]]]]:
    """(linhas de 'Monster details', [(título da tabela de drop, linhas), ...])."""
    details: list[Line] = []
    tables: list[tuple[str, list[Line]]] = []
    current: list[Line] | None = None
    for line in lines:
        if line.heading and _DETAILS.match(line.text):
            current = details
        elif line.heading and (match := _TABLE.match(line.text)):
            current = []
            tables.append((match["title"].strip(), current))
        elif current is not None:
            current.append(line)
    return details, tables


def _details(details: list[Line], unmapped: list[str], notes: list[str], warnings: list[str]) -> dict:
    stats: dict = {}
    for line in details:
        text = line.text
        if _UPDATED.match(text) or _SPAWNS.match(text) or _RESPAWN.match(text) or _UTC_TIME.match(text):
            continue
        pair = COLON_PAIR.match(text)
        if not pair:
            notes.append(text)  # frase solta, ex.: "DMG & DEF Adjustment removed after character level 1095."
            continue
        key = DETAIL_LABELS.get(pair["label"].strip().lower())
        if not key:
            unmapped.append(f"Monster details: {text}")
            continue
        raw = pair["value"]
        if key in ("atk", "elemental_dmg"):
            low, high = parse_range(raw)
            value = (low, high) if low is not None else None
        else:
            value = parse_int(raw)
        if value is None:
            warnings.append(f"{key}: valor não numérico {raw!r}")
        else:
            stats[key] = value
    return stats


def _respawn(details: list[Line]) -> tuple[int | None, str | None]:
    """'Respawns after 24 Hours' -> (86400, '24 Hours'). Bosses com horário fixo trazem a lista de horários
    ('Respawns after 18:11 (UTC)' + linhas '22:00 (UTC)'): vira texto em respawn_raw, sem segundos."""
    for i, line in enumerate(details):
        match = _RESPAWN.match(line.text)
        if not match:
            continue
        rest = match["rest"].strip()
        times = ([rest] if _UTC_TIME.match(rest) else []) + [
            d.text for d in details[i + 1:] if _UTC_TIME.match(d.text)]
        if times:
            return None, "UTC: " + ", ".join(t.replace(" (UTC)", "") for t in times)
        return (parse_duration_seconds(rest), rest) if rest else (None, None)
    return None, None


def _maps(details: list[Line], provenance: dict, warnings: list[str]) -> list[dict]:
    found: dict[str, dict] = {}
    for line in details:
        match = _SPAWNS.match(line.text)
        if not match:
            continue
        where = _map_name(match["where"])
        links = [link for link in line.links if urls.classify(link.href) == "map"]
        if links:
            for link in links:
                map_name = urls.name_from_url(link.href)
                # "Spawns in Kalima 1.": o link é "Kalima", mas Kalima 1..7 são mapas distintos no jogo.
                if len(links) == 1 and re.fullmatch(rf"{re.escape(map_name)} \d+", where):
                    map_name = where
                found.setdefault(slugify(map_name), {"name": map_name, "url": urls.canonical(link.href)})
        else:
            # "Lorencia, Noria, Devias, or Lost Tower." sem link: um mapa por nome da lista.
            for name in _split_maps(where):
                warnings.append(f"mapa sem link: {name!r}")
                found.setdefault(slugify(name), {"name": name, "url": None})
    return [empty_map(map_id, m["name"], {**provenance, "source_url": m["url"] or provenance["source_url"]})
            for map_id, m in found.items() if map_id]


MAP_TYPOS = {"Adia": "Aida"}


def _split_maps(where: str) -> list[str]:
    """'Lorencia, Noria, Devias, or Lost Tower' -> ['Lorencia', 'Noria', 'Devias', 'Lost Tower'] (também '&' e 'and')."""
    parts = re.split(r"\s*,\s*(?:or\s+|and\s+|&\s*)?|\s+(?:or|and|&)\s+", where)
    return [MAP_TYPOS.get(p.strip(), p.strip()) for p in parts if p.strip()]


def _map_name(text: str) -> str:
    """'Blood Castle Mini-game 1.' -> 'Blood Castle 1' (mesmo nome que o servidor usa)."""
    name = clean(re.sub(r"[.\s]+$", "", text))
    return re.sub(r"\s+Mini-game(?=\s+\d+$)", "", name, flags=re.IGNORECASE)


def _table_kind(title: str) -> str:
    lowered = title.lower()
    return next((kind for word, kind in TABLE_KINDS if word in lowered), "unknown")


def _category(label: str) -> str | None:
    lowered = label.lower()
    return next((category for pattern, category in CATEGORIES if re.match(pattern, lowered)), None)


def _drops(tables: list[tuple[str, list[Line]]], monster_id: str, provenance: dict,
           notes: list[str], warnings: list[str]) -> tuple[list[dict], list[str]]:
    drops: dict[tuple, dict] = {}
    for title, lines in tables:
        kind = _table_kind(title)
        if kind == "unknown":
            # "Bloodangel Drop Table" + "This monster can drop any normal Bloodangel armor item."
            first = next((line.text for line in lines if not line.links), "")
            kind = _table_kind(first.replace("normal", "general")) if "can drop any" in first else "unknown"
        if kind == "unknown":
            warnings.append(f"tabela de drop de tipo desconhecido: {title!r}")
        category: str | None = None
        for line in lines:
            text = line.text
            if _UPDATED.match(text):
                continue
            item_links = [link for link in line.links if urls.classify(link.href) == "item"]
            if not item_links:
                sub = _SUBSECTION.match(text)
                if sub:
                    category = _category(sub["label"])
                    if category is None:
                        warnings.append(f"subseção de drop desconhecida: {text!r}")
                elif text.lower() not in ("zen", "none"):  # Zen não é item; "None" = subseção vazia
                    notes.append(f"{title}: {text}")  # ex.: "This monster can drop any Excellent Holyangel armor item."
                continue
            quantity = _QUANTITY.search(text)
            item_name = urls.name_from_url(item_links[0].href)
            item_id = slugify(item_name)
            if not item_id:
                continue
            drops.setdefault((item_id, kind, title, category), {
                "monster_id": monster_id,
                "item_id": item_id,
                "item_name": item_name,
                "kind": kind,
                "table": title,
                "category": category,
                "quantity": int(quantity["n"]) if quantity else None,
                "rate": None,
                **provenance,
            })
    return list(drops.values()), [title for title, _ in tables]
