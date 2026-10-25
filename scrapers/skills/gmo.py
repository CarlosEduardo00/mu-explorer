"""Tabelas de skills dos guias de classe do Global MU Online (/guides/<classe>/, data/raw/gmo/guides/<chave>.html,
baixados por `python -m scrapers.gmo fetch`).

Estrutura real (out/2026): `<h2 id="skills">All <Classe> skills</h2>` seguido de `<table class="tblSmall cSk">` com as
colunas Skill, Unlocked as, Level, Requirements, Mana / AG, Range, Base dmg; depois `<h3>4th and 5th class skills</h3>`
com uma segunda tabela igual (melhorias da 4ª classe e skills da 5ª). "—" = sem valor; `<i>weapon</i>` ao lado do nome
marca a skill que vem da arma. Requisitos como "STR 1,045, AGI 418" ou "ENE 1,058". O GMO é servidor S21 (privado):
os números valem como referência quando o Fanz não cobre a classe.
"""
from __future__ import annotations

import re

from selectolax.lexbor import LexborHTMLParser

from scrapers.common.html import clean
from scrapers.common.ids import slugify

SEASON = "S21"
STATS = {"STR": "str", "AGI": "agi", "VIT": "vit", "STA": "vit", "ENE": "ene", "CMD": "cmd", "COM": "cmd"}
COLUMNS = {"skill": "name", "unlocked as": "unlocked_as", "level": "level", "requirements": "requirements",
           "mana / ag": "cost", "range": "range", "base dmg": "base_dmg"}
# Erros de grafia do GMO (ex.: "Holly Sweep" = Holy Sweep), corrigidos também nas melhorias ("... Enhancement Skill").
NAME_FIXES = {"Holly Sweep": "Holy Sweep", "Secred Impact": "Sacred Impact", "Busting Flare": "Bursting Flare"}


def fix_name(name: str) -> str:
    for wrong, right in NAME_FIXES.items():
        name = name.replace(wrong, right)
    return name


def _int(text: str) -> int | None:
    m = re.search(r"\d[\d,]*", text or "")
    return int(m.group(0).replace(",", "")) if m else None


def _value(text: str) -> str | None:
    text = clean(text)
    return None if text in ("", "—", "-", "–") else text


def parse_class_skills(html: str) -> tuple[list[dict], list[str]]:
    """HTML do guia de classe do GMO -> (skills, textos não mapeados). `stage` = "class" (tabela principal) ou
    "enhanced" (4ª e 5ª classe)."""
    tree = LexborHTMLParser(html)
    skills, unmapped, seen = [], [], set()
    for t_index, table in enumerate(tree.css("table.cSk")):
        rows = table.css("tr")
        if not rows:
            continue
        head = [COLUMNS.get(clean(c.text()).lower()) for c in rows[0].css("th")]
        for tr in rows[1:]:
            cells = tr.css("td")
            if len(cells) != len(head):
                continue
            row = dict(zip(head, cells))
            name_cell = row.get("name")
            if name_cell is None:
                continue
            bold = name_cell.css_first("b")
            name = clean((bold or name_cell).text())
            name = fix_name(name)
            weapon = any(clean(i.text()).lower() == "weapon" for i in name_cell.css("i"))
            req = {"level": None, "str": None, "agi": None, "vit": None, "ene": None, "cmd": None, "other": []}
            level = _value(row["level"].text()) if "level" in row else None
            req["level"] = _int(level) if level else None
            text = _value(row["requirements"].text()) if "requirements" in row else None
            for part in (p.strip() for p in (text or "").split(",") if p.strip()):
                if m := re.match(r"^([A-Z]{3})\s+(\d[\d,]*)$", part) if not part[0].isdigit() else None:
                    if m.group(1) in STATS:
                        req[STATS[m.group(1)]] = _int(m.group(2))
                        continue
                if part.isdigit() and req["other"] == [] and any(req[s] for s in STATS.values()):
                    continue   # "STR 1,045" partido na vírgula do milhar
                req["other"].append(part)
                unmapped.append(f"{name}: {part}")
            # "1,045" vira "1" + "045" no split acima: refaz os números a partir do texto inteiro.
            for stat, value in re.findall(r"\b([A-Z]{3})\s+(\d{1,3}(?:,\d{3})*)", text or ""):
                if stat in STATS:
                    req[STATS[stat]] = _int(value)
            req["other"] = [o for o in req["other"] if not re.fullmatch(r"\d{3}", o)]
            cost = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", row["cost"].text())] if "cost" in row else []
            skill = {
                "id": slugify(name.replace("’", "'")), "name": name, "stage": "class" if t_index == 0 else "enhanced",
                "unlocked_as": _value(row["unlocked_as"].text()) if "unlocked_as" in row else None,
                "mana_cost": cost[0] if cost else None, "ag_cost": cost[1] if len(cost) > 1 else None,
                "range": _int(_value(row["range"].text()) or "") if "range" in row else None,
                "base_dmg": _int(_value(row["base_dmg"].text()) or "") if "base_dmg" in row else None,
                "requirements": req, "learn": {"method": "weapon" if weapon else None, "item_name": None},
            }
            if skill["id"] in seen or not name:
                continue
            seen.add(skill["id"])
            skills.append(skill)
    unmapped = [u for u in unmapped if not re.search(r": \d{3}$", u)]
    return skills, unmapped
