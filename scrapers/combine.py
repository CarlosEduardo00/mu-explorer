"""Cruzamento de fontes (fase 3): Fanz como base, MuEmu completando o que o Fanz não publica.

python -m scrapers.combine  ->  data/processed/combined/*.json, item_matches.json, monster_matches.json
                                e combine_report.md (o que foi preenchido, o que não casou, divergências).

Regras:
- Global MU Online (se data/processed/gmo existir): imagens de monstros que faltam, monstros e mapas novos e
  as zonas de spawn da S21 (nos mapas que ele cobre, substituem os spawns do MuEmu); marcadores em map_markers.json.
- Itens: casam pelo nome. Excellent/ancient do Fanz casam com o item base do MuEmu (no MU eles têm o mesmo
  grupo/índice do item base). Do MuEmu vêm group, index, durability e category, só quando o Fanz não tem.
- Monstros: casam pelo nome e, havendo variantes (ex.: Aegis em Kalima 1-7), pelo nível. Do MuEmu vêm o
  número do monstro e o respawn. Os pontos de spawn com coordenadas do MuEmu entram para monstros casados.
- Os valores do Fanz nunca são sobrescritos; diferenças entre as fontes vão para o relatório.
"""
from __future__ import annotations

import argparse
import difflib
import json
import logging
import re
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from scrapers.common import qa
from scrapers.common.ids import slugify
from scrapers.common.model import REPO_ROOT
from scrapers.common.storage import dump_records

log = logging.getLogger("scrapers.combine")
OUTPUT = {"item": "items.json", "monster": "monsters.json", "map": "maps.json", "npc": "npcs.json",
          "spawn": "spawns.json", "drop": "drops.json", "source": "sources.json"}


def _load(directory: Path) -> dict[str, list[dict]]:
    data = qa.load(directory)
    path = directory / "sources.json"
    data["source"] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    return data


def _index(rows: list[dict]) -> dict[str, list[dict]]:
    by_name: dict[str, list[dict]] = {}
    for row in rows:
        by_name.setdefault(slugify(row["name"]), []).append(row)
    return by_name


def item_keys(item: dict) -> list[tuple[str, str]]:
    """Chaves de busca (método, slug) em ordem de preferência."""
    name = item["name"]
    keys = [("nome", slugify(name))]
    if name.lower().startswith("excellent "):
        keys.append(("item base do excellent", slugify(name[len("excellent "):])))
    elif item.get("grade") == "ancient" and len(name.split()) > 2:
        keys.append(("item base do ancient", slugify(name.split(" ", 1)[1])))
    return keys


def match_items(fanz: list[dict], muemu: list[dict]) -> tuple[list[dict], list[dict], list[str]]:
    """(itens enriquecidos, casamentos, divergências)."""
    by_name = _index(muemu)
    out, matches, diffs = [], [], []
    for item in fanz:
        item = dict(item)
        for method, key in item_keys(item):
            candidates = sorted(by_name.get(key, []), key=lambda m: (m["group"], m["index"]))
            if not candidates:
                continue
            base = candidates[0]
            matches.append({"fanz_id": item["id"], "muemu_id": base["id"], "method": method,
                            "candidates": [c["id"] for c in candidates] if len(candidates) > 1 else []})
            for field in ("group", "index", "durability", "category"):
                if item.get(field) is None and base.get(field) is not None:
                    item[field] = base[field]
            if method == "nome":
                diffs.extend(_item_diffs(item, base))
            break
        out.append(item)
    return out, matches, diffs


def _item_diffs(fanz: dict, muemu: dict) -> list[str]:
    diffs = []
    for stat, value in fanz["requirements"].items():
        other = muemu["requirements"].get(stat)
        if value is not None and other is not None and value != other:
            diffs.append(f"item {fanz['id']}: requisito {stat} Fanz={value} MuEmu={other}")
    for stat in ("defense", "damage_min", "damage_max"):
        a, b = fanz["stats"].get(stat), muemu["stats"].get(stat)
        if a is not None and b is not None and a != b:
            diffs.append(f"item {fanz['id']}: {stat} Fanz={a} MuEmu={b}")
    return diffs


