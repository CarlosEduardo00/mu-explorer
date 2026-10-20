from scrapers.fanz import discover, urls


def test_page_url_e_nome_da_url():
    url = urls.page_url("item", "Dragon Armor")
    assert url == "https://muonlinefanz.com/tools/items/data/itemdb/Dragon%20Armor.php"
    assert urls.name_from_url(url) == "Dragon Armor"


def test_classify():
    assert urls.classify("https://muonlinefanz.com/tools/items/data/itemdb/Dragon%20Armor.php") == "item"
    assert urls.classify("http://www.muonlinefanz.com/tools/mobs/data/mobdb/Goblin.php") == "monster"
    assert urls.classify("https://muonlinefanz.com/tools/maps/data/mapdb/Lorencia.php") == "map"
    assert urls.classify("https://muonlinefanz.com/tools/items/data/php/list.php") is None
    assert urls.classify("https://muonlinefanz.com/tools/items/") is None
    assert urls.classify("https://example.com/tools/items/data/itemdb/X.php") is None


def test_caminhos_bloqueados_cobrem_o_robots_txt():
    assert set(urls.DENY_PATHS) == {
        "/tools/items/data/php/", "/tools/mobs/data/php/", "/tools/npc/data/php/", "/tools/maps/data/php/"}


def test_sitemap_texto_e_xml():
    text = "http://www.muonlinefanz.com/tools/items/data/itemdb/Dragon Armor.php\n\nhttps://muonlinefanz.com/x\n"
    assert discover.urls_from_sitemap(text) == [
        "http://www.muonlinefanz.com/tools/items/data/itemdb/Dragon%20Armor.php", "https://muonlinefanz.com/x"]
    xml = "<urlset><url><loc> https://muonlinefanz.com/a </loc></url></urlset>"
    assert discover.urls_from_sitemap(xml) == ["https://muonlinefanz.com/a"]


def test_links_da_listagem():
    html = """<a href="data/itemdb/Kris.php">Kris</a><a href="/tools/items/?page=2">2</a>
    <a href="data/itemdb/Kris.php">Kris</a><a href="data/php/list.php">x</a>"""
    assert discover.links_from_list_page(html, urls.ITEM_LIST_URL, "item") == [
        "https://muonlinefanz.com/tools/items/data/itemdb/Kris.php"]


def test_amostra():
    items = [str(i) for i in range(100)]
    assert discover.sample(items, 3, "first") == ["0", "1", "2"]
    assert discover.sample(items, 3, "spread") == ["0", "50", "99"]
    assert discover.sample(items, 200) == items
    assert discover.sample([], 5) == []
