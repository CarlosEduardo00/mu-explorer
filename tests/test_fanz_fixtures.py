"""Parse de HTML REAL do Fanz salvo em tests/fixtures/fanz/{items,mobs}/.

Para gerar: `python -m scrapers.fanz poc` e depois `python -m scrapers.fanz fixtures --golden`
(revise os .expected.json antes de commitar). Sem fixtures, o teste é pulado.
Com .expected.json ao lado do HTML, o teste vira de regressão: qualquer mudança no
resultado do parse precisa ser intencional (regere com --golden).
"""
import json
from pathlib import Path

import pytest

from scrapers.common.model import validate
from scrapers.common.storage import decode_html
from scrapers.fanz.pipeline import KIND_DIRS, PARSERS

FIXTURES = Path(__file__).parent / "fixtures" / "fanz"
CASES = [
    pytest.param(kind, path, id=f"{kind_dir}/{path.name}")
    for kind, kind_dir in KIND_DIRS.items()
    for path in sorted((FIXTURES / kind_dir).glob("*.html"))
] or [pytest.param(None, None, marks=pytest.mark.skip(reason="sem HTML real em tests/fixtures/fanz"))]


@pytest.mark.parametrize("kind, path", CASES)
def test_fixture_real(kind, path):
    meta = json.loads(path.with_name(path.stem + ".meta.json").read_text(encoding="utf-8"))
    result = PARSERS[kind](decode_html(path.read_bytes(), meta.get("encoding")), meta)
    assert result.record["name"]
    assert validate(kind, result.record) == []
    for entity in ("map", "spawn", "drop"):
        for row in result.related.get(f"{entity}s", []):
            assert validate(entity, row) == []
    expected_path = path.with_name(path.stem + ".expected.json")
    if expected_path.exists():
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        assert {"record": result.record, "related": result.related} == expected
