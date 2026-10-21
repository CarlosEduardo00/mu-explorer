"""Infra de teste: sessão HTTP falsa e relógio falso (os testes nunca acessam a rede)."""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from requests.structures import CaseInsensitiveDict


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@dataclass
class FakeResponse:
    status_code: int = 200
    content: bytes = b""
    headers: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


class FakeSession:
    """Responde a partir de um dicionário url -> resposta (ou lista de respostas, em sequência)."""

    def __init__(self, routes: dict, clock: FakeClock):
        self.routes = routes
        self.clock = clock
        self.headers: CaseInsensitiveDict = CaseInsensitiveDict()
        self.calls: list[tuple[float, str]] = []

    def get(self, url: str, timeout: float, allow_redirects: bool):
        return self._respond("GET", url, None, allow_redirects)

    def post(self, url: str, data: dict, timeout: float, allow_redirects: bool):
        return self._respond("POST", url, data, allow_redirects)

    def _respond(self, method: str, url: str, data: dict | None, allow_redirects: bool):
        assert allow_redirects is False
        self.calls.append((self.clock.now, url))
        self.posts = getattr(self, "posts", [])
        if method == "POST":
            self.posts.append((url, data))
            route = self.routes.get(("POST", url, tuple(sorted(data.items()))))
            if route is None:
                return FakeResponse(404, b"not found")
            return route
        route = self.routes.get(url)
        if route is None:
            return FakeResponse(404, b"not found")
        if isinstance(route, list):
            route = route.pop(0) if len(route) > 1 else route[0]
        if isinstance(route, Exception):
            raise route
        return route


def html_response(body: str, status: int = 200, content_type: str = "text/html; charset=utf-8") -> FakeResponse:
    return FakeResponse(status, body.encode("utf-8"), CaseInsensitiveDict({"Content-Type": content_type}))


def meta_for(url: str, fetched_at: str = "2026-10-20T12:00:00Z") -> dict:
    return {"url": url, "final_url": url, "fetched_at": fetched_at, "status": 200, "file": "test.html"}


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()
