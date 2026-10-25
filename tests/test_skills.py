"""Skills por classe: guia oficial (JSON dos chunks do Guide MU Online em tests/fixtures/guidemu), árvore do guia de classe
do Fanz e tabela do guia do GMO (HTML real em tests/fixtures/skills e tests/fixtures/planner), o cruzamento das fontes e a
ligação de cada skill ao item que a ensina."""
from pathlib import Path

from scrapers.combine import item_resolver, match_items, muemu_skill_items, reordered_name, skill_item_names
from scrapers.common.model import validate
from scrapers.guidemu.parse import SKILL_CLASSES
from scrapers.guidemu.skills import parse_enhancements, parse_properties, parse_skills
from scrapers.skills import fanz, gmo
from scrapers.skills.build import fill_from_gmo, from_guide, from_tree, key, link_items, skill_slug

FIX = Path(__file__).parent / "fixtures"


def read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def by_name(skills: list[dict]) -> dict[str, dict]:
    return {s["name"]: s for s in skills}


def test_arvore_do_slayer():
    skills, unmapped = fanz.parse_class_skills(read("skills/fanz-class-slayer-skills.html"))
    assert unmapped == []
    names = [s["name"] for s in skills]
    assert names[:4] == ["Lunge", "Uppercut", "Cyclone", "Twisting Slash"]
    s = by_name(skills)
    bat = s["Bat Flock"]
    assert (bat["kind"], bat["element"], bat["mana_cost"], bat["ag_cost"], bat["imprint_dmg_pct"]) == ("attack", "darkness", 20, 5, 100)
    assert {k: v for k, v in bat["requirements"].items() if v} == {"level": 270, "str": 100, "agi": 380}
    assert bat["learn"] == {"method": "item", "item_name": "Orb of Bat Flock"}
    assert bat["description"].startswith("Summons a flock of bats")
    assert s["Pierce Attack"]["requirements"]["other"] == ["Skill: Bat Flock", "Master Skill: Bat Flock Mastery Level 10"]
    assert s["Lunge"]["learn"]["method"] == "weapon"
    assert s["Plasma Storm"]["learn"]["method"] == "mount" and s["Plasma Storm"]["tree"] == "item"
    assert s["Archangel's Will"]["learn"]["method"] == "weapon"
    assert s["Rush"]["learn"]["method"] == "master"
    assert (s["Crescent Moon Slash"]["tree"], s["Crescent Moon Slash"]["learn"]["method"]) == ("special", "castle-siege")


def test_arvore_do_mg_no_layout_antigo():
    skills, _ = fanz.parse_class_skills(read("skills/fanz-class-mg-skills.html"))
    s = by_name(skills)
    poison = s["Poison"]
    assert (poison["kind"], poison["imprint_dmg_pct"], poison["requirements"]["ene"]) == ("attack", 150, 140)
    assert poison["learn"] == {"method": "item", "item_name": "Scroll of Poison"}
    assert poison["description"] == "Deal poison damage to the target. It has a chance to deal additional poison damage over time."
    assert s["Defense"]["learn"]["method"] == "weapon"
    assert s["Blood Storm"]["learn"]["method"] == "master"   # "learned via Master Skill Tree" não é item
    assert "Fire Slash Strengthener (Lv 10)" in s["Fire Blood"]["requirements"]["other"]


def test_arvore_do_dk():
    skills, unmapped = fanz.parse_class_skills(read("skills/fanz-class-dk-skills.html"))
    s = by_name(skills)
    assert s["Swell Life"]["learn"]["item_name"] == "Swell Life Orb" and s["Swell Life"]["kind"] == "buff"
    assert "Base HP +12%" in s["Swell Life"]["effects"]
    assert s["Combo"]["kind"] == "combo" and s["Combo"]["learn"]["method"] is None
    assert s["Fire Blow"]["requirements"]["other"] == ["Death Stab Proficiency Lv 10"]
    assert s["Fire Blow"]["requirements"]["level"] == 400
    assert unmapped == []
    assert fanz.page_updated_at(read("skills/fanz-class-dk-skills.html")) == "2025-05-08"


