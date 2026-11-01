"""Parser do MasterMU: só fatos do guia de drop de itens de skill (sem copiar texto nem imagens).

Página `/guides/view/mu-online-skill-drop-guide-scrolls-orbs-crystals-and-parchments` (out/2026), dentro de
`article.hm-prose`: um `<h3 id="<classe>">` por classe seguido de uma tabela "Skill | Drop Location". A célula da skill
tem o nome (às vezes o do item, como "Articulation: Ignition Bomber Book of Laws", ou um nome antigo, como "Fortitude"
para Swell Life) e o ícone da skill (`.../skilldrop/<Nome>.webp`, que ajuda a casar o nome). A célula de local tem os
mapas separados por vírgula ou "Ruud Store" (comprado com Ruud, na loja de Priest James).

Saída: data/processed/mastermu/skill_drops.json, um registro por skill:
{class_id, label, icon_name, maps (nomes como na fonte), map_ids (ids do site, quando o nome casa), ruud_store,
season "S21", source, source_url, scraped_at}. Mapa sem id no site vai para o relatório (log), não some.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from selectolax.lexbor import LexborHTMLParser

from scrapers.common.storage import RawStore, dump_records

log = logging.getLogger("scrapers.mastermu")

SOURCE = "mastermu"
SEASON = "S21"
SKILL_DROP_KEY = "mu-online-skill-drop-guide-scrolls-orbs-crystals-and-parchments"
SKILL_DROP_URL = f"https://mastermu.net/guides/view/{SKILL_DROP_KEY}"

# Âncora da classe no guia -> id da classe no site.
CLASS_IDS = {
    "alchemist": "alchemist", "dark-wizard": "dark-wizard", "dark-knight": "dark-knight", "fairy-elf": "fairy-elf",
    "magic-gladiator": "magic-gladiator", "dark-lord": "dark-lord", "summoner": "summoner",
    "rage-fighter": "rage-fighter", "grow-lancer": "grow-lancer", "rune-wizard": "rune-mage", "slayer": "slayer",
    "gun-crusher": "gun-crusher", "white-wizard-kundun-mephis": "white-wizard", "lemuria": "mage",
    "illusion-knight": "illusion-knight", "crusader": "crusader",
}
# Nome do mapa no guia -> id do mapa no site. "Kanturu" no grupo de Atlans/Tarkan/Icarus/Aida é Kanturu Ruins (nível
# parecido); "Swamp" e "Swamp of Calmness" são o mesmo mapa (Swamp of Peace no Fanz), que no site tem os spots como
# Swamp of Calmness.
MAP_IDS = {
    "Devias": "devias", "Dungeon": "dungeon", "Lost Tower": "lost-tower", "Atlans": "atlans", "Tarkan": "tarkan",
    "Icarus": "icarus", "Aida": "aida", "Kanturu": "kanturu-ruins", "Raklion": "raklion", "Swamp": "swamp-of-calmness",
    "Swamp of Calmness": "swamp-of-calmness", "Vulcanus": "vulcanus", "Karutan": "karutan", "Acheron": "acheron",
}
RUUD_STORE = "ruud store"


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def icon_name(src: str | None) -> str | None:
    """'.../skilldrop/SwellLife.webp' -> 'Swell Life' (nome da skill no ícone, em palavras)."""
    m = re.search(r"/([A-Za-z0-9]+)\.(?:webp|png|jpg|gif)$", src or "")
    if not m:
        return None
    return re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=of[A-Z])", " ", m.group(1)).replace(" of", " of").strip()


def parse_skill_drops(html: str, fetched_at: str | None = None) -> tuple[list[dict], list[str]]:
    """Tabelas por classe -> registros. Devolve também os textos não mapeados (classe ou mapa desconhecido)."""
    tree = LexborHTMLParser(html)
    article = tree.css_first("article") or tree.body
    out: list[dict] = []
    unmapped: list[str] = []
    class_id = None
    for node in article.traverse(include_text=False):
        if node.tag == "h3":
            anchor = node.attributes.get("id") or ""
            class_id = CLASS_IDS.get(anchor)
            if anchor and class_id is None and anchor not in ("skill-item-types", "mu-helper-auto-pick"):
                unmapped.append(f"classe: {anchor}")
            continue
        if node.tag != "table" or class_id is None:
            continue
        head = [_clean(th.text()).lower() for th in node.css("thead th")]
        if head[:2] != ["skill", "drop location"]:
            continue
        for tr in node.css("tbody tr"):
            cells = tr.css("td")
            if len(cells) < 2:
                continue
            img = cells[0].css_first("img")
            label = _clean(cells[0].text())
            where = _clean(cells[1].text())
            ruud = where.lower() == RUUD_STORE
            maps = [] if ruud else [m.strip() for m in where.split(",") if m.strip()]
            for name in maps:
                if name not in MAP_IDS:
                    unmapped.append(f"mapa: {name}")
            out.append({
                "class_id": class_id, "label": label, "icon_name": icon_name(img.attributes.get("src") if img else None),
                "maps": maps, "map_ids": list(dict.fromkeys(MAP_IDS[m] for m in maps if m in MAP_IDS)),
                "ruud_store": ruud, "season": SEASON, "source": SOURCE, "source_url": SKILL_DROP_URL,
                "scraped_at": fetched_at,
            })
        class_id = None
    return out, sorted(set(unmapped))


def parse_store(data_dir: Path) -> int:
    store = RawStore(data_dir / "raw")
    page = store.load(SOURCE, "guides", SKILL_DROP_KEY, SKILL_DROP_URL)
    if page is None:
        log.error("guia de drop de skills não está em data/raw/mastermu (rode: python -m scrapers.mastermu fetch)")
        return 1
    rows, unmapped = parse_skill_drops(page.html, page.meta.get("fetched_at"))
    for line in unmapped:
        log.warning("não mapeado: %s", line)
    out = data_dir / "processed" / SOURCE
    out.mkdir(parents=True, exist_ok=True)
    dump_records(out / "skill_drops.json", rows)
    fetched = page.meta.get("fetched_at")
    dump_records(out / "sources.json", [{
        "id": SOURCE, "name": "MasterMU", "url": "https://mastermu.net",
        "credit": "Fatos do MasterMU (mastermu.net), servidor privado Season 21: mapas onde dropam os itens de skill e o "
                  "que vem da loja de Ruud. Os guias de eventos e sistemas do site foram reescritos por nós a partir dos "
                  "fatos; não copiamos texto nem imagens.",
        "pages": 1, "first_scraped_at": fetched, "last_scraped_at": fetched,
    }])
    log.info("%d skills de %d classes (%d na Ruud Store) · não mapeados: %d · %s", len(rows),
             len({r["class_id"] for r in rows}), sum(r["ruud_store"] for r in rows), len(unmapped), out / "skill_drops.json")
    return 0
