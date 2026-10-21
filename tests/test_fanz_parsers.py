"""Asserts explícitos sobre páginas REAIS do Fanz (tests/fixtures/fanz/).

Cada teste confere valores contra o que a página mostra, para pegar erro de interpretação que
o teste de regressão (test_fanz_fixtures.py, que só compara com o parse anterior) não pegaria.
"""
import collections
import json
from pathlib import Path

import pytest

from scrapers.common.model import validate
from scrapers.common.storage import decode_html
from scrapers.fanz.parse_item import parse_item
from scrapers.fanz.parse_map import parse_map
from scrapers.fanz.parse_monster import parse_monster
from scrapers.fanz.parse_npc import parse_npc
from scrapers.fanz.pipeline import build_dataset

FIXTURES = Path(__file__).parent / "fixtures" / "fanz"


def load(kind_dir: str, slug: str):
    meta = json.loads((FIXTURES / kind_dir / f"{slug}.meta.json").read_text(encoding="utf-8"))
    html = decode_html((FIXTURES / kind_dir / f"{slug}.html").read_bytes(), meta.get("encoding"))
    return html, meta


def item(slug: str):
    return parse_item(*load("items", slug))


def mob(slug: str):
    return parse_monster(*load("mobs", slug))


# --- itens ---------------------------------------------------------------------------------

def test_item_armadura_excellent():
    result = item("excellent-silver-heart-knight-helm-belief")
    r = result.record
    assert validate("item", r) == []
    assert (r["id"], r["name"]) == ("excellent-silver-heart-knight-helm-belief",
                                    "Excellent Silver Heart Knight Helm (Belief)")
    assert r["stats"] == {"defense": 348}
    assert r["requirements"] == {"level": 1100, "strength": None, "agility": 125, "vitality": None,
                                 "energy": 755, "command": None}
    assert r["classes"] == ["Dragon Knight"]
    assert r["grade"] == "excellent"
    assert r["options"] == ["Jewel of Life", "Jewel of Harmony", "Luck"]
    assert r["option_groups"] == [{
        "title": "Excellent option", "max": 3,
        "lines": ["HP +165", "Mana +165", "DEF Rate +10%", "Decrease DMG +45", "Reflect DMG +5%",
                  "Base DEF +1.5 per 20 levels"],
    }]
    assert r["related_items"][:2] == ["forefather-s-silver-heart-knight-helm",
                                      "forefather-s-silver-heart-knight-helm-belief"]
    assert r["image_url"] is None  # esta página só tem o ícone de ajuda, sem imagem do item
    assert (r["source"], r["season"], r["page_updated_at"]) == ("fanz", None, None)
    assert result.warnings == [] and result.unmapped == []


def test_item_arma_com_faixa_de_dano():
    r = item("excellent-silver-heart-rune-mace").record
    assert validate("item", r) == []
    assert r["stats"] == {"hands": 1, "damage_min": 193, "damage_max": 200, "attack_speed": 40,
                          "wiz_dmg_raise_pct": 123}
    assert r["classes"] == ["Rune Grand Master"]  # "[Rune Grand Master]" na página


def test_item_com_varias_classes_e_abreviacoes():
    assert item("light-crossbow").record["classes"] == ["Fairy Elf"]
    assert item("excellent-bloodangel-summoner-gloves").record["classes"] == ["Dimension Master"]  # "DiM"


def test_item_imagem_so_da_pasta_de_graficos():
    assert item("light-crossbow").record["image_url"] == (
        "https://muonlinefanz.com/tools/items/data/graphics/Light%20Crossbow.jpg")
    assert item("wrath-scroll").record["image_url"] is None  # só o ícone de ajuda


def test_item_consumivel_sem_detalhes():
    result = item("agi-fruit")
    r = result.record
    assert validate("item", r) == []
    assert r["stats"] == {} and r["classes"] == [] and r["options"] == [] and r["grade"] is None
    assert r["notes"][0].startswith("It is used to create additional stat points")
    assert "agi-fruit" not in r["related_items"] and "str-fruit" in r["related_items"]


def test_item_prerequisites_em_vez_de_requirements():
    r = item("wrath-scroll").record
    assert (r["requirements"]["strength"], r["requirements"]["agility"], r["requirements"]["level"]) == (200, 200, 66)
    assert r["classes"] == ["Grow Lancer"]  # "GL"


def test_item_asas_sem_secao_item_details():
    r = item("wings-of-conviction").record
    assert r["stats"] == {"defense": 140, "damage": 100, "dmg_pct": 55, "absorb_dmg_pct": 43}
    assert r["requirements"]["level"] == 800 and r["classes"] == ["Slaughterer"]
    assert "Increased Movement Speed" in r["notes"]
    assert [(g["title"], g["max"]) for g in r["option_groups"]] == [
        ("Additional option", 4), ("Base option", None), ("Additional option", 1)]
    assert r["options"] == ["Jewel of Life", "Luck"]


