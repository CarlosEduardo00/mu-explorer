from pathlib import Path

from scrapers.fanz import discover, urls

FIX = Path(__file__).parent / "fixtures" / "fanz" / "index"


def test_page_url_e_nome_da_url():
    url = urls.page_url("item", "Dragon Armor")
    assert url == "https://muonlinefanz.com/tools/items/data/itemdb/Dragon%20Armor.php"
    assert urls.name_from_url(url) == "Dragon Armor"
    assert urls.name_from_url("https://muonlinefanz.com/tools/items/data/itemdb/Antonia's%20Sword.php") == "Antonia's Sword"


def test_classify_e_canonical():
    assert urls.classify("https://muonlinefanz.com/tools/items/data/itemdb/Dragon%20Armor.php") == "item"
    assert urls.classify("http://www.muonlinefanz.com/tools/mobs/data/mobdb/Goblin.php") == "monster"
    assert urls.classify("https://muonlinefanz.com/tools/maps/data/mapdb/Lorencia.php") == "map"
    assert urls.classify("https://muonlinefanz.com/tools/items/data/php/list.php") is None
    assert urls.classify("https://muonlinefanz.com/tools/items/") is None
    assert urls.classify("https://example.com/tools/items/data/itemdb/X.php") is None
    assert urls.canonical("http://www.muonlinefanz.com/a/B%20c.php?x=1") == "https://muonlinefanz.com/a/B%20c.php?x=1"
    assert urls.canonical("http://example.com/a") == "http://example.com/a"


def test_caminhos_bloqueados_cobrem_o_robots_txt():
    assert set(urls.DENY_PATHS) == {
        "/tools/items/data/php/", "/tools/mobs/data/php/", "/tools/npc/data/php/", "/tools/maps/data/php/"}
    assert urls.SITEMAP_URL.startswith("https://")  # o proxy do ambiente só aceita HTTPS


def test_sitemap_real_so_tem_guias():
    found = discover.urls_from_sitemap((FIX / "sitemap.txt").read_text())
    assert len(found) > 50
    grouped = discover.group_by_kind(found)
    assert grouped == {"item": [], "monster": [], "map": [], "npc": []}  # listas de itens/mobs são só por listagem


def test_sitemap_xml():
    xml = "<urlset><url><loc> https://muonlinefanz.com/a </loc></url></urlset>"
    assert discover.urls_from_sitemap(xml) == ["https://muonlinefanz.com/a"]


def test_listagem_real_de_itens():
    html = (FIX / "item-list-p1.html").read_text(encoding="utf-8")
    links = discover.links_from_list_page(html, urls.ITEM_LIST_URL, "item")
    assert len(links) == 59
    assert links[0] == "https://muonlinefanz.com/tools/items/data/itemdb/AGI%20Fruit.php"
    assert discover.list_page_count(html) == 52
    assert discover.links_from_list_page(html, urls.ITEM_LIST_URL, "monster") == []


def test_listagem_real_de_monstros():
    html = (FIX / "monster-list-p1.html").read_text(encoding="utf-8")
    links = discover.links_from_list_page(html, urls.MOB_LIST_URL, "monster")
    assert len(links) == 59 and links[0].endswith("/tools/mobs/data/mobdb/Aegis.php")
    assert discover.list_page_count(html) == 5


def test_paginas_espacadas():
    assert discover.spread_pages(52, 5) == [1, 14, 27, 39, 52]
    assert discover.spread_pages(5, 10) == [1, 2, 3, 4, 5]
    assert discover.spread_pages(1, 5) == [1] and discover.spread_pages(0, 5) == []
    assert discover.list_page_count("<p>sem paginação</p>") == 1


def test_amostra():
    items = [str(i) for i in range(100)]
    assert discover.sample(items, 3, "first") == ["0", "1", "2"]
    assert discover.sample(items, 3, "spread") == ["0", "50", "99"]
    assert discover.sample(items, 200) == items
    assert discover.sample([], 5) == []
