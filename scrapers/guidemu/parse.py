"""data/raw/guidemu -> data/processed/guidemu (offline).

Saídas:
- monsters.json: monstros (schema `monster`) com nível, HP, dano, defesa e imagem.
- spots.json: um registro por spot: mapa e zona do guia, número, tipo (low/medium/high -> heat low/mid/hot),
  coordenada (x, y) do jogo, quantidade de monstros e os monstros (ids). Interno: vira farm_spots no `scrapers.spots`.
- groups.json: a organização do guia (mapa -> zonas: andares, áreas), na ordem do site (por nível).
- map_images.json: imagem de spots de cada mapa/zona e a transformação coordenada do jogo -> posição na imagem
  (em %), ajustada aos spots (as imagens seguem a orientação do minimapa do jogo, girada 45°). Base do terreno dos
  mapas que o MuEmu não tem (`scrapers.terrain`).
"""
from __future__ import annotations

import logging
from pathlib import Path

from scrapers.common.ids import slugify
from scrapers.common.model import validate
from scrapers.common.storage import RawStore, dump_records
from scrapers.guidemu.bundle import find_json

log = logging.getLogger("scrapers.guidemu")

SOURCE = "guidemu"
BASE = "https://guidemuonline.com"
HEAT = {"low": "low", "medium": "mid", "high": "hot"}
FIT_MAX_ERROR = 2.5   # % da imagem: acima disso a transformação não serve para o terreno


