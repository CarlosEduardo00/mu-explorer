"""Mapas e zonas do Guide MU Online -> mapas do site.

O guia organiza os mapas como o jogo: um mapa pode ter zonas (andares, áreas). Uma zona é
- uma área do mesmo mapa (Atlans 1/2/3, Lost Tower 1..7, Aida 1/2, as áreas Alkamar e Ubaid de Acheron): o spot fica
  no mapa, com a zona como subcategoria; ou
- um mapa próprio no site (Kalima 1..7, andares do Deep Dungeon, Atlans Abyss 1..3, Karutan 1/2, Debenter, Nars...).

As correspondências foram conferidas contra o terreno do MuEmu: os spots de cada zona caem em chão andável do mapa
escolhido (100% em quase todas). Nomes que não estão aqui viram o slug do nome no guia.
"""
from __future__ import annotations

import re

from scrapers.common.ids import slugify

# Mapa do guia (slug) -> id do mapa no site, quando o nome difere.
MAP_IDS = {
    "elbeland": "elveland", "swamp-of-peace": "swamp-of-calmness", "cubera-mines": "cubera-mine",
    "atlans-abbys": "abyss-of-atlans", "temple-of-arnil": "arenil-temple", "gray-aida": "ashen-aida",
    "burning-kethotum": "blaze-kethotum", "kanturu-underground": "kanturu-undergrounds",
    "forgotten-raklion": "raklion-of-oblivion", "barracks-of-balgass": "balgass-barracks",
}
# (mapa, zona) do guia (slugs) -> mapa próprio no site.
ZONE_MAPS = {
    **{("kalima", f"kalima-{n}"): f"kalima-{n}" for n in range(1, 8)},
    **{("deep-dungeon", f"{n}{suffix}-floor"): f"deep-dungeon-{n}" for n, suffix in
       ((1, "st"), (2, "nd"), (3, "rd"), (4, "th"), (5, "th"))},
    ("atlans-abbys", "atlans-abbys-1"): "abyss-of-atlans", ("atlans-abbys", "atlans-abbys-2"): "abyss-of-atlans-2",
    ("atlans-abbys", "atlans-abbys-3"): "abyss-of-atlans-3",
    ("karutan", "karutan-1"): "karutan", ("karutan", "karutan-2"): "karutan-2",
    ("acheron", "debenter"): "debenter", ("acheron", "nars"): "nars", ("acheron", "uruk-mountain"): "uruk-mountain",
}


def map_id(group: str) -> str:
    """Id no site do mapa (grupo) do guia."""
    slug = slugify(group)
    return MAP_IDS.get(slug, slug)


def place(group: str, zone: str | None) -> tuple[str, str | None]:
    """(id do mapa no site, zona dentro dele ou None) de um mapa/zona do guia."""
    g = slugify(group)
    if zone is None:
        return map_id(group), None
    own = ZONE_MAPS.get((g, slugify(zone)))
    return (own, None) if own else (map_id(group), zone_label(zone))


def zone_label(zone: str) -> str:
    """Nome da zona como subcategoria: "Zone 3" -> "Área 3"; "1st Floor" -> "Andar 1"; o resto fica (nome próprio)."""
    m = re.fullmatch(r"Zone (\d+)", zone.strip())
    if m:
        return f"Área {m.group(1)}"
    m = re.fullmatch(r"(\d+)(?:st|nd|rd|th) Floor", zone.strip())
    if m:
        return f"Andar {m.group(1)}"
    return zone.strip()
