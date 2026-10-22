"""Guias do Guide MU Online (páginas renderizadas por scrapers.guidemu.render) -> blocos de conteúdo.

Cada guia vira {id, path, series, title, siblings, blocks, image_urls, ...}. Blocos:
- heading {level, text}, paragraph {text, style}, image {src, alt}, list {items}, table {head, rows},
- card {kind, blocks} (cartões do site: guide, quest, npc, info, item), grid {items} (cartões lado a lado),
- tabs {tabs: [{label, blocks}]} (abas; o conteúdo de cada uma vem do que o renderizador guardou),
- accordion {items: [{title, blocks}]}.
Texto: {"t": modelo, "m": [termos]}. O modelo é o texto com marcadores {0}, {1}... no lugar dos termos do jogo
(span.text-accent e nomes entre aspas simples, como 'Ring of Honor'), que não são traduzidos, e com <b>, <em> para
negrito e destaque. A tradução (data/curated/translations/guides.pt-BR.json) troca o modelo inteiro, mantendo os
marcadores: a frase fica natural e os termos voltam iguais.
"""
from __future__ import annotations

import re
from html import escape

from selectolax.lexbor import LexborHTMLParser, LexborNode

BASE = "https://guidemuonline.com"
SKIP_CLASSES = {"adsbygoogle", "contenido-panc", "btn-more-info", "boton-go-to"}
INLINE = {"-text", "span", "b", "strong", "em", "a", "small", "br", "sup", "sub", "u"}
EMPHASIS = {"text-danger": "danger", "text-warning": "warn", "text-info": "info"}
# 'Nome Entre Aspas' no texto: termo do jogo (começa com maiúscula ou número; aspas fora de palavras, então
# "Giaon's" e "Tarkan's" não contam).
QUOTED = re.compile(r"(?<![\w'])'([A-Z0-9][^'\n]{0,58}?)'(?![\w])")
MAX_TERM_WORDS = 6   # destaque mais longo que isso (ou terminado em ":") é ênfase de frase, não nome do jogo


def is_term(text: str) -> bool:
    text = text.strip()
    return bool(text) and len(text.split()) <= MAX_TERM_WORDS and not text.endswith((":", ".", "!", "?"))


def _classes(node: LexborNode) -> set[str]:
    return set((node.attributes.get("class") or "").split())


