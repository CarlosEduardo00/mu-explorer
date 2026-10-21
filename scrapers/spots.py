"""Spots de farm gerados a partir dos spawns com coordenadas (hoje, do MuEmu).

Não copia guias de spots: agrupa os spawns do mesmo mapa por região (grade de 32 × 32 casas) e descreve cada grupo
(centro, área, monstros, quantidade e faixa de nível). Eventos (Blood Castle...) e monstros dourados ficam de fora.

    python -m scrapers.spots                 # data/processed/muemu -> data/processed/muemu/farm_spots.json
    python -m scrapers.spots --set combined
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from scrapers.common.model import REPO_ROOT, validate
from scrapers.common.storage import dump_records

log = logging.getLogger("scrapers.spots")

FARM_KINDS = {"normal", "spot"}
CELL = 32               # grade de 32 × 32 casas (o mapa tem 256 × 256): cada célula com monstros vira um spot
WIDE_AREA = 40          # área de spawn com lado maior que isso vira spot próprio
MIN_MONSTERS = 4        # grupos menores não são "spot de farm"


def spawn_center(spawn: dict) -> tuple[float, float] | None:
    """Centro do spawn. Área (x..x2, y..y2) quando x2/y2 formam um retângulo válido; senão o ponto (x, y)."""
    x, y, x2, y2 = spawn.get("x"), spawn.get("y"), spawn.get("x2"), spawn.get("y2")
    if x is None or y is None:
        return None
    if x2 is not None and y2 is not None and x2 >= x and y2 >= y:
        return (x + x2) / 2, (y + y2) / 2
    return float(x), float(y)


def spawn_box(spawn: dict) -> tuple[int, int, int, int]:
    x, y, x2, y2 = spawn["x"], spawn["y"], spawn.get("x2"), spawn.get("y2")
    if x2 is not None and y2 is not None and x2 >= x and y2 >= y:
        return x, y, x2, y2
    return x, y, x, y


def spawn_count(spawn: dict) -> int:
    # Normal = um monstro; Spot = Quant monstros na área.
    return spawn["count"] if spawn.get("kind") == "spot" and spawn.get("count") else 1


def is_wide(spawn: dict) -> bool:
    """Área de spawn grande (ex.: monstro espalhado pelo mapa todo): vira spot próprio, não entra na grade."""
    x0, y0, x1, y1 = spawn_box(spawn)
    return x1 - x0 > WIDE_AREA or y1 - y0 > WIDE_AREA


def cluster(spawns: list[dict], cell: int = CELL) -> list[list[int]]:
    """Agrupa por célula de uma grade cell × cell (pelo centro do spawn); cada área grande vira um grupo."""
    groups: dict[tuple, list[int]] = {}
    for i, s in enumerate(spawns):
        if is_wide(s):
            groups.setdefault(("wide", spawn_box(s)), []).append(i)   # mesma área = mesmo spot
            continue
        cx, cy = spawn_center(s)
        groups.setdefault(("cell", int(cy // cell), int(cx // cell)), []).append(i)
    return sorted(groups.values(), key=lambda g: min(g))


def build_spots(spawns: list[dict], monsters: list[dict], maps: list[dict]) -> list[dict]:
    level = {m["id"]: m.get("level") for m in monsters}
    names = {m["id"]: m["name"] for m in monsters}
    map_names = {m["id"]: m["name"] for m in maps}
    by_map: dict[str, list[dict]] = {}
    for s in spawns:
        if s.get("kind") in FARM_KINDS and spawn_center(s) is not None:
            by_map.setdefault(s["map_id"], []).append(s)
    spots = []
    for map_id in sorted(by_map):
        rows = by_map[map_id]
        groups = cluster(rows)
        numbered = 0
        for group in groups:
            members = [rows[i] for i in group]
            counts: dict[str, int] = {}
            for s in members:
                counts[s["monster_id"]] = counts.get(s["monster_id"], 0) + spawn_count(s)
            total = sum(counts.values())
            if total < MIN_MONSTERS:
                continue
            levels = [level[m] for m in counts if level.get(m) is not None]
            boxes = [spawn_box(s) for s in members]
            weights = [spawn_count(s) for s in members]
            centers = [spawn_center(s) for s in members]
            cx = sum(c[0] * w for c, w in zip(centers, weights)) / sum(weights)
            cy = sum(c[1] * w for c, w in zip(centers, weights)) / sum(weights)
            numbered += 1
            source = members[0]
            spots.append({
                "id": f"{map_id}-{numbered}",
                "map_id": map_id,
                "map_name": map_names.get(map_id, map_id),
                "x": round(cx), "y": round(cy),
                "x_min": min(b[0] for b in boxes), "y_min": min(b[1] for b in boxes),
                "x_max": max(b[2] for b in boxes), "y_max": max(b[3] for b in boxes),
                "monsters": sorted(
                    ({"monster_id": m, "name": names.get(m, m), "level": level.get(m), "count": c} for m, c in counts.items()),
                    key=lambda r: (r["level"] is None, r["level"] or 0, r["name"])),
                "total": total,
                "level_min": min(levels) if levels else None,
                "level_max": max(levels) if levels else None,
                "season": source.get("season"),
                "source": source.get("source"),
                "source_url": source.get("source_url"),
                "scraped_at": source.get("scraped_at"),
            })
    return spots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scrapers.spots", description="Spots de farm a partir dos spawns")
    parser.add_argument("--set", default="muemu", help="conjunto em data/processed (padrão: muemu)")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    folder = args.data_dir / "processed" / args.set
    load = lambda name: json.loads((folder / name).read_text(encoding="utf-8")) if (folder / name).exists() else []
    spots = build_spots(load("spawns.json"), load("monsters.json"), load("maps.json"))
    errors = [f"{s['id']}: {e}" for s in spots for e in validate("farm_spot", s)]
    dump_records(folder / "farm_spots.json", spots)
    for error in errors[:20]:
        log.error(error)
    log.info("%d spots em %d mapas · erros de schema: %d · %s", len(spots), len({s["map_id"] for s in spots}),
             len(errors), folder / "farm_spots.json")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
