"""CLI: python -m scrapers.fanz {fetch,parse,poc,fixtures}."""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

from scrapers.common.http import RobotsUnavailable
from scrapers.common.model import REPO_ROOT
from scrapers.common.storage import RawStore
from scrapers.fanz import pipeline
from scrapers.fanz.report import build_report

log = logging.getLogger("scrapers.fanz")
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "fanz"


def _add_fetch_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--items", type=int, default=20, help="quantos itens baixar (padrão: 20)")
    parser.add_argument("--mobs", type=int, default=20, help="quantos monstros baixar (padrão: 20)")
    parser.add_argument("--sample", choices=("spread", "first"), default="spread",
                        help="spread: espaçados ao longo da lista; first: os primeiros")
    parser.add_argument("--list-pages", type=int, default=5,
                        help="quantas páginas das listagens usar para descobrir URLs (padrão: 5, espaçadas)")
    parser.add_argument("--refresh", action="store_true", help="rebaixa páginas que já estão em disco")
    parser.add_argument("--interval", type=float, default=1.0, help="segundos entre requisições (mín. 1)")


def cmd_fetch(args: argparse.Namespace) -> int:
    session = pipeline.make_session(min_interval=args.interval)
    store = RawStore(args.data_dir / "raw")
    try:
        stats = pipeline.fetch(session, store, items=args.items, mobs=args.mobs,
                               mode=args.sample, refresh=args.refresh, list_pages=args.list_pages)
    except RobotsUnavailable as exc:
        log.error("robots.txt indisponível, coleta abortada: %s", exc)
        return 2
    log.info("descobertas: %s · baixadas: %d · já em disco: %d · bloqueadas: %d · falhas: %d · requisições: %d",
             stats.discovered, stats.downloaded, stats.cached, len(stats.blocked), len(stats.failed),
             session.request_count)
    for line in stats.blocked:
        log.warning("bloqueada por robots.txt: %s", line)
    for line in stats.failed:
        log.warning("falha: %s", line)
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    store = RawStore(args.data_dir / "raw")
    dataset = pipeline.parse_store(store)
    out_dir = args.data_dir / "processed" / pipeline.SOURCE
    pipeline.write_dataset(dataset, out_dir)
    report_path = out_dir / "poc_report.md"
    report_path.write_text(build_report(dataset), encoding="utf-8")
    log.info("itens: %d · monstros: %d · mapas: %d · drops: %d · erros de schema: %d · falhas: %d",
             len(dataset.items), len(dataset.monsters), len(dataset.maps), len(dataset.drops),
             len(dataset.schema_errors), len(dataset.failures))
    log.info("JSON em %s; relatório em %s", out_dir, report_path)
    return 1 if dataset.schema_errors or dataset.failures else 0


def cmd_poc(args: argparse.Namespace) -> int:
    code = cmd_fetch(args)
    return code if code else cmd_parse(args)


def cmd_fixtures(args: argparse.Namespace) -> int:
    """Copia o HTML bruto para tests/fixtures/fanz; com --golden grava também o parse atual como esperado.

    --only slug1,slug2 limita às páginas indicadas (nomes dos arquivos em data/raw, sem extensão).
    As páginas 1 das listagens e o sitemap vão junto, para os testes de descoberta.
    """
    store = RawStore(args.data_dir / "raw")
    only = {slug.strip() for slug in args.only.split(",")} if args.only else None
    copied = 0
    for kind, kind_dir in pipeline.KIND_DIRS.items():
        target = FIXTURES_DIR / kind_dir
        target.mkdir(parents=True, exist_ok=True)
        for page in store.iter(pipeline.SOURCE, kind_dir):
            if not 200 <= page.meta.get("status", 0) < 300 or (only and page.path.stem not in only):
                continue
            shutil.copy2(page.path, target / page.path.name)
            shutil.copy2(store.meta_path(page.path), target / store.meta_path(page.path).name)
            copied += 1
            if args.golden:
                result = pipeline.PARSERS[kind](page.html, page.meta)
                expected = {"record": result.record, "related": result.related}
                (target / f"{page.path.stem}.expected.json").write_text(
                    json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index_target = FIXTURES_DIR / "index"
    index_target.mkdir(parents=True, exist_ok=True)
    for page in store.iter(pipeline.SOURCE, "index"):
        if page.path.stem in ("sitemap", "item-list-p1", "monster-list-p1"):
            shutil.copy2(page.path, index_target / page.path.name)
            shutil.copy2(store.meta_path(page.path), index_target / store.meta_path(page.path).name)
    log.info("%d páginas copiadas para %s%s", copied, FIXTURES_DIR, " (com golden)" if args.golden else "")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scrapers.fanz", description="Scraper do MU Online Fanz")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data", help="raiz de raw/ e processed/")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_fetch_args(sub.add_parser("fetch", help="baixa o HTML bruto (sitemap -> amostra -> data/raw/fanz)"))
    sub.add_parser("parse", help="HTML bruto -> data/processed/fanz/*.json + poc_report.md (offline)")
    _add_fetch_args(sub.add_parser("poc", help="fetch + parse"))
    fixtures = sub.add_parser("fixtures", help="copia o HTML bruto para tests/fixtures/fanz")
    fixtures.add_argument("--golden", action="store_true", help="grava <arquivo>.expected.json com o parse atual")
    fixtures.add_argument("--only", help="slugs separados por vírgula (ex.: dark-knight,aegis); padrão: todas")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(message)s", stream=sys.stderr)
    commands = {"fetch": cmd_fetch, "parse": cmd_parse, "poc": cmd_poc, "fixtures": cmd_fixtures}
    return commands[args.command](args)
