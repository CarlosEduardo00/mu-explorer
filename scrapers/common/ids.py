"""Geração de IDs internos (slugs) a partir de nomes."""
from __future__ import annotations

import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """'Dragon Armor' -> 'dragon-armor'; remove acentos e pontuação."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return _NON_ALNUM.sub("-", ascii_text.lower()).strip("-")
