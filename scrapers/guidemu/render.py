"""Páginas do guia que só existem depois do JavaScript (guias: o texto fica no código React ofuscado, em pedaços).

Renderiza num Chromium headless (Playwright, extra `render`: `pip install -e ".[render]"`; usa o Chromium do
Playwright do ambiente) com as regras da coleta: robots.txt (checado pelo PoliteSession), no máximo 1 requisição por
segundo por host (toda requisição do navegador passa pelo mesmo RateLimiter), User-Agent identificado e só o que
o site precisa para montar a página (HTML, scripts e CSS do próprio host; sem imagens, fontes, anúncios, estatísticas
nem Firebase). Abas: o site só monta a aba ativa, então cada aba é clicada e o conteúdo dela é guardado no fim da
página salva, em <section class="mu-explorer-tab" data-tablist="N" data-tab="rótulo" data-mode="pane|after">.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit

from scrapers.common.http import USER_AGENT, PoliteSession, host_key

log = logging.getLogger("scrapers.guidemu")

BLOCKED = re.compile(r"googlesyndication|googletagmanager|google-analytics|doubleclick|adservice|cloudflareinsights"
                     r"|youtube|firestore|firebase")
ALLOWED_TYPES = {"document", "script", "stylesheet", "xhr", "fetch"}   # o webpack só monta a rota com o CSS dela

# Abre cada aba do conteúdo e devolve [[índice da lista de abas, rótulo, HTML, modo], ...]. Modo "pane": o conteúdo
# fica no painel da aba. Modo "after": abas separadoras (partes de uma quest), em que o painel fica vazio e o conteúdo
# da parte é o que vem depois da lista, na mesma linha. Lista de uma aba só é cabeçalho de seção: não é clicada.
TABS_JS = """async () => {
  const sel = '.contenido-column [role=tablist]';
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const labelsOf = (l) => [...l.querySelectorAll('[role=tab]')].map((t) => t.textContent.trim());
  const keyOf = (l) => labelsOf(l).join('|');
  // O React remonta as abas a cada clique: a lista e a aba são achadas de novo pelos rótulos toda vez.
  const find = (key) => [...document.querySelectorAll(sel)].find((l) => keyOf(l) === key);
  const out = [], seen = [];
  for (let guard = 0; guard < 40; guard++) {
    const list = [...document.querySelectorAll(sel)].find((l) => !seen.includes(keyOf(l)));
    if (!list) break;
    const key = keyOf(list);
    seen.push(key);
    if (labelsOf(list).length < 2) continue;   // aba única = cabeçalho de seção, o conteúdo vem logo depois
    for (const label of labelsOf(list)) {
      const tab = find(key) && [...find(key).querySelectorAll('[role=tab]')].find((t) => t.textContent.trim() === label);
      if (!tab) continue;
      tab.click();
      await sleep(400);
      const cur = find(key);
      const now = cur && [...cur.querySelectorAll('[role=tab]')].find((t) => t.textContent.trim() === label);
      const pane = now && document.getElementById(now.getAttribute('aria-controls'));
      let html = pane ? pane.innerHTML.trim() : '', mode = 'pane';
      if (!html && cur) {
        let col = cur;
        while (col.parentElement && !col.parentElement.classList.contains('row')) col = col.parentElement;
        const after = [];
        for (let n = col.nextElementSibling; n; n = n.nextElementSibling) after.push(n.outerHTML);
        html = after.join(''); mode = 'after';
      }
      out.push([seen.length - 1, label, html, mode]);
    }
  }
  return out;
}"""


@dataclass
class Rendered:
    """Como um FetchResult: o RawStore grava conteúdo e metadados do mesmo jeito."""
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


class Renderer:
    def __init__(self, session: PoliteSession):
        from playwright.sync_api import sync_playwright
        self.session = session          # robots.txt e o mesmo limite de 1 req/s por host da coleta normal
        self.request_count = 0
        self._current: str | None = None
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self._context = self._browser.new_context(user_agent=USER_AGENT, java_script_enabled=True)
        self._context.route("**/*", self._handle)

    def _handle(self, route) -> None:
        req = route.request
        host = urlsplit(req.url).netloc
        page_host = urlsplit(self._current).netloc if self._current else host
        if req.resource_type not in ALLOWED_TYPES or host != page_host or BLOCKED.search(req.url):
            route.abort()
            return
        if not self.session.is_allowed(req.url):
            log.warning("bloqueado pelo robots.txt: %s", req.url)
            route.abort()
            return
        key = host_key(req.url)
        self.session.limiter.wait(key)
        self.request_count += 1
        route.continue_()
        self.session.limiter.mark(key)

    def render(self, url: str, wait_for: str = "h1") -> Rendered:
        self._current = url
        page = self._context.new_page()
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            status = response.status if response else 0
            page.wait_for_selector(wait_for, timeout=30_000)
            page.wait_for_timeout(800)
            tabs = page.evaluate(TABS_JS)
            page.evaluate("""(tabs) => {
              const box = document.createElement('div');
              box.id = 'mu-explorer-tabs';
              for (const [i, label, html, mode] of tabs) {
                const s = document.createElement('section');
                s.className = 'mu-explorer-tab'; s.dataset.tablist = i; s.dataset.tab = label; s.dataset.mode = mode;
                s.innerHTML = html;
                box.appendChild(s);
              }
              document.body.appendChild(box);
            }""", tabs)
            html = page.evaluate("() => '<!doctype html>' + document.documentElement.outerHTML")
        finally:
            page.close()
        return Rendered(url=url, final_url=url, status=status, content=html.encode("utf-8"),
                        content_type="text/html; charset=utf-8", encoding="utf-8",
                        fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    def close(self) -> None:
        self._context.close()
        self._browser.close()
        self._pw.stop()
