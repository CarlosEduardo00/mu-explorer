"""Copia para o nosso hospedeiro as imagens que o site usa (publicação autorizada pelas fontes, out/2026).

    python -m scrapers.media fetch      # baixa o que falta (1 req/s por host, robots.txt) -> site/public/media/
    python -m scrapers.media list       # só mostra quantas faltam

As imagens vêm dos registros de data/processed/combined (image_url, minimap_url) e de data/curated/planner.json
(imagens de classes e evoluções). Cada arquivo fica em site/public/media/<host>/<caminho da URL> e o manifesto
data/media.json liga a URL original ao caminho local. O site (lib/data.ts) troca a URL pela cópia quando ela existe;
o campo image_url dos dados continua apontando para a fonte (procedência). URL que responde sem imagem (o Fanz devolve
a página "404 - Page not found" com HTTP 200) fica no manifesto com "path": null: o site não mostra imagem quebrada e
o fetch não tenta de novo (só com --refresh).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scrapers.common.http import PoliteSession, RobotsUnavailable
from scrapers.common.model import REPO_ROOT
from scrapers.fanz import urls as fanz_urls

log = logging.getLogger("scrapers.media")

MEDIA_DIR = REPO_ROOT / "site" / "public" / "media"
MANIFEST = REPO_ROOT / "data" / "media.json"
HOSTS = {"muonlinefanz.com": "fanz", "www.muonlinefanz.com": "fanz", "globalmuonline.com": "gmo"}
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp", "image/gif")


def image_urls(data_dir: Path) -> list[str]:
    urls: set[str] = set()
    for name in ("items", "monsters", "maps", "npcs"):
        path = data_dir / "processed" / "combined" / f"{name}.json"
        if path.exists():
            for row in json.loads(path.read_text(encoding="utf-8")):
                urls.update(row[k] for k in ("image_url", "minimap_url") if row.get(k))
    planner = data_dir / "curated" / "planner.json"
    if planner.exists():
        for ruleset in json.loads(planner.read_text(encoding="utf-8"))["rulesets"]:
            for cls in ruleset["classes"]:
                urls.update(u for u in [cls.get("image_url"), *[e.get("image_url") for e in cls["evolutions"]]] if u)
    return sorted(u for u in urls if urlsplit(u).netloc in HOSTS)


def local_path(url: str) -> str:
    """Caminho público estável: /media/<fonte>/<caminho da URL, sem espaços nem caracteres estranhos>."""
    parts = urlsplit(url)
    path = unquote(parts.path).lstrip("/")
    safe = re.sub(r"[^A-Za-z0-9._/-]+", "-", path).strip("-")
    if safe != path:  # nomes diferentes que viram o mesmo slug não colidem
        stem, dot, ext = safe.rpartition(".")
        safe = f"{stem}-{hashlib.sha1(path.encode()).hexdigest()[:6]}.{ext}" if dot else safe
    return f"/media/{HOSTS[parts.netloc]}/{safe}"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}


def save_manifest(manifest: dict) -> None:
    MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def cmd_fetch(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    todo = [u for u in image_urls(args.data_dir) if args.refresh or u not in manifest]
    log.info("%d imagens a baixar", len(todo))
    session = PoliteSession(min_interval=max(1.0, args.interval), deny_paths=fanz_urls.DENY_PATHS)
    ok = failed = 0
    for i, url in enumerate(todo, 1):
        try:
            result = session.get(url)
        except RobotsUnavailable as exc:
            log.error("robots.txt indisponível, coleta abortada: %s", exc)
            break
        except Exception as exc:  # bloqueio de robots, rede: registra e segue
            log.warning("falha em %s: %s", url, exc)
            failed += 1
            continue
        ctype = (result.content_type or "").split(";")[0].strip().lower()
        if not result.ok or ctype not in IMAGE_TYPES or not result.content:
            log.warning("ignorada %s (HTTP %s, %s)", url, result.status, ctype)
            if result.status < 500:  # resposta definitiva da fonte: não há imagem nessa URL
                manifest[url] = {"path": None, "status": result.status, "type": ctype, "fetched_at": result.fetched_at}
            failed += 1
            continue
        rel = local_path(url)
        target = MEDIA_DIR.parent / rel.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(result.content)
        manifest[url] = {"path": rel, "bytes": len(result.content), "type": ctype, "fetched_at": result.fetched_at}
        ok += 1
        if i % 100 == 0:
            save_manifest(manifest)
            log.info("%d/%d", i, len(todo))
    save_manifest(manifest)
    log.info("baixadas: %d · falhas: %d · no manifesto: %d", ok, failed, len(manifest))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    urls = image_urls(args.data_dir)
    missing = [u for u in urls if u not in manifest]
    broken = [u for u in urls if u in manifest and not manifest[u].get("path")]
    print(f"{len(urls)} imagens usadas pelo site · {len(urls) - len(missing) - len(broken)} copiadas · "
          f"{len(broken)} sem imagem na fonte · {len(missing)} faltando")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scrapers.media", description="Cópia local das imagens do site")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--refresh", action="store_true")
    fetch.add_argument("--interval", type=float, default=1.0)
    sub.add_parser("list")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    return {"fetch": cmd_fetch, "list": cmd_list}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
