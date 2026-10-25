"""Skills das páginas de classe do guia (/characters/<classe>): JSON em string literal de um chunk JS.

Estrutura real (out/2026, chunk 2044): lista com uma entrada por skill:
`nombre`, `imagenFirebase` (ícone .webp no Firebase Storage do site), `equipado` (classes que usam; "Lemuria" = Mage,
"Rune Wizard" = Rune Mage), `redireccion` (endereços /characters/<...>), `requirestats` (["Strength: 100",
"Agility: 380"], "Not Required"), `requirelevel` (0 = sem nível), `requireskill` (skill anterior),
`masterskilltree` ("Bat Flock Mastery 10 Points"), `propiedadesskill` (["Mana 20 / AG 5", "Range 6",
"Basic Skill Damage 90 (Elemental Imprint Bonus 100%)", "Range 6 / Cooldown: 5 sec", "Non-element"]), `descripcion`,
`typeSkill` (acquired = aprendida com item, weapon, master, pet, default, quest) e `castlesiege`.

Árvore de melhorias da 4ª classe (chunk 5606): uma entrada por nó (`nombre`, `imagen`, `equipado`, `requirements`,
`description`, `niveles` por ponto, `pagina`); ficam só os nós que são skills ("Multi-Shot Enhancement Skill",
"Bat Flock Enhancement"). Os ícones da árvore vêm do próprio chunk (static/media/<nome>.<hash>.webp).
"""
from __future__ import annotations

import json
import re

from scrapers.common.ids import slugify
from scrapers.guidemu.bundle import js_strings

BASE = "https://guidemuonline.com"
STATS = {"strength": "str", "agility": "agi", "stamina": "vit", "vitality": "vit", "energy": "ene", "command": "cmd"}
TYPES = {"acquired": "item", "weapon": "weapon", "master": "master", "pet": "mount", "default": "default", "quest": "quest"}


def skill_list(text: str, marker: str) -> list[dict]:
    """Primeira lista JSON do chunk que tem `marker` em todas as entradas."""
    for s in js_strings(text):
        if s.startswith("[{") and marker in s:
            try:
                data = json.loads(s)
            except ValueError:
                continue
            if data and all(marker in d for d in data if isinstance(d, dict)):
                return data
    return []


def _int(text: str) -> int | None:
    m = re.search(r"\d[\d,]*", text or "")
    return int(m.group(0).replace(",", "")) if m else None


def parse_properties(props: list[str]) -> dict:
    """["Mana 20 / AG 5", "Range 6 / Cooldown: 5 sec", "Basic Skill Damage 90 (Elemental Imprint Bonus 100%)"] -> campos."""
    out = {"mana_cost": None, "ag_cost": None, "range": None, "cooldown_s": None, "base_dmg": None, "imprint_dmg_pct": None,
           "element": None}
    for prop in props:
        for part in (p.strip() for p in prop.split("/")):
            if m := re.fullmatch(r"Mana (\d+)", part):
                out["mana_cost"] = int(m.group(1))
            elif m := re.fullmatch(r"AG (\d+)", part):
                out["ag_cost"] = int(m.group(1))
            elif m := re.fullmatch(r"Range (\d+)", part):
                out["range"] = int(m.group(1))
            elif m := re.fullmatch(r"Cooldown: ([\d.]+) sec", part):
                out["cooldown_s"] = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
            elif m := re.fullmatch(r"Basic Skill Damage (\d+)(?: \(Elemental Imprint Bonus (\d+)%\))?", part):
                out["base_dmg"] = int(m.group(1))
                out["imprint_dmg_pct"] = int(m.group(2)) if m.group(2) else None
            elif part == "Non-element":
                out["element"] = "none"
    return out


def parse_skills(text: str, class_ids: dict[str, str], fetched_at: str | None) -> list[dict]:
    """JSON de skills do chunk -> registros (um por skill; `classes` = ids das classes do site)."""
    out = []
    for d in skill_list(text, "typeSkill"):
        names = [c for c in (d.get("equipado") or []) if c]
        classes = [class_ids[c] for c in names if c in class_ids]
        name = (d.get("nombre") or "").strip()
        if not name or not classes:
            continue
        req = {"level": d.get("requirelevel") or None, "str": None, "agi": None, "vit": None, "ene": None, "cmd": None}
        for line in d.get("requirestats") or []:
            if m := re.fullmatch(r"(\w+): ([\d,]+)", line.strip()):
                if m.group(1).lower() in STATS:
                    req[STATS[m.group(1).lower()]] = _int(m.group(2))
        slug = (d.get("redireccion") or [""])[0]
        out.append({
            "name": name, "classes": classes, "image_url": d.get("imagenFirebase") or None,
            "requirements": req, "require_skill": (d.get("requireskill") or "").strip() or None,
            "master_tree": (d.get("masterskilltree") or "").strip() or None,
            **parse_properties(d.get("propiedadesskill") or []),
            "description": (d.get("descripcion") or "").strip() or None,
            "type": TYPES.get(d.get("typeSkill") or ""), "castle_siege": bool(d.get("castlesiege")),
            "season": None, "source": "guidemu", "source_url": f"{BASE}/characters/{slug}" if slug else BASE,
            "scraped_at": fetched_at,
        })
    return out


def media_urls(text: str) -> dict[str, str]:
    """Ícones do chunk: 'BatFlockEnhancement' -> URL de static/media/BatFlockEnhancement.<hash>.webp."""
    return {m.group(1): f"{BASE}/{m.group(0)}" for m in re.finditer(r"static/media/([A-Za-z0-9]+)\.[0-9a-f]{8,}\.(?:webp|png|gif)", text)}


def parse_enhancements(text: str, class_ids: dict[str, str], known: dict[str, set[str]], fetched_at: str | None) -> list[dict]:
    """Árvore de melhorias (4ª classe): só os nós que são skills da classe ("<skill> Enhancement Skill" ou
    "<skill> Enhancement", com <skill> uma skill da classe). `known`: classe -> nomes de skill (minúsculos)."""
    icons = media_urls(text)
    out, seen = [], set()
    for d in skill_list(text, "pagina"):
        cls = class_ids.get(d.get("equipado") or "")
        name = (d.get("nombre") or "").strip()
        m = re.fullmatch(r"(.+?) Enhancement(?: Skill)?", name)
        if not cls or not m or (cls, name) in seen:
            continue
        if not name.endswith("Enhancement Skill") and m.group(1).lower() not in known.get(cls, set()):
            continue
        seen.add((cls, name))
        reqs = [r.strip() for r in d.get("requirements") or [] if r.strip()]
        out.append({
            "name": name, "classes": [cls], "base_skill": m.group(1), "image_url": icons.get(d.get("imagen") or ""),
            "requirements_text": reqs, "description": (d.get("description") or "").strip() or None,
            "levels": [str(x) for x in d.get("niveles") or []],
            "season": None, "source": "guidemu", "source_url": f"{BASE}/characters/{slugify(d.get('equipado') or '')}",
            "scraped_at": fetched_at,
        })
    return out
