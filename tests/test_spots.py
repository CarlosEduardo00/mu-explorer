"""Spots de farm gerados dos spawns (scrapers/spots.py)."""
from scrapers.common.model import validate
from scrapers.spots import build_spots, spawn_center

MONSTERS = [{"id": "spider", "name": "Spider", "level": 2}, {"id": "budge", "name": "Budge Dragon", "level": 4},
            {"id": "lich", "name": "Lich", "level": 14}, {"id": "gate", "name": "Castle Gate", "level": 1}]
MAPS = [{"id": "lorencia", "name": "Lorencia"}]
PROV = {"season": None, "source": "muemu", "source_url": "https://example.com/x#L1", "scraped_at": "2026-10-21T13:25:11Z"}


def spawn(monster, x, y, kind="normal", x2=None, y2=None, count=None):
    return {"monster_id": monster, "map_id": "lorencia", "kind": kind, "x": x, "y": y, "x2": x2, "y2": y2,
            "radius": 30, "count": count, **PROV}


def test_centro_usa_area_quando_valida_e_ponto_quando_nao():
    assert spawn_center(spawn("spider", 10, 20, "spot", 20, 40, 5)) == (15, 30)
    assert spawn_center(spawn("spider", 182, 126, "spot", 6, 4, 35)) == (182, 126)   # x2 < x no MuEmu: usa o ponto
    assert spawn_center({"x": None, "y": 3}) is None


def test_agrupa_por_regiao_soma_quantidades_e_faixa_de_nivel():
    spawns = [spawn("spider", 180, 110, "spot", 190, 120, 10)] + [spawn("budge", 185, 115) for _ in range(5)] + [
        spawn("lich", 20, 20) for _ in range(6)]
    spots = build_spots(spawns, MONSTERS, MAPS)
    assert [s["id"] for s in spots] == ["lorencia-1", "lorencia-2"]
    first = spots[0]
    assert first["total"] == 15 and (first["level_min"], first["level_max"]) == (2, 4)
    assert [(m["name"], m["count"]) for m in first["monsters"]] == [("Spider", 10), ("Budge Dragon", 5)]
    assert (first["x_min"], first["y_min"], first["x_max"], first["y_max"]) == (180, 110, 190, 120)
    assert all(validate("farm_spot", s) == [] for s in spots)


def test_ignora_eventos_e_grupos_pequenos_e_junta_areas_grandes_iguais():
    spawns = [spawn("gate", 14, 75, "event") for _ in range(10)] + [spawn("lich", 100, 100) for _ in range(2)] + [
        spawn("budge", 135, 20, "spot", 240, 88, 30), spawn("budge", 135, 20, "spot", 240, 88, 30)]
    spots = build_spots(spawns, MONSTERS, MAPS)
    assert len(spots) == 1
    assert spots[0]["total"] == 60 and spots[0]["monsters"][0]["monster_id"] == "budge"


def test_heat_por_volume_e_boss():
    from scrapers.spots import classify_heat
    spots = [{"total": t, "monsters": [{"monster_id": "x"}]} for t in (3, 9, 10, 12, 30)]
    spots.append({"total": 3, "monsters": [{"monster_id": "chefe"}]})
    classify_heat(spots, {"chefe"})   # mediana 10
    assert [s["heat"] for s in spots] == ["low", "mid", "mid", "mid", "hot", "boss"]
    iguais = [{"total": 9, "monsters": [{"monster_id": "x"}]} for _ in range(4)]
    classify_heat(iguais, set())
    assert {s["heat"] for s in iguais} == {"mid"}


def test_zonas_vizinhas_em_lados_de_uma_linha_da_grade_ficam_juntas():
    spawns = [spawn("lich", 45, 37, "spot", 50, 42, 3), spawn("lich", 47, 38, "spot", 51, 43, 3),
              spawn("lich", 120, 120, "spot", 125, 125, 3)]
    spots = build_spots(spawns, MONSTERS, MAPS)
    assert [s["total"] for s in spots] == [6, 3]
