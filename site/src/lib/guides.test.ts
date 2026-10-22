import test from "node:test";
import assert from "node:assert/strict";
import { textHtml, translated, placeholders, PT } from "./guides.ts";

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
