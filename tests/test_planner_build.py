"""Gerador das regras de classe do planner, sobre trechos reais dos guias do Fanz e do MuEmu."""
import json
from pathlib import Path

import pytest

from scrapers.common.model import REPO_ROOT, validate
from scrapers.planner import build

FIX = Path(__file__).parent / "fixtures" / "planner"


def lines(key: str) -> list[str]:
    return (FIX / f"class-{key}.lines.txt").read_text(encoding="utf-8").splitlines()


def test_guia_de_classe_tier_1():
    guide = build.parse_guide(lines("slayer"))
    assert (guide["name"], guide["tier"], guide["unlock_level"]) == ("Slayer", 1, None)
    assert guide["rates"] == [(5, False), (6, True)] and guide["max_level"] == 1450
    assert [(e["tier"], e["name"], e["level"]) for e in guide["evolutions"]] == [
        (1, "Slayer", None), (2, "Royal Slayer", 150), (3, "Master Slayer", 400), (4, "Slaughterer", 800)]


def test_guia_de_classe_tier_2():
    guide = build.parse_guide(lines("gl"))
    assert (guide["name"], guide["tier"], guide["unlock_level"]) == ("Grow Lancer", 2, 220)
    assert guide["rates"] == [(7, False)]  # 7 por nível, sem mudança no Hero Status
    assert [e["name"] for e in guide["evolutions"]] == ["Grow Lancer", "Mirage Lancer", "Shining Lancer"]


def test_guia_com_faixa_de_niveis_na_linha_seguinte():
    # O guia do DK escreve "+6 Stat Points per level" e, na linha seguinte, "From level 220 ~ 400."
    guide = build.parse_guide(lines("dk"))
    assert guide["rates"] == [(5, False), (6, True)]


def test_pontos_por_nivel_viram_faixas():
    assert build.rates_to_steps([(5, False), (6, True)]) == [
        {"from_level": 2, "per_level": 5}, {"from_level": 220, "per_level": 6}]
    assert build.rates_to_steps([(7, False)]) == [{"from_level": 2, "per_level": 7}]


def test_atributos_base_do_stat_planner_e_do_muemu():
    plan = build.parse_planner_bases((FIX / "stat-planner-excerpt.html").read_text(encoding="utf-8"))
    assert plan["gun"] == {"str": 20, "agi": 18, "vit": 20, "ene": 25}
    assert plan["slayer"] == {"str": 28, "agi": 30, "vit": 15, "ene": 10}
    muemu = build.parse_muemu_bases((FIX / "Characters.xml").read_text(encoding="utf-8"))
    assert muemu["GunCrusher"] == {"str": 20, "agi": 18, "vit": 20, "ene": 25, "cmd": 0}
    for key, mu in (("gun", "GunCrusher"), ("slayer", "Slayer"), ("gl", "GrowLancer")):
        assert plan[key] == {k: v for k, v in muemu[mu].items() if k != "cmd"}  # as duas fontes concordam


PLANNER = REPO_ROOT / "data" / "curated" / "planner.json"


@pytest.fixture(scope="module")
def planner() -> dict:
    return json.loads(PLANNER.read_text(encoding="utf-8"))


def test_planner_json_valido(planner):
    assert validate("planner", planner) == []


def test_planner_json_ordem_e_publicacao(planner):
    assert [r["id"] for r in planner["rulesets"]] == ["global-atual", "classico"]  # mais nova primeiro
    atual, classico = planner["rulesets"]
    assert atual["publish"] is True and classico["publish"] is True  # publicação autorizada (out/2026)
    assert [c["id"] for c in atual["classes"][:3]] == ["gun-crusher", "slayer", "grow-lancer"]
    assert len(atual["classes"]) == 16 and len(classico["classes"]) == 11


def test_classes_novas_do_gmo_com_base_citada_e_imagens(planner):
    atual = {c["id"]: c for c in planner["rulesets"][0]["classes"]}
    cr = atual["crusader"]
    assert cr["base"] == {"str": 26, "agi": 18, "vit": 19, "ene": 20, "cmd": 0} and cr["sources"]
    assert [e["name"] for e in cr["evolutions"]][-1] == "Templar Commander"
    assert atual["alchemist"]["base"]["ene"] == 25 and atual["illusion-knight"]["base"]["agi"] == 28
    assert all(c.get("image_url", "").startswith("https://globalmuonline.com/guides/classes/img/") for c in atual.values())
    assert atual["magic-gladiator"]["evolutions"][0]["image_url"].endswith("magic-gladiator-t1.webp")


def test_guia_de_classe_do_gmo():
    info = build.parse_gmo_class((FIX / "gmo-crusader.html").read_text(encoding="utf-8"))
    assert info["points"] == 5
    assert info["line"][0] == (1, "Crusader") and info["line"][-1] == (5, "Templar Commander")
    assert info["images"][1] == "https://globalmuonline.com/guides/classes/img/crusader-t1.webp"


def test_planner_json_regras_das_tres_primeiras_classes(planner):
    atual = {c["id"]: c for c in planner["rulesets"][0]["classes"]}
    gc, sl, gl = atual["gun-crusher"], atual["slayer"], atual["grow-lancer"]
    assert gc["base"] == {"str": 20, "agi": 18, "vit": 20, "ene": 25, "cmd": 0}
    assert gc["points"] == [{"from_level": 2, "per_level": 5}, {"from_level": 220, "per_level": 6}]
    assert "Heist Gun Crusher" in gc["names"] and "Slaughterer" in sl["names"]
    assert (gl["tier"], gl["unlock_level"], gl["points"]) == (2, 220, [{"from_level": 2, "per_level": 7}])
    assert gl["max_level"] == 1450 and planner["rulesets"][1]["classes"][0]["max_level"] == 400


def test_planner_json_so_dark_lord_tem_comando(planner):
    for ruleset in planner["rulesets"]:
        with_cmd = [c["id"] for c in ruleset["classes"] if c["base"]["cmd"]]
        assert with_cmd == ["dark-lord"]


def test_planner_json_classico_usa_a_base_do_muemu(planner):
    atual = {c["id"]: c for c in planner["rulesets"][0]["classes"]}
    classico = {c["id"]: c for c in planner["rulesets"][1]["classes"]}
    assert classico["summoner"]["base"]["ene"] == 30 and atual["summoner"]["base"]["ene"] == 23  # mudou entre versões
    assert classico["magic-gladiator"]["points"] == [{"from_level": 2, "per_level": 7}]
    assert classico["slayer"]["points"] == [{"from_level": 2, "per_level": 5}]