# Diferença de nível aceita num par só por nome: até ~10 níveis é rebalanceamento entre seasons; bem mais
# que isso costuma ser outra criatura com o mesmo nome (ex.: Death King boss 67 x invasão dourada 30).
MAX_LEVEL_GAP = 20


def match_monsters(fanz: list[dict], muemu: list[dict]) -> tuple[list[dict], list[dict], list[str]]:
    by_name = _index(muemu)
    out, matches, diffs = [], [], []
    for monster in fanz:
        monster = dict(monster)
        candidates = by_name.get(slugify(monster["name"]), [])
        if candidates:
            level = monster.get("level")
            same = [c for c in candidates if c.get("level") == level]
            if same:
                base, method = same[0], "nome e nível"
            else:
                base = min(candidates, key=lambda c: abs((c.get("level") or 0) - (level or 0)))
                gap = abs((base.get("level") or 0) - (level or 0))
                if gap > MAX_LEVEL_GAP:
                    diffs.append(f"monstro {monster['id']}: par descartado, nível Fanz={level} MuEmu={base.get('level')}")
                    out.append(monster)
                    continue
                method = "nome (nível diferente)"
                diffs.append(f"monstro {monster['id']}: nível Fanz={level} MuEmu={base.get('level')}")
            matches.append({"fanz_id": monster["id"], "muemu_id": base["id"], "method": method,
                            "candidates": [c["id"] for c in candidates] if len(candidates) > 1 else []})
            for field in ("number", "respawn_seconds", "respawn_raw"):
                if monster.get(field) is None:
                    monster[field] = base.get(field)
            if method == "nome e nível":
                for stat in ("hp", "atk_min", "atk_max", "def"):
                    a, b = monster.get(stat), base.get(stat)
                    if a is not None and b is not None and a != b:
                        diffs.append(f"monstro {monster['id']}: {stat} Fanz={a} MuEmu={b}")
        out.append(monster)
    return out, matches, diffs


SPAWN_DEFAULTS = {"kind": None, "x": None, "y": None, "x2": None, "y2": None, "radius": None, "count": None}


def combine(fanz: dict[str, list[dict]], muemu: dict[str, list[dict]]) -> tuple[dict, dict, list[str]]:
    # Tolera JSON do Fanz gerado antes dos campos novos de monstro/spawn.
    fanz = dict(fanz, monster=[{"number": None, **m} for m in fanz["monster"]],
                spawn=[{**SPAWN_DEFAULTS, **s} for s in fanz["spawn"]])
    items, item_matches, item_diffs = match_items(fanz["item"], muemu["item"])
    monsters, monster_matches, monster_diffs = match_monsters(fanz["monster"], muemu["monster"])
    to_fanz = {m["muemu_id"]: m["fanz_id"] for m in monster_matches}
    spawns = list(fanz["spawn"])
    muemu_spawns = [dict(s, monster_id=to_fanz[s["monster_id"]]) for s in muemu["spawn"] if s["monster_id"] in to_fanz]
    spawns += muemu_spawns
    used_maps = {s["map_id"] for s in spawns}
    maps = {m["id"]: m for m in fanz["map"]}
    for m in muemu["map"]:
        if m["id"] in used_maps:
            maps.setdefault(m["id"], m)
    data = {
        "item": items, "monster": monsters, "map": [maps[k] for k in sorted(maps)], "npc": fanz.get("npc", []),
        "spawn": spawns,
        "drop": [{**d, "map_id": d.get("map_id")} for d in fanz["drop"]],
        "source": fanz.get("source", []) + muemu.get("source", []),
    }
    matches = {"item": item_matches, "monster": monster_matches}
    return data, matches, item_diffs + monster_diffs


# Grafias do GMO -> id do mapa como no Fanz (o mesmo mapa com outro nome).
GMO_MAP_ALIASES = {
    "elbeland": "elveland", "kubera-mine": "cubera-mine", "nixie-lake": "nixies-lake",
    "kanturu-remain": "kanturu-relics", "balgass-refuge": "balgass-resting-place",
}


