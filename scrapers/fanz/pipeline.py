"""Orquestração do Fanz: descobrir URLs -> baixar HTML bruto -> parse -> validar -> gravar JSON."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import requests

from scrapers.common.http import BlockedByRobots, PoliteSession
from scrapers.common.model import ParseResult, validate
from scrapers.common.storage import RawStore, dump_records
from scrapers.fanz import discover, urls
from scrapers.fanz.parse_common import SOFT_404
from scrapers.fanz.parse_item import parse_item
from scrapers.fanz.parse_map import parse_map
from scrapers.fanz.parse_monster import parse_monster
from scrapers.fanz.parse_npc import parse_npc

log = logging.getLogger(__name__)

SOURCE = urls.SOURCE_ID
KIND_DIRS = {"item": "items", "monster": "mobs", "map": "maps", "npc": "npcs"}
PARSERS = {"item": parse_item, "monster": parse_monster, "map": parse_map, "npc": parse_npc}


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
                  list_pages: int = 5, kinds: tuple[str, ...] = ("item", "monster")) -> dict[str, list[str]]:
    """Sitemap primeiro. O sitemap do Fanz só lista guias, então na prática cai na listagem:
    página 1 por GET e mais algumas páginas espaçadas por POST (botão de página do site)."""
    grouped: dict[str, list[str]] = {kind: [] for kind in kinds}
    try:
        text = _get_text(session, store, "index", "sitemap", urls.SITEMAP_URL, ".txt", refresh)
        if text:
            found = discover.group_by_kind(discover.urls_from_sitemap(text))
            grouped = {kind: found.get(kind, []) for kind in kinds}
    except (requests.RequestException, BlockedByRobots) as exc:
        log.warning("sitemap indisponível (%s); usando páginas de listagem", exc)
    for kind in kinds:
        list_url = urls.LIST_URLS[kind]
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


def fetch(session: PoliteSession, store: RawStore, *, items: int = 20, mobs: int = 20, maps: int = 0,
          npcs: int = 0, mode: str = "spread", refresh: bool = False, list_pages: int = 5) -> FetchStats:
    wanted = {kind: n for kind, n in (("item", items), ("monster", mobs), ("map", maps), ("npc", npcs)) if n > 0}
    grouped = discover_urls(session, store, refresh, list_pages, tuple(wanted))
    stats = FetchStats(discovered={kind: len(found) for kind, found in grouped.items()})
    for kind, n in wanted.items():
        log.info("%d URLs de %s descobertas; amostra de %d (%s)", len(grouped[kind]), kind, n, mode)
        for url in discover.sample(grouped[kind], n, mode):
            name = urls.name_from_url(url)
            if not refresh and _cached_ok(store, KIND_DIRS[kind], name, url):
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
            if result.ok and not SOFT_404.match(result.text):
                stats.downloaded += 1
                log.info("ok  %s", url)
            else:
                stats.failed.append(f"{url}: HTTP {result.status}" + (" (página vazia/404 do site)" if result.ok else ""))
    return stats


def _cached_ok(store: RawStore, kind_dir: str, name: str, url: str) -> bool:
    """Já baixada com sucesso e com conteúdo (falsos 200 do site são tentados de novo)."""
    page = store.load(SOURCE, kind_dir, name, url)
    return page is not None and 200 <= page.meta.get("status", 0) < 300 and not SOFT_404.match(page.html)


def linked_item_urls(processed: Path) -> list[str]:
    """URLs de itens que os monstros dropam, mas que não estão no conjunto de itens (não aparecem na listagem)."""
    items = {i["id"] for i in json.loads((processed / "items.json").read_text(encoding="utf-8"))}
    drops = json.loads((processed / "drops.json").read_text(encoding="utf-8"))
    names = sorted({d["item_name"] for d in drops if d["item_id"] not in items})
    return [urls.page_url("item", name) for name in names]


def fetch_urls(session: PoliteSession, store: RawStore, kind: str, page_urls: list[str], refresh: bool = False) -> FetchStats:
    """Baixa uma lista explícita de páginas (ex.: itens linkados fora da listagem)."""
    stats = FetchStats(discovered={kind: len(page_urls)})
    for url in page_urls:
        name = urls.name_from_url(url)
        if not refresh and _cached_ok(store, KIND_DIRS[kind], name, url):
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
        if result.ok and not SOFT_404.match(result.text):
            stats.downloaded += 1
            log.info("ok  %s", url)
        else:
            stats.failed.append(f"{url}: HTTP {result.status}" + (" (página vazia/404 do site)" if result.ok else ""))
    return stats


# --- parse e validação ----------------------------------------------------------------------

@dataclass
class Dataset:
    items: list[dict]
    monsters: list[dict]
    maps: list[dict]
    npcs: list[dict]
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
            if SOFT_404.match(page.html):
                failures.append((page.meta["file"], "página vazia ou '404 - Page not found' com HTTP 200"))
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
    page_maps: dict[str, dict] = {}
    npcs: dict[str, dict] = {}
    maps: dict[str, dict] = {}
    spawns: dict[tuple, dict] = {}
    drops: dict[tuple, dict] = {}
    duplicates: list[str] = []
    targets = {"item": items, "monster": monsters, "map": page_maps, "npc": npcs}
    for result in results:
        target = targets[result.kind]
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

    maps = _merge_maps(page_maps, maps)
    _add_map_page_spawns(page_maps, maps, monsters, spawns)

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
        npcs=[npcs[k] for k in sorted(npcs)],
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


def _merge_maps(page_maps: dict[str, dict], cited: dict[str, dict]) -> dict[str, dict]:
    """Mapas com página própria são os registros oficiais. Mapas só citados em páginas de monstro entram
    como variantes: 'Kalima 1' (link para Kalima.php) ganha parent_id = 'kalima'."""
    merged = dict(page_maps)
    by_url = {m["source_url"]: m["id"] for m in page_maps.values()}
    for map_id, record in cited.items():
        if map_id in merged:
            continue
        parent = by_url.get(record["source_url"])
        merged[map_id] = {**record, "parent_id": parent if parent != map_id else None}
    return merged


def _add_map_page_spawns(page_maps: dict[str, dict], maps: dict[str, dict], monsters: dict[str, dict],
                         spawns: dict[tuple, dict]) -> None:
    """Monstros listados na página do mapa viram spawns, se a página do monstro ainda não os ligou ao mapa
    (nem a uma variante dele, como kalima-1 para kalima)."""
    children: dict[str, set[str]] = {}
    for record in maps.values():
        if record.get("parent_id"):
            children.setdefault(record["parent_id"], set()).add(record["id"])
    for record in page_maps.values():
        family = {record["id"]} | children.get(record["id"], set())
        provenance = {k: record[k] for k in ("season", "source", "source_url", "scraped_at")}
        for monster_id in record["monsters"] + record["special_monsters"] + record["bosses"]:
            if monster_id not in monsters or any((monster_id, m) in spawns for m in family):
                continue
            spawns[(monster_id, record["id"])] = {
                "monster_id": monster_id, "map_id": record["id"], "kind": None, "x": None, "y": None,
                "x2": None, "y2": None, "radius": None, "count": None, **provenance}


def _label(entity: str, row: dict) -> str:
    if "id" in row:
        return f"{entity} {row['id']}"
    if entity == "spawn":
        return f"spawn {row.get('monster_id')}->{row.get('map_id')}"
    return f"drop {row.get('monster_id')}->{row.get('item_id')}"


def validate_dataset(dataset: Dataset) -> list[str]:
    errors = []
    for entity, rows in (("item", dataset.items), ("monster", dataset.monsters), ("map", dataset.maps),
                         ("npc", dataset.npcs),
                         ("spawn", dataset.spawns), ("drop", dataset.drops), ("source", dataset.sources)):
        for row in rows:
            errors.extend(f"{_label(entity, row)}: {error}" for error in validate(entity, row))
    return errors


OUTPUT_FILES = {
    "items.json": "items", "monsters.json": "monsters", "maps.json": "maps", "npcs.json": "npcs",
    "spawns.json": "spawns", "drops.json": "drops", "sources.json": "sources",
}


def write_dataset(dataset: Dataset, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, attr in OUTPUT_FILES.items():
        path = out_dir / filename
        dump_records(path, getattr(dataset, attr))
        written.append(path)
    return written


def expected_counts(store: RawStore) -> tuple[dict[str, int], list[str]]:
    """Quantos itens/monstros as listagens do site mostram. Só conta se TODAS as páginas da
    listagem estiverem em disco (numa amostra, a contagem esperada não faz sentido)."""
    counts: dict[str, int] = {}
    notes: list[str] = []
    pages = {page.path.stem: page for page in store.iter(SOURCE, "index")
             if 200 <= page.meta.get("status", 0) < 300}
    for kind, list_url in urls.LIST_URLS.items():
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


def dead_item_ids(store: RawStore) -> set[str]:
    """Itens cuja página o site responde com HTTP 200 mas vazia ou '404 - Page not found'."""
    from scrapers.common.ids import slugify
    return {slugify(page.meta.get("key") or page.path.stem) for page in store.iter(SOURCE, KIND_DIRS["item"])
            if 200 <= page.meta.get("status", 0) < 300 and SOFT_404.match(page.html)}


def broken_listed(store: RawStore) -> dict[str, int]:
    """Por tipo, quantas páginas listadas no site respondem vazias/'404' com HTTP 200."""
    pages = {page.path.stem: page for page in store.iter(SOURCE, "index") if 200 <= page.meta.get("status", 0) < 300}
    out: dict[str, int] = {}
    for kind, list_url in urls.LIST_URLS.items():
        listed = {link for stem, page in pages.items() if stem.startswith(f"{kind}-list-p")
                  for link in discover.links_from_list_page(page.html, list_url, kind)}
        broken = {page.meta["url"] for page in store.iter(SOURCE, KIND_DIRS[kind])
                  if 200 <= page.meta.get("status", 0) < 300 and SOFT_404.match(page.html)}
        if listed & broken:
            out[kind] = len(listed & broken)
    return out
