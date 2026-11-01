/**
 * Guias (aba de guias do Guide MU Online, scrapers.guidemu.guides) e a tradução aproximada para o português.
 *
 * O texto vem como modelo: {"t": "I would like to find the {0} for me.", "m": ["'Ring of Honor'"]}. Os marcadores
 * {n} são termos do jogo (itens de quest, nomes entre aspas simples, nomes destacados no guia), que não se traduzem;
 * <b>, <em> e <br> vêm do parser (o texto já está escapado). A tradução (data/curated/translations/guides.pt-BR.json,
 * nossa, aproximada e não oficial) troca o modelo inteiro e mantém os marcadores.
 */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

/** t: modelo em inglês (HTML já escapado); pt: texto em português quando o guia foi escrito por nós (sem marcadores). */
export interface Text { t: string; m?: string[]; pt?: string }
export type Block =
  | { type: "heading"; level: number; text: Text; style?: string }
  | { type: "paragraph"; text: Text; style?: string; center?: boolean }
  | { type: "image"; src: string; alt: string | null }
  | { type: "list"; items: Text[] }
  | { type: "table"; head: (Text | null)[]; rows: (Text | null)[][] }
  | { type: "card"; kind: string; blocks: Block[] }
  | { type: "grid"; items: Block[] }
  | { type: "tabs"; tabs: { label: Text; blocks: Block[] }[] }
  | { type: "accordion"; items: { title: Text | null; blocks: Block[] }[] };
export interface Guide {
  id: string; path: string; series: string; title: Text; siblings: { label: string; id: string }[]; blocks: Block[];
  image_urls: string[]; source: string; source_url: string; scraped_at: string | null;
}

/** Séries de guias (como as do site de origem), na ordem da página /guias/. */
export const SERIES: { id: string; label: string; text: string }[] = [
  { id: "class-change", label: "Quests de troca de classe", text: "Da 2ª à 5ª classe: onde começa, o que pede e o que dá cada parte." },
  { id: "events", label: "Eventos", text: "Castle Siege, Crywolf, Arca War e os ingressos de Blood Castle, Devil Square e Kalima." },
  { id: "wings", label: "Como criar asas", text: "Materiais, combinações e chances, das 1ª às 4ª asas e capas." },
  { id: "crafting", label: "Criação e evolução", text: "Bound Wings, Spirit Stones, Bloodangel e montarias." },
  { id: "elemental", label: "Sistema elemental", text: "Pentagramas, errtels e as versões mastery." },
  { id: "systems", label: "Sistemas do jogo", text: "Pandora's Jewels, Guardian e Artifact." },
  { id: "everyday", label: "Dia a dia", text: "Ruud, itens de skill, cartas, loja pessoal e teclas de atalho." },
];

// ---------------------------------------------------------------- layout das grades de cartões

const plainLength = (t: Text | null | undefined) => (t ? t.t.replace(/<[^>]+>/g, "").length + (t.m ?? []).join("").length : 0);

/** Altura aproximada de um bloco, em "caracteres" (uma imagem vale umas 5 linhas de texto). */
export function blockWeight(b: Block): number {
  switch (b.type) {
    case "heading": return 60;
    case "paragraph": return 40 + plainLength(b.text);
    case "image": return 250;
    case "list": return b.items.reduce((n, t) => n + 40 + plainLength(t), 0);
    case "table": return 80 + b.rows.length * 45;
    case "card": return 40 + b.blocks.reduce((n, x) => n + blockWeight(x), 0);
    case "grid": return Math.max(0, ...b.items.map(blockWeight));
    case "tabs": return Math.max(0, ...b.tabs.map((t) => t.blocks.reduce((n, x) => n + blockWeight(x), 0)));
    case "accordion": return 60 * b.items.length;
  }
}

/**
 * Quais cartões de uma grade ocupam a linha inteira. No site de origem os cartões ficam lado a lado mesmo quando um
 * é muito mais longo que o outro, o que deixa um buraco ao lado do longo. Aqui as linhas são simuladas como no
 * desktop (até `perRow` cartões por linha, na ordem): numa linha em que o cartão mais longo passa de `ratio` vezes o
 * mais curto, ele vai para uma linha só dele, e a conta recomeça. Nas outras linhas a largura de cada cartão é
 * proporcional ao tamanho (flex-grow no GuideBlocks), o que iguala as alturas. No celular, um embaixo do outro.
 */
export function wideCards(items: Block[], perRow = 3, ratio = 2.5, minWide = 600): boolean[] {
  const w = items.map(blockWeight);
  const wide = w.map(() => false);
  for (let changed = true; changed;) {
    changed = false;
    const rows: number[][] = [];
    let row: number[] = [];
    w.forEach((_, i) => {
      if (wide[i]) { if (row.length) rows.push(row); row = []; return; }
      row.push(i);
      if (row.length === perRow) { rows.push(row); row = []; }
    });
    if (row.length) rows.push(row);
    for (const r of rows) {
      const ws = r.map((i) => w[i]);
      const max = Math.max(...ws);
      if (r.length > 1 && max > minWide && max > ratio * Math.min(...ws)) {
        wide[r[ws.indexOf(max)]] = true;
        changed = true;
        break;
      }
    }
  }
  return wide;
}