def _gmo_map_id(map_id: str, known: set[str]) -> tuple[str, str | None]:
    """(id, parent_id). Andares numerados (deep-dungeon-3, karutan-2) ficam com o mapa-pai, se ele existir."""
    map_id = GMO_MAP_ALIASES.get(map_id, map_id)
    base = re.sub(r"-\d+$", "", map_id)
    return map_id, (base if base != map_id and base in known else None)


ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7"}
# Nomes das listas de drop do GMO (/drop/location) -> id do mapa no site, quando o slug não bate.
GMO_DROP_MAP_ALIASES = {
    "abyss-of-atlas-1": "abyss-of-atlans", "abyss-of-atlas-2": "abyss-of-atlans-2", "abyss-of-atlas-3": "abyss-of-atlans-3",
    "barracks-of-balgass": "balgass-barracks", "land-of-trial": "land-of-trials", "deepdungeon-1": "deep-dungeon-1",
    "deepdungeon-2": "deep-dungeon-2", "deepdungeon-3": "deep-dungeon-3", "deepdungeon-4": "deep-dungeon-4",
    "deepdungeon-5": "deep-dungeon-5", "urkmountain": "uruk-mountain", "urk-mountain": "uruk-mountain",
    "swamp-of-calmness": "swamp-of-calmness", "kanturu-remain": "kanturu-relics", "kanturu-ruins": "kanturu-1",
}


def gmo_drop_map_id(name: str, known: set[str]) -> str | None:
    """'Kalima I' -> 'kalima-1'; 'AbyssOfAtlas 3' -> 'abyss-of-atlans-3'; mapa desconhecido -> None."""
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    slug = slugify(spaced)
    parts = slug.split("-")
    if parts and parts[-1] in ROMAN:
        parts[-1] = ROMAN[parts[-1]]
    slug = "-".join(parts)
    for candidate in (slug, GMO_DROP_MAP_ALIASES.get(slug), GMO_MAP_ALIASES.get(slug), slug.replace("-1", "") if slug.endswith("-1") else None):
        if candidate and candidate in known:
            return candidate
    return None


def _name_key(name: str) -> str:
    """Chave de nome para casar grafias: minúsculas, sem pontuação, sem "'s", "Helmet" = "Helm"."""
    text = re.sub(r"\bhelmet\b", "helm", name.lower().replace("'s", "").replace("’s", ""))
    return re.sub(r"[^a-z0-9]", "", text)


def item_resolver(items: list[dict], muemu_names: dict[str, str] | None = None) -> "Callable[[str], dict | None]":
    """Acha o item do site pelo nome de outra fonte: igual (slug ou chave de nome), pelo nome do MuEmu (mesmo
    grupo/índice), ou parecido (difflib ≥ 0,9 com a mesma última palavra: "Storm Jahad Armor" -> "Storm Zahard Armor").
    Só itens de grau normal (ou sem grau) entram no casamento aproximado: as listas trazem o item base."""
    by_id = {i["id"]: i for i in items}
    by_key = {}
    for i in items:
        by_key.setdefault(_name_key(i["name"]), i)
    base = {k: i for k, i in by_key.items() if i.get("grade") in ("normal", None)}
    base_keys = list(base)
    cache: dict[str, dict | None] = {}

    def resolve(name: str) -> dict | None:
        if name in cache:
            return cache[name]
        found = by_id.get(slugify(name)) or by_key.get(_name_key(name))
        if found is None and muemu_names:
            found = by_id.get(muemu_names.get(slugify(name), ""))
        if found is None:
            key = _name_key(name)
            last = name.lower().split()[-1] if name.split() else ""
            for cand in difflib.get_close_matches(key, base_keys, n=3, cutoff=0.9):
                if base[cand]["name"].lower().split()[-1].rstrip("s") == last.rstrip("s"):
                    found = base[cand]
                    break
        cache[name] = found
        return found
    return resolve


def expand_drop_lists(lists: list[dict]) -> list[dict]:
    """drop_lists.json do GMO (mapa -> monstro -> nomes) -> registros de drop ainda com os nomes da fonte."""
    out = []
    for lst in lists:
        prov = {"season": lst.get("season"), "source": "gmo", "source_url": lst["source_url"], "scraped_at": lst["scraped_at"]}
        for monster in lst["monsters"]:
            for name in monster["items"]:
                out.append({"monster_id": slugify(monster["name"]), "item_id": slugify(name), "item_name": name, "kind": "unknown",
                            "table": None, "category": None, "quantity": None, "rate": None, "map_id": None,
                            "monster_name": monster["name"], "map_name": lst["map_name"], **prov})
    return out


