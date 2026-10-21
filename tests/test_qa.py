"""Verificações de QA (fase 3) sobre conjuntos de dados pequenos montados à mão."""
import copy

from scrapers.common import qa
from scrapers.common.storage import RawStore
from scrapers.fanz import pipeline
from tests.test_fanz_urls import FIX

PROV = {"season": None, "source": "fanz", "source_url": "https://muonlinefanz.com/x", "scraped_at": "2026-10-21T12:00:00Z"}


def item(item_id, name, related=()):
    return {"id": item_id, "name": name, "related_items": list(related), **PROV}


def dataset():
    return {
        "item": [item("kris", "Kris"), item("short-sword", "Short Sword", related=["kris", "rapier"])],
        "monster": [{"id": "goblin", "name": "Goblin", "level": 3, **PROV},
                    {"id": "spider", "name": "Spider", "level": 2, **PROV}],
        "map": [{"id": "lorencia", "name": "Lorencia", **PROV}],
        "spawn": [{"monster_id": "goblin", "map_id": "lorencia", **PROV}],
        "drop": [{"monster_id": "goblin", "item_id": "kris"}, {"monster_id": "goblin", "item_id": "short-swrd"}],
    }


def by_name(checks):
    return {c.name: c for c in checks}


def test_contagem_com_tolerancia():
    checks = by_name(qa.check_counts(dataset(), {"item": 2, "monster": 100}))
    assert checks["contagem de item"].severity == "ok"
    assert checks["contagem de monster"].severity == "erro"
    assert "98 faltando" in checks["contagem de monster"].detail


def test_campos_obrigatorios():
    data = dataset()
    data["monster"][1]["level"] = None
    checks = by_name(qa.check_required(data))
    assert checks["campos obrigatórios de monster (id, name, level, source_url, scraped_at)"].examples == ["spider"]
    assert checks["campos obrigatórios de item (id, name, source_url, scraped_at)"].severity == "ok"


def test_integridade_com_sugestao_de_nome():
    checks = by_name(qa.check_integrity(dataset()))
    drops = checks["drops -> itens"]
    assert drops.severity == "erro"
    assert drops.examples == ["short-swrd -> short-sword?"]  # nome divergente: sugere o mais parecido
    assert checks["drops -> monstros"].severity == "ok"
    assert checks["spawns -> mapas/monstros"].severity == "ok"
    assert checks["itens relacionados -> itens"].severity == "aviso"  # "rapier" sem registro
    assert checks["monstros sem mapa"].examples == ["spider"]


def test_alerta_quando_a_coleta_muda_demais():
    before = dataset()
    after = copy.deepcopy(before)
    after["item"][0]["name"] = "Kris (novo layout)"
    after["item"][1]["scraped_at"] = "2026-10-22T00:00:00Z"  # só a data da coleta mudou: não conta
    checks = by_name(qa.check_drift(after, before))
    changed = checks["items alterados desde a coleta anterior"]
    assert changed.severity == "aviso" and changed.examples == ["kris"]
    assert checks["variação na contagem de item"].severity == "ok"
    after["monster"] = after["monster"][:1]
    assert by_name(qa.check_drift(after, before))["variação na contagem de monster"].severity == "aviso"


def test_relatorio():
    report = qa.build_report("teste", qa.check_integrity(dataset()))
    assert report.startswith("# QA — teste")
    assert "❌ | drops -> itens" in report and "short-swrd -> short-sword?" in report


def test_contagem_esperada_so_com_listagem_completa(tmp_path):
    store = RawStore(tmp_path)
    for kind in ("item", "monster"):
        src = FIX / f"{kind}-list-p1.html"
        target = tmp_path / "fanz" / "index"
        target.mkdir(parents=True, exist_ok=True)
        (target / src.name).write_bytes(src.read_bytes())
        (target / f"{kind}-list-p1.meta.json").write_text((FIX / f"{kind}-list-p1.meta.json").read_text())
    counts, notes = pipeline.expected_counts(store)
    assert counts == {}  # fixtures só têm a página 1 de cada listagem
    assert notes == ["item: só 1 de 52 páginas da listagem em disco", "monster: só 1 de 5 páginas da listagem em disco"]
