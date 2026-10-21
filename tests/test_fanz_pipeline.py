"""Fluxo completo (sitemap -> listagens -> HTML bruto -> parse -> JSON -> relatório) com rede falsa
servindo o HTML real de tests/fixtures/fanz/."""
import json
from pathlib import Path

from scrapers.common.storage import RawStore
from scrapers.fanz import pipeline, urls
from scrapers.fanz.report import build_report
from tests.conftest import FakeSession, html_response

FIX = Path(__file__).parent / "fixtures" / "fanz"
ROBOTS = (
    "# Rule 1\nUser-agent: *\n" + "".join(f"Disallow: {p}\n" for p in urls.DENY_PATHS)
    + "\nSitemap: http://www.muonlinefanz.com/files/sitemap/sitemap.txt\n"
)


def fixture(*parts: str) -> str:
    return (FIX.joinpath(*parts)).read_text(encoding="utf-8")


ITEM_LIST_P1, MOB_LIST_P1 = fixture("index", "item-list-p1.html"), fixture("index", "monster-list-p1.html")
AGI = "https://muonlinefanz.com/tools/items/data/itemdb/AGI%20Fruit.php"
ABSOLUTE = "https://muonlinefanz.com/tools/items/data/itemdb/Absolute%20Scepter.php"
AEGIS = "https://muonlinefanz.com/tools/mobs/data/mobdb/Aegis.php"
AGON = "https://muonlinefanz.com/tools/mobs/data/mobdb/Agon.php"


def routes():
    robots = html_response(ROBOTS, content_type="text/plain")
    page = lambda p: ("POST", urls.ITEM_LIST_URL, (("curpagenum", str(p)),))  # noqa: E731
    mob_page = lambda p: ("POST", urls.MOB_LIST_URL, (("curpagenum", str(p)),))  # noqa: E731
    r = {
        "https://muonlinefanz.com/robots.txt": robots,
        "https://www.muonlinefanz.com/robots.txt": robots,
        urls.SITEMAP_URL: html_response(fixture("index", "sitemap.txt"), content_type="text/plain"),
        urls.ITEM_LIST_URL: html_response(ITEM_LIST_P1),
        urls.MOB_LIST_URL: html_response(MOB_LIST_P1),
        AGI: html_response(fixture("items", "agi-fruit.html")),
        ABSOLUTE: html_response("gone", status=404),
        AEGIS: html_response(fixture("mobs", "aegis.html")),
        AGON: html_response("gone", status=404),
    }
    for n in (14, 27, 39, 52):
        r[page(n)] = html_response(ITEM_LIST_P1)  # conteúdo repetido: só interessa que o POST aconteça
    for n in (2, 3, 4, 5):
        r[mob_page(n)] = html_response(MOB_LIST_P1)
    return r


def make(tmp_path, clock):
    fake = FakeSession(routes(), clock)
    session = pipeline.make_session(session=fake, clock=clock, sleep=clock.sleep)
    return session, fake, RawStore(tmp_path / "raw")


def test_fetch_usa_listagem_quando_o_sitemap_nao_tem_itens(tmp_path, clock):
    session, fake, store = make(tmp_path, clock)
    stats = pipeline.fetch(session, store, items=2, mobs=2, mode="first")

    assert stats.discovered == {"item": 59, "monster": 59}
    assert stats.downloaded == 2 and stats.blocked == []
    assert stats.failed == [f"{ABSOLUTE}: HTTP 404", f"{AGON}: HTTP 404"]
    # Listagem de itens: página 1 por GET e mais 4 páginas espaçadas (de 52) por POST.
    posted = [(url, data) for url, data in fake.posts]
    assert [d["curpagenum"] for u, d in posted if u == urls.ITEM_LIST_URL] == ["14", "27", "39", "52"]
    assert [d["curpagenum"] for u, d in posted if u == urls.MOB_LIST_URL] == ["2", "3", "4", "5"]
    requested = [url for _, url in fake.calls]
    assert not any("/data/php/" in url for url in requested)
    times = [t for t, _ in fake.calls]
    assert all(b - a >= 1.0 for a, b in zip(times, times[1:]))  # no máximo 1 req/s

    index_files = sorted(p.name for p in (tmp_path / "raw/fanz/index").glob("*.html"))
    assert "item-list-p1.html" in index_files and "item-list-p52.html" in index_files
    meta = json.loads((tmp_path / "raw/fanz/items/agi-fruit.meta.json").read_text())
    assert meta["url"] == AGI and meta["status"] == 200 and len(meta["sha256"]) == 64


def test_segunda_execucao_reaproveita_o_disco(tmp_path, clock):
    session, fake, store = make(tmp_path, clock)
    pipeline.fetch(session, store, items=2, mobs=2, mode="first")
    calls = len(fake.calls)
    again = pipeline.fetch(session, store, items=2, mobs=2, mode="first")
    assert again.downloaded == 0 and again.cached == 2  # as 404 são tentadas de novo
    assert len(fake.calls) == calls + 2


def test_parse_valida_e_escreve(tmp_path, clock):
    session, _, store = make(tmp_path, clock)
    pipeline.fetch(session, store, items=2, mobs=2, mode="first")
    dataset = pipeline.parse_store(store)

    assert dataset.schema_errors == [] and dataset.duplicates == []
    assert dataset.failures == [("absolute-scepter.html", "HTTP 404"), ("agon.html", "HTTP 404")]
    assert [i["id"] for i in dataset.items] == ["agi-fruit"]
    assert [m["id"] for m in dataset.monsters] == ["aegis"]
    assert len(dataset.drops) == 63 and [m["id"] for m in dataset.maps] == ["kalima"]
    assert dataset.sources[0]["pages"] == 2

    written = pipeline.write_dataset(dataset, tmp_path / "processed")
    assert {p.name for p in written} == set(pipeline.OUTPUT_FILES)
    assert json.loads((tmp_path / "processed/items.json").read_text())[0]["name"] == "AGI Fruit"

    report = build_report(dataset)
    assert "## Campos não extraídos" in report and "## Falhas" in report
    assert "`respawn_seconds`" in report  # o Fanz não publica respawn
