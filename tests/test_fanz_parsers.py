"""Testes dos parsers do Fanz com HTML HIPOTÉTICO, escrito à mão.

Não é HTML real do muonlinefanz.com: o ambiente onde o parser foi escrito não tinha acesso
ao site. Estes testes garantem que a extração por rótulo/seção funciona em layouts comuns
(tabela rótulo/valor, "Rótulo: valor", drops por coluna ou por linha). A validação contra
páginas reais fica em test_fanz_fixtures.py, que roda sobre tests/fixtures/fanz/.
"""
from scrapers.common.model import validate
from scrapers.fanz.parse_item import parse_item
from scrapers.fanz.parse_monster import parse_monster
from tests.conftest import meta_for

ITEM_URL = "https://muonlinefanz.com/tools/items/data/itemdb/Dragon%20Armor.php"
MOB_URL = "https://muonlinefanz.com/tools/mobs/data/mobdb/Goblin.php"
ITEMDB = "/tools/items/data/itemdb"

ITEM_TABLE_LAYOUT = f"""<html><head><title>Dragon Armor - MU Online Fanz</title></head><body>
<div id="menu"><a href="/tools/items/">Items</a> <a href="/tools/mobs/">Mobs</a></div>
<h1>Dragon Armor</h1>
<img src="/tools/items/data/graphics/Dragon Armor.jpg" alt="Dragon Armor">
<table>
  <tr><th>Item Details</th></tr>
  <tr><td>DEF</td><td>50</td></tr>
  <tr><td>Durability</td><td>68</td></tr>
  <tr><td>Item Grade</td><td>Normal</td></tr>
  <tr><th>Requirements</th></tr>
  <tr><td>Level</td><td>45</td></tr>
  <tr><td>Strength</td><td>120</td></tr>
  <tr><td>Agility</td><td>30</td></tr>
  <tr><td>Can be equipped by</td><td>Dark Knight, Blade Knight, Magic Gladiator</td></tr>
  <tr><th>Possible Additional Options</th></tr>
  <tr><td colspan="2">Jewel of Life</td></tr>
  <tr><td colspan="2">Jewel of Harmony</td></tr>
  <tr><td colspan="2">Luck</td></tr>
</table>
<h3>Related Items</h3>
<ul><li><a href="{ITEMDB}/Dragon Helm.php">Dragon Helm</a></li>
    <li><a href="{ITEMDB}/Dragon Pants.php">Dragon Pants</a></li></ul>
<p>Data updated May 10, 2025</p>
<footer>MU Online Fanz is a fan resource operated with permission of Webzen.</footer>
</body></html>"""

ITEM_TEXT_LAYOUT = """<h2>Kris</h2>
<div>Attack: 6 ~ 10</div><div>Attack Speed: 50</div><div>Durability: 20</div>
<div>Required Strength: 10</div><div>Required Agility: 8</div>
<div>Classes: DW / DK / ELF / MG</div>
<div>Luck: Yes</div><div>Skill: No</div><div>Grade: Normal</div><div>Weight: 3</div>"""

MOB_COLUMN_LAYOUT = f"""<html><head><title>Goblin - MU Online Fanz</title></head><body>
<h1>Goblin</h1>
<img src="/tools/mobs/data/graphics/Goblin.jpg">
<table>
  <tr><th>Level</th><td>3</td></tr>
  <tr><th>Max HP</th><td>45</td></tr>
  <tr><th>ATK DMG</th><td>7 ~ 10</td></tr>
  <tr><th>ATK Rate</th><td>13</td></tr>
  <tr><th>DEF</th><td>1</td></tr>
  <tr><th>DEF Rate</th><td>1</td></tr>
  <tr><th>Respawn Time</th><td>10 seconds</td></tr>
  <tr><th>Map</th><td><a href="/tools/maps/data/mapdb/Lorencia.php">Lorencia</a>,
                      <a href="/tools/maps/data/mapdb/Noria.php">Noria</a></td></tr>
</table>
<h3>Drops</h3>
<p>This monster does not drop normal items.</p>
<table>
  <tr><th>Excellent Armors</th><th>Excellent Attack Weapons</th><th>Excellent Magic Weapons</th><th>Excellent Shields</th></tr>
  <tr><td><a href="{ITEMDB}/Leather Armor.php">Leather Armor</a><br><a href="{ITEMDB}/Leather Helm.php">Leather Helm</a></td>
      <td><a href="{ITEMDB}/Kris.php">Kris</a></td>
      <td><a href="{ITEMDB}/Skull Staff.php">Skull Staff</a></td>
      <td><a href="{ITEMDB}/Small Shield.php">Small Shield</a></td></tr>
</table>
<p>Data updated May 03, 2019</p>
</body></html>"""

MOB_ROW_LAYOUT = f"""<h2>Spider</h2>
<ul><li>Level: 2</li><li>HP: 30</li><li>Attack: 4-7</li><li>Defense: 1</li><li>Spawn: Lorencia</li>
    <li>Moving Speed: 400</li></ul>
<table><tr><th>Drop List</th></tr>
  <tr><td>Excellent Armor</td><td><a href="{ITEMDB}/Pad Armor.php">Pad Armor</a>, <a href="{ITEMDB}/Pad Helm.php">Pad Helm</a></td></tr>
</table>"""


