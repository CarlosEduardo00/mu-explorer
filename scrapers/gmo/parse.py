"""Parser dos guias de mapa do Global MU Online (/guides/<mapa>/).

Estrutura real (out/2026), dentro de `.guideContent`:
- `h1` "<Mapa> Map Guide"; imagem 3D do mapa em `img.lmBase`.
- Zonas de spawn: `<polygon class="lmZone ..." data-m="<nº do monstro no jogo>" data-t="<nome>"
  data-c="x1,y1 – x2,y2" data-d="Lv 66 · 14,000 HP · 420–460 dmg · 9 here" data-img="...">`.
- Marcadores: `<button class="lmM t-spot|t-gate|t-npc..." data-t data-c="x, y" data-d>`; `t-spot` são os spots
  de caça que o minimapa do próprio jogo marca.
- Cards `.monCard` (imagem, nome) e a tabela "Full stat table" (Monster, Lv, HP, Damage, Def, Atk rate, Block,
  ..., Respawn, On map).
- FAQ "What level do I need for <Mapa>?" com o nível do warp.
Páginas sem zonas nem tabela de monstros (classes, NPCs, sistemas) são ignoradas aqui.
"""
from __future__ import annotations

import html as htmllib
import json
import logging
import re
from pathlib import Path
from urllib.parse import urljoin

from selectolax.lexbor import LexborHTMLParser

from scrapers.common.ids import slugify
from scrapers.common.model import validate
from scrapers.common.storage import RawStore, dump_records

log = logging.getLogger("scrapers.gmo")

SOURCE = "gmo"
BASE = "https://globalmuonline.com"
SEASON = "S21"
MARKER_KINDS = {"t-spot": "spot", "t-gate": "gate", "t-warp": "warp", "t-npc": "npc", "t-shop": "shop",
                "t-quest": "quest", "t-event": "event"}


def _num(text: str | None) -> int | None:
    if text is None:
        return None
    m = re.search(r"-?[\d,]+", text)
    return int(m.group(0).replace(",", "")) if m else None


def _range(text: str | None) -> tuple[int | None, int | None]:
    nums = [int(n.replace(",", "")) for n in re.findall(r"[\d,]+", text or "")]
    return (nums[0], nums[-1]) if nums else (None, None)


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    # data-* vem com entidades escapadas duas vezes ("&amp;ndash;")
    return re.sub(r"\s+", " ", htmllib.unescape(htmllib.unescape(text))).strip() or None


def _coords(text: str | None) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", text or "")]


def _seconds(text: str | None) -> int | None:
    if not text:
        return None
    m = re.match(r"\s*([\d.,]+)\s*(s|sec|m|min|h)", text)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    return int(value * {"s": 1, "sec": 1, "m": 60, "min": 60, "h": 3600}[m.group(2)])


def zone_count(detail: str | None) -> int | None:
    """Quantidade de monstros da zona: "... · 9 here" (alguns mapas) ou "... · 9 per spot" (outros)."""
    m = re.search(r"([\d,]+)\s*(?:here|per spot)\b", detail or "")
    return _num(m.group(1)) if m else None


def _stat_table(root) -> list[dict]:
    """Linhas da tabela cujo cabeçalho começa com Monster/Lv/HP, como dicionários coluna -> texto."""
    for table in root.css("table"):
        rows = table.css("tr")
        if not rows:
            continue
        head = [c.text(strip=True) for c in rows[0].css("th,td")]
        if head[:3] == ["Monster", "Lv", "HP"]:
            return [dict(zip(head, [c.text(strip=True) for c in r.css("th,td")])) for r in rows[1:]]
    return []