def add_gmo_drops(data: dict, drops: list[dict], to_id: dict[str, str], muemu_names: dict[str, str] | None = None) -> Counter:
    """Listas de drop por mapa do GMO (servidor S21): monstro -> item no mapa. Só completam itens sem nenhum drop nas
    tabelas do Fanz (o jogo oficial vem primeiro; e o arquivo de drops não passa do limite de 25 MB por arquivo do
    Cloudflare). Liga aos ids do site: monstro pelo nome (também sem o número de variante, "Aegis 1"), item pelo nome
    (item_resolver) e mapa pelo nome. Item que o site não tem fica de fora (contado no relatório)."""
    stats = Counter()
    if not drops:
        return stats
    resolve_item = item_resolver(data["item"], muemu_names)
    by_slug = _index(data["monster"])
    monsters = {m["id"] for m in data["monster"]}
    known_maps = {m["id"] for m in data["map"]}

    def monster_id(raw_id: str) -> str | None:
        for slug in (raw_id, re.sub(r"-?\d+$", "", raw_id)):
            if slug in to_id:
                return to_id[slug]
            if slug in by_slug:
                return by_slug[slug][0]["id"]
            if slug in monsters:
                return slug
        return None

    # Par monstro -> item que as tabelas do Fanz já trazem não se repete (o Fanz vem primeiro). Um registro por par:
    # map_id fica null quando o monstro aparece (spawns) num dos mapas da lista (o site acha os mapas pelos spawns);
    # senão, guarda o primeiro mapa da lista. Assim o drops.json fica bem abaixo dos 25 MB por arquivo do Cloudflare.
    covered = {(d["monster_id"], d["item_id"]) for d in data["drop"]}
    spawn_maps: dict[str, set[str]] = {}
    for s in data.get("spawn", []):
        spawn_maps.setdefault(s["monster_id"], set()).add(s["map_id"])
    pairs: dict[tuple[str, str], dict] = {}
    out = []
    for d in drops:
        item = resolve_item(d["item_name"])
        mid = monster_id(d["monster_id"])
        if item is None:
            stats["drops do GMO com item que o site não tem"] += 1
            continue
        if mid is None:
            stats["drops do GMO com monstro desconhecido"] += 1
            continue
        if (mid, item["id"]) in covered:
            stats["drops do GMO já nas tabelas do Fanz"] += 1
            continue
        map_id = gmo_drop_map_id(d.get("map_name") or "", known_maps)
        key = (mid, item["id"])
        if key in pairs:
            if map_id and map_id in spawn_maps.get(mid, set()):
                pairs[key]["map_id"] = None
            continue
        record = {k: v for k, v in d.items() if k not in ("monster_name", "map_name")}
        record.update(monster_id=mid, item_id=item["id"], item_name=item["name"],
                      map_id=None if map_id in spawn_maps.get(mid, set()) else map_id,
                      kind=item["grade"] if item.get("grade") in ("normal", "excellent", "ancient", "socket") else "unknown")
        pairs[key] = record
        out.append(record)
    data["drop"] = data["drop"] + out
    stats["drops do GMO (pares monstro -> item)"] = len(out)
    stats["itens com drop do GMO"] = len({r["item_id"] for r in out})
    return stats


