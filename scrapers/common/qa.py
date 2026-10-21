"""QA dos dados processados (fase 3): contagens, campos obrigatórios, integridade referencial,
nomes divergentes e variação em relação à coleta anterior.

Independe da fonte: trabalha sobre os JSON de data/processed/<fonte>/.
"""
from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field
from pathlib import Path

from scrapers.common.ids import slugify
from scrapers.common.model import validate

FILES = {"item": "items.json", "monster": "monsters.json", "map": "maps.json", "npc": "npcs.json",
         "spawn": "spawns.json", "drop": "drops.json"}
REQUIRED = {
    "item": ["id", "name", "source_url", "scraped_at"],
    "monster": ["id", "name", "level", "source_url", "scraped_at"],
    "map": ["id", "name"],
    "npc": ["id", "name"],
}
# Campos que mudam a cada coleta e não indicam mudança de conteúdo.
VOLATILE = {"scraped_at"}


@dataclass
class Check:
    name: str
    severity: str           # "erro" | "aviso" | "ok"
    detail: str
    examples: list[str] = field(default_factory=list)


def load(directory: Path) -> dict[str, list[dict]]:
    data = {}
    for entity, filename in FILES.items():
        path = directory / filename
        data[entity] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    return data


def check_counts(data: dict[str, list[dict]], expected: dict[str, int], tolerance: float = 0.01,
                 broken: dict[str, int] | None = None) -> list[Check]:
    """broken: quantas páginas da listagem o próprio site devolve quebradas (não contam como falta nossa)."""
    checks = []
    broken = broken or {}
    for entity, wanted in expected.items():
        got = len(data.get(entity, []))
        missing = wanted - got
        known = broken.get(entity, 0)
        severity = "ok" if missing - known <= wanted * tolerance else "erro"
        detail = f"{got} de {wanted}"
        if missing:
            detail += f" ({missing} faltando" + (f"; {known} com página quebrada no site)" if known else ")")
        checks.append(Check(f"contagem de {entity}", severity, detail))
    return checks


def check_schema(data: dict[str, list[dict]]) -> list[Check]:
    checks = []
    for entity, rows in data.items():
        errors = [f"{r.get('id') or r.get('monster_id')}: {e}" for r in rows for e in validate(entity, r)]
        checks.append(Check(f"schema de {entity}", "erro" if errors else "ok",
                            f"{len(errors)} erros em {len(rows)} registros", errors[:10]))
    return checks


def check_required(data: dict[str, list[dict]]) -> list[Check]:
    checks = []
    for entity, fields in REQUIRED.items():
        rows = data.get(entity, [])
        bad = [r.get("id", "?") for r in rows if any(r.get(f) in (None, "", []) for f in fields)]
        checks.append(Check(f"campos obrigatórios de {entity} ({', '.join(fields)})",
                            "erro" if bad else "ok", f"{len(bad)} de {len(rows)} sem algum campo", bad[:10]))
    return checks


def _suggest(missing: list[str], names_by_id: dict[str, str]) -> list[str]:
    """Para cada id inexistente, o id existente mais parecido (nomes divergentes entre páginas/fontes)."""
    known = list(names_by_id)
    out = []
    for item_id in missing:
        match = difflib.get_close_matches(item_id, known, n=1, cutoff=0.85)
        out.append(f"{item_id} -> {match[0]}?" if match else item_id)
    return out


def check_integrity(data: dict[str, list[dict]], dead_items: set[str] | None = None) -> list[Check]:
    """dead_items: ids de itens cuja página existe no link da fonte, mas está quebrada no próprio site."""
    items = {i["id"]: i["name"] for i in data["item"]}
    monsters = {m["id"] for m in data["monster"]}
    maps = {m["id"] for m in data["map"]}
    dead_items = dead_items or set()
    checks = []

    missing = [d["item_id"] for d in data["drop"] if d["item_id"] not in items]
    broken_items = sorted(set(missing) - dead_items)
    dead = sorted(set(missing) & dead_items)
    checks.append(Check("drops -> itens", "erro" if broken_items else "ok",
                        f"{sum(1 for i in missing if i not in dead_items)} de {len(data['drop'])} drops apontam para "
                        f"{len(broken_items)} itens nunca vistos", _suggest(broken_items[:15], items)))
    if dead:
        checks.append(Check("drops -> itens com página quebrada na fonte", "aviso",
                            f"{sum(1 for i in missing if i in dead_items)} drops apontam para {len(dead)} itens cuja "
                            f"página responde '404' com HTTP 200 no site", dead[:15]))
    orphan = sorted({d["monster_id"] for d in data["drop"] if d["monster_id"] not in monsters})
    checks.append(Check("drops -> monstros", "erro" if orphan else "ok",
                        f"{len(orphan)} monstros inexistentes", orphan[:10]))
    bad_spawns = sorted({f"{s['monster_id']}->{s['map_id']}" for s in data["spawn"]
                         if s["map_id"] not in maps or s["monster_id"] not in monsters})
    checks.append(Check("spawns -> mapas/monstros", "erro" if bad_spawns else "ok",
                        f"{len(bad_spawns)} spawns quebrados", bad_spawns[:10]))
    related = sorted({r for i in data["item"] for r in i.get("related_items", []) if r not in items})
    # Itens relacionados vêm muitas vezes de texto sem link no Fanz: quebra é aviso, não erro.
    checks.append(Check("itens relacionados -> itens", "aviso" if related else "ok",
                        f"{len(related)} ids de itens relacionados sem registro", _suggest(related[:15], items)))
    without_spawn = sorted(monsters - {s["monster_id"] for s in data["spawn"]})
    checks.append(Check("monstros sem mapa", "aviso" if without_spawn else "ok",
                        f"{len(without_spawn)} de {len(monsters)}", without_spawn[:10]))
    if data.get("npc") or any(m.get("monsters") for m in data["map"]):
        checks += _map_npc_integrity(data, monsters, maps)
    dup_names = _duplicates(data["item"])
    checks.append(Check("itens com o mesmo nome normalizado", "aviso" if dup_names else "ok",
                        f"{len(dup_names)} grupos", dup_names[:10]))
    return checks


