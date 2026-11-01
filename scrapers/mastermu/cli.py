"""CLI: python -m scrapers.mastermu {fetch,parse}.

MasterMU (mastermu.net) é um servidor privado (Season 21, x100). Sem autorização para publicar o conteúdo: o site usa
só fatos (em que mapas cada item de skill dropa, o que vem da Ruud Store) e guias reescritos por nós. O robots.txt
libera tudo menos /admin, /api, /install, /panel e /cron; o sitemap lista os guias (/guides/view/<slug>).
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

from scrapers.common.http import PoliteSession, RobotsUnavailable
from scrapers.common.model import REPO_ROOT
from scrapers.common.storage import RawStore

log = logging.getLogger("scrapers.mastermu")

SOURCE = "mastermu"
BASE = "https://mastermu.net"
SITEMAP = f"{BASE}/sitemap.xml"


def guide_urls(sitemap_xml: str) -> list[str]:
    """Guias listados no sitemap (/guides/view/<slug>), sem repetir."""
    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sitemap_xml)
    return sorted(dict.fromkeys(u for u in urls if u.startswith(f"{BASE}/guides/view/")))


def guide_key(url: str) -> str:
    return url.removeprefix(f"{BASE}/guides/view/").strip("/")


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


def cmd_parse(args: argparse.Namespace) -> int:
    from scrapers.mastermu.parse import parse_store
    return parse_store(args.data_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scrapers.mastermu", description="Scraper do MasterMU (só fatos)")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="sitemap -> guias em data/raw/mastermu/guides (1 req/s)")
    fetch.add_argument("--refresh", action="store_true")
    fetch.add_argument("--interval", type=float, default=1.0)
    fetch.add_argument("--only", help="slugs separados por vírgula")
    sub.add_parser("parse", help="data/raw/mastermu -> data/processed/mastermu/*.json (offline)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    return {"fetch": cmd_fetch, "parse": cmd_parse}[args.command](args)
