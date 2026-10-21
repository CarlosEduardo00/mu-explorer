import pytest
import requests
from requests.structures import CaseInsensitiveDict

from scrapers.common.http import (
    USER_AGENT, BlockedByRobots, PoliteSession, RobotsUnavailable, charset_from, host_key, normalize_url,
)
from tests.conftest import FakeResponse, FakeSession, html_response

BASE = "https://example.com"
ROBOTS_URL = f"{BASE}/robots.txt"
ROBOTS = "User-agent: *\nDisallow: /tools/items/data/php/\n"


def robots(text: str = ROBOTS) -> FakeResponse:
    return html_response(text, content_type="text/plain")


def make(routes: dict, clock, **kwargs):
    fake = FakeSession(routes, clock)
    session = PoliteSession(session=fake, clock=clock, sleep=clock.sleep, **kwargs)
    return session, fake


def redirect(location: str, status: int = 302) -> FakeResponse:
    return FakeResponse(status, b"", CaseInsensitiveDict({"Location": location}))


def test_user_agent_identificado(clock):
    _, fake = make({}, clock)
    assert fake.headers["User-Agent"] == USER_AGENT
    assert USER_AGENT.startswith("mu-explorer-bot/")


def test_no_maximo_uma_requisicao_por_segundo(clock):
    routes = {ROBOTS_URL: robots(), f"{BASE}/a": html_response("a"), f"{BASE}/b": html_response("b")}
    session, fake = make(routes, clock)
    session.get(f"{BASE}/a")
    session.get(f"{BASE}/b")
    assert [url for _, url in fake.calls] == [ROBOTS_URL, f"{BASE}/a", f"{BASE}/b"]
    times = [t for t, _ in fake.calls]
    assert all(later - earlier >= 1.0 for earlier, later in zip(times, times[1:]))


def test_www_e_dominio_sem_www_dividem_o_limite(clock):
    routes = {
        ROBOTS_URL: robots(), "https://www.example.com/robots.txt": robots(),
        f"{BASE}/a": html_response("a"), "https://www.example.com/b": html_response("b"),
    }
    session, fake = make(routes, clock)
    session.get(f"{BASE}/a")
    session.get("https://www.example.com/b")
    times = [t for t, _ in fake.calls]
    assert all(later - earlier >= 1.0 for earlier, later in zip(times, times[1:]))
    assert host_key("https://www.example.com/x") == host_key("https://example.com/y")


def test_intervalo_abaixo_de_um_segundo_e_recusado():
    with pytest.raises(ValueError):
        PoliteSession(min_interval=0.5)


def test_respeita_crawl_delay(clock):
    routes = {ROBOTS_URL: robots("User-agent: *\nCrawl-delay: 3\n"),
              f"{BASE}/a": html_response("a"), f"{BASE}/b": html_response("b")}
    session, fake = make(routes, clock)
    session.get(f"{BASE}/a")
    session.get(f"{BASE}/b")
    assert fake.calls[2][0] - fake.calls[1][0] >= 3.0


def test_robots_bloqueia_sem_fazer_a_requisicao(clock):
    session, fake = make({ROBOTS_URL: robots()}, clock)
    blocked = f"{BASE}/tools/items/data/php/list.php"
    with pytest.raises(BlockedByRobots):
        session.get(blocked)
    assert blocked not in [url for _, url in fake.calls]


def test_lista_de_bloqueio_vale_mesmo_se_robots_liberar(clock):
    session, fake = make({ROBOTS_URL: robots("User-agent: *\nDisallow:\n")}, clock,
                         deny_paths=("/tools/mobs/data/php/",))
    for url in (f"{BASE}/tools/mobs/data/php/list.php", f"{BASE}/tools/mobs/data/%70hp/list.php",
                f"{BASE}/Tools/Mobs/Data/PHP/list.php"):
        with pytest.raises(BlockedByRobots):
            session.get(url)
    assert fake.calls == []  # bloqueado antes de qualquer requisição