def _map_npc_integrity(data: dict[str, list[dict]], monsters: set[str], maps: set[str]) -> list[Check]:
    npcs = {n["id"] for n in data.get("npc", [])}
    listed = sorted({f"{m['id']}:{x}" for m in data["map"] for key in ("monsters", "special_monsters", "bosses")
                     for x in m.get(key, []) if x not in monsters})
    map_npcs = sorted({f"{m['id']}:{x}" for m in data["map"] for x in m.get("npcs", []) if x not in npcs})
    npc_maps = sorted({f"{n['id']}:{loc['map_id']}" for n in data.get("npc", []) for loc in n["locations"]
                       if loc["map_id"] not in maps})
    parents = sorted({f"{m['id']}->{m['parent_id']}" for m in data["map"]
                      if m.get("parent_id") and m["parent_id"] not in maps})
    return [
        Check("mapas -> monstros listados", "aviso" if listed else "ok", f"{len(listed)} sem registro", listed[:10]),
        Check("mapas -> NPCs listados", "aviso" if map_npcs else "ok", f"{len(map_npcs)} sem registro", map_npcs[:10]),
        Check("NPCs -> mapas", "aviso" if npc_maps else "ok", f"{len(npc_maps)} sem registro", npc_maps[:10]),
        Check("mapas -> mapa pai", "erro" if parents else "ok", f"{len(parents)} quebrados", parents[:10]),
    ]


def _duplicates(rows: list[dict]) -> list[str]:
    groups: dict[str, list[str]] = {}
    for row in rows:
        groups.setdefault(slugify(row["name"]).replace("-", ""), []).append(row["name"])
    return [" | ".join(names) for names in groups.values() if len(names) > 1]


def check_drift(current: dict[str, list[dict]], previous: dict[str, list[dict]],
                count_threshold: float = 0.05, change_threshold: float = 0.2) -> list[Check]:
    """Alerta quando uma nova coleta muda demais em relação à anterior (site mudou de layout, parser quebrou...)."""
    checks = []
    for entity in ("item", "monster", "drop"):
        before, after = previous.get(entity, []), current.get(entity, [])
        if not before:
            continue
        delta = (len(after) - len(before)) / len(before)
        checks.append(Check(f"variação na contagem de {entity}", "aviso" if abs(delta) > count_threshold else "ok",
                            f"{len(before)} -> {len(after)} ({delta:+.1%})"))
        if entity == "drop":
            continue
        old = {r["id"]: _stable(r) for r in before}
        new = {r["id"]: _stable(r) for r in after}
        common = old.keys() & new.keys()
        changed = sorted(k for k in common if old[k] != new[k])
        ratio = len(changed) / len(common) if common else 0.0
        checks.append(Check(f"{entity}s alterados desde a coleta anterior",
                            "aviso" if ratio > change_threshold else "ok",
                            f"{len(changed)} de {len(common)} ({ratio:.1%}); removidos: {len(old.keys() - new.keys())},"
                            f" novos: {len(new.keys() - old.keys())}", changed[:10]))
    return checks


def _stable(row: dict) -> str:
    return json.dumps({k: v for k, v in row.items() if k not in VOLATILE}, sort_keys=True, ensure_ascii=False)


def build_report(title: str, checks: list[Check]) -> str:
    icon = {"erro": "❌", "aviso": "⚠️", "ok": "✅"}
    errors = sum(c.severity == "erro" for c in checks)
    warnings = sum(c.severity == "aviso" for c in checks)
    out = [f"# QA — {title}", "", f"{errors} erros · {warnings} avisos · {len(checks)} verificações", "",
           "| | verificação | resultado |", "|---|---|---|"]
    out += [f"| {icon[c.severity]} | {c.name} | {c.detail} |" for c in checks]
    detailed = [c for c in checks if c.examples and c.severity != "ok"]
    if detailed:
        out += ["", "## Exemplos", ""]
        for check in detailed:
            out += [f"**{check.name}**", ""] + [f"- `{e}`" for e in check.examples] + [""]
    return "\n".join(out) + "\n"
