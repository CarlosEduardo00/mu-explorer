"""Extração genérica de linhas, seções e pares rótulo -> valor (HTML mínimo escrito à mão)."""
from scrapers.common.html import Document, PairIndex, norm_label

BASE = "https://muonlinefanz.com/tools/mobs/data/mobdb/Goblin.php"


def pairs_of(html: str) -> dict[str, str]:
    return {p.label: p.value for p in Document(html, BASE).pairs}


def test_formatos_de_par():
    html = """
    <b>Level:</b> 50<br>
    Max HP: 1,200<br>
    <table><tr><th>DEF</th><td>30</td></tr>
           <tr><td>ATK Rate</td><td>200</td><td>DEF Rate</td><td>15</td></tr></table>
    <dl><dt>Respawn</dt><dd>10 sec</dd></dl>
    <p>Strength:</p><p>120</p>
    <p>Durability 68</p>
    """
    assert pairs_of(html) == {
        "Level": "50", "Max HP": "1,200", "DEF": "30", "ATK Rate": "200", "DEF Rate": "15",
        "Respawn": "10 sec", "Strength": "120", "Durability": "68",
    }


def test_linhas_de_cabecalho_e_de_links_nao_viram_pares():
    html = """<table><tr><th>Excellent Armors</th><th>Excellent Shields</th></tr>
    <tr><td><a href="/tools/items/data/itemdb/Leather Armor.php">Leather Armor</a></td>
        <td><a href="/tools/items/data/itemdb/Small Shield.php">Small Shield</a></td></tr></table>"""
    assert pairs_of(html) == {}


def test_links_guardam_o_cabecalho_da_coluna():
    html = """<table><tr><th>Excellent Armors</th><th></th><th>Excellent Shields</th></tr>
    <tr><td><a href="/a.php">A</a></td><td>-</td><td><a href="/b.php">B</a></td></tr></table>"""
    links = Document(html, BASE).links
    assert [(link.text, link.column) for link in links] == [("A", "Excellent Armors"), ("B", "Excellent Shields")]
    assert links[0].href == "https://muonlinefanz.com/a.php"


def test_secoes_por_titulo():
    html = """<h1>Goblin</h1><p>Level: 3</p>
    <table><tr><th colspan="2">Drops</th></tr><tr><td>x</td><td>y</td></tr></table>
    <h3>Related</h3><p>z</p>"""
    doc = Document(html, BASE)
    assert doc.headings == ["Goblin", "Drops", "Related"]
    assert [p.section for p in doc.pairs] == ["Goblin", "Drops"]
    assert [s.heading for s in doc.sections_matching("drop")] == ["Drops"]


def test_ignora_script_style_e_comentarios():
    html = "<script>var Level = 1;</script><style>p{}</style><!-- HP: 9 --><p>HP: 10</p>"
    assert pairs_of(html) == {"HP": "10"}


def test_imagens_e_links_absolutos_com_espacos_codificados():
    doc = Document('<img src="../graphics/Dragon Armor.jpg" alt="Dragon Armor">', BASE)
    assert doc.images[0].src == "https://muonlinefanz.com/tools/mobs/data/graphics/Dragon%20Armor.jpg"
    assert doc.images[0].alt == "Dragon Armor"


def test_pair_index_consome_e_reporta_nao_mapeados():
    index = PairIndex(Document("<p>Level: 3</p><p>HP: 10</p><p>Moving Speed: 400</p>", BASE).pairs)
    assert index.take(r"level").value == "3"
    assert index.take(r"level") is None  # já consumido
    assert index.take(r"hp|max hp").value == "10"
    assert [p.label for p in index.unmapped()] == ["Moving Speed"]


def test_norm_label():
    assert norm_label("Max. HP:") == "max hp"
    assert norm_label("ATK  DMG") == "atk dmg"
