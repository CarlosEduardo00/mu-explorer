"""Descoberta de URLs: sitemap primeiro, páginas de listagem como fallback."""
from __future__ import annotations

import re

from selectolax.lexbor import LexborHTMLParser

from scrapers.common.html import absolute_url
from scrapers.common.http import normalize_url
from scrapers.fanz import urls

_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)


def urls_from_sitemap(text: str) -> list[str]:
    """Aceita sitemap em texto (uma URL por linha) ou XML (<loc>)."""
    found = _LOC.findall(text) if "<loc>" in text.lower() else [
        line.strip() for line in text.splitlines() if line.strip().lower().startswith("http")
    ]
    return list(dict.fromkeys(normalize_url(u) for u in found))


def links_from_list_page(html: str, base_url: str, kind: str) -> list[str]:
    tree = LexborHTMLParser(html)
    out = []
    for a in tree.css("a[href]"):
        url = absolute_url(base_url, a.attributes["href"] or "")
        if urls.classify(url) == kind:
            out.append(url)
    return list(dict.fromkeys(out))


def group_by_kind(all_urls: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {"item": [], "monster": [], "map": [], "npc": []}
    for url in all_urls:
        kind = urls.classify(url)
        if kind:
            grouped[kind].append(url)
    return grouped


def sample(items: list[str], n: int, mode: str = "spread") -> list[str]:
    """'first' pega os n primeiros; 'spread' pega n espaçados ao longo da lista (mais variedade)."""
    if n <= 0 or not items:
        return []
    if n >= len(items) or mode == "first":
        return items[:n]
    if n == 1:
        return [items[0]]
    step = (len(items) - 1) / (n - 1)
    return list(dict.fromkeys(items[round(i * step)] for i in range(n)))

