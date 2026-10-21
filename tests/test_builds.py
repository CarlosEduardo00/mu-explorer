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
