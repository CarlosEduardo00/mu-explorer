"""Skills por classe: árvore do guia de classe do Fanz e tabela do guia do GMO (HTML real em tests/fixtures/skills e
tests/fixtures/planner), e a ligação de cada skill ao item que a ensina."""
from pathlib import Path

from scrapers.combine import item_resolver, match_items, muemu_skill_items, reordered_name, skill_item_names
from scrapers.common.model import validate
from scrapers.skills import fanz, gmo
from scrapers.skills.build import key, link_items

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
    assert skills["gun-crusher"][0]["learn"] == {"method": "item", "item_name": "Orb of Ice Break", "item_id": "orb-of-ice-break", "drops": []}
    assert skills["gun-crusher"][1]["learn"]["method"] is None
    assert skills["alchemist"][0]["learn"]["item_id"] is None   # Scroll of Lightning é do DW: não vale para o Alchemist
    ww = skills["white-wizard"][0]["learn"]
    assert (ww["item_name"], ww["item_id"], ww["drops"]) == ("Shining Bird Law Book", None, [{"monster_id": "lizard-warrior", "map_id": "lorencia"}])


def test_schema_da_skill():
    skills, _ = fanz.parse_class_skills(read("skills/fanz-class-slayer-skills.html"))
    s = skills[6]
    record = {"id": f"slayer--{s['id']}", "skill_id": s["id"], "class_id": "slayer", "order": 6,
              **{k: v for k, v in s.items() if k != "id"}, "stage": "class", "unlocked_as": None, "range": None, "base_dmg": None,
              "season": None, "source": "fanz", "source_url": "https://muonlinefanz.com/guide/characters/slayer/",
              "scraped_at": "2026-10-21T20:03:59Z", "page_updated_at": "2025-05-08"}
    record["learn"] = {**record["learn"], "item_id": "orb-of-bat-flock", "drops": []}
    assert validate("skill", record) == []
