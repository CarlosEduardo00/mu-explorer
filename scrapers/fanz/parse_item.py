"""Parser de página de item do Fanz (/tools/items/data/itemdb/<Nome>.php).

Rótulos e seções são casados por regex sobre o texto normalizado (ver scrapers/common/html.py).
Os padrões abaixo foram escritos a partir da descrição dos campos, antes de ver o HTML real:
ajuste-os com base em `unmapped` e nos títulos de seção do relatório da PoC.
"""
from __future__ import annotations

import re

from scrapers.common.html import Document, PairIndex, clean
from scrapers.common.ids import slugify
from scrapers.common.model import ParseResult
from scrapers.common.mu import find_classes, is_known_class, split_classes
from scrapers.common.parsing import find_updated_date, parse_bool, parse_int, parse_number, parse_range
from scrapers.fanz import urls
from scrapers.fanz.parse_common import find_image, pick_name

REQ_WORDS = r"(?:req|reqd|required|requirement|requirements|requires|min|minimum|need|needed)"
REQ_STATS = {
    "level": r"lv|lvl|level",
    "strength": r"str|strength",
    "agility": r"agi|agility|dex|dexterity",
    "vitality": r"vit|vitality|sta|stamina",
    "energy": r"ene|enr|energy",
    "command": r"cmd|com|command|leadership",
}
# (padrão do rótulo, chave em stats, tipo do valor)
STATS = [
    (r"(?:def|defense|defence)(?: power)?", "defense", "number"),
    (r"(?:def|defense|defence) (?:rate|success rate|success)", "defense_rate", "number"),
    (r"min(?:imum)? (?:atk|attack|dmg|damage)", "damage_min", "number"),
    (r"max(?:imum)? (?:atk|attack|dmg|damage)", "damage_max", "number"),
    (r"(?:atk|attack|dmg|damage)(?: dmg| damage| power)?", "damage", "range"),
    (r"(?:wiz|wizardry|magic|magical)(?: dmg| damage| power| rate| increase)?", "magic_power", "number"),
    (r"curse(?: power| damage| spell| spell power)?", "curse_power", "number"),
    (r"(?:atk|attack) speed", "attack_speed", "number"),
    (r"(?:walk|walking|move|moving|movement) speed", "move_speed", "number"),
    (r"(?:dmg|damage) (?:increase|inc|boost)", "damage_increase", "number"),
    (r"(?:dmg|damage) (?:absorb|absorption|decrease|reduction|reduce)", "damage_absorb", "number"),
]
CLASS_LABEL = (
    r"(?:can be )?(?:equipped|equip|equipable|usable|used|wear|wearable|worn)(?: by)?"
    r"|(?:class|classes|character|characters|job|jobs)(?: requirement| req| required| allowed| restriction)?"
    r"|(?:required|allowed|usable|equipable) (?:class|classes|character|characters)"
)
CLASS_INLINE = re.compile(r"(?:can be )?(?:equipped|used|worn|wearable|usable) by\s*:?\s*(.+)", re.IGNORECASE)
OPTION_LABEL = (
    r"(?:possible |additional |available |extra |item )?options?(?: available| possible)?"
    r"|(?:can have|can be added|addable)(?: options?)?"
)
OPTION_SECTION = r"option|addition"
_OPTION_NAMES = {
    "luck": "Luck", "skill": "Skill",
    "life": "Jewel of Life", "jewel of life": "Jewel of Life",
    "harmony": "Jewel of Harmony", "jewel of harmony": "Jewel of Harmony",
    "excellent": "Excellent", "ancient": "Ancient", "socket": "Socket",
    "380": "380 Option", "pvp": "PvP Option", "guardian": "Guardian Option", "mastery": "Mastery",
}
# "Luck: Yes", "Can have skill: No", "Life option: O"... ("Life" sozinho não: pode ser HP de pet).
OPTION_FLAG = re.compile(
    r"(?:can have |has |with )?(?:(?P<name>jewel of life|jewel of harmony|luck|skill|excellent|ancient"
    r"|socket|380|pvp|guardian|mastery)(?: option| options)?|(?P<name2>life|harmony) options?)"
)
_OPTION_SEARCH = re.compile(r"\b(jewel of life|jewel of harmony|luck|skill|excellent|ancient|socket|380|pvp|guardian|mastery)\b",
                            re.IGNORECASE)
RELATED_SECTION = r"related|similar|same set|set items?|see also|other items"


def parse_item(html: str, meta: dict) -> ParseResult:
    url = meta["url"]
    doc = Document(html, base_url=meta.get("final_url") or url)
    pairs = PairIndex(doc.pairs)
    warnings: list[str] = []
    url_name = urls.name_from_url(url)
    name = pick_name(doc, url_name, warnings)

    record = {
        "id": slugify(name),
        "name": name,
        "category": _text(pairs.take(r"(?:item )?(?:category|type|kind|slot|group)")),
        "group": None,
        "index": None,
        "classes": _classes(doc, pairs, warnings),
        "requirements": _requirements(pairs, warnings),
        "stats": _stats(pairs, warnings),
        "durability": _int(pairs.take(r"(?:max |maximum )?(?:dur|durability)"), "durability", warnings),
        "grade": _text(pairs.take(r"(?:item )?(?:grade|rank|rarity|tier|quality)")),
        "options": _options(doc, pairs),
        "related_items": _related(doc, url_name),
        "image_url": find_image(doc, name, urls.ITEM_IMAGE_PREFIX),
        "season": None,
        "source": urls.SOURCE_ID,
        "source_url": url,
        "scraped_at": meta["fetched_at"],
        "page_updated_at": find_updated_date(doc.text_lines),
    }
    return ParseResult(
        kind="item",
        record=record,
        source_file=meta.get("file", ""),
        warnings=warnings,
        unmapped=pairs.unmapped(),
        headings=doc.headings,
    )


