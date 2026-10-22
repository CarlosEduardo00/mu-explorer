"""CLI: python -m scrapers.gmo {fetch,fetch-drops,parse}."""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

from scrapers.common.http import PoliteSession, RobotsUnavailable
from scrapers.common.model import REPO_ROOT
from scrapers.common.storage import RawStore

log = logging.getLogger("scrapers.gmo")

SOURCE = "gmo"
BASE = "https://globalmuonline.com"
SITEMAP = f"{BASE}/sitemap.xml"
# Guias de conjuntos de itens (centenas de páginas) ficam de fora: não servem para mapas, monstros ou classes.
SKIP_GUIDES = ("ancient-items/", "mastery-items/", "legendary-items/")


def guide_urls(sitemap_xml: str) -> list[str]:
    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sitemap_xml)
    out = []
    for url in urls:
        path = url.removeprefix(BASE + "/")
        if path.startswith("guides/") and path != "guides/" and not path.removeprefix("guides/").startswith(SKIP_GUIDES):
            out.append(url)
    return sorted(dict.fromkeys(out))


def guide_key(url: str) -> str:
    return url.removeprefix(BASE + "/guides/").strip("/").replace("/", "--") or "index"


def cmd_fetch(args: argparse.Namespace) -> int:
    session = PoliteSession(min_interval=max(1.0, args.interval))
    store = RawStore(args.data_dir / "raw")
    try:
        result = session.get(SITEMAP)
    except RobotsUnavailable as exc:
        log.error("robots.txt indisponível, coleta abortada: %s", exc)
        return 2
    store.save(SOURCE, "index", "sitemap", result, ".xml")
    if not result.ok:
        log.error("sitemap respondeu HTTP %s", result.status)
        return 1
    urls = guide_urls(result.text)
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        urls = [u for u in urls if guide_key(u) in wanted]
    log.info("%d guias no sitemap", len(urls))
    done = cached = failed = 0
    for url in urls:
        key = guide_key(url)
        if not args.refresh and store.exists(SOURCE, "guides", key, url):
            cached += 1
            continue
        page = session.get(url)
        store.save(SOURCE, "guides", key, page)
        if page.ok:
            done += 1
        else:
            failed += 1
            log.warning("HTTP %s em %s", page.status, url)
    log.info("baixadas: %d · já em disco: %d · falhas: %d · requisições: %d", done, cached, failed, session.request_count)
    return 0


DROP_INDEX = f"{BASE}/drop/location"


def drop_location_urls(index_html: str) -> list[str]:
    """Páginas de drop por mapa listadas em /drop/location (cada uma traz monstro -> itens)."""
    urls = re.findall(r'href="(https://globalmuonline\.com/drop/location/[^"#?]+)"', index_html)
    return sorted(dict.fromkeys(urls))


def drop_key(url: str) -> str:
    return url.removeprefix(DROP_INDEX + "/").strip("/").replace("+", "-").replace("/", "--") or "index"


def cmd_fetch_drops(args: argparse.Namespace) -> int:
    """Listas de drop por mapa (/drop/location/<Mapa>): ~110 páginas, 1 req/s."""
    session = PoliteSession(min_interval=max(1.0, args.interval))
    store = RawStore(args.data_dir / "raw")
    try:
        index = session.get(DROP_INDEX)
    except RobotsUnavailable as exc:
        log.error("robots.txt indisponível, coleta abortada: %s", exc)
        return 2
    store.save(SOURCE, "drops", "index", index)
    if not index.ok:
        log.error("%s respondeu HTTP %s", DROP_INDEX, index.status)
        return 1
    urls = drop_location_urls(index.text)
    log.info("%d mapas com lista de drop", len(urls))
    done = cached = failed = 0
    for url in urls:
        key = drop_key(url)
        if not args.refresh and store.exists(SOURCE, "drops", key, url):
            cached += 1
            continue
        page = session.get(url)
        store.save(SOURCE, "drops", key, page)
        if page.ok:
            done += 1
        else:
            failed += 1
            log.warning("HTTP %s em %s", page.status, url)
    log.info("baixadas: %d · já em disco: %d · falhas: %d · requisições: %d", done, cached, failed, session.request_count)
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    from scrapers.gmo.parse import parse_store
    return parse_store(args.data_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scrapers.gmo", description="Scraper do Global MU Online")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="sitemap -> guias (mapas, classes...) em data/raw/gmo/guides (1 req/s)")
    fetch.add_argument("--refresh", action="store_true")
    fetch.add_argument("--interval", type=float, default=1.0)
    fetch.add_argument("--only", help="chaves separadas por vírgula (ex.: atlans,slayer)")
    drops = sub.add_parser("fetch-drops", help="/drop/location -> listas de drop por mapa em data/raw/gmo/drops (1 req/s)")
    drops.add_argument("--refresh", action="store_true")
    drops.add_argument("--interval", type=float, default=1.0)
    sub.add_parser("parse", help="data/raw/gmo -> data/processed/gmo/*.json (offline)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    return {"fetch": cmd_fetch, "fetch-drops": cmd_fetch_drops, "parse": cmd_parse}[args.command](args)