def test_item_elemental_e_errtel():
    r = item("antonia-s-sword").record
    assert r["stats"] == {"elemental_dmg_min": 209, "elemental_dmg_max": 284, "elemental_def": 288}
    assert r["requirements"]["level"] == 300
    assert {g["title"] for g in r["option_groups"]} == {"Possible additional options", "Errtel bonus"}


def test_item_conjunto_ancient_e_grau():
    r = item("akhir-s-hirat-gloves").record
    assert r["grade"] == "ancient" and r["classes"] == ["Grow Lancer"]
    assert any(g["title"] == "Set option" for g in r["option_groups"])


def test_item_que_nao_dropa():
    r = item("lost-map-5").record
    assert validate("item", r) == []
    assert "This item doesn't drop by any monster..." in r["notes"]


# --- monstros ------------------------------------------------------------------------------

def test_monstro_basico():
    result = mob("dark-knight")
    r = result.record
    assert validate("monster", r) == []
    assert {k: r[k] for k in ("id", "name", "level", "hp", "atk_min", "atk_max", "atk_rate", "def", "def_rate")} == {
        "id": "dark-knight", "name": "Dark Knight", "level": 48, "hp": 3000, "atk_min": 150, "atk_max": 155,
        "atk_rate": 240, "def": 80, "def_rate": 70}
    assert r["page_updated_at"] == "2019-05-03"
    assert r["respawn_seconds"] is None and r["respawn_raw"] is None  # o site não publica respawn
    assert r["difficulty"] is None and r["drops_normal_items"] is True
    assert r["image_url"] == "https://muonlinefanz.com/tools/mobs/data/graphics/Dark%20Knight.jpg"
    [dungeon] = result.related["maps"]
    assert (dungeon["id"], dungeon["name"], dungeon["source_url"]) == (
        "dungeon", "Dungeon", "https://muonlinefanz.com/tools/maps/data/mapdb/Dungeon.php")
    assert dungeon["parent_id"] is None and dungeon["monsters"] == []  # detalhes vêm da página do mapa
    assert [(s["monster_id"], s["map_id"]) for s in result.related["spawns"]] == [("dark-knight", "dungeon")]
    assert result.warnings == [] and result.unmapped == []


def test_monstro_drops_por_tabela_e_categoria():
    drops = mob("dark-knight").related["drops"]
    assert len(drops) == 161
    for drop in drops:
        assert validate("drop", drop) == []
    by = collections.Counter((d["kind"], d["category"]) for d in drops)
    assert by[("normal", "armor")] == 38 and by[("excellent", "armor")] == 19
    assert by[("excellent", "magic_weapon")] == 1 and by[("normal", "skill")] == 24
    by_id = {d["item_id"]: d for d in drops}
    assert by_id["scale-armor"]["table"] == "General Drop Table"
    assert by_id["excellent-bronze-helm"]["kind"] == "excellent"
    assert by_id["suspicious-scrap-of-paper"]["quantity"] == 1          # "(x1)"
    assert by_id["archangel-scroll-3"]["item_name"] == "Archangel Scroll +3"
    assert "zen" not in by_id  # Zen não é item
    assert all(d["rate"] is None for d in drops)  # o site não informa taxa


def test_monstro_com_dificuldade_e_sufixo_no_titulo():
    result = mob("aegis")
    r = result.record
    assert (r["name"], r["id"], r["difficulty"], r["level"], r["hp"]) == ("Aegis", "aegis", 1, 17, 440)
    # "Spawns in Kalima 1." com link para Kalima.php: Kalima 1..7 são mapas distintos.
    assert [(m["id"], m["name"]) for m in result.related["maps"]] == [("kalima-1", "Kalima 1")]
    assert result.related["maps"][0]["source_url"] == "https://muonlinefanz.com/tools/maps/data/mapdb/Kalima.php"


def test_monstro_elemental_e_tabelas_em_frase():
    result = mob("bass")
    r = result.record
    assert validate("monster", r) == []
    assert (r["elemental_def"], r["elemental_dmg_min"], r["elemental_dmg_max"]) == (1500, 960, 990)
    assert r["atk_rate"] is None  # a página não tem ATK Rate
    assert r["notes"] == ["Excellent Holyangel Drop Table: This monster can drop any Excellent Holyangel armor item."]
    assert {d["table"] for d in result.related["drops"]} == {
        "General Drop Table", "Excellent Drop Table", "Excellent Holyangel Drop Table"}


def test_monstro_tabela_ancient():
    result = mob("erohim")
    assert "Ancient Drop Table: Ancient Physical Weapons" in result.record["notes"]
    assert {d["kind"] for d in result.related["drops"]} <= {"normal", "excellent", "ancient"}


