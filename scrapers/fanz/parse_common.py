"""Partes comuns aos parsers de item e monstro do Fanz.

Layout das páginas (observado em 40 páginas reais, ver tests/fixtures/fanz/):
  [menu de navegação ... "|||"] [conteúdo] ["b2023.11.20.001" (versão do template)] [rodapé]
O menu tem ~110 linhas e confunde qualquer extração, então o conteúdo é recortado entre o
marcador "|||" e a linha de versão do template.
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

from scrapers.common.html import Document, Line, norm_label

CONTENT_START = r"^\|\|\|$"
CONTENT_END = r"^b\d{4}\.\d{2}\.\d{2}\.\d+$"
# Linhas que são propaganda/UI, não conteúdo.
NOISE = re.compile(
    r"^(?:\[?Advertisement\]?:?|Search monster drops >>|Set the item level\.\.\."
    r"|Set the map's difficulty level to update the monster's data:)$",
    re.IGNORECASE,
)
_DIFFICULTY = re.compile(r"\s*\[Difficulty:?\s*(\d+)\]\s*$", re.IGNORECASE)


def open_document(html: str, url: str, heading) -> Document:
    return Document(html, url, start=CONTENT_START, end=CONTENT_END, heading=heading)


def content_lines(doc: Document) -> list[Line]:
    return [line for line in doc.lines if line.text and not NOISE.match(line.text)]


def page_title(lines: list[Line], url_name: str) -> tuple[str, int | None]:
    """Título visível da página (linha que, sem '[Difficulty: N]', bate com o nome da URL)."""
    target = norm_label(url_name)
    for line in lines[:12]:
        text = line.text
        difficulty = _DIFFICULTY.search(text)
        bare = _DIFFICULTY.sub("", text)
        if norm_label(bare) == target:
            return bare, int(difficulty.group(1)) if difficulty else None
    return url_name, None


def find_image(doc: Document, path_prefix: str) -> str | None:
    """Imagem do registro: só vale a que está na pasta de gráficos da fonte.
    Páginas sem imagem própria só têm o ícone de ajuda (/data/graphics/help.jpg): ficam com null."""
    for image in doc.images:
        if unquote(urlsplit(image.src).path).startswith(path_prefix):
            return image.src
    return None