def test_tabela_do_gmo():
    skills, unmapped = gmo.parse_class_skills(read("planner/gmo-crusader.html"))
    assert unmapped == []
    s = by_name(skills)
    assert "Holly Sweep" not in s   # erro de grafia corrigido
    sweep = s["Holy Sweep"]
    assert {k: v for k, v in sweep["requirements"].items() if v} == {"level": 50, "str": 420, "agi": 168}
    assert (sweep["stage"], sweep["unlocked_as"], sweep["mana_cost"], sweep["ag_cost"], sweep["base_dmg"]) == ("class", "Impact Crusader", 13, 1, 300)
    assert s["Sacred Impact"]["requirements"]["str"] == 1045   # "STR 1,045, AGI 418": milhar com vírgula
    assert s["Defense"]["learn"]["method"] == "weapon"
    assert s["Holy Sweep Enhancement Skill"]["stage"] == "enhanced"
    slayer, _ = gmo.parse_class_skills(read("skills/gmo-slayer.html"))
    assert by_name(slayer)["Lunge"]["learn"]["method"] == "weapon"
    assert by_name(slayer)["Bat Flock"]["requirements"]["agi"] == 380


def test_nomes_de_item_de_skill():
    assert reordered_name("Scroll of Fire Burst") == "Fire Burst Scroll"
    assert reordered_name("Healing Orb") == "Orb of Healing"
    assert reordered_name("Dragon Armor") is None
    assert "Orb of Sword Inertia" in skill_item_names("Sword Inertia Bead")
    assert "Magic Arrow Book" in skill_item_names("Magic Arrow Act")
    assert skill_item_names("Orb of Anger Blow")[0] == "Orb of Rageful Blow"
    assert key("Sword’s Fury") == key("Sword's Fury") == "swordfury"


def item(name: str, classes: list[str], group=None, index=None, source="fanz") -> dict:
    from scrapers.common.ids import slugify
    return {"id": slugify(name), "name": name, "classes": classes, "grade": None, "group": group, "index": index,
            "category": None, "durability": None, "requirements": {}, "stats": {}, "source": source}


def test_itens_de_skill_do_muemu_e_grafias_do_gmo():
    fanz_items = [item("Healing Orb", ["Fairy Elf"]), item("Fire Burst Scroll", ["Dark Lord"])]
    muemu = [item("Orb of Healing", ["Fairy Elf"], 12, 8, "muemu"), item("Scroll of Fire Burst", ["Dark Lord"], 12, 21, "muemu"),
             item("Orb of Sword Inertia", ["Slayer"], 12, 476, "muemu"), item("Orb of Summoning", ["Fairy Elf"], 12, 11, "muemu"),
             item("Seed Sphere (Fire)", ["Dark Wizard"], 12, 100, "muemu")]
    items, matches, _ = match_items(fanz_items, muemu)
    assert {m["fanz_id"]: m["muemu_id"] for m in matches} == {"healing-orb": "orb-of-healing", "fire-burst-scroll": "scroll-of-fire-burst"}
    assert items[0]["group"] == 12 and items[0]["index"] == 8
    extra = muemu_skill_items(items, muemu, matches)
    assert [i["name"] for i in extra] == ["Orb of Sword Inertia"]   # Orb of Summoning: o Fanz lista por monstro
    resolve = item_resolver(items + extra)
    assert resolve("Sword Inertia Bead")["id"] == "orb-of-sword-inertia"
    assert resolve("Scroll of FireBurst")["id"] == "fire-burst-scroll"


def skill(class_id: str, name: str, source: str, method=None, item_name=None) -> dict:
    return {"id": key(name), "name": name, "source": source, "learn": {"method": method, "item_name": item_name}}


