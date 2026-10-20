"""Fluxo completo (sitemap -> HTML bruto -> parse -> JSON -> relatório) com rede falsa."""
import json

from scrapers.common.storage import RawStore
from scrapers.fanz import pipeline, urls
from scrapers.fanz.report import build_report
from tests.conftest import FakeSession, html_response
from tests.test_fanz_parsers import ITEM_TABLE_LAYOUT, MOB_COLUMN_LAYOUT

FANZ_ROBOTS = "User-agent: *\n" + "".join(f"Disallow: {p}\n" for p in urls.DENY_PATHS)
ITEM = "https://muonlinefanz.com/tools/items/data/itemdb/Dragon%20Armor.php"
ITEM2 = "https://muonlinefanz.com/tools/items/data/itemdb/Kris.php"
MOB = "https://muonlinefanz.com/tools/mobs/data/mobdb/Goblin.php"
SITEMAP = "\n".join([
    "https://muonlinefanz.com/tools/items/data/itemdb/Dragon Armor.php", ITEM2, MOB,
    "https://muonlinefanz.com/tools/items/data/php/list.php",
    "https://muonlinefanz.com/tools/maps/data/mapdb/Lorencia.php",
])


def routes():
    return {
        "http://www.muonlinefanz.com/robots.txt": html_response(FANZ_ROBOTS, content_type="text/plain"),
        "https://muonlinefanz.com/robots.txt": html_response(FANZ_ROBOTS, content_type="text/plain"),
        urls.SITEMAP_URL: html_response(SITEMAP, content_type="text/plain"),
        ITEM: html_response(ITEM_TABLE_LAYOUT),
        ITEM2: html_response("<h2>Kris</h2><div>Attack: 6 ~ 10</div>"),
        MOB: html_response(MOB_COLUMN_LAYOUT),
    }


def test_fetch_parse_e_escrita(tmp_path, clock):
    fake = FakeSession(routes(), clock)
    session = pipeline.make_session(session=fake, clock=clock, sleep=clock.sleep)
    store = RawStore(tmp_path / "raw")

    stats = pipeline.fetch(session, store, items=2, mobs=5)
    assert stats.discovered == {"item": 2, "monster": 1}
    assert (stats.downloaded, stats.failed, stats.blocked) == (3, [], [])
    requested = [url for _, url in fake.calls]
    assert not any("/data/php/" in url for url in requested)
    times = [t for t, _ in fake.calls]
    assert all(b - a >= 1.0 for a, b in zip(times, times[1:]))

    raw = sorted(p.name for p in (tmp_path / "raw" / "fanz" / "items").iterdir())
    assert raw == ["dragon-armor.html", "dragon-armor.meta.json", "kris.html", "kris.meta.json"]
    meta = json.loads((tmp_path / "raw/fanz/items/dragon-armor.meta.json").read_text())
    assert meta["url"] == ITEM and meta["status"] == 200 and len(meta["sha256"]) == 64

    # Segunda execução reaproveita o disco: nenhuma página baixada de novo.
    calls_before = len(fake.calls)
    again = pipeline.fetch(session, store, items=2, mobs=5)
    assert (again.downloaded, again.cached) == (0, 3)
    assert len(fake.calls) == calls_before

    dataset = pipeline.parse_store(store)
    assert dataset.schema_errors == [] and dataset.failures == [] and dataset.duplicates == []
    assert [i["id"] for i in dataset.items] == ["dragon-armor", "kris"]
    assert [m["id"] for m in dataset.monsters] == ["goblin"]
    assert len(dataset.drops) == 5 and len(dataset.spawns) == 2
    assert dataset.sources[0]["pages"] == 3

    out = tmp_path / "processed"
    written = pipeline.write_dataset(dataset, out)
    assert {p.name for p in written} == set(pipeline.OUTPUT_FILES)
    assert json.loads((out / "items.json").read_text())[0]["name"] == "Dragon Armor"

    report = build_report(dataset)
    assert "## Campos não extraídos" in report
    assert "Drops que apontam para itens fora do conjunto coletado: 4"  # kris está na amostra in report


def test_parse_ignora_paginas_com_erro_http(tmp_path, clock):
    r = routes()
    r[ITEM2] = html_response("gone", status=404)
    session = pipeline.make_session(session=FakeSession(r, clock), clock=clock, sleep=clock.sleep)
    store = RawStore(tmp_path / "raw")
    stats = pipeline.fetch(session, store, items=2, mobs=0)
    assert stats.failed == [f"{ITEM2}: HTTP 404"]
    dataset = pipeline.parse_store(store)
    assert [i["id"] for i in dataset.items] == ["dragon-armor"]
    assert dataset.failures == [("kris.html", "HTTP 404")]
