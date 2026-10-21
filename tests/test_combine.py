"""Cruzamento Fanz + MuEmu com registros pequenos montados à mão."""
from scrapers.combine import combine, item_keys

PROV = {"season": None, "source": "fanz", "source_url": "https://muonlinefanz.com/x", "scraped_at": "2026-10-21T12:00:00Z"}
REQ = {"level": None, "strength": None, "agility": None, "vitality": None, "energy": None, "command": None}


def fitem(name, grade=None, strength=None, durability=None):
    from scrapers.common.ids import slugify
    return {"id": slugify(name), "name": name, "grade": grade, "group": None, "index": None, "category": None,
            "durability": durability, "requirements": {**REQ, "strength": strength}, "stats": {}, **PROV}


def mitem(item_id, name, group, index, strength=None):
    return {"id": item_id, "name": name, "group": group, "index": index, "category": "armor", "durability": 56,
            "requirements": {**REQ, "strength": strength}, "stats": {}, **PROV, "source": "muemu"}


def mon(mid, name, level, **extra):
    return {"id": mid, "name": name, "level": level, "number": None, "respawn_seconds": None, "respawn_raw": None,
            "hp": None, "atk_min": None, "atk_max": None, "def": None, **PROV, **extra}


def spawn(monster_id, map_id, **extra):
    return {"monster_id": monster_id, "map_id": map_id, **PROV, **extra}


def test_chaves_de_busca():
    assert item_keys({"name": "Excellent Bronze Helm"}) == [("nome", "excellent-bronze-helm"),
                                                           ("item base do excellent", "bronze-helm")]
    assert item_keys({"name": "Agnis Adamantine Armor", "grade": "ancient"})[1] == ("item base do ancient",
                                                                                    "adamantine-armor")
    assert item_keys({"name": "Dragon Armor", "grade": "normal"}) == [("nome", "dragon-armor")]


def dataset():
    fanz = {
        "item": [fitem("Adamantine Armor", strength=200), fitem("Excellent Adamantine Armor", "excellent"),
                 fitem("Agnis Adamantine Armor", "ancient"), fitem("Mystery Item", durability=9)],
        "monster": [mon("aegis", "Aegis", 32), mon("dark-knight", "Dark Knight", 48, hp=3000), mon("bass", "Bass", 127)],
        "map": [{"id": "dungeon", "name": "Dungeon", **PROV}],
        "spawn": [spawn("dark-knight", "dungeon")],
        "drop": [], "source": [],
    }
    muemu = {
        "item": [mitem("adamantine-armor-g8-i66", "Adamantine Armor", 8, 66, strength=201),
                 mitem("adamantine-armor-g8-i26", "Adamantine Armor", 8, 26, strength=200)],
        "monster": [mon("aegis-147", "Aegis", 17, number=147, respawn_seconds=10),
                    mon("aegis-177", "Aegis", 32, number=177, respawn_seconds=10),
                    mon("dark-knight", "Dark Knight", 48, number=10, respawn_seconds=10, hp=2900)],
        "map": [{"id": "dungeon", "name": "Dungeon", **PROV}, {"id": "kalima-2", "name": "Kalima 2", **PROV},
                {"id": "lorencia", "name": "Lorencia", **PROV}],
        "spawn": [spawn("aegis-177", "kalima-2", kind="normal", x=1, y=2), spawn("dark-knight", "dungeon", kind="normal"),
                  spawn("rabbit", "lorencia", kind="spot")],
        "drop": [], "source": [],
    }
    return fanz, muemu


def test_itens_recebem_grupo_indice_do_item_base():
    data, matches, diffs = combine(*dataset())
    items = {i["id"]: i for i in data["item"]}
    for item_id in ("adamantine-armor", "excellent-adamantine-armor", "agnis-adamantine-armor"):
        assert (items[item_id]["group"], items[item_id]["index"], items[item_id]["durability"]) == (8, 26, 56)
    assert items["mystery-item"]["group"] is None and items["mystery-item"]["durability"] == 9  # Fanz não é sobrescrito
    methods = {m["fanz_id"]: m["method"] for m in matches["item"]}
    assert methods == {"adamantine-armor": "nome", "excellent-adamantine-armor": "item base do excellent",
                       "agnis-adamantine-armor": "item base do ancient"}
    assert matches["item"][0]["candidates"] == ["adamantine-armor-g8-i26", "adamantine-armor-g8-i66"]
    assert diffs == ["monstro dark-knight: hp Fanz=3000 MuEmu=2900"]  # requisito igual no candidato escolhido


def test_monstros_casam_por_nome_e_nivel_e_trazem_respawn_e_spots():
    data, matches, _ = combine(*dataset())
    monsters = {m["id"]: m for m in data["monster"]}
    assert (monsters["aegis"]["number"], monsters["aegis"]["respawn_seconds"]) == (177, 10)  # nível 32 -> 177
    assert monsters["dark-knight"]["hp"] == 3000  # valor do Fanz mantido
    assert monsters["bass"]["respawn_seconds"] is None  # sem par no MuEmu
    spawns = {(s["monster_id"], s["map_id"], s.get("kind")) for s in data["spawn"]}
    assert spawns == {("dark-knight", "dungeon", None), ("dark-knight", "dungeon", "normal"),
                      ("aegis", "kalima-2", "normal")}  # spawn do rabbit (sem par) fica de fora
    assert [m["id"] for m in data["map"]] == ["dungeon", "kalima-2"]  # só mapas usados
