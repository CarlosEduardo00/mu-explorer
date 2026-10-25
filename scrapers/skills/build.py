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
    """'Sword’s Fury' -> 'swordfury' (compara nomes das duas fontes)."""
    return re.sub(r"[^a-z0-9]", "", name.lower().replace("’", "'").replace("'s ", " "))


def _meta(path: Path) -> dict:
    meta = path.with_name(path.stem + ".meta.json")
    return json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}


def load_class_skills(raw: Path) -> tuple[dict[str, list[dict]], list[str]]:
    """Skills por classe (ordem do planner), já com procedência. Devolve também as linhas não mapeadas."""
    out: dict[str, list[dict]] = {}
    unmapped: list[str] = []
    for class_id, _, guide, _, _ in CLASSES + [(c, None, None, None, None) for c in GMO_KEYS if c not in FANZ_GUIDES]:
        skills: list[dict] = []
        fanz_path = raw / "fanz" / "tools" / f"class-{guide}.html" if guide else None
        if fanz_path and fanz_path.exists():
            html = fanz_path.read_text(encoding="utf-8", errors="replace")
            meta = _meta(fanz_path)
            found, lines = fanz_parser.parse_class_skills(html)
            unmapped += [f"fanz/{class_id}: {x}" for x in lines]
            prov = {"season": None, "source": "fanz", "source_url": meta.get("url"), "scraped_at": meta.get("fetched_at"),
                    "page_updated_at": fanz_parser.page_updated_at(html)}
            skills += [{**s, "stage": "class", "unlocked_as": None, "range": None, "base_dmg": None, **prov} for s in found]
        gmo_path = raw / "gmo" / "guides" / f"{GMO_KEYS[class_id]}.html"
        if gmo_path.exists():
            meta = _meta(gmo_path)
            found, lines = gmo_parser.parse_class_skills(gmo_path.read_text(encoding="utf-8", errors="replace"))
            unmapped += [f"gmo/{class_id}: {x}" for x in lines]
            known = {key(s["name"]) for s in skills}
            prov = {"season": gmo_parser.SEASON, "source": "gmo", "source_url": meta.get("url"),
                    "scraped_at": meta.get("fetched_at"), "page_updated_at": None}
            for s in found:
                k = key(s["name"])
                if k in GMO_SKIP or k in known or GMO_TO_FANZ.get(k) in known:
                    continue
                known.add(k)
                skills.append({**s, "tree": None, "kind": None, "description": None, "effects": [],
                               "element": None, "imprint_dmg_pct": None, "slot": None, **prov})
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
            if s["source"] != "gmo" or learn["method"] is not None:
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


def build(data_dir: Path, folder: Path) -> tuple[list[dict], list[str]]:
    raw = data_dir / "raw"
    load = lambda path: json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    skills, unmapped = load_class_skills(raw)
    planner = load(data_dir / "curated" / "planner.json") or {}
    lists = load(data_dir / "processed" / "gmo" / "drop_lists.json")
    gmo_names = {key(n): n for lst in lists for m in lst["monsters"] for n in m["items"]}
    link_items(skills, load(folder / "items.json"), class_names(planner),
               gmo_item_drops(lists, load(folder / "monsters.json"), load(folder / "maps.json")), gmo_names)
    out = []
    for class_id, rows in skills.items():
        for order, s in enumerate(rows):
            record = {"id": f"{class_id}--{s['id']}", "skill_id": s["id"], "class_id": class_id, "order": order,
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