def test_nao_segue_redirecionamento_para_caminho_bloqueado(clock):
    target = f"{BASE}/tools/items/data/php/x.php"
    session, fake = make({ROBOTS_URL: robots(), f"{BASE}/a": redirect(target)}, clock)
    with pytest.raises(BlockedByRobots):
        session.get(f"{BASE}/a")
    assert target not in [url for _, url in fake.calls]


def test_segue_redirecionamento_permitido(clock):
    session, _ = make({ROBOTS_URL: robots(), f"{BASE}/a": redirect("/b", 301), f"{BASE}/b": html_response("ok")}, clock)
    result = session.get(f"{BASE}/a")
    assert (result.url, result.final_url, result.status, result.text) == (f"{BASE}/a", f"{BASE}/b", 200, "ok")


def test_robots_inexistente_libera_tudo(clock):
    session, _ = make({f"{BASE}/a": html_response("a")}, clock)  # robots.txt -> 404
    assert session.get(f"{BASE}/a").status == 200


@pytest.mark.parametrize("failure", [FakeResponse(503), requests.ConnectionError("sem rede")])
def test_robots_ilegivel_aborta_a_coleta(clock, failure):
    session, fake = make({ROBOTS_URL: [failure]}, clock)
    with pytest.raises(RobotsUnavailable):
        session.get(f"{BASE}/a")
    assert f"{BASE}/a" not in [url for _, url in fake.calls]


def test_retry_com_backoff_em_503(clock):
    routes = {ROBOTS_URL: robots(), f"{BASE}/a": [FakeResponse(503), FakeResponse(503), html_response("ok")]}
    session, fake = make(routes, clock)
    assert session.get(f"{BASE}/a").status == 200
    assert [url for _, url in fake.calls].count(f"{BASE}/a") == 3
    assert 2.0 in clock.sleeps and 4.0 in clock.sleeps


def test_respeita_retry_after(clock):
    limited = FakeResponse(429, b"", CaseInsensitiveDict({"Retry-After": "7"}))
    session, _ = make({ROBOTS_URL: robots(), f"{BASE}/a": [limited, html_response("ok")]}, clock)
    assert session.get(f"{BASE}/a").status == 200
    assert 7.0 in clock.sleeps


def test_desiste_apos_max_tentativas(clock):
    session, fake = make({ROBOTS_URL: robots(), f"{BASE}/a": [FakeResponse(503)]}, clock)
    assert session.get(f"{BASE}/a").status == 503
    assert [url for _, url in fake.calls].count(f"{BASE}/a") == 3


def test_espacos_na_url_sao_codificados(clock):
    url = f"{BASE}/tools/items/data/itemdb/Dragon%20Armor.php"
    session, fake = make({ROBOTS_URL: robots(), url: html_response("x")}, clock)
    session.get(f"{BASE}/tools/items/data/itemdb/Dragon Armor.php")
    assert fake.calls[-1][1] == url
    assert normalize_url(url) == url  # não recodifica %20


def test_charset_from():
    assert charset_from("text/html; charset=ISO-8859-1") == "iso-8859-1"
    assert charset_from("text/html") is None
    assert charset_from(None) is None


def test_post_form_passa_pelas_mesmas_regras(clock):
    key = ("POST", f"{BASE}/lista", (("curpagenum", "3"),))
    session, fake = make({ROBOTS_URL: robots(), key: html_response("pagina 3")}, clock)
    session.get(f"{BASE}/lista")  # 404 (rota GET inexistente), só para consumir o primeiro intervalo
    result = session.post_form(f"{BASE}/lista", {"curpagenum": "3"})
    assert (result.status, result.text) == (200, "pagina 3")
    assert fake.posts == [(f"{BASE}/lista", {"curpagenum": "3"})]
    times = [t for t, _ in fake.calls]
    assert all(later - earlier >= 1.0 for earlier, later in zip(times, times[1:]))


def test_post_form_respeita_bloqueios(clock):
    session, fake = make({ROBOTS_URL: robots()}, clock)
    with pytest.raises(BlockedByRobots):
        session.post_form(f"{BASE}/tools/items/data/php/list.php", {"a": "1"})
    assert getattr(fake, "posts", []) == []
