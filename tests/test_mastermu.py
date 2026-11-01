"""MasterMU: guia de drop de itens de skill (recorte real em tests/fixtures/mastermu, só títulos e tabelas) e a ligação
com as skills do site."""
from pathlib import Path

from scrapers.mastermu.cli import guide_key, guide_urls
from scrapers.mastermu.parse import icon_name, parse_skill_drops
from scrapers.skills.build import link_mastermu, mastermu_names

FIX = Path(__file__).parent / "fixtures" / "mastermu"


def rows() -> tuple[list[dict], list[str]]:
    return parse_skill_drops((FIX / "skill-drop-guide.html").read_text(encoding="utf-8"), "2026-11-01T18:50:58Z")


def test_urls_dos_guias_no_sitemap():
    xml = ("<urlset><url><loc>https://mastermu.net/guides</loc></url>"
           "<url><loc>https://mastermu.net/guides/view/faq</loc></url>"
           "<url><loc>https://mastermu.net/guides/view/faq</loc></url>"
           "<url><loc>https://mastermu.net/news/19</loc></url></urlset>")
    assert guide_urls(xml) == ["https://mastermu.net/guides/view/faq"]
    assert guide_key("https://mastermu.net/guides/view/leveling-guide") == "leveling-guide"


def test_tabelas_por_classe():
    found, unmapped = rows()
    assert unmapped == ["classe: unknown-class"]
    assert {r["class_id"] for r in found} == {"alchemist", "dark-knight", "fairy-elf", "crusader"}
    by = {(r["class_id"], r["label"]): r for r in found}
    swell = by[("dark-knight", "Fortitude")]
    assert swell["icon_name"] == "Swell Life"
    assert swell["map_ids"] == ["devias", "dungeon", "lost-tower"] and not swell["ruud_store"]
    blow = by[("dark-knight", "Fire Blow")]
    assert blow["ruud_store"] and blow["maps"] == [] and blow["map_ids"] == []
    death = by[("dark-knight", "Death Stab")]
    assert death["map_ids"] == ["atlans", "tarkan", "icarus", "aida", "kanturu-ruins"]   # Kanturu = Kanturu Ruins
    assert by[("crusader", "Holy Sweep")]["map_ids"] == ["swamp-of-calmness"]
    alch = by[("alchemist", "Articulation: Ignition Bomber Book of Laws")]
    assert "swamp-of-calmness" in alch["map_ids"] and alch["season"] == "S21" and alch["source"] == "mastermu"
    assert icon_name("https://x/skilldrop/StrikeofDestruction.webp") == "Strike of Destruction"


def skill(name: str, method=None, aliases=()) -> dict:
    return {"name": name, "aliases": list(aliases), "stage": "class", "learn": {"method": method, "item_name": None}}


def test_ligacao_com_as_skills_do_site():
    found, _ = rows()
    skills = {
        "dark-knight": [skill("Swell Life", "item"), skill("Sword's Fury", "item"), skill("Fire Blow", "item")],
        "alchemist": [skill("Ignition Bomber", "item")],
        "crusader": [skill("Luguard’s Protection: Punishment"), skill("Holy Sweep")],
        "fairy-elf": [skill("Recovery", "item"), skill("Improve Elemental Attack Power")],
    }
    unmatched = link_mastermu(skills, found)
    dk = {s["name"]: s["learn"] for s in skills["dark-knight"]}
    assert dk["Swell Life"]["drop_maps"] == ["devias", "dungeon", "lost-tower"]   # "Fortitude", casado pelo ícone
    assert dk["Sword's Fury"]["drop_maps"] == ["acheron"]                          # "Swords Fury"
    assert (dk["Fire Blow"]["shop"], dk["Fire Blow"]["drop_maps"]) == ("ruud", [])
    ib = skills["alchemist"][0]["learn"]
    assert ib["item_name"] == "Articulation: Ignition Bomber Book of Laws" and ib["drop_maps"]
    lugard = skills["crusader"][0]["learn"]
    assert (lugard["method"], lugard["drop_maps"]) == ("item", ["swamp-of-calmness"])   # sem método -> item
    assert skills["fairy-elf"][1]["learn"]["shop"] == "ruud"                             # "Elemental Attack"
    assert "fairy-elf: Penetration" in unmatched   # a skill não está na lista de teste
    assert mastermu_names({"label": "Formation: Angel Homunculus Book of Laws", "icon_name": "Angelic Homunculus"})[:2] == [
        "Formation: Angel Homunculus Book of Laws", "Angel Homunculus"]
