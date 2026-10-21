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
_LEVEL_SUFFIX = re.compile(r"\s*\[(?:Lv:?\s*\d+|\+\d+)\]\s*$", re.IGNORECASE)  # "[Lv: 1]", "[+0]"
SOFT_404 = re.compile(r"^\s*(?:404 - Page not found\.?)?\s*$", re.IGNORECASE)


def open_document(html: str, url: str, heading) -> Document:
    return Document(html, url, start=CONTENT_START, end=CONTENT_END, heading=heading)


def content_lines(doc: Document) -> list[Line]:
    return [line for line in doc.lines if line.text and not NOISE.match(line.text)]


def page_title(lines: list[Line], url_name: str, warnings: list[str]) -> tuple[str, int | None]:
    """Título visível da página (linha que, sem '[Difficulty: N]', '[Lv: N]' ou '[+N]', bate com o nome da
    URL). Se nenhuma bate, usa o nome da URL e avisa."""
    target = norm_label(url_name)
    for line in lines[:12]:
        text = line.text
        difficulty = _DIFFICULTY.search(text)
        bare = _LEVEL_SUFFIX.sub("", _DIFFICULTY.sub("", text))
        if norm_label(bare) == target:
            return bare, int(difficulty.group(1)) if difficulty else None
    title = next((line.text for line in lines[:3] if not line.text.lower().startswith("home - tools")), None)
    warnings.append(f"título da página ({title!r}) não bate com o nome da URL ({url_name!r})")
    return url_name, None


def find_image(doc: Document, path_prefix: str) -> str | None:
    """Imagem do registro: só vale a que está na pasta de gráficos da fonte.
    Páginas sem imagem própria só têm o ícone de ajuda (/data/graphics/help.jpg): ficam com null."""
    for image in doc.images:
        if unquote(urlsplit(image.src).path).startswith(path_prefix):
            return image.src
    return None
