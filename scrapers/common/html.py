"""Extração de conteúdo de HTML independente de fonte.

O HTML vira uma lista de linhas (com células, links e imagens) e, a partir delas,
seções (por título) e pares rótulo -> valor. Os parsers de cada fonte mapeiam
rótulos por regex em vez de depender de seletores CSS, que quebram fácil e que
só dá para escrever depois de ver o HTML real.

Formatos de par reconhecidos:
- linha de tabela com 2 células:          <tr><th>Level</th><td>50</td></tr>
- linha de tabela rótulo/valor alternados: <tr><td>DEF</td><td>50</td><td>DEF Rate</td><td>30</td></tr>
- "Rótulo: valor" (inclusive com <b>):    <b>Level:</b> 50
- "Rótulo:" seguido do valor na linha seguinte
- <dt>Rótulo</dt><dd>valor</dd>
- rótulo seguido de número sem dois-pontos: "Defense 50"
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from urllib.parse import urljoin

from requests.utils import requote_uri
from selectolax.lexbor import LexborHTMLParser, LexborNode

SKIP_TAGS = frozenset({
    "script", "style", "noscript", "template", "head", "title", "iframe", "svg",
    "select", "button", "object", "embed",
})
HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6", "caption", "legend"})
BLOCK_TAGS = HEADING_TAGS | frozenset({
    "address", "article", "aside", "blockquote", "center", "div", "dl", "fieldset",
    "figcaption", "figure", "footer", "form", "header", "hr", "li", "main", "nav", "ol",
    "p", "pre", "section", "table", "tbody", "tfoot", "thead", "ul",
})

_WS = re.compile(r"\s+")
_COLON_PAIR = re.compile(r"^(?P<label>[^:]{1,40}?)\s*:\s*(?P<value>.*\S)\s*$")
_BARE_PAIR = re.compile(
    r"^(?P<label>[A-Za-z][A-Za-z .'/()-]{1,30}?)\s+"
    r"(?P<value>[+-]?\d[\d,.]*(?:\s*(?:~|-|to)\s*\d[\d,.]*)?\s*%?"
    r"(?:\s*(?:sec|secs|seconds|s|min|mins|minutes)\.?)?)$"
)


def clean(text: str | None) -> str:
    if not text:
        return ""
    return _WS.sub(" ", text.replace("\xa0", " ")).strip()


def norm_label(label: str) -> str:
    """'Max. HP:' -> 'max hp'. Base para casar rótulos por regex."""
    return _WS.sub(" ", re.sub(r"[^a-z0-9]+", " ", label.lower())).strip()


def absolute_url(base_url: str, href: str) -> str:
    return requote_uri(urljoin(base_url, href.strip()))


def _is_label(text: str) -> bool:
    text = text.strip().rstrip(":").strip()
    return (
        0 < len(text) <= 40
        and bool(re.search(r"[A-Za-z]", text))
        and len(text.split()) <= 6
        and not re.search(r"\d{2,}", text)
        and not text.lower().startswith("http")
    )


@dataclass
class Link:
    text: str
    href: str
    column: str | None = None  # cabeçalho da coluna da tabela onde o link está, se houver


@dataclass
class Image:
    src: str
    alt: str = ""
    title: str = ""


@dataclass
class Line:
    cells: list[str]
    heading: bool = False
    header_row: bool = False  # linha de cabeçalho de colunas de tabela (só <th>)
    links: list[Link] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(self.cells)


@dataclass
class Pair:
    label: str          # rótulo como aparece (sem ':' final)
    key: str            # rótulo normalizado (norm_label)
    value: str
    section: str | None  # título da seção onde o par apareceu
    line_index: int


@dataclass
class Section:
    heading: str | None
    lines: list[tuple[int, Line]]

    @property
    def links(self) -> list[Link]:
        return [link for _, line in self.lines for link in line.links]

    @property
    def images(self) -> list[Image]:
        return [image for _, line in self.lines for image in line.images]


class _Table:
    def __init__(self) -> None:
        self.headers: list[str] | None = None


class _LineBuilder:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.lines: list[Line] = []
        self._buf: list[str] = []
        self._cells: list[str] = []
        self._links: list[Link] = []
        self._images: list[Image] = []
        self._heading_depth = 0
        self._tables: list[_Table] = []
        self._rows: list[list[tuple[str, int, str]]] = []  # (tag, colspan, texto) por <tr> aberto
        self._column: str | None = None

    def walk(self, node: LexborNode) -> None:
        for child in node.iter(include_text=True):
            if child.is_comment_node:
                continue
            tag = child.tag
            if tag == "-text":
                self._buf.append(child.text_content or "")
            elif tag in SKIP_TAGS:
                continue
            elif tag == "br":
                self.end_line()
            elif tag == "img":
                src = child.attributes.get("src")
                if src:
                    self._images.append(Image(
                        src=absolute_url(self.base_url, src),
                        alt=clean(child.attributes.get("alt")),
                        title=clean(child.attributes.get("title")),
                    ))
            elif tag == "a":
                href = child.attributes.get("href")
                if href and not href.strip().lower().startswith(("javascript:", "#", "mailto:")):
                    self._links.append(Link(
                        text=clean(child.text()),
                        href=absolute_url(self.base_url, href),
                        column=self._column,
                    ))
                self.walk(child)
            elif tag == "table":
                self.end_line()
                self._tables.append(_Table())
                saved_column, self._column = self._column, None
                self.walk(child)
                self.end_line()
                self._tables.pop()
                self._column = saved_column
            elif tag == "tr":
                self._walk_row(child)
            elif tag in ("td", "th"):
                self._walk_cell(child, tag)
            elif tag == "dt":
                self.end_line()
                self.walk(child)
                self._end_cell()
            elif tag == "dd":
                self._end_cell()
                self.walk(child)
                self.end_line()
            elif tag in BLOCK_TAGS:
                self.end_line()
                is_heading = tag in HEADING_TAGS
                self._heading_depth += is_heading
                self.walk(child)
                self.end_line()
                self._heading_depth -= is_heading
            else:
                self.walk(child)

    def _walk_row(self, node: LexborNode) -> None:
        self.end_line()
        self._rows.append([])
        self.walk(node)
        self._end_cell()
        row = self._rows.pop()
        filled = [cell for cell in row if cell[2]]
        # Linha com uma única célula <th> funciona como título de seção.
        single_header = len(self._cells) == 1 and len(filled) == 1 and filled[0][0] == "th"
        # Primeira linha só de <th> com 2+ células: cabeçalhos das colunas da tabela.
        header_row = len(filled) >= 2 and all(cell[0] == "th" for cell in row)
        table = self._tables[-1] if self._tables else None
        if table and table.headers is None and header_row:
            table.headers = [text for _, colspan, text in row for _ in range(colspan)]
        self.end_line(force_heading=single_header, header_row=header_row)

    def _walk_cell(self, node: LexborNode, tag: str) -> None:
        self._end_cell()
        colspan_attr = node.attributes.get("colspan") or "1"
        colspan = int(colspan_attr) if colspan_attr.isdigit() else 1
        row = self._rows[-1] if self._rows else None
        table = self._tables[-1] if self._tables else None
        saved_column = self._column
        if row is not None and table and table.headers:
            start = sum(cell[1] for cell in row)
            self._column = table.headers[start] if start < len(table.headers) else None
        self.walk(node)
        text = self._end_cell()
        if row is not None:
            row.append((tag, colspan, text))
        self._column = saved_column

    def _end_cell(self) -> str:
        text = clean("".join(self._buf))
        self._buf.clear()
        if text:
            self._cells.append(text)
        return text

    def end_line(self, force_heading: bool = False, header_row: bool = False) -> None:
        self._end_cell()
        if self._cells or self._images:
            self.lines.append(Line(
                cells=self._cells,
                heading=bool(self._cells) and (force_heading or self._heading_depth > 0),
                header_row=header_row,
                links=self._links,
                images=self._images,
            ))
        self._cells, self._links, self._images = [], [], []


class Document:
    """Página HTML já convertida em linhas, seções e pares rótulo -> valor."""

    def __init__(self, html: str, base_url: str):
        tree = LexborHTMLParser(html)
        title = tree.css_first("title")
        self.title = clean(title.text()) if title else ""
        self.base_url = base_url
        builder = _LineBuilder(base_url)
        if tree.body is not None:
            builder.walk(tree.body)
        builder.end_line()
        self.lines: list[Line] = builder.lines

    @cached_property
    def text_lines(self) -> list[str]:
        return [line.text for line in self.lines if line.text]

    @cached_property
    def headings(self) -> list[str]:
        return [line.text for line in self.lines if line.heading]

    @cached_property
    def sections(self) -> list[Section]:
        sections = [Section(heading=None, lines=[])]
        for i, line in enumerate(self.lines):
            if line.heading:
                sections.append(Section(heading=line.text, lines=[]))
            else:
                sections[-1].lines.append((i, line))
        return sections

    def sections_matching(self, pattern: str) -> list[Section]:
        regex = re.compile(pattern, re.IGNORECASE)
        return [s for s in self.sections if s.heading and regex.search(s.heading)]

    @cached_property
    def links(self) -> list[Link]:
        return [link for line in self.lines for link in line.links]

    @cached_property
    def images(self) -> list[Image]:
        return [image for line in self.lines for image in line.images]

    @cached_property
    def pairs(self) -> list[Pair]:
        out: list[Pair] = []
        section: str | None = None
        for i, line in enumerate(self.lines):
            if line.heading:
                section = line.text
                continue
            if line.header_row:
                continue
            for label, value in self._line_pairs(i, line):
                label = clean(label).rstrip(":").strip()
                value = clean(value)
                if label and value:
                    out.append(Pair(label=label, key=norm_label(label), value=value, section=section, line_index=i))
        return out

    def _line_pairs(self, i: int, line: Line) -> list[tuple[str, str]]:
        cells = line.cells
        link_texts = {link.text for link in line.links}

        def is_label(cell: str) -> bool:  # texto de link não é rótulo (ex.: linha de itens)
            return _is_label(cell) and cell not in link_texts

        if len(cells) == 2 and is_label(cells[0]) and ":" not in cells[0].rstrip(":"):
            return [(cells[0], cells[1])]
        if (len(cells) >= 4 and len(cells) % 2 == 0
                and all(is_label(c) for c in cells[0::2])
                and all(re.search(r"\d", c) for c in cells[1::2])):
            return list(zip(cells[0::2], cells[1::2]))
        found: list[tuple[str, str]] = []
        for j, cell in enumerate(cells):
            colon = _COLON_PAIR.match(cell)
            if colon and is_label(colon["label"]):
                found.append((colon["label"], colon["value"]))
            elif cell.endswith(":") and is_label(cell) and j == len(cells) - 1:
                nxt = self.lines[i + 1] if i + 1 < len(self.lines) else None
                if nxt is not None and not nxt.heading and nxt.text:
                    found.append((cell, nxt.text))
            else:
                bare = _BARE_PAIR.match(cell)
                if bare:
                    found.append((bare["label"], bare["value"]))
        return found


class PairIndex:
    """Consome pares de um Document, guardando quais foram mapeados para o schema."""

    def __init__(self, pairs: list[Pair]):
        self.pairs = pairs
        self._used: set[int] = set()

    def take(self, pattern: str, *, section: str | None = None) -> Pair | None:
        found = self.take_all(pattern, section=section, limit=1)
        return found[0] if found else None

    def take_all(self, pattern: str, *, section: str | None = None, limit: int | None = None) -> list[Pair]:
        key_re = re.compile(pattern)
        section_re = re.compile(section, re.IGNORECASE) if section else None
        out = []
        for idx, pair in enumerate(self.pairs):
            if idx in self._used or not key_re.fullmatch(pair.key):
                continue
            if section_re and not (pair.section and section_re.search(pair.section)):
                continue
            self._used.add(idx)
            out.append(pair)
            if limit and len(out) >= limit:
                break
        return out

    def in_sections(self, sections: list[Section]) -> list[Pair]:
        """Pares ainda não usados que estão nas linhas dessas seções (sem marcá-los)."""
        lines = {i for s in sections for i, _ in s.lines}
        return [p for idx, p in enumerate(self.pairs) if idx not in self._used and p.line_index in lines]

    def mark(self, pair: Pair) -> None:
        self._used.add(self.pairs.index(pair))

    def line_has_pair(self, line_index: int) -> bool:
        return any(p.line_index == line_index for p in self.pairs)

    def unmapped(self) -> list[Pair]:
        return [p for idx, p in enumerate(self.pairs) if idx not in self._used]
