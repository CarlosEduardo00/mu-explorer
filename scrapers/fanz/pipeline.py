"""Orquestração do Fanz: descobrir URLs -> baixar HTML bruto -> parse -> validar -> gravar JSON."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import requests

from scrapers.common.http import BlockedByRobots, PoliteSession
from scrapers.common.model import ParseResult, validate
from scrapers.common.storage import RawStore
from scrapers.fanz import discover, urls
from scrapers.fanz.parse_item import parse_item
from scrapers.fanz.parse_monster import parse_monster

log = logging.getLogger(__name__)

SOURCE = urls.SOURCE_ID
KIND_DIRS = {"item": "items", "monster": "mobs"}
PARSERS = {"item": parse_item, "monster": parse_monster}


def make_session(**kwargs) -> PoliteSession:
    return PoliteSession(deny_paths=urls.DENY_PATHS, **kwargs)


# --- coleta ----------------------------------------------------------------------------------

@dataclass
class FetchStats:
    discovered: dict[str, int] = field(default_factory=dict)
    downloaded: int = 0
    cached: int = 0
    failed: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)


def _get_text(session: PoliteSession, store: RawStore, kind_dir: str, key: str, url: str,
              ext: str, refresh: bool, form: dict[str, str] | None = None) -> str | None:
    """Baixa (ou reaproveita do disco) uma página de índice e devolve o texto."""
    if not refresh:
        page = store.load(SOURCE, kind_dir, key, url, ext)
        if page and 200 <= page.meta.get("status", 0) < 300:
            return page.html
    result = session.post_form(url, form) if form else session.get(url)
    store.save(SOURCE, kind_dir, key, result, ext)
    if not result.ok:
        log.warning("HTTP %s em %s", result.status, url)
        return None
    return result.text


def discover_urls(session: PoliteSession, store: RawStore, refresh: bool = False,
                  list_pages: int = 5) -> dict[str, list[str]]:
    """Sitemap primeiro. O sitemap do Fanz só lista guias, então na prática cai na listagem:
    página 1 por GET e mais algumas páginas espaçadas por POST (botão de página do site)."""
    grouped: dict[str, list[str]] = {"item": [], "monster": []}
    try:
        text = _get_text(session, store, "index", "sitemap", urls.SITEMAP_URL, ".txt", refresh)
        if text:
            found = discover.group_by_kind(discover.urls_from_sitemap(text))
            grouped = {"item": found["item"], "monster": found["monster"]}
    except (requests.RequestException, BlockedByRobots) as exc:
        log.warning("sitemap indisponível (%s); usando páginas de listagem", exc)
    for kind, list_url in (("item", urls.ITEM_LIST_URL), ("monster", urls.MOB_LIST_URL)):
        if grouped[kind]:
            continue
        log.info("sem URLs de %s no sitemap; usando a listagem %s", kind, list_url)
        html = _get_text(session, store, "index", f"{kind}-list-p1", list_url, ".html", refresh)
        if not html:
            continue
        found = discover.links_from_list_page(html, list_url, kind)
        total = discover.list_page_count(html)
        extra = [n for n in discover.spread_pages(total, list_pages) if n != 1]
        log.info("listagem de %s: %d páginas no site; baixando também as páginas %s", kind, total, extra)
        for number in extra:
            page_html = _get_text(session, store, "index", f"{kind}-list-p{number}", list_url, ".html",
                                  refresh, form={"curpagenum": str(number)})
            if page_html:
                found += discover.links_from_list_page(page_html, list_url, kind)
        grouped[kind] = list(dict.fromkeys(found))
    return grouped


def fetch(session: PoliteSession, store: RawStore, *, items: int = 20, mobs: int = 20,
          mode: str = "spread", refresh: bool = False, list_pages: int = 5) -> FetchStats:
    grouped = discover_urls(session, store, refresh, list_pages)
    stats = FetchStats(discovered={kind: len(found) for kind, found in grouped.items()})
    for kind, n in (("item", items), ("monster", mobs)):
        log.info("%d URLs de %s descobertas; amostra de %d (%s)", len(grouped[kind]), kind, n, mode)
        for url in discover.sample(grouped[kind], n, mode):
            name = urls.name_from_url(url)
            if not refresh and store.exists(SOURCE, KIND_DIRS[kind], name, url):
                stats.cached += 1
                continue
            try:
                result = session.get(url)
            except BlockedByRobots:
                stats.blocked.append(url)
                continue
            except requests.RequestException as exc:
                stats.failed.append(f"{url}: {exc}")
                continue
            store.save(SOURCE, KIND_DIRS[kind], name, result)
            if result.ok:
                stats.downloaded += 1
                log.info("ok  %s", url)
            else:
                stats.failed.append(f"{url}: HTTP {result.status}")
    return stats


# --- parse e validação ----------------------------------------------------------------------

@dataclass
class Dataset:
    items: list[dict]
    monsters: list[dict]
    maps: list[dict]
    spawns: list[dict]
    drops: list[dict]
    sources: list[dict]
    results: list[ParseResult]
    failures: list[tuple[str, str]]
    duplicates: list[str]
    schema_errors: list[str]


def parse_store(store: RawStore) -> Dataset:
    results: list[ParseResult] = []
    failures: list[tuple[str, str]] = []
    for kind, kind_dir in KIND_DIRS.items():
        for page in store.iter(SOURCE, kind_dir):
            status = page.meta.get("status", 0)
            if not 200 <= status < 300:
                failures.append((page.meta["file"], f"HTTP {status}"))
                continue
            try:
                results.append(PARSERS[kind](page.html, page.meta))
            except Exception as exc:  # um HTML estranho não pode derrubar o lote inteiro
                log.exception("falha no parse de %s", page.path)
                failures.append((page.meta["file"], f"{type(exc).__name__}: {exc}"))
    return build_dataset(results, failures)


def build_dataset(results: list[ParseResult], failures: list[tuple[str, str]] | None = None) -> Dataset:
    items: dict[str, dict] = {}
    monsters: dict[str, dict] = {}
    maps: dict[str, dict] = {}
    spawns: dict[tuple, dict] = {}
    drops: dict[tuple, dict] = {}
    duplicates: list[str] = []
    for result in results:
        target = items if result.kind == "item" else monsters
        record_id = result.record["id"]
        if record_id in target:
            duplicates.append(f"{result.kind} {record_id}: {target[record_id]['source_url']} e {result.record['source_url']}")
            continue
        target[record_id] = result.record
        for m in result.related.get("maps", []):
            maps.setdefault(m["id"], m)
        for s in result.related.get("spawns", []):
            spawns.setdefault((s["monster_id"], s["map_id"]), s)
        for d in result.related.get("drops", []):
            drops.setdefault((d["monster_id"], d["item_id"], d["kind"], d["category"]), d)

    scraped = sorted(r.record["scraped_at"] for r in results)
    sources = [{
        "id": SOURCE,
        "name": urls.SOURCE_NAME,
        "url": urls.BASE_URL,
        "credit": urls.SOURCE_CREDIT,
        "pages": len(results),
        "first_scraped_at": scraped[0] if scraped else None,
        "last_scraped_at": scraped[-1] if scraped else None,
    }]
    dataset = Dataset(
        items=[items[k] for k in sorted(items)],
        monsters=[monsters[k] for k in sorted(monsters)],
        maps=[maps[k] for k in sorted(maps)],
        spawns=[spawns[k] for k in sorted(spawns)],
        drops=[drops[k] for k in sorted(drops, key=lambda k: tuple(str(x) for x in k))],
        sources=sources,
        results=results,
        failures=list(failures or []),
        duplicates=duplicates,
        schema_errors=[],
    )
    dataset.schema_errors = validate_dataset(dataset)
    return dataset


def _label(entity: str, row: dict) -> str:
    if "id" in row:
        return f"{entity} {row['id']}"
    if entity == "spawn":
        return f"spawn {row.get('monster_id')}->{row.get('map_id')}"
    return f"drop {row.get('monster_id')}->{row.get('item_id')}"


def validate_dataset(dataset: Dataset) -> list[str]:
    errors = []
    for entity, rows in (("item", dataset.items), ("monster", dataset.monsters), ("map", dataset.maps),
                         ("spawn", dataset.spawns), ("drop", dataset.drops), ("source", dataset.sources)):
        for row in rows:
            errors.extend(f"{_label(entity, row)}: {error}" for error in validate(entity, row))
    return errors


OUTPUT_FILES = {
    "items.json": "items", "monsters.json": "monsters", "maps.json": "maps",
    "spawns.json": "spawns", "drops.json": "drops", "sources.json": "sources",
}


def write_dataset(dataset: Dataset, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, attr in OUTPUT_FILES.items():
        path = out_dir / filename
        path.write_text(json.dumps(getattr(dataset, attr), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def expected_counts(store: RawStore) -> tuple[dict[str, int], list[str]]:
    """Quantos itens/monstros as listagens do site mostram. Só conta se TODAS as páginas da
    listagem estiverem em disco (numa amostra, a contagem esperada não faz sentido)."""
    counts: dict[str, int] = {}
    notes: list[str] = []
    pages = {page.path.stem: page for page in store.iter(SOURCE, "index")
             if 200 <= page.meta.get("status", 0) < 300}
    for kind, list_url in (("item", urls.ITEM_LIST_URL), ("monster", urls.MOB_LIST_URL)):
        first = pages.get(f"{kind}-list-p1")
        if first is None:
            notes.append(f"{kind}: página 1 da listagem não está em disco")
            continue
        total = discover.list_page_count(first.html)
        have = [pages.get(f"{kind}-list-p{n}") for n in range(1, total + 1)]
        if not all(have):
            notes.append(f"{kind}: só {sum(1 for p in have if p)} de {total} páginas da listagem em disco")
            continue
        links = {link for page in have for link in discover.links_from_list_page(page.html, list_url, kind)}
        counts[kind] = len(links)
    return counts, notes