class TextBuilder:
    """Monta o modelo de um trecho de texto com marcadores para os termos."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.terms: list[str] = []

    def term(self, text: str) -> None:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return
        if text not in self.terms:
            self.terms.append(text)
        self.parts.append("{%d}" % self.terms.index(text))

    def plain(self, text: str) -> None:
        pos = 0
        for m in QUOTED.finditer(text):
            self.parts.append(escape(text[pos:m.start()], quote=False))
            self.term(m.group(0))
            pos = m.end()
        self.parts.append(escape(text[pos:], quote=False))

    def walk(self, node: LexborNode) -> None:
        child = node.child
        while child is not None:
            self.node(child)
            child = child.next

    def node(self, child: LexborNode) -> None:
        if child.tag == "-text":
            self.plain(child.text_content or "")
        elif child.tag == "br":
            self.parts.append("<br>")
        elif child.tag in ("i", "img", "button", "script", "ins", "-comment"):
            pass
        else:
            cls = _classes(child)
            if ("text-accent" in cls or "text-accent-upper" in cls) and is_term(child.text()):
                self.term(child.text())
            elif "text-accent" in cls or "text-accent-upper" in cls:
                self.parts.append('<em class="accent">')
                self.walk(child)
                self.parts.append("</em>")
            elif child.tag in ("b", "strong") or "fw-bold" in cls:
                self.parts.append("<b>")
                self.walk(child)
                self.parts.append("</b>")
            elif cls & EMPHASIS.keys():
                kind = EMPHASIS[next(iter(cls & EMPHASIS.keys()))]
                self.parts.append(f'<em class="{kind}">')
                self.walk(child)
                self.parts.append("</em>")
            else:
                self.walk(child)

    def result(self) -> dict | None:
        text = re.sub(r"\s+", " ", "".join(self.parts)).strip()
        text = re.sub(r"<(b|em[^>]*)>\s*</(b|em)>", "", text)
        if not re.sub(r"<[^>]+>", "", text).strip():
            return None
        return {"t": text, "m": self.terms} if self.terms else {"t": text}


def rich(node: LexborNode) -> dict | None:
    b = TextBuilder()
    b.walk(node)
    return b.result()


class GuideParser:
    def __init__(self, panes: dict[str, tuple[str, str]]):
        self.panes = panes   # rótulo da aba -> (HTML, modo) guardado pelo renderizador
        self.images: list[str] = []

    def blocks(self, node: LexborNode) -> list[dict]:
        out: list[dict] = []
        run: list[LexborNode] = []   # texto e destaques seguidos: um parágrafo só

        def flush() -> None:
            if run:
                b = TextBuilder()
                for n in run:
                    b.node(n)
                text = b.result()
                if text:
                    out.append({"type": "paragraph", "text": text})
                run.clear()

        child = node.child
        while child is not None:
            if child.tag in INLINE and not _classes(child) & SKIP_CLASSES and not (child.tag == "small" and child.css_first("table")):
                run.append(child)
            else:
                flush()
                out += self.block(child)
                # abas separadoras: o que vem depois da lista é o conteúdo da parte ativa, já dentro das abas
                if child.tag != "-text" and self._separator(child):
                    break
            child = child.next
        flush()
        return out

    def _separator(self, node: LexborNode) -> bool:
        tablist = node if node.attributes.get("role") == "tablist" else node.css_first("[role=tablist]")
        if tablist is None:
            return False
        tabs = tablist.css("[role=tab]")
        return len(tabs) > 1 and self.panes.get(tabs[0].text(strip=True), ("", ""))[1] == "after"

    def block(self, node: LexborNode) -> list[dict]:
        tag, cls = node.tag, _classes(node)
        if tag in ("-text", "-comment", "script", "ins", "button", "i", "style") or cls & SKIP_CLASSES:
            return []
        if tag in ("h1", "h2", "h3", "h4", "h5"):
            text = rich(node)
            return [{"type": "heading", "level": min(4, max(2, int(tag[1]))), "text": text}] if text else []
        if tag in ("p", "li") or (tag == "div" and "text-accent-upper" in cls):
            text = rich(node)
            if not text:
                return []
            style = "label" if "text-accent-upper" in cls else "accent" if "text-accent" in cls else \
                "danger" if "text-danger" in cls else "level" if "text-required-level" in cls else None
            block = {"type": "paragraph", "text": text}
            if style:
                block["style"] = style
            if "text-center" in cls:
                block["center"] = True
            return [block]
        if tag == "img":
            src = node.attributes.get("src") or ""
            if not src or src.startswith("/static/") or src.startswith("data:"):
                return []
            src = src if src.startswith("http") else BASE + src
            self.images.append(src)
            alt = re.sub(r"\s*Mu Online$", "", (node.attributes.get("alt") or "").strip())
            return [{"type": "image", "src": src, "alt": alt or None}]
        if tag in ("ul", "ol"):
            if node.attributes.get("role") == "tablist":
                return self.tabs(node)
            items = [t for t in (rich(li) for li in node.css("li")) if t]
            return [{"type": "list", "items": items}] if items else []
        if tag == "table":
            head = [rich(th) for th in node.css("thead th")]
            rows = [[rich(td) for td in tr.css("td")] for tr in node.css("tbody tr")]
            rows = [r for r in rows if any(r)]
            return [{"type": "table", "head": head, "rows": rows}] if rows else []
        if "accordionGuide" in cls:
            title = node.css_first(".accordion-button")
            body = node.css_first(".accordion-body")
            return [{"type": "accordion", "items": [{"title": rich(title) if title else None,
                                                      "blocks": self.blocks(body) if body else []}]}]
        if "tab-content" in cls:
            return []   # o conteúdo das abas vem dos painéis guardados (ver tabs)
        if "card" in cls:
            kind = ("quest" if "card-npc-quest" in cls else "info" if "card-quest-info" in cls
                    else "item" if "card-bg-sinhover" in cls else "guide")
            inner = self.blocks(node)
            return [{"type": "card", "kind": kind, "blocks": inner}] if inner else []
        # contêiner: uma linha com vários cartões vira grade
        inner = self.blocks(node)
        cards = [b for b in inner if b["type"] == "card"]
        if "row" in cls and len(cards) >= 2 and len(cards) == len(inner):
            return [{"type": "grid", "items": cards}]
        return inner

    def tabs(self, node: LexborNode) -> list[dict]:
        tabs = node.css("[role=tab]")
        if len(tabs) == 1:   # aba única: cabeçalho de seção
            text = rich_text(tabs[0].text(strip=True))
            return [{"type": "heading", "level": 2, "text": text, "style": "section"}] if text else []
        out = []
        for tab in tabs:
            label = tab.text(strip=True)
            html = self.panes.get(label, ("", ""))[0]
            blocks = self.blocks(LexborHTMLParser(f"<div>{html}</div>").css_first("div")) if html else []
            out.append({"label": rich_text(label), "blocks": blocks})
        return [{"type": "tabs", "tabs": out}] if out else []


def rich_text(text: str) -> dict | None:
    b = TextBuilder()
    b.plain(text)
    return b.result()


SERIES = {"class-change": "class-change", "how-to-create-wings": "wings", "elemental-system": "elemental"}


def guide_id(path: str) -> str:
    """Id curto do guia: o fim do caminho, sem "-guide" ("elemental-system/errtels-guide" -> "errtels")."""
    return re.sub(r"-guide$", "", path.strip("/").split("/")[-1])


def parse_guide(html: str, meta: dict) -> dict | None:
    tree = LexborHTMLParser(html)
    h1 = tree.css_first(".contenido-column h1")
    if not h1:
        return None
    url = meta.get("url") or ""
    path = url.removeprefix(f"{BASE}/guides/").strip("/")
    panes = {s.attributes.get("data-tab") or "": (s.inner_html or "", s.attributes.get("data-mode") or "pane")
             for s in tree.css("#mu-explorer-tabs section")}
    parser = GuideParser(panes)
    root = h1.parent
    siblings = []
    for a in root.css("a"):
        if a.css_first(".boton-go-to") and (a.attributes.get("href") or "").startswith("/guides/"):
            siblings.append({"label": a.text(strip=True), "id": guide_id(a.attributes["href"].removeprefix("/guides/"))})
    blocks = []
    node = h1.next
    while node is not None:
        blocks += parser.block(node)
        if node.tag != "-text" and parser._separator(node):
            break
        node = node.next
    return {
        "id": guide_id(path), "path": path, "series": SERIES.get(path.split("/")[0], "systems"),
        "title": rich(h1), "siblings": siblings, "blocks": blocks,
        "image_urls": list(dict.fromkeys(parser.images)),
        "source": "guidemu", "source_url": url, "scraped_at": meta.get("fetched_at"),
    }
