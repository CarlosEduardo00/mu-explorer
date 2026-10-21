"""Cliente HTTP educado usado por todos os scrapers.

- respeita robots.txt (e não coleta se ele não puder ser lido);
- bloqueia, por código, caminhos proibidos da fonte mesmo que o robots.txt mude;
- no máximo 1 requisição/segundo por host (ou o Crawl-delay, se maior), sem paralelismo;
- User-Agent identificado;
- retries com backoff exponencial em 429/5xx e erros de rede, respeitando Retry-After;
- segue redirecionamentos manualmente, checando robots.txt a cada salto;
- GET e POST de formulário de consulta (post_form) compartilham todas essas regras.
"""
from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import unquote, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests
from requests.utils import requote_uri

from scrapers.common.storage import decode_html

log = logging.getLogger(__name__)

USER_AGENT = "mu-explorer-bot/0.1 (+https://github.com/carloseduardo00/mu-explorer)"
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
REDIRECT_STATUS = frozenset({301, 302, 303, 307, 308})


class BlockedByRobots(Exception):
    """A URL é proibida pelo robots.txt ou pela lista de bloqueio da fonte."""


class RobotsUnavailable(Exception):
    """Não foi possível ler o robots.txt; por cautela, não coletamos."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_url(url: str) -> str:
    """Codifica espaços e caracteres inválidos sem recodificar os já escapados."""
    return requote_uri(url.strip())


def host_key(url: str) -> str:
    """Chave do limitador: 'www.exemplo.com' e 'exemplo.com' contam como o mesmo servidor."""
    host = (urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def charset_from(content_type: str | None) -> str | None:
    match = re.search(r"charset=([\w.-]+)", content_type or "", re.IGNORECASE)
    return match.group(1).lower() if match else None


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    content: bytes
    content_type: str | None
    encoding: str | None
    fetched_at: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def text(self) -> str:
        return decode_html(self.content, self.encoding)


class RateLimiter:
    """Garante um intervalo mínimo entre o fim de uma requisição e o início da próxima, por host."""

    def __init__(self, min_interval: float, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last: dict[str, float] = {}

    def wait(self, key: str, min_interval: float | None = None) -> None:
        interval = max(self.min_interval, min_interval or 0.0)
        last = self._last.get(key)
        if last is not None:
            remaining = interval - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)

    def mark(self, key: str) -> None:
        self._last[key] = self._clock()


class PoliteSession:
    def __init__(
        self,
        *,
        user_agent: str = USER_AGENT,
        min_interval: float = 1.0,
        timeout: float = 30.0,
        max_attempts: int = 3,
        max_redirects: int = 5,
        deny_paths: Iterable[str] = (),
        session: requests.Session | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if min_interval < 1.0:
            raise ValueError("min_interval abaixo de 1s viola a regra de coleta (máx. 1 req/s)")
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.max_redirects = max_redirects
        self.deny_paths = tuple(deny_paths)
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
            "Accept-Language": "en",
        })
        self.limiter = RateLimiter(min_interval, clock, sleep)
        self._sleep = sleep
        self._robots: dict[str, RobotFileParser] = {}
        self._crawl_delay: dict[str, float] = {}
        self.request_count = 0

    # --- API pública ---------------------------------------------------------------------

    def is_allowed(self, url: str) -> bool:
        path = unquote(urlsplit(url).path).lower()
        if any(path.startswith(p.lower()) for p in self.deny_paths):
            return False
        return self._robots_for(url).can_fetch(self.user_agent, url)

    def get(self, url: str) -> FetchResult:
        return self._fetch(url, None)

    def post_form(self, url: str, data: dict[str, str]) -> FetchResult:
        """POST de formulário de consulta (ex.: botão de página de uma listagem).

        Só para formulários que apenas LEEM dados (paginação, filtros): como o GET, é repetido
        em caso de erro temporário. Passa pelas mesmas regras (robots, bloqueios, 1 req/s).
        """
        return self._fetch(url, dict(data))

    def _fetch(self, url: str, data: dict[str, str] | None) -> FetchResult:
        requested = normalize_url(url)
        resp, final_url = self._follow(requested, check_robots=True, data=data)
        content_type = resp.headers.get("Content-Type")
        return FetchResult(
            url=requested,
            final_url=final_url,
            status=resp.status_code,
            content=resp.content,
            content_type=content_type,
            encoding=charset_from(content_type),
            fetched_at=utc_now(),
        )

    # --- internos -------------------------------------------------------------------------

    def _follow(self, url: str, *, check_robots: bool,
                data: dict[str, str] | None = None) -> tuple[requests.Response, str]:
        current = url
        for _ in range(self.max_redirects + 1):
            if check_robots and not self.is_allowed(current):
                raise BlockedByRobots(current)
            resp = self._send(current, data)
            location = resp.headers.get("Location")
            if resp.status_code in REDIRECT_STATUS and location:
                current = normalize_url(urljoin(current, location))
                data = None  # após redirecionamento, segue por GET
                continue
            return resp, current
        raise requests.TooManyRedirects(url)

    def _robots_for(self, url: str) -> RobotFileParser:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin in self._robots:
            return self._robots[origin]
        robots_url = origin + "/robots.txt"
        try:
            resp, _ = self._follow(robots_url, check_robots=False)
        except requests.RequestException as exc:
            raise RobotsUnavailable(f"{robots_url}: {exc}") from exc
        parser = RobotFileParser(robots_url)
        if resp.status_code == 200:
            parser.parse(resp.text.splitlines())
        elif 400 <= resp.status_code < 500:
            # RFC 9309: robots.txt inexistente (4xx) significa sem restrições.
            parser.parse([])
            parser.allow_all = True
        else:
            raise RobotsUnavailable(f"{robots_url}: HTTP {resp.status_code}")
        delay = parser.crawl_delay(self.user_agent)
        if delay:
            self._crawl_delay[host_key(url)] = float(delay)
        self._robots[origin] = parser
        log.info("robots.txt carregado de %s (crawl-delay=%s)", robots_url, delay)
        return parser

    def _send(self, url: str, data: dict[str, str] | None = None) -> requests.Response:
        key = host_key(url)
        for attempt in range(1, self.max_attempts + 1):
            self.limiter.wait(key, self._crawl_delay.get(key))
            try:
                self.request_count += 1
                if data is None:
                    resp = self.session.get(url, timeout=self.timeout, allow_redirects=False)
                else:
                    resp = self.session.post(url, data=data, timeout=self.timeout, allow_redirects=False)
            except (requests.ConnectionError, requests.Timeout):
                self.limiter.mark(key)
                if attempt == self.max_attempts:
                    raise
                self._sleep(self._backoff(attempt, None))
                continue
            self.limiter.mark(key)
            if resp.status_code in RETRY_STATUS and attempt < self.max_attempts:
                log.warning("HTTP %s em %s; nova tentativa %d", resp.status_code, url, attempt + 1)
                self._sleep(self._backoff(attempt, resp.headers.get("Retry-After")))
                continue
            return resp
        raise AssertionError("inalcançável")

    @staticmethod
    def _backoff(attempt: int, retry_after: str | None) -> float:
        if retry_after and retry_after.strip().isdigit():
            return min(float(retry_after), 120.0)
        return 2.0 ** attempt  # 2s, 4s, 8s...
