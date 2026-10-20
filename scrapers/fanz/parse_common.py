"""Partes comuns aos parsers de item e monstro do Fanz."""
from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

from scrapers.common.html import Document, norm_label

_SITE_SUFFIX = re.compile(r"\s*[-|–:]\s*(?:mu\s*online\s*fanz|muonlinefanz).*$", re.IGNORECASE)


def pick_name(doc: Document, url_name: str, warnings: list[str]) -> str:
    """Nome do registro: o título da página que bate com o nome da URL; senão o nome da URL."""
    target = norm_label(url_name)
    candidates = [*doc.headings, _SITE_SUFFIX.sub("", doc.title), doc.title]
    for candidate in candidates:
        if candidate and norm_label(candidate) == target:
            return candidate
    if doc.headings:
        warnings.append(f"nenhum título bate com o nome da URL ({url_name!r}); títulos: {doc.headings[:3]}")
    return url_name


def find_image(doc: Document, name: str, path_prefix: str) -> str | None:
    """Imagem do registro: a que está na pasta de imagens da fonte, ou a com alt igual ao nome."""
    for image in doc.images:
        if unquote(urlsplit(image.src).path).startswith(path_prefix):
            return image.src
    target = norm_label(name)
    for image in doc.images:
        if target and target in (norm_label(image.alt), norm_label(image.title)):
            return image.src
    return None
