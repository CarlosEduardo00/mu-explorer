"""Parser de página de mapa do Fanz (/tools/maps/data/mapdb/<Mapa>.php).

Estrutura real (conteúdo entre o menu e o rodapé):

    <Nome do mapa>
    <parágrafo de apresentação>
    #Hot Spots #Monster List ...      (índice de âncoras: ignorado)
    Quick Facts                        requisitos de entrada, nível recomendado...
      Valued monster drops: / Valued special monster drops: / Valued boss drops: ...
    Hot Spots #                        mapa clicável num iframe em /tools/maps/data/php/ (bloqueado no
                                       robots.txt: não coletamos; coordenadas de spots vêm do MuEmu)
    Monster List # / Special Monster List # / Boss Monster List #   links para /mobdb/ + resumo de stats
    NPC List #                         links para /npcdb/
    Notes & Tips #                     "This map has entrances to/from:" + nomes de mapas
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

from scrapers.common.html import Line
from scrapers.common.ids import slugify
from scrapers.common.model import ParseResult, empty_map
from scrapers.fanz import urls
from scrapers.fanz.parse_common import content_lines, find_image, open_document, page_title

MAP_IMAGE_PREFIX = "/tools/maps/data/graphics/"
_SECTION = re.compile(r"^(?P<title>[A-Za-z &]+?)(?:\.\.\.)?\s*#$")
_ANCHOR = re.compile(r"^#\S")  # índice "#Hot Spots" no topo
_VALUED = re.compile(r"^Valued (?P<group>[a-z ]*?)(?:monster )?drops?\s*(?::|\.\.\.)$", re.IGNORECASE)
_NAV = re.compile(r"(Database ↗|^🔙)")
_CONNECTIONS = re.compile(r"entrances? to/from", re.IGNORECASE)
_BOILERPLATE = re.compile(r"^(© muonlinefanz\.com|This is a list of|Hunting in an area with more)", re.IGNORECASE)
_LIST_KEYS = {"monster list": "monsters", "special monster list": "special_monsters",
              "boss monster list": "bosses", "boss zone": "bosses", "npc list": "npcs"}


def _is_heading(line: Line) -> bool:
    return not line.links and bool(_SECTION.match(line.text) or line.text == "Quick Facts")


def parse_map(html: str, meta: dict) -> ParseResult:
    url = meta["url"]
    doc = open_document(html, url, _is_heading)
    url_name = urls.name_from_url(url)
    lines = [line for line in content_lines(doc) if not _NAV.search(line.text)]
    warnings: list[str] = []
    unmapped: list[str] = []
    if not doc.trimmed:
        warnings.append("marcador '|||' do menu não encontrado: conteúdo não recortado")
    name, _ = page_title(lines, url_name, warnings)
    provenance = {"season": None, "source": urls.SOURCE_ID, "source_url": url, "scraped_at": meta["fetched_at"]}
    record = empty_map(slugify(name), name, provenance)

    section = "intro"
    valued_group: str | None = None
    for i, line in enumerate(lines):
        text = line.text
        if line.heading:
            match = _SECTION.match(text)
            section = (match["title"] if match else text).strip().lower()
            valued_group = None
            continue
        if _ANCHOR.match(text) or _BOILERPLATE.match(text) or text == name:
            continue
        if section == "intro":
            if record["description"] is None and len(text) > 40:
                record["description"] = text
            continue
        if section == "quick facts":
            valued = _VALUED.match(text)
            if valued:
                valued_group = (valued["group"].strip() or "monster").replace(" ", "_")
                record["valued_drops"].setdefault(valued_group, [])
            elif valued_group:
                record["valued_drops"][valued_group].append(text)
            else:
                record["quick_facts"].append(text)
            continue
        key = _LIST_KEYS.get(section)
        if key:
            kind = "npc" if key == "npcs" else "monster"
            for link in line.links:
                if urls.classify(link.href) == kind:
                    record[key].append(slugify(urls.name_from_url(link.href)))
            continue
        if section.startswith("notes"):
            record["notes"].append(text)
            if _CONNECTIONS.search(text):
                record["connections"] = _connections(lines[i + 1:])
            continue
        if section != "hot spots":
            unmapped.append(f"{section}: {text}")

    for key in ("monsters", "special_monsters", "bosses", "npcs", "connections"):
        record[key] = list(dict.fromkeys(record[key]))
    record["image_url"] = find_image(doc, MAP_IMAGE_PREFIX)
    record.update(map_levels(record["quick_facts"]))
    record["minimap_url"] = find_minimap(doc)
    return ParseResult(kind="map", record=record, source_file=meta.get("file", ""), warnings=warnings,
                       unmapped=unmapped, headings=doc.headings)


_REQUIRES = re.compile(r"^Requires character level ([\d,]+) to enter", re.IGNORECASE)
_RECOMMENDED = re.compile(r"^Recommended for characters level ([\d,]+) ~ ([\d,]+|\?)", re.IGNORECASE)
_LESS_THAN = re.compile(r"^Recommended for characters less than level ([\d,]+)", re.IGNORECASE)


_MINIMAP = re.compile(r"/tools/maps/data/graphics/[^/]+/map\.jpg$", re.IGNORECASE)


def find_minimap(doc) -> str | None:
    """Minimapa do jogo (graphics/<Mapa>/map.jpg, 1024×1024 = 4 px por casa; horizontal = y, vertical = x).
    É a imagem de fundo dos Hot Spots; os pontos dos Hot Spots ficam no php bloqueado e não são coletados."""
    for image in doc.images:
        if _MINIMAP.search(unquote(urlsplit(image.src).path)):
            return image.src
    return None


def map_levels(quick_facts: list[str]) -> dict:
    """Nível para entrar e faixa recomendada, das frases principais dos Quick Facts (andares e sub-mapas ficam no texto)."""
    out = {"level_required": None, "level_recommended_min": None, "level_recommended_max": None}
    num = lambda s: int(s.replace(",", ""))
    for fact in quick_facts:
        if out["level_required"] is None and (m := _REQUIRES.match(fact)):
            out["level_required"] = num(m.group(1))
        elif out["level_recommended_min"] is None and (m := _RECOMMENDED.match(fact)):
            out["level_recommended_min"] = num(m.group(1))
            out["level_recommended_max"] = None if m.group(2) == "?" else num(m.group(2))
        elif out["level_recommended_min"] is None and (m := _LESS_THAN.match(fact)):
            out["level_recommended_min"], out["level_recommended_max"] = 1, num(m.group(1)) - 1
    return out


def _connections(lines: list[Line]) -> list[str]:
    """Nomes de mapa logo abaixo de 'This map has entrances to/from:' (linhas curtas, sem ponto final)."""
    out = []
    for line in lines:
        text = line.text
        if line.heading or text.endswith((".", ":", "!")) or len(text) > 40:
            break
        out.append(slugify(text))
    return out