/** Imagem de capa do guia: nos de asas, a primeira asa (a primeira imagem é a Chaos Goblin Machine em todos). */
export const guideCover = (g: { series: string; image_urls: string[] }): string | null =>
  (g.series === "wings" ? g.image_urls.find((u) => /items(\/|%2F)wings(\/|%2F)/.test(u)) : undefined) ?? g.image_urls[0] ?? null;

const escapeHtml = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

/** HTML de um texto: o modelo (traduzido ou original) com os termos no lugar dos marcadores. */
export function textHtml(text: Text | null | undefined, template?: string): string {
  if (!text) return "";
  return (template ?? text.t).replace(/\{(\d+)\}/g, (_, n) => {
    const term = text.m?.[Number(n)];
    return term == null ? "" : `<span class="term">${escapeHtml(term)}</span>`;
  });
}

/** Marcadores de um modelo, para conferir se a tradução manteve todos. */
export const placeholders = (t: string) => [...t.matchAll(/\{(\d+)\}/g)].map((m) => m[1]).sort().join(",");

const translationPath = resolve(process.cwd(), "data", "curated", "translations", "guides.pt-BR.json");
export const PT: Record<string, string> = existsSync(translationPath) ? JSON.parse(readFileSync(translationPath, "utf-8")) : {};

/** Tradução do modelo, se houver uma válida (com os mesmos marcadores). Guias nossos já trazem o português. */
export function translated(text: Text | null | undefined, dict: Record<string, string> = PT): string | null {
  if (!text) return null;
  if (text.pt != null) return text.pt;
  const pt = dict[text.t];
  return pt != null && placeholders(pt) === placeholders(text.t) ? pt : null;
}

// ---------------------------------------------------------------- guias escritos por nós

/** Texto do arquivo curado: [português, inglês] ou um texto igual nas duas línguas (nomes, números). */
export type CuratedText = string | [string, string];
export type CuratedBlock =
  | { h: CuratedText } | { h3: CuratedText } | { p: CuratedText } | { tip: CuratedText } | { list: CuratedText[] }
  | { table: { head: CuratedText[]; rows: CuratedText[][] } };
export interface CuratedGuide {
  id: string; series: string; title: CuratedText; blocks: CuratedBlock[];
  cover: { item?: string; npc?: string } | null;
}
/** Resolve um link [[tipo:id|texto]] para endereço e nome; null quando o registro não existe. */
export type LinkResolver = (kind: string, id: string) => { href: string; label: string } | null;

const LINK = /\[\[(item|npc|map|guide|skills)(?::([a-z0-9-]+))?(?:\|([^\]]+))?\]\]/g;

/** Texto do arquivo curado -> HTML: escapa, **negrito** vira <b> e [[...]] vira link. Link sem destino lança erro. */
export function curatedHtml(text: string, link: LinkResolver): string {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(LINK, (whole, kind: string, id: string | undefined, label: string | undefined) => {
      const target = link(kind, id ?? "");
      if (!target) throw new Error(`link sem destino nos guias: ${whole}`);
      return `<a href="${target.href}">${label ?? escapeHtml(target.label)}</a>`;
    });
}

/** [português, inglês] -> Text com os dois; texto único -> Text só com o original (igual nas duas línguas). */
export function curatedText(text: CuratedText, link: LinkResolver): Text {
  return Array.isArray(text) ? { t: curatedHtml(text[1], link), pt: curatedHtml(text[0], link) } : { t: curatedHtml(text, link) };
}

/** Blocos do arquivo curado -> blocos dos guias (os mesmos que GuideBlocks já desenha). */
export function curatedBlocks(blocks: CuratedBlock[], link: LinkResolver): Block[] {
  const tx = (t: CuratedText) => curatedText(t, link);
  return blocks.map((b): Block => {
    if ("h" in b) return { type: "heading", level: 2, text: tx(b.h), style: "section" };
    if ("h3" in b) return { type: "heading", level: 2, text: tx(b.h3) };
    if ("p" in b) return { type: "paragraph", text: tx(b.p) };
    if ("tip" in b) return { type: "card", kind: "info", blocks: [{ type: "paragraph", text: tx(b.tip) }] };
    if ("list" in b) return { type: "list", items: b.list.map(tx) };
    return { type: "table", head: b.table.head.map(tx), rows: b.table.rows.map((r) => r.map(tx)) };
  });
}

/** Guias do arquivo curado (data/curated/guides.mu-explorer.json) no formato dos guias do site. */
export function curatedGuides(list: CuratedGuide[], link: LinkResolver, cover: (c: CuratedGuide["cover"]) => string | null): Guide[] {
  return list.map((g) => {
    const img = cover(g.cover);
    return {
      id: g.id, path: `${g.series}/${g.id}`, series: g.series, title: curatedText(g.title, link), siblings: [],
      blocks: curatedBlocks(g.blocks, link), image_urls: img ? [img] : [], source: "mu-explorer", source_url: "", scraped_at: null,
    };
  });
}