def add_gmo(data: dict, gmo: dict, muemu_names: dict[str, str] | None = None) -> dict:
    """Global MU Online (S21, só local): imagens de monstros que faltam, monstros e mapas novos, e as zonas de
    spawn. Nos mapas que o GMO cobre, os spawns dele substituem os do MuEmu (S21 e mais recentes; evita spots
    duplicados). Valores que já existem não são sobrescritos. Devolve contagens para o relatório."""
    stats = Counter()
    if not gmo.get("monster"):
        return stats
    known = {m["id"] for m in data["map"]}
    rename = {m["id"]: _gmo_map_id(m["id"], known) for m in gmo["map"]}
    gmo = dict(gmo,
               map=[dict(m, id=rename[m["id"]][0], parent_id=m.get("parent_id") or rename[m["id"]][1]) for m in gmo["map"]],
               spawn=[dict(s, map_id=rename.get(s["map_id"], (s["map_id"], None))[0]) for s in gmo["spawn"]],
               map_marker=[dict(k, map_id=rename.get(k["map_id"], (k["map_id"], None))[0]) for k in gmo.get("map_marker", [])])
    monsters = {m["id"]: m for m in data["monster"]}
    by_slug = _index(data["monster"])
    to_id = {}
    for g in gmo["monster"]:
        found = by_slug.get(slugify(g["name"]))
        if found:
            target = min(found, key=lambda m: abs((m.get("level") or 0) - (g.get("level") or 0)))
            to_id[g["id"]] = target["id"]
            for m in found:
                if m.get("image_url") is None and g.get("image_url"):
                    m["image_url"] = g["image_url"]
                    stats["imagens"] += 1
        elif g["id"] not in monsters:
            monsters[g["id"]] = dict(g)
            to_id[g["id"]] = g["id"]
            stats["monstros novos"] += 1
    data["monster"] = sorted(monsters.values(), key=lambda m: m["id"])
    gmo_maps = {s["map_id"] for s in gmo["spawn"]}
    kept = [s for s in data["spawn"] if not (s["map_id"] in gmo_maps and s.get("source") == "muemu")]
    stats["spawns do MuEmu trocados"] = len(data["spawn"]) - len(kept)
    new = [dict(s, monster_id=to_id.get(s["monster_id"], s["monster_id"])) for s in gmo["spawn"]]
    data["spawn"] = kept + new
    stats["spawns do GMO"] = len(new)
    maps = {m["id"]: m for m in data["map"]}
    for g in gmo["map"]:
        if g["id"] not in maps:
            maps[g["id"]] = g
            stats["mapas novos"] += 1
        else:
            m = maps[g["id"]]
            for field in ("level_required", "image_url", "description"):
                if m.get(field) is None and g.get(field) is not None:
                    m[field] = g[field]
    data["map"] = [maps[k] for k in sorted(maps)]
    data["map_marker"] = gmo.get("map_marker", [])
    data["source"] = data["source"] + gmo.get("source", [])
    stats.update(add_gmo_drops(data, gmo.get("drop", []), to_id, muemu_names))
    return stats


