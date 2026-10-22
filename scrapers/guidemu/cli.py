"""CLI: python -m scrapers.guidemu {fetch,parse}."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from scrapers.common.http import PoliteSession, RobotsUnavailable
from scrapers.common.ids import slugify
from scrapers.common.model import REPO_ROOT
from scrapers.common.storage import RawStore
from scrapers.guidemu.bundle import chunk_files, find_json, main_script

log = logging.getLogger("scrapers.guidemu")

SOURCE = "guidemu"
BASE = "https://guidemuonline.com"
ENTRY = f"{BASE}/maps/lorencia"
# Conteúdo procurado nos chunks: o JSON dos mapas (com spots) e o dos monstros.
MARKERS = {"maps": "cantidadmobs", "monsters": "minattack"}
# Chunks que tinham esses dados em out/2026: tentados primeiro (o id costuma ficar; o hash muda a cada versão).
HINTS = (8413, 4972)


def image_urls(maps: list[dict]) -> list[tuple[str, str]]:
    """(chave, URL) das imagens de spots de cada mapa e de cada zona (andar/área) do mapa."""
    out = []
    for m in maps:
        if m.get("imagenSpotUrl"):
            out.append((slugify(m["name"]), m["imagenSpotUrl"]))
        for z in m.get("zonaSpots") or []:
            if z.get("imagenZonaSpotUrl"):
                out.append((slugify(f"{m['name']} {z['nameZonaSpots']}"), z["imagenZonaSpotUrl"]))
    return out


def cmd_fetch(args: argparse.Namespace) -> int:
    """Página -> main.js -> chunks com os dados (mapas, monstros) -> imagens dos mapas. 1 req/s."""
    session = PoliteSession(min_interval=max(1.0, args.interval))
    store = RawStore(args.data_dir / "raw")
    try:
        page = session.get(ENTRY)
        store.save(SOURCE, "pages", "maps-lorencia", page)
        script = main_script(page.text) if page.ok else None
        if not script:
            log.error("script principal não encontrado em %s (HTTP %s)", ENTRY, page.status)
            return 1
        main = session.get(BASE + script)
        store.save(SOURCE, "js", "main", main, ".js")
        chunks = chunk_files(main.text) if main.ok else {}
        if not chunks:
            log.error("tabela de chunks não encontrada em %s (o formato do site mudou?)", script)
            return 1
        order = [c for c in HINTS if c in chunks] + sorted(c for c in chunks if c not in HINTS)
        missing, data = dict(MARKERS), {}
        for chunk in order:
            if not missing:
                break
            result = session.get(f"{BASE}/{chunks[chunk]}")
            found = [name for name, marker in missing.items() if result.ok and marker in result.text]
            if found:
                store.save(SOURCE, "js", f"chunk-{chunk}", result, ".js")
                for name in found:
                    data[name] = find_json(result.text, MARKERS[name])
                    del missing[name]
                    log.info("%s: chunk %s", name, chunks[chunk])
        if missing:
            log.error("dados não encontrados nos chunks: %s", ", ".join(missing))
            return 1
        done = failed = 0
        for key, url in [] if args.no_images else image_urls(data["maps"] or []):
            if not args.refresh and store.exists(SOURCE, "maps", key, url, ".webp"):
                continue
            img = session.get(url)
            store.save(SOURCE, "maps", key, img, ".webp")
            done, failed = (done + 1, failed) if img.ok else (done, failed + 1)
    except RobotsUnavailable as exc:
        log.error("robots.txt indisponível, coleta abortada: %s", exc)
        return 2
    log.info("imagens de mapas: %d baixadas · %d falhas · requisições: %d", done, failed, session.request_count)
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    from scrapers.guidemu.parse import parse_store
    return parse_store(args.data_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scrapers.guidemu", description="Guide MU Online: mapas, spots e monstros")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="JS com os dados + imagens dos mapas -> data/raw/guidemu (1 req/s)")
    fetch.add_argument("--refresh", action="store_true", help="baixa de novo as imagens que já estão em disco")
    fetch.add_argument("--no-images", action="store_true")
    fetch.add_argument("--interval", type=float, default=1.0)
    sub.add_parser("parse", help="data/raw/guidemu -> data/processed/guidemu (offline)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    return {"fetch": cmd_fetch, "parse": cmd_parse}[args.command](args)
