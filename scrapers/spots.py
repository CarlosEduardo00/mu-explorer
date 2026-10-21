"""Spots de farm gerados a partir dos spawns com coordenadas (hoje, do MuEmu).

Não copia guias de spots: agrupa os spawns próximos do mesmo mapa (até 10 casas entre centros, spot de no máximo 24 × 24) e descreve cada grupo
(centro, área, monstros, quantidade e faixa de nível). Eventos (Blood Castle...) e monstros dourados ficam de fora.

`heat` classifica o spot como os mapas de "hot spots": boss (tem chefe: está na lista de bosses do mapa ou renasce
em 1 h ou mais), senão hot / mid / low pelo volume de monstros comparado à mediana dos spots do mesmo mapa.

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
LINK = 10               # spawns a até 10 casas (centro a centro) do grupo entram nele
MAX_SPAN = 24           # um spot não passa de 24 × 24 casas
WIDE_AREA = 40          # área de spawn com lado maior que isso vira spot próprio
MIN_MONSTERS = 3        # grupos menores não são "spot de farm"


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


def cluster(spawns: list[dict], link: float = LINK, max_span: int = MAX_SPAN) -> list[list[int]]:
    """Agrupa spawns próximos: cada spawn entra no grupo mais perto cujo centro está a até `link` casas, desde que o
    grupo não passe de `max_span` casas de lado (evita encadear o mapa inteiro). Áreas grandes viram grupo próprio
    (a mesma área repetida, um grupo só). Ordem determinística (pelo centro)."""
    groups: list[dict] = []
    wide: dict[tuple, list[int]] = {}
    for i in sorted(range(len(spawns)), key=lambda k: spawn_center(spawns[k])):
        s = spawns[i]
        box = spawn_box(s)
        if is_wide(s):
            wide.setdefault(box, []).append(i)
            continue
        cx, cy = spawn_center(s)
        w = spawn_count(s)
        best = None
        for g in groups:
            d = ((cx - g["cx"]) ** 2 + (cy - g["cy"]) ** 2) ** 0.5
            nb = (min(g["box"][0], box[0]), min(g["box"][1], box[1]), max(g["box"][2], box[2]), max(g["box"][3], box[3]))
            if d <= link and nb[2] - nb[0] <= max_span and nb[3] - nb[1] <= max_span and (best is None or d < best[0]):
                best = (d, g, nb)
        if best:
            _, g, nb = best
            total = g["w"] + w
            g["cx"], g["cy"] = (g["cx"] * g["w"] + cx * w) / total, (g["cy"] * g["w"] + cy * w) / total
            g["w"], g["box"] = total, nb
            g["idx"].append(i)
        else:
            groups.append({"idx": [i], "cx": cx, "cy": cy, "w": w, "box": box})
    return sorted([sorted(g["idx"]) for g in groups] + [sorted(v) for v in wide.values()], key=lambda g: min(g))


BOSS_RESPAWN = 3600     # renasce em 1 h ou mais: chefe


def classify_heat(spots: list[dict], bosses: set[str]) -> None:
    """Preenche `heat` nos spots de UM mapa: boss (tem chefe); senão pelo volume comparado à mediana do mapa:
    hot >= 1,5 × mediana, low <= 0,75 × mediana, mid no meio (volumes iguais no mapa inteiro = mid)."""
    totals = sorted(s["total"] for s in spots if not any(m["monster_id"] in bosses for m in s["monsters"]))
    median = totals[len(totals) // 2] if totals else 0
    for s in spots:
        if any(m["monster_id"] in bosses for m in s["monsters"]):
            s["heat"] = "boss"
        elif not median:
            s["heat"] = "mid"
        else:
            s["heat"] = "hot" if s["total"] >= 1.5 * median else "low" if s["total"] <= 0.75 * median else "mid"


def build_spots(spawns: list[dict], monsters: list[dict], maps: list[dict]) -> list[dict]:
    level = {m["id"]: m.get("level") for m in monsters}
    boss_ids = {m["id"] for m in monsters if (m.get("respawn_seconds") or 0) >= BOSS_RESPAWN}
    for m in maps:
        boss_ids.update(m.get("bosses") or [])
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
        first = len(spots)
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
        classify_heat(spots[first:], boss_ids)
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
