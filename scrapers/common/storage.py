"""Armazenamento do conteúdo bruto baixado: data/raw/<fonte>/<tipo>/<slug>.html + <slug>.meta.json."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from scrapers.common.ids import slugify

if TYPE_CHECKING:
    from scrapers.common.http import FetchResult

_META_CHARSET = re.compile(rb"""<meta[^>]+charset=["']?([\w.-]+)""", re.IGNORECASE)


def decode_html(data: bytes, declared: str | None = None) -> str:
    sniffed = _META_CHARSET.search(data[:4096])
    candidates = [declared, sniffed.group(1).decode("ascii") if sniffed else None, "utf-8"]
    for encoding in candidates:
        if not encoding:
            continue
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("cp1252", errors="replace")


@dataclass
class RawPage:
    path: Path
    meta: dict

    @property
    def content(self) -> bytes:
        return self.path.read_bytes()

    @property
    def html(self) -> str:
        return decode_html(self.content, self.meta.get("encoding"))


class RawStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)

    def _dir(self, source: str, kind: str) -> Path:
        return self.root / source / kind

    @staticmethod
    def meta_path(path: Path) -> Path:
        return path.with_name(path.stem + ".meta.json")

    def path_for(self, source: str, kind: str, key: str, url: str, ext: str = ".html") -> Path:
        """Arquivo da URL. Se o slug já pertence a outra URL, acrescenta um hash curto."""
        base = slugify(key) or "page"
        directory = self._dir(source, kind)
        plain = directory / f"{base}{ext}"
        meta = self._read_meta(plain)
        if meta is None or meta.get("url") == url:
            return plain
        return directory / f"{base}--{hashlib.sha1(url.encode()).hexdigest()[:8]}{ext}"

    def exists(self, source: str, kind: str, key: str, url: str, ext: str = ".html") -> bool:
        """True se a página já foi baixada com sucesso (2xx). Erros ficam no disco, mas são refeitos."""
        page = self.load(source, kind, key, url, ext)
        return page is not None and 200 <= page.meta.get("status", 0) < 300

    def save(self, source: str, kind: str, key: str, result: FetchResult, ext: str = ".html") -> Path:
        path = self.path_for(source, kind, key, result.url, ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(result.content)
        meta = {
            "source": source,
            "kind": kind,
            "key": key,
            "file": path.name,
            "url": result.url,
            "final_url": result.final_url,
            "status": result.status,
            "content_type": result.content_type,
            "encoding": result.encoding,
            "fetched_at": result.fetched_at,
            "bytes": len(result.content),
            "sha256": hashlib.sha256(result.content).hexdigest(),
        }
        self.meta_path(path).write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def load(self, source: str, kind: str, key: str, url: str, ext: str = ".html") -> RawPage | None:
        path = self.path_for(source, kind, key, url, ext)
        meta = self._read_meta(path)
        return RawPage(path, meta) if meta is not None and path.exists() else None

    def iter(self, source: str, kind: str) -> Iterator[RawPage]:
        directory = self._dir(source, kind)
        if not directory.is_dir():
            return
        for meta_path in sorted(directory.glob("*.meta.json")):
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            path = directory / meta["file"]
            if path.exists():
                yield RawPage(path, meta)

    def _read_meta(self, path: Path) -> dict | None:
        meta_path = self.meta_path(path)
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text(encoding="utf-8"))