def test_monstro_sem_estatisticas_na_pagina():
    r = mob("swamp-wizard").record
    assert validate("monster", r) == []
    assert r["level"] == 275
    assert all(r[k] is None for k in ("hp", "atk_min", "atk_max", "atk_rate", "def", "def_rate"))
    assert r["notes"][0] == "DMG & DEF Adjustment removed after character level 875."


def test_monstro_com_mapa_sem_link():
    result = mob("giant-ogre")
    assert [m["id"] for m in result.related["maps"]] == ["blood-castle-1"]  # "Blood Castle Mini-game 1."
    assert result.warnings == ["mapa sem link: 'Blood Castle 1'"]


@pytest.mark.parametrize("parser, html", [(parse_item, "<html><body><p>sem menu</p></body></html>"),
                                          (parse_monster, "<html><body><p>sem menu</p></body></html>")])
def test_pagina_sem_estrutura_conhecida_gera_aviso_e_nao_quebra(parser, html):
    meta = {"url": "https://muonlinefanz.com/tools/items/data/itemdb/X.php", "final_url": None,
            "fetched_at": "2026-10-21T12:00:00Z", "status": 200, "file": "x.html"}
    result = parser(html, meta)
    assert any("não encontrado" in w for w in result.warnings)
    assert result.record["name"] == "X"


# --- mapas e NPCs --------------------------------------------------------------------------


def test_mapa_lorencia():
    result = parse_map(*load("maps", "lorencia"))
    m = result.record
    assert validate("map", m) == []
    assert (m["id"], m["name"], m["parent_id"]) == ("lorencia", "Lorencia", None)
    assert m["description"].startswith("Lorencia is well established city.")
    assert m["quick_facts"][0] == "Requires character level 10 to enter or warp."
    assert set(m["valued_drops"]) == {"monster", "special"} and "Jewel of Chaos" in m["valued_drops"]["monster"]
    assert len(m["monsters"]) == 8 and len(m["special_monsters"]) == 6 and len(m["bosses"]) == 1
    assert m["npcs"][:3] == ["shadow-phantom-soldier", "hanzo-the-blacksmith", "pasi-the-mage"]
    assert m["connections"] == ["noria", "devias", "dungeon", "valley-of-loren", "deep-dungeon"]
    assert m["image_url"].startswith("https://muonlinefanz.com/tools/maps/data/graphics/Lorencia/")
    assert result.unmapped == []


def test_mapa_com_ligacoes_e_npc():
    m = parse_map(*load("maps", "balgass-barracks")).record
    assert m["connections"] == ["crywolf", "balgass-resting-place"] and m["npcs"] == ["gatekeeper"]
    assert m["quick_facts"][0].startswith("Requires completing the Evidence of Strength quest")


def test_npc_mercador_com_precos():
    n = parse_npc(*load("npcs", "arena-guard")).record
    assert validate("npc", n) == []
    assert (n["id"], n["type"]) == ("arena-guard", "Merchant NPC")
    assert n["locations"] == [{"map_id": "arena", "map_name": "Arena", "x": 72, "y": 164}]
    assert len(n["sells"]) == 27
    assert n["sells"][0] == {"item_id": "apple", "item_name": "Apple", "category": "Recovery Items",
                             "price_zen": 20, "details": None}
    assert all(s["price_zen"] is not None for s in n["sells"])


def test_npc_com_opcoes_do_item_e_varios_mapas():
    n = parse_npc(*load("npcs", "hanzo-the-blacksmith")).record
    assert [loc["map_id"] for loc in n["locations"]] == ["lorencia", "crywolf"]
    first = n["sells"][0]
    assert (first["item_name"], first["details"], first["price_zen"], first["category"]) == (
        "Small Shield", "[+0] [+5 DEF Rate] [+Luck]", 230, "Shield Items")


def test_npc_sem_coordenada_e_de_crafting():
    soldier = parse_npc(*load("npcs", "shadow-phantom-soldier")).record
    assert soldier["type"] == "Quest NPC"
    assert soldier["locations"][0] == {"map_id": "lorencia", "map_name": "Lorencia", "x": None, "y": None}  # @(various)
    machine = parse_npc(*load("npcs", "chaos-goblin-machine"))
    assert machine.record["type"] == "Crafting NPC" and machine.record["sells"] == []
    assert machine.unmapped  # receitas de crafting ainda não são extraídas: vão para o relatório


def test_variante_de_mapa_ganha_mapa_pai_e_mapa_lista_monstros():
    dataset = build_dataset([mob("aegis"), parse_map(*load("maps", "kalima"))])
    maps = {m["id"]: m for m in dataset.maps}
    assert maps["kalima-1"]["parent_id"] == "kalima" and maps["kalima"]["parent_id"] is None
    assert dataset.schema_errors == []
    # Aegis já está em kalima-1 pela página do monstro: a página de Kalima não duplica o spawn.
    assert [(s["monster_id"], s["map_id"]) for s in dataset.spawns] == [("aegis", "kalima-1")]
