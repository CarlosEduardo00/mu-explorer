"""Gera data/curated/builds.json: builds prontas para seguir, só do MU Online oficial da Webzen.

    python -m scrapers.planner builds      # data/raw/fanz/tools/stat-planner.html -> data/curated/builds.json (offline)

De onde vem cada parte (nada de servidor privado):
- Distribuição de pontos das 13 classes que o Fanz cobre: presets do Stat Planner do MU Online Fanz (os mesmos da
  página "Stat Builds"), em % dos pontos ganhos por nível. O Fanz é um recurso de fã do servidor oficial, operado com
  permissão da Webzen; a publicação do conteúdo foi autorizada ao dono do projeto (out/2026). Crédito no rodapé.
- Fatos de jogo (qual atributo escala o dano de cada classe, requisitos de skill, renovações): guias oficiais da Webzen
  (muonline.webzen.com/en/gameinfo/guide/detail/N) e guias de classe do Fanz.
- Illusion Knight, Alchemist e Crusader: não há distribuição publicada por fonte do oficial. A proporção é nossa, feita
  a partir do atributo principal e dos requisitos de skill dos guias oficiais, e a build diz isso (`basis: "nossa"`).
- Vídeos: títulos e links de jogadores do servidor oficial (servidores Helheim, Midgard, Alfheim, Idavoll ou "Webzen"
  no título); servem para ver a build em jogo.

Cada build vira regras do planner (fase única: primeiro o que o equipamento exige de Força e Agilidade, o resto na
proporção da distribuição). `status`: "atual", ou "antiga" quando uma renovação oficial mudou o atributo que escala o
dano depois que a distribuição foi publicada (a nota diz qual).
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from scrapers.planner.build import CLASSES

log = logging.getLogger("scrapers.planner")

FANZ = "https://muonlinefanz.com"
STAT_BUILDS = f"{FANZ}/guide/hunting/stat-builds/"
STAT_PLANNER = f"{FANZ}/tools/stat-planner/"


def webzen(n: int) -> dict:
    return {"name": f"Webzen: guia oficial do MU Online ({n})", "url": f"https://muonline.webzen.com/en/gameinfo/guide/detail/{n}"}


def yt(title: str, video: str) -> dict:
    url = video if video.startswith("http") else f"https://www.youtube.com/watch?v={video}"
    return {"title": title, "url": url}


STAT_KEYS = {"STR": "str", "AGI": "agi", "STA": "vit", "ENE": "ene", "COM": "cmd", "CMD": "cmd"}


def parse_presets(html: str) -> dict[str, list[dict]]:
    """Presets do Stat Planner do Fanz: {chave da classe: [{"title", "ratio": {stat: %}}]} na ordem da página.
    Cada preset é um <text-subtitle> seguido dos spans `str<N>_factor_<classe>`; os fatores estão no script
    (`var STRfactor<N>_<classe> = 0.55;`)."""
    factors: dict[tuple[str, str], dict[str, float]] = {}
    for stat, n, key, value in re.findall(r"var\s+(STR|AGI|STA|ENE|COM|CMD)factor(\d)_(\w+)\s*=\s*([\d.]+)", html):
        factors.setdefault((key, n), {})[STAT_KEYS[stat]] = float(value)
    out: dict[str, list[dict]] = {}
    for title in re.finditer(r"<text-subtitle>([^<]+)</text-subtitle>", html):
        nxt = re.compile(r'id="str(\d)_factor_(\w+)"').search(html, title.end())
        sub = re.compile(r"<text-subtitle>").search(html, title.end())
        if not nxt or (sub and sub.start() < nxt.start()):
            continue  # título de classe (não tem fatores logo depois)
        n, key = nxt.group(1), nxt.group(2)
        ratio = {k: round(v * 100) for k, v in factors.get((key, n), {}).items() if v > 0}
        if ratio:
            out.setdefault(key, []).append({"title": title.group(1).strip(), "ratio": ratio})
    return out


# Builds por classe. "preset" = título do preset no Stat Planner do Fanz; sem preset, "ratio" é nosso (basis "nossa").
# skills: requisitos oficiais (atributo total) das skills que marcam a build; gear: variante das peças de set
# ("ATK", "ENE", "WIZ", "Belief"), para o site sugerir o equipamento certo.
BUILDS: dict[str, list[dict]] = {
    "dark-knight": [
        {"id": "dk-duas-armas", "preset": "2 Weapons", "name": "Duas armas (Força)", "role": "pvm",
         "summary": "A build de dano do Dark Knight: Força como atributo principal (é ela que escala o dano desde a "
                    "renovação da S18) e Agilidade para velocidade, com uma arma em cada mão.",
         "skills": [{"name": "Sword Fury", "req": {"str": 1060}}, {"name": "Water Blow", "req": {"str": 1090}}],
         "notes": ["Duas armas dão +10% de dano; duas armas iguais, +30%."],
         "sources": [webzen(321), webzen(106)],
         "videos": []},
        {"id": "dk-escudo", "preset": "Weapon+Shield", "name": "Arma e escudo (PvP)", "role": "pvp", "gear": "Belief",
         "summary": "Mais Vitalidade e Energia para aguentar dano, com escudo: a skill Firm Belief transforma o "
                    "personagem em Belief Knight, que ganha defesa.",
         "skills": [{"name": "Firm Belief (com escudo)", "req": {"ene": 1040}}],
         "notes": [], "sources": [webzen(106)], "videos": []},
        {"id": "dk-suporte", "preset": "Support", "name": "Suporte de grupo", "role": "suporte",
         "summary": "Vitalidade e Energia para a skill de grupo do Dragon Knight, que usa a Agilidade para absorver "
                    "parte do HP da party e a Energia para aumentar o ataque dela.",
         "skills": [{"name": "Skill de suporte do grupo", "req": {"ene": 1052}}],
         "notes": [], "sources": [webzen(106)],
         "videos": [yt("Dragon Knight Support lvl 800 | Mu Online WEBZEN", "Jd2V26cMqAQ")]},
    ],
    "dark-wizard": [
        {"id": "dw-pvm", "preset": "PVM", "name": "Energia e Agilidade (PvM)", "role": "pvm",
         "summary": "Energia para o dano mágico e bastante Agilidade para a taxa de ataque e a velocidade de magia.",
         "skills": [], "notes": [], "sources": [webzen(6)], "videos": []},
        {"id": "dw-pvp", "preset": "PVP", "name": "Energia (PvP)", "role": "pvp",
         "summary": "Ainda mais Energia (dano e defesa mágica) e menos Agilidade; para duelos e castle siege.",
         "skills": [], "notes": [], "sources": [webzen(6)], "videos": []},
        {"id": "dw-suporte", "preset": "Support", "name": "Suporte (Energia)", "role": "suporte",
         "summary": "Quase tudo em Energia, para os buffs e o escudo de mana do grupo. Pouco usada fora de party fixa.",
         "skills": [], "notes": [], "sources": [webzen(6)], "videos": []},
    ],
    "fairy-elf": [
        {"id": "elf-agilidade", "preset": "Attacker", "name": "Agilidade (ataque)", "role": "pvm", "gear": "ATK",
         "summary": "A Elf de ataque: Agilidade como atributo principal (arcos e bestas) e Força para o equipamento. "
                    "É o tipo de ataque da renovação oficial da Elf.",
         "skills": [{"name": "Dex Booster", "req": {"agi": 500}}, {"name": "Raining Arrow", "req": {"agi": 1302}}],
         "notes": ["Raining Arrow também pede 10 pontos de Multi Shot na árvore de skills."],
         "sources": [webzen(284)],
         "videos": [yt("Agility Elf BUILD PVM - MU Online 2025 Webzen", "JwV0msgyB0g"),
                    yt("Agility Elf Build PVM Raining Arrow - S17.2-2", "YAp5A3Eo5x8")]},
        {"id": "elf-energia", "preset": "Support", "name": "Energia (suporte)", "role": "suporte", "gear": "ENE",
         "summary": "A Elf de suporte da renovação oficial: Energia para os buffs e escudos exclusivos, e Vitalidade.",
         "skills": [], "notes": [], "sources": [webzen(284)], "videos": []},
    ],
    "magic-gladiator": [
        {"id": "mg-forca", "preset": "Attacker", "name": "Força e Agilidade (cavaleiro)", "role": "pvm", "gear": "ATK",
         "summary": "MG físico: Força e Agilidade, que são os atributos do dano do MG desde a S18. Duas espadas de uma "
                    "mão puxam Agilidade (velocidade); espada de duas mãos puxa Força (dano).",
         "skills": [], "notes": [], "sources": [webzen(321), webzen(244)], "videos": []},
        {"id": "mg-energia", "preset": "Wizardry", "name": "Energia (mago)", "role": "pvm", "gear": "WIZ",
         "summary": "MG mago: Energia para o dano mágico, com cajado na mão esquerda somando Wizardry; Agilidade para "
                    "a velocidade.",
         "skills": [], "notes": [], "sources": [webzen(244)],
         "videos": [yt("Rebuild Energy Magic Gladiator LvL 956 - Mu Online Webzen S18.2.2", "Ol5xzixaUZY")]},
        {"id": "mg-pvp", "preset": "PVP / Tank", "name": "PvP / tanque", "role": "pvp", "gear": "ATK",
         "summary": "Mais Vitalidade para aguentar dano em PvP, sem largar Agilidade e Força.",
         "skills": [], "notes": [], "sources": [webzen(321)],
         "videos": [yt("MG PvP nível 400 (espanhol)", "kKuSew1QI1o")]},
    ],
    "dark-lord": [
        {"id": "dl-forca", "preset": "Attacker", "name": "Força (ataque)", "role": "pvm",
         "summary": "Força como atributo principal, com Energia e um pouco de Comando. Desde a renovação da S19 "
                    "(parte 2), o dano do Dark Lord vem de Força e Comando.",
         "skills": [], "status": "antiga",
         "status_note": "Distribuição publicada antes da renovação do Dark Lord na S19 (parte 2), que passou a "
                        "escalar o dano com Força e Comando: confira o Comando antes de seguir.",
         "notes": [], "sources": [webzen(348)],
         "videos": [yt("Build PVM DL de Força - Mu Online Webzen", "-fM4l3m7YQM")]},
        {"id": "dl-comando", "preset": "Commander", "name": "Comando (PvM)", "role": "pvm",
         "summary": "Comando como atributo principal, para as skills do Lord e o dano depois da renovação da S19.",
         "skills": [{"name": "Lord of Dignity Strengthener", "req": {"ene": 102, "cmd": 300}},
                    {"name": "Crown Force", "req": {"ene": 300, "cmd": 400}}],
         "notes": ["Na renovação da S19, os pontos do Dark Lord foram reiniciados: quem já tinha personagem refez a build."],
         "sources": [webzen(348), webzen(347)],
         "videos": [yt("Dark Lord Command Build Level 800 PVM - 2025 Webzen", "Rw2yadq0XI8"),
                    yt("Rebuilding DL Lv.1300+ - Alfheim - S19.2.3", "22ZwhE-IMdw")]},
        {"id": "dl-pvp", "preset": "PVP / Tank", "name": "PvP / tanque", "role": "pvp",
         "summary": "Vitalidade e Agilidade para sobreviver e acertar em PvP.",
         "skills": [], "notes": [], "sources": [webzen(348)],
         "videos": [yt("Dark Lord Build 190 SPEED Level 850+", "wGnbCuiiqto")]},
    ],
    "summoner": [
        {"id": "sum-energia", "preset": "Attacker", "name": "Energia (ataque)", "role": "pvm",
         "summary": "Energia como atributo principal nos dois estilos do Summoner: Chaos Wizard (Berserker, com o "
                    "dano de maldição do livro) e Cursed Wizard (Darkness, área e debuffs com o cajado).",
         "skills": [], "notes": [], "sources": [webzen(91)],
         "videos": [yt("Build Summoner PVM - Mu Global", "BV9gUU7ZqEo"), yt("TOP SMS PVP de Helheim", "9vrCf8dUBRY")]},
    ],
    "rage-fighter": [
        {"id": "rf-vitalidade", "preset": "PVP / Tank", "name": "Vitalidade e Agilidade", "role": "híbrida",
         "summary": "Desde a renovação da S18, o dano do Rage Fighter escala com Agilidade e Vitalidade: é a build "
                    "que segue o jogo atual, boa em PvP e em PvM.",
         "skills": [], "notes": [], "sources": [webzen(321)],
         "videos": [yt("MU Online Webzen RF vitalidad test daño PVM", "K51qT6tsjIQ")]},
        {"id": "rf-forca", "preset": "PVM", "name": "Força (PvM, clássica)", "role": "pvm", "status": "antiga",
         "status_note": "Distribuição de antes da renovação da S18 (parte 2-2): hoje o dano do RF escala com "
                        "Agilidade e Vitalidade, não com Força.",
         "summary": "A build clássica de caça do RF, com Força para matar rápido sozinho.",
         "skills": [], "notes": [], "sources": [webzen(87), webzen(321)], "videos": []},
        {"id": "rf-energia", "preset": "Support", "name": "Energia (suporte)", "role": "suporte",
         "summary": "Energia para as skills de grupo do RF, em party e em muitos monstros ao mesmo tempo.",
         "skills": [], "notes": [], "sources": [webzen(87)], "videos": []},
    ],
    "grow-lancer": [
        {"id": "gl-forca", "preset": "Attacker", "name": "Força (ataque)", "role": "pvm",
         "summary": "Força como atributo principal: o mais forte para caçar e para PvP, e o buff Wrath escala com "
                    "Força e Agilidade.",
         "skills": [{"name": "Shining Pick", "req": {"str": 600}}],
         "notes": [], "sources": [webzen(97), webzen(329)], "videos": []},
        {"id": "gl-agilidade", "preset": "Elemental", "name": "Agilidade (elemental)", "role": "pvm",
         "summary": "Agilidade como atributo principal: caça mais rápido e chega na skill de Ruud de Agilidade.",
         "skills": [{"name": "Oversting", "req": {"agi": 1470}}],
         "notes": [], "sources": [webzen(97), webzen(329)], "videos": []},
    ],
    "slayer": [
        {"id": "slayer-agilidade", "preset": "High DMG", "name": "Agilidade (dano)", "role": "pvm",
         "summary": "A build atual do Slayer: o dano escala com Agilidade desde a renovação da S18, e as skills "
                    "principais pedem muita Agilidade.",
         "skills": [{"name": "Bat Flock", "req": {"str": 100, "agi": 380}}, {"name": "Detection", "req": {"agi": 800}},
                    {"name": "Pierce Attack", "req": {"str": 300, "agi": 1100}}, {"name": "Demolish", "req": {"agi": 1450}}],
         "notes": ["Pierce Attack também pede 10 pontos de Bat Flock Mastery na árvore."],
         "sources": [webzen(100), webzen(321)],
         "videos": [yt("Build de Slayer Top PVM - Midgard", "qVzFOrcH3ec"),
                    yt("Agi Slayer Pierce Attack (Test Server S15.3)", "WdnNtLn8DAY")]},
        {"id": "slayer-forca", "preset": "High Speed", "name": "Força (velocidade, clássica)", "role": "pvm",
         "status": "antiga",
         "status_note": "Distribuição de antes da renovação da S18 (parte 2-2): hoje o dano do Slayer escala com Agilidade.",
         "summary": "A build de Força de antes da renovação, focada em velocidade de ataque.",
         "skills": [], "notes": [], "sources": [webzen(321)], "videos": []},
    ],
    "gun-crusher": [
        {"id": "gc-energia", "preset": "Attacker", "name": "Energia (ataque)", "role": "pvm",
         "summary": "Energia é o atributo principal: a Magic Gun soma Wizardry e o dano mágico escala com Energia. "
                    "Agilidade dá taxa de defesa e taxa de ataque em PvP.",
         "skills": [], "notes": [], "sources": [webzen(79)], "videos": []},
    ],
    "rune-mage": [
        {"id": "rm-energia", "preset": "Attacker", "name": "Energia (ataque)", "role": "pvm",
         "summary": "Energia como atributo principal. Na renovação da S20 (parte 2) o Rune Mage ganhou o atributo "
                    "Magic Power e a Rune Mace de uma mão passou a dar Wizardry.",
         "skills": [], "notes": [], "sources": [webzen(92), webzen(388)], "videos": []},
    ],
    "white-wizard": [
        {"id": "ww-ataque", "preset": "Attacker", "name": "Agilidade e Energia", "role": "híbrida",
         "summary": "Metade em Agilidade e o resto quase todo em Energia: a Energia fortalece a magia (PvM) e a "
                    "Agilidade pesa mais em PvP. Defesa baixa; combina com a Lemuria no Bond Buff.",
         "skills": [], "notes": [], "sources": [webzen(259), webzen(266)],
         "videos": [yt("Kundun White Wizard Lv 780 PVM - Speed Server 2024 Webzen", "nesyTY7WwV4"),
                    yt("Light Wizard (Kundun) 1700 PVM - S20", "https://www.youtube.com/shorts/i8JvFQf2oBk")]},
    ],
    "mage": [
        {"id": "mage-energia", "preset": "Attacker", "name": "Energia (ataque)", "role": "pvm",
         "summary": "Quase tudo em Energia: a Lemuria ataca com orbes e a Energia fortalece a magia; HP e defesa baixos.",
         "skills": [], "notes": [], "sources": [webzen(259)], "videos": []},
    ],
    "illusion-knight": [
        {"id": "ik-agilidade", "ratio": {"str": 25, "agi": 55, "vit": 15, "ene": 5}, "name": "Agilidade (PvM)",
         "role": "pvm",
         "summary": "No guia oficial, a Agilidade (Dexterity) aumenta o ataque e o dano de skill do Illusion Knight, e "
                    "todas as skills principais pedem Agilidade.",
         "skills": [{"name": "Charging Slash", "req": {"agi": 80}}, {"name": "Wind Glaive", "req": {"agi": 650}},
                    {"name": "Illusion Avatar", "req": {"agi": 900}}, {"name": "Blade Storm", "req": {"agi": 1150}}],
         "notes": ["Blade Storm também pede 10 pontos de Wind Glaive na árvore."],
         "sources": [webzen(290), webzen(291)],
         "videos": [yt("Illusion Knight Level 750 PVM/PVE BUILD Speed Server - 2024 Webzen", "FJjS3YXD8Z4")]},
    ],
    "alchemist": [
        {"id": "alchemist-energia", "ratio": {"str": 5, "agi": 10, "vit": 20, "ene": 65}, "name": "Energia (PvM)",
         "role": "pvm", "fill": {"agi": 120},
         "summary": "No guia oficial, a Energia fortalece as skills mágicas do Alchemist; os elixires pedem um pouco "
                    "de Agilidade (até ~120).",
         "skills": [{"name": "Angel Homunculus", "req": {"ene": 70}}, {"name": "Ignition Bomber", "req": {"ene": 680}},
                    {"name": "Confusion Stone", "req": {"ene": 850}}, {"name": "Countless Weapon", "req": {"ene": 1025}}],
         "notes": [], "sources": [webzen(365), webzen(366), webzen(367)],
         "videos": [yt("Alchemist BUILD level 800 PVM - 2025 Webzen", "dBWZXSYzwnA"),
                    yt("ALCHEMIST GUIDE: Build, Skills...", "oD55Ij6ExZc")]},
    ],
    "crusader": [
        {"id": "crusader-forca", "ratio": {"str": 55, "agi": 22, "vit": 13, "ene": 10}, "name": "Força (martelo)",
         "role": "pvm",
         "summary": "Força como atributo principal, com martelo e Paladin Shield. As skills pedem Agilidade em torno de "
                    "40% da Força exigida, e o buff Retaliation (Lugard's Blessing) pede 200 de Energia.",
         "skills": [{"name": "Divine Fall", "req": {"str": 60, "agi": 29}}, {"name": "Retaliation", "req": {"ene": 200}},
                    {"name": "Holy Sweep", "req": {"str": 420, "agi": 168}},
                    {"name": "Sacred Impact", "req": {"str": 1045, "agi": 418}}],
         "notes": [], "sources": [webzen(419), webzen(420), webzen(421)], "videos": []},
    ],
}

ROLE_ORDER = {"pvm": 0, "híbrida": 1, "pvp": 2, "suporte": 3}


def build_builds(raw_dir: Path) -> tuple[dict, list[str]]:
    html_path = raw_dir / "fanz" / "tools" / "stat-planner.html"
    presets = parse_presets(html_path.read_text(encoding="utf-8", errors="replace")) if html_path.exists() else {}
    planner_key = {cid: pkey for cid, _, _, pkey, _ in CLASSES}
    guide_key = {cid: gkey for cid, _, gkey, _, _ in CLASSES}
    notes, out = [], []
    for class_id, defs in BUILDS.items():
        for d in defs:
            if "preset" in d:
                found = next((p for p in presets.get(planner_key[class_id], []) if p["title"] == d["preset"]), None)
                if found is None:
                    notes.append(f"{d['id']}: preset {d['preset']!r} não achado no Stat Planner")
                    continue
                ratio, basis = found["ratio"], "fanz"
                sources = [{"name": "MU Online Fanz: Stat Builds", "url": STAT_BUILDS},
                           {"name": "MU Online Fanz: Stat Planner", "url": STAT_PLANNER},
                           {"name": "MU Online Fanz: guia da classe", "url": f"{FANZ}/guide/characters/{guide_key[class_id]}/"}]
            else:
                ratio, basis, sources = d["ratio"], "nossa", []
            if "cmd" in ratio and class_id != "dark-lord":
                ratio = {k: v for k, v in ratio.items() if k != "cmd"}
            fill = [{"stat": "str", "to": "gear"}, {"stat": "agi", "to": "gear"}]
            fill += [{"stat": s, "to": v} for s, v in d.get("fill", {}).items()]
            build = {
                "id": d["id"], "class_id": class_id, "name": d["name"], "role": d["role"], "summary": d["summary"],
                "status": d.get("status", "atual"), "basis": basis, "ratio": ratio,
                "phases": [{"from_level": 1, "fill": fill, "split": ratio}],
                "skills": d.get("skills", []), "videos": d.get("videos", []),
                "notes": ([d["status_note"]] if d.get("status_note") else []) + d.get("notes", []),
                "sources": sources + d.get("sources", []),
            }
            if d.get("gear"):
                build["gear_variant"] = d["gear"]
            out.append(build)
    out.sort(key=lambda b: (list(BUILDS).index(b["class_id"]), b["status"] != "atual", ROLE_ORDER[b["role"]]))
    return {"builds": out}, notes


def main(data_dir: Path) -> int:
    from scrapers.common.model import validate_file
    data, notes = build_builds(data_dir / "raw")
    errors = validate_file("builds", data)
    target = data_dir / "curated" / "builds.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for note in notes:
        log.warning(note)
    for error in errors[:20]:
        log.error(error)
    by_basis = {k: sum(1 for b in data["builds"] if b["basis"] == k) for k in ("fanz", "nossa")}
    log.info("%d builds (%d com distribuição do Fanz, %d nossas) em %s; %d avisos; %d erros de schema",
             len(data["builds"]), by_basis["fanz"], by_basis["nossa"], target, len(notes), len(errors))
    return 1 if errors or notes else 0
