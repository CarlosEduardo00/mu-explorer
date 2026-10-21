"""Parse dos arquivos de dados do MuEmu: itemS16.txt, Monster.xml e MonsterSetBase.xml."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter

from scrapers.common.ids import slugify
from scrapers.common.model import empty_map
from scrapers.muemu import source

_REQUIREMENT_COLUMNS = {"strength": "ReqStr", "agility": "ReqDex", "energy": "ReqEne",
                        "vitality": "ReqVit", "command": "ReqCmd"}


def _int(value: str | None) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _attr_int(element: ET.Element, attr: str) -> int | None:
    raw = element.get(attr)
    return _int(raw) if raw not in (None, "") else None


def _provenance(meta: dict, path: str, line: int | None = None, season: str | None = None) -> dict:
    return {
        "season": season,
        "source": source.SOURCE_ID,
        "source_url": source.blob_url(meta["commit"], path, line),
        "scraped_at": meta["fetched_at"],
    }


def _unique_ids(names: list[str], suffixes: list[str]) -> list[str]:
    """Slug do nome; quando o nome se repete, todos os repetidos ganham um sufixo (grupo/índice, número)."""
    counts = Counter(slugify(n) for n in names)
    return [slugify(n) if counts[slugify(n)] == 1 else f"{slugify(n)}-{suffix}" for n, suffix in zip(names, suffixes)]


def parse_items(text: str, meta: dict) -> tuple[list[dict], list[str]]:
    path = source.FILES["items"]
    header: list[str] | None = None
    rows: list[tuple[int, dict]] = []
    warnings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        cols = line.split("\t")
        if line.startswith("//ItemIndex"):
            header = [c.lstrip("/").strip() for c in cols]
            continue
        if not line.strip() or line.startswith("//") or header is None:
            continue
        if len(cols) < 35:
            warnings.append(f"{path}:{lineno}: linha com {len(cols)} colunas ignorada")
            continue
        rows.append((lineno, dict(zip(header, cols))))

    names = [row["szItemName"].strip().strip('"') for _, row in rows]
    ids = _unique_ids(names, [f"g{_int(r['ItemSubGroup'])}-i{_int(r['ItemSubIndex'])}" for _, r in rows])
    items = []
    for (lineno, row), name, item_id in zip(rows, names, ids):
        group, index, drop_level = _int(row["ItemSubGroup"]), _int(row["ItemSubIndex"]), _int(row["DropLevel"])
        requirements = {stat: source.requirement(_int(row[col]), drop_level, group, name, stat)
                        for stat, col in _REQUIREMENT_COLUMNS.items()}
        requirements = {"level": _int(row["ReqLvl"]) or None, **requirements}
        stats = {key: _int(row[col]) for key, col in (
            ("damage_min", "DamageMin"), ("damage_max", "DamageMax"), ("defense", "Defense"),
            ("defense_rate", "DefenseRate"), ("attack_speed", "AttackSpeed"), ("walk_speed", "WalkSpeed"),
            ("magic_power", "MagicPower"), ("magic_resistance", "MagicResistance"),
        ) if _int(row[col]) > 0}
        if group in source.WEAPON_GROUPS:
            stats["hands"] = 2 if _int(row["TwoHands"]) else 1
        items.append({
            "id": item_id,
            "name": name,
            "category": source.GROUP_CATEGORIES.get(group),
            "group": group,
            "index": index,
            "classes": [label for column, label in source.CLASS_COLUMNS.items() if _int(row.get(column)) > 0],
            "requirements": requirements,
            "stats": stats,
            "durability": _int(row["Durability"]) or _int(row["MagicDur"]) or None,
            "grade": None,
            "options": [],
            "option_groups": [],
            "related_items": [],
            "notes": [],
            "image_url": None,
            **_provenance(meta, path, lineno, source.ITEMS_SEASON),
            "page_updated_at": meta.get("commit_date"),
        })
    return items, warnings


def _line_numbers(text: str, pattern: str) -> dict[str, int]:
    found = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in re.finditer(pattern, line):
            found.setdefault(match.group(1), lineno)
    return found


def parse_monsters(text: str, meta: dict) -> tuple[list[dict], list[str]]:
    path = source.FILES["monsters"]
    lines = _line_numbers(text, r'<Info Monster="(\d+)"')
    infos = list(ET.fromstring(text).iter("Info"))
    names = [(info.get("Name") or "").strip() for info in infos]
    ids = _unique_ids(names, [info.get("Monster") or "" for info in infos])
    monsters, warnings = [], []
    for info, name, monster_id in zip(infos, names, ids):
        if not name or not monster_id:
            warnings.append(f"monstro sem nome: Monster={info.get('Monster')}")
            continue

        def value(attr: str, parent=info) -> int | None:
            node = parent.find(attr)
            raw = node.text if node is not None else parent.get(attr)
            number = _int(raw)
            return number if number > 0 else None

        regen = info.get("RegenTime")
        monsters.append({
            "id": monster_id,
            "name": name,
            "number": _int(info.get("Monster")),
            "level": value("Level"),
            "difficulty": None,
            "hp": value("HP"),
            "atk_min": value("DmgMin"),
            "atk_max": value("DmgMax"),
            "atk_rate": value("Attack"),
            "def": value("Defense"),
            "def_rate": value("Success"),
            "elemental_def": value("PentagramDefense"),
            "elemental_dmg_min": value("PentagramDamageMin"),
            "elemental_dmg_max": value("PentagramDamageMax"),
            "respawn_seconds": _int(regen) if regen not in (None, "") else None,
            "respawn_raw": f"RegenTime={regen}" if regen not in (None, "") else None,
            "drops_normal_items": None,
            "notes": [],
            "image_url": None,
            **_provenance(meta, path, lines.get(info.get("Monster") or "")),
            "page_updated_at": meta.get("commit_date"),
        })
    return monsters, warnings


def parse_spawns(text: str, monsters: list[dict], meta: dict) -> tuple[list[dict], list[dict], list[str]]:
    """(mapas, spawns, avisos). NPCs ficam de fora; cada entrada do arquivo vira um spawn com coordenadas."""
    path = source.FILES["spawns"]
    by_number = {m["number"]: m for m in monsters}
    maps: dict[str, dict] = {}
    spawns, warnings = [], []
    missing: Counter[int] = Counter()
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"\s*<(\w+) ", line)
        if not match or match.group(1) not in source.SPAWN_KINDS:
            continue
        element = ET.fromstring(re.sub(r">.*$", "/>", line.strip().rstrip("/")))
        number = _int(element.get("Type"))
        monster = by_number.get(number)
        if monster is None:
            missing[number] += 1
            continue
        name = source.map_name(element.get("Map") or "")
        map_id = slugify(name)
        maps.setdefault(map_id, empty_map(map_id, name, _provenance(meta, path)))
        spawns.append({
            "monster_id": monster["id"],
            "map_id": map_id,
            "kind": source.SPAWN_KINDS[match.group(1)],
            "x": _attr_int(element, "PosX"), "y": _attr_int(element, "PosY"),
            "x2": _attr_int(element, "PosX2"), "y2": _attr_int(element, "PosY2"),
            "radius": _attr_int(element, "Radio"),
            "count": _attr_int(element, "Quant"),
            **_provenance(meta, path, lineno),
        })
    if missing:
        warnings.append(f"{sum(missing.values())} spawns de {len(missing)} tipos sem monstro em Monster.xml: "
                        f"{sorted(missing)[:10]}")
    return list(maps.values()), spawns, warnings
