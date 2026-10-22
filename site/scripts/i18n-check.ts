/**
 * Cobertura da tradução para o inglês (lib/i18n.ts): lê as páginas geradas em site/dist, passa cada texto visível
 * (e placeholder, title, aria-label, <title>) pelo translate() e lista os que continuam em português.
 * Uso: npm run build && npm run i18n:check   (sai com erro se sobrar texto sem tradução).
 *
 * "Em português" é heurístico: acentos do português ou palavras que não existem em inglês (de, para, não...).
 * Ficam de fora os textos já em inglês ou do jogo, como no navegador: [lang=en], .tx, .term, [translate=no],
 * [data-i18n=off], script, style, code, pre.
 */
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { translate } from "../src/lib/i18n.ts";

const DIST = join(import.meta.dirname, "..", "dist");
const VOID = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"]);
const PT = /[ãõçáéíóúâêôà]|\b(de|da|dos|das|em|na|nos|nas|para|por|que|uma|ou|ao|os|e|mais|sem|cada|monstros|mapas|itens|pontos|ver|vendido|dropa|todos|todas|classe|guia|guias|leva|chega|vindo|resumo|camadas|andares|chegada|entrada|mapa|monstro|nenhum|nenhuma|ordem|tipo|filtros|buscar|mostrar|limpar|ordenar|abrir|copiar|escolha|adicionar|atributos?|requisitos|notas|tabela|detalhes|chefes?|comuns|diversos|mercador|resto|sobram|faltam|outros|outras|livros|botas|luvas|elmos|escudos|joias|eventos|caixa|loja|evento|dano|defesa|taxa|pontos|curva|equipamento|guias?)\b/i;
const ENTITIES: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", "#39": "'" };
const decode = (s: string) => s.replace(/&(#x?[\da-f]+|\w+);/gi, (m, e: string) =>
  e[0] === "#" ? String.fromCodePoint(e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : Number(e.slice(1))) : ENTITIES[e] ?? m);
const norm = (s: string) => decode(s).replace(/\s+/g, " ").trim();

function* pages(dir: string): Generator<string> {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) yield* pages(join(dir, e.name));
    else if (e.name.endsWith(".html")) yield join(dir, e.name);
  }
}

// Textos das fontes (inglês do jogo, títulos de vídeo): não são da interface, mesmo quando parecem português.
const ROOT = join(import.meta.dirname, "..", "..");
const fromData = new Set<string>();
const collect = (v: unknown): void => {
  if (typeof v === "string") fromData.add(v.replace(/\s+/g, " ").trim());
  else if (Array.isArray(v)) v.forEach(collect);
  else if (v && typeof v === "object") Object.values(v).forEach(collect);
};
const dataDir = join(ROOT, "data", "processed", process.env.SITE_DATA || "combined");
if (existsSync(dataDir)) for (const f of readdirSync(dataDir)) if (f.endsWith(".json")) collect(JSON.parse(readFileSync(join(dataDir, f), "utf-8")));
const builds = join(ROOT, "data", "curated", "builds.json");
if (existsSync(builds)) collect(JSON.parse(readFileSync(builds, "utf-8")).builds.map((b: { videos: unknown[] }) => b.videos));

const found = new Map<string, Set<string>>();   // texto sem tradução -> páginas
function check(text: string, page: string) {
  const s = norm(text);
  if (!s || !/[A-Za-zÀ-ÿ]/.test(s) || fromData.has(s) || translate(s) !== s || !PT.test(s)) return;
  if (!found.has(s)) found.set(s, new Set());
  found.get(s)!.add(page);
}

function skips(tag: string): boolean {
  const cls = / class="([^"]*)"/.exec(tag)?.[1].split(/\s+/) ?? [];
  return cls.includes("tx") || cls.includes("term") || / lang="en"/.test(tag) || / translate="no"/.test(tag) || / data-i18n="off"/.test(tag);
}

let count = 0;
for (const file of pages(DIST)) {
  count++;
  const page = "/" + relative(DIST, file).replace(/index\.html$/, "");
  let html = readFileSync(file, "utf-8");
  const title = /<title>([\s\S]*?)<\/title>/.exec(html)?.[1];
  if (title && !/name="mu:title-en"/.test(html)) check(title, page);
  // código e scripts saem, mas continuam separando os textos vizinhos (no navegador são nós diferentes)
  html = html.replace(/<(script|style|pre|code|title)\b[^>]*>[\s\S]*?<\/\1>/gi, "<x/>").replace(/<!--[\s\S]*?-->/g, "");
  const stack: boolean[] = [];   // por elemento aberto: se está dentro de algo que não se traduz
  for (const tok of html.match(/<[^>]+>|[^<]+/g) ?? []) {
    const skipping = stack.length > 0 && stack[stack.length - 1];
    if (tok[0] !== "<") { if (!skipping) check(tok, page); continue; }
    if (tok[1] === "/") { stack.pop(); continue; }
    if (tok[1] === "!" || tok[1] === "?") continue;
    const name = /^<([\w-]+)/.exec(tok)?.[1].toLowerCase() ?? "";
    const skip = skipping || skips(tok);
    if (!skip) for (const m of tok.matchAll(/ (placeholder|title|aria-label)="([^"]*)"/g)) check(m[2], page);
    if (!VOID.has(name) && !tok.endsWith("/>")) stack.push(skip);
  }
}

const list = [...found].sort((a, b) => b[1].size - a[1].size);
for (const [s, where] of list) console.log(`${String(where.size).padStart(5)}  ${JSON.stringify(s)}  ${[...where].slice(0, 2).join(" ")}`);
console.log(`${count} páginas; ${list.length} textos em português sem tradução para o inglês.`);
process.exitCode = list.length ? 1 : 0;