def test_skill_aponta_para_o_item_e_os_drops():
    items = [item("Summon Scroll", ["Dark Lord"]), item("Orb of Ice Break", ["Gun Crusher"]),
             item("Scroll of Lightning", ["Dark Wizard"]), item("Magic Arrow Book", ["Rune Wizard"])]
    skills = {
        "dark-lord": [skill("dark-lord", "Summon", "fanz", "item", "Summoning Scroll")],
        "rune-mage": [skill("rune-mage", "Magic Arrow", "fanz", "item", "Scroll of Magic Arrow")],
        "gun-crusher": [skill("gun-crusher", "Ice Break", "gmo"), skill("gun-crusher", "Fixed Fire", "gmo")],
        "alchemist": [skill("alchemist", "Lightning", "gmo")],
        "white-wizard": [skill("white-wizard", "Shining Bird", "gmo")],
    }
    names = {"gun-crusher": {"Gun Crusher"}, "alchemist": {"Alchemist"}, "white-wizard": {"White Wizard"}}
    drops = {key("Shining Bird Law Book"): [{"monster_id": "lizard-warrior", "map_id": "lorencia"}]}
    link_items(skills, items, names, drops, {key("Shining Bird Law Book"): "Shining Bird Law Book"})
    assert skills["dark-lord"][0]["learn"]["item_id"] == "summon-scroll"
    assert skills["rune-mage"][0]["learn"]["item_id"] == "magic-arrow-book"
    assert skills["gun-crusher"][0]["learn"] == {"method": "item", "item_name": "Orb of Ice Break", "item_id": "orb-of-ice-break",
                                                 "drops": [], "item_from_class": None}
    assert skills["gun-crusher"][1]["learn"]["method"] is None
    assert skills["alchemist"][0]["learn"]["item_id"] is None   # Scroll of Lightning é do DW: não vale para o Alchemist
    ww = skills["white-wizard"][0]["learn"]
    assert (ww["item_name"], ww["item_id"], ww["drops"]) == ("Shining Bird Law Book", None, [{"monster_id": "lizard-warrior", "map_id": "lorencia"}])


def test_skill_de_varias_classes_usa_o_item_da_outra_classe():
    items = [item("Scroll of Fire Ball", ["Dark Wizard"])]
    skills = {"dark-wizard": [skill("dark-wizard", "Fire Ball", "guidemu", "item", "Scroll of Fire Ball")],
              "alchemist": [skill("alchemist", "Fire Ball", "guidemu", "item")]}
    link_items(skills, items, {"alchemist": {"Alchemist"}}, {}, {})
    learn = skills["alchemist"][0]["learn"]
    assert (learn["item_id"], learn["item_from_class"]) == ("scroll-of-fire-ball", "dark-wizard")
    assert skills["dark-wizard"][0]["learn"]["item_from_class"] is None


def guide_skills() -> dict[str, dict]:
    return by_name(parse_skills(read("guidemu/chunk-skills.js"), SKILL_CLASSES, "2026-10-25T16:28:00Z"))


def test_skills_do_guia_oficial():
    s = guide_skills()
    bat = s["Bat Flock"]
    assert bat["classes"] == ["slayer"] and bat["type"] == "item"
    assert {k: v for k, v in bat["requirements"].items() if v} == {"level": 270, "str": 100, "agi": 380}
    assert (bat["mana_cost"], bat["ag_cost"], bat["range"], bat["base_dmg"], bat["imprint_dmg_pct"]) == (20, 5, 6, 90, 100)
    assert bat["image_url"].startswith("https://firebasestorage.googleapis.com/") and bat["source_url"].endswith("/characters/slayer")
    assert s["Fire Ball"]["classes"] == ["dark-wizard", "magic-gladiator", "summoner", "rune-mage", "mage", "alchemist"]
    flare = s["Bursting Flare"]
    assert (flare["require_skill"], flare["master_tree"]) == ("Death Fire", "Death Fire Mastery 10 Points")
    assert s["Cyclone"]["type"] == "weapon" and s["Crescent Moon Slash"]["type"] == "default"
    assert s["Charge Slash"]["requirements"]["level"] is None   # o guia não traz requisitos do Illusion Knight
    assert parse_properties(["Range 6 / Cooldown: 1.5 sec", "Non-element"]) == {
        "mana_cost": None, "ag_cost": None, "range": 6, "cooldown_s": 1.5, "base_dmg": None, "imprint_dmg_pct": None, "element": "none"}


