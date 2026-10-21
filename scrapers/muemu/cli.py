"""CLI: python -m scrapers.muemu {fetch,parse}.

fetch: git clone raso do repositório em data/raw/muemu/repo e grava data/raw/muemu/meta.json (commit, data).
parse: arquivos do repositório -> data/processed/muemu/*.json (offline).
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

from scrapers.common.http import utc_now
from scrapers.common.model import REPO_ROOT, validate
from scrapers.common.storage import dump_records
from scrapers.muemu import parse, source

log = logging.getLogger("scrapers.muemu")


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def cmd_fetch(args: argparse.Namespace) -> int:
    raw = args.data_dir / "raw" / source.SOURCE_ID
    repo = raw / "repo"
    if (repo / ".git").exists():
        _git("fetch", "--depth", "1", "origin", cwd=repo)
        _git("reset", "--hard", "FETCH_HEAD", cwd=repo)
    else:
        raw.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", source.REPO_URL, str(repo)], check=True,
                       env={"GIT_LFS_SKIP_SMUDGE": "1", **__import__("os").environ})
    meta = {
        "repo": source.REPO_URL,
        "commit": _git("rev-parse", "HEAD", cwd=repo),
        "commit_date": _git("log", "-1", "--format=%cs", cwd=repo),
        "fetched_at": utc_now(),
        "files": source.FILES,
    }
    (raw / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    log.info("MuEmu em %s (commit %s de %s)", repo, meta["commit"][:10], meta["commit_date"])
    return 0


def load_raw(data_dir: Path) -> tuple[dict, dict[str, str]]:
    raw = data_dir / "raw" / source.SOURCE_ID
    meta = json.loads((raw / "meta.json").read_text(encoding="utf-8"))
    texts = {key: (raw / "repo" / path).read_text(encoding="utf-8", errors="replace") for key, path in source.FILES.items()}
    return meta, texts


def build(meta: dict, texts: dict[str, str]) -> tuple[dict[str, list[dict]], list[str]]:
    items, warnings = parse.parse_items(texts["items"], meta)
    monsters, more = parse.parse_monsters(texts["monsters"], meta)
    maps, spawns, even_more = parse.parse_spawns(texts["spawns"], monsters, meta)
    sources = [{
        "id": source.SOURCE_ID, "name": source.SOURCE_NAME, "url": source.REPO_URL, "credit": source.CREDIT,
        "pages": len(source.FILES), "first_scraped_at": meta["fetched_at"], "last_scraped_at": meta["fetched_at"],
        "revision": meta.get("commit"),
    }]
    data = {"item": items, "monster": monsters, "map": maps, "spawn": spawns, "drop": [], "source": sources}
    return data, warnings + more + even_more


OUTPUT = {"item": "items.json", "monster": "monsters.json", "map": "maps.json", "spawn": "spawns.json",
          "drop": "drops.json", "source": "sources.json"}


def cmd_parse(args: argparse.Namespace) -> int:
    meta, texts = load_raw(args.data_dir)
    data, warnings = build(meta, texts)
    errors = [f"{entity} {row.get('id') or row.get('monster_id')}: {e}"
              for entity, rows in data.items() for row in rows for e in validate(entity, row)]
    out = args.data_dir / "processed" / source.SOURCE_ID
    out.mkdir(parents=True, exist_ok=True)
    for entity, filename in OUTPUT.items():
        dump_records(out / filename, data[entity])
    for warning in warnings:
        log.warning(warning)
    for error in errors[:20]:
        log.error(error)
    log.info("itens: %d · monstros: %d · mapas: %d · spawns: %d · erros de schema: %d · JSON em %s",
             len(data["item"]), len(data["monster"]), len(data["map"]), len(data["spawn"]), len(errors), out)
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scrapers.muemu", description="Dados do MuEmu")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="git clone/atualiza o repositório do MuEmu em data/raw/muemu/")
    sub.add_parser("parse", help="arquivos do MuEmu -> data/processed/muemu/*.json")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    return {"fetch": cmd_fetch, "parse": cmd_parse}[args.command](args)