def parse_map_guide(html: str, meta: dict) -> dict | None:
    """{map, monsters, spawns, markers} de um guia de mapa; None se a página não é guia de mapa."""
    tree = LexborHTMLParser(html)
    root = tree.css_first(".guideContent") or tree.body
    zones = root.css("polygon.lmZone")
    table = _stat_table(root)
    h1 = tree.css_first("h1")
    if not h1 or (not zones and not table):
        return None
    name = re.sub(r"\s*Map Guide\s*$", "", h1.text(strip=True)).strip()
    map_id = slugify(name)
    url = meta.get("url") or meta.get("final_url") or ""
    prov = {"season": SEASON, "source": SOURCE, "source_url": url, "scraped_at": meta.get("fetched_at")}

    images = {}
    for card in root.css(".monCard"):
        img, title = card.css_first("img"), card.css_first("b")
        if img and title and img.attributes.get("src"):
            images[title.text(strip=True)] = urljoin(BASE, img.attributes["src"])

    monsters: dict[str, dict] = {}
    for row in table:
        mname = row.get("Monster")
        if not mname:
            continue
        lo, hi = _range(row.get("Damage"))
        monsters[mname] = {
            "id": slugify(mname), "name": mname, "number": None, "level": _num(row.get("Lv")), "difficulty": None,
            "hp": _num(row.get("HP")), "atk_min": lo, "atk_max": hi, "atk_rate": _num(row.get("Atk rate")),
            "def": _num(row.get("Def")), "def_rate": _num(row.get("Block")), "elemental_def": None,
            "elemental_dmg_min": None, "elemental_dmg_max": None,
            "respawn_seconds": _seconds(row.get("Respawn")), "respawn_raw": row.get("Respawn") or None,
            "drops_normal_items": None, "notes": [], "image_url": images.get(mname),
            **prov, "page_updated_at": _updated(tree),
        }

    spawns = []
    for zone in zones:
        a = zone.attributes
        mname = _clean(a.get("data-t"))
        if not mname:
            continue
        number = _num(a.get("data-m"))
        if mname in monsters and monsters[mname]["number"] is None:
            monsters[mname]["number"] = number
        if mname not in monsters:   # zona de monstro que não está na tabela (evento, especial)
            detail = _clean(a.get("data-d")) or ""
            lo, hi = _range(re.search(r"([\d,]+\s*[–-]\s*[\d,]+)\s*dmg", detail).group(1)) if "dmg" in detail else (None, None)
            monsters[mname] = {
                "id": slugify(mname), "name": mname, "number": number, "level": _num(re.search(r"Lv\s*([\d,]+)", detail).group(1)) if "Lv" in detail else None,
                "difficulty": None, "hp": _num(re.search(r"([\d,]+)\s*HP", detail).group(1)) if "HP" in detail else None,
                "atk_min": lo, "atk_max": hi, "atk_rate": None, "def": None, "def_rate": None, "elemental_def": None,
                "elemental_dmg_min": None, "elemental_dmg_max": None, "respawn_seconds": None, "respawn_raw": None,
                "drops_normal_items": None, "notes": [], "image_url": urljoin(BASE, a["data-img"]) if a.get("data-img") else None,
                **prov, "page_updated_at": _updated(tree),
            }
        c = _coords(a.get("data-c"))
        count = zone_count(_clean(a.get("data-d")))
        spawns.append({
            "monster_id": slugify(mname), "map_id": map_id, "kind": "spot",
            "x": c[0] if len(c) > 0 else None, "y": c[1] if len(c) > 1 else None,
            "x2": c[2] if len(c) > 3 else None, "y2": c[3] if len(c) > 3 else None,
            "radius": None, "count": count, **prov,
        })

    markers = []
    for button in root.css("button.lmM"):
        a = button.attributes
        kind = next((MARKER_KINDS[c] for c in (a.get("class") or "").split() if c in MARKER_KINDS), None)
        if kind is None:
            continue
        title = _clean(a.get("data-t")) or kind
        if kind == "spot" and "hot" in title.lower():
            kind = "hot_spot"
        c = _coords(a.get("data-c"))
        markers.append({"map_id": map_id, "kind": kind, "name": title, "x": c[0] if c else None,
                        "y": c[1] if len(c) > 1 else None, "description": _clean(a.get("data-d")),
                        "source": SOURCE, "source_url": url, "scraped_at": meta.get("fetched_at")})

    base_img = root.css_first("img.lmBase") or root.css_first(".lmStage img")
    level = _warp_level(root, name)
    record = {
        "id": map_id, "name": name, "parent_id": None, "description": _description(tree), "quick_facts": [],
        "valued_drops": {}, "monsters": list(dict.fromkeys(slugify(m) for m in monsters)), "special_monsters": [],
        "bosses": [], "npcs": [], "connections": [], "notes": [],
        "image_url": urljoin(BASE, base_img.attributes["src"]) if base_img and base_img.attributes.get("src") else None,
        **prov, "page_updated_at": _updated(tree),
        "level_required": level, "level_recommended_min": None, "level_recommended_max": None,
    }
    return {"map": record, "monsters": list(monsters.values()), "spawns": spawns, "markers": markers}


