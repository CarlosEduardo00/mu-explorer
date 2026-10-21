"""Parser de página de item do Fanz (/tools/items/data/itemdb/<Nome>.php).

Estrutura real da página (conteúdo entre o menu e o rodapé), com seções que terminam em "...":

    <título do item>
    Item details...            DEF: +348 | 2-H ATK DMG: 150 ~ 190 | ATK Speed: 50 ...
    Requirements...            Agility: 125 | Character Level 1100 | Can be equipped by DK, DW
    Possible additional options...   +Jewel of Life option* | +Luck option | +Sockets (x5 max)
    Excellent option... (x3 max)     HP +165 | Mana +165 ...      (também Additional/Elemental/Base/Set option)
    Related items...           nomes (alguns com link)
    Notes & links...           texto livre; traz o grau: "This item is an 'excellent' grade item"

Itens consumíveis usam "Item usage..." / "Prerequisites..." (em vez de Item details/Requirements).
O que a página NÃO traz: categoria, durabilidade, data de atualização (só a versão do template).
"""
from __future__ import annotations

import re

from scrapers.common.html import Line, clean
from scrapers.common.ids import slugify
from scrapers.common.model import ParseResult
from scrapers.common.mu import is_known_class, split_classes
from scrapers.common.parsing import parse_int, parse_number, parse_range
from scrapers.fanz import urls
from scrapers.fanz.parse_common import content_lines, find_image, open_document, page_title

_SECTION = re.compile(r"^(?P<title>[^.]{2,45}?)\.\.\.\s*(?:\(x(?P<max>\d+) max\))?$")
_PLAIN_SECTION = re.compile(r"^(?P<title>Item details|Requirements|Prerequisites)\s*[:.]*$", re.IGNORECASE)
_NOT_SECTION = re.compile(r"^(?:The following items|This item|If you|Set the item level)", re.IGNORECASE)
_BREADCRUMB = re.compile(r"^Home\s*-\s*Tools", re.IGNORECASE)
REQUIREMENT_KEYS = {
    "level": "level", "character level": "level", "lv": "level",
    "strength": "strength", "str": "strength",
    "agility": "agility", "agi": "agility",
    "vitality": "vitality", "stamina": "vitality", "vit": "vitality", "sta": "vitality",
    "energy": "energy", "ene": "energy", "eng": "energy",
    "command": "command", "com": "command", "com level": "command", "leadership": "command",
}
STAT_ALIASES = {
    "def": "defense", "def rate": "defense_rate", "defense rate": "defense_rate",
    "atk dmg": "damage", "atk speed": "attack_speed", "wiz speed": "wizardry_speed",
}
OPTION_NAMES = [
    (r"jewel of life", "Jewel of Life"), (r"jewel of harmony", "Jewel of Harmony"),
    (r"luck", "Luck"), (r"sockets?", "Socket"), (r"skill", "Skill"),
]
OPTION_LINE = re.compile(r"^\+\s*(?P<name>[A-Za-z ]+?)(?: options?)?\*?(?:\s*\(x\d+ max\))?$")
GRADE = re.compile(r"is an? '([a-z ]+)' grade item", re.IGNORECASE)
CLASS_LINE = re.compile(r"^Can be equipped by\s+(?P<classes>.+)$", re.IGNORECASE)
BARE_PAIR = re.compile(r"^(?P<label>[A-Za-z][A-Za-z .'()/\\-]*?)\s+(?P<value>[+-]?\d[\d,]*)$")
COLON_PAIR = re.compile(r"^(?P<label>[^:]{1,40}):\s*(?P<value>.+)$")


def _is_heading(line: Line) -> bool:
    text = line.text
    if line.links or _NOT_SECTION.match(text):
        return False
    return bool(_SECTION.match(text) or _PLAIN_SECTION.match(text))


def _snake(label: str) -> str:
    return slugify(label).replace("-", "_")


def parse_item(html: str, meta: dict) -> ParseResult:
    url = meta["url"]
    doc = open_document(html, url, _is_heading)
    url_name = urls.name_from_url(url)
    lines = content_lines(doc)
    warnings: list[str] = []
    unmapped: list[str] = []
    if not doc.trimmed:
        warnings.append("marcador '|||' do menu não encontrado: conteúdo não recortado")
    name, _ = page_title(lines, url_name, warnings)

    sections = _split_sections(lines)
    requirements, classes = _requirements(sections, warnings, unmapped)
    notes: list[str] = []
    stats = _stats(sections, name, notes, unmapped)
    options, option_groups = _options(sections)
    notes += _notes(sections)

    record = {
        "id": slugify(name),
        "name": name,
        "category": None,
        "group": None,
        "index": None,
        "classes": classes,
        "requirements": requirements,
        "stats": stats,
        "durability": None,
        "grade": _grade(notes),
        "options": options,
        "option_groups": option_groups,
        "related_items": _related(sections, url_name),
        "notes": notes,
        "image_url": find_image(doc, urls.ITEM_IMAGE_PREFIX),
        "season": None,
        "source": urls.SOURCE_ID,
        "source_url": url,
        "scraped_at": meta["fetched_at"],
        "page_updated_at": None,
    }
    return ParseResult(
        kind="item",
        record=record,
        source_file=meta.get("file", ""),
        warnings=warnings,
        unmapped=unmapped,
        headings=[title for title, _, _ in sections if title],
    )


