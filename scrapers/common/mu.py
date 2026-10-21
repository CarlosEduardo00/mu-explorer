"""Vocabulário do jogo usado pelos parsers (classes de personagem)."""
from __future__ import annotations

import re

from scrapers.common.html import clean

# Classes base e evoluções conhecidas. Lista parcial: serve para separar textos corridos
# ("Dark Wizard Dark Knight") e abreviações. Classe desconhecida é mantida como veio e
# aparece como aviso no relatório.
KNOWN_CLASSES = [
    "Dark Wizard", "Soul Master", "Grand Master", "Soul Wizard", "Darkness Wizard",
    "Dark Knight", "Blade Knight", "Blade Master", "Dragon Knight", "Ignition Knight",
    "Fairy Elf", "Muse Elf", "High Elf", "Noble Elf", "Royal Elf",
    "Magic Gladiator", "Duel Master", "Magic Knight",
    "Dark Lord", "Lord Emperor", "Empire Lord",
    "Summoner", "Bloody Summoner", "Dimension Master", "Dimension Summoner",
    "Rage Fighter", "Fist Master", "Fist Blazer",
    "Grow Lancer", "Mirage Lancer", "Shining Lancer",
    "Rune Wizard", "Rune Mage", "Rune Spell Master", "Grand Rune Master", "Rune Grand Master", "Majestic Rune Wizard",
    "Slayer", "Royal Slayer", "Master Slayer", "Slaughterer",
    "Gun Crusher", "Gun Breaker", "Master Gun Breaker", "Heist Gun Crasher", "Heist Gun Crusher",
    "Light Wizard", "White Wizard", "Shine Wizard", "Light Master",
    "Mage", "Lemuria Mage", "War Mage", "Wo Mage", "Arch Mage", "Mystic Mage",
    "Illusion Knight", "Alchemist", "Crusader", "Soul Lancer", "Emperor Lord",
    "All Classes",  # o Fanz usa para itens sem restrição de classe
]
ABBREVIATIONS = {
    "DW": "Dark Wizard", "SM": "Soul Master", "GM": "Grand Master", "GRM": "Grand Master",
    "DK": "Dark Knight", "BK": "Blade Knight", "BM": "Blade Master",
    "FE": "Fairy Elf", "ELF": "Fairy Elf", "ME": "Muse Elf", "HE": "High Elf",
    "MG": "Magic Gladiator", "DUM": "Duel Master", "DM": "Duel Master", "DL": "Dark Lord", "LE": "Lord Emperor",
    "SUM": "Summoner", "BS": "Bloody Summoner", "DIM": "Dimension Master", "RF": "Rage Fighter", "FM": "Fist Master",
    "GL": "Grow Lancer", "ML": "Mirage Lancer", "RW": "Rune Wizard", "SL": "Slayer", "GC": "Gun Crusher",
}

_CANONICAL = {name.lower(): name for name in KNOWN_CLASSES}
_CLASS_RE = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in sorted(KNOWN_CLASSES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
_SPLIT_RE = re.compile(r"\s*(?:,|/|;|\||&|\band\b|\.\s)\s*", re.IGNORECASE)  # "MG. RF"


def is_known_class(name: str) -> bool:
    return name.lower() in _CANONICAL


def split_classes(text: str) -> list[str]:
    """'Dark Wizard, Soul Master / DK' -> ['Dark Wizard', 'Soul Master', 'Dark Knight']."""
    out: list[str] = []
    for part in _SPLIT_RE.split(text):
        part = clean(part).strip("[]() ")
        if not part:
            continue
        found = _CLASS_RE.findall(part)
        if found:
            out.extend(_CANONICAL[f.lower()] for f in found)
        elif part.upper() in ABBREVIATIONS and len(part) <= 4:  # 'DW', 'ELF', 'DiM'...
            out.append(ABBREVIATIONS[part.upper()])
        else:
            out.append(part)
    return list(dict.fromkeys(out))


def find_classes(text: str) -> list[str]:
    """Só as classes conhecidas presentes no texto, sem tokens desconhecidos."""
    return list(dict.fromkeys(_CANONICAL[f.lower()] for f in _CLASS_RE.findall(text)))
