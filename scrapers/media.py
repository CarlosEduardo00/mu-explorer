"""Copia para o nosso hospedeiro as imagens que o site usa (publicação autorizada pelas fontes, out/2026).

    python -m scrapers.media fetch      # baixa o que falta (1 req/s por host, robots.txt) -> site/public/media/
    python -m scrapers.media list       # só mostra quantas faltam

As imagens vêm dos registros de data/processed/combined (image_url, minimap_url; nas skills também preview_url) e de
data/curated/planner.json (imagens de classes e evoluções). Cada arquivo fica em site/public/media/<host>/<caminho da URL> e o manifesto
data/media.json liga a URL original ao caminho local. O site (lib/data.ts) troca a URL pela cópia quando ela existe;
o campo image_url dos dados continua apontando para a fonte (procedência). URL que responde sem imagem (o Fanz devolve
a página "404 - Page not found" com HTTP 200) fica no manifesto com "path": null: o site não mostra imagem quebrada e
o fetch não tenta de novo (só com --refresh).

As prévias animadas das skills (GIF do Fanz, de 1 a 3 MB) viram vídeo, cerca de 7 vezes menor, quando há ffmpeg
(`python -m scrapers.media compact`, também no fim do fetch): WebM (VP9, codec aberto) no caminho do manifesto e um MP4
(H.264) ao lado, com o mesmo nome, para os navegadores sem VP9 (Safari antigo).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scrapers.common.http import PoliteSession, RobotsUnavailable
from scrapers.common.model import REPO_ROOT
from scrapers.fanz import urls as fanz_urls

log = logging.getLogger("scrapers.media")

MEDIA_DIR = REPO_ROOT / "site" / "public" / "media"
MANIFEST = REPO_ROOT / "data" / "media.json"
HOSTS = {"muonlinefanz.com": "fanz", "www.muonlinefanz.com": "fanz", "globalmuonline.com": "gmo",
         "firebasestorage.googleapis.com": "guidemu",   # imagens do Guide MU Online (Firebase Storage)
         "guidemuonline.com": "guidemu"}                # ícones da árvore de melhorias (static/media do site)
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp", "image/gif")


def image_urls(data_dir: Path) -> list[str]:
    urls: set[str] = set()
    for name in ("items", "monsters", "maps", "npcs"):
        path = data_dir / "processed" / "combined" / f"{name}.json"
        if path.exists():
            for row in json.loads(path.read_text(encoding="utf-8")):
                urls.update(row[k] for k in ("image_url", "minimap_url") if row.get(k))
    skills = data_dir / "processed" / "combined" / "skills.json"
    if skills.exists():   # ícones (guia oficial) e prévias animadas (Fanz) das skills
        for row in json.loads(skills.read_text(encoding="utf-8")):
            urls.update(row[k] for k in ("image_url", "preview_url") if row.get(k))
    guides = data_dir / "processed" / "combined" / "guides.json"
    if guides.exists():
        for guide in json.loads(guides.read_text(encoding="utf-8")):
            urls.update(guide.get("image_urls") or [])
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
    if "/o/" in path and parts.netloc == "firebasestorage.googleapis.com":   # .../o/<objeto>?alt=media
        path = path.split("/o/", 1)[1]
    safe = re.sub(r"[^A-Za-z0-9._/-]+", "-", path).strip("-")
    if safe != path:  # nomes diferentes que viram o mesmo slug não colidem
        stem, dot, ext = safe.rpartition(".")
        safe = f"{stem}-{hashlib.sha1(path.encode()).hexdigest()[:6]}.{ext}" if dot else safe
    return f"/media/{HOSTS[parts.netloc]}/{safe}"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}


def save_manifest(manifest: dict) -> None:
    MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def gifs_to_video(manifest: dict) -> int:
    """GIFs copiados -> <nome>.webm (VP9) + <nome>.mp4 (H.264), sem som e com dimensões pares; o manifesto aponta para o
    .webm. Devolve quantos converteu. Sem ffmpeg, os GIFs ficam como estão."""
    todo = [row for row in manifest.values() if row.get("type") == "image/gif" and (row.get("path") or "").endswith(".gif")]
    ffmpeg = shutil.which("ffmpeg")
    if todo and ffmpeg is None:
        log.warning("%d GIFs ficam como estão: ffmpeg não encontrado", len(todo))
        return 0
    common = ["-movflags", "+faststart", "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-an"]
    done = 0
    for row in todo:
        src = MEDIA_DIR.parent / row["path"].lstrip("/")
        if not src.exists():
            continue
        webm, mp4 = src.with_suffix(".webm"), src.with_suffix(".mp4")
        for codec, target in ((["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "36"], webm),
                              (["-c:v", "libx264", "-crf", "26", "-preset", "slow"], mp4)):
            subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(src), *common, *codec, str(target)], check=True)
        src.unlink()
        row.update(path=row["path"][: -len(".gif")] + ".webm", bytes=webm.stat().st_size, type="video/webm",
                   source_type="image/gif")
        done += 1
    return done


def cmd_compact(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    log.info("GIFs convertidos para vídeo: %d", gifs_to_video(manifest))
    save_manifest(manifest)
    return 0


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
    converted = gifs_to_video(manifest)
    save_manifest(manifest)
    log.info("baixadas: %d · falhas: %d · GIFs em vídeo: %d · no manifesto: %d", ok, failed, converted, len(manifest))
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
    sub.add_parser("compact")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    return {"fetch": cmd_fetch, "list": cmd_list, "compact": cmd_compact}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