Section = tuple[str, int | None, list[Line]]  # (título, máx. "(xN max)", linhas)


def _split_sections(lines: list[Line]) -> list[Section]:
    sections: list[Section] = [("", None, [])]
    for line in lines:
        match = (_SECTION.match(line.text) or _PLAIN_SECTION.match(line.text)) if line.heading else None
        if match:
            maximum = match.groupdict().get("max")
            sections.append((match["title"].strip(), int(maximum) if maximum else None, []))
        else:
            sections[-1][2].append(line)
    return sections


def _named(sections: list[Section], *titles: str) -> list[Section]:
    wanted = {t.lower() for t in titles}
    return [s for s in sections if s[0].lower() in wanted]


def _requirements(sections: list[Section], warnings: list[str],
                  unmapped: list[str]) -> tuple[dict[str, int | None], list[str]]:
    requirements: dict[str, int | None] = dict.fromkeys(("level", "strength", "agility", "vitality", "energy", "command"))
    classes: list[str] = []
    for _, _, lines in _named(sections, "Requirements", "Prerequisites"):
        for line in lines:
            text = line.text
            if (match := CLASS_LINE.match(text)):
                if match["classes"].strip().lower() == "classes":
                    warnings.append("o site não lista as classes ('Can be equipped by Classes')")
                else:
                    classes.extend(split_classes(match["classes"]))
                continue
            pair = COLON_PAIR.match(text) or BARE_PAIR.match(text)
            key = REQUIREMENT_KEYS.get(re.sub(r"[^a-z ]", "", pair["label"].lower()).strip()) if pair else None
            value = parse_int(pair["value"]) if pair else None
            if key and value is not None:
                requirements[key] = value
            else:
                unmapped.append(f"Requirements: {text}")
    classes = list(dict.fromkeys(classes))
    if unknown := [c for c in classes if not is_known_class(c)]:
        warnings.append(f"classes não reconhecidas: {unknown}")
    return requirements, classes


def _stats(sections: list[Section], title_text: str, notes: list[str], unmapped: list[str]) -> dict[str, int | float]:
    """Stats base: todo par numérico de 'Item details'. 'N-H ATK DMG: a ~ b' vira damage_min/max."""
    stats: dict[str, int | float] = {}
    # Sem "Item details", os detalhes vêm soltos logo depois do título (ex.: asas).
    for title, _, lines in sections:
        if title.lower() != "item details" and title != "":
            continue
        for line in lines:
            if _BREADCRUMB.match(line.text) or line.text == title_text:
                continue
            pair = COLON_PAIR.match(line.text)
            if not pair:
                notes.append(line.text)  # ex.: "Increased Movement Speed" (efeito sem número)
                continue
            label, raw = pair["label"].strip(), pair["value"]
            value = parse_number(raw)
            if value is None:
                unmapped.append(f"Item details: {line.text}")
                continue
            hands = re.match(r"(\d)-H\s+(.*)", label)
            if hands:
                stats["hands"] = int(hands.group(1))
                label = hands.group(2)
            key = STAT_ALIASES.get(label.lower(), _snake(label))
            if raw.strip().endswith("%"):
                key += "_pct"
            if "~" in raw:
                low, high = parse_range(raw)
                stats[f"{key}_min"], stats[f"{key}_max"] = low, high
            else:
                stats[key] = value
    return stats


def _options(sections: list[Section]) -> tuple[list[str], list[dict]]:
    options: list[str] = []
    groups: list[dict] = []
    for title, maximum, lines in sections:
        if not title.lower().endswith(("option", "options")) and title.lower() != "errtel bonus":
            continue
        entries: list[str] = []
        for line in lines:
            text = line.text
            if (match := OPTION_LINE.match(text)):
                known = next((label for pattern, label in OPTION_NAMES if re.fullmatch(pattern, match["name"].strip().lower())), None)
                if known:
                    options.append(known)
                    continue
            if text.startswith("*"):
                continue  # nota de rodapé das opções ("*the item's STR requirement increases...")
            entries.append(text)
        if entries:
            groups.append({"title": title, "max": maximum, "lines": entries})
    return list(dict.fromkeys(options)), groups


def _related(sections: list[Section], url_name: str) -> list[str]:
    ids: list[str] = []
    for _, _, lines in _named(sections, "Related items"):
        for line in lines:
            if line.text.startswith("The following items"):
                continue
            item_links = [link for link in line.links if urls.classify(link.href) == "item"]
            name = urls.name_from_url(item_links[0].href) if item_links else line.text
            if name != url_name:
                ids.append(slugify(name))
    return list(dict.fromkeys(i for i in ids if i))


def _notes(sections: list[Section]) -> list[str]:
    notes: list[str] = []
    for _, _, lines in _named(sections, "Notes & links", "Item usage"):
        notes.extend(clean(line.text) for line in lines)
    return notes


def _grade(notes: list[str]) -> str | None:
    for note in notes:
        if (match := GRADE.search(note)):
            return match.group(1).lower()
    return None
