"""Mapas vetoriais próprios a partir do terreno do servidor (MuEmu, Data/Terrains/*.att).

Cada .att é uma grade 256 × 256 (os últimos 65.536 bytes; índice = y × 256 + x) com flags por casa:
1 = zona segura, 4 = bloqueado (parede, árvore, prédio), 8 = fora do mapa. Daqui saem três camadas:
- land: tudo que é mapa (sem a flag 8);
- walk: chão andável (sem 4 nem 8);
- safe: zona segura (flag 1, dentro do mapa).
Cada camada vira contornos (bordas das casas encadeadas em polígonos) simplificados por Douglas-Peucker e
gravados como `d` de <path> SVG, na orientação do mapa interativo (horizontal = y, vertical = x; casa (x, y)
centrada em (y, x)). Nada é copiado das imagens das fontes: o desenho é nosso, gerado da geometria do jogo.

    python -m scrapers.terrain      # data/raw/muemu/repo/Data/Terrains -> data/processed/terrain/terrains.json

O arquivo de cada mapa foi conferido contra os spawns (a fração de spawns em chão andável tem de superar a
fração de chão do mapa); mapas da S21 que mudaram (ex.: Aida) ficam de fora e usam a imagem do minimapa.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from scrapers.common.model import REPO_ROOT

log = logging.getLogger("scrapers.terrain")

SIZE = 256
FILES = {
    "lorencia": "Lorencia", "dungeon": "Dungeon", "devias": "Devias", "noria": "Noria", "lost-tower": "LostTower",
    "arena": "Stadium", "atlans": "Atlans", "tarkan": "Tarkan", "devil-square": "DevilSquare",
    "devil-square-2": "DevilSquare", "icarus": "Icarus", "kalima": "Kalima", "land-of-trials": "LandofTrial",
    "crywolf": "Crywolf", "kanturu-1": "Kantru1", "kanturu-2": "Kantru2", "kanturu-relics": "Kantru2",
    "elveland": "Elbeland", "swamp-of-darkness": "SwampOfDarkness", "raklion": "Raklion", "vulcanus": "Vulcan",
    "cubera-mine": "KuberaMine1", "acheron": "91_Acheron", "debenter": "95_Debenter", "nars": "110_Nars",
    "ferea": "112_Ferea", "nixies-lake": "113_NixieLake", "uruk-mountain": "100_UrkMontain",
    "karutan": "80_Karutan1", "karutan-2": "81_Karutan2", "loren-market": "79_LorenMarket",
    "valley-of-loren": "ValleyofLoren", "abyss-of-atlans": "World129", "abyss-of-atlans-2": "World130",
    "abyss-of-atlans-3": "World131", "scorched-canyon": "World132",
    **{f"deep-dungeon-{n}": f"DeepDugeon{n}" for n in range(1, 6)},
    **{f"kalima-{n}": "Kalima" for n in range(1, 8)},
}
EPSILON = 0.75   # tolerância do Douglas-Peucker, em casas


def read_grid(path: Path) -> bytes:
    data = path.read_bytes()
    if len(data) < SIZE * SIZE:
        raise ValueError(f"{path.name}: {len(data)} bytes, esperado ao menos {SIZE * SIZE}")
    return data[-SIZE * SIZE:]


def layer_masks(grid: bytes) -> dict[str, list[list[bool]]]:
    """Máscaras na orientação do desenho: linha = x (vertical), coluna = y (horizontal)."""
    def mask(pred):
        return [[pred(grid[y * SIZE + x]) for y in range(SIZE)] for x in range(SIZE)]
    return {
        "land": mask(lambda v: not v & 8),
        "walk": mask(lambda v: not v & 4 and not v & 8),
        "safe": mask(lambda v: bool(v & 1) and not v & 8),
    }


def contours(mask: list[list[bool]]) -> list[list[tuple[int, int]]]:
    """Polígonos (em vértices de casa, (coluna, linha)) das bordas entre casas cheias e vazias.
    Bordas orientadas com a área cheia à direita; em vértices com duas saídas, vira à direita (consistente)."""
    rows, cols = len(mask), len(mask[0])
    filled = lambda r, c: 0 <= r < rows and 0 <= c < cols and mask[r][c]
    out: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for r in range(rows):
        for c in range(cols):
            if not mask[r][c]:
                continue
            if not filled(r - 1, c):
                out.setdefault((c, r), []).append((c + 1, r))
            if not filled(r, c + 1):
                out.setdefault((c + 1, r), []).append((c + 1, r + 1))
            if not filled(r + 1, c):
                out.setdefault((c + 1, r + 1), []).append((c, r + 1))
            if not filled(r, c - 1):
                out.setdefault((c, r + 1), []).append((c, r))
    loops = []
    while out:
        start = next(iter(out))
        loop = [start]
        prev, cur = None, start
        while True:
            nexts = out[cur]
            if len(nexts) == 1 or prev is None:
                nxt = nexts.pop(0)
            else:   # vértice em diagonal: escolhe a saída que vira à direita em relação à direção de chegada
                dx, dy = cur[0] - prev[0], cur[1] - prev[1]
                right = (cur[0] - dy, cur[1] + dx)
                nxt = right if right in nexts else nexts[0]
                nexts.remove(nxt)
            if not nexts:
                del out[cur]
            prev, cur = cur, nxt
            if cur == start:
                break
            loop.append(cur)
        loops.append(loop)
    return loops


def simplify(points: list[tuple[float, float]], eps: float = EPSILON) -> list[tuple[float, float]]:
    """Douglas-Peucker (iterativo) num polígono fechado: divide pelos dois pontos mais distantes entre si."""
    if len(points) < 4:
        return points
    far = max(range(len(points)), key=lambda i: (points[i][0] - points[0][0]) ** 2 + (points[i][1] - points[0][1]) ** 2)
    def dp(seq):
        keep = [False] * len(seq)
        keep[0] = keep[-1] = True
        stack = [(0, len(seq) - 1)]
        while stack:
            a, b = stack.pop()
            (x1, y1), (x2, y2) = seq[a], seq[b]
            dx, dy = x2 - x1, y2 - y1
            norm = (dx * dx + dy * dy) ** 0.5 or 1.0
            best, idx = 0.0, None
            for i in range(a + 1, b):
                d = abs(dy * (seq[i][0] - x1) - dx * (seq[i][1] - y1)) / norm
                if d > best:
                    best, idx = d, i
            if idx is not None and best > eps:
                keep[idx] = True
                stack += [(a, idx), (idx, b)]
        return [p for p, k in zip(seq, keep) if k]
    first = dp(points[: far + 1])
    second = dp(points[far:] + [points[0]])
    return first[:-1] + second[:-1]


def path_data(loops: list[list[tuple[int, int]]], min_area: float = 1.5) -> str:
    """`d` SVG: polígonos simplificados, deslocados meia casa (casa (x, y) centrada em (y, x))."""
    parts = []
    for loop in loops:
        pts = simplify([(float(c), float(r)) for c, r in loop])
        area = abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))) / 2
        if len(pts) < 3 or area < min_area:
            continue
        coords = " ".join(f"{x - 0.5:g},{y - 0.5:g}" for x, y in pts)
        parts.append(f"M{coords}Z")
    return "".join(parts)


def build(terrain_dir: Path) -> tuple[dict, list[str]]:
    out, notes = {}, []
    cache: dict[str, dict] = {}
    for map_id, name in sorted(FILES.items()):
        path = terrain_dir / f"{name}.att"
        if not path.exists():
            notes.append(f"{map_id}: {path.name} ausente")
            continue
        if name not in cache:
            masks = layer_masks(read_grid(path))
            cache[name] = {layer: path_data(contours(m)) for layer, m in masks.items()}
        out[map_id] = {"file": f"Data/Terrains/{name}.att", **cache[name]}
    return out, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scrapers.terrain", description="Mapas vetoriais do terreno")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    terrain_dir = args.data_dir / "raw" / "muemu" / "repo" / "Data" / "Terrains"
    data, notes = build(terrain_dir)
    meta_path = args.data_dir / "raw" / "muemu" / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    target = args.data_dir / "processed" / "terrain" / "terrains.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"source": "muemu", "revision": meta.get("commit"), "maps": data},
                                 ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    for note in notes:
        log.warning(note)
    log.info("%d mapas vetoriais · %s (%.0f KB)", len(data), target, target.stat().st_size / 1024)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