def test_item_layout_tabela():
    result = parse_item(ITEM_TABLE_LAYOUT, meta_for(ITEM_URL))
    record = result.record
    assert validate("item", record) == []
    assert record["id"] == "dragon-armor"
    assert record["name"] == "Dragon Armor"
    assert record["stats"] == {"defense": 50}
    assert record["durability"] == 68
    assert record["grade"] == "normal"
    assert record["requirements"] == {"level": 45, "strength": 120, "agility": 30,
                                      "vitality": None, "energy": None, "command": None}
    assert record["classes"] == ["Dark Knight", "Blade Knight", "Magic Gladiator"]
    assert record["options"] == ["Jewel of Life", "Jewel of Harmony", "Luck"]
    assert record["related_items"] == ["dragon-helm", "dragon-pants"]
    assert record["image_url"] == "https://muonlinefanz.com/tools/items/data/graphics/Dragon%20Armor.jpg"
    assert record["page_updated_at"] == "2025-05-10"
    assert (record["source"], record["source_url"], record["scraped_at"]) == ("fanz", ITEM_URL, "2026-10-20T12:00:00Z")
    assert record["category"] is None  # não está na página: fica null, não é inventado
    assert result.unmapped == [] and result.warnings == []


def test_item_layout_texto():
    result = parse_item(ITEM_TEXT_LAYOUT, meta_for("https://muonlinefanz.com/tools/items/data/itemdb/Kris.php"))
    record = result.record
    assert validate("item", record) == []
    assert record["stats"] == {"damage_min": 6, "damage_max": 10, "attack_speed": 50}
    assert record["requirements"]["strength"] == 10 and record["requirements"]["agility"] == 8
    assert record["classes"] == ["Dark Wizard", "Dark Knight", "Fairy Elf", "Magic Gladiator"]
    assert record["options"] == ["Luck"]  # "Skill: No" não entra
    assert record["image_url"] is None
    assert [p.label for p in result.unmapped] == ["Weight"]  # vai para o relatório


def test_item_nome_da_pagina_diferente_da_url_gera_aviso():
    result = parse_item("<h1>Something Else</h1>", meta_for(ITEM_URL))
    assert result.record["name"] == "Dragon Armor"
    assert any("nenhum título bate" in w for w in result.warnings)


def test_monstro_drops_por_coluna():
    result = parse_monster(MOB_COLUMN_LAYOUT, meta_for(MOB_URL))
    record = result.record
    assert validate("monster", record) == []
    assert {k: record[k] for k in ("id", "level", "hp", "atk_min", "atk_max", "atk_rate", "def", "def_rate")} == {
        "id": "goblin", "level": 3, "hp": 45, "atk_min": 7, "atk_max": 10, "atk_rate": 13, "def": 1, "def_rate": 1}
    assert (record["respawn_seconds"], record["respawn_raw"]) == (10, "10 seconds")
    assert record["drops_normal_items"] is False
    assert record["page_updated_at"] == "2019-05-03"
    assert record["image_url"] == "https://muonlinefanz.com/tools/mobs/data/graphics/Goblin.jpg"

    maps = result.related["maps"]
    assert [(m["id"], m["source_url"]) for m in maps] == [
        ("lorencia", "https://muonlinefanz.com/tools/maps/data/mapdb/Lorencia.php"),
        ("noria", "https://muonlinefanz.com/tools/maps/data/mapdb/Noria.php"),
    ]
    assert [(s["monster_id"], s["map_id"]) for s in result.related["spawns"]] == [("goblin", "lorencia"), ("goblin", "noria")]
    drops = {(d["item_id"], d["kind"], d["category"]) for d in result.related["drops"]}
    assert drops == {
        ("leather-armor", "excellent", "armor"), ("leather-helm", "excellent", "armor"),
        ("kris", "excellent", "weapon"), ("skull-staff", "excellent", "magic_weapon"),
        ("small-shield", "excellent", "shield"),
    }
    for entity in ("map", "spawn", "drop"):
        for row in result.related[f"{entity}s"]:
            assert validate(entity, row) == []
    assert result.unmapped == [] and result.warnings == []


def test_monstro_drops_por_linha_e_mapa_sem_link():
    result = parse_monster(MOB_ROW_LAYOUT, meta_for("https://muonlinefanz.com/tools/mobs/data/mobdb/Spider.php"))
    record = result.record
    assert validate("monster", record) == []
    assert (record["level"], record["hp"], record["atk_min"], record["atk_max"], record["def"]) == (2, 30, 4, 7, 1)
    assert record["atk_rate"] is None and record["respawn_seconds"] is None and record["drops_normal_items"] is None
    assert [m["id"] for m in result.related["maps"]] == ["lorencia"]
    assert any("mapas sem link" in w for w in result.warnings)
    assert {(d["item_id"], d["kind"], d["category"]) for d in result.related["drops"]} == {
        ("pad-armor", "excellent", "armor"), ("pad-helm", "excellent", "armor")}
    assert [p.label for p in result.unmapped] == ["Moving Speed"]


def test_secao_de_drop_sem_links_gera_aviso():
    html = "<h1>Bat</h1><h3>Drops</h3><p>Excellent items level 10~20</p>"
    result = parse_monster(html, meta_for("https://muonlinefanz.com/tools/mobs/data/mobdb/Bat.php"))
    assert result.related["drops"] == []
    assert any("sem links de item" in w for w in result.warnings)
