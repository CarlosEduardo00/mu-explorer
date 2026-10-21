"""Relatório em Markdown da coleta/parse: preenchimento dos campos e o que não foi extraído."""
from __future__ import annotations

import json
from collections import Counter

from scrapers.common.http import utc_now
from scrapers.fanz.pipeline import Dataset

# Campos que já sabemos que o Fanz não fornece: aparecem no relatório como "esperado".
EXPECTED_EMPTY = {
    "group": "Fanz não tem grupo/índice do MU; virá do muonline.us",
    "index": "Fanz não tem grupo/índice do MU; virá do muonline.us",
    "season": "season alvo ainda é decisão em aberto",
}


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _filled(value) -> bool:
    return value not in (None, "", [], {})


def fill_rates(records: list[dict]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    order: list[str] = []

    def bump(key: str, filled: bool) -> None:
        if key not in counts:
            order.append(key)
        counts[key] += filled

    for record in records:
        for key, value in record.items():
            if isinstance(value, dict):
                if key == "stats":
                    bump("stats", bool(value))
                    for stat in value:
                        bump(f"stats.{stat}", True)
                else:
                    for sub, sub_value in value.items():
                        bump(f"{key}.{sub}", _filled(sub_value))
            else:
                bump(key, _filled(value))
    return [(key, counts[key]) for key in order]


def _fill_table(title: str, records: list[dict]) -> list[str]:
    lines = [f"### {title} ({len(records)})", ""]
    if not records:
        return lines + ["Nenhum registro.", ""]
    lines += ["| campo | preenchido | % | obs. |", "|---|---:|---:|---|"]
    for key, count in fill_rates(records):
        note = EXPECTED_EMPTY.get(key, "") if count == 0 else ""
        lines.append(f"| `{key}` | {count} | {100 * count // len(records)}% | {note} |")
    return lines + [""]


def _missing(records: list[dict]) -> list[str]:
    return [key for key, count in fill_rates(records) if count == 0 and key not in EXPECTED_EMPTY]


def build_report(dataset: Dataset) -> str:
    items, monsters = dataset.items, dataset.monsters
    item_ids = {i["id"] for i in items}
    outside = [d for d in dataset.drops if d["item_id"] not in item_ids]
    out = [
        "# Relatório da coleta — MU Online Fanz",
        "",
        f"Gerado em {utc_now()}.",
        "",
        "## Resumo",
        "",
        f"- Páginas parseadas: {len(dataset.results)} (falhas: {len(dataset.failures)})",
        f"- Itens: {len(items)} · Monstros: {len(monsters)} · Mapas: {len(dataset.maps)}"
        f" · Spawns: {len(dataset.spawns)} · Drops: {len(dataset.drops)}",
        f"- Drops que apontam para itens fora do conjunto coletado: {len(outside)}"
        " (esperado na amostra; na coleta completa deve ser 0)",
        f"- Erros de schema: {len(dataset.schema_errors)} · IDs duplicados: {len(dataset.duplicates)}",
        "",
        "## Campos não extraídos",
        "",
        f"- Itens: {', '.join(f'`{k}`' for k in _missing(items)) or 'nenhum'}",
        f"- Monstros: {', '.join(f'`{k}`' for k in _missing(monsters)) or 'nenhum'}",
        "",
        "## Preenchimento por campo",
        "",
        *_fill_table("Itens", items),
        *_fill_table("Monstros", monsters),
    ]
    for kind, title in (("item", "itens"), ("monster", "monstros")):
        results = [r for r in dataset.results if r.kind == kind]
        lines: Counter[str] = Counter()
        headings: Counter[str] = Counter()
        for result in results:
            lines.update(set(result.unmapped))
            headings.update(set(result.headings))
        out += [f"## Linhas não aproveitadas — {title}", ""]
        if lines:
            out += ["| linha | páginas |", "|---|---:|"]
            out += [f"| {_cell(text)} | {n} |" for text, n in lines.most_common(40)]
        else:
            out.append("Nenhuma.")
        out += ["", f"## Seções vistas — {title}", ""]
        out += [f"- {h} ({n})" for h, n in headings.most_common(30)] or ["Nenhuma."]
        out.append("")

    out += ["## Avisos por página", ""]
    warned = [r for r in dataset.results if r.warnings]
    for result in warned:
        out.append(f"- `{result.source_file}`")
        out += [f"  - {w}" for w in result.warnings]
    out += ["Nenhum."] if not warned else []
    out.append("")
    if dataset.failures:
        out += ["## Falhas", ""] + [f"- `{f}`: {err}" for f, err in dataset.failures] + [""]
    if dataset.schema_errors:
        out += ["## Erros de schema", ""] + [f"- {e}" for e in dataset.schema_errors[:100]] + [""]
    if dataset.duplicates:
        out += ["## IDs duplicados", ""] + [f"- {d}" for d in dataset.duplicates] + [""]
    for title, rows in (("item", items), ("monstro", monsters)):
        if rows:
            out += [f"## Exemplo de {title}", "", "```json", json.dumps(rows[0], ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(out)