def _int(v) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _pct(v) -> float | None:
    try:
        return float(str(v).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None


def monster_record(m: dict, meta: dict) -> dict:
    return {
        "id": slugify(m["name"]), "name": m["name"].strip(), "number": None, "level": _int(m.get("level")),
        "difficulty": None, "hp": _int(m.get("hp")), "atk_min": _int(m.get("minattack")), "atk_max": _int(m.get("maxattack")),
        "atk_rate": None, "def": _int(m.get("defense")), "def_rate": _int(m.get("defensesuccessrate")),
        "elemental_def": _int(m.get("elementaldef")) or None,
        "elemental_dmg_min": _int(m.get("elementaldmg")) or None, "elemental_dmg_max": _int(m.get("elementaldmg")) or None,
        "respawn_seconds": None, "respawn_raw": None, "drops_normal_items": None, "notes": [],
        "image_url": m.get("imagenMonsterFirebase") or None, "season": None, "source": SOURCE,
        "source_url": f"{BASE}/maps", "scraped_at": meta.get("fetched_at"), "page_updated_at": None,
    }


def fit_transform(points: list[tuple[int, int, float, float]]) -> tuple[list[list[float]], float, int] | None:
    """Transformação (x, y) do jogo -> (left %, top %) da imagem: rotação + escala + espelho + translação
    (left + i·top = α·(x − i·y) + β), por mínimos quadrados; descarta spots fora da curva (erro > FIT_MAX_ERROR)
    enquanto sobrarem 3. Devolve ([[a, b, c], [d, e, f]], erro médio em %, pontos usados) ou None."""
    import numpy as np
    pts = list(points)
    while len(pts) >= 2:
        w = np.array([complex(x, -y) for x, y, _, _ in pts])
        z = np.array([complex(left, top) for _, _, left, top in pts])
        A = np.stack([w, np.ones_like(w)], 1)
        (alpha, beta), *_ = np.linalg.lstsq(A, z, rcond=None)
        err = np.abs(A @ np.array([alpha, beta]) - z)
        worst = int(err.argmax())
        if err[worst] > FIT_MAX_ERROR and len(pts) > 3:
            pts.pop(worst)
            continue
        p, q = alpha.real, alpha.imag
        # left = p·x + q·y + Re β ; top = q·x − p·y + Im β
        matrix = [[float(p), float(q), float(beta.real)], [float(q), float(-p), float(beta.imag)]]
        return matrix, float(err.mean()), len(pts)
    return None


def parse_maps(maps: list[dict], monsters: list[dict], meta: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """(groups, spots, map_images) a partir do JSON de mapas do site."""
    names = {m["id"]: m["name"].strip() for m in monsters}
    groups, spots, images = [], [], []
    prov = {"source": SOURCE, "scraped_at": meta.get("fetched_at")}
    for m in maps:
        name = m["name"].strip()
        url = BASE + (m.get("url") or f"/maps/{slugify(name)}")
        areas = [(None, m.get("spots") or [], m.get("imagenSpotUrl"))]
        areas += [(z["nameZonaSpots"].strip(), z.get("spotsZona") or [], z.get("imagenZonaSpotUrl")) for z in m.get("zonaSpots") or []]
        zones = [zone for zone, _, _ in areas if zone]
        groups.append({"name": name, "id": slugify(name), "source_url": url, "level": (m.get("lvlmapa") or "").strip() or None,
                       "description": (m.get("descripcion") or "").strip() or None, "zones": zones,
                       "monsters": [names[i] for i in m.get("monsters") or [] if i in names]})
        for zone, rows, image in areas:
            fit_points = []
            for row in rows:
                x, y, count = _int(row.get("coordenadaX")), _int(row.get("coordenadaY")), _int(row.get("cantidadmobs"))
                if x is None or y is None or not (0 <= x < 256 and 0 <= y < 256):
                    continue
                mons = [names[i] for i in row.get("monsters") or [] if i in names]
                spots.append({"map": name, "zone": zone, "n": row.get("id"), "heat": HEAT.get(row.get("tipo"), "mid"),
                              "x": x, "y": y, "count": count, "monsters": mons, "monster_ids": [slugify(n) for n in mons],
                              "element": row.get("element") or None, "source_url": url, **prov})
                left, top = _pct(row.get("left")), _pct(row.get("top"))
                if left is not None and top is not None:
                    fit_points.append((x, y, left, top))
            if image:
                fit = fit_transform(fit_points)
                images.append({"map": name, "zone": zone, "key": slugify(f"{name} {zone}" if zone else name), "image_url": image,
                               "transform": fit[0] if fit else None, "error": round(fit[1], 2) if fit else None,
                               "points": fit[2] if fit else 0})
    return groups, spots, images


ALPHA = 40   # opacidade mínima de um pixel de mapa (o fundo das imagens é transparente)


def image_frame(image, transform: list[list[float]]) -> list[list[float]] | None:
    """Cantos (x, y) do jogo do retângulo da imagem que tem desenho: a área que o guia mostra para a zona."""
    import numpy as np
    alpha = np.asarray(image.convert("RGBA"))[..., 3] > ALPHA
    if not alpha.any():
        return None
    rows, cols = np.nonzero(alpha)
    h, w = alpha.shape
    (a, b, c), (d, e, f) = transform
    det = a * e - b * d
    if abs(det) < 1e-9:
        return None
    corners = []
    for px, py in [(cols.min(), rows.min()), (cols.max(), rows.min()), (cols.max(), rows.max()), (cols.min(), rows.max())]:
        left, top = px / w * 100 - c, py / h * 100 - f
        corners.append([round((e * left - b * top) / det, 1), round((a * top - d * left) / det, 1)])
    return corners


def load_bundle(store: RawStore) -> tuple[list, list, dict]:
    maps = monsters = None
    meta: dict = {}
    for page in store.iter(SOURCE, "js"):
        if page.path.stem == "main":
            continue
        text = page.content.decode("utf-8", errors="replace")
        if maps is None and "cantidadmobs" in text:
            maps, meta = find_json(text, "cantidadmobs"), page.meta
        if monsters is None and "minattack" in text:
            monsters = find_json(text, "minattack")
    return maps or [], monsters or [], meta


def parse_store(data_dir: Path) -> int:
    store = RawStore(data_dir / "raw")
    maps, monsters, meta = load_bundle(store)
    if not maps or not monsters:
        log.error("dados do guia não encontrados em data/raw/guidemu/js (rode: python -m scrapers.guidemu fetch)")
        return 1
    records = list({r["id"]: r for r in (monster_record(m, meta) for m in monsters if m.get("name"))}.values())
    groups, spots, images = parse_maps(maps, monsters, meta)
    from PIL import Image
    for entry in images:
        raw = data_dir / "raw" / SOURCE / "maps" / f"{entry['key']}.webp"
        good = entry["transform"] and entry["error"] is not None and entry["error"] <= FIT_MAX_ERROR
        entry["frame"] = image_frame(Image.open(raw), entry["transform"]) if good and raw.exists() else None
    errors = [f"monster {r['id']}: {e}" for r in records for e in validate("monster", r)]
    out = data_dir / "processed" / SOURCE
    out.mkdir(parents=True, exist_ok=True)
    dump_records(out / "monsters.json", records)
    dump_records(out / "spots.json", spots)
    dump_records(out / "groups.json", groups)
    dump_records(out / "map_images.json", images)
    dump_records(out / "sources.json", [{
        "id": SOURCE, "name": "Guide MU Online", "url": BASE,
        "credit": "Mapas, spots e monstros do Guide MU Online (guidemuonline.com), guia do MU Online oficial. Publicados com autorização.",
        "pages": len(groups), "first_scraped_at": meta.get("fetched_at"), "last_scraped_at": meta.get("fetched_at")}])
    for err in errors[:20]:
        log.error(err)
    bad = [f"{i['map']}/{i['zone']}" for i in images if i["transform"] is None or i["error"] > FIT_MAX_ERROR]
    log.info("mapas: %d · zonas: %d · spots: %d · monstros: %d · imagens: %d (sem transformação: %s) · erros de schema: %d",
             len(groups), sum(len(g["zones"]) for g in groups), len(spots), len(records), len(images), ", ".join(bad) or "nenhuma", len(errors))
    return 1 if errors else 0
