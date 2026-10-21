"""Parse dos arquivos do MuEmu sobre trechos reais (tests/fixtures/muemu/)."""
from pathlib import Path

from scrapers.common.model import validate
from scrapers.muemu import parse, source

FIX = Path(__file__).parent / "fixtures" / "muemu"
META = {"commit": "659dccb962", "commit_date": "2023-05-30", "fetched_at": "2026-10-21T13:30:00Z"}


def read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_itens():
    items, warnings = parse.parse_items(read("itemS16.txt"), META)
    assert warnings == []
    by_id = {i["id"]: i for i in items}
    assert set(by_id) == {"kris", "book-of-lagle", "adamantine-armor-g8-i26", "adamantine-armor-g8-i66",
                          "drain-life-parchment"}  # nome repetido ganha sufixo de grupo/índice
    for item in items:
        assert validate("item", item) == []
    kris = by_id["kris"]
    assert (kris["group"], kris["index"], kris["category"], kris["durability"]) == (0, 0, "sword", 20)
    assert kris["stats"] == {"damage_min": 6, "damage_max": 11, "attack_speed": 50, "hands": 1}
    assert kris["requirements"]["strength"] == 20 + 40 * 6 * 3 // 100  # fator 40, drop level 6
    assert kris["classes"][:3] == ["Dark Wizard", "Dark Knight", "Fairy Elf"]
    assert (kris["season"], kris["source"]) == ("S16", "muemu")
    assert kris["source_url"] == f"{source.REPO_URL}/blob/659dccb962/Data/itemS16.txt#L2"
    adamantine = by_id["adamantine-armor-g8-i26"]
    assert (adamantine["requirements"]["strength"], adamantine["requirements"]["agility"]) == (200, 69)  # = Fanz
    assert by_id["book-of-lagle"]["requirements"]["energy"] == 411  # livros: energia x3 (= Fanz)
    assert by_id["drain-life-parchment"]["requirements"]["energy"] == 150  # scroll: valor direto (= Fanz)


def test_formula_de_requisitos():
    assert source.requirement(77, 78, 8, "Adamantine Armor", "strength") == 200
    assert source.requirement(171, 148, 8, "Dark Devil Armor", "energy") == 1032  # energia x4
    assert source.requirement(0, 78, 8, "X", "strength") is None


def test_monstros_e_spawns():
    monsters, warnings = parse.parse_monsters(read("Monster.xml"), META)
    assert warnings == []
    by_id = {m["id"]: m for m in monsters}
    assert set(by_id) == {"dark-knight", "aegis-147", "aegis-177"}  # Aegis tem uma variante por Kalima
    dk = by_id["dark-knight"]
    assert {k: dk[k] for k in ("number", "level", "hp", "atk_min", "atk_max", "atk_rate", "def", "def_rate",
                               "respawn_seconds")} == {
        "number": 10, "level": 48, "hp": 3000, "atk_min": 150, "atk_max": 155, "atk_rate": 240, "def": 80,
        "def_rate": 70, "respawn_seconds": 10}  # mesmos números do Fanz, mais o respawn
    for monster in monsters:
        assert validate("monster", monster) == []

    maps, spawns, warnings = parse.parse_spawns(read("MonsterSetBase.xml"), monsters, META)
    assert [(m["id"], m["name"]) for m in maps] == [("dungeon", "Dungeon"), ("kalima-1", "Kalima 1")]
    assert [(s["monster_id"], s["map_id"], s["kind"], s["x"], s["y"]) for s in spawns] == [
        ("dark-knight", "dungeon", "normal", 41, 88), ("dark-knight", "dungeon", "normal", 19, 120),
        ("aegis-147", "kalima-1", "normal", 34, 22)]  # NPC fica de fora
    assert warnings == ["1 spawns de 1 tipos sem monstro em Monster.xml: [413]"]
    for entity, rows in (("map", maps), ("spawn", spawns)):
        for row in rows:
            assert validate(entity, row) == []


def test_nomes_de_mapa():
    assert source.map_name("LostTower") == "Lost Tower"
    assert source.map_name("Dugeon") == "Dungeon"
    assert source.map_name("Kalima3") == "Kalima 3"
    assert source.map_name("Kantru1") == "Kanturu 1"
    assert source.map_name("ValleyofLoren") == "Valley of Loren"
