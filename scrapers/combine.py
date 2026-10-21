"""Cruzamento de fontes (fase 3): Fanz como base, MuEmu completando o que o Fanz não publica.

python -m scrapers.combine  ->  data/processed/combined/*.json, item_matches.json, monster_matches.json
                                e combine_report.md (o que foi preenchido, o que não casou, divergências).

Regras:
- Itens: casam pelo nome. Excellent/ancient do Fanz casam com o item base do MuEmu (no MU eles têm o mesmo
  grupo/índice do item base). Do MuEmu vêm group, index, durability e category, só quando o Fanz não tem.
- Monstros: casam pelo nome e, havendo variantes (ex.: Aegis em Kalima 1-7), pelo nível. Do MuEmu vêm o
  número do monstro e o respawn. Os pontos de spawn com coordenadas do MuEmu entram para monstros casados.
- Os valores do Fanz nunca são sobrescritos; diferenças entre as fontes vão para o relatório.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
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
        "drop": fanz["drop"], "source": fanz.get("source", []) + muemu.get("source", []),
    }
    matches = {"item": item_matches, "monster": monster_matches}
    return data, matches, item_diffs + monster_diffs


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
    out = processed / "combined"
    out.mkdir(parents=True, exist_ok=True)
    for entity, filename in OUTPUT.items():
        dump_records(out / filename, data[entity])
    for entity in ("item", "monster"):
        dump_records(out / f"{entity}_matches.json", matches[entity])
    (out / "combine_report.md").write_text(build_report(data, matches, diffs, fanz, muemu), encoding="utf-8")
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