def test_arvore_de_melhorias_do_guia():
    tree = by_name(parse_enhancements(read("guidemu/chunk-skill-tree.js"), SKILL_CLASSES, {"slayer": {"bat flock"}}, None))
    assert set(tree) == {"Multi-Shot Enhancement Skill", "Bat Flock Enhancement", "Charge Slash Enhancement Skill"}
    bat = tree["Bat Flock Enhancement"]
    assert (bat["classes"], bat["base_skill"], bat["levels"][:3]) == (["slayer"], "Bat Flock", ["1", "2", "4"])
    assert bat["image_url"].startswith("https://guidemuonline.com/static/media/BatFlockEnhancement.")
    assert bat["requirements_text"] == ["Required Points: 1", "Bat Flock Mastery Master Skill 10 Point(s) required"]
    rec = from_tree(bat)
    assert (rec["stage"], rec["learn"]["method"], rec["requirements"]["other"][0]) == ("enhanced", "enhance-tree", "Required Points: 1")


def test_guia_oficial_completado_pelo_fanz_e_pelo_gmo():
    guide = guide_skills()
    fanz_skills, _ = fanz.parse_class_skills(read("skills/fanz-class-slayer-skills.html"))
    f = by_name(fanz_skills)["Bat Flock"]
    bat = from_guide(guide["Bat Flock"], {**f, "preview_url": None})
    assert bat["requirements"]["agi"] == 380 and bat["base_dmg"] == 90          # do guia
    assert bat["learn"] == {"method": "item", "item_name": "Orb of Bat Flock"}    # do Fanz
    assert bat["description"].startswith("Summons a flock of bats") and bat["element"] == "darkness"
    flare = from_guide(guide["Bursting Flare"], None)
    assert flare["requirements"]["other"] == ["Skill: Death Fire", "Master Skill: Death Fire Mastery 10 Points"]
    # Illusion Knight: o guia não tem requisitos; vêm do GMO (Season 21).
    ik, _ = gmo.parse_class_skills(read("skills/gmo-illusion-knight.html"))
    charge = fill_from_gmo(from_guide(guide["Charge Slash"], None), by_name(ik)["Charge Slash"])
    assert {k: v for k, v in charge["requirements"].items() if v} == {"level": 25, "agi": 80}
    assert (charge["season"], charge["mana_cost"], charge["source"]) == ("S21", 3, "guidemu")
    assert fill_from_gmo(bat, by_name(ik)["Charge Slash"]) is bat and bat["season"] is None   # já tem requisito: fica
    assert skill_slug("Sword’s Fury") == "swords-fury" and key("Alchemy: Angel Homunculus") == key("Angel Homunculus")


def test_schema_da_skill():
    skills, _ = fanz.parse_class_skills(read("skills/fanz-class-slayer-skills.html"))
    s = skills[6]
    record = {"id": f"slayer--{s['id']}", "skill_id": s["id"], "class_id": "slayer", "order": 6,
              **{k: v for k, v in s.items() if k != "id"}, "stage": "class", "unlocked_as": None, "range": None, "base_dmg": None,
              "season": None, "source": "fanz", "source_url": "https://muonlinefanz.com/guide/characters/slayer/",
              "scraped_at": "2026-10-21T20:03:59Z", "page_updated_at": "2025-05-08"}
    record["learn"] = {**record["learn"], "item_id": "orb-of-bat-flock", "drops": [], "item_from_class": None}
    record.update(aliases=[], cooldown_s=None, levels=[], image_url=None, preview_url=record.get("preview_url"))
    assert validate("skill", record) == []
