"""Árvore de skills dos guias de classe do Fanz (/guide/characters/<classe>/, data/raw/fanz/tools/class-<chave>.html,
baixados por `python -m scrapers.planner fetch`).

Estrutura real (out/2026): seções "Basic Skill Tree" e "Special Skill Tree"; cada skill é um
`<div id="skill_<b|s|m><nº>">` que só aparece quando a pessoa clica na imagem da árvore:
- `<text-subtitle>Nome</text-subtitle>`, a descrição em texto corrido e uma lista com o tipo ("ATK Skill",
  "Buff Skill"), os efeitos (lista interna), "Mana cost: N", "AG cost: N", "<Elemento> element" e "Imprint DMG: +N%";
- depois de `<hr />`, "Base Requirements:" e uma lista: "Skill Item: Orb of X" (ou "Item: ..."), "Character Level: Level N",
  "STR Level: Level N" / "AGI points: N", "Skill: X", "Master Skill: ...", "Weapon item with Skill option equipped.",
  "Mount: Dinorant with Skill option", "Only available in the Castle Siege mini-game."...
- `b` = árvore básica, `s` = especial (Castle Siege), `m` = skills de item ou montaria (aparecem na árvore básica).
Os guias de Gun Crusher, White Wizard e Mage ainda não têm a árvore (só um comentário no HTML).

Rótulo de requisito que não casa com nenhuma regra vai para `unmapped` (relatório), não para o registro.
"""
from __future__ import annotations

import html as htmllib
import re

from scrapers.common.html import clean
from scrapers.common.ids import slugify
from scrapers.common.parsing import find_updated_date

TREES = {"b": "basic", "s": "special", "m": "item"}
STAT_KEYS = {"str": "str", "strength": "str", "agi": "agi", "agility": "agi", "sta": "vit", "stamina": "vit", "vit": "vit",
             "vitality": "vit", "ene": "ene", "energy": "ene", "cmd": "cmd", "com": "cmd", "command": "cmd"}
ELEMENTS = {"fire", "water", "earth", "wind", "darkness", "light", "lightning", "ice", "poison"}

_DIV = re.compile(r'<div id="skill_([bsm])(\d+)">(.*?)</div>', re.S)
_LI = re.compile(r"<li>(.*?)(?=<li>|</li>|<ul>|</ul>)", re.S)
# Prévia animada da skill (GIF/JPG) que o script mostra ao clicar na árvore; nem toda skill tem.
_PREVIEW = re.compile(r"getElementById\('skill_([bsm]\d+)'\)\.style\.display='block';\s*\w+\[0\]\.innerHTML=\s*'<img src=\"([^\"]+)\"", re.S)


def _text(fragment: str) -> str:
    return clean(htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment)))


def _items(fragment: str) -> list[str]:
    """Textos dos <li> na ordem, inclusive os das listas internas (o HTML do Fanz não fecha as listas direito)."""
    return [t for t in (_text(m.group(1)) for m in _LI.finditer(fragment)) if t]


def _int(text: str) -> int | None:
    m = re.search(r"\d[\d,]*", text)
    return int(m.group(0).replace(",", "")) if m else None


def parse_requirement(line: str, skill: dict) -> bool:
    """Aplica uma linha de "Base Requirements" ao registro. Devolve False quando a linha não casa com nenhuma regra."""
    req, learn = skill["requirements"], skill["learn"]
    text = line.rstrip(".")
    if m := re.match(r"^(?:Skill )?Item:\s*(.+)$", text, re.I):
        name = m.group(1).strip()
        if re.search(r"\bweapon\b.*\bSkill option\b", name, re.I):
            learn["method"] = "weapon"
            req["other"].append(line)
        else:
            learn.update(method="item", item_name=name)
        return True
    if re.match(r"^(Weapon|Shield) item with Skill option", text, re.I):
        learn["method"] = "weapon"
        return True
    if m := re.match(r"^(?:Mount|Pet Item):\s*(.+)$", text, re.I):
        learn["method"] = "mount"
        req["other"].append(line)
        return True
    if re.search(r"Castle Siege", text, re.I):
        learn["method"] = "castle-siege"
        return True
    if re.match(r"^No requirements$", text, re.I):
        return True
    if m := re.match(r"^Character Level:?\s*(?:Level\s*)?(\d[\d,]*)$", text, re.I):
        req["level"] = _int(m.group(1))
        return True
    stat = r"(STR|AGI|STA|VIT|ENE|CMD|COM|Strength|Agility|Stamina|Vitality|Energy|Command)"
    if m := re.match(rf"^{stat}(?:\s+(?:Level|points?))?:?\s*(?:Level\s*)?(\d[\d,]*|\?)$", text, re.I):
        if m.group(2) == "?":
            req["other"].append(line)
        else:
            req[STAT_KEYS[m.group(1).lower()]] = _int(m.group(2))
        return True
    if re.search(r"Master Skill Points", text, re.I):
        if learn["method"] is None:
            learn["method"] = "master"
        req["other"].append(line)
        return True
    if re.match(r"^(Skill|Master Skill|Character Class|Quest):", text, re.I) or re.search(
            r"\b(Strengthener|Mastery|Proficiency|Power Up\(\d\))\b.*\b(Level|Lv)\s*\d+\)?$|^Master Skill Rank|"
            r"\bitem (mounted|equipped)$", text, re.I):
        req["other"].append(line)
        if re.match(r"^Master Skill:\s*Rank", text, re.I) and learn["method"] is None:
            learn["method"] = "master"
        if re.match(r"^Quest:", text, re.I) and learn["method"] is None:
            learn["method"] = "quest"
        return True
    return False


