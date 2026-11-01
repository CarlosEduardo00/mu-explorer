import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { textHtml, translated, placeholders, PT, curatedHtml, curatedText, curatedBlocks, curatedGuides, SERIES, type LinkResolver } from "./guides.ts";

test("termos do jogo voltam no lugar dos marcadores, escapados", () => {
  const text = { t: "Find the {0} and give it to {1}. <b>Tarkan</b>", m: ["'Ring of Honor'", "<Marlon>"] };
  assert.equal(textHtml(text), 'Find the <span class="term">\'Ring of Honor\'</span> and give it to <span class="term">&lt;Marlon&gt;</span>. <b>Tarkan</b>');
  assert.equal(textHtml(text, "Encontre o {0} e entregue a {1}."), 'Encontre o <span class="term">\'Ring of Honor\'</span> e entregue a <span class="term">&lt;Marlon&gt;</span>.');
  assert.equal(textHtml(null), "");
});

test("tradução só vale com os mesmos marcadores", () => {
  const dict = { "Go to {0}.": "Vá até {0}.", "Talk to {0} in {1}.": "Fale com {0}." };
  assert.equal(translated({ t: "Go to {0}.", m: ["Noria"] }, dict), "Vá até {0}.");
  assert.equal(translated({ t: "Talk to {0} in {1}.", m: ["Moss", "Elbeland"] }, dict), null);
  assert.equal(translated({ t: "Sem tradução" }, dict), null);
  assert.equal(placeholders("{1} e {0} e {1}"), "0,1,1");
});

test("dicionário dos guias: toda tradução mantém os termos", () => {
  const bad = Object.entries(PT).filter(([en, pt]) => placeholders(en) !== placeholders(pt));
  assert.deepEqual(bad, []);
  assert.ok(Object.keys(PT).length > 500);
});

test("cartão muito mais longo que os da linha ocupa a linha inteira; parecidos ficam lado a lado", async () => {
  const { wideCards } = await import("./guides.ts");
  const card = (chars: number) => ({ type: "card" as const, kind: "guide", blocks: [{ type: "paragraph" as const, text: { t: "x".repeat(chars) } }] });
  assert.deepEqual(wideCards([card(400), card(600), card(2000)]), [false, false, true]);
  assert.deepEqual(wideCards([card(900), card(950), card(500)]), [false, false, false]);
  assert.deepEqual(wideCards([card(2300), card(1100)]), [false, false]);   // 2,1×: larguras proporcionais resolvem
  assert.deepEqual(wideCards([card(200)]), [false]);
});

const fakeLink: LinkResolver = (kind, id) => (kind === "skills" ? { href: "/skills/", label: "Skills" }
  : id ? { href: `/${kind}/${id}/`, label: id.toUpperCase() } : null);

test("guias escritos por nós: texto escapado, negrito e links", () => {
  assert.equal(curatedHtml("5 **Jewel** <x> & [[item:sign-of-lord]]", fakeLink), '5 <b>Jewel</b> &lt;x&gt; &amp; <a href="/item/sign-of-lord/">SIGN-OF-LORD</a>');
  assert.equal(curatedHtml("ver [[guide:mounts|montarias]] e [[skills|skills]]", fakeLink), 'ver <a href="/guide/mounts/">montarias</a> e <a href="/skills/">skills</a>');
  assert.throws(() => curatedHtml("[[npc:nada]]", () => null), /link sem destino/);
  assert.deepEqual(curatedText(["Olá", "Hello"], fakeLink), { t: "Hello", pt: "Olá" });
  assert.deepEqual(curatedText("Kalima 7", fakeLink), { t: "Kalima 7" });
  assert.equal(translated(curatedText(["Olá", "Hello"], fakeLink)), "Olá");
  const blocks = curatedBlocks([{ h: ["Título", "Title"] }, { tip: ["Dica", "Tip"] }, { table: { head: ["A"], rows: [["1"]] } }], fakeLink);
  assert.deepEqual(blocks.map((b) => b.type), ["heading", "card", "table"]);
});

test("arquivo de guias nossos: séries conhecidas e todos os links com destino", () => {
  const root = resolve(import.meta.dirname, "../../..");
  const read = (p: string) => JSON.parse(readFileSync(resolve(root, p), "utf-8"));
  const file = read("data/curated/guides.mu-explorer.json");
  const ids: Record<string, Set<string>> = {
    item: new Set(read("data/processed/combined/items.json").map((x: { id: string }) => x.id)),
    npc: new Set(read("data/processed/combined/npcs.json").map((x: { id: string }) => x.id)),
    map: new Set(read("data/processed/combined/maps.json").map((x: { id: string }) => x.id)),
    guide: new Set([...read("data/processed/combined/guides.json").map((x: { id: string }) => x.id), ...file.guides.map((g: { id: string }) => g.id)]),
  };
  const link: LinkResolver = (kind, id) => (kind === "skills" || ids[kind]?.has(id) ? { href: `/${kind}/${id}/`, label: id } : null);
  const guides = curatedGuides(file.guides, link, () => null);   // lança erro se algum link não tiver destino
  assert.ok(guides.length >= 10);
  assert.ok(guides.every((g) => SERIES.some((s) => s.id === g.series) && g.title.pt && g.blocks.length > 0));
  for (const g of file.guides) {
    if (g.cover?.item) assert.ok(ids.item.has(g.cover.item), `capa de ${g.id}`);
    if (g.cover?.npc) assert.ok(ids.npc.has(g.cover.npc), `capa de ${g.id}`);
  }
});
