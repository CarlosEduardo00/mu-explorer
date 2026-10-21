"""Constantes e vocabulário da fonte MuEmu (emulador C# open source, licença MIT).

Repositório: https://github.com/deep-thought-42/MuEmu. Não é scraping: os dados vêm dos arquivos do
repositório (git clone). São dados de servidor privado; itens da Season 16 (itemS16.txt).
"""
from __future__ import annotations

import re

SOURCE_ID = "muemu"
SOURCE_NAME = "MuEmu (emulador open source)"
REPO_URL = "https://github.com/deep-thought-42/MuEmu"
CREDIT = "Dados de arquivos do MuEmu (github.com/deep-thought-42/MuEmu, licença MIT). Dados de servidor privado."
FILES = {
    "items": "Data/itemS16.txt",
    "monsters": "Data/Monsters/Monster.xml",
    "spawns": "Data/Monsters/MonsterSetBase.xml",
}
ITEMS_SEASON = "S16"

# Grupo do item no MU -> categoria.
GROUP_CATEGORIES = {
    0: "sword", 1: "axe", 2: "mace", 3: "spear", 4: "bow", 5: "staff", 6: "shield",
    7: "helm", 8: "armor", 9: "pants", 10: "gloves", 11: "boots",
    12: "wings_misc", 13: "accessory_misc", 14: "consumable_misc", 15: "scroll",
}
WEAPON_GROUPS = range(0, 6)
# Colunas de classe do itemS16.txt -> classe base (valor > 0: pode equipar).
CLASS_COLUMNS = {
    "DW": "Dark Wizard", "DK": "Dark Knight", "FE": "Fairy Elf", "MG": "Magic Gladiator",
    "DL": "Dark Lord", "SU": "Summoner", "RF": "Rage Fighter", "GL": "Grow Lancer",
    "RW": "Rune Wizard", "SL": "Slayer", "GC": "Gun Crusher",
}
# Tipos de entrada do MonsterSetBase.xml -> kind do spawn. NPCs ficam de fora.
SPAWN_KINDS = {"Spot": "spot", "Normal": "normal", "Golden": "golden", "BloodCastle": "event"}

# Grafias do MonsterSetBase -> nome do mapa como o jogo/Fanz escrevem.
MAP_ALIASES = {
    "Dugeon": "Dungeon", "Davias": "Devias", "Kantru": "Kanturu", "Vulcan": "Vulcanus",
    "Stadium": "Arena", "SantaTown": "Santa's Village", "ValleyofLoren": "Valley of Loren",
}


def map_name(raw: str) -> str:
    """'LostTower' -> 'Lost Tower', 'Kalima3' -> 'Kalima 3', 'Dugeon' -> 'Dungeon'."""
    match = re.fullmatch(r"(?P<base>.*?)(?P<number>\d*)", raw.strip())
    base, number = match["base"], match["number"]
    base = MAP_ALIASES.get(base, base)
    if " " not in base and "'" not in base:
        base = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base)
    return f"{base} {number}".strip()


def blob_url(commit: str, path: str, line: int | None = None) -> str:
    url = f"{REPO_URL}/blob/{commit}/{path}"
    return f"{url}#L{line}" if line else url


def requirement(factor: int, drop_level: int, group: int, name: str, stat: str) -> int | None:
    """Requisito final do item +0 a partir do fator do itemS16.txt (fórmula do jogo).

    Validado contra o Fanz: força/agilidade batem em ~98% dos itens. Energia usa x4, exceto os livros
    do Summoner (x3). Scrolls/pergaminhos (grupo 15) guardam o valor direto.
    """
    if factor <= 0:
        return None
    if group == 15:
        return factor
    multiplier = 4 if stat == "energy" and not (group == 5 and name.startswith("Book")) else 3
    return 20 + factor * drop_level * multiplier // 100
