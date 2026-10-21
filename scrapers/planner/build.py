"""Gera data/curated/planner.json: regras de classes por conjunto de regras ("ruleset"), das mais novas
para as mais antigas.

Fontes (todas já em data/raw/, baixadas pelos outros scrapers):
- Guias de classe e Stat Planner do Fanz (`python -m scrapers.planner fetch`, ~15 requisições): pontos por
  nível, nível de desbloqueio, evolução e atributos base do jogo atual. Rótulo "global-atual".
- Characters.xml e código do MuEmu (MIT): atributos base e pontos por nível de uma season clássica.
  Rótulo "classico".

Só fatos de regra entram no arquivo (números e nomes de classe). As distribuições de pontos sugeridas pelo
Stat Planner do Fanz são curadoria do autor e NÃO são copiadas.

`publish`: o conjunto "global-atual" vem dos guias do Fanz; segue o mesmo bloqueio de publicação dos demais
dados do Fanz (ver CLAUDE.md) e só aparece no site em build local (SITE_DATA=combined).
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from scrapers.common.html import Document
from scrapers.common.http import utc_now
from scrapers.common.model import REPO_ROOT
from scrapers.common.storage import RawStore, dump_records  # noqa: F401  (dump_records usado em testes)

log = logging.getLogger("scrapers.planner")
STATS = ("str", "agi", "vit", "ene", "cmd")
HERO_STATUS_LEVEL = 220  # quest "Hero Status": a partir dela, classes de 1º tier ganham 6 pontos por nível

# id, nome, chave do guia do Fanz, chave no script do Stat Planner, BaseClass no Characters.xml do MuEmu
CLASSES = [
    # As três primeiras são as que o projeto atende primeiro; depois, o resto na ordem do jogo.
    ("gun-crusher", "Gun Crusher", "gun-crusher", "gun", "GunCrusher"),
    ("slayer", "Slayer", "slayer", "slayer", "Slayer"),
    ("grow-lancer", "Grow Lancer", "gl", "gl", "GrowLancer"),
    ("dark-wizard", "Dark Wizard", "dw", "dw", "DarkWizard"),
    ("dark-knight", "Dark Knight", "dk", "dk", "DarkKnight"),
    ("fairy-elf", "Fairy Elf", "elf", "elf", "FaryElf"),
    ("magic-gladiator", "Magic Gladiator", "mg", "mg", "MagicGladiator"),
    ("dark-lord", "Dark Lord", "dl", "dl", "DarkLord"),
    ("summoner", "Summoner", "sum", "sum", "Summoner"),
    ("rage-fighter", "Rage Fighter", "rf", "rf", "RageFighter"),
    ("rune-mage", "Rune Mage", "rm", "rune", "RuneWizard"),
    ("white-wizard", "White Wizard", "white-wizard", "ww", None),
    ("mage", "Mage", "mage", "mage", None),
]
# O guia do Dark Knight tem o layout antigo, sem a seção "Class Evolution": nomes tirados do próprio guia
# ("Blade Knight (2nd class)"...) e níveis iguais aos de todas as outras classes de 1º tier.
DK_EVOLUTIONS = [(1, "Dark Knight", None), (2, "Blade Knight", 150), (3, "Blade Master", 400), (4, "Dragon Knight", 800)]
# Nomes com que o MuEmu e o Fanz escrevem a classe-base nos itens ("Rune Wizard" no MuEmu = Rune Mage).
ALIASES = {"rune-mage": ["Rune Wizard"]}
FANZ_CREDIT = "Dados de regra (números e nomes) dos guias de classe de MU Online Fanz (muonlinefanz.com), conteúdo de IZAKTLY."
MUEMU_CREDIT = "Characters.xml e código do MuEmu (github.com/deep-thought-42/MuEmu), licença MIT."


# --- Fanz -------------------------------------------------------------------------------------

def guide_lines(html: str) -> list[str]:
    doc = Document(html, "https://muonlinefanz.com/", start=r"^\|\|\|$", end=r"^b\d{4}\.\d{2}\.\d{2}\.\d+$")
    return [line.text for line in doc.lines if line.text]


def parse_planner_bases(html: str) -> dict[str, dict[str, int]]:
    """Atributos base por classe nos scripts do Stat Planner: {'gun': {'str': 20, ...}} (vit = 'STA')."""
    out: dict[str, dict[str, int]] = {}
    for script in re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.S):
        key = re.search(r"var totalStats_(\w+) = ", script)
        if not key:
            continue
        cls = key.group(1)
        bases = {}
        for stat, name in (("str", "STR"), ("agi", "AGI"), ("vit", "STA"), ("ene", "ENE")):
            match = re.search(rf"var {name}base_{cls} = (\d+);", script)
            if match:
                bases[stat] = int(match.group(1))
        out[cls] = bases
    return out


def parse_guide(lines: list[str]) -> dict:
    """Fatos do guia de uma classe: tier, nível de desbloqueio, pontos por nível, evolução, nome."""
    head = lines[:80]
    tier = next((int(m.group(1)) for x in head if (m := re.match(r"^Tier (\d) Class", x))), None)
    unlock = next((int(m.group(1)) for x in head if (m := re.search(r"unlocked after reaching level (\d+)", x, re.I))), None)
    rates = []
    for x in head:
        m = re.search(r"\+(\d+) stat points? per (?:character )?level( after Hero Status quest)?", x, re.I)
        if m:
            rates.append((int(m.group(1)), bool(m.group(2))))
    evolutions: list[dict] = []
    start = next((i for i, x in enumerate(lines) if x.startswith("Class Evolution")), None)
    if start is not None:
        current = None
        for x in lines[start + 1:start + 90]:
            if x.startswith(("Advertisement", "Stats & Formulas")):
                break
            m = re.match(r"^(\d)(?:st|nd|rd|th): (.+)$", x)
            if m:
                current = {"tier": int(m.group(1)), "name": m.group(2).strip(), "level": None}
                evolutions.append(current)
            elif current and (lv := re.search(r"Reaching Character Level (\d+)", x)):
                current["level"] = int(lv.group(1))
    max_level = max((int(m.group(1)) for x in lines[:200] if (m := re.search(r"Stops gaining EXP at Level (\d+)", x))), default=None)
    return {"name": lines[0] if lines and lines[0] != "Advertisement:" else None, "tier": tier,
            "unlock_level": unlock, "rates": rates, "evolutions": evolutions, "max_level": max_level}


def rates_to_steps(rates: list[tuple[int, bool]]) -> list[dict]:
    """[(5, False), (6, True)] -> [{'from_level': 2, 'per_level': 5}, {'from_level': 220, 'per_level': 6}]."""
    steps = []
    for per_level, after_hero in rates:
        steps.append({"from_level": HERO_STATUS_LEVEL if after_hero else 2, "per_level": per_level})
    return sorted(steps, key=lambda s: s["from_level"])


# --- MuEmu ------------------------------------------------------------------------------------

def parse_muemu_bases(xml_text: str) -> dict[str, dict[str, int]]:
    root = ET.fromstring(xml_text)
    out = {}
    for char in root.iter("Character"):
        stats = char.find("Stats")
        if stats is not None:
            out[char.get("BaseClass")] = {s: int(stats.get(s.capitalize(), 0)) for s in STATS}
    return out


# --- montagem ---------------------------------------------------------------------------------

def build(raw_dir: Path) -> tuple[dict, list[str]]:
    notes: list[str] = []
    fanz_dir = raw_dir / "fanz" / "tools"
    plan = parse_planner_bases((fanz_dir / "stat-planner.html").read_text(encoding="utf-8", errors="replace"))
    muemu = parse_muemu_bases((raw_dir / "muemu" / "repo" / "Data" / "Characters.xml").read_text(encoding="utf-8"))

    current, classic = [], []
    for class_id, name, guide_key, plan_key, mu_key in CLASSES:
        guide = parse_guide(guide_lines((fanz_dir / f"class-{guide_key}.html").read_text(encoding="utf-8", errors="replace")))
        evolutions = guide["evolutions"] or [{"tier": t, "name": n, "level": lv} for t, n, lv in DK_EVOLUTIONS if class_id == "dark-knight"]
        tier = guide["tier"] or 1
        steps = rates_to_steps(guide["rates"]) or ([{"from_level": 2, "per_level": 5}, {"from_level": HERO_STATUS_LEVEL, "per_level": 6}] if tier == 1 else [])
        if not guide["rates"]:
            notes.append(f"{class_id}: guia sem linha de pontos por nível; usada a regra do tier {tier}")

        # Jogo atual: Stat Planner do Fanz (o comando do Dark Lord não está lá: vem do MuEmu).
        # Clássico: Characters.xml do MuEmu. Quando as duas fontes diferem, é mudança entre versões do jogo.
        fanz_base = {s: plan.get(plan_key, {}).get(s) for s in STATS}
        mu_base = muemu.get(mu_key) if mu_key else None
        if any(fanz_base[s] is None for s in STATS[:4]):
            notes.append(f"{class_id}: atributos base incompletos no Stat Planner do Fanz")
        base = {s: (fanz_base[s] if fanz_base[s] is not None else (mu_base[s] if mu_base else 0)) for s in STATS}
        if mu_base and any(fanz_base[s] is not None and fanz_base[s] != mu_base[s] for s in STATS[:4]):
            notes.append(f"{class_id}: base mudou entre o clássico {tuple(mu_base[s] for s in STATS[:4])} e o atual "
                         f"{tuple(base[s] for s in STATS[:4])} (esperado: versões diferentes do jogo)")
        if class_id == "dark-lord" and not base["cmd"]:
            notes.append("dark-lord: comando base ausente")

        names = [name, *ALIASES.get(class_id, []), *[e["name"] for e in evolutions]]
        current.append({
            "id": class_id, "name": name, "tier": tier, "unlock_level": guide["unlock_level"], "base": base,
            "points": steps, "max_level_points": 400, "max_level": guide["max_level"] or 1450,
            "evolutions": [{"tier": e["tier"], "name": e["name"], "level": e["level"]} for e in evolutions],
            "names": list(dict.fromkeys(names)),
        })
        if mu_base:
            classic.append({
                "id": class_id, "name": name, "tier": None, "unlock_level": None, "base": dict(mu_base),
                # Regra do código do MuEmu: 5 pontos por nível, 7 para Magic Gladiator e Dark Lord.
                "points": [{"from_level": 2, "per_level": 7 if class_id in ("magic-gladiator", "dark-lord") else 5}],
                "max_level_points": 400, "max_level": 400, "evolutions": [], "names": list(dict.fromkeys([name, *ALIASES.get(class_id, [])])),
            })

    data = {
        "version": 1,
        "generated_at": utc_now(),
        "stats": list(STATS),
        "rulesets": [  # da mais nova para a mais antiga
            {"id": "global-atual", "name": "Global atual", "description": "Regras do jogo atual, segundo os guias de classe do Fanz.",
             "publish": False, "credit": FANZ_CREDIT, "classes": current},
            {"id": "classico", "name": "Clássico (emulador MuEmu)", "description": "Regras de um servidor clássico, segundo o emulador MuEmu (5 pontos por nível; 7 para MG e DL).",
             "publish": True, "credit": MUEMU_CREDIT, "classes": classic},
        ],
    }
    return data, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scrapers.planner", description="Regras de classes do planner")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="baixa os guias de classe e o Stat Planner do Fanz (~15 requisições a 1 req/s)")
    sub.add_parser("build", help="gera data/curated/planner.json a partir de data/raw (offline)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    if args.command == "fetch":
        return cmd_fetch(args)
    data, notes = build(args.data_dir / "raw")
    from scrapers.common.model import validate_file
    errors = validate_file("planner", data)
    out = args.data_dir / "curated" / "planner.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for note in notes:
        log.warning(note)
    for error in errors[:20]:
        log.error(error)
    log.info("%d classes (global-atual), %d (clássico); %d avisos; %d erros de schema; em %s",
             len(data["rulesets"][0]["classes"]), len(data["rulesets"][1]["classes"]), len(notes), len(errors), out)
    return 1 if errors else 0


def cmd_fetch(args: argparse.Namespace) -> int:
    from scrapers.common.http import RobotsUnavailable
    from scrapers.fanz import pipeline, urls
    session = pipeline.make_session()
    store = RawStore(args.data_dir / "raw")
    pages = {"stat-planner": f"{urls.BASE_URL}/tools/stat-planner/"}
    pages.update({f"class-{guide}": f"{urls.BASE_URL}/guide/characters/{guide}/" for _, _, guide, _, _ in CLASSES})
    try:
        for key, url in pages.items():
            result = session.get(url)
            store.save("fanz", "tools", key, result)
            log.info("%s -> HTTP %s", url, result.status)
    except RobotsUnavailable as exc:
        log.error("robots.txt indisponível, coleta abortada: %s", exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
