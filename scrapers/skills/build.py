"""Skills de cada classe -> data/processed/<conjunto>/skills.json (só no conjunto combined: Fanz e GMO).

    python -m scrapers.skills [--set combined]

Fontes (já em data/raw/, nenhuma requisição aqui):
- Fanz: árvore de skills dos guias de classe (10 classes; jogo oficial). Base de cada classe que ele cobre.
- GMO: tabelas de skills dos guias de classe (16 classes; servidor S21). Para Gun Crusher, White Wizard, Mage,
  Illusion Knight, Alchemist e Crusader (o Fanz não tem a árvore) e, nas outras, só as skills que o Fanz não traz
  (melhorias da 4ª classe, skills da 5ª, Dex Booster...). Registros do GMO levam `season: "S21"`.

Como aprender (`learn`): item (orb, scroll, livro), arma/escudo com a opção Skill, montaria, árvore de mestre, quest ou
Castle Siege. O item que o guia cita é ligado ao item do site (`item_id`): pelo nome, por grafias conhecidas
("Summoning Scroll" = Summon Scroll) e pelas variantes do cruzamento ("Scroll of X" = "X Book" no Rune Wizard). Nas
classes que só o GMO cobre, o item vem do nome da skill ("Orb of Ice Break"), só quando o item é da própria classe.
Item que o site não tem, mas que aparece nas listas de drop do GMO ("Shining Bird Law Book"), guarda os drops ali
mesmo (`learn.drops`: monstro e mapa). Onde dropa o item do site sai do drops.json, no build do site.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from scrapers.combine import gmo_drop_map_id, item_resolver, skill_item_names
from scrapers.common.html import absolute_url
from scrapers.common.ids import slugify
from scrapers.common.model import REPO_ROOT, validate
from scrapers.common.storage import dump_records
from scrapers.planner.build import CLASSES, GMO_KEYS
from scrapers.skills import fanz as fanz_parser
from scrapers.skills import gmo as gmo_parser

log = logging.getLogger("scrapers.skills")

FANZ_GUIDES = {class_id: key for class_id, _, key, _, _ in CLASSES}
# Skill do GMO que é a mesma do Fanz com o nome do cliente novo (mesmos requisitos ou nível).
GMO_TO_FANZ = {
    "swordfury": "swordfurymastery", "strongbelief": "firmbelief", "solidprotection": "strongblessing",
    "angerstrike": "ragefulblow", "electricspike": "electricspark", "dignity": "increasecriticaldamage",
}
# Buff de experiência do servidor (todas as classes, nível 50): não é skill de classe.
GMO_SKIP = {"blessingofexperience"}
# Skill do GMO que é a mesma do guia oficial com outra grafia.
GMO_TO_GUIDE = {"angerstrike": "ragefulblow", "dignity": "criticaldamageincrease", "electricspike": "electricspark",
                "beginnerbless": "basicbless", "beginnerbasicdefenseimprovement": "basicdefenseincrease",
                "beginnerattackpowerimprovement": "basicattackincrease", "beginnerrecovery": "basicrecovery"}
# Nome do item no guia -> nome do item no site, quando não basta trocar a ordem das palavras.
ITEM_ALIASES = {
    "Summoning Scroll": "Summon Scroll",
    "Scroll of Wizardry Expansion": "Scroll of Wizardry Enhance",   # Expansion of Wizardry, ENE 1058 nos dois
    "Scroll of Blast": "Scroll of Comet Fall",   # Comet Fall se chamava Blast; o guia do MG cita "Scroll of Cometfall"
}
# Classes que só o GMO cobre: skill -> item, quando o nome do item não repete o da skill.
SKILL_ITEMS = {("gun-crusher", "deathfire"): "Orb of Fire Death"}
SKILL_ITEM_FORMS = ("Orb of {}", "Scroll of {}", "{} Book", "{} Parchment", "Parchment of {}", "{} Scroll",
                    "Crystal of {}", "{} Bead", "{} Act", "{} Law Book")
# Nas listas do GMO só valem as formas que não se confundem com arma ("Lightning Book" é o livro do set Lightning).
GMO_ONLY_FORMS = ("{} Bead", "{} Act", "{} Law Book", "Orb of {}", "Scroll of {}", "{} Parchment")


def key(name: str) -> str:
    """'Sword’s Fury' -> 'swordfury', 'Alchemy: Angel Homunculus' -> 'angelhomunculus' (compara nomes das fontes)."""
    name = re.sub(r"^alchemy:\s*", "", name.lower())
    return re.sub(r"[^a-z0-9]", "", name.replace("’", "'").replace("'s ", " "))


def skill_slug(name: str) -> str:
    """Endereço da skill: "Sword's Fury" -> "swords-fury", "Luguard’s Protection: Punishment" -> "luguards-protection-punishment"."""
    return slugify(name.replace("’", "'").replace("'", ""))


def _meta(path: Path) -> dict:
    meta = path.with_name(path.stem + ".meta.json")
    return json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}


# Nome no Fanz -> nome no guia oficial (o mesmo skill com o nome do cliente atual).
FANZ_TO_GUIDE = {
    "swordfurymastery": "swordfury", "firmbelief": "strongbelief", "strongblessing": "solidprotection",
    "increasecriticaldamage": "criticaldamageincrease",
}


def _empty(name: str) -> dict:
    return {"id": slugify(name.replace("’", "'")), "name": name, "aliases": [], "tree": None, "stage": "class",
            "unlocked_as": None, "kind": None, "description": None, "effects": [], "mana_cost": None, "ag_cost": None,
            "range": None, "cooldown_s": None, "base_dmg": None, "element": None, "imprint_dmg_pct": None,
            "requirements": {"level": None, "str": None, "agi": None, "vit": None, "ene": None, "cmd": None, "other": []},
            "learn": {"method": None, "item_name": None}, "levels": [], "image_url": None, "preview_url": None, "slot": None}


def from_guide(g: dict, fanz: dict | None) -> dict:
    """Skill do guia oficial (requisitos, custos, ícone e tipo atuais) completada pelo Fanz (item, efeitos, elemento,
    descrição já traduzida)."""
    rec = _empty(g["name"])
    req = {k: g["requirements"].get(k) for k in ("level", "str", "agi", "vit", "ene", "cmd")}
    other = ([f"Skill: {g['require_skill']}"] if g.get("require_skill") else []) + \
            ([f"Master Skill: {g['master_tree']}"] if g.get("master_tree") else [])
    method = "castle-siege" if g.get("castle_siege") else g.get("type")
    rec.update({k: g.get(k) for k in ("mana_cost", "ag_cost", "range", "cooldown_s", "base_dmg", "imprint_dmg_pct",
                                      "element", "description", "image_url")})
    rec.update(requirements={**req, "other": other}, learn={"method": method, "item_name": None},
               season=g.get("season"), source="guidemu", source_url=g.get("source_url"), scraped_at=g.get("scraped_at"),
               page_updated_at=None)
    if fanz:
        if fanz["name"] != g["name"]:
            rec["aliases"] = [fanz["name"]]
        rec.update(tree=fanz["tree"], kind=fanz["kind"], effects=fanz["effects"], slot=fanz["slot"],
                   preview_url=fanz.get("preview_url"), element=fanz["element"] or rec["element"],
                   imprint_dmg_pct=rec["imprint_dmg_pct"] or fanz["imprint_dmg_pct"],
                   mana_cost=rec["mana_cost"] if rec["mana_cost"] is not None else fanz["mana_cost"],
                   ag_cost=rec["ag_cost"] if rec["ag_cost"] is not None else fanz["ag_cost"])
        # Descrição: a do Fanz (oficial, já com tradução nossa); a do guia fica quando o Fanz não tem.
        rec["description"] = fanz["description"] or rec["description"]
        if not any(req.values()) and not other:   # o guia não diz requisito: os do Fanz
            rec["requirements"] = fanz["requirements"]
        if fanz["learn"]["item_name"]:
            rec["learn"] = {"method": "item", "item_name": fanz["learn"]["item_name"]}
        elif rec["learn"]["method"] is None:
            rec["learn"] = fanz["learn"]
    return rec


def fill_from_gmo(rec: dict, gmo: dict | None) -> dict:
    """Skill do guia oficial sem requisito (nem no Fanz), como as do Illusion Knight: requisitos e custos que faltam vêm
    da tabela do GMO, e a skill ganha `season: "S21"` (o site avisa que os requisitos são da Season 21)."""
    req = rec["requirements"]
    if gmo is None or any(req[k] is not None for k in ("level", "str", "agi", "vit", "ene", "cmd")) or req["other"]:
        return rec
    if not any(gmo["requirements"][k] is not None for k in ("level", "str", "agi", "vit", "ene", "cmd")):
        return rec
    rec["requirements"] = {**gmo["requirements"], "other": list(gmo["requirements"]["other"])}
    for k in ("mana_cost", "ag_cost", "range"):
        if rec[k] is None:
            rec[k] = gmo.get(k)
    rec["season"] = gmo_parser.SEASON
    return rec


def from_tree(t: dict) -> dict:
    """Skill da árvore de melhorias da 4ª classe (guia oficial): melhora uma skill da classe com pontos da árvore."""
    rec = _empty(t["name"])
    rec.update(stage="enhanced", description=t.get("description"), image_url=t.get("image_url"), levels=t.get("levels") or [],
               requirements={**rec["requirements"], "other": t.get("requirements_text") or []},
               learn={"method": "enhance-tree", "item_name": None},
               season=None, source="guidemu", source_url=t.get("source_url"), scraped_at=t.get("scraped_at"), page_updated_at=None)
    return rec


def load_class_skills(raw: Path, guide: list[dict] | None = None, tree: list[dict] | None = None) -> tuple[dict[str, list[dict]], list[str]]:
    """Skills por classe (ordem do planner), já com procedência. Ordem das fontes: guia oficial (Guide MU Online), Fanz
    (skills que o guia não lista, como Impale e Combo), árvore de melhorias da 4ª classe (guia) e, por último, o GMO:
    a classe inteira quando nenhuma outra fonte a cobre (White Wizard, Crusader) e, nas outras, só as skills que faltam
    (Dex Booster, Raining Arrow, Crown Force...). Devolve também as linhas de requisito não mapeadas."""
    guide, tree = guide or [], tree or []
    out: dict[str, list[dict]] = {}
    unmapped: list[str] = []
    for class_id, _, fanz_key, _, _ in CLASSES + [(c, None, None, None, None) for c in GMO_KEYS if c not in FANZ_GUIDES]:
        fanz: list[dict] = []
        fanz_path = raw / "fanz" / "tools" / f"class-{fanz_key}.html" if fanz_key else None
        if fanz_path and fanz_path.exists():
            html = fanz_path.read_text(encoding="utf-8", errors="replace")
            meta = _meta(fanz_path)
            found, lines = fanz_parser.parse_class_skills(html)
            unmapped += [f"fanz/{class_id}: {x}" for x in lines]
            prov = {"season": None, "source": "fanz", "source_url": meta.get("url"), "scraped_at": meta.get("fetched_at"),
                    "page_updated_at": fanz_parser.page_updated_at(html)}
            for f in found:
                preview = absolute_url(meta.get("url") or "", f["preview_url"]) if f.get("preview_url") else None
                fanz.append({**_empty(f["name"]), **f, "preview_url": preview, **prov})
        by_key = {FANZ_TO_GUIDE.get(key(f["name"]), key(f["name"])): f for f in fanz}
        gmo_path = raw / "gmo" / "guides" / f"{GMO_KEYS[class_id]}.html"
        gmo_found: list[dict] = []
        if gmo_path.exists():
            gmo_found, lines = gmo_parser.parse_class_skills(gmo_path.read_text(encoding="utf-8", errors="replace"))
            unmapped += [f"gmo/{class_id}: {x}" for x in lines]
        gmo_by_key = {GMO_TO_GUIDE.get(key(s["name"]), key(s["name"])): s for s in gmo_found if s["stage"] == "class"}
        skills: list[dict] = []
        for g in (g for g in guide if class_id in g["classes"]):
            f = by_key.pop(key(g["name"]), None)
            skills.append(fill_from_gmo(from_guide(g, f), gmo_by_key.get(key(g["name"]))))
        used = {id(f) for f in by_key.values()}
        skills += [f for f in fanz if id(f) in used]          # do Fanz e não do guia (ex.: Impale, Combo)
        enhanced = [from_tree(t) for t in tree if class_id in t["classes"]]
        skills += enhanced
        if gmo_found:
            meta = _meta(gmo_path)
            known = {key(s["name"]) for s in skills} | {key(a) for s in skills for a in s["aliases"]}
            prov = {"season": gmo_parser.SEASON, "source": "gmo", "source_url": meta.get("url"),
                    "scraped_at": meta.get("fetched_at"), "page_updated_at": None}
            for s in gmo_found:
                k = key(s["name"])
                if k in GMO_SKIP or k in known or GMO_TO_FANZ.get(k) in known or GMO_TO_GUIDE.get(k) in known:
                    continue
                if s["stage"] == "enhanced" and enhanced:   # a árvore oficial já descreve as melhorias
                    continue
                known.add(k)
                skills.append({**_empty(s["name"]), **s, **prov})
        if skills:
            out[class_id] = skills
    return out, unmapped


def class_names(planner: dict) -> dict[str, set[str]]:
    """Classe -> nomes da classe e das evoluções (para conferir as classes que podem usar um item)."""
    names: dict[str, set[str]] = {}
    for ruleset in planner.get("rulesets", []):
        for c in ruleset["classes"]:
            names.setdefault(c["id"], set()).update(c.get("names", []), [e["name"] for e in c.get("evolutions", [])])
    return names


def gmo_item_drops(lists: list[dict], monsters: list[dict], maps: list[dict]) -> dict[str, list[dict]]:
    """Nome do item (chave) -> [{monster_id, map_id}] nas listas de drop do GMO, com os ids do site."""
    by_slug = {m["id"]: m["id"] for m in monsters}
    by_slug.update({slugify(m["name"]): m["id"] for m in monsters})
    known_maps = {m["id"] for m in maps}
    out: dict[str, list[dict]] = {}
    for lst in lists:
        map_id = gmo_drop_map_id(lst.get("map_name") or "", known_maps)
        for monster in lst["monsters"]:
            slug = slugify(monster["name"])
            mid = by_slug.get(slug) or by_slug.get(re.sub(r"-?\d+$", "", slug))
            if mid is None:
                continue
            for name in monster["items"]:
                rows = out.setdefault(key(name), [])
                if not any(r["monster_id"] == mid and r["map_id"] == map_id for r in rows):
                    rows.append({"monster_id": mid, "map_id": map_id})
    return out


def link_items(skills: dict[str, list[dict]], items: list[dict], names: dict[str, set[str]],
               gmo_drops: dict[str, list[dict]], gmo_names: dict[str, str]) -> None:
    """Preenche learn.item_id (item do site) ou learn.drops (só nas listas do GMO)."""
    resolve = item_resolver(items)
    by_id = {i["id"]: i for i in items}

    def site_item(name: str) -> dict | None:
        for candidate in (ITEM_ALIASES.get(name, name), *skill_item_names(name)):
            if (found := resolve(candidate)) is not None:
                return found
        # "Scroll of Magic Arrow" (guia do Fanz) = "Magic Arrow Book" (item do Rune Wizard no MuEmu)
        if m := re.match(r"^Scroll of (.+)$", name):
            return resolve(f"{m.group(1)} Book")
        return None

    fanz_items = {s["learn"]["item_name"] for rows in skills.values() for s in rows if s["learn"]["item_name"]}
    for class_id, rows in skills.items():
        own = names.get(class_id, set())
        for s in rows:
            learn = s["learn"]
            learn.setdefault("item_id", None)
            learn.setdefault("drops", [])
            if learn["item_name"]:
                found = site_item(learn["item_name"])
                learn["item_id"] = found["id"] if found else None
                if found is None and (drops := gmo_drops.get(key(learn["item_name"]))):
                    learn["drops"] = drops
                continue
            if s["source"] == "fanz" or learn["method"] not in (None, "item"):
                continue
            # Classes sem o guia do Fanz: item com o nome da skill, só se o site diz que é da própria classe
            # (itens de outras classes com o mesmo nome, como Scroll of Lightning do DW, ficam de fora).
            skill_key = key(s["name"])
            candidates = [SKILL_ITEMS[(class_id, skill_key)]] if (class_id, skill_key) in SKILL_ITEMS else []
            candidates += [form.format(s["name"]) for form in SKILL_ITEM_FORMS]
            for name in candidates:
                found = resolve(name)
                if found is not None and own & set(by_id[found["id"]].get("classes") or []) and name not in fanz_items:
                    learn.update(method="item", item_name=found["name"], item_id=found["id"])
                    break
            for name in [form.format(s["name"]) for form in GMO_ONLY_FORMS] if len(s["name"].split()) > 1 else []:
                if learn["item_id"] is None and resolve(name) is None and (drops := gmo_drops.get(key(name))):
                    learn.update(method="item", item_name=gmo_names.get(key(name), name), drops=drops)
                    break
    # Skill que o guia oficial lista para várias classes (Fire Ball: DW, MG, Summoner, Rune Wizard, Mage, Alchemist): a
    # classe sem item conhecido mostra o item da mesma skill em outra classe, dizendo de qual (`item_from_class`).
    shared: dict[str, tuple[str, dict]] = {}
    for class_id, rows in skills.items():
        for s in rows:
            if s["learn"].get("item_id") and s["source"] == "guidemu":
                shared.setdefault(key(s["name"]), (class_id, s["learn"]))
    for class_id, rows in skills.items():
        for s in rows:
            learn = s["learn"]
            learn.setdefault("item_from_class", None)
            if learn["method"] == "item" and not learn.get("item_id") and not learn["drops"] and key(s["name"]) in shared:
                other, src = shared[key(s["name"])]
                if other != class_id:
                    learn.update(item_name=src["item_name"], item_id=src["item_id"], item_from_class=other)


def build(data_dir: Path, folder: Path) -> tuple[list[dict], list[str]]:
    raw = data_dir / "raw"
    load = lambda path: json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    guide_dir = data_dir / "processed" / "guidemu"
    skills, unmapped = load_class_skills(raw, load(guide_dir / "skills.json"), load(guide_dir / "skill_tree.json"))
    planner = load(data_dir / "curated" / "planner.json") or {}
    lists = load(data_dir / "processed" / "gmo" / "drop_lists.json")
    gmo_names = {key(n): n for lst in lists for m in lst["monsters"] for n in m["items"]}
    link_items(skills, load(folder / "items.json"), class_names(planner),
               gmo_item_drops(lists, load(folder / "monsters.json"), load(folder / "maps.json")), gmo_names)
    out = []
    for class_id, rows in skills.items():
        seen: set[str] = set()
        for order, s in enumerate(rows):
            sid = skill_slug(s["name"])
            if sid in seen:
                continue
            seen.add(sid)
            record = {"id": f"{class_id}--{sid}", "skill_id": sid, "class_id": class_id, "order": order,
                      **{k: v for k, v in s.items() if k != "id"}}
            out.append(record)
    return out, unmapped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scrapers.skills", description="Skills de cada classe")
    parser.add_argument("--set", default="combined", help="conjunto em data/processed (padrão: combined)")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    folder = args.data_dir / "processed" / args.set
    if args.set != "combined":
        log.info("skills só no conjunto combined (Fanz e GMO); nada a fazer em %s", args.set)
        return 0
    skills, unmapped = build(args.data_dir, folder)
    errors = [f"{s['id']}: {e}" for s in skills for e in validate("skill", s)]
    dump_records(folder / "skills.json", skills)
    for line in unmapped:
        log.warning("requisito não mapeado: %s", line)
    for error in errors[:20]:
        log.error(error)
    learned = [s for s in skills if s["learn"]["method"] == "item"]
    log.info("%d skills de %d classes · %d com item (%d no site, %d só nas listas do GMO) · erros de schema: %d · %s",
             len(skills), len({s["class_id"] for s in skills}), len(learned),
             sum(1 for s in learned if s["learn"]["item_id"]), sum(1 for s in learned if s["learn"]["drops"]),
             len(errors), folder / "skills.json")
    return 1 if errors else 0
