"""Leitura dos arquivos JavaScript do site (React + webpack, código ofuscado).

- `main.<hash>.js` traz a tabela que liga cada chunk ao seu hash (`static/js/<id>.<hash>.chunk.js`), mas os valores
  vêm de uma tabela de strings rotacionada (javascript-obfuscator). A rotação sai de duas âncoras conhecidas: a
  função que monta a URL usa as strings 'static/js/' e '.chunk.js'.
- Os dados (mapas com spots, monstros) são um JSON dentro de uma string literal de um chunk; `find_json` acha a
  string pelo conteúdo e decodifica.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator

_STRING = re.compile(r"'((?:[^'\\\n]|\\.)*)'")
_ESCAPE = re.compile(r"\\(?:x([0-9a-fA-F]{2})|u([0-9a-fA-F]{4})|(.))", re.DOTALL)
_SIMPLE = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


def unescape_js(s: str) -> str:
    """Conteúdo de uma string JS entre aspas simples (\\x22, \\u00e9, \\n, \\' ...)."""
    def repl(m: re.Match) -> str:
        if m.group(1):
            return chr(int(m.group(1), 16))
        if m.group(2):
            return chr(int(m.group(2), 16))
        return _SIMPLE.get(m.group(3), m.group(3))
    return _ESCAPE.sub(repl, s)


def js_strings(text: str) -> Iterator[str]:
    """Strings literais (aspas simples) do código, já decodificadas."""
    for m in _STRING.finditer(text):
        yield unescape_js(m.group(1))


def main_script(index_html: str) -> str | None:
    """Caminho do script principal no HTML (ex.: /static/js/main.ec0bf085.js)."""
    m = re.search(r'src="(/static/js/main\.[0-9a-f]+\.js)"', index_html)
    return m.group(1) if m else None


def _string_array(text: str) -> tuple[str, list[str]] | None:
    """(nome da função, strings) da tabela do ofuscador: function a1_0x5403(){const _0x..=['..', ..];...}."""
    m = re.search(r"function (\w+)\(\)\{(?:const|var|let) \w+=\[", text)
    if not m:
        return None
    pos, out = m.end(), []
    while True:
        while pos < len(text) and text[pos] in " ,\n\r\t":
            pos += 1
        if pos >= len(text) or text[pos] == "]":
            break
        s = _STRING.match(text, pos)
        if not s:
            return None
        out.append(unescape_js(s.group(1)))
        pos = s.end()
    return m.group(1), out


def chunk_files(main_js: str) -> dict[int, str]:
    """{id do chunk: 'static/js/<id>.<hash>.chunk.js'} a partir do main.js ofuscado. Vazio se o formato mudou."""
    table = _string_array(main_js)
    if not table:
        return {}
    array_fn, strings = table
    dec = re.search(r"function (\w+)\(\w+,\w+\)\{(?:const|var|let) \w+=" + re.escape(array_fn)
                    + r"\(\);return \1=function\(\w+,\w+\)\{\w+=\w+-(0x[0-9a-f]+|\d+);", main_js)
    fn = re.search(r"\['u'\]=(\w+)=>(\w+)\((0x[0-9a-f]+)\)\+\1\+'\.'\+\{([^}]*)\}\[\1\]\+\2\((0x[0-9a-f]+)\)", main_js)
    if not dec or not fn:
        return {}
    base, n = int(dec.group(2), 0), len(strings)
    prefix_at, suffix_at = int(fn.group(3), 16) - base, int(fn.group(5), 16) - base
    shift = next((r for r in range(n) if strings[(prefix_at + r) % n].endswith("static/js/")
                  and strings[(suffix_at + r) % n] == ".chunk.js"), None)
    if shift is None:
        return {}
    prefix = strings[(prefix_at + shift) % n].lstrip("/")
    out = {}
    for m in re.finditer(r"(0x[0-9a-f]+|\d+):(?:'([0-9a-f]+)'|\w+\((0x[0-9a-f]+)\))", fn.group(4)):
        chunk = int(m.group(1), 0)
        digest = m.group(2) or strings[(int(m.group(3), 16) - base + shift) % n]
        out[chunk] = f"{prefix}{chunk}.{digest}.chunk.js"
    return out


def find_json(text: str, marker: str):
    """Primeiro JSON (lista ou objeto) guardado numa string literal que contém `marker`; None se não houver."""
    for s in js_strings(text):
        if marker in s and s.lstrip()[:1] in "[{":
            try:
                return json.loads(s)
            except ValueError:
                continue
    return None
