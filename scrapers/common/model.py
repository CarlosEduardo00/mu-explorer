"""Resultado de parse e validação contra os JSON Schemas de schema/."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

from scrapers.common.html import Pair

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schema"
ENTITIES = ("item", "monster", "map", "spawn", "drop", "source")


@dataclass
class ParseResult:
    kind: str                       # "item" ou "monster"
    record: dict
    source_file: str = ""
    warnings: list[str] = field(default_factory=list)
    unmapped: list[Pair] = field(default_factory=list)   # rótulos achados e não mapeados
    headings: list[str] = field(default_factory=list)    # títulos de seção da página
    related: dict[str, list[dict]] = field(default_factory=dict)  # maps/spawns/drops extraídos


@cache
def validator(entity: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{entity}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate(entity: str, record: dict) -> list[str]:
    """Lista de erros legíveis (vazia se o registro é válido)."""
    errors = sorted(validator(entity).iter_errors(record), key=lambda e: list(e.path))
    return [f"{'/'.join(str(p) for p in e.path) or '<raiz>'}: {e.message}" for e in errors]
