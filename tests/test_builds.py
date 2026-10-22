"""Builds prontas do planner (data/curated/builds.json): schema e coerência com as regras de classes."""
import json

import pytest

from scrapers.common.model import REPO_ROOT, validate

BUILDS = REPO_ROOT / "data" / "curated" / "builds.json"
PLANNER = REPO_ROOT / "data" / "curated" / "planner.json"


@pytest.fixture(scope="module")
def builds() -> list[dict]:
    data = json.loads(BUILDS.read_text(encoding="utf-8"))
    assert validate("builds", data) == []
    return data["builds"]


def test_ids_unicos(builds):
    ids = [b["id"] for b in builds]
    assert len(ids) == len(set(ids))


def test_toda_build_aponta_para_classe_existente_e_cobre_todas_as_classes(builds):
    classes = {c["id"] for r in json.loads(PLANNER.read_text(encoding="utf-8"))["rulesets"] for c in r["classes"]}
    assert {b["class_id"] for b in builds} <= classes
    assert classes <= {b["class_id"] for b in builds}, "toda classe do planner tem ao menos uma build"


def test_fases_em_ordem_comecam_no_nivel_1_e_sempre_ha_onde_gastar(builds):
    for b in builds:
        levels = [p["from_level"] for p in b["phases"]]
        assert levels[0] == 1 and levels == sorted(set(levels)), b["id"]
        for p in b["phases"]:
            assert p["split"], f"{b['id']}: fase {p['from_level']} sem split deixaria pontos parados"


def test_comando_so_em_dark_lord(builds):
    for b in builds:
        if b["class_id"] != "dark-lord":
            stats = {r["stat"] for p in b["phases"] for r in p["fill"]} | {s for p in b["phases"] for s in p["split"]}
            assert "cmd" not in stats, b["id"]


OFFICIAL = ("https://muonlinefanz.com/", "https://muonline.webzen.com/")


def test_so_fontes_do_servidor_oficial(builds):
    """Builds são do MU oficial da Webzen: fontes só do Fanz (recurso do oficial) e dos guias da Webzen; vídeos do YouTube."""
    for b in builds:
        assert b["sources"], b["id"]
        for s in b["sources"]:
            assert s["url"].startswith(OFFICIAL), f"{b['id']}: fonte fora do oficial: {s['url']}"
        for v in b.get("videos", []):
            assert v["url"].startswith(("https://www.youtube.com/", "https://youtube.com/")), b["id"]


def test_distribuicao_soma_100_e_e_a_mesma_do_split(builds):
    for b in builds:
        assert sum(b["ratio"].values()) == 100, b["id"]
        assert b["phases"][0]["split"] == b["ratio"], b["id"]


def test_build_antiga_explica_a_renovacao(builds):
    for b in builds:
        if b["status"] == "antiga":
            assert b["notes"] and "renovação" in b["notes"][0], b["id"]


def test_presets_do_stat_planner():
    from scrapers.planner.builds import parse_presets
    html = (REPO_ROOT / "tests" / "fixtures" / "planner" / "stat-planner-presets.html").read_text(encoding="utf-8")
    presets = parse_presets(html)
    assert [p["title"] for p in presets["dl"]] == ["Attacker", "Commander", "PVP / Tank"]
    assert presets["dl"][1]["ratio"] == {"str": 20, "agi": 15, "vit": 5, "ene": 20, "cmd": 40}   # COMfactor = Comando
    assert presets["dl"][2]["ratio"] == {"str": 15, "agi": 30, "vit": 45, "ene": 10}               # 0% fica de fora
    assert presets["slayer"][0] == {"title": "High DMG", "ratio": {"str": 25, "agi": 50, "vit": 15, "ene": 10}}