def _updated(tree) -> str | None:
    m = re.search(r"Last updated:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", tree.text())
    if not m:
        return None
    from datetime import datetime
    return datetime.strptime(m.group(1), "%B %d, %Y").strftime("%Y-%m-%d")


def _description(tree) -> str | None:
    meta = tree.css_first('meta[name="description"]')
    return _clean(meta.attributes.get("content")) if meta else None


def _warp_level(root, name: str) -> int | None:
    """Nível do FAQ 'What level do I need for <Mapa>?' (primeiro número de 'Level N')."""
    text = root.text(separator="\n")
    m = re.search(r"What level do I need[^\n]*\n\s*([^\n]+)", text)
    if not m:
        return None
    lv = re.search(r"[Ll]evel\s+([\d,]+)", m.group(1))
    return _num(lv.group(1)) if lv else None


def merge_monsters(rows: list[dict]) -> list[dict]:
    """O mesmo monstro aparece em vários mapas: fica o primeiro registro, com imagem e número preenchidos se faltarem."""
    out: dict[str, dict] = {}
    for row in rows:
        kept = out.setdefault(row["id"], row)
        for key in ("image_url", "number", "level", "hp", "respawn_seconds"):
            if kept.get(key) is None and row.get(key) is not None:
                kept[key] = row[key]
    return list(out.values())


def parse_store(data_dir: Path) -> int:
    store = RawStore(data_dir / "raw")
    maps, monsters, spawns, markers, skipped = [], [], [], [], 0
    for page in sorted(store.iter(SOURCE, "guides"), key=lambda p: p.path.name):
        if not 200 <= page.meta.get("status", 0) < 300:
            continue
        result = parse_map_guide(page.html, page.meta)
        if result is None:
            skipped += 1
            continue
        maps.append(result["map"])
        monsters += result["monsters"]
        spawns += result["spawns"]
        markers += result["markers"]
    monsters = merge_monsters(monsters)
    out = data_dir / "processed" / SOURCE
    out.mkdir(parents=True, exist_ok=True)
    data = {"map": maps, "monster": monsters, "spawn": spawns, "map_marker": markers}
    errors = [f"{e} {r.get('id') or r.get('monster_id') or r.get('name')}: {err}" for e, rows in data.items() for r in rows
              for err in validate(e, r)]
    for name, rows in (("maps", maps), ("monsters", monsters), ("spawns", spawns), ("map_markers", markers)):
        dump_records(out / f"{name}.json", rows)
    dump_records(out / "drops.json", [])
    dump_records(out / "sources.json", [{
        "id": SOURCE, "name": "Global MU Online", "url": BASE,
        "credit": "Guias de mapas do Global MU Online (globalmuonline.com), servidor privado Season 21. Uso só local até haver autorização.",
        "pages": len(maps), "first_scraped_at": min((m["scraped_at"] for m in maps if m["scraped_at"]), default=None),
        "last_scraped_at": max((m["scraped_at"] for m in maps if m["scraped_at"]), default=None)}])
    for err in errors[:20]:
        log.error(err)
    with_img = sum(1 for m in monsters if m["image_url"])
    log.info("mapas: %d · monstros: %d (%d com imagem) · spawns: %d · marcadores: %d · outras páginas: %d · erros de schema: %d",
             len(maps), len(monsters), with_img, len(spawns), len(markers), skipped, len(errors))
    return 1 if errors else 0
