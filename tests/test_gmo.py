"""Parser dos guias de mapa do Global MU Online, sobre a página real de Atlans."""
import json
from pathlib import Path

from scrapers.common.model import validate
from scrapers.gmo.cli import guide_key, guide_urls
from scrapers.gmo.parse import merge_monsters, parse_map_guide, zone_count

FIX = Path(__file__).parent / "fixtures" / "gmo"


def atlans():
    html = (FIX / "atlans.html").read_text(encoding="utf-8")
    meta = json.loads((FIX / "atlans.meta.json").read_text(encoding="utf-8"))
    return parse_map_guide(html, meta)


def test_mapa_monstros_com_stats_e_imagem():
    r = atlans()
    assert r["map"]["id"] == "atlans" and r["map"]["level_required"] == 50
    bahamut = next(m for m in r["monsters"] if m["id"] == "bahamut")
    assert (bahamut["level"], bahamut["hp"], bahamut["atk_min"], bahamut["atk_max"], bahamut["def"]) == (43, 4800, 260, 280, 65)
    assert bahamut["respawn_seconds"] == 8
    assert bahamut["image_url"] == "https://globalmuonline.com/guides/atlans/img/bahamut.webp"
    assert all(validate("monster", m) == [] for m in r["monsters"])
    assert validate("map", r["map"]) == []


def test_zonas_de_spawn_com_coordenadas_quantidade_e_numero_do_monstro():
    r = atlans()
    great = [s for s in r["spawns"] if s["monster_id"] == "great-bahamut"]
    assert any((s["x"], s["y"], s["x2"], s["y2"], s["count"]) == (222, 154, 229, 159, 9) for s in great)
    assert next(m for m in r["monsters"] if m["id"] == "great-bahamut")["number"] == 51
    assert all(validate("spawn", s) == [] for s in r["spawns"])


def test_marcadores_spots_do_minimapa_e_portais():
    r = atlans()
    kinds = {m["kind"] for m in r["markers"]}
    assert {"spot", "gate"} <= kinds
    noria = next(m for m in r["markers"] if m["name"] == "Noria entrance")
    assert (noria["kind"], noria["x"], noria["y"]) == ("gate", 10, 10)
    assert all(validate("map_marker", m) == [] for m in r["markers"])


def test_pagina_que_nao_e_mapa_e_ignorada():
    assert parse_map_guide("<html><body><h1>Slayer</h1><p>texto</p></body></html>", {}) is None


def test_sitemap_ignora_conjuntos_de_itens():
    xml = "".join(f"<url><loc>https://globalmuonline.com/{p}</loc></url>" for p in
                  ["guides/", "guides/atlans/", "guides/ancient-items/x/", "drop", "guides/slayer/"])
    assert guide_urls(xml) == ["https://globalmuonline.com/guides/atlans/", "https://globalmuonline.com/guides/slayer/"]
    assert guide_key("https://globalmuonline.com/guides/atlans/") == "atlans"


def test_mesmo_monstro_em_varios_mapas_vira_um_registro():
    a = {"id": "x", "image_url": None, "number": None, "level": 1, "hp": 1, "respawn_seconds": None}
    b = {"id": "x", "image_url": "u", "number": 7, "level": 2, "hp": 2, "respawn_seconds": 5}
    assert merge_monsters([a, b]) == [{"id": "x", "image_url": "u", "number": 7, "level": 1, "hp": 1, "respawn_seconds": 5}]


def test_quantidade_da_zona_nas_duas_grafias():
    assert zone_count("Lv 66 · 14,000 HP · 420–460 dmg · 9 here") == 9
    assert zone_count("Lv 2 · 60 HP · 8–14 dmg · 30 per spot") == 30
    assert zone_count("Lv 2 · 60 HP") is None