def build_report(data: dict, matches: dict, diffs: list[str], fanz: dict, muemu: dict) -> str:
    def filled(field: str, entity: str) -> str:
        before = sum(1 for r in fanz[entity] if r.get(field) is not None)
        after = sum(1 for r in data[entity] if r.get(field) is not None)
        return f"{before} → {after} de {len(data[entity])}"

    item_methods = Counter(m["method"] for m in matches["item"])
    monster_methods = Counter(m["method"] for m in matches["monster"])
    ambiguous = [m for m in matches["item"] if m["candidates"]]
    matched_items = {m["fanz_id"] for m in matches["item"]}
    matched_monsters = {m["fanz_id"] for m in matches["monster"]}
    fanz_maps, muemu_maps = {m["id"] for m in fanz["map"]}, {m["id"] for m in muemu["map"]}
    out = [
        "# Cruzamento Fanz + MuEmu", "",
        "Base: Fanz. O MuEmu só preenche campos vazios; os valores do Fanz nunca são sobrescritos.", "",
        "## Casamento", "",
        f"- Itens: {len(matched_items)} de {len(fanz['item'])} casados ({dict(item_methods)}); "
        f"{len(ambiguous)} com mais de um candidato no MuEmu (usado o de menor grupo/índice).",
        f"- Monstros: {len(matched_monsters)} de {len(fanz['monster'])} casados ({dict(monster_methods)}).",
        f"- Spawns com coordenadas vindos do MuEmu: {len(data['spawn']) - len(fanz['spawn'])}.", "",
        "## Campos preenchidos (antes → depois)", "",
        f"- item.group: {filled('group', 'item')}",
        f"- item.index: {filled('index', 'item')}",
        f"- item.durability: {filled('durability', 'item')}",
        f"- item.category: {filled('category', 'item')}",
        f"- monster.respawn_seconds: {filled('respawn_seconds', 'monster')}",
        f"- monster.number: {filled('number', 'monster')}", "",
        "## Mapas", "",
        f"- Só no Fanz: {', '.join(sorted(fanz_maps - muemu_maps)) or 'nenhum'}",
        f"- Só no MuEmu: {', '.join(sorted(muemu_maps - fanz_maps)) or 'nenhum'}", "",
        f"## Itens do Fanz sem par no MuEmu ({len(fanz['item']) - len(matched_items)})", "",
        ", ".join(sorted(i["name"] for i in fanz["item"] if i["id"] not in matched_items)[:80]) or "Nenhum.", "",
        f"## Monstros do Fanz sem par no MuEmu ({len(fanz['monster']) - len(matched_monsters)})", "",
        ", ".join(sorted(m["name"] for m in fanz["monster"] if m["id"] not in matched_monsters)[:80]) or "Nenhum.", "",
        f"## Divergências de valores ({len(diffs)})", "",
        "Itens e monstros casados pelo nome exato (e nível) cujos números diferem. O MuEmu é Season 16 de",
        "servidor privado; o Fanz acompanha o global. Diferença aqui não é erro de parse.", "",
    ]
    out += [f"- {d}" for d in diffs[:150]]
    if len(diffs) > 150:
        out.append(f"- ... e mais {len(diffs) - 150} (lista completa em divergences.json)")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scrapers.combine", description="Cruza Fanz e MuEmu")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    processed = args.data_dir / "processed"
    fanz, muemu = _load(processed / "fanz"), _load(processed / "muemu")
    data, matches, diffs = combine(fanz, muemu)
    gmo_dir = processed / "gmo"
    gmo = _load(gmo_dir) if gmo_dir.exists() else {}
    if gmo_dir.exists():
        markers = gmo_dir / "map_markers.json"
        gmo["map_marker"] = json.loads(markers.read_text(encoding="utf-8")) if markers.exists() else []
        lists = gmo_dir / "drop_lists.json"
        gmo["drop"] = expand_drop_lists(json.loads(lists.read_text(encoding="utf-8"))) if lists.exists() else []
    # Nome do MuEmu -> item do site (mesmo grupo/índice), para casar grafias de outras fontes de emulador.
    muemu_by_id = {m["id"]: m for m in muemu["item"]}
    muemu_names = {slugify(muemu_by_id[match["muemu_id"]]["name"]): match["fanz_id"]
                   for match in matches["item"] if match["muemu_id"] in muemu_by_id}
    gmo_stats = add_gmo(data, gmo, muemu_names)
    out = processed / "combined"
    out.mkdir(parents=True, exist_ok=True)
    for entity, filename in OUTPUT.items():
        dump_records(out / filename, data[entity])
    for entity in ("item", "monster"):
        dump_records(out / f"{entity}_matches.json", matches[entity])
    dump_records(out / "map_markers.json", data.get("map_marker", []))
    report = build_report(data, matches, diffs, fanz, muemu)
    if gmo_stats:
        report += "\n## Global MU Online (S21, só local)\n\n" + "\n".join(f"- {k}: {v}" for k, v in gmo_stats.items()) + "\n"
    (out / "combine_report.md").write_text(report, encoding="utf-8")
    from scrapers.common.storage import RawStore
    from scrapers.fanz.pipeline import dead_item_ids
    dead = dead_item_ids(RawStore(args.data_dir / "raw"))
    checks = qa.check_schema({k: v for k, v in data.items() if k != "source"}) + qa.check_integrity(data, dead)
    dump_records(out / "divergences.json", diffs)
    errors = [c for c in checks if c.severity == "erro"]
    for check in checks:
        if check.severity != "ok":
            log.warning("%s: %s — %s", check.severity, check.name, check.detail)
    log.info("itens casados: %d/%d · monstros casados: %d/%d · spawns: %d · divergências: %d · em %s",
             len(matches["item"]), len(data["item"]), len(matches["monster"]), len(data["monster"]),
             len(data["spawn"]), len(diffs), out)
    return 1 if any(c.name.startswith("schema") for c in errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