def parse_skill(tree: str, number: str, body: str) -> tuple[dict, list[str]]:
    name_match = re.search(r"<text-subtitle>(.*?)</text-subtitle>", body, re.S)
    name = _text(name_match.group(1)) if name_match else ""
    rest = body[name_match.end():] if name_match else body
    effects_html, _, req_html = rest.partition("<hr")
    head = effects_html.split("<ul>", 1)[0]
    # Layout do guia do MG: "<em><strong>ATK Skill</strong></em><br /><em>descrição</em>".
    kind_match = re.search(r"<strong>\s*((?:ATK|WIZ|Curse|Non-ATK|Buff|Debuff|Passive|Summon) Skill)\s*</strong>", head, re.I)
    if kind_match:
        head = head.replace(kind_match.group(0), "")
    description = _text(head)
    skill = {
        "id": slugify(name.replace("’", "'")), "name": name, "tree": TREES[tree], "kind": None, "description": description or None,
        "effects": [], "mana_cost": None, "ag_cost": None, "element": None, "imprint_dmg_pct": None,
        "requirements": {"level": None, "str": None, "agi": None, "vit": None, "ene": None, "cmd": None, "other": []},
        "learn": {"method": None, "item_name": None}, "slot": f"{tree}{number}",
    }
    kinds = {"atk": "attack", "wiz": "attack", "curse": "attack", "comb": "combo", "non-atk": "utility"}
    if kind_match:
        word = kind_match.group(1).rsplit(" ", 1)[0].lower()
        skill["kind"] = kinds.get(word, word)
    for line in _items(effects_html):
        if m := re.match(r"^(ATK|WIZ|Curse|Non-ATK|Buff|Debuff|Passive|Summon|Comb)\s+Skill:?$", line, re.I):
            skill["kind"] = skill["kind"] or kinds.get(m.group(1).lower(), m.group(1).lower())
        elif line == name and name.startswith("Summon "):   # summons do Elf: "Summon Goblin" no lugar do tipo
            skill["kind"] = skill["kind"] or "summon"
        elif m := re.match(r"^Mana cost:\s*(\d[\d,]*)", line, re.I):
            skill["mana_cost"] = _int(m.group(1))
        elif m := re.match(r"^AG cost:\s*(\d[\d,]*)", line, re.I):
            skill["ag_cost"] = _int(m.group(1))
        elif m := re.match(r"^(\w+) element$", line, re.I):
            skill["element"] = m.group(1).lower() if m.group(1).lower() in ELEMENTS else None
        elif re.match(r"^Non-element$", line, re.I):
            skill["element"] = "none"
        elif m := re.match(r"^Imprint (?:DMG|Bonus):\s*\+?(\d+)%", line, re.I):
            skill["imprint_dmg_pct"] = int(m.group(1))
        else:
            skill["effects"].append(line)
    # Guia do MG: "This skill can be learned via <strong>Scroll of Poison</strong>." e a lista "Prerequisites:".
    if via := re.search(r"learned (?:via|by using|with)\s*<strong>(.*?)</strong>", req_html, re.I | re.S):
        if re.search(r"Master Skill", via.group(1), re.I):
            skill["learn"]["method"] = "master"
        else:
            skill["learn"].update(method="item", item_name=_text(via.group(1)))
    elif re.search(r"Skill option", _text(req_html.split("<ul>", 1)[0]), re.I):
        skill["learn"]["method"] = "weapon"
    unmapped = []
    for line in _items(req_html.partition("Base Requirements")[2] or req_html):
        if not parse_requirement(line, skill):
            unmapped.append(line)
            skill["requirements"]["other"].append(line)
    return skill, unmapped


def parse_class_skills(html: str) -> tuple[list[dict], list[str]]:
    """HTML do guia de classe -> (skills na ordem da árvore, linhas de requisito não mapeadas)."""
    previews = {sid: url.replace("http://", "https://") for sid, url in _PREVIEW.findall(html)}
    skills, unmapped, seen = [], [], set()
    for tree, number, body in _DIV.findall(html):
        if "<text-subtitle>" not in body:
            continue
        skill, lines = parse_skill(tree, number, body)
        skill["preview_url"] = previews.get(f"{tree}{number}")
        if not skill["name"] or skill["id"] in seen:
            continue
        seen.add(skill["id"])
        skills.append(skill)
        unmapped += [f"{skill['name']}: {x}" for x in lines]
    return skills, unmapped


def page_updated_at(html: str) -> str | None:
    m = re.search(r"Page updated ([A-Z][a-z]+ \d{1,2}, \d{4})", html)
    return find_updated_date([f"Page updated {m.group(1)}"]) if m else None