def _text(pair) -> str | None:
    if pair is None:
        return None
    return clean(pair.value).lower() or None


def _flag_name(key: str) -> str | None:
    match = OPTION_FLAG.fullmatch(key)
    return _OPTION_NAMES[match.group("name") or match.group("name2")] if match else None


def _int(pair, field: str, warnings: list[str]) -> int | None:
    if pair is None:
        return None
    value = parse_int(pair.value)
    if value is None:
        warnings.append(f"{field}: valor não numérico {pair.value!r}")
    return value


def _requirements(pairs: PairIndex, warnings: list[str]) -> dict[str, int | None]:
    reqs: dict[str, int | None] = dict.fromkeys(REQ_STATS)
    for stat, alias in REQ_STATS.items():
        explicit = rf"(?:{REQ_WORDS} )+(?:{alias})|(?:{alias})(?: {REQ_WORDS})+"
        pair = pairs.take(explicit) or pairs.take(rf"(?:{alias})", section=r"req")
        # "Level" solto em página de item pode ser o nível do item, não o requisito.
        if pair is None and stat != "level":
            pair = pairs.take(rf"(?:{alias})")
        reqs[stat] = _int(pair, f"requirements.{stat}", warnings)
    return reqs


def _stats(pairs: PairIndex, warnings: list[str]) -> dict[str, int | float]:
    stats: dict[str, int | float] = {}
    for pattern, key, kind in STATS:
        pair = pairs.take(pattern)
        if pair is None:
            continue
        if kind == "range":
            low, high = parse_range(pair.value)
            if low is None:
                warnings.append(f"stats.{key}: valor não numérico {pair.value!r}")
                continue
            stats.setdefault("damage_min", low)
            stats.setdefault("damage_max", high)
        else:
            value = parse_number(pair.value)
            if value is None:
                warnings.append(f"stats.{key}: valor não numérico {pair.value!r}")
                continue
            stats[key] = value
    return stats


def _classes(doc: Document, pairs: PairIndex, warnings: list[str]) -> list[str]:
    classes: list[str] = []
    pair = pairs.take(CLASS_LABEL)
    if pair:
        classes = split_classes(pair.value)
    if not classes:
        for line in doc.text_lines:
            match = CLASS_INLINE.search(line)
            if match:
                classes = split_classes(match.group(1))
                break
    if not classes:
        for section in doc.sections_matching(r"class|equip|wear|requir"):
            for i, line in section.lines:
                if not pairs.line_has_pair(i):
                    classes.extend(find_classes(line.text))
            for image in section.images:
                classes.extend(find_classes(f"{image.alt} | {image.title}"))
    classes = list(dict.fromkeys(classes))
    unknown = [c for c in classes if not is_known_class(c)]
    if unknown:
        warnings.append(f"classes não reconhecidas: {unknown}")
    return classes


def _canonical_option(text: str) -> str | None:
    text = clean(text).strip("+-•*· ")
    if not text or len(text) > 60:
        return None
    match = _OPTION_SEARCH.search(text)
    return _OPTION_NAMES[match.group(1).lower()] if match else text


def _options(doc: Document, pairs: PairIndex) -> list[str]:
    options: list[str] = []
    pair = pairs.take(OPTION_LABEL)
    if pair:
        options.extend(filter(None, (_canonical_option(p) for p in re.split(r"[,/;|]", pair.value))))
    sections = doc.sections_matching(OPTION_SECTION)
    # Pares do tipo "Luck: Yes" em qualquer lugar, e quaisquer pares dentro da seção de opções.
    for p in pairs.in_sections(sections) + [p for p in pairs.unmapped() if _flag_name(p.key)]:
        flag = parse_bool(p.value)
        known = _flag_name(p.key)
        if flag is None and not known:
            continue
        pairs.mark(p)
        if flag is not False:
            options.append(known or clean(p.label))
    for section in sections:
        for i, line in section.lines:
            if pairs.line_has_pair(i):
                continue
            for part in re.split(r"[,;|]", line.text):
                option = _canonical_option(part)
                if option:
                    options.append(option)
    return list(dict.fromkeys(options))


def _related(doc: Document, url_name: str) -> list[str]:
    related_sections = doc.sections_matching(RELATED_SECTION)
    if related_sections:
        links = [link for s in related_sections for link in s.links]
    else:
        option_sections = {id(s) for s in doc.sections_matching(OPTION_SECTION)}
        links = [link for s in doc.sections if id(s) not in option_sections for link in s.links]
    ids = [
        slugify(urls.name_from_url(link.href))
        for link in links
        if urls.classify(link.href) == "item" and urls.name_from_url(link.href) != url_name
    ]
    return list(dict.fromkeys(i for i in ids if i))
