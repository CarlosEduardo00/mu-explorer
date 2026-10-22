/**
 * Tradução da página para o inglês no navegador (carregado só quando a pessoa escolhe English; ver lib/i18n.ts).
 * Troca os textos e os atributos de texto (placeholder, title, aria-label), o título da aba e, depois, o que os
 * scripts da página montarem (MutationObserver). Fica de fora o que já está em inglês ou é termo do jogo:
 * [lang=en], .tx (textos com as duas línguas), .term, [translate=no], [data-i18n=off], código.
 */
import { translate } from "./i18n";

const SKIP = 'script, style, code, pre, textarea, [translate="no"], [data-i18n="off"], .tx, .term, [lang="en"]:not(html)';
const ATTRS = ["placeholder", "title", "aria-label"] as const;
const done = new WeakMap<Node, string>();   // texto que nós mesmos pusemos (não traduz de novo)

function text(node: Text) {
  const raw = node.data;
  if (done.get(node) === raw) return;
  const s = raw.replace(/\s+/g, " ").trim();
  if (!s || !/[A-Za-zÀ-ÿ\d]/.test(s)) return;
  const t = translate(s);
  if (t !== s) {
    const lead = raw.match(/^\s*/)![0], trail = raw.match(/\s*$/)![0];
    node.data = lead + t + trail;
  }
  done.set(node, node.data);
}

function attrs(el: Element) {
  for (const a of ATTRS) {
    const v = el.getAttribute(a);
    if (!v) continue;
    const s = v.replace(/\s+/g, " ").trim();
    const t = translate(s);
    if (t !== s) el.setAttribute(a, t);
  }
}

function walk(root: Node) {
  const start = root.nodeType === Node.TEXT_NODE ? root.parentElement : (root as Element);
  if (!start || start.closest(SKIP)) return;
  if (root.nodeType === Node.TEXT_NODE) { text(root as Text); return; }
  attrs(root as Element);
  const it = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (n.nodeType === Node.ELEMENT_NODE && (n as Element).matches(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
  });
  for (let n = it.nextNode(); n; n = it.nextNode()) {
    if (n.nodeType === Node.TEXT_NODE) text(n as Text);
    else attrs(n as Element);
  }
}

export function start() {
  const html = document.documentElement;
  html.lang = "en";
  const titleEn = document.querySelector<HTMLMetaElement>('meta[name="mu:title-en"]')?.content;
  document.title = titleEn ? `${titleEn} · MU Explorer` : translate(document.title.replace(/\s+/g, " ").trim());
  walk(document.body);
  html.classList.remove("i18n-wait");
  new MutationObserver((list) => {
    for (const m of list) {
      if (m.type === "characterData") walk(m.target);
      else if (m.type === "attributes") attrs(m.target as Element);
      else m.addedNodes.forEach((n) => walk(n));
    }
  }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: [...ATTRS] });
}
