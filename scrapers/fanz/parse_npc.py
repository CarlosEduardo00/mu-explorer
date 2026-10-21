"""Parser de página de NPC do Fanz (/tools/npc/data/npcdb/<NPC>.php).

Estrutura real (conteúdo entre o menu e o rodapé):

    <Nome>
    Overview:  Merchant NPC | Quest NPC | Crafting NPC | Miscellaneous NPC | Mini-game NPC | Event NPC
    Location:  Arena @(72, 164)        (link para o mapa; pode haver várias linhas; "@(?, ?)" = sem coordenada)
    <parágrafo de descrição>
    Item Selling List                  mercadores: "Recovery Items:" -> item (link) -> "x20 Zen"

Receitas de crafting (Possible Crafts List, Required ingredients...) ainda não são extraídas: as linhas
vão para `unmapped` no relatório.
"""
from __future__ import annotations

import re

from scrapers.common.html import Line
from scrapers.common.ids import slugify
from scrapers.common.model import ParseResult
from scrapers.common.parsing import parse_int
from scrapers.fanz import urls
from scrapers.fanz.parse_common import content_lines, find_image, open_document, page_title

NPC_IMAGE_PREFIX = "/tools/npc/data/graphics/"
# "Arena @(72, 164)", "Acheron @(?, ?)", "Lorencia @(various)"
_LOCATION = re.compile(r"^(?P<map>.+?)\s*@\(\s*(?P<x>[^,)]+?)\s*(?:,\s*(?P<y>[^)]+?))?\s*\)")
_DETAILS = re.compile(r"^\[.*\]$")
_PRICE = re.compile(r"^x\s*(?P<zen>[\d,]+)\s*Zen$", re.IGNORECASE)
_SUBSECTION = re.compile(r"^(?P<label>[A-Za-z][A-Za-z /&-]{2,40}):$")
_NAV = re.compile(r"(Database ↗|^🔙)")
_BOILERPLATE = re.compile(r"^© muonlinefanz\.com$")


def parse_npc(html: str, meta: dict) -> ParseResult:
    url = meta["url"]
    doc = open_document(html, url, None)
    url_name = urls.name_from_url(url)
    lines = [line for line in content_lines(doc) if not _NAV.search(line.text) and not _BOILERPLATE.match(line.text)]
    warnings: list[str] = []
    unmapped: list[str] = []
    if not doc.trimmed:
        warnings.append("marcador '|||' do menu não encontrado: conteúdo não recortado")
    name, _ = page_title(lines, url_name, warnings)
    texts = [line.text for line in lines]

    npc_type = texts[texts.index("Overview:") + 1] if "Overview:" in texts[:-1] else None
    locations = _locations(lines, texts)
    description = None
    if "Location:" in texts:
        after = texts.index("Location:") + 1 + max(len(locations), 1)
        description = next((t for t in texts[after:after + 3] if len(t) > 40 and not t.endswith(":")), None)
    sells, rest = _sells(lines, texts)
    known = {name, "Overview:", "Location:", npc_type, description}
    unmapped += [f"{t}" for t in rest if t not in known and not _LOCATION.match(t)][:200]

    record = {
        "id": slugify(name),
        "name": name,
        "type": npc_type,
        "locations": locations,
        "description": description,
        "sells": sells,
        "image_url": find_image(doc, NPC_IMAGE_PREFIX),
        "season": None,
        "source": urls.SOURCE_ID,
        "source_url": url,
        "scraped_at": meta["fetched_at"],
        "page_updated_at": None,
    }
    return ParseResult(kind="npc", record=record, source_file=meta.get("file", ""), warnings=warnings,
                       unmapped=unmapped, headings=[])


def _locations(lines: list[Line], texts: list[str]) -> list[dict]:
    if "Location:" not in texts:
        return []
    out = []
    for line in lines[texts.index("Location:") + 1:]:
        match = _LOCATION.match(line.text)
        if not match:
            break
        map_links = [link for link in line.links if urls.classify(link.href) == "map"]
        map_name = urls.name_from_url(map_links[0].href) if map_links else match["map"].strip()
        out.append({
            "map_id": slugify(map_name),
            "map_name": map_name,
            "x": parse_int(match["x"]) if (match["x"] or "").isdigit() else None,
            "y": parse_int(match["y"]) if (match["y"] or "").isdigit() else None,
        })
    return out


def _sells(lines: list[Line], texts: list[str]) -> tuple[list[dict], list[str]]:
    """Itens da 'Item Selling List' (categoria -> item com link -> preço). Devolve também o resto do texto."""
    if "Item Selling List" not in texts:
        return [], texts
    start = texts.index("Item Selling List")
    sells: list[dict] = []
    category: str | None = None
    for line in lines[start + 1:]:
        text = line.text
        item_links = [link for link in line.links if urls.classify(link.href) == "item"]
        if item_links:
            item_name = urls.name_from_url(item_links[0].href)
            sells.append({"item_id": slugify(item_name), "item_name": item_name, "category": category,
                          "price_zen": None, "details": None})
        elif _DETAILS.match(text) and sells:
            sells[-1]["details"] = text
        elif (price := _PRICE.match(text)) and sells:
            sells[-1]["price_zen"] = parse_int(price["zen"])
        elif (sub := _SUBSECTION.match(text)):
            category = sub["label"].strip()
        elif text:
            break  # fim da lista
    return sells, texts[:start]
