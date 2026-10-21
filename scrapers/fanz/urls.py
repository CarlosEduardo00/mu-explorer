"""URLs do MU Online Fanz e classificação de links."""
from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlsplit

SOURCE_ID = "fanz"
SOURCE_NAME = "MU Online Fanz"
SOURCE_CREDIT = "Dados de MU Online Fanz (muonlinefanz.com), conteúdo de IZAKTLY, recurso de fã operado com permissão da Webzen."
BASE_URL = "https://muonlinefanz.com"
HOSTS = frozenset({"muonlinefanz.com", "www.muonlinefanz.com"})
SITEMAP_URL = "https://www.muonlinefanz.com/files/sitemap/sitemap.txt"  # o robots.txt cita http://, mas o proxy do ambiente só aceita HTTPS

ITEM_LIST_URL = f"{BASE_URL}/tools/items/"
MOB_LIST_URL = f"{BASE_URL}/tools/mobs/"
MAP_LIST_URL = f"{BASE_URL}/tools/maps/"
NPC_LIST_URL = f"{BASE_URL}/tools/npc/"
LIST_URLS = {"item": ITEM_LIST_URL, "monster": MOB_LIST_URL, "map": MAP_LIST_URL, "npc": NPC_LIST_URL}
PREFIXES = {
    "item": "/tools/items/data/itemdb/",
    "monster": "/tools/mobs/data/mobdb/",
    "map": "/tools/maps/data/mapdb/",
    "npc": "/tools/npc/data/npcdb/",
}
ITEM_IMAGE_PREFIX = "/tools/items/data/graphics/"
MOB_IMAGE_PREFIX = "/tools/mobs/data/graphics/"

# Bloqueados no robots.txt do Fanz. Também bloqueados no código, mesmo que o robots.txt mude.
DENY_PATHS = (
    "/tools/items/data/php/",
    "/tools/mobs/data/php/",
    "/tools/npc/data/php/",
    "/tools/maps/data/php/",
)


def canonical(url: str) -> str:
    """Força https e tira o 'www.' (as páginas misturam http://, https:// e www)."""
    parts = urlsplit(url)
    if (parts.hostname or "").lower() not in HOSTS:
        return url
    return parts._replace(scheme="https", netloc="muonlinefanz.com").geturl()


def is_fanz(url: str) -> bool:
    return (urlsplit(url).hostname or "").lower() in HOSTS


def classify(url: str) -> str | None:
    """'item', 'monster', 'map', 'npc' ou None para outras páginas."""
    if not is_fanz(url):
        return None
    path = unquote(urlsplit(url).path)
    if not path.endswith(".php"):
        return None
    for kind, prefix in PREFIXES.items():
        if path.startswith(prefix) and "/" not in path[len(prefix):]:
            return kind
    return None


def name_from_url(url: str) -> str:
    """'.../itemdb/Dragon%20Armor.php' -> 'Dragon Armor'."""
    name = unquote(PurePosixPath(urlsplit(url).path).name)
    return name[:-4] if name.endswith(".php") else name


def page_url(kind: str, name: str) -> str:
    return f"{BASE_URL}{PREFIXES[kind]}{quote(name)}.php"
