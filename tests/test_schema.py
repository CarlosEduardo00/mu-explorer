import json

import pytest
from jsonschema import Draft202012Validator

from scrapers.common.model import ENTITIES, SCHEMA_DIR, validate


@pytest.mark.parametrize("entity", ENTITIES)
def test_schemas_sao_validos(entity):
    Draft202012Validator.check_schema(json.loads((SCHEMA_DIR / f"{entity}.schema.json").read_text()))


def test_schema_rejeita_campo_extra_e_falta_de_obrigatorio():
    spawn = {"monster_id": "goblin", "map_id": "lorencia", "season": None, "source": "fanz",
             "source_url": "https://muonlinefanz.com/x", "scraped_at": "2026-10-20T12:00:00Z"}
    assert validate("spawn", spawn) == []
    assert validate("spawn", {**spawn, "extra": 1})
    missing = dict(spawn)
    del missing["map_id"]
    assert validate("spawn", missing)
    assert validate("spawn", {**spawn, "map_id": "Lorencia"})  # id precisa ser slug
